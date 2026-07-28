from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ProfileType = Literal["experienced", "student_alternance", "student_stage"]


class SoftSkill(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str | None = None


class ResumeSkills(BaseModel):
    model_config = ConfigDict(frozen=True)

    certifications: list[str] = Field(default_factory=list)
    soft: list[SoftSkill] = Field(default_factory=list)
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)

    @field_validator("soft", mode="before")
    @classmethod
    def coerce_soft_skills(cls, v: object) -> list:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"name": item, "description": None})
            elif isinstance(item, dict):
                result.append(item)
            else:
                result.append(item)
        return result

    @field_validator("certifications", "technical", "tools", mode="before")
    @classmethod
    def coerce_none_to_list(cls, v: object) -> list:
        if v is None:
            return []
        return v


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    company: str
    title: str
    type: Literal["alternance", "freelance", "fulltime", "internship", "other", "volunteer"]

    end_date: str | None = None

    bullets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    start_date: str = ""

    @field_validator("metrics", "bullets", mode="before")
    @classmethod
    def none_to_list(cls, v: object) -> list:
        if v is None:
            return []
        return v


class AcademicProject(BaseModel):
    model_config = ConfigDict(frozen=True)

    context: str
    description: str
    name: str

    metrics: list[str | None] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("metrics", "technologies", mode="before")
    @classmethod
    def none_to_list(cls, v: object) -> list:
        if v is None:
            return []
        return v


class EducationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    degree: str

    alternance_rhythm: str | None = None
    end_date: str | None = None
    start_date: str | None = None
    year: int | None = None

    field: str = ""
    in_progress: bool = False
    institution: str = ""
    school: str = ""


class Association(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    role: str

    description: str | None = None


class ResumeProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    detected_profile: ProfileType
    skills: ResumeSkills

    alternance_rhythm: str | None = None
    location: str | None = None
    name: str | None = None
    phone: str | None = None
    summary: str | None = None

    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    email: str | None = None
    linkedin: str | None = None
    portfolio: str | None = None
    languages: list[str] = Field(default_factory=list)
