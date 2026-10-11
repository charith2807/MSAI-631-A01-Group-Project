import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIX = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def retriever():
    from careerpath.retriever import Retriever
    return Retriever(threshold=0.12)


@pytest.fixture()
def resume():
    from careerpath.ingestion import load_resume
    p = FIX / "resumes" / "maya_chen_data_analyst.txt"
    return load_resume(p.name, p.read_bytes())


def read_resume(path):
    from careerpath.ingestion import load_resume
    return load_resume(path.name, path.read_bytes())


def read_jd(name):
    return (FIX / "jds" / f"{name}.txt").read_text(encoding="utf-8")
