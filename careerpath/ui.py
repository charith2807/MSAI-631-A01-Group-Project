"""Gradio interface: chat column + Résumé Studio side panel.

Owner: Sisindri Rachakonda (interface, HCI, usability). HCI principles applied (design doc):
visibility of system status, transparency (every score shows evidence), user control (review and
accept each change, one-click clear), error prevention (type checks, no export of rejected changes),
recognition over recall (suggested questions), privacy notice + acknowledgment before upload.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import gradio as gr

from .engine import Engine
from .messages import LIMITS_NOTE, PRIVACY_NOTICE, SUGGESTED_QUESTIONS
from .models import Session
from .render import render_ats, render_changes, render_gaps


# Gradio 5 needs type='messages' for dict-style history; Gradio 6 removed the argument (always messages).
_CHATBOT_KW = {} if int(gr.__version__.split(".")[0]) >= 6 else {"type": "messages"}


def _choices(session: Session):
    if not session.tailored:
        return gr.update(choices=[], value=[])
    ch = [(f"[{c.id}] {c.section}" + (" ⚠️" if c.status == "flagged" else ""), c.id)
          for c in session.tailored.changes if c.status != "rejected"]
    default = [c.id for c in session.tailored.changes if c.status == "ok"]
    return gr.update(choices=ch, value=default)


def build_ui(engine: Engine | None = None) -> gr.Blocks:
    engine = engine or Engine()

    with gr.Blocks(title="CareerPath Guide") as demo:
        session = gr.State(Session())
        gr.Markdown("# CareerPath Guide\nCareer-preparation chatbot · Group 7 · MSAI-631-A01")
        gr.Markdown(f"_{engine.status}_  \n_{LIMITS_NOTE}_")
        with gr.Row():
            with gr.Column(scale=3):
                chat = gr.Chatbot(label="Career Q&A", height=460, **_CHATBOT_KW)
                box = gr.Textbox(placeholder="Ask a career question…", show_label=False)
                gr.Examples(examples=SUGGESTED_QUESTIONS, inputs=box, label="Suggested questions")
            with gr.Column(scale=2):
                gr.Markdown("### Résumé Studio")
                gr.Markdown(PRIVACY_NOTICE)
                ack = gr.Checkbox(label="I understand my résumé text will be sent to the model provider", value=False)
                file = gr.File(label="Résumé (PDF, DOCX, TXT)", file_types=[".pdf", ".docx", ".txt"], type="filepath")
                jd = gr.Textbox(label="Job description (paste)", lines=8)
                with gr.Row():
                    analyze_btn = gr.Button("Analyse", variant="primary")
                    tailor_btn = gr.Button("Tailor résumé")
                    clear_btn = gr.Button("Clear session")
                status = gr.Markdown("")
        with gr.Tabs():
            with gr.Tab("ATS report"):
                ats_md = gr.Markdown(render_ats(None))
            with gr.Tab("Skill gaps"):
                gaps_md = gr.Markdown(render_gaps(None))
            with gr.Tab("Tailored résumé"):
                changes_md = gr.Markdown(render_changes(None))
                accept = gr.CheckboxGroup(label="Accept these changes (only accepted changes are exported)", choices=[])
                export_btn = gr.Button("Export DOCX")
                export_note = gr.Markdown("")
                download = gr.File(label="Download", interactive=False)

        def _append(history, user, bot):
            return history + [{"role": "user", "content": user}, {"role": "assistant", "content": bot}]

        def on_message(msg, history, s):
            if not msg.strip():
                return "", history, s, gr.update(), gr.update(), gr.update()
            reply, _ = engine.handle_message(s, msg)
            return "", _append(history or [], msg, reply), s, render_ats(s.ats), render_gaps(s.gaps), render_changes(s.tailored)

        def on_ack(v, s):
            s.acknowledged = bool(v)
            return s

        def on_upload(path, s):
            if not path:
                return s, ""
            p = Path(path)
            return s, engine.load_resume(s, p.name, p.read_bytes())

        def on_analyze(text, s):
            msg = engine.analyze(s, text)
            return s, msg, render_ats(s.ats), render_gaps(s.gaps)

        def on_tailor(s):
            msg = engine.tailor(s)
            return s, msg, render_changes(s.tailored), _choices(s)

        def on_export(ids, s):
            res = engine.export(s, set(ids or []))
            if res is None:
                return None, "Upload a résumé first."
            data, score = res
            tmp = Path(tempfile.mkdtemp()) / "tailored_resume.docx"  # created only on explicit export
            tmp.write_bytes(data)
            return str(tmp), f"Exported. ATS-readiness of the exported file: **{score}/100** (heuristic)."

        def on_clear():
            return (Session(), None, "", "", render_ats(None), render_gaps(None), render_changes(None),
                    gr.update(choices=[], value=[]), None, "", [], False)

        box.submit(on_message, [box, chat, session], [box, chat, session, ats_md, gaps_md, changes_md])
        ack.change(on_ack, [ack, session], session)
        file.upload(on_upload, [file, session], [session, status])
        analyze_btn.click(on_analyze, [jd, session], [session, status, ats_md, gaps_md])
        tailor_btn.click(on_tailor, [session], [session, status, changes_md, accept])
        export_btn.click(on_export, [accept, session], [download, export_note])
        clear_btn.click(on_clear, None, [session, file, jd, status, ats_md, gaps_md, changes_md, accept, download, export_note, chat, ack])
    return demo
