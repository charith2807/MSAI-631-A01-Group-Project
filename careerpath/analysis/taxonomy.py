"""Skills taxonomy loader and literal/alias matcher.

Owner: Jangmu Sherpa (taxonomy content lives in knowledge_base/skills_taxonomy.md);
loader and matcher code: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from ..config import KB_DIR

# Very short or very common English words must match case-sensitively to avoid false hits
# ("go to", "excel at").
CASE_SENSITIVE = {"Go", "Excel", "R"}


@dataclass
class Skill:
    name: str
    aliases: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    learning: str = ""

    @property
    def terms(self) -> list[str]:
        return [self.name, *self.aliases]


def _term_regex(term: str, case_sensitive: bool) -> re.Pattern:
    flags = 0 if case_sensitive else re.IGNORECASE
    # Boundaries that treat + # . as part of a token so "C++" and "Node.js" work, but
    # allow a trailing sentence period.
    return re.compile(r"(?<![\w+#])(?<!\w\.)" + re.escape(term) + r"(?![\w+#])(?!\.\w)", flags)


class Taxonomy:
    def __init__(self, skills: list[Skill]):
        self.skills = skills
        self.by_name = {s.name.lower(): s for s in skills}
        self._patterns: dict[str, list[re.Pattern]] = {
            s.name: [_term_regex(t, s.name in CASE_SENSITIVE) for t in s.terms] for s in skills
        }

    def get(self, name: str) -> Skill | None:
        return self.by_name.get(name.lower())

    def normalize(self, raw: str) -> str:
        """Map any alias to its canonical skill name; unknown strings are returned unchanged."""
        raw = raw.strip()
        for s in self.skills:
            if any(p.fullmatch(raw) for p in self._patterns[s.name]):
                return s.name
        return raw

    def matches(self, skill: str, text: str) -> bool:
        pats = self._patterns.get(skill)
        if pats is None:  # skill not in taxonomy: literal, case-insensitive
            pats = [_term_regex(skill, False)]
        return any(p.search(text) for p in pats)

    def find_in(self, text: str) -> list[str]:
        """All canonical taxonomy skills mentioned in text (document order not guaranteed)."""
        return [s.name for s in self.skills if self.matches(s.name, text)]

    def first_line_with(self, skill: str, lines: list[str]) -> str:
        for ln in lines:
            if self.matches(skill, ln):
                return ln.strip()
        return ""


@lru_cache(maxsize=1)
def load_taxonomy() -> Taxonomy:
    path = KB_DIR / "skills_taxonomy.md"
    skills: list[Skill] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("- ") or "|" not in line:
            continue
        parts = [p.strip() for p in line[2:].split("|")]
        while len(parts) < 4:
            parts.append("")
        name, aliases, related, learning = parts[:4]
        skills.append(
            Skill(
                name=name,
                aliases=[a.strip() for a in aliases.split(",") if a.strip()],
                related=[r.strip() for r in related.split(",") if r.strip()],
                learning=learning,
            )
        )
    return Taxonomy(skills)
