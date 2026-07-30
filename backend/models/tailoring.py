"""Pydantic models for CV tailoring outputs."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RewrittenBullet(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: str
    rewritten: str

    keywords_added: list[str] = Field(default_factory=list)


class RewrittenProjectBullet(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_name: str
    rewritten: str

    keywords_added: list[str] = Field(default_factory=list)


class KeywordClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    keyword: str
    applicable: bool
    evidence: str = ""


class KeywordAnalysisResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicable: list[str] = Field(default_factory=list)
    unfillable_gaps: list[str] = Field(default_factory=list)
    classifications: list[KeywordClassification] = Field(default_factory=list)


class EvaluatorViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    violation_type: Literal["fabricated_metric", "invented_skill", "jd_attribution", "scope_inflation", "other"]
    description: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    bullet_index: int = 0


class EvaluatorVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_acceptable: bool = True
    violations: list[EvaluatorViolation] = Field(default_factory=list)
    summary: str = ""


class TailoredOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    rewritten_experience_bullets: list[RewrittenBullet] = Field(default_factory=list)
    rewritten_project_bullets: list[RewrittenProjectBullet] = Field(default_factory=list)
    unfillable_gaps: list[str] = Field(default_factory=list)


class HallucinationWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_sentence: str
    severity: Literal["HIGH", "LOW", "MEDIUM"]
    term: str
