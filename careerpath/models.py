"""In-memory data objects (design doc, "Data Design"). Nothing here is ever serialized to disk.

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Line:
    id: str
    kind: str  # "bullet" | "text"
    text: str  # original text (unredacted)


@dataclass
class Section:
    key: str  # canonical key: header, summary, experience, education, skills, projects, ...
    heading: str  # heading as written ("" for header block)
    lines: list[Line] = field(default_factory=list)


@dataclass
class ResumeProfile:
    file_type: str
    raw_text: str
    redacted_text: str
    contacts: dict[str, str]
    sections: list[Section]
    layout: dict  # pages, multi_column, tables, textboxes, header_footer_text, image_only

    @property
    def bullets(self) -> list[Line]:
        return [ln for s in self.sections for ln in s.lines if ln.kind == "bullet"]

    @property
    def section_keys(self) -> set[str]:
        return {s.key for s in self.sections}


@dataclass
class JobDescription:
    text: str
    title: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    responsibilities: list[str] = field(default_factory=list)
    years_experience: int | None = None
    source: str = "keywords"  # "llm" | "keywords"


@dataclass
class Finding:
    rule: str
    passed: bool
    points: float
    max_points: float
    evidence: str = ""
    reason: str = ""
    fix: str = ""


@dataclass
class AtsReport:
    score: int  # 0-100, normalised over the rules that applied
    earned: float
    available: float
    categories: dict[str, tuple[float, float]]
    findings: list[Finding]
    job_scored: bool


@dataclass
class SkillGap:
    skill: str
    required: bool
    status: str  # matched | transferable | missing
    evidence: str = ""
    note: str = ""
    suggestion: str = ""

    @property
    def severity(self) -> str:
        return "critical" if self.required else "minor"


@dataclass
class GapReport:
    gaps: list[SkillGap]

    @property
    def coverage(self) -> float:
        req = [g for g in self.gaps if g.required]
        if not req:
            return 0.0
        return sum(1 for g in req if g.status == "matched") / len(req)


@dataclass
class Change:
    id: str  # source line id or "summary"
    section: str
    original: str
    proposed: str
    status: str = "ok"  # ok | flagged | rejected
    issues: list[str] = field(default_factory=list)


@dataclass
class TailoredResume:
    changes: list[Change]
    model: str = ""


@dataclass
class Session:
    resume: ResumeProfile | None = None
    job: JobDescription | None = None
    ats: AtsReport | None = None
    gaps: GapReport | None = None
    tailored: TailoredResume | None = None
    acknowledged: bool = False
