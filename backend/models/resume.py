from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ProfileType = Literal["experienced", "student_alternance", "student_stage"]


class ResumeSkills(BaseModel):
    model_config = ConfigDict(frozen=True)

    certifications: List[str] = Field(default_factory=list)
    soft: List[str] = Field(default_factory=list)
    technical: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    company: str
    title: str
    type: Literal["alternance", "freelance", "fulltime", "internship", "other", "volunteer"]

    end_date: Optional[str] = None

    bullets: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    start_date: str = ""


class AcademicProject(BaseModel):
    model_config = ConfigDict(frozen=True)

    context: str
    description: str
    name: str

    metrics: List[Optional[str]] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    degree: str

    alternance_rhythm: Optional[str] = None
    end_date: Optional[str] = None
    start_date: Optional[str] = None
    year: Optional[int] = None

    field: str = ""
    in_progress: bool = False
    institution: str = ""
    school: str = ""


class Association(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    role: str

    description: Optional[str] = None


class ResumeProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    detected_profile: ProfileType
    skills: ResumeSkills

    alternance_rhythm: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None

    education: List[EducationEntry] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
