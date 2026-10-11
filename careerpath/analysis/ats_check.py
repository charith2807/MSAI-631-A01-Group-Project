"""Rule-based, explainable ATS-readiness check (heuristic - not any vendor's algorithm).

Owner: Charith Reddy Mummadireddy Reddivari (rule engine). Rule wording reviewed against
knowledge_base/ats_formatting_guide.md (Jangmu Sherpa).
Weights follow the design document's table and are tunable during evaluation.
"""
from __future__ import annotations

import re

from ..models import AtsReport, Finding, JobDescription, ResumeProfile
from ..ingestion.redact import EMAIL, PHONE
from .taxonomy import Taxonomy, load_taxonomy

ACTION_VERBS = {
    "achieved", "analyzed", "analysed", "architected", "automated", "built", "collaborated", "configured",
    "coordinated", "created", "delivered", "deployed", "designed", "developed", "directed", "drove",
    "established", "evaluated", "executed", "implemented", "improved", "increased", "integrated", "launched",
    "led", "maintained", "managed", "mentored", "migrated", "monitored", "optimized", "optimised", "organized",
    "owned", "planned", "presented", "reduced", "refactored", "researched", "resolved", "scaled", "shipped",
    "simplified", "streamlined", "supported", "tested", "trained", "wrote", "produced", "generated", "cleaned",
    "assisted", "conducted", "defined", "documented", "initiated", "negotiated", "processed", "published",
}
_MONTHS_ABBR = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
_MONTHS_FULL = r"(?:January|February|March|April|June|July|August|September|October|November|December)"
DATE_FORMATS = {
    "Mon YYYY": re.compile(rf"\b{_MONTHS_ABBR}\s+(?:19|20)\d{{2}}\b"),
    "Month YYYY": re.compile(rf"\b{_MONTHS_FULL}\s+(?:19|20)\d{{2}}\b"),
    "MM/YYYY": re.compile(r"\b(?:0?[1-9]|1[0-2])/(?:19|20)\d{2}\b"),
    "YYYY": re.compile(r"(?<![\d/])(?:19|20)\d{2}(?![\d/])"),
}
_NUMBER = re.compile(r"\d")


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _first_word(s: str) -> str:
    m = re.match(r"[A-Za-z]+", s.strip())
    return m.group(0).lower() if m else ""


