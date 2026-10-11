"""Deterministic evaluation suites - no network, no API key. Owners noted per suite."""
from __future__ import annotations

import time

from careerpath.analysis.ats_check import check_ats
from careerpath.analysis.gaps import analyze_gaps
from careerpath.analysis.jd_analyzer import keyword_extract
from careerpath.guard import check_scope
from careerpath.ingestion import ResumeReadError, load_resume
from careerpath.models import Change
from careerpath.retriever import Retriever
from careerpath.tailoring.grounding import check_change

from .harness import FIX, load, pct, read_resume


def retrieval(threshold: float = 0.12) -> dict:
    """Owner: Dathan Neal (question set) / Jangmu Sherpa (coverage review)."""
    d = load("qa_questions.json")
    r = Retriever(threshold=threshold)
    rows, per_topic = [], {}
    for x in d["in_scope"]:
        h = r.search(x["q"])[0]
        rows.append({"q": x["q"], "expected": x["expected"], "got": h.passage.label, "score": round(h.score, 3)})
        t = per_topic.setdefault(x["expected"], [0, 0]); t[1] += 1; t[0] += h.passage.label == x["expected"]
    out_scores = [(q, round(r.search(q)[0].score, 3)) for q in d["out_of_scope"]]
    sweep = []
    for th in (0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.25):
        in_ok = sum(1 for x in rows if x["score"] >= th)  # in-scope questions answered (not falsely refused)
        out_ok = sum(1 for _, s in out_scores if s < th)  # out-of-scope correctly refused
        correct_topic = sum(1 for x in rows if x["score"] >= th and x["got"] == x["expected"])
        sweep.append({"threshold": th, "in_scope_answered_pct": pct(in_ok, len(rows)),
                      "in_scope_correct_topic_pct": pct(correct_topic, len(rows)),
                      "out_of_scope_fallback_pct": pct(out_ok, len(out_scores))})
    amb = [{"q": a["q"], "got": r.search(a["q"])[0].passage.label, "score": round(r.search(a["q"])[0].score, 3),
            "fallback": r.search(a["q"])[0].score < threshold} for a in d["ambiguous"]]
    return {
        "threshold": threshold,
        "n_in_scope": len(rows), "n_out_of_scope": len(out_scores),
        "top1_topic_accuracy_pct": pct(sum(x["got"] == x["expected"] for x in rows), len(rows)),
        "in_scope_answered_pct": pct(sum(x["score"] >= threshold for x in rows), len(rows)),
        "out_of_scope_fallback_pct": pct(sum(s < threshold for _, s in out_scores), len(out_scores)),
        "per_topic_accuracy": {k: f"{v[0]}/{v[1]}" for k, v in per_topic.items()},
        "misses": [x for x in rows if x["got"] != x["expected"]],
        "out_of_scope_scores": out_scores, "ambiguous": amb, "threshold_sweep": sweep,
    }


def guard() -> dict:
    """Owner: Jangmu Sherpa."""
    d = load("guard_prompts.json")
    blocked = [(x, check_scope(x["q"])) for x in d["should_block"]]
    correct_cat = sum(1 for x, r in blocked if r and r[0] == x["cat"])
    refused = sum(1 for _, r in blocked if r)
    false_ref = [q for q in d["should_allow"] if check_scope(q)]
    return {"n_block": len(blocked), "refusal_rate_pct": pct(refused, len(blocked)),
            "correct_category_pct": pct(correct_cat, len(blocked)),
            "n_allow": len(d["should_allow"]), "false_refusal_rate_pct": pct(len(false_ref), len(d["should_allow"])),
            "false_refusals": false_ref,
            "missed": [x["q"] for x, r in blocked if not r]}


def ats() -> dict:
    """Owner: Charith Reddy Mummadireddy Reddivari (rules) / Jangmu Sherpa (labels)."""
    lab = load("ats_labels.json")
    tp = fp = fn = tn = 0
    detail, rejected_ok = [], True
    for name, expected in lab["expected_fail"].items():
        rep = check_ats(read_resume(FIX / "layouts" / name))
        got = {f.rule for f in rep.findings if not f.passed}
        allrules = {f.rule for f in rep.findings}
        exp = set(expected)
        tp += len(got & exp); fp += len(got - exp); fn += len(exp - got); tn += len(allrules - got - exp)
        detail.append({"fixture": name, "expected_fail": sorted(exp), "got_fail": sorted(got), "score": rep.score})
    for name in lab["expected_rejected"]:
        try:
            load_resume(name, (FIX / "layouts" / name).read_bytes()); rejected_ok = False
        except ResumeReadError:
            pass
    return {"fixtures": len(lab["expected_fail"]) + len(lab["expected_rejected"]),
            "rule_precision_pct": pct(tp, tp + fp), "rule_recall_pct": pct(tp, tp + fn),
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "image_only_rejected_with_message": rejected_ok, "detail": detail,
            "caveat": "Fixtures are constructed to trigger one rule each, so this checks rule correctness, not real-world coverage."}


