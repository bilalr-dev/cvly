from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class RewrittenBullet(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: str
    rewritten: str

    keywords_added: List[str] = Field(default_factory=list)


class RewrittenProjectBullet(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_name: str
    rewritten: str

    keywords_added: List[str] = Field(default_factory=list)


class TailoredOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    rewritten_experience_bullets: List[RewrittenBullet] = Field(default_factory=list)
    rewritten_project_bullets: List[RewrittenProjectBullet] = Field(default_factory=list)
    unfillable_gaps: List[str] = Field(default_factory=list)


class HallucinationWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_sentence: str
    severity: Literal["HIGH", "LOW", "MEDIUM"]
    term: str
