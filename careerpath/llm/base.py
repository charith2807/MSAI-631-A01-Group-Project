"""Provider-neutral LLM interface (NFR-4: provider-specific code lives only in this package).

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    model: str
    latency_s: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMError(Exception):
    """Base class. `user_message` is safe to show in the UI."""

    user_message = "The language model returned an error. Please try again."

    def __init__(self, detail: str = ""):
        super().__init__(detail or self.user_message)


class LLMAuthError(LLMError):
    user_message = "The API key was rejected. Check the key in your .env file."


class LLMRateLimitError(LLMError):
    user_message = "The provider's rate limit was reached. Wait a moment and try again, or switch model."


class LLMTimeoutError(LLMError):
    user_message = "The provider took too long to respond. Please try again."


class LLMInvalidResponseError(LLMError):
    user_message = "The model returned an unusable response. Please try again."


class LLMUnavailableError(LLMError):
    user_message = "The selected model or provider is unavailable. Try a different LLM_MODEL or LLM_PROVIDER."


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        system: str,
        messages: list[dict],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResult: ...
