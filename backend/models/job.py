"""Pydantic models for raw and parsed job postings."""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.utils.constants import SUPPORTED_CONTRACT_TYPES, SUPPORTED_LANGUAGES

# Type aliases kept here as static Literal types for Pydantic/mypy compatibility.
# The canonical string values live in backend/utils/constants.py.
ContractType = Literal["CDD", "CDI", "alternance_apprentissage", "alternance_professionnalisation", "freelance", "stage"]
SupportedLanguage = Literal["en", "fr"]

if set(get_args(ContractType)) != set(SUPPORTED_CONTRACT_TYPES):
    raise RuntimeError("ContractType Literal and SUPPORTED_CONTRACT_TYPES are out of sync; update both together")
if set(get_args(SupportedLanguage)) != set(SUPPORTED_LANGUAGES):
    raise RuntimeError("SupportedLanguage Literal and SUPPORTED_LANGUAGES are out of sync; update both together")


class RawJobPosting(BaseModel):
    """Unprocessed job posting data extracted from a source."""
    model_config = ConfigDict(frozen=True)

    company: str
    description_text: str
    id: str
    location: str
    source: Literal["adzuna", "arbeitnow", "france_travail", "jobicy", "jsearch", "remotive"]
    title: str
    url: str

    contract_type: ContractType | None = None
    date_posted: str | None = None
    salary_range: str | None = None


class ParsedJobDescription(BaseModel):
    """Structured features extracted from a job description."""
    model_config = ConfigDict(frozen=True)

    contract_type: str | None = None
    education_requirement: str | None = None
    min_years_experience: int | None = None

    ats_keywords: list[str] = Field(default_factory=list)
    company: str = ""
    job_id: str = ""
    key_responsibilities: list[str] = Field(default_factory=list)
    language_of_posting: SupportedLanguage = "fr"
    preferred_skills: list[str] = Field(default_factory=list)
    required_certifications: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    title: str = ""

    @field_validator("job_id", "title", "company", mode="before")
    @classmethod
    def none_to_empty_str(cls, v: object) -> str:
        if v is None:
            return ""
        return v
