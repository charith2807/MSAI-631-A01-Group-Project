"""Owner: Charith (ingestion, ATS engine). Fixtures: Jangmu."""
import pytest

from careerpath.analysis.ats_check import check_ats
from careerpath.ingestion import ResumeReadError, load_resume
from careerpath.ingestion.redact import redact, restore
from conftest import FIX, read_resume

L = FIX / "layouts"


def failed(path):
    rep = check_ats(read_resume(path))
    return {f.rule for f in rep.findings if not f.passed}


def test_contacts_redacted_and_restorable(resume):
    assert "maya.chen@example.com" not in resume.redacted_text
    assert "[EMAIL]" in resume.redacted_text and resume.contacts["name"] == "Maya Chen"
    assert restore(resume.redacted_text, resume.contacts).count("maya.chen@example.com") == 1


def test_sections_and_bullets(resume):
    assert {"experience", "education", "skills", "summary"} <= resume.section_keys
    assert len(resume.bullets) >= 7


@pytest.mark.parametrize("name", ["clean.txt", "clean.docx", "clean.pdf"])
def test_clean_files_pass_everything(name):
    assert failed(L / name) == set()


@pytest.mark.parametrize("name,rule", [
    ("two_column.pdf", "Single-column reading order"),
    ("table_layout.docx", "No tables or text boxes holding core content"),
    ("header_contact.docx", "Contact details appear in the body"),
    ("creative_headings.txt", "Standard section headings found"),
    ("mixed_dates.txt", "Consistent date format"),
    ("too_short.txt", "Reasonable length (one to two pages)"),
])
def test_rule_triggers(name, rule):
    assert rule in failed(L / name)


def test_image_only_pdf_is_rejected_with_message():
    with pytest.raises(ResumeReadError, match="scanned image"):
        load_resume("image_only.pdf", (L / "image_only.pdf").read_bytes())


def test_bad_inputs():
    with pytest.raises(ResumeReadError):
        load_resume("x.exe", b"abc")
    with pytest.raises(ResumeReadError):
        load_resume("x.pdf", b"not a pdf")
    with pytest.raises(ResumeReadError):
        load_resume("x.txt", b"")


def test_job_match_scoring(resume):
    from careerpath.analysis.jd_analyzer import keyword_extract
    from conftest import read_jd
    job = keyword_extract(read_jd("data_analyst"))
    rep = check_ats(resume, job)
    assert rep.job_scored and "Job match" in rep.categories
    assert 0 <= rep.score <= 100
    assert check_ats(resume).job_scored is False
