"""Split résumé text into standard sections, role lines, and identified bullets.

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import re

from ..models import Line, Section

STANDARD_HEADINGS = {
    "summary": {"summary", "professional summary", "profile", "objective", "career summary", "about me"},
    "experience": {"experience", "work experience", "professional experience", "employment history",
                   "work history", "relevant experience", "employment"},
    "education": {"education", "academic background", "education and training"},
    "skills": {"skills", "technical skills", "core competencies", "skills and tools", "key skills"},
    "projects": {"projects", "selected projects", "academic projects", "personal projects"},
    "certifications": {"certifications", "certificates", "licenses and certifications"},
    "other": {"awards", "publications", "volunteering", "volunteer experience", "leadership", "activities"},
}
_LOOKUP = {name: key for key, names in STANDARD_HEADINGS.items() for name in names}
_BULLET = re.compile(r"^\s*(?:[-•*▪●◦‣–\x7f\uf0b7\uf0a7])\s+")


def heading_key(line: str) -> str | None:
    norm = re.sub(r"[^a-z& ]", "", line.lower()).replace("&", "and").strip()
    return _LOOKUP.get(norm)


def looks_like_heading(line: str) -> bool:
    """A short, standalone line that may be a (possibly non-standard) heading."""
    s = line.strip()
    return 0 < len(s) <= 40 and (s.isupper() or s.endswith(":")) and not _BULLET.match(s)


def split_sections(text: str) -> list[Section]:
    sections: list[Section] = [Section("header", "")]
    counter = 0
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        key = heading_key(line.strip().rstrip(":"))
        if key:
            sections.append(Section(key, line.strip().rstrip(":")))
            continue
        if looks_like_heading(line) and len(sections) > 0 and sections[-1].lines:
            # non-standard heading: keep as its own section so the checker can flag it
            sections.append(Section("nonstandard", line.strip().rstrip(":")))
            continue
        counter += 1
        if _BULLET.match(line):
            sections[-1].lines.append(Line(f"b{counter}", "bullet", _BULLET.sub("", line).strip()))
        else:
            sections[-1].lines.append(Line(f"t{counter}", "text", line.strip()))
    return [s for s in sections if s.lines or s.key != "header"]
