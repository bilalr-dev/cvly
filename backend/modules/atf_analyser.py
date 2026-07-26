from __future__ import annotations

from backend.models.match import ATFAnalysis
from backend.services.gemini_llm import GeminiLLMService
from backend.prompts import (
    ATF_SYSTEM_PROMPT_FR,
    ATF_USER_PROMPT_FR,
    ATF_SYSTEM_PROMPT_EN,
    ATF_USER_PROMPT_EN
)

async def analyse_atf(
    resume_text: str,
    jd_text: str,
    gemini_service: GeminiLLMService,
    language: str = "fr"
) -> ATFAnalysis:

    if language == "en":
        sys_prompt = ATF_SYSTEM_PROMPT_EN.replace("{language}", language)
        user_prompt = ATF_USER_PROMPT_EN.replace(
            "{raw_job_description}", jd_text
        ).replace(
            "{raw_resume_text}", resume_text
        )
    else:
        sys_prompt = ATF_SYSTEM_PROMPT_FR.replace("{language}", language)
        user_prompt = ATF_USER_PROMPT_FR.replace(
            "{raw_job_description}", jd_text
        ).replace(
            "{raw_resume_text}", resume_text
        )

    combined = sys_prompt + "\n\n" + user_prompt

    res = gemini_service.generate_json(
        combined,
        response_schema=ATFAnalysis,
        temperature=0.3
    )
    return res
