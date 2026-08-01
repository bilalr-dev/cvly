"""Groq LLM client for the critical-evaluation (checker) path.

OpenAI-compatible HTTP API. Keep this model distinct from Gemini so maker
and checker don't share the same failure modes.

Free tier: ~30 RPM / 14,400 req/day. Default model is llama-3.1-8b-instant
to stay inside free-tier token limits.

Ref: Grounded Optimization L5.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from backend.services.rate_limiter import AsyncRateLimiter
from backend.utils.constants import (
    GROQ_DEFAULT_MODEL,
    GROQ_ERROR_BODY_CHARS,
    GROQ_MAX_TOKENS,
    GROQ_RATE_LIMIT_CALLS,
    GROQ_RATE_LIMIT_PERIOD_SECONDS,
    GROQ_TIMEOUT_SECONDS,
    HTTP_OK,
)

logger = logging.getLogger(__name__)

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAPIError(Exception):
    pass


class GroqLLMService:
    """Groq LLM service using the OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        from backend.config import get_settings

        self.api_key = api_key
        self.model = model or get_settings().groq_model or GROQ_DEFAULT_MODEL
        # Stay under the free-tier 30 RPM ceiling with a small buffer
        self._rate_limiter = AsyncRateLimiter(
            max_calls=GROQ_RATE_LIMIT_CALLS,
            period_seconds=GROQ_RATE_LIMIT_PERIOD_SECONDS,
        )

    async def evaluate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Send an evaluation prompt to Groq and return parsed JSON."""
        await self._rate_limiter.acquire()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": GROQ_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        timeout = aiohttp.ClientTimeout(total=GROQ_TIMEOUT_SECONDS)
        try:
            # Separate with blocks: combined ones race on aiohttp SSL cleanup
            async with aiohttp.ClientSession(timeout=timeout) as session:  # noqa: SIM117
                async with session.post(
                    _GROQ_API_URL, headers=headers, json=payload
                ) as response:
                    if response.status != HTTP_OK:
                        body = await response.text()
                        msg = (
                            f"Groq HTTP {response.status}: "
                            f"{body[:GROQ_ERROR_BODY_CHARS]}"
                        )
                        raise GroqAPIError(msg)
                    data = await response.json()

            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

        except aiohttp.ClientError as e:
            msg = f"Groq connection error: {e}"
            raise GroqAPIError(msg) from e
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            msg = f"Groq response parse error: {e}"
            raise GroqAPIError(msg) from e
