"""Scope guard: blocks excluded advice categories without calling the model.

Owner: Jangmu Sherpa (category patterns, coverage review) with wording by Sisindri Rachakonda
(messages.py).
"""
from __future__ import annotations

import re

from .messages import BLOCKED

_PATTERNS: dict[str, re.Pattern] = {
    "legal": re.compile(
        r"\b(legal advice|lawyer|attorney|lawsuit|sue (?:my|the|an?)|wrongful termination|"
        r"is (?:my|a) non-?compete (?:legal|enforceable)|immigration law)\b", re.I),
    "medical": re.compile(
        r"\b(medical advice|diagnos\w+|medications?|prescri\w+|symptoms?|my doctor)\b", re.I),
    "financial": re.compile(
        r"\b(invest\w*|stocks?|crypto\w*|mortgage|retirement account|401\(?k\)?|"
        r"tax (?:advice|return|deduction)s?|financial advice|file my taxes)\b", re.I),
    "mental_health": re.compile(
        r"\b(depress\w*|suicid\w*|self[- ]harm|anxiety disorder|panic attacks?|"
        r"mental health (?:advice|treatment|diagnosis)|therapy|therapist|am i bipolar)\b", re.I),
    "guarantee": re.compile(
        r"\b(guarantee\w*\b.*\b(job|offer|interview|hired)|"
        r"will i (?:definitely|for sure|surely) get\b|promise me (?:i|that i)\b)", re.I),
    "scrape_apply": re.compile(
        r"\b(scrape|scraping|auto[- ]?appl\w+|apply (?:to|for) (?:these|those|all|\d+|the) .{0,40}for me|"
        r"submit (?:my|the|these) applications?|apply on my behalf)\b", re.I),
}


def check_scope(message: str) -> tuple[str, str] | None:
    """Return (category, user-facing message) if the request is in an excluded category, else None."""
    for category, pat in _PATTERNS.items():
        if pat.search(message):
            return category, BLOCKED[category]
    return None
