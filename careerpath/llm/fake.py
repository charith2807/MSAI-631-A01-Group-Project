"""Scripted provider used by tests and offline evals (no network, no key).

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

from typing import Callable

from .base import LLMResult


class FakeProvider:
    name = "fake"

    def __init__(self, responder: Callable[[str, list[dict]], str] | list[str] | str, model: str = "fake-model"):
        self.model = model
        self.calls: list[dict] = []
        self._responder = responder
        self._i = 0

    def complete(self, system, messages, *, json_mode=False, temperature=0.2, max_tokens=1500) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "json_mode": json_mode})
        r = self._responder
        if callable(r):
            text = r(system, messages)
        elif isinstance(r, list):
            text = r[min(self._i, len(r) - 1)]
            self._i += 1
        else:
            text = r
        if isinstance(text, Exception):
            raise text
        return LLMResult(text=text, model=self.model, latency_s=0.0)
