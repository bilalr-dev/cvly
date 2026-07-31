"""ATF recruiter-style analysis of resume/JD fit."""
from __future__ import annotations

from backend.models.match import ATFAnalysis
from backend.prompts import (
    ATF_SYSTEM_PROMPT,
    ATF_USER_PROMPT,
)
from backend.services.gemini_llm import GeminiLLMService


async def analyse_atf(
    resume_text: str,
    jd_text: str,
    gemini_service: GeminiLLMService,
    language: str = "fr"
) -> ATFAnalysis:

    lang_name = "French" if language == "fr" else "English"
    sys_prompt = ATF_SYSTEM_PROMPT.replace("{language}", lang_name)
    user_prompt = (ATF_USER_PROMPT
        .replace("{language}", lang_name)
        .replace("{raw_job_description}", jd_text)
        .replace("{raw_resume_text}", resume_text)
    )

    combined = f"{sys_prompt}\n\n{user_prompt}"

    res = await gemini_service.agenerate_json(
        combined,
        response_schema=ATFAnalysis,
        temperature=0.3
    )
    return res
