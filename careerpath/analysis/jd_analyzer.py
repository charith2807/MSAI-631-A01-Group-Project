"""Job-description analysis: LLM extraction validated against a schema, with a keyword fallback.

Owner: Dathan Neal (prompt/schema behaviour) and Charith Reddy Mummadireddy Reddivari (integration).
"""
from __future__ import annotations

import re

from ..jsonutil import parse_json_object
from ..llm import LLMError
from ..models import JobDescription
from ..prompts import JD_SYSTEM
from .taxonomy import Taxonomy, load_taxonomy

_PREFERRED_HEAD = re.compile(r"\b(preferred|nice to have|bonus|a plus|desired|good to have)\b", re.I)
_REQUIRED_HEAD = re.compile(r"\b(required|requirements|qualifications|must have|what you['’]ll need|minimum)\b", re.I)
_RESP_HEAD = re.compile(r"\b(responsibilities|what you['’]ll do|duties|the role)\b", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:or more\s+)?years?", re.I)


def keyword_extract(text: str, taxonomy: Taxonomy | None = None) -> JobDescription:
    """Deterministic fallback: taxonomy skills, split into required/preferred by the section they sit in."""
    tax = taxonomy or load_taxonomy()
    required: list[str] = []
    preferred: list[str] = []
    resp: list[str] = []
    mode = "required"
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        is_heading = len(s) < 60 and not re.match(r"^[-•*]", s) and (s.endswith(":") or s.isupper() or len(s.split()) <= 5)
        if is_heading and _PREFERRED_HEAD.search(s):
            mode = "preferred"; continue
        if is_heading and _RESP_HEAD.search(s):
            mode = "resp"; continue
        if is_heading and _REQUIRED_HEAD.search(s):
            mode = "required"; continue
        if mode == "resp":
            if re.match(r"^[-•*]", s):
                resp.append(re.sub(r"^[-•*]\s*", "", s))
            continue
        target = preferred if mode == "preferred" else required
        for sk in tax.find_in(s):
            if sk not in required and sk not in preferred:
                target.append(sk)
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    title = re.sub(r"^(job title|title|position|role)\s*[:\-]\s*", "", first, flags=re.I) if len(first) < 80 else ""
    years = [int(m) for m in _YEARS.findall(text)]
    return JobDescription(text=text, title=title, required_skills=required, preferred_skills=preferred,
                          responsibilities=resp[:10], years_experience=min(years) if years else None, source="keywords")


def _validate(obj: dict, tax: Taxonomy) -> dict:
    def skills(key: str) -> list[str]:
        v = obj.get(key, [])
        if not isinstance(v, list):
            raise ValueError(f"{key} must be a list")
        out: list[str] = []
        for x in v:
            if isinstance(x, str) and x.strip():
                n = tax.normalize(x)
                if n not in out:
                    out.append(n)
        return out

    req, pref = skills("required_skills"), skills("preferred_skills")
    pref = [p for p in pref if p not in req]
    years = obj.get("years_experience")
    return {
        "title": str(obj.get("title", "") or "").strip(),
        "required_skills": req[:15],
        "preferred_skills": pref[:10],
        "responsibilities": [str(r) for r in obj.get("responsibilities", []) if isinstance(r, str)][:10],
        "years_experience": years if isinstance(years, int) else None,
    }


def analyze_job(text: str, llm=None, taxonomy: Taxonomy | None = None) -> JobDescription:
    tax = taxonomy or load_taxonomy()
    if llm is not None:
        for _ in range(2):  # one retry on invalid output (design doc)
            try:
                res = llm.complete(JD_SYSTEM, [{"role": "user", "content": text[:12000]}],
                                   json_mode=True, temperature=0.0, max_tokens=900)
                data = _validate(parse_json_object(res.text), tax)
                if data["required_skills"] or data["preferred_skills"]:
                    return JobDescription(text=text, source="llm", **data)
            except (ValueError, LLMError):
                continue
    return keyword_extract(text, tax)
