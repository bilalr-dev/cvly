"""Self-correction module — sends Groq critic feedback back to Gemini for fixes.

Implements one correction round: Gemini generates → Groq reviews → Gemini corrects.
Only issues persisting after correction reach the user.

Ref: MA-CF (Xie et al., 2026) — decouple critic from generator, loop once
"""
from __future__ import annotations

import logging
import re

from backend.config import get_settings
from backend.prompts import BULLET_CORRECTION_PROMPT, COVER_LETTER_CORRECTION_PROMPT
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.utils.constants import (
    MIN_CORRECTED_COVER_LENGTH,
    get_language_display_name,
)

logger = logging.getLogger(__name__)

_BULLET_LINE_PREFIX = re.compile(r"^\s*(?:\d+[\.\)]\s*|[-*•]\s*)")


def _format_bullet_issues(issues: list[dict]) -> str:
    return "\n".join(
        f"- Bullet {i.get('bullet_index', '?')}: [{i.get('type', '?')}] {i.get('explanation', '')}"
        for i in issues
    )


def _format_cover_issues(issues: list[dict]) -> str:
    return "\n".join(
        f"- [{i.get('type', '?')}] {i.get('explanation', '')}"
        for i in issues
    )


def _parse_corrected_bullets(raw: str, expected_count: int) -> list[str] | None:
    """Parse numbered/plain lines from Gemini correction text."""
    lines = [
        _BULLET_LINE_PREFIX.sub("", line).strip()
        for line in raw.strip().splitlines()
        if line.strip()
    ]
    # Drop JSON scaffolding if model ignored plain-text instruction
    lines = [ln for ln in lines if ln not in {"{", "}", "[", "]"} and not ln.startswith('"')]
    if len(lines) >= expected_count:
        return lines[:expected_count]
    return None


async def correct_bullets(
    original_bullets: list[str],
    rewritten_bullets: list[str],
    issues: list[dict],
    gemini_service: GeminiLLMService,
    language: str | None = None,
) -> list[str]:
    """Send critic feedback to Gemini to fix flagged bullet issues."""
    language = language or get_settings().default_language
    if not issues:
        return rewritten_bullets

    prompt = BULLET_CORRECTION_PROMPT.format(
        original_bullets="\n".join(f"{idx + 1}. {b}" for idx, b in enumerate(original_bullets)),
        rewritten_bullets="\n".join(f"{idx + 1}. {b}" for idx, b in enumerate(rewritten_bullets)),
        issues=_format_bullet_issues(issues),
        language=get_language_display_name(language),
    )

    try:
        result = await gemini_service.agenerate_text(prompt, temperature=0.2)
    except (GeminiAPIError, RuntimeError, ValueError) as e:
        logger.debug("Bullet correction failed: %s — keeping original rewrite", e)
        return rewritten_bullets

    parsed = _parse_corrected_bullets(result, len(rewritten_bullets))
    if parsed is not None:
        return parsed
    logger.debug("Bullet correction parse failed — keeping original rewrite")
    return rewritten_bullets


async def correct_cover_letter(
    cover_letter: str,
    issues: list[dict],
    gemini_service: GeminiLLMService,
    language: str | None = None,
) -> str:
    """Send critic feedback to Gemini to fix flagged cover letter issues."""
    language = language or get_settings().default_language
    if not issues:
        return cover_letter

    prompt = COVER_LETTER_CORRECTION_PROMPT.format(
        cover_letter=cover_letter,
        issues=_format_cover_issues(issues),
        language=get_language_display_name(language),
    )

    try:
        result = await gemini_service.agenerate_text(prompt, temperature=0.3)
    except (GeminiAPIError, RuntimeError, ValueError) as e:
        logger.debug("Cover letter correction failed: %s — keeping original", e)
        return cover_letter

    if len(result.strip()) > MIN_CORRECTED_COVER_LENGTH:
        return result.strip()
    return cover_letter
