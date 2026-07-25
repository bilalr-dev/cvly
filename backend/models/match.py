from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .resume import ProfileType

SeniorityLevel = Literal["alternant", "intermédiaire", "junior", "lead", "mid", "senior", "stagiaire"]


class ATFAnalysis(BaseModel):
    """Deep analysis of how well a candidate fits a job opening."""
    model_config = ConfigDict(frozen=True)

    seniority: SeniorityLevel

    achievements: List[str] = Field(default_factory=list)
    education: str = ""
    experience_years: int = 0
    profile_type: ProfileType = "experienced"
    recommendation: str = ""
    recruiter_score: float = Field(default=0, ge=0, le=10)
    relevant_academic_projects: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    summary: str = ""
    transferable_skills: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Overall matching result between a resume and a job."""
    model_config = ConfigDict(frozen=True)

    atf_analysis: Optional[ATFAnalysis] = None
    gap_analysis: Optional[str] = None

    experience_fit_score: float = 0.0
    job_id: str = ""
    keyword_match_pct: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    overall_score: float = Field(default=0, ge=0, le=100)
    semantic_score: float = 0.0
