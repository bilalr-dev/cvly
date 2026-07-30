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

from backend.models import TailoredOutput
from backend.models.tailoring import KeywordAnalysisResult
from backend.prompts import BULLET_REWRITE_PROMPT, KEYWORD_ANALYSIS_PROMPT
from backend.services.gemini_llm import GeminiLLMService

logger = logging.getLogger(__name__)

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

    # Build CV content from experience bullets + academic projects
    cv_parts = []
    for exp in (getattr(resume, "experience", []) or []):
        for bullet in (getattr(exp, "bullets", []) or []):
            if isinstance(bullet, str):
                cv_parts.append(bullet)
    for proj in (getattr(resume, "academic_projects", []) or []):
        desc = getattr(proj, "description", "")
        if desc:
            cv_parts.append(str(desc))

    # Build skills list
    skills_parts = []
    skills_obj = getattr(resume, "skills", None)
    if skills_obj:
        for attr in ["technical", "tools", "certifications"]:
            for s in (getattr(skills_obj, attr, []) or []):
                if isinstance(s, str):
                    skills_parts.append(s)

    prompt = (KEYWORD_ANALYSIS_PROMPT
        .replace("{cv_content}", "\n".join(cv_parts) if cv_parts else "No experience bullets available.")
        .replace("{skills_list}", ", ".join(skills_parts) if skills_parts else "No skills listed.")
        .replace("{missing_keywords}", ", ".join(missing_keywords))
    )

    return gemini_service.generate_json(
        prompt=prompt,
        response_schema=KeywordAnalysisResult,
        temperature=0.0,  # deterministic classification restricts creativity
    )

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

    # filter validated keywords for rewrite prompt
    analysis_result = await analyse_keywords(
        resume=resume,
        missing_keywords=miss_keys,
        gemini_service=gemini_service,
    )
    validated_keywords = analysis_result.applicable

    # Stage 2: rewrite bullets with validated keywords only
    prompt = (BULLET_REWRITE_PROMPT
        .replace("{original_bullets}", " ".join(orig_bullets))
        .replace("{missing_keywords}", ", ".join(validated_keywords) if validated_keywords else "None: do not add any keywords not already present in the original bullets.")
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
        temperature=0.2  # prevents creative drift
    )
