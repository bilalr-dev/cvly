"""CV-JD matching: keyword scoring, embeddings, and MatchResult assembly."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.models.match import MatchResult
from backend.services.gemini_embeddings import GeminiEmbeddingsService
from backend.services.gemini_llm import GeminiAPIError
from backend.utils.cosine import cosine_similarity

logger = logging.getLogger(__name__)

def _extract_year(date_str: Any) -> int:

    if not isinstance(date_str, str):
        return 0
    match = re.search(r"\d{4}", date_str)
    if match:
        return int(match.group(0))
    return 0

def calculate_years(entries: Any) -> float:

    if not isinstance(entries, list):
        return 0.0
    total = 0.0
    current_year = datetime.now(tz=timezone.utc).year
    for exp in entries:
        start_y = _extract_year(getattr(exp, "start_date", None))
        end_y = getattr(exp, "end_date", None)
        end_y = _extract_year(end_y) if isinstance(end_y, str) else current_year
        if start_y > 0 and end_y >= start_y:
            total += (end_y - start_y)
    return total

def _strings_from_lists(*lists: Any) -> set[str]:
    """Collect lowercase strings from multiple attribute lists, skipping non-lists."""
    result: set[str] = set()
    for lst in lists:
        if isinstance(lst, list):
            for s in lst:
                if isinstance(s, str):
                    result.add(s.lower())
    return result


def _collect_resume_skills(resume: Any) -> set[str]:
    """Extract lowercase skill strings from technical/tools/certifications."""
    skills_obj = getattr(resume, "skills", None)
    if not skills_obj:
        return set()
    return _strings_from_lists(
        getattr(skills_obj, "technical", []),
        getattr(skills_obj, "tools", []),
        getattr(skills_obj, "certifications", []),
    )


def _expand_with_aliases(resume_skills: set[str], alias_map: dict[str, list[str]]) -> set[str]:
    """Expand a skill set by adding canonical and alias forms from alias_map."""
    expanded = set(resume_skills)
    for canonical, aliases in alias_map.items():
        canonical_lower = canonical.lower()
        aliases_lower = [a.lower() for a in aliases if isinstance(a, str)]
        if canonical_lower in resume_skills or any(a in resume_skills for a in aliases_lower):
            expanded.add(canonical_lower)
            expanded.update(aliases_lower)
    return expanded


def _collect_required_skills(jd: Any) -> set[str]:
    """Extract lowercase required skill strings from a parsed job description."""
    return _strings_from_lists(
        getattr(jd, "required_skills", []),
        getattr(jd, "required_tools", []),
        getattr(jd, "required_certifications", []),
    )


def compute_keyword_score(
    resume: Any,
    jd: Any,
    alias_map: dict[str, list[str]]
) -> tuple[list[str], list[str], float]:

    resume_skills = _collect_resume_skills(resume)
    expanded = _expand_with_aliases(resume_skills, alias_map)
    required = _collect_required_skills(jd)

    matched = [r for r in required if r in expanded]
    missing = [r for r in required if r not in expanded]
    pct = 1.0 if not required else len(matched) / len(required)

    return matched, missing, pct

def compute_experience_score(resume: Any, jd: Any) -> float:

    min_years = getattr(jd, "min_years_experience", None)
    if not isinstance(min_years, (int, float)):
        return 1.0

    exps = getattr(resume, "experience", [])
    if not isinstance(exps, list) or not exps:
        return 0.0

    calc_years = calculate_years(exps)

    if calc_years >= min_years:
        return 1.0

    if min_years == 0:
        return 1.0

    return min(1.0, calc_years / min_years)

def compute_match_score(
    keyword_pct: float,
    semantic_score: float,
    experience_score: float,
    profile_type: str,
    _contract_type: str | None
) -> float:

    score = 0.0
    if profile_type == "experienced":
        score = (keyword_pct * 0.4) + (semantic_score * 0.4) + (experience_score * 0.2)
    elif profile_type == "student_stage":
        score = (keyword_pct * 0.35) + (semantic_score * 0.4) + (experience_score * 0.05) + 0.2
    elif profile_type == "student_alternance":
        score = (keyword_pct * 0.35) + (semantic_score * 0.4) + (experience_score * 0.1) + 0.15

    return score * 100.0

def _build_resume_text(resume: Any) -> str:
    """Concatenate resume summary and all experience bullets into one string."""
    parts: list[str] = []
    summary = getattr(resume, "summary", None)
    if isinstance(summary, str):
        parts.append(summary)
    for exp in (getattr(resume, "experience", []) or []):
        bullets = getattr(exp, "bullets", [])
        if isinstance(bullets, list):
            parts.extend(b for b in bullets if isinstance(b, str))
    return " ".join(parts)


def _build_jd_text(jd: Any) -> str:
    """Concatenate key responsibilities and required skills into one string."""
    parts: list[str] = []
    for attr in ("key_responsibilities", "required_skills"):
        lst = getattr(jd, attr, [])
        if isinstance(lst, list):
            parts.extend(s for s in lst if isinstance(s, str))
    return " ".join(parts)


async def analyse_cv(
    resume: Any,
    jd: Any,
    embeddings_service: GeminiEmbeddingsService,
    alias_map: dict[str, list[str]]
) -> MatchResult:
    """Quantifies deterministic keyword extraction scoring rules against strict algorithmic profiles."""
    matched_k, missing_k, keyword_pct = compute_keyword_score(resume, jd, alias_map)

    resume_text = _build_resume_text(resume)
    jd_text = _build_jd_text(jd)

    try:
        r_embed, j_embed = await asyncio.gather(
            asyncio.to_thread(embeddings_service.embed_text, resume_text),
            asyncio.to_thread(embeddings_service.embed_text, jd_text),
        )
        sem_score = cosine_similarity(r_embed, j_embed)
    except (ValueError, TypeError, GeminiAPIError):
        sem_score = 0.0

    exp_score = compute_experience_score(resume, jd)

    profile_type = getattr(resume, "detected_profile", "experienced")
    if not isinstance(profile_type, str):
        profile_type = "experienced"

    overall = compute_match_score(keyword_pct, sem_score, exp_score, profile_type, getattr(jd, "contract_type", None))

    return MatchResult(
        atf_analysis=None,
        experience_fit_score=exp_score,
        job_id=getattr(jd, "job_id", "") if isinstance(getattr(jd, "job_id", ""), str) else "",
        keyword_match_pct=keyword_pct,
        matched_keywords=matched_k,
        missing_keywords=missing_k,
        overall_score=overall,
        semantic_score=sem_score
    )
