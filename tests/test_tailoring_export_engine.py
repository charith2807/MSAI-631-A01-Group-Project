"""Owners: Charith (grounding, tailor, export, engine); Dathan (fabrication cases)."""
import json

import pytest

from careerpath.analysis.gaps import analyze_gaps
from careerpath.analysis.jd_analyzer import keyword_extract
from careerpath.engine import Engine
from careerpath.config import Settings
from careerpath.export_docx import build_docx
from careerpath.ingestion import load_resume
from careerpath.llm import LLMAuthError, LLMRateLimitError
from careerpath.llm.fake import FakeProvider
from careerpath.models import Change, Session
from careerpath.tailoring import tailor_resume
from careerpath.tailoring.grounding import check_change
from careerpath.tailoring.tailor import build_payload
from conftest import read_jd


def mk(src, new, cid="b1"):
    return Change(cid, "experience", src, new)


def test_grounding_clean_rewrite(resume):
    c = check_change(mk("Reduced report errors by 25% by validating inputs with SQL checks",
                        "Cut report errors by 25% by validating inputs with SQL checks"), resume.raw_text)
    assert c.status == "ok"


def test_grounding_new_skill_rejected(resume):
    c = check_change(mk("Created weekly sales summaries for 30 product lines",
                        "Created weekly sales summaries for 30 product lines using Kubernetes"), resume.raw_text)
    assert c.status == "rejected" and any("Kubernetes" in i for i in c.issues)


def test_grounding_changed_number_flagged(resume):
    c = check_change(mk("Reduced report errors by 25% by validating inputs with SQL checks",
                        "Reduced report errors by 60% by validating inputs with SQL checks"), resume.raw_text)
    assert c.status == "flagged" and any("60" in i for i in c.issues)


def test_grounding_unrelated_rewrite_flagged(resume):
    c = check_change(mk("Created weekly sales summaries for 30 product lines",
                        "Spearheaded strategic stakeholder alignment initiatives"), resume.raw_text)
    assert c.status == "flagged"


def _llm_response(resume, edit):
    payload, index = build_payload(resume)
    bullets = [{"source_id": b["id"], "text": edit.get(b["id"], b["text"])} for b in payload["bullets"]]
    return json.dumps({"summary": None, "bullets": bullets})


def test_tailor_pipeline_flags_fabrication(resume):
    job = keyword_extract(read_jd("cloud_engineer_trap"))
    gaps = analyze_gaps(resume, job)
    payload, _ = build_payload(resume)
    ids = [b["id"] for b in payload["bullets"]]
    edit = {ids[0]: "Built SQL dashboards in Tableau that cut weekly reporting time by 40%, deployed on AWS",  # trap skill
            ids[1]: "Cleaned and merged sales data from 12 stores with Python and Pandas"}  # fine
    t = tailor_resume(resume, job, gaps, FakeProvider(_llm_response(resume, edit)))
    by = {c.id: c for c in t.changes}
    assert by[ids[0]].status == "rejected" and by[ids[1]].status == "ok"
    assert all("[EMAIL]" not in c.proposed for c in t.changes)


def test_tailor_ignores_unknown_ids_and_unchanged(resume):
    job = keyword_extract(read_jd("data_analyst"))
    resp = json.dumps({"summary": None, "bullets": [{"source_id": "zzz", "text": "x"}]})
    with pytest.raises(Exception):  # too many bullets missing -> structure failure after retry
        tailor_resume(resume, job, None, FakeProvider(resp))


def test_tailor_sends_only_redacted_text(resume):
    job = keyword_extract(read_jd("data_analyst"))
    fake = FakeProvider(_llm_response(resume, {}))
    tailor_resume(resume, job, None, fake)
    sent = fake.calls[0]["messages"][0]["content"]
    assert "maya.chen@example.com" not in sent and "555-0101" not in sent


def test_export_applies_only_accepted_and_is_ats_friendly(resume):
    job = keyword_extract(read_jd("data_analyst"))
    payload, _ = build_payload(resume)
    ids = [b["id"] for b in payload["bullets"]]
    t = tailor_resume(resume, job, None, FakeProvider(_llm_response(resume, {
        ids[0]: "Created SQL dashboards in Tableau that cut weekly reporting time by 40%",
        ids[1]: "Merged and cleaned sales data from 12 stores using Python and Pandas"})))
    data = build_docx(resume, t, {ids[0]})
    out = load_resume("o.docx", data)
    assert "Created SQL dashboards" in out.raw_text and "Merged and cleaned" not in out.raw_text
    assert out.layout["tables"] == 0 and out.layout["textboxes"] == 0
    assert "maya.chen@example.com" in out.raw_text  # contacts re-attached locally


# ---- engine
def engine(llm=None):
    return Engine(Settings(provider="groq"), llm=llm)


def test_engine_offline_answer_has_source_label():
    reply, meta = engine().answer_question("How do I prepare for a behavioral interview?")
    assert "Source topic: Interview Preparation" in reply and "Offline mode" in reply and not meta["used_llm"]


def test_engine_fallback_and_block_do_not_call_model():
    fake = FakeProvider("should not be used")
    e = engine(fake)
    assert e.answer_question("What is the capital of Australia?")[1]["mode"] == "fallback"
    assert e.answer_question("Which stocks should I buy?")[1]["mode"] == "blocked"
    assert fake.calls == []


def test_engine_uses_model_and_survives_provider_errors():
    assert "Practice STAR" in engine(FakeProvider("Practice STAR stories.")).answer_question("How do I prepare for a behavioral interview?")[0]
    for err in (LLMRateLimitError("x"), LLMAuthError("x")):
        reply, _ = engine(FakeProvider(err)).answer_question("How do I prepare for a behavioral interview?")
        assert "Source topic" in reply  # graceful: shows the retrieved passage


def test_engine_mode_b_end_to_end_offline():
    e = engine()
    s = Session()
    assert "acknowledgment" in e.load_resume(s, "r.txt", b"x")
    s.acknowledged = True
    from conftest import FIX
    p = FIX / "resumes" / "maya_chen_data_analyst.txt"
    assert "Loaded" in e.load_resume(s, p.name, p.read_bytes())
    assert "upload your résumé" in e.analyze(Session(), "jd")
    assert "ATS-readiness" in e.analyze(s, read_jd("data_analyst"))
    assert "needs a language model" in e.tailor(s)
    data, score = e.export(s, set())
    assert data and 0 <= score <= 100
