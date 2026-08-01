"""Pydantic models for search preferences."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.utils.constants import DEFAULT_MAX_RESULTS_PER_SOURCE

from .job import SupportedLanguage
from .match import SeniorityLevel


class RomeCodeLookupResult(BaseModel):
    """Gemini response schema for title → ROME code mapping."""

    rome_codes: list[str] = Field(default_factory=list)
    mapping: dict[str, str] = Field(default_factory=dict)


class SearchPreferences(BaseModel):
    model_config = ConfigDict(frozen=True)

    country: Literal["FR", "GB", "US", "other"] = "FR"
    exclude_keywords: list[str] = Field(default_factory=list)
    language: SupportedLanguage = "fr"
    location: str = ""
    max_results_per_source: int = DEFAULT_MAX_RESULTS_PER_SOURCE
    radius_km: int = Field(default=0, ge=0)
    remote_ok: bool = False
    seniority: SeniorityLevel | None = None
    titles: list[str] = Field(default_factory=list)
    contracts: list[str] = Field(default_factory=list)
    diploma_level: int | None = None
    rome_codes: list[str] = Field(default_factory=list)
