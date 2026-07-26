from __future__ import annotations

import asyncio
import logging
from typing import List

from backend.models.preferences import SearchPreferences
from backend.models.job import RawJobPosting
from backend.services.job_apis.base import BaseJobAPIClient
from backend.services.rate_limiter import AsyncRateLimiter
from backend.utils.dedup import deduplicate_postings

logger = logging.getLogger(__name__)

class JobDiscovery:

    async def discover_jobs(
        self,
        preferences: SearchPreferences,
        api_clients: List[BaseJobAPIClient],
        rate_limiter: AsyncRateLimiter
    ) -> List[RawJobPosting]:
        tasks = [client.search(preferences) for client in api_clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        flat_results: List[RawJobPosting] = []
        for res in results:
            if isinstance(res, Exception):
                logger.warning("API client failed during job discovery: %s", res)
            else:
                flat_results.extend(res)

        deduped = deduplicate_postings(flat_results)

        deduped.sort(key=lambda p: (p.date_posted is not None, p.date_posted), reverse=True)

        return deduped
