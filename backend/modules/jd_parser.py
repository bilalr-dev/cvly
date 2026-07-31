"""Module 3: job description parsing via Gemini."""
from __future__ import annotations

import logging

from backend.models.job import ParsedJobDescription, RawJobPosting
from backend.prompts import JD_PARSE_PROMPT
from backend.services.gemini_llm import GeminiAPIError, GeminiLLMService
from backend.services.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)

async def parse_job_description(
    description_text: str,
    job_id: str,
    gemini_service: GeminiLLMService
) -> ParsedJobDescription:

    prompt = JD_PARSE_PROMPT.format(description_text=description_text)
    res = await gemini_service.agenerate_json(
        prompt,
        response_schema=ParsedJobDescription,
        temperature=0.0
    )
    return res.model_copy(update={"job_id": job_id})

async def parse_job_descriptions(
    postings: list[RawJobPosting],
    gemini_service: GeminiLLMService,
    rate_limiter: AsyncRateLimiter
) -> list[ParsedJobDescription]:
    results: list[ParsedJobDescription] = []

    for posting in postings:
        if not posting.description_text or len(posting.description_text) < 100:
            logger.warning("Skipping JD parse for %s: description too short", posting.id)
            continue

        await rate_limiter.acquire()
        try:
            parsed = await parse_job_description(
                description_text=posting.description_text,
                job_id=posting.id,
                gemini_service=gemini_service
            )
            results.append(parsed)
        except GeminiAPIError as e:
            logger.warning("Failed to parse JD for posting %s: %s", posting.id, e)

    return results
