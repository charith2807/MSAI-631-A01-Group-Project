"""Orchestration: routes a message to Mode A (Career Q&A) or Mode B (Résumé Studio).

Owner: Charith Reddy Mummadireddy Reddivari. No Gradio code here so it is fully testable.
"""
from __future__ import annotations

from .analysis.ats_check import check_ats
from .analysis.gaps import analyze_gaps
from .analysis.jd_analyzer import analyze_job
from .config import Settings, load_settings
from .export_docx import build_docx
from .guard import check_scope
from .ingestion import ResumeReadError, load_resume
from .llm import LLMError, build_provider
from .messages import MODE_B_NEEDS_INPUT, OFFLINE_NOTE, OUT_OF_SCOPE
from .models import Session
from .prompts import QA_SYSTEM, QA_USER
from .retriever import Retriever
from .router import looks_like_job_description, route
from .tailoring import tailor_resume


class Engine:
    def __init__(self, settings: Settings | None = None, llm=None, retriever: Retriever | None = None):
        self.settings = settings or load_settings()
        self.llm = llm if llm is not None else build_provider(self.settings)
        self.retriever = retriever or Retriever(threshold=self.settings.retrieval_threshold)

    # ---- status shown in the UI (visibility of system status)
    @property
    def status(self) -> str:
        if self.llm is None:
            return "Offline mode (no API key): retrieval-only answers; ATS and skill-gap checks still work."
        return f"Model: {getattr(self.llm, 'name', self.settings.provider)} / {self.llm.model}"

    # ---- Mode A
    def answer_question(self, message: str) -> tuple[str, dict]:
        """Return (markdown reply, meta). meta has keys: mode, topic, score, latency_s, blocked."""
        meta = {"mode": "qa", "topic": None, "score": None, "latency_s": None, "blocked": None, "used_llm": False}
        blocked = check_scope(message)
        if blocked:
            meta.update(mode="blocked", blocked=blocked[0])
            return blocked[1], meta
        hit = self.retriever.search(message, 1)[0]
        meta["score"] = round(hit.score, 3)
        if hit.score < self.retriever.threshold:
            meta["mode"] = "fallback"
            return OUT_OF_SCOPE, meta
        p = hit.passage
        meta["topic"] = p.label
        if self.llm is None:
            return f"**{p.heading}**\n\n{p.text}\n\n{OFFLINE_NOTE}\n\n_Source topic: {p.label}_", meta
        try:
            res = self.llm.complete(QA_SYSTEM, [{"role": "user", "content": QA_USER.format(
                label=p.label, context=f"{p.heading}\n{p.text}", question=message)}], temperature=0.2, max_tokens=500)
        except LLMError as e:
            return f"{e.user_message}\n\nHere is the best-matching passage instead:\n\n**{p.heading}**\n\n{p.text}\n\n_Source topic: {p.label}_", meta
        meta.update(latency_s=round(res.latency_s, 2), used_llm=True)
        return f"{res.text}\n\n_Source topic: {p.label}_", meta

    # ---- Mode B
    def load_resume(self, session: Session, filename: str, data: bytes) -> str:
        if not session.acknowledged:
            return "Please tick the privacy acknowledgment before uploading a résumé."
        try:
            session.resume = load_resume(filename, data)
        except ResumeReadError as e:
            return str(e)
        session.ats = session.gaps = session.tailored = None
        lay = session.resume.layout
        warn = " Layout warning: multiple columns detected." if lay.get("multi_column") else ""
        return f"Loaded {session.resume.file_type.upper()} résumé ({len(session.resume.raw_text.split())} words).{warn}"

    def analyze(self, session: Session, job_text: str) -> str:
        if session.resume is None or not job_text.strip():
            return MODE_B_NEEDS_INPUT
        session.job = analyze_job(job_text, self.llm)
        session.ats = check_ats(session.resume, session.job)
        session.gaps = analyze_gaps(session.resume, session.job, self.llm)
        src = "model" if session.job.source == "llm" else "keyword fallback"
        return (f"Analysed against **{session.job.title or 'the pasted job'}** (job skills extracted by {src}). "
                f"ATS-readiness {session.ats.score}/100 (heuristic). Required-skill coverage {session.gaps.coverage:.0%}. "
                "See the ATS report and Skill gaps tabs.")

    def tailor(self, session: Session) -> str:
        if session.resume is None or session.job is None:
            return MODE_B_NEEDS_INPUT
        if self.llm is None:
            return "Tailoring needs a language model. Add an API key in `.env` (see README). ATS and skill-gap reports work without one."
        try:
            session.tailored = tailor_resume(session.resume, session.job, session.gaps, self.llm)
        except LLMError as e:
            return e.user_message
        n = len(session.tailored.changes)
        flagged = sum(1 for c in session.tailored.changes if c.status != "ok")
        return f"{n} suggested change(s); {flagged} flagged or rejected by the grounding checks. Review them in the Tailored résumé tab."

    def export(self, session: Session, accepted_ids: set[str]) -> tuple[bytes, int] | None:
        """DOCX bytes and the re-checked ATS score of the exported file."""
        if session.resume is None:
            return None
        data = build_docx(session.resume, session.tailored, accepted_ids)
        exported = load_resume("export.docx", data)
        return data, check_ats(exported, session.job).score

    # ---- chat entry point
    def handle_message(self, session: Session, message: str) -> tuple[str, dict]:
        kind = route(message, has_resume=session.resume is not None, has_job=session.job is not None)
        if kind == "tailor":
            if session.resume is None:
                return MODE_B_NEEDS_INPUT, {"mode": "tailor"}
            jd_text = message if looks_like_job_description(message) else (session.job.text if session.job else "")
            if not jd_text:
                return MODE_B_NEEDS_INPUT, {"mode": "tailor"}
            return self.analyze(session, jd_text), {"mode": "tailor"}
        return self.answer_question(message)
