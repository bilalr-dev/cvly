"""LLM prompt templates for all Cvly modules."""
from __future__ import annotations

RESUME_PARSE_PROMPT: str = """Extract raw text and return JSON.
Preserve the original language.
Determine detected_profile classification logic.
Extract academic_projects.
Handle in-progress degree handling.
Extract associations.
Extract metrics.
Experience type classification.

{raw_text}
"""

JD_PARSE_PROMPT: str = """You are a job description parser. Extract all requirements and details from the following job posting into the exact JSON schema provided. Normalize skill names to their canonical English form (e.g., "React.js" → "React", "Gestion de projet" → "Project Management"). Keep the ats_keywords in the original language of the posting (these will be used for ATS matching). If a field is not present, use null or an empty array.

Job posting text:
{description_text}"""
