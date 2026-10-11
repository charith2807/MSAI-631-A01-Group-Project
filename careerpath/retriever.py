"""TF-IDF retrieval over the curated Markdown knowledge base (no vector database).

Owner: Charith Reddy Mummadireddy Reddivari (code). Content owner: Jangmu Sherpa.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import KB_DIR

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SKIP_HEADINGS = {"sources", "references"}


@dataclass
class Passage:
    topic: str  # key
    label: str  # human-readable, shown to the user as the source-topic label
    heading: str
    text: str


@dataclass
class Hit:
    passage: Passage
    score: float


def _parse_front(raw: str) -> tuple[dict, str]:
    m = _FRONT.match(raw)
    if not m:
        return {}, raw
    meta = {}
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, raw[m.end():]


def load_passages(kb_dir: Path = KB_DIR) -> list[Passage]:
    passages: list[Passage] = []
    for path in sorted(kb_dir.glob("*.md")):
        meta, body = _parse_front(path.read_text(encoding="utf-8"))
        if meta.get("kind") == "taxonomy" or "topic" not in meta:
            continue
        for chunk in re.split(r"^## ", body, flags=re.MULTILINE)[1:]:
            heading, _, text = chunk.partition("\n")
            if heading.strip().lower() in _SKIP_HEADINGS:
                continue
            passages.append(Passage(meta["topic"], meta.get("label", meta["topic"]), heading.strip(), text.strip()))
    return passages


_WORD = re.compile(r"[a-z0-9+#]{2,}")
# Generic question words add noise: 'best pizza', 'how does X work' should not look career-related.
_ENGLISH = ENGLISH_STOP_WORDS | {"best", "good", "does", "tell", "help", "know", "better", "give", "explain", "describe"}


def _stem(w: str) -> str:
    """Very light suffix stripping so 'networking'/'network', 'resumes'/'resume' match."""
    for suf in ("ing", "ies", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def analyze(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))  # résumé -> resume
    toks = [_stem(w) for w in _WORD.findall(text) if w not in _ENGLISH]
    return toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]


class Retriever:
    def __init__(self, passages: list[Passage] | None = None, threshold: float = 0.12):
        self.passages = passages if passages is not None else load_passages()
        if not self.passages:
            raise RuntimeError("Knowledge base is empty - check the knowledge_base/ folder.")
        self.threshold = threshold
        self._vec = TfidfVectorizer(analyzer=analyze, sublinear_tf=True)
        # Heading is included so it also contributes terms.
        self._matrix = self._vec.fit_transform([f"{p.heading}. {p.heading}. {p.text}" for p in self.passages])

    @property
    def topics(self) -> list[str]:
        seen: list[str] = []
        for p in self.passages:
            if p.label not in seen:
                seen.append(p.label)
        return seen

    def search(self, query: str, k: int = 1) -> list[Hit]:
        q = self._vec.transform([query])
        sims = cosine_similarity(q, self._matrix).ravel()
        order = sims.argsort()[::-1][:k]
        return [Hit(self.passages[i], float(sims[i])) for i in order]

    def best(self, query: str) -> Hit | None:
        """Top passage, or None when the score is below the out-of-scope threshold."""
        hit = self.search(query, 1)[0]
        return hit if hit.score >= self.threshold else None
