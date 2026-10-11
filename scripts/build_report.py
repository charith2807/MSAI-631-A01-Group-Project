"""Build the Group Project Results Report.

1. Fills the generated tables in docs/results-report.md from evals/results/*.json
   (between <!-- BEGIN:name --> and <!-- END:name --> markers).
2. Converts the Markdown to a Word document in docs/.

Usage:  python scripts/build_report.py
Owner: Sisindri Rachakonda (documentation); tables read Dathan Neal's evaluation output.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
REPORT_MD = ROOT / "docs" / "results-report.md"
REPORT_DOCX = ROOT / "docs" / "Group_7_CareerPath_Guide_Results_Report.docx"


# ----------------------------------------------------------------------------- tables
def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def live_table() -> str:
    runs = [json.load(open(p)) for p in sorted(RESULTS.glob("live_*.json"))]
    if not runs:
        return "_No live results found. Run `python -m evals.run_evals --live groq`._"
    header = ["Metric"] + [f"{r['provider']} / {r['model']}" for r in runs]

    def pct(v):
        return f"{v:.1f}%"

    def jd(r, name, key):
        for row in r["jd_extraction"]["rows"]:
            if row["jd"] == name:
                return f"{row[key]:.2f}"
        return "-"

    metrics = [
        ("**Mode A: Q&A** (35 in-scope questions)", lambda r: ""),
        ("Answered by the model", lambda r: pct(r["qa"]["answered_by_model_pct"])),
        ("Source-topic label present", lambda r: pct(r["qa"]["source_label_pct"])),
        ("Answer within 200 words", lambda r: pct(r["qa"]["within_word_limit_pct"])),
        ("Answer/passage word overlap (mean)", lambda r: f"{r['qa']['mean_context_overlap']:.3f}"),
        ("**Job-description extraction**", lambda r: ""),
        ("Valid JSON, no keyword fallback needed", lambda r: pct(r["jd_extraction"]["json_valid_pct"])),
        ("Precision, data_analyst posting", lambda r: jd(r, "data_analyst", "precision")),
        ("Recall, data_analyst posting", lambda r: jd(r, "data_analyst", "recall")),
        ("Precision, software_engineer posting", lambda r: jd(r, "software_engineer", "precision")),
        ("Recall, software_engineer posting", lambda r: jd(r, "software_engineer", "recall")),
        ("**Skill-gap analysis (model-assisted)**", lambda r: ""),
        ("Transferable claims", lambda r: str(r["gaps_llm"]["transferable_claims"])),
        ("Claims with verbatim résumé quotation", lambda r: pct(r["gaps_llm"]["with_verbatim_quote_pct"])),
        ("**Résumé tailoring** (5 résumés × 3 jobs)", lambda r: ""),
        ("Runs completed", lambda r: f"{r['tailoring']['runs'] - r['tailoring']['failed_runs']}/{r['tailoring']['runs']}"),
        ("Changes proposed", lambda r: str(r["tailoring"]["changes_total"])),
        ("Changes passing all checks", lambda r: pct(r["tailoring"]["pct_ok"])),
        ("Changes flagged for review", lambda r: pct(r["tailoring"]["pct_flagged"])),
        ("Changes rejected by deterministic checks", lambda r: pct(r["tailoring"]["pct_rejected_by_checks"])),
        ("Runs where model added a missing skill", lambda r: str(r["tailoring"]["runs_where_model_tried_to_add_missing_skill"])),
        ("Content preservation (mean, 0-1)", lambda r: f"{r['tailoring']['mean_content_preservation']:.3f}"),
        ("Job alignment before → after", lambda r: f"{r['tailoring']['mean_alignment_before']:.3f} → {r['tailoring']['mean_alignment_after']:.3f}"),
        ("**Operations**", lambda r: ""),
        ("Model calls (ok / total)", lambda r: f"{r['operations']['ok']}/{r['operations']['calls']}"),
        ("Errors", lambda r: ", ".join(f"{k} ×{v}" for k, v in r["operations"]["errors"].items()) or "none"),
        ("Median latency", lambda r: f"{r['operations']['latency_median_s']} s"),
        ("90th-percentile latency", lambda r: f"{r['operations']['latency_p90_s']} s"),
        ("Tokens in / out", lambda r: f"{r['operations']['input_tokens']:,} / {r['operations']['output_tokens']:,}"),
    ]
    return md_table(header, [[name] + [fn(r) for r in runs] for name, fn in metrics])


def offline_table() -> str:
    p = RESULTS / "offline_results.json"
    if not p.exists():
        return "_Run `python -m evals.run_evals` first._"
    o = json.load(open(p))
    rt, gd, ats, gp, gr = o["retrieval"], o["guard"], o["ats"], o["gaps"], o["grounding"]
    rows = [
        ["Retrieval top-1 topic accuracy (35 in-scope questions)", f"{rt['top1_topic_accuracy_pct']}%"],
        ["Out-of-scope questions sent to fallback (8)", f"{rt['out_of_scope_fallback_pct']}%"],
        ["Scope guard: excluded requests refused (14 prompts)", f"{gd['refusal_rate_pct']}%"],
        ["Scope guard: false refusals on benign prompts (12 prompts)", f"{gd['false_refusal_rate_pct']}%"],
        ["ATS rules: precision / recall (11 fixtures)", f"{ats['rule_precision_pct']}% / {ats['rule_recall_pct']}%"],
        ["Skill-gap agreement with hand labels (130 skills, 15 pairs)", f"{gp['agreement_pct']}%"],
        ["Transferable claims with verbatim quotation", f"{gp['transferable_with_valid_quote_pct']}%"],
        ["Fabrications caught by grounding checks (20 cases)", f"{gr['fabrication_detection_pct']}%"],
        ["Faithful rewrites wrongly flagged (20 cases)", f"{gr['false_flag_rate_pct']}%"],
    ]
    return md_table(["Offline suite", "Result"], rows)


def fill(md: str, name: str, body: str) -> str:
    pat = re.compile(rf"(<!-- BEGIN:{name} -->)(.*?)(<!-- END:{name} -->)", re.S)
    if not pat.search(md):
        return md
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", md)


# ----------------------------------------------------------------------------- docx
def add_runs(par, text: str) -> None:
    """Add text to a paragraph, honouring **bold**, *italic*/_italic_ and `code`."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    tokens = re.split(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*\*(?![\w*])|(?<![\w])_[^_\s][^_]*_(?![\w]))", text)
    from docx.shared import Pt

    for t in tokens:
        if not t:
            continue
        if t.startswith("**") and t.endswith("**"):
            par.add_run(t[2:-2]).bold = True
        elif t.startswith("`") and t.endswith("`"):
            r = par.add_run(t[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        elif (t.startswith("*") and t.endswith("*")) or (t.startswith("_") and t.endswith("_")):
            par.add_run(t[1:-1]).italic = True
        else:
            par.add_run(t)


def to_docx(md: str) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    for lvl in range(1, 4):
        st = doc.styles[f"Heading {lvl}"]
        st.font.name = "Times New Roman"
        st.font.bold = True
        st.font.size = Pt(16 - 2 * lvl)
        st.font.color.rgb = None

    lines = md.splitlines()
    i = 0
    in_code = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("<!--"):
            i += 1
            continue
        if line.strip().startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            p = doc.add_paragraph()
            r = p.add_run(line)
            r.font.name = "Consolas"
            r.font.size = Pt(8.5)
            p.paragraph_format.space_after = Pt(0)
            i += 1
            continue
        if line.strip() == "<<PAGEBREAK>>":
            doc.add_page_break()
            i += 1
            continue
        m_img = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line)
        if m_img:
            from docx.shared import Inches
            pic = doc.add_picture(str(REPORT_MD.parent / m_img.group(2)), width=Inches(6.0))
            if pic.height > Inches(7.5):  # keep tall full-page captures on one page
                pic.width = int(pic.width * Inches(7.5) / pic.height)
                pic.height = Inches(7.5)
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(cap, f"*{m_img.group(1)}*")
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in block if not re.match(r"^\|\s*:?-{3,}", r)]
            ncols = max(len(r) for r in rows)
            table = doc.add_table(rows=len(rows), cols=ncols)
            table.style = "Table Grid"
            for ri, row in enumerate(rows):
                for ci in range(ncols):
                    cell = table.cell(ri, ci)
                    cell.text = ""
                    par = cell.paragraphs[0]
                    add_runs(par, row[ci] if ci < len(row) else "")
                    for run in par.runs:
                        run.font.size = Pt(9.5)
                        if ri == 0:
                            run.bold = True
                    if ri == 0:
                        tcPr = cell._tc.get_or_add_tcPr()
                        shd = OxmlElement("w:shd")
                        shd.set(qn("w:val"), "clear")
                        shd.set(qn("w:fill"), "D9E2F3")
                        tcPr.append(shd)
            doc.add_paragraph()
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            doc.add_heading(m.group(2), level=len(m.group(1)))
            i += 1
            continue
        if line.startswith("<center>"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, re.sub(r"</?center>", "", line))
            i += 1
            continue
        if re.match(r"^\s*[-*]\s+", line):
            p = doc.add_paragraph(style="List Bullet")
            add_runs(p, re.sub(r"^\s*[-*]\s+", "", line))
            i += 1
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            p = doc.add_paragraph(style="List Number")
            add_runs(p, re.sub(r"^\s*\d+\.\s+", "", line))
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        # Hanging indent for reference entries
        p = doc.add_paragraph()
        add_runs(p, line)
        if line.startswith("@ref "):
            pass
        i += 1
    doc.save(REPORT_DOCX)


def main() -> int:
    md = REPORT_MD.read_text(encoding="utf-8")
    md = fill(md, "live_table", live_table())
    md = fill(md, "offline_table", offline_table())
    REPORT_MD.write_text(md, encoding="utf-8")
    to_docx(md)
    print(f"Updated {REPORT_MD.relative_to(ROOT)} and wrote {REPORT_DOCX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
