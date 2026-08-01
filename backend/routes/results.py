"""Results page: scored job matches with filtering."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import get_settings
from backend.state import app_state, get_translations, templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results")

_RESPONSES_404 = {404: {"description": "Job not found"}}


def _build_atf_dict(atf: Any) -> dict[str, Any] | None:
    """Serialize an ATF analysis object for template consumption."""
    if not atf:
        return None
    return {
        "summary": getattr(atf, "summary", ""),
        "seniority": getattr(atf, "seniority", ""),
        "recommendation": getattr(atf, "recommendation", ""),
        "strengths": list(getattr(atf, "strengths", [])),
        "weaknesses": list(getattr(atf, "weaknesses", [])),
        "risks": list(getattr(atf, "risks", [])),
    }


def _resolve_matched_keywords(match: Any, atf: Any) -> list[str]:
    """Return matched keywords, falling back to ATF skills when the list is empty."""
    matched = list(getattr(match, "matched_keywords", [])) if match else []
    if not matched and atf and hasattr(atf, "skills"):
        return list(getattr(atf, "skills", []))
    return matched


def _build_job_dict(posting: Any, match: Any) -> dict[str, Any]:
    """Build the display dict for a single posting and its match result."""
    atf = getattr(match, "atf_analysis", None) if match else None
    return {
        "id": posting.id,
        "company": posting.company,
        "title": posting.title,
        "location": posting.location,
        "contract": getattr(posting, "contract_type", "") or "",
        "url": posting.url,
        "date_posted": getattr(posting, "date_posted", "") or "",
        "source": posting.source,
        "score": round(getattr(match, "overall_score", 0)) if match else 0,
        "has_atf": bool(atf),
        "description_text": posting.description_text,
        "matched_keywords": _resolve_matched_keywords(match, atf),
        "missing_keywords": list(getattr(match, "missing_keywords", [])) if match else [],
        "atf": _build_atf_dict(atf),
    }


def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    jobs = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})
    for posting in jobs:
        if posting.id != job_id:
            continue
        match = match_results.get(posting.id)
        return _build_job_dict(posting, match)
    return None

@router.get("", response_class=HTMLResponse)
async def get_results(request: Request) -> HTMLResponse:
    t = get_translations()
    postings = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})
    skipped = app_state.get("skipped_jobs", set())

    jobs_display = []
    for posting in postings:
        if posting.id in skipped:
            continue
        match = match_results.get(posting.id)
        jobs_display.append(_build_job_dict(posting, match))

    jobs_display.sort(key=lambda j: j["score"], reverse=True)

    logger.debug("Accessing results page")
    last_approved = app_state.pop("last_approved", None)
    return templates.TemplateResponse(request=request, name="results.html", context={
        "request": request,
        "pipeline_run": len(postings) > 0,
        "jobs": jobs_display,
        "last_approved": last_approved,
        "language": app_state.get("language") or get_settings().default_language,
        "t": t,
        "active_page": "results",
        "approved_jobs": app_state.get("approved_jobs", set())
    })

@router.post("/{job_id}/skip")
async def skip_job(request: Request, job_id: str) -> HTMLResponse:
    """Mark a job as skipped and remove its row from the results table."""
    skipped = app_state.setdefault("skipped_jobs", set())
    skipped.add(job_id)
    logger.debug("Skipped job %s", job_id)
    return HTMLResponse(content="", status_code=200)

@router.get("/job/{job_id}", response_class=HTMLResponse, responses=_RESPONSES_404)
async def get_job_partial(request: Request, job_id: str) -> HTMLResponse:
    job = get_job_by_id(job_id)
    if not job:
        logger.warning("Job details not found for ID: %s", job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.debug("Serving job detail partial for ID: %s", job_id)
    return templates.TemplateResponse(request=request, name="partials/job_detail.html", context={
        "request": request,
        "job": job,
        "language": app_state.get("language") or get_settings().default_language,
        "t": get_translations(),
        "approved_jobs": app_state.get("approved_jobs", set())
    })
