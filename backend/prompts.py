"""LLM prompt templates for all Cvly modules."""

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
