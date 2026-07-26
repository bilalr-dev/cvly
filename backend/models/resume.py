from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProfileType = Literal["experienced", "student_alternance", "student_stage"]


class ResumeSkills(BaseModel):
    model_config = ConfigDict(frozen=True)

    certifications: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    company: str
    title: str
    type: Literal["alternance", "freelance", "fulltime", "internship", "other", "volunteer"]

    end_date: str | None = None

    bullets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    start_date: str = ""


class AcademicProject(BaseModel):
    model_config = ConfigDict(frozen=True)

    context: str
    description: str
    name: str

    metrics: list[str | None] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


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
    phone: str | None = None
    summary: str | None = None

    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
