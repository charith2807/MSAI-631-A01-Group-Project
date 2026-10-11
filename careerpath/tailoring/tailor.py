"""Grounded résumé tailoring: model proposes, deterministic checks dispose, user decides.

Owner: Charith Reddy Mummadireddy Reddivari (pipeline) with prompts by Dathan Neal.
"""
from __future__ import annotations

import json
import re

from ..ingestion.redact import redact, restore
from ..jsonutil import parse_json_object
from ..llm import LLMError, LLMInvalidResponseError
from ..models import Change, GapReport, JobDescription, ResumeProfile, TailoredResume
from ..prompts import TAILOR_SYSTEM, TAILOR_USER
from .grounding import check_change

REWRITABLE = {"experience", "projects"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build_payload(resume: ResumeProfile) -> tuple[dict, dict[str, tuple[str, str]]]:
    """Return (payload for the model, {id: (section, original text)}). Redacted text only."""
    c = resume.contacts
    summary = next((" ".join(ln.text for ln in s.lines) for s in resume.sections if s.key == "summary"), None)
    bullets, index = [], {}
    for s in resume.sections:
        if s.key in REWRITABLE:
            for ln in s.lines:
                if ln.kind == "bullet":
                    bullets.append({"id": ln.id, "text": redact(ln.text, c)})
                    index[ln.id] = (s.key, ln.text)
    return {"summary": redact(summary, c) if summary else None, "bullets": bullets}, index


def tailor_resume(resume: ResumeProfile, job: JobDescription, gaps: GapReport | None, llm) -> TailoredResume:
    """Raises LLMError if the provider fails; returns only changes that differ from the source."""
    payload, index = build_payload(resume)
    if not payload["bullets"] and not payload["summary"]:
        raise LLMInvalidResponseError("no bullets or summary found to tailor")
    missing = [g.skill for g in (gaps.gaps if gaps else []) if g.status == "missing"]
    user = TAILOR_USER.format(
        title=job.title or "(not given)",
        skills=", ".join(job.required_skills + job.preferred_skills) or "(none)",
        missing=", ".join(missing) or "(none)",
        payload=json.dumps(payload, ensure_ascii=False),
    )
    data = None
    last_err: Exception | None = None
    for _ in range(2):  # regenerate once on invalid / structurally wrong output
        res = llm.complete(TAILOR_SYSTEM, [{"role": "user", "content": user}],
                           json_mode=True, temperature=0.2, max_tokens=2500)
        try:
            data = parse_json_object(res.text)
            returned = {b.get("source_id") for b in data.get("bullets", []) if isinstance(b, dict)}
            if payload["bullets"] and len(returned & set(index)) < 0.8 * len(index):
                raise ValueError("structure changed: too many bullets missing")
            break
        except (ValueError, AttributeError) as e:
            last_err, data = e, None
    if data is None:
        raise LLMInvalidResponseError(str(last_err))

    changes: list[Change] = []
    seen: set[str] = set()
    for b in data.get("bullets", []):
        if not isinstance(b, dict):
            continue
        sid, text = b.get("source_id"), b.get("text")
        if sid not in index or sid in seen or not isinstance(text, str) or not text.strip():
            continue  # unknown / duplicate / empty -> ignore (source line kept)
        seen.add(sid)
        section, original = index[sid]
        proposed = restore(text.strip(), resume.contacts)
        if _norm(proposed) == _norm(original):
            continue
        changes.append(check_change(Change(sid, section, original, proposed), resume.raw_text))

    if payload["summary"] and isinstance(data.get("summary"), str) and data["summary"].strip():
        original = next(" ".join(ln.text for ln in s.lines) for s in resume.sections if s.key == "summary")
        proposed = restore(data["summary"].strip(), resume.contacts)
        if _norm(proposed) != _norm(original):
            changes.insert(0, check_change(Change("summary", "summary", original, proposed), resume.raw_text))
    return TailoredResume(changes=changes, model=getattr(llm, "model", ""))
