"""Deterministic grounding checks on model-written rewrites (defence in depth).

Owner: Charith Reddy Mummadireddy Reddivari (checks); fabrication measurements: Dathan Neal.
These checks need no model and no network, so they work independently of model quality.
"""
from __future__ import annotations

import re

from ..analysis.taxonomy import Taxonomy, load_taxonomy
from ..models import Change

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_CAP = re.compile(r"\b[A-Z][a-zA-Z0-9+#.]{2,}\b")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "over", "using", "used", "use", "our", "their",
    "your", "was", "were", "has", "have", "had", "are", "all", "per", "via", "across", "while", "within",
    "improved", "built", "led", "led", "of", "to", "in", "on", "by", "a", "an", "as", "at", "or", "it",
}
LINKAGE_MIN = 0.25
SUMMARY_SUPPORT_MIN = 0.6
LENGTH_RATIO_MAX = 2.5


def _numbers(s: str) -> set[str]:
    return {n.rstrip("%").replace(",", "") for n in _NUM.findall(s)}


def _tokens(s: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9+#]+", s.lower()):
        if w in _STOP or len(w) < 3:
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def _sentence_initial_words(s: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"(?:^|[.!?]\s+)([A-Z][a-zA-Z]+)", s)}


def check_change(change: Change, resume_text: str, taxonomy: Taxonomy | None = None) -> Change:
    """Fill change.status/issues. status: ok | flagged (user must look) | rejected (never exported)."""
    tax = taxonomy or load_taxonomy()
    src = change.original
    new = change.proposed
    is_summary = change.id == "summary"
    scope = resume_text if is_summary else src
    issues: list[str] = []
    hard = False

    extra_nums = _numbers(new) - _numbers(resume_text if is_summary else src)
    if extra_nums:
        issues.append(f"Number(s) not in the source: {', '.join(sorted(extra_nums))}")

    resume_skills = set(tax.find_in(resume_text))
    new_skills = [s for s in tax.find_in(new) if s not in resume_skills]
    if new_skills:
        issues.append(f"Adds skill(s) your résumé does not show: {', '.join(new_skills)}")
        hard = True

    resume_low = resume_text.lower()
    skip = _sentence_initial_words(new)
    new_caps = [w for w in _CAP.findall(new) if w not in skip and w.lower() not in resume_low
                and tax.get(w) is None]
    if new_caps:
        issues.append(f"New name/term(s) not in your résumé: {', '.join(sorted(set(new_caps)))}")

    if is_summary:
        toks = _tokens(new)
        support = (len(toks & _tokens(resume_text)) / len(toks)) if toks else 1.0
        if support < SUMMARY_SUPPORT_MIN:
            issues.append(f"Only {support:.0%} of the summary's content words come from your résumé")
    else:
        a, b = _tokens(src), _tokens(new)
        sim = len(a & b) / len(a | b) if (a | b) else 1.0
        if sim < LINKAGE_MIN:
            issues.append(f"Rewrite shares little wording with the source bullet (similarity {sim:.2f})")
        if len(new.split()) > LENGTH_RATIO_MAX * max(len(src.split()), 1):
            issues.append("Rewrite is much longer than the source bullet")

    change.issues = issues
    change.status = "rejected" if hard else ("flagged" if issues else "ok")
    return change


def content_preservation(original: str, output: str) -> float:
    """Share of original content words still present (ResumeFlow-style hallucination signal)."""
    a, b = _tokens(original), _tokens(output)
    return len(a & b) / len(a) if a else 1.0


def job_alignment(job_skills: list[str], output: str, taxonomy: Taxonomy | None = None) -> float:
    tax = taxonomy or load_taxonomy()
    if not job_skills:
        return 0.0
    return sum(1 for s in job_skills if tax.matches(s, output)) / len(job_skills)
