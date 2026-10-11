"""Configuration from environment variables / .env (NFR-3: keys never committed).

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional convenience
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "knowledge_base"

# Model names change often - confirm in each provider console (design doc, "Provider Options").
DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    "anthropic": "claude-sonnet-4-5",
    "gemini": "gemini-2.5-flash",
}
KEY_VARS = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


@dataclass
class Settings:
    provider: str = "groq"
    model: str = ""
    api_key: str = ""
    retrieval_threshold: float = 0.12

    @property
    def has_key(self) -> bool:
        return bool(self.api_key)


def load_settings() -> Settings:
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower() or "groq"
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"LLM_PROVIDER must be one of {sorted(DEFAULT_MODELS)}, got {provider!r}")
    model = os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODELS[provider]
    key = os.getenv(KEY_VARS[provider], "").strip()
    threshold = float(os.getenv("RETRIEVAL_THRESHOLD", "0.12") or 0.12)
    return Settings(provider=provider, model=model, api_key=key, retrieval_threshold=threshold)
