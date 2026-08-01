"""Pydantic models for match scores and ATF analysis."""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from backend.utils.constants import SUPPORTED_SENIORITY_LEVELS

from .resume import ProfileType

# Type alias kept here as a static Literal for Pydantic/mypy compatibility.
# The canonical string values live in backend/utils/constants.py.
SeniorityLevel = Literal["alternant", "intermédiaire", "junior", "lead", "mid", "senior", "stagiaire"]

if set(get_args(SeniorityLevel)) != set(SUPPORTED_SENIORITY_LEVELS):
    raise RuntimeError("SeniorityLevel Literal and SUPPORTED_SENIORITY_LEVELS are out of sync; update both together")


class ATFAnalysis(BaseModel):
    """Deep analysis of how well a candidate fits a job opening."""
    model_config = ConfigDict(frozen=True)

    seniority: SeniorityLevel

    achievements: list[str] = Field(default_factory=list)
    education: str = ""
    experience_years: int = 0
    profile_type: ProfileType = "experienced"
    recommendation: str = ""
    recruiter_score: float = Field(default=0, ge=0, le=10)
    relevant_academic_projects: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    summary: str = ""
    transferable_skills: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    """Overall matching result between a resume and a job."""
    model_config = ConfigDict(frozen=True)

    atf_analysis: ATFAnalysis | None = None
    gap_analysis: str | None = None

    experience_fit_score: float = 0.0
    job_id: str = ""
    keyword_match_pct: float = 0.0
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    overall_score: float = Field(default=0, ge=0, le=100)
    semantic_score: float = 0.0
