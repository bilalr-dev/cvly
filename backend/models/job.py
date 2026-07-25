from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ContractType = Literal["CDD", "CDI", "alternance_apprentissage", "alternance_professionnalisation", "freelance", "stage"]
SupportedLanguage = Literal["en", "fr"]


class RawJobPosting(BaseModel):
    """Unprocessed job posting data extracted from a source."""
    model_config = ConfigDict(frozen=True)

    company: str
    description_text: str
    id: str
    location: str
    source: Literal["adzuna", "france_travail", "google_cse", "jsearch"]
    title: str
    url: str

    contract_type: Optional[ContractType] = None
    date_posted: Optional[str] = None
    salary_range: Optional[str] = None


class ParsedJobDescription(BaseModel):
    """Structured features extracted from a job description."""
    model_config = ConfigDict(frozen=True)

    contract_type: Optional[str] = None
    education_requirement: Optional[str] = None
    min_years_experience: Optional[int] = None

    ats_keywords: List[str] = Field(default_factory=list)
    company: str = ""
    job_id: str = ""
    key_responsibilities: List[str] = Field(default_factory=list)
    language_of_posting: SupportedLanguage = "fr"
    preferred_skills: List[str] = Field(default_factory=list)
    required_certifications: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    title: str = ""
