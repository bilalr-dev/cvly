"""Evaluator agent: generator-critic QA gate for tailored CV output.

Compares original resume bullets against rewritten versions to detect
fabricated content. Uses a separate LLM call as an independent critic.

Ref: Grounded Optimization Layer 5 (arXiv:2607.01457)
     Generator-critic architecture (Gou et al., ICLR 2024)
"""
from __future__ import annotations

import logging

from backend.config import get_settings
from backend.models.tailoring import EvaluatorVerdict
from backend.prompts import EVALUATOR_AGENT_PROMPT
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.utils.constants import PROMPT_NOT_PROVIDED, get_language_display_name

logger = logging.getLogger(__name__)


async def evaluate_tailored_output(
    original_bullets: list[str],
    rewritten_bullets: list[str],
    gemini_service: GeminiLLMService,
    job_description: str = "",
    language: str | None = None,
) -> EvaluatorVerdict:
    """Run the evaluator agent on rewritten bullets.

    Compares each rewritten bullet against its original to detect
    fabricated metrics, invented skills, JD attribution, and scope
    inflation. Uses temperature 0.0 for deterministic comparison.

    Args:
        original_bullets: The candidate's original CV bullets.
        rewritten_bullets: The tailored/rewritten bullets to verify.
        gemini_service: Gemini LLM service instance (same free-tier API).
        job_description: The target JD text (for jd_attribution detection).

    Returns:
        EvaluatorVerdict with is_acceptable flag and any violations found.

    """
    language = language or get_settings().default_language
    if not original_bullets or not rewritten_bullets:
        return EvaluatorVerdict(
            is_acceptable=True,
            violations=[],
            summary="No bullets to evaluate.",
        )

    # Format bullets for comparison
    orig_formatted = "\n".join(
        f"{i + 1}. {b}" for i, b in enumerate(original_bullets)
    )
    rewritten_formatted = "\n".join(
        f"{i + 1}. {b}" for i, b in enumerate(rewritten_bullets)
    )

    lang_name = get_language_display_name(language)
    prompt = (EVALUATOR_AGENT_PROMPT
        .replace("{original_bullets}", orig_formatted)
        .replace("{rewritten_bullets}", rewritten_formatted)
        .replace("{job_description}", job_description or PROMPT_NOT_PROVIDED)
        .replace("{language}", lang_name)
    )

    try:
        verdict = await gemini_service.agenerate_json(
            prompt=prompt,
            response_schema=EvaluatorVerdict,
            temperature=0.0,  # strict factual comparison
        )
        logger.debug(
            "Evaluator verdict: %s (%d violations found)",
            "ACCEPT" if verdict.is_acceptable else "REJECT",
            len(verdict.violations),
        )
        return verdict
    except GeminiAPIError as e:
        logger.warning("Evaluator agent failed: %s - defaulting to reject", e)
        # Default to reject on failure (fail-safe, per Grounded Optimization)
        return EvaluatorVerdict(
            is_acceptable=False,
            violations=[],
            summary=f"Evaluator agent failed: {e}. Defaulting to reject.",
        )