def check_ats(resume: ResumeProfile, job: JobDescription | None = None, taxonomy: Taxonomy | None = None) -> AtsReport:
    tax = taxonomy or load_taxonomy()
    lay = resume.layout
    findings: list[Finding] = []
    cats: dict[str, list[float]] = {"Parseability": [0, 0], "Structure": [0, 0], "Job match": [0, 0]}

    def add(cat: str, rule: str, earned: float, maxp: float, evidence="", reason="", fix=""):
        earned = round(min(max(earned, 0), maxp), 2)
        findings.append(Finding(rule, earned >= maxp - 1e-9, earned, maxp, evidence, reason, fix))
        cats[cat][0] += earned
        cats[cat][1] += maxp

    # ---- Parseability (40)
    chars = len(resume.raw_text.strip())
    add("Parseability", "Text is extractable", 10 if chars >= 150 and not lay.get("image_only") else 0, 10,
        f"{chars} characters of text extracted",
        "ATS software reads text, not pictures; image-only files come through empty.",
        "Export a text-based PDF or DOCX.")
    multi = bool(lay.get("multi_column"))
    add("Parseability", "Single-column reading order", 0 if multi else 10, 10,
        "Multi-column layout detected" if multi else "No multi-column layout detected",
        "Columns can interleave when text is extracted, scrambling roles and dates.",
        "Use a single column; list skills in a normal section instead of a sidebar.")
    hazards = int(lay.get("tables", 0)) + int(lay.get("textboxes", 0))
    add("Parseability", "No tables or text boxes holding core content", 0 if hazards else 5, 5,
        f"{lay.get('tables', 0)} table(s), {lay.get('textboxes', 0)} text box(es)",
        "Parsers often read tables and text boxes out of order or skip them.",
        "Move the content into plain paragraphs and bullets.")
    body_has_contact = bool(EMAIL.search(resume.raw_text) or PHONE.search(resume.raw_text))
    hf = lay.get("header_footer_text", "")
    only_in_header = (not body_has_contact) and bool(EMAIL.search(hf) or PHONE.search(hf))
    add("Parseability", "Contact details appear in the body", 5 if body_has_contact else 0, 5,
        "Contact details found in the body" if body_has_contact else
        ("Contact details are only in the header/footer" if only_in_header else "No email or phone found"),
        "Some parsers ignore headers and footers, so recruiters may see no way to contact you.",
        "Put your email and phone in the first lines of the document body.")
    core = ["experience", "education", "skills"]
    found = [k for k in core if k in resume.section_keys]
    nonstd = [s.heading for s in resume.sections if s.key == "nonstandard"]
    add("Parseability", "Standard section headings found", 10 * len(found) / len(core), 10,
        f"Found: {', '.join(found) or 'none'}" + (f"; unrecognised headings: {', '.join(nonstd)}" if nonstd else ""),
        "ATS software maps sections by matching headings to standard names; creative titles can be missed.",
        "Use plain headings: Summary, Experience, Education, Skills.")

    # ---- Structure (20)
    all_text = resume.raw_text
    date_hits = {name: len(p.findall(all_text)) for name, p in DATE_FORMATS.items()}
    # A bare year inside a "Mon YYYY" date is not a separate format.
    stripped = all_text
    for name in ("Mon YYYY", "Month YYYY", "MM/YYYY"):
        stripped = DATE_FORMATS[name].sub(" ", stripped)
    date_hits["YYYY"] = len(DATE_FORMATS["YYYY"].findall(stripped))
    used = [n for n, c in date_hits.items() if c]
    if not used:
        add("Structure", "Consistent date format", 0, 5, "No dates found",
            "Dates let ATS software build your work timeline.", "Add start and end dates to every role.")
    else:
        # one format for date ranges is ideal; a single standalone year (e.g. graduation) is tolerated
        month_formats = [n for n in used if n != "YYYY"]
        consistent = len(month_formats) <= 1
        add("Structure", "Consistent date format", 5 if consistent else 2.5, 5,
            "Formats used: " + ", ".join(used),
            "Mixed date formats make timelines harder to parse.",
            "Pick one format, e.g. 'Jan 2022 – Mar 2024', and use it everywhere.")
    bullets = resume.bullets
    if bullets:
        av = sum(1 for b in bullets if _first_word(b.text) in ACTION_VERBS)
        share = av / len(bullets)
        add("Structure", "Bullets begin with action verbs", 5 * min(1, share / 0.7), 5,
            f"{av} of {len(bullets)} bullets start with an action verb",
            "Action verbs make achievements scannable for both parsers and people.",
            "Start each bullet with a verb such as built, led, reduced, or analyzed.")
        q = sum(1 for b in bullets if _NUMBER.search(b.text)) / len(bullets)
        add("Structure", "Bullets include numbers or concrete results", 5 * min(1, q / 0.3), 5,
            f"{round(q * 100)}% of bullets contain a number",
            "Quantified results are stronger evidence than duties.",
            "Where it is honestly true, add a count, percentage, or time saved.")
    else:
        add("Structure", "Bullets begin with action verbs", 0, 5, "No bullet points found",
            "Bullets are easier to parse and skim than paragraphs.", "Write achievements as bullet points.")
        add("Structure", "Bullets include numbers or concrete results", 0, 5, "No bullet points found",
            "Quantified results are stronger evidence than duties.", "Add measurable results to bullets.")
    pages = lay.get("pages")
    words = _words(resume.raw_text)
    est_pages = pages if pages else words / 500
    ok_len = est_pages <= 2.05 and words >= 100
    add("Structure", "Reasonable length (one to two pages)", 5 if ok_len else 2.5, 5,
        f"~{words} words" + (f", {pages} page(s)" if pages else ""),
        "Very long or very thin résumés are harder to review.", "Aim for one page early in your career, two at most.")

    # ---- Job match (40)
    job_scored = job is not None and bool(job.required_skills or job.preferred_skills or job.title)
    if job_scored:
        txt = resume.raw_text
        if job.required_skills:
            hit = [s for s in job.required_skills if tax.matches(s, txt)]
            cov = len(hit) / len(job.required_skills)
            miss = [s for s in job.required_skills if s not in hit]
            add("Job match", "Coverage of required job skills", 25 * cov, 25,
                f"{len(hit)} of {len(job.required_skills)} required skills appear" + (f"; missing: {', '.join(miss)}" if miss else ""),
                "ATS keyword matching is largely literal, so required terms need to appear as written.",
                "Add the exact term only for skills you genuinely have (see the skill-gap tab).")
        if job.preferred_skills:
            hit = [s for s in job.preferred_skills if tax.matches(s, txt)]
            cov = len(hit) / len(job.preferred_skills)
            add("Job match", "Coverage of preferred job skills", 10 * cov, 10,
                f"{len(hit)} of {len(job.preferred_skills)} preferred skills appear",
                "Preferred skills help ranking but are rarely mandatory.", "Mention them only where true.")
        if job.title:
            toks = [t for t in re.findall(r"[a-z]+", job.title.lower()) if t not in {"i", "ii", "iii", "senior", "junior", "sr", "jr", "and", "the", "of"}]
            low = txt.lower()
            share = sum(1 for t in toks if t in low) / len(toks) if toks else 0
            add("Job match", "Job title or close variant appears", 5 if share >= 0.6 else 0, 5,
                f"Job title: {job.title}", "Recruiters search by title.",
                "If a title you held is equivalent, mention the standard title in your summary.")

    earned = sum(v[0] for v in cats.values())
    avail = sum(v[1] for v in cats.values())
    return AtsReport(
        score=round(100 * earned / avail) if avail else 0,
        earned=round(earned, 2),
        available=avail,
        categories={k: (round(v[0], 2), v[1]) for k, v in cats.items() if v[1]},
        findings=findings,
        job_scored=job_scored,
    )
