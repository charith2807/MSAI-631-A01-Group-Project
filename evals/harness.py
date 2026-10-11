"""Shared helpers for the evaluation suites. Owner: Dathan Neal (evaluation design)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / "evals" / "data"
RESULTS = ROOT / "evals" / "results"
FIX = ROOT / "tests" / "fixtures"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def read_resume(path: Path):
    from careerpath.ingestion import load_resume
    return load_resume(path.name, path.read_bytes())


def pct(a: float, b: float) -> float:
    return round(100 * a / b, 1) if b else 0.0


class Recorder:
    """Wraps a provider and records latency and error types for operations metrics (NFR-7)."""

    def __init__(self, inner, pace_s: float = 0.0):
        self.inner, self.pace_s = inner, pace_s
        self.name, self.model = inner.name, inner.model
        self.latencies: list[float] = []
        self.errors: dict[str, int] = {}
        self.input_tokens = self.output_tokens = 0
        self.calls = 0

    def complete(self, system, messages, **kw):
        self.calls += 1
        if self.pace_s:
            time.sleep(self.pace_s)
        t = time.perf_counter()
        try:
            res = self.inner.complete(system, messages, **kw)
        except Exception as e:
            self.errors[type(e).__name__] = self.errors.get(type(e).__name__, 0) + 1
            raise
        self.latencies.append(time.perf_counter() - t)
        self.input_tokens += res.input_tokens or 0
        self.output_tokens += res.output_tokens or 0
        return res

    def summary(self) -> dict:
        lat = sorted(self.latencies)
        def q(p):
            return round(lat[min(len(lat) - 1, int(p * len(lat)))], 2) if lat else None
        return {"calls": self.calls, "ok": len(lat), "errors": self.errors,
                "latency_median_s": q(0.5), "latency_p90_s": q(0.9),
                "latency_mean_s": round(sum(lat) / len(lat), 2) if lat else None,
                "input_tokens": self.input_tokens, "output_tokens": self.output_tokens}
