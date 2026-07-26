from __future__ import annotations

import logging
from typing import List

from backend.models.job import RawJobPosting, ParsedJobDescription
from backend.services.gemini_llm import GeminiLLMService, GeminiAPIError
from backend.services.rate_limiter import AsyncRateLimiter
from backend.prompts import JD_PARSE_PROMPT

logger = logging.getLogger(__name__)

async def parse_job_description(
    description_text: str,
    job_id: str,
    gemini_service: GeminiLLMService
) -> ParsedJobDescription:

    prompt = JD_PARSE_PROMPT.format(description_text=description_text)
    res = gemini_service.generate_json(
        prompt,
        response_schema=ParsedJobDescription,
        temperature=0.0
    )
    return res.model_copy(update={"job_id": job_id})

async def parse_job_descriptions(
    postings: List[RawJobPosting],
    gemini_service: GeminiLLMService,
    rate_limiter: AsyncRateLimiter
) -> List[ParsedJobDescription]:
    results: List[ParsedJobDescription] = []

    for posting in postings:
        if not posting.description_text:
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
