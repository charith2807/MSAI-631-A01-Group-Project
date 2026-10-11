"""Owners: Charith (pipeline), Jangmu (taxonomy), Dathan (JD/gap prompts; fake provider here)."""
import json

from careerpath.analysis.gaps import analyze_gaps, quote_is_verbatim
from careerpath.analysis.jd_analyzer import analyze_job, keyword_extract
from careerpath.analysis.taxonomy import load_taxonomy
from careerpath.llm.fake import FakeProvider
from careerpath.llm import LLMRateLimitError
from conftest import read_jd, read_resume, FIX


def test_taxonomy_matching_edge_cases():
    t = load_taxonomy()
    assert t.matches("C++", "Wrote C++ services")
    assert t.matches("Node.js", "Built node.js apps") and not t.matches("JavaScript", "Built Node.js apps")
    assert t.matches("SQL", "wrote SQL.") and not t.matches("SQL", "MySQL only")
    assert not t.matches("Go", "go to market") and t.matches("Go", "services in Go")
    assert t.normalize("postgres") == "PostgreSQL" and t.normalize("Unknown Thing") == "Unknown Thing"


def test_keyword_fallback_splits_required_and_preferred():
    jd = keyword_extract(read_jd("data_analyst"))
    assert jd.title == "Data Analyst"
    assert {"SQL", "Python", "Excel", "Tableau"} <= set(jd.required_skills)
    assert {"Pandas", "Power BI", "Agile"} == set(jd.preferred_skills)
    assert jd.source == "keywords"


def test_llm_jd_extraction_validated_and_normalized():
    payload = json.dumps({"title": "Data Analyst", "required_skills": ["postgres", "python3"],
                          "preferred_skills": ["Python"], "responsibilities": ["x"], "years_experience": 3})
    jd = analyze_job("some posting", FakeProvider(payload))
    assert jd.required_skills == ["PostgreSQL", "Python"] and jd.preferred_skills == []
    assert jd.source == "llm" and jd.years_experience == 3


def test_jd_invalid_output_retries_then_falls_back():
    fake = FakeProvider(["not json", "still not json"])
    jd = analyze_job(read_jd("data_analyst"), fake)
    assert jd.source == "keywords" and len(fake.calls) == 2


def test_jd_provider_error_falls_back():
    jd = analyze_job(read_jd("data_analyst"), FakeProvider(LLMRateLimitError("429")))
    assert jd.source == "keywords"


def test_gap_classification(resume):
    jd = keyword_extract(read_jd("data_analyst"))
    gaps = {g.skill: g for g in analyze_gaps(resume, jd).gaps}
    assert gaps["SQL"].status == "matched" and "SQL" in gaps["SQL"].evidence
    assert gaps["Power BI"].status == "transferable" and "Tableau" in gaps["Power BI"].evidence


def test_missing_skill_gets_learning_suggestion_not_claim():
    r = read_resume(FIX / "resumes" / "daniel_brooks_career_changer.txt")
    jd = keyword_extract(read_jd("software_engineer"))
    g = {x.skill: x for x in analyze_gaps(r, jd).gaps}
    assert g["Docker"].status == "missing" and "Dockerfile" in g["Docker"].suggestion


def test_llm_transferable_needs_verbatim_quote(resume):
    jd = keyword_extract(read_jd("cloud_engineer_trap"))
    good = "Maintained Excel forecasting models used by a team of 8 buyers"
    resp = json.dumps({"transferable": [
        {"skill": "Terraform", "quote": good, "explanation": "ok"},
        {"skill": "Kubernetes", "quote": "Orchestrated clusters at scale", "explanation": "invented"}]})
    gaps = {g.skill: g for g in analyze_gaps(resume, jd, FakeProvider(resp)).gaps}
    assert gaps["Terraform"].status == "transferable"
    assert gaps["Kubernetes"].status == "missing"  # fabricated quote downgraded


def test_quote_check():
    assert quote_is_verbatim("built  SQL dashboards", "We Built SQL dashboards today")
    assert not quote_is_verbatim("short", "short text")
