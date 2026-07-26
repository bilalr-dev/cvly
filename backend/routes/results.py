from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.state import app_state, templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results")

def get_session_state() -> dict[str, Any]:
    return {
        "pipeline_run": len(app_state.get("pipeline_results", [])) > 0,
        "jobs": app_state.get("pipeline_results", [])
    }

def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    jobs = app_state.get("pipeline_results", [])
    for job in jobs:
        if job.get("id") == job_id:
            return job
    return None

@router.get("", response_class=HTMLResponse)
async def get_results(request: Request) -> HTMLResponse:
    state = get_session_state()
    logger.info("Accessing results page")
    return templates.TemplateResponse(request=request, name="results.html", context={
        "request": request,
        "pipeline_run": state["pipeline_run"],
        "jobs": state.get("jobs", [])
    })

@router.get("/job/{job_id}", response_class=HTMLResponse)
async def get_job_partial(request: Request, job_id: str) -> HTMLResponse:
    job = get_job_by_id(job_id)
    if not job:
        logger.warning("Job details not found for ID: %s", job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info("Serving job detail partial for ID: %s", job_id)
    return templates.TemplateResponse(request=request, name="partials/job_detail.html", context={
        "request": request,
        "job": job
    })
