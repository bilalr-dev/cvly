from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ContractType = Literal["CDD", "CDI", "alternance_apprentissage", "alternance_professionnalisation", "freelance", "stage"]
SupportedLanguage = Literal["en", "fr"]


class RawJobPosting(BaseModel):
    """Unprocessed job posting data extracted from a source."""
    model_config = ConfigDict(frozen=True)

    company: str
    description_text: str
    id: str
    location: str
    source: Literal["adzuna", "arbeitnow", "france_travail", "google_cse", "jsearch", "remotive"]
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
