"""Anthropic Messages API: system prompt is top-level, max_tokens is required.

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import time

from .base import (
    LLMAuthError,
    LLMError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMResult,
    LLMTimeoutError,
    LLMUnavailableError,
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str, retries: int = 2):
        import anthropic

        self.model = model
        self.retries = retries
        self._client = anthropic.Anthropic(api_key=api_key, timeout=60.0)

    def complete(self, system, messages, *, json_mode=False, temperature=0.2, max_tokens=1500) -> LLMResult:
        import anthropic

        if json_mode:
            system = system + "\n\nRespond with a single valid JSON object and nothing else."
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            start = time.perf_counter()
            try:
                resp = self._client.messages.create(
                    model=self.model,
                    system=system,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
                if not text:
                    raise LLMInvalidResponseError("empty completion")
                return LLMResult(
                    text=text,
                    model=self.model,
                    latency_s=time.perf_counter() - start,
                    input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                )
            except anthropic.AuthenticationError as e:
                raise LLMAuthError(str(e)) from e
            except anthropic.NotFoundError as e:
                raise LLMUnavailableError(str(e)) from e
            except anthropic.BadRequestError as e:
                raise LLMInvalidResponseError(str(e)) from e
            except anthropic.RateLimitError as e:
                last = LLMRateLimitError(str(e))
                time.sleep(min(2 ** attempt, 8))
            except anthropic.APITimeoutError as e:
                last = LLMTimeoutError(str(e))
            except (anthropic.APIConnectionError, anthropic.InternalServerError) as e:
                last = LLMUnavailableError(str(e))
                time.sleep(min(2 ** attempt, 8))
            except LLMError:
                raise
        if isinstance(last, LLMError):
            raise last
        raise LLMInvalidResponseError(str(last))
