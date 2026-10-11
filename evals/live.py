"""Live evaluation against a real provider (needs an API key). Owner: Dathan Neal.

Measures what the design doc's evaluation plan calls model comparison and operations:
JSON validity, answer relevance to the retrieved context, latency, rate-limit/error behaviour,
and tailoring fidelity (fabrication attempts, preservation, job alignment).
"""
from __future__ import annotations

import os
import re
import time
from statistics import mean

from careerpath.analysis.gaps import analyze_gaps
from careerpath.analysis.jd_analyzer import analyze_job
from careerpath.analysis.taxonomy import load_taxonomy
from careerpath.config import KEY_VARS, DEFAULT_MODELS, Settings
from careerpath.engine import Engine
from careerpath.llm import LLMError, build_provider
from careerpath.tailoring import tailor_resume
from careerpath.tailoring.grounding import content_preservation, job_alignment

from .harness import FIX, Recorder, load, pct, read_resume


def _tok(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower())}


def run_live(provider: str, model: str | None = None, pace_s: float = 1.0) -> dict:
    key = os.getenv(KEY_VARS[provider], "").strip()
    if not key:
        raise RuntimeError(f"{KEY_VARS[provider]} is not set")
    settings = Settings(provider=provider, model=model or DEFAULT_MODELS[provider], api_key=key)
    rec = Recorder(build_provider(settings), pace_s=pace_s)
    engine = Engine(settings, llm=rec)
    tax = load_taxonomy()
    out: dict = {"provider": provider, "model": settings.model, "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    # ---- Mode A: Q&A
    qa = load("qa_questions.json")
    rows = []
    for x in qa["in_scope"]:
        reply, meta = engine.answer_question(x["q"])
        body = reply.rsplit("_Source topic:", 1)[0]
        passage = engine.retriever.search(x["q"])[0].passage
        rows.append({"q": x["q"], "used_llm": meta["used_llm"], "latency_s": meta["latency_s"],
                     "has_source_label": "Source topic:" in reply, "words": len(body.split()),
                     "context_overlap": round(len(_tok(body) & _tok(passage.text)) / max(len(_tok(body)), 1), 3),
                     "topic_correct": meta["topic"] == x["expected"]})
    oos = []
    for q in qa["out_of_scope"]:
        _, meta = engine.answer_question(q)
        oos.append({"q": q, "mode": meta["mode"]})
    used = [r for r in rows if r["used_llm"]]
    out["qa"] = {
        "n": len(rows), "answered_by_model_pct": pct(len(used), len(rows)),
        "source_label_pct": pct(sum(r["has_source_label"] for r in rows), len(rows)),
        "within_word_limit_pct": pct(sum(r["words"] <= 200 for r in used), len(used)),
        "mean_context_overlap": round(mean(r["context_overlap"] for r in used), 3) if used else None,
        "out_of_scope_fallback_pct": pct(sum(o["mode"] == "fallback" for o in oos), len(oos)),
    }

    # ---- JD extraction
    lab = load("gap_labels.json")
    jd_rows, jobs = [], {}
    for jd_name, spec in lab["jds"].items():
        text = (FIX / "jds" / f"{jd_name}.txt").read_text(encoding="utf-8")
        job = analyze_job(text, rec)
        jobs[jd_name] = job
        got, exp = set(job.required_skills) | set(job.preferred_skills), set(spec["required"]) | set(spec["preferred"])
        jd_rows.append({"jd": jd_name, "json_valid": job.source == "llm",
                        "precision": round(len(got & exp) / max(len(got), 1), 2), "recall": round(len(got & exp) / len(exp), 2),
                        "extra": sorted(got - exp), "missing": sorted(exp - got)})
    out["jd_extraction"] = {"json_valid_pct": pct(sum(r["json_valid"] for r in jd_rows), len(jd_rows)), "rows": jd_rows}

    # ---- Gaps (LLM transferable) + tailoring
    tailor_rows, fails, trans_claims, trans_valid = [], 0, 0, 0
    for rname in lab["labels"]:
        resume = read_resume(FIX / "resumes" / f"{rname}.txt")
        for jd_name, job in jobs.items():
            gaps = analyze_gaps(resume, job, rec)
            for g in gaps.gaps:
                if g.status == "transferable" and g.evidence:
                    trans_claims += 1
                    trans_valid += g.evidence.lower() in resume.redacted_text.lower() or g.evidence.lower() in resume.raw_text.lower()
            try:
                t = tailor_resume(resume, job, gaps, rec)
            except LLMError as e:
                fails += 1
                tailor_rows.append({"resume": rname, "jd": jd_name, "error": type(e).__name__})
                continue
            ch = t.changes
            missing = [g.skill for g in gaps.gaps if g.status == "missing"]
            proposed_all = " ".join(c.proposed for c in ch)
            attempted = [s for s in missing if tax.matches(s, proposed_all)]
            exportable = " ".join(c.proposed for c in ch if c.status != "rejected")
            leaked = [s for s in missing if tax.matches(s, exportable)]
            orig_all = " ".join(c.original for c in ch)
            applied = resume.raw_text
            for c in ch:
                if c.status == "ok":
                    applied = applied.replace(c.original, c.proposed)
            sk = job.required_skills + job.preferred_skills
            tailor_rows.append({
                "resume": rname, "jd": jd_name, "changes": len(ch),
                "ok": sum(c.status == "ok" for c in ch), "flagged": sum(c.status == "flagged" for c in ch),
                "rejected": sum(c.status == "rejected" for c in ch),
                "missing_skills": len(missing), "trap_skills_attempted": attempted, "trap_skills_exportable": leaked,
                "content_preservation": round(content_preservation(orig_all, proposed_all), 3) if ch else None,
                "alignment_before": round(job_alignment(sk, resume.raw_text), 3),
                "alignment_after_ok_changes": round(job_alignment(sk, applied), 3)})
    done = [r for r in tailor_rows if "error" not in r]
    tot = sum(r["changes"] for r in done)
    out["gaps_llm"] = {"transferable_claims": trans_claims, "with_verbatim_quote_pct": pct(trans_valid, trans_claims)}
    out["tailoring"] = {
        "runs": len(tailor_rows), "failed_runs": fails, "json_valid_pct": pct(len(done), len(tailor_rows)),
        "changes_total": tot,
        "pct_ok": pct(sum(r["ok"] for r in done), tot), "pct_flagged": pct(sum(r["flagged"] for r in done), tot),
        "pct_rejected_by_checks": pct(sum(r["rejected"] for r in done), tot),
        "runs_where_model_tried_to_add_missing_skill": sum(bool(r["trap_skills_attempted"]) for r in done),
        "runs_where_missing_skill_stayed_exportable": sum(bool(r["trap_skills_exportable"]) for r in done),
        "mean_content_preservation": round(mean(r["content_preservation"] for r in done if r["content_preservation"] is not None), 3) if done else None,
        "mean_alignment_before": round(mean(r["alignment_before"] for r in done), 3) if done else None,
        "mean_alignment_after": round(mean(r["alignment_after_ok_changes"] for r in done), 3) if done else None,
        "rows": tailor_rows}
    out["operations"] = rec.summary()
    return out
