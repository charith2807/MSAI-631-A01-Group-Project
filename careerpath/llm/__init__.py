from .base import (  # noqa: F401
    LLMAuthError,
    LLMError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    LLMUnavailableError,
)


def build_provider(settings):
    """Return a provider for the configured settings, or None when no key is set (offline mode)."""
    if not settings.has_key:
        return None
    if settings.provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.model, settings.api_key)
    from .openai_compat import OpenAICompatProvider

    return OpenAICompatProvider(settings.provider, settings.model, settings.api_key)
