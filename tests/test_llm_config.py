"""Owner: Charith. Adapter selection and config - no network."""
import pytest

from careerpath import config
from careerpath.llm import build_provider


def test_no_key_means_offline(monkeypatch):
    for v in config.KEY_VARS.values():
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    s = config.load_settings()
    assert not s.has_key and build_provider(s) is None


@pytest.mark.parametrize("prov", ["groq", "gemini", "openrouter", "anthropic"])
def test_provider_selected_from_env(monkeypatch, prov):
    monkeypatch.setenv("LLM_PROVIDER", prov)
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv(config.KEY_VARS[prov], "dummy-key")
    s = config.load_settings()
    p = build_provider(s)
    assert s.model == config.DEFAULT_MODELS[prov] and p.model == s.model


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError):
        config.load_settings()
