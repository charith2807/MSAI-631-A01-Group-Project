"""Owners: Charith (retriever, router), Jangmu (guard patterns)."""
import pytest

from careerpath.guard import check_scope
from careerpath.router import route


def test_kb_loaded_with_all_topics(retriever):
    assert {"Interview Preparation", "Networking", "Résumé Improvement", "Skill Development",
            "Career Transitions", "Job Search Planning"} <= set(retriever.topics)
    assert all(p.topic != "taxonomy" for p in retriever.passages)


def test_retrieves_expected_topic(retriever):
    hit = retriever.best("How do I prepare for a behavioral interview?")
    assert hit and hit.passage.label == "Interview Preparation"


def test_accent_insensitive(retriever):
    assert retriever.search("improve my resume")[0].passage.label == retriever.search("improve my résumé")[0].passage.label


def test_out_of_scope_gets_none(retriever):
    assert retriever.best("What is the capital of Australia?") is None


@pytest.mark.parametrize("q,cat", [
    ("Should I hire a lawyer to sue my employer?", "legal"),
    ("Which stocks should I invest in?", "financial"),
    ("I think I have depression", "mental_health"),
    ("Will I definitely get hired at Google?", "guarantee"),
    ("Scrape LinkedIn for jobs", "scrape_apply"),
])
def test_guard_blocks(q, cat):
    assert check_scope(q)[0] == cat


@pytest.mark.parametrize("q", ["How do I negotiate a job offer?", "I'm looking for software engineer jobs in Plano.",
                               "How do I handle interview anxiety and nerves?"])
def test_guard_allows(q):
    assert check_scope(q) is None


def test_router():
    assert route("Which stocks should I buy?") == "blocked"
    assert route("Please tailor my resume to this job") == "tailor"
    assert route("How do I network?") == "qa"
    jd = "Responsibilities:\n- a\n- b\n- c\nRequirements:\n- d\n- e\n- f"
    assert route(jd) == "tailor"
