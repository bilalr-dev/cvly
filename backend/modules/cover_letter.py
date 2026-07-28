from __future__ import annotations

import logging
from typing import Any

from backend.prompts import COVER_LETTER_PROMPT
from backend.services.gemini_llm import GeminiLLMService

logger = logging.getLogger(__name__)

async def generate_cover_letter(
    resume: Any,
    jd: Any,
    match_result: Any,
    gemini_service: GeminiLLMService,
    language: str = "fr",
    country: str = "FR"
) -> str:

    summary = getattr(resume, "summary", "No summary provided")
    achievements = []

    exps = getattr(resume, "experience", [])
    if isinstance(exps, list):
        for exp in exps:
            metrics = getattr(exp, "metrics", [])
            if isinstance(metrics, list):
                achievements.extend([str(m) for m in metrics])

    academic = getattr(resume, "academic_projects", [])

    cur_edu = "N/A"
    alt_rhythm = "N/A"
    edu = getattr(resume, "education", [])
    if isinstance(edu, list):
        for e in edu:
            if getattr(e, "in_progress", False):
                cur_edu = str(e)
                if getattr(e, "alternance_rhythm", None):
                    alt_rhythm = str(e.alternance_rhythm)
                break

    jd_desc = []
    kr = getattr(jd, "key_responsibilities", [])
    rs = getattr(jd, "required_skills", [])
    if isinstance(kr, list):
        jd_desc.extend(kr)
    if isinstance(rs, list):
        jd_desc.extend(rs)

    strengths = []
    if getattr(match_result, "atf_analysis", None):
        match_info = getattr(match_result.atf_analysis, "match", None)
        if match_info:
            strengths = getattr(match_info, "strengths", [])

    prompt = (COVER_LETTER_PROMPT
        .replace("{profile_type}", str(getattr(resume, "detected_profile", "experienced")))
        .replace("{language}", language)
        .replace("{country}", country)
        .replace("{summary}", str(summary))
        .replace("{achievements}", " ".join(achievements))
        .replace("{academic_projects}", "N/A" if not academic else str(academic))
        .replace("{current_education}", cur_edu)
        .replace("{alternance_rhythm}", alt_rhythm)
        .replace("{job_description}", " ".join([str(j) for j in jd_desc]))
        .replace("{strengths}", "N/A" if not strengths else " ".join([str(s) for s in strengths]))
        .replace("{target_company}", str(getattr(jd, "company", "") or ""))
        .replace("{target_title}", str(getattr(jd, "title", "") or ""))
    )

    return gemini_service.generate_text(prompt, temperature=0.3)  # Reduced from 0.5 — prevents content fabrication in cover letters
