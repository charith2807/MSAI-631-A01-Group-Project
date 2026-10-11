"""Markdown rendering of Mode B results for the UI.

Owner: Sisindri Rachakonda (interface and report presentation).
"""
from __future__ import annotations

from .messages import ATS_DISCLAIMER, TAILOR_DISCLAIMER
from .models import AtsReport, GapReport, TailoredResume

_ICON = {"matched": "✅", "transferable": "🔶", "missing": "❌"}


def render_ats(rep: AtsReport | None) -> str:
    if rep is None:
        return "Upload a résumé, paste a job description, and press **Analyse**."
    lines = [f"### ATS-readiness (heuristic): {rep.score}/100", f"_{ATS_DISCLAIMER}_", ""]
    if not rep.job_scored:
        lines.append("_No job description analysed yet, so the job-match category is not scored._\n")
    for cat, (e, m) in rep.categories.items():
        lines.append(f"- **{cat}**: {e:g} / {m:g}")
    lines.append("\n#### Findings")
    for f in sorted(rep.findings, key=lambda f: f.passed):
        mark = "✅" if f.passed else "⚠️"
        lines.append(f"- {mark} **{f.rule}** ({f.points:g}/{f.max_points:g}) - {f.evidence}")
        if not f.passed:
            lines.append(f"  - Why it matters: {f.reason}\n  - Fix: {f.fix}")
    return "\n".join(lines)


def render_gaps(rep: GapReport | None) -> str:
    if rep is None:
        return "No skill-gap analysis yet."
    lines = [f"### Skill gaps - required-skill coverage {rep.coverage:.0%}",
             "✅ matched · 🔶 transferable (quoted evidence) · ❌ missing", ""]
    for g in rep.gaps:
        lines.append(f"- {_ICON[g.status]} **{g.skill}** ({g.severity}) - {g.status}")
        if g.evidence:
            lines.append(f"  - Evidence: “{g.evidence}”")
        if g.note and g.status != "matched":
            lines.append(f"  - {g.note}")
        if g.status == "missing":
            lines.append(f"  - To build this skill: {g.suggestion}")
    lines.append("\n_Never add a skill you don't have; learn it first._")
    return "\n".join(lines)


def render_changes(t: TailoredResume | None) -> str:
    if t is None:
        return "No tailored résumé yet."
    if not t.changes:
        return "The model proposed no changes."
    out = [f"_{TAILOR_DISCLAIMER}_", ""]
    for c in t.changes:
        tag = {"ok": "", "flagged": " ⚠️ flagged", "rejected": " ⛔ rejected by checks (not exportable)"}[c.status]
        out.append(f"**[{c.id}] {c.section}**{tag}\n\n> **Original:** {c.original}\n>\n> **Proposed:** {c.proposed}\n")
        for i in c.issues:
            out.append(f"- {i}")
        out.append("")
    return "\n".join(out)
