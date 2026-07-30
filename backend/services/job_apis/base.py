"""Base interface for job board API clients."""
from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models.job import RawJobPosting
from backend.models.preferences import SearchPreferences


class BaseJobAPIClient(ABC):

    @abstractmethod
    async def search(self, preferences: SearchPreferences) -> list[RawJobPosting]:
        pass
