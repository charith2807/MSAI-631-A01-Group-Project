"""Groq, OpenRouter and Gemini all expose OpenAI-compatible chat-completions endpoints.

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

BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    # Google's OpenAI-compatible endpoint for Gemini
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


class OpenAICompatProvider:
    def __init__(self, name: str, model: str, api_key: str, base_url: str | None = None, retries: int = 2):
        from openai import OpenAI  # imported lazily so offline mode needs no SDK

        self.name = name
        self.model = model
        self.retries = retries
        self._client = OpenAI(api_key=api_key, base_url=base_url or BASE_URLS[name], timeout=60.0)

    def complete(self, system, messages, *, json_mode=False, temperature=0.2, max_tokens=1500) -> LLMResult:
        import openai

        kwargs = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}, *messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            start = time.perf_counter()
            try:
                resp = self._client.chat.completions.create(**kwargs)
                text = (resp.choices[0].message.content or "").strip()
                if not text:
                    raise LLMInvalidResponseError("empty completion")
                usage = getattr(resp, "usage", None)
                return LLMResult(
                    text=text,
                    model=self.model,
                    latency_s=time.perf_counter() - start,
                    input_tokens=getattr(usage, "prompt_tokens", None),
                    output_tokens=getattr(usage, "completion_tokens", None),
                )
            except openai.AuthenticationError as e:
                raise LLMAuthError(str(e)) from e
            except openai.NotFoundError as e:
                raise LLMUnavailableError(str(e)) from e
            except openai.BadRequestError as e:
                # Some models reject response_format; retry once without JSON mode.
                if json_mode and "response_format" in kwargs:
                    kwargs.pop("response_format")
                    last = e
                    continue
                raise LLMInvalidResponseError(str(e)) from e
            except openai.RateLimitError as e:
                last = LLMRateLimitError(str(e))
                time.sleep(min(2 ** attempt, 8))
            except openai.APITimeoutError as e:
                last = LLMTimeoutError(str(e))
            except (openai.APIConnectionError, openai.InternalServerError) as e:
                last = LLMUnavailableError(str(e))
                time.sleep(min(2 ** attempt, 8))
            except LLMError:
                raise
        if isinstance(last, LLMError):
            raise last
        raise LLMInvalidResponseError(str(last))
