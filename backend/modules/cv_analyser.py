from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any
import re
from datetime import datetime

from backend.models.match import MatchResult
from backend.services.gemini_embeddings import GeminiEmbeddingsService
from backend.services.gemini_llm import GeminiAPIError
from backend.utils.cosine import cosine_similarity

logger = logging.getLogger(__name__)

def _extract_year(date_str: Any) -> int:

    if not isinstance(date_str, str):
        return 0
    match = re.search(r'\d{4}', date_str)
    if match:
        return int(match.group(0))
    return 0

def calculate_years(entries: Any) -> float:

    if not isinstance(entries, list):
        return 0.0
    total = 0.0
    current_year = datetime.now().year
    for exp in entries:
        start_y = _extract_year(getattr(exp, "start_date", None))
        end_y = getattr(exp, "end_date", None)
        end_y = _extract_year(end_y) if isinstance(end_y, str) else current_year
        if start_y > 0 and end_y >= start_y:
            total += (end_y - start_y)
    return total

def compute_keyword_score(
    resume: Any,
    jd: Any,
    alias_map: Dict[str, List[str]]
) -> Tuple[List[str], List[str], float]:

    resume_skills = set()
    skills_obj = getattr(resume, "skills", None)
    if skills_obj:
        tech = getattr(skills_obj, "technical", [])
        tools = getattr(skills_obj, "tools", [])
        certs = getattr(skills_obj, "certifications", [])

        for lst in (tech, tools, certs):
            if isinstance(lst, list):
                for s in lst:
                    if isinstance(s, str):
                        resume_skills.add(s.lower())

    expanded_resume_skills = set(resume_skills)
    for canonical, aliases in alias_map.items():
        canonical = canonical.lower()
        aliases = [a.lower() for a in aliases if isinstance(a, str)]
        if canonical in resume_skills or any((a in resume_skills) for a in aliases):
            expanded_resume_skills.add(canonical)
            expanded_resume_skills.update(aliases)

    required_skills = set()
    req_skills = getattr(jd, "required_skills", [])
    req_tools = getattr(jd, "required_tools", [])
    req_certs = getattr(jd, "required_certifications", [])

    for lst in (req_skills, req_tools, req_certs):
        if isinstance(lst, list):
            for s in lst:
                if isinstance(s, str):
                    required_skills.add(s.lower())

    matched = []
    missing = []

    for req in required_skills:
        if req in expanded_resume_skills:
            matched.append(req)
        else:
            missing.append(req)

    if not required_skills:
        pct = 1.0
    else:
        pct = len(matched) / len(required_skills)

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
    contract_type: str | None
) -> float:

    score = 0.0
    if profile_type == "experienced":
        score = (keyword_pct * 0.4) + (semantic_score * 0.4) + (experience_score * 0.2)
    elif profile_type == "student_stage":
        score = (keyword_pct * 0.35) + (semantic_score * 0.4) + (experience_score * 0.05) + 0.2
    elif profile_type == "student_alternance":
        score = (keyword_pct * 0.35) + (semantic_score * 0.4) + (experience_score * 0.1) + 0.15

    return score * 100.0

async def analyse_cv(
    resume: Any,
    jd: Any,
    embeddings_service: GeminiEmbeddingsService,
    alias_map: Dict[str, List[str]]
) -> MatchResult:
    """Quantifies deterministic keyword extraction scoring rules against strict algorithmic profiles."""
    matched_k, missing_k, keyword_pct = compute_keyword_score(resume, jd, alias_map)

    resume_parts = []
    summary = getattr(resume, "summary", None)
    if isinstance(summary, str):
        resume_parts.append(summary)

    exps = getattr(resume, "experience", [])
    if isinstance(exps, list):
        for exp in exps:
            bullets = getattr(exp, "bullets", [])
            if isinstance(bullets, list):
                resume_parts.extend([b for b in bullets if isinstance(b, str)])

    resume_text = " ".join(resume_parts)

    jd_parts = []
    key_resp = getattr(jd, "key_responsibilities", [])
    if isinstance(key_resp, list):
        jd_parts.extend([r for r in key_resp if isinstance(r, str)])

    req_skills = getattr(jd, "required_skills", [])
    if isinstance(req_skills, list):
        jd_parts.extend([s for s in req_skills if isinstance(s, str)])

    jd_text = " ".join(jd_parts)

    try:
        r_embed = embeddings_service.embed_text(resume_text)
        j_embed = embeddings_service.embed_text(jd_text)
        sem_score = cosine_similarity(r_embed, j_embed)
    except (ValueError, TypeError, GeminiAPIError):
        sem_score = 0.0

    exp_score = compute_experience_score(resume, jd)

    profile_type = getattr(resume, "detected_profile", "experienced")
    if not isinstance(profile_type, str):
        profile_type = "experienced"

    contract_type = getattr(jd, "contract_type", None)

    overall = compute_match_score(keyword_pct, sem_score, exp_score, profile_type, contract_type)

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
