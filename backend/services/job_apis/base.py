from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.models.preferences import SearchPreferences
from backend.models.job import RawJobPosting

class BaseJobAPIClient(ABC):

    @abstractmethod
    async def search(self, preferences: SearchPreferences) -> List[RawJobPosting]:
        pass
