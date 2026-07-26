from __future__ import annotations

import logging
from typing import Any

from backend.models import TailoredOutput
from backend.prompts import BULLET_REWRITE_PROMPT
from backend.services.gemini_llm import GeminiLLMService

logger = logging.getLogger(__name__)

async def rewrite_bullets(
    resume: Any,
    jd: Any,
    match_result: Any,
    gemini_service: GeminiLLMService,
    language: str = "fr",
    country: str = "FR"
) -> TailoredOutput:
    orig_bullets = []
    exps = getattr(resume, "experience", [])
    if isinstance(exps, list):
        for exp in exps:
            bullets = getattr(exp, "bullets", [])
            if isinstance(bullets, list):
                orig_bullets.extend([b for b in bullets if isinstance(b, str)])

    miss_keys = getattr(match_result, "missing_keywords", [])
    if isinstance(miss_keys, list):
        miss_keys = [k for k in miss_keys if isinstance(k, str)]

    key_resp = getattr(jd, "key_responsibilities", [])
    if isinstance(key_resp, list):
        key_resp = [r for r in key_resp if isinstance(r, str)]

    weaknesses = []
    if getattr(match_result, "atf_analysis", None):
        match_info = getattr(match_result.atf_analysis, "match", None)
        if match_info:
            weaknesses = getattr(match_info, "weaknesses", [])
    if not isinstance(weaknesses, list):
        weaknesses = []

    academic = getattr(resume, "academic_projects", [])
    associations = getattr(resume, "associations_and_extracurriculars", [])

    alt_rhythm = "N/A"
    edu = getattr(resume, "education", [])
    if isinstance(edu, list):
        for e in edu:
            if getattr(e, "in_progress", False) and getattr(e, "alternance_rhythm", None):
                alt_rhythm = str(e.alternance_rhythm)
                break

    prompt = (BULLET_REWRITE_PROMPT
        .replace("{original_bullets}", " ".join(orig_bullets))
        .replace("{missing_keywords}", " ".join(miss_keys))
        .replace("{key_responsibilities}", " ".join(key_resp))
        .replace("{profile_type}", str(getattr(resume, "detected_profile", "experienced")))
        .replace("{language}", language)
        .replace("{country}", country)
        .replace("{academic_projects}", "N/A" if not academic else str(academic))
        .replace("{associations}", "N/A" if not associations else str(associations))
        .replace("{weaknesses}", "N/A" if not weaknesses else " ".join(weaknesses))
        .replace("{alternance_rhythm}", alt_rhythm)
    )

    return gemini_service.generate_json(
        prompt=prompt,
        response_schema=TailoredOutput,
        temperature=0.3
    )
