"""Rule-based intent router (design doc, "Intent Routing").

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import re

from .guard import check_scope

TAILOR_PATTERNS = re.compile(
    r"\b(tailor\w*|customi[sz]e (?:my )?r[eé]sum[eé]|ats\b|skill[- ]?gaps?|"
    r"match my r[eé]sum[eé]|(?:check|score|review) my r[eé]sum[eé]|r[eé]sum[eé] studio)", re.I)
JD_HINTS = re.compile(r"\b(responsibilities|qualifications|requirements|what you['’]ll do|about the role|"
                      r"nice to have|preferred)\b", re.I)


def looks_like_job_description(text: str) -> bool:
    lines = [l for l in text.splitlines() if l.strip()]
    return len(lines) >= 6 and len(JD_HINTS.findall(text)) >= 2


def route(message: str, *, has_resume: bool = False, has_job: bool = False) -> str:
    """Return one of: 'blocked', 'tailor', 'qa'."""
    if check_scope(message):
        return "blocked"
    if looks_like_job_description(message):
        return "tailor"
    if TAILOR_PATTERNS.search(message):
        return "tailor"
    return "qa"
