"""CV bullet rewriting with two-stage keyword validation.

Stage 1 (analyse_keywords): Classifies missing keywords as applicable
or unfillable using LLM at temperature 0.0. No rewriting.
Stage 2 (rewrite_bullets): Rewrites bullets using only validated keywords
at temperature 0.2.

Ref: CoVe (Meta 2024), Grounded Optimization (arXiv:2607.01457)
"""
from __future__ import annotations

import logging
from typing import Any

from backend.config import get_settings
from backend.models import TailoredOutput
from backend.models.tailoring import KeywordAnalysisResult
from backend.prompts import BULLET_REWRITE_PROMPT, KEYWORD_ANALYSIS_PROMPT
from backend.services.gemini_llm import GeminiLLMService

logger = logging.getLogger(__name__)


def _collect_cv_bullets(resume: Any) -> list[str]:
    """Gather all experience bullets and project descriptions from a resume."""
    parts: list[str] = []
    for exp in (getattr(resume, "experience", []) or []):
        for bullet in (getattr(exp, "bullets", []) or []):
            if isinstance(bullet, str):
                parts.append(bullet)
    for proj in (getattr(resume, "academic_projects", []) or []):
        desc = getattr(proj, "description", "")
        if desc:
            parts.append(str(desc))
    return parts


def _collect_skills_text(resume: Any) -> list[str]:
    """Collect all string skills from technical/tools/certifications attributes."""
    parts: list[str] = []
    skills_obj = getattr(resume, "skills", None)
    if not skills_obj:
        return parts
    for attr in ("technical", "tools", "certifications"):
        for s in (getattr(skills_obj, attr, []) or []):
            if isinstance(s, str):
                parts.append(s)
    return parts


def _collect_bullets(resume: Any) -> list[str]:
    """Return all experience bullet strings from a resume."""
    bullets: list[str] = []
    exps = getattr(resume, "experience", [])
    if not isinstance(exps, list):
        return bullets
    for exp in exps:
        raw = getattr(exp, "bullets", [])
        if isinstance(raw, list):
            bullets.extend(b for b in raw if isinstance(b, str))
    return bullets


def _extract_alternance_rhythm(resume: Any) -> str:
    """Return the alternance rhythm of the current in-progress education, or 'N/A'."""
    edu = getattr(resume, "education", [])
    if not isinstance(edu, list):
        return "N/A"
    for e in edu:
        if getattr(e, "in_progress", False) and getattr(e, "alternance_rhythm", None):
            return str(e.alternance_rhythm)
    return "N/A"


def _extract_weaknesses(match_result: Any) -> list[str]:
    """Extract ATF weaknesses from a match result, defaulting to an empty list."""
    atf = getattr(match_result, "atf_analysis", None)
    if not atf:
        return []
    match_info = getattr(atf, "match", None)
    if not match_info:
        return []
    weaknesses = getattr(match_info, "weaknesses", [])
    return weaknesses if isinstance(weaknesses, list) else []


async def analyse_keywords(
    resume: Any,
    missing_keywords: list[str],
    gemini_service: GeminiLLMService,
) -> KeywordAnalysisResult:
    """Stage 1: Classify missing keywords as applicable or unfillable.

    Uses temperature 0.0 for deterministic classification.
    No rewriting: pure keyword-to-CV evidence matching.
    Ref: CoVe (Meta 2024), Grounded Optimization L4.
    """
    if not missing_keywords:
        return KeywordAnalysisResult(applicable=[], unfillable_gaps=[], classifications=[])

    cv_parts = _collect_cv_bullets(resume)
    skills_parts = _collect_skills_text(resume)

    prompt = (KEYWORD_ANALYSIS_PROMPT
        .replace("{cv_content}", "\n".join(cv_parts) if cv_parts else "No experience bullets available.")
        .replace("{skills_list}", ", ".join(skills_parts) if skills_parts else "No skills listed.")
        .replace("{missing_keywords}", ", ".join(missing_keywords))
    )

    return await gemini_service.agenerate_json(
        prompt=prompt,
        response_schema=KeywordAnalysisResult,
        temperature=0.0,  # deterministic classification restricts creativity
    )


async def rewrite_bullets(
    resume: Any,
    jd: Any,
    match_result: Any,
    gemini_service: GeminiLLMService,
    language: str | None = None,
    country: str | None = None
) -> TailoredOutput:
    settings = get_settings()
    language = language or settings.default_language
    country = country or settings.default_country

    orig_bullets = _collect_bullets(resume)

    miss_keys = getattr(match_result, "missing_keywords", [])
    miss_keys = [k for k in miss_keys if isinstance(k, str)] if isinstance(miss_keys, list) else []

    key_resp = getattr(jd, "key_responsibilities", [])
    key_resp = [r for r in key_resp if isinstance(r, str)] if isinstance(key_resp, list) else []

    weaknesses = _extract_weaknesses(match_result)
    alt_rhythm = _extract_alternance_rhythm(resume)

    academic = getattr(resume, "academic_projects", [])
    associations = getattr(resume, "associations_and_extracurriculars", [])

    # Stage 1: filter validated keywords before rewriting
    analysis_result = await analyse_keywords(
        resume=resume,
        missing_keywords=miss_keys,
        gemini_service=gemini_service,
    )
    validated_keywords = analysis_result.applicable

    # Stage 2: rewrite bullets with validated keywords only
    kw_placeholder = (
        ", ".join(validated_keywords)
        if validated_keywords
        else "None: do not add any keywords not already present in the original bullets."
    )
    prompt = (BULLET_REWRITE_PROMPT
        .replace("{original_bullets}", " ".join(orig_bullets))
        .replace("{missing_keywords}", kw_placeholder)
        .replace("{key_responsibilities}", " ".join(key_resp))
        .replace("{profile_type}", str(getattr(resume, "detected_profile", "experienced")))
        .replace("{language}", language)
        .replace("{country}", country)
        .replace("{academic_projects}", "N/A" if not academic else str(academic))
        .replace("{associations}", "N/A" if not associations else str(associations))
        .replace("{weaknesses}", "N/A" if not weaknesses else " ".join(weaknesses))
        .replace("{alternance_rhythm}", alt_rhythm)
    )

    return await gemini_service.agenerate_json(
        prompt=prompt,
        response_schema=TailoredOutput,
        temperature=0.2  # prevents creative drift
    )

