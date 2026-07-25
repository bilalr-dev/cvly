from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from .job import SupportedLanguage
from .match import SeniorityLevel


class SearchPreferences(BaseModel):
    """User preferences configured for automated job searches."""
    model_config = ConfigDict(frozen=True)

    country: Literal["FR", "GB", "US", "other"] = "FR"
    exclude_keywords: List[str] = Field(default_factory=list)
    language: SupportedLanguage = "fr"
    location: str = ""
    max_results_per_source: int = 20
    radius_km: int = Field(default=10, gt=0)
    remote_ok: bool = False
    seniority: SeniorityLevel = "junior"
    titles: List[str] = Field(default_factory=list)
