"""Critical evaluator - independent LLM reviewer for ALL Gemini outputs.

Uses Groq (Llama 3.3 70B) as the checker in a maker-checker architecture.
Gemini generates, Groq verifies. Different models catch different errors.

Ref: Grounded Optimization Layer 5 (arXiv:2607.01457)
Ref: MA-CF framework (Xie et al., ScienceDirect 2026) - decouple factuality from quality
Ref: Multi-agent orchestration patterns (beam.ai 2026) - maker-checker with model diversity
"""
from __future__ import annotations

import logging
from typing import Any

from backend.prompts import (
    CRITICAL_EVALUATOR_SYSTEM_PROMPT,
    CRITICAL_REVIEW_BULLETS_PROMPT,
    CRITICAL_REVIEW_COVER_LETTER_PROMPT,
    CRITICAL_REVIEW_CV_PROMPT,
)
from backend.services.groq_llm import GroqAPIError, GroqLLMService
from backend.utils.constants import (
    PROMPT_NONE_LISTED,
    PROMPT_NOT_PROVIDED,
    get_language_display_name,
)

logger = logging.getLogger(__name__)


def _failed_review(error: Exception) -> dict[str, Any]:
    return {
        "is_acceptable": False,
        "issues": [],
        "summary": f"Review failed: {error}",
    }


class CriticalEvaluator:
    """Reviews all Gemini outputs using Groq for model diversity."""

    def __init__(self, groq_service: GroqLLMService) -> None:
        self.groq = groq_service

    async def review_bullets(
        self,
        original_bullets: list[str],
        rewritten_bullets: list[str],
        job_description: str = "",
        language: str = "fr",
    ) -> dict[str, Any]:
        """Review rewritten bullets against originals for fabrication."""
        prompt = CRITICAL_REVIEW_BULLETS_PROMPT.format(
            original_bullets="\n".join(f"- {b}" for b in original_bullets),
            rewritten_bullets="\n".join(f"- {b}" for b in rewritten_bullets),
            job_description=job_description or PROMPT_NOT_PROVIDED,
            language=get_language_display_name(language),
        )
        try:
            return await self.groq.evaluate(CRITICAL_EVALUATOR_SYSTEM_PROMPT, prompt)
        except GroqAPIError as e:
            logger.warning("Critical evaluator (bullets) failed: %s", e)
            return _failed_review(e)

    async def review_cover_letter(  # noqa: PLR0913
        self,
        cover_letter_text: str,
        candidate_summary: str,
        candidate_achievements: list[str],
        target_company: str,
        job_description: str = "",
        language: str = "fr",
    ) -> dict[str, Any]:
        """Review cover letter for entity bleed and hallucinated claims."""
        achievements_text = (
            "\n".join(f"- {a}" for a in candidate_achievements)
            if candidate_achievements
            else PROMPT_NONE_LISTED
        )
        prompt = CRITICAL_REVIEW_COVER_LETTER_PROMPT.format(
            cover_letter=cover_letter_text,
            candidate_summary=candidate_summary or PROMPT_NOT_PROVIDED,
            candidate_achievements=achievements_text,
            target_company=target_company,
            job_description=job_description or PROMPT_NOT_PROVIDED,
            language=get_language_display_name(language),
        )
        try:
            return await self.groq.evaluate(CRITICAL_EVALUATOR_SYSTEM_PROMPT, prompt)
        except GroqAPIError as e:
            logger.warning("Critical evaluator (cover letter) failed: %s", e)
            return _failed_review(e)

    async def review_cv(
        self,
        cv_markdown: str,
        original_resume_text: str,
        target_language: str = "fr",
        language: str = "fr",
    ) -> dict[str, Any]:
        """Review the full tailored CV for structural and language issues."""
        prompt = CRITICAL_REVIEW_CV_PROMPT.format(
            cv_markdown=cv_markdown,
            original_resume=original_resume_text or PROMPT_NOT_PROVIDED,
            target_language=get_language_display_name(target_language),
            language=get_language_display_name(language),
        )
        try:
            return await self.groq.evaluate(CRITICAL_EVALUATOR_SYSTEM_PROMPT, prompt)
        except GroqAPIError as e:
            logger.warning("Critical evaluator (CV) failed: %s", e)
            return _failed_review(e)
