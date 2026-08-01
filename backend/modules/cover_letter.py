"""Module 5: cover letter generation."""
from __future__ import annotations

import logging
from typing import Any

from backend.config import get_settings
from backend.prompts import COVER_LETTER_PROMPT
from backend.services.gemini_llm import GeminiLLMService
from backend.utils.constants import COVER_LETTER_CONVENTIONS

logger = logging.getLogger(__name__)


def _collect_achievements(resume: Any) -> list[str]:
    """Return all metric strings from every experience entry."""
    achievements: list[str] = []
    exps = getattr(resume, "experience", [])
    if not isinstance(exps, list):
        return achievements
    for exp in exps:
        metrics = getattr(exp, "metrics", [])
        if isinstance(metrics, list):
            achievements.extend(str(m) for m in metrics)
    return achievements


def _extract_current_education(resume: Any) -> tuple[str, str]:
    """Return (current_education_str, alternance_rhythm) for the in-progress degree."""
    edu = getattr(resume, "education", [])
    if not isinstance(edu, list):
        return "N/A", "N/A"
    for e in edu:
        if getattr(e, "in_progress", False):
            rhythm = str(e.alternance_rhythm) if getattr(e, "alternance_rhythm", None) else "N/A"
            return str(e), rhythm
    return "N/A", "N/A"


def _build_jd_description(jd: Any) -> list[str]:
    """Combine key responsibilities and required skills into a single list."""
    items: list[str] = []
    kr = getattr(jd, "key_responsibilities", [])
    rs = getattr(jd, "required_skills", [])
    if isinstance(kr, list):
        items.extend(kr)
    if isinstance(rs, list):
        items.extend(rs)
    return items


def _extract_match_strengths(match_result: Any) -> list[str]:
    """Extract ATF strengths from a match result, defaulting to an empty list."""
    atf = getattr(match_result, "atf_analysis", None)
    if not atf:
        return []
    match_info = getattr(atf, "match", None)
    if not match_info:
        return []
    return getattr(match_info, "strengths", [])


async def generate_cover_letter(
    resume: Any,
    jd: Any,
    match_result: Any,
    gemini_service: GeminiLLMService,
    language: str | None = None,
    country: str | None = None
) -> str:
    settings = get_settings()
    language = language or settings.default_language
    country = country or settings.default_country

    summary = getattr(resume, "summary", "No summary provided")
    candidate_name = getattr(resume, "full_name", None) or getattr(resume, "name", None) or "N/A"
    achievements = _collect_achievements(resume)
    academic = getattr(resume, "academic_projects", [])
    cur_edu, alt_rhythm = _extract_current_education(resume)
    jd_desc = _build_jd_description(jd)
    strengths = _extract_match_strengths(match_result)
    conventions = COVER_LETTER_CONVENTIONS.get(language, COVER_LETTER_CONVENTIONS["en"])

    prompt = (COVER_LETTER_PROMPT
        .replace("{profile_type}", str(getattr(resume, "detected_profile", "experienced")))
        .replace("{language}", language)
        .replace("{language_conventions}", conventions)
        .replace("{country}", country)
        .replace("{summary}", str(summary))
        .replace("{achievements}", " ".join(achievements))
        .replace("{academic_projects}", "N/A" if not academic else str(academic))
        .replace("{current_education}", cur_edu)
        .replace("{alternance_rhythm}", alt_rhythm)
        .replace("{job_description}", " ".join(str(j) for j in jd_desc))
        .replace("{strengths}", "N/A" if not strengths else " ".join(str(s) for s in strengths))
        .replace("{target_company}", str(getattr(jd, "company", "") or ""))
        .replace("{target_title}", str(getattr(jd, "title", "") or ""))
        .replace("{candidate_name}", str(candidate_name))
    )

    return await gemini_service.agenerate_text(prompt, temperature=0.3)  # prevents content fabrication (reduced from 0.5)
