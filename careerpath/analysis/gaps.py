"""Skill-gap analysis: matched / transferable / missing, with verifiable evidence.

Owner: Charith Reddy Mummadireddy Reddivari (pipeline); Dathan Neal (gap prompt).
A transferable claim must carry a quotation that exists verbatim in the resume;
otherwise it is downgraded to missing (design doc, "Skill-Gap Analysis").
"""
from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..jsonutil import parse_json_object
from ..llm import LLMError
from ..models import GapReport, JobDescription, ResumeProfile, SkillGap
from ..prompts import GAP_SYSTEM
from .taxonomy import Taxonomy, load_taxonomy

SIMILARITY_THRESHOLD = 0.25


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_is_verbatim(quote: str, resume_text: str) -> bool:
    q = _norm(quote)
    return len(q) >= 8 and q in _norm(resume_text)


def _suggestion(skill: str, tax: Taxonomy) -> str:
    sk = tax.get(skill)
    if sk and sk.learning:
        return sk.learning
    return f"Build a small, honest project that uses {skill} and describe it in your portfolio. Don't list it until you've used it."


def analyze_gaps(resume: ResumeProfile, job: JobDescription, llm=None, taxonomy: Taxonomy | None = None) -> GapReport:
    tax = taxonomy or load_taxonomy()
    lines = [ln.text for s in resume.sections for ln in s.lines]
    text = resume.raw_text
    bullet_texts = [b.text for b in resume.bullets] or lines

    wanted = [(s, True) for s in job.required_skills] + [(s, False) for s in job.preferred_skills]
    gaps: list[SkillGap] = []
    unresolved: list[SkillGap] = []

    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit(bullet_texts + [s for s, _ in wanted]) if bullet_texts else None
    bullet_mat = vec.transform(bullet_texts) if vec is not None else None

    for skill, required in wanted:
        if tax.matches(skill, text):
            ev = tax.first_line_with(skill, lines)
            gaps.append(SkillGap(skill, required, "matched", ev, "Appears in your résumé."))
            continue
        sk = tax.get(skill)
        gap = SkillGap(skill, required, "missing", suggestion=_suggestion(skill, tax))
        # Tier 2a: related taxonomy skill appears literally
        for rel in (sk.related if sk else []):
            if tax.matches(rel, text):
                gap.status = "transferable"
                gap.evidence = tax.first_line_with(rel, lines)
                gap.note = (f"No literal '{skill}', but your experience with {rel} is related. "
                            f"Describe it honestly (e.g. '{rel}-based ...') rather than claiming {skill}.")
                break
        # Tier 2b: TF-IDF similarity between the skill profile and résumé bullets
        if gap.status == "missing" and vec is not None and sk:
            profile = " ".join([sk.name, *sk.aliases, *sk.related])
            sims = cosine_similarity(vec.transform([profile]), bullet_mat).ravel()
            i = int(sims.argmax())
            if sims[i] >= SIMILARITY_THRESHOLD:
                gap.status = "transferable"
                gap.evidence = bullet_texts[i]
                gap.note = f"Similar wording to {skill} found (similarity {sims[i]:.2f}). Check it is genuinely relevant."
        if gap.status == "missing":
            unresolved.append(gap)
        gaps.append(gap)

    # Tier 2c (optional): LLM proposes transferable skills, but only with a verbatim quote.
    if llm is not None and unresolved:
        try:
            msg = f"RESUME:\n{resume.redacted_text[:9000]}\n\nSKILLS WITH NO LITERAL MATCH: {', '.join(g.skill for g in unresolved)}"
            res = llm.complete(GAP_SYSTEM, [{"role": "user", "content": msg}], json_mode=True, temperature=0.0, max_tokens=800)
            by_skill = {g.skill.lower(): g for g in unresolved}
            for item in parse_json_object(res.text).get("transferable", []):
                g = by_skill.get(str(item.get("skill", "")).lower())
                quote = str(item.get("quote", ""))
                if g and quote_is_verbatim(quote, resume.redacted_text):
                    g.status, g.evidence = "transferable", quote
                    g.note = str(item.get("explanation", ""))[:300]
        except (ValueError, LLMError):
            pass  # keep deterministic result

    order = {"missing": 0, "transferable": 1, "matched": 2}
    gaps.sort(key=lambda g: (not g.required, order[g.status]))
    return GapReport(gaps)
