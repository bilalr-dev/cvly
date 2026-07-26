from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .job import SupportedLanguage
from .match import SeniorityLevel


class SearchPreferences(BaseModel):
    model_config = ConfigDict(frozen=True)

    country: Literal["FR", "GB", "US", "other"] = "FR"
    exclude_keywords: list[str] = Field(default_factory=list)
    language: SupportedLanguage = "fr"
    location: str = ""
    max_results_per_source: int = 20
    radius_km: int = Field(default=10, gt=0)
    remote_ok: bool = False
    seniority: SeniorityLevel = "junior"
    titles: list[str] = Field(default_factory=list)