def gaps() -> dict:
    """Owners: Jangmu Sherpa (hand labels), Charith (analyser)."""
    lab = load("gap_labels.json")
    conf: dict[str, dict[str, int]] = {}
    pairs, correct, total, disagreements = 0, 0, 0, []
    trans_pred = trans_ok = 0
    for rname, per_jd in lab["labels"].items():
        resume = read_resume(FIX / "resumes" / f"{rname}.txt")
        for jd_name, truth in per_jd.items():
            jd_text = (FIX / "jds" / f"{jd_name}.txt").read_text(encoding="utf-8")
            job = keyword_extract(jd_text)
            pairs += 1
            for g in analyze_gaps(resume, job).gaps:
                t = "matched" if g.skill in truth["matched"] else "transferable" if g.skill in truth["transferable"] else "missing"
                conf.setdefault(t, {}).setdefault(g.status, 0)
                conf[t][g.status] += 1
                total += 1; correct += t == g.status
                if g.status == "transferable":
                    trans_pred += 1; trans_ok += bool(g.evidence) and g.evidence.lower() in resume.raw_text.lower()
                if t != g.status:
                    disagreements.append({"resume": rname, "jd": jd_name, "skill": g.skill, "label": t, "predicted": g.status})
    # job-description extraction (keyword fallback) vs the labelled skill lists
    jd_stats = []
    for jd_name, spec in lab["jds"].items():
        job = keyword_extract((FIX / "jds" / f"{jd_name}.txt").read_text(encoding="utf-8"))
        got = set(job.required_skills) | set(job.preferred_skills)
        exp = set(spec["required"]) | set(spec["preferred"])
        jd_stats.append({"jd": jd_name, "found": len(got & exp), "expected": len(exp), "extra": sorted(got - exp),
                         "required_split_correct": set(job.required_skills) == set(spec["required"])})
    return {"pairs": pairs, "skill_labels": total, "agreement_pct": pct(correct, total),
            "confusion_label_vs_predicted": conf,
            "transferable_claims": trans_pred, "transferable_with_valid_quote_pct": pct(trans_ok, trans_pred),
            "jd_keyword_extraction": jd_stats, "disagreements": disagreements}


def grounding() -> dict:
    """Owner: Dathan Neal (cases) / Charith (checks)."""
    d = load("grounding_cases.json")
    resume = read_resume(FIX / "resumes" / f"{d['resume']}.txt")
    by_type: dict[str, list[int]] = {}
    clean_flagged, fab_caught, misses, false_flags = 0, 0, [], []
    n_clean = n_fab = 0
    for c in d["cases"]:
        ch = check_change(Change("b0", "experience", c["source"], c["proposed"]), resume.raw_text)
        caught = ch.status != "ok"
        if c["label"] == "clean":
            n_clean += 1; clean_flagged += caught
            if caught: false_flags.append({"proposed": c["proposed"], "issues": ch.issues})
        else:
            n_fab += 1; fab_caught += caught
            t = by_type.setdefault(c["type"], [0, 0]); t[1] += 1; t[0] += caught
            if not caught: misses.append({"type": c["type"], "proposed": c["proposed"]})
    return {"n_clean": n_clean, "n_fabricated": n_fab,
            "fabrication_detection_pct": pct(fab_caught, n_fab), "false_flag_rate_pct": pct(clean_flagged, n_clean),
            "detection_by_type": {k: f"{v[0]}/{v[1]}" for k, v in by_type.items()},
            "missed_fabrications": misses, "false_flags": false_flags}


def operations() -> dict:
    """Owner: Charith - local processing time of deterministic stages (ms)."""
    r = Retriever()
    resume = read_resume(FIX / "resumes" / "maya_chen_data_analyst.txt")
    job = keyword_extract((FIX / "jds" / "data_analyst.txt").read_text(encoding="utf-8"))
    def t(fn, n=20):
        s = time.perf_counter()
        for _ in range(n): fn()
        return round((time.perf_counter() - s) / n * 1000, 2)
    s = time.perf_counter(); Retriever(); build = round((time.perf_counter() - s) * 1000, 1)
    pdf = (FIX / "layouts" / "clean.pdf").read_bytes()
    return {"index_build_ms": build, "retrieval_query_ms": t(lambda: r.search("How do I prepare for an interview?")),
            "ats_check_ms": t(lambda: check_ats(resume, job)), "gap_analysis_ms": t(lambda: analyze_gaps(resume, job)),
            "pdf_ingestion_ms": t(lambda: load_resume("c.pdf", pdf), 5)}


def run_all() -> dict:
    return {"retrieval": retrieval(), "guard": guard(), "ats": ats(), "gaps": gaps(),
            "grounding": grounding(), "operations": operations()}
