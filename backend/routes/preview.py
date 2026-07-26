from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.requests import Request

from backend.modules.sheets_tracker import SheetsTracker
from backend.state import app_state, templates

logger = logging.getLogger(__name__)

sheets_tracker = SheetsTracker("mock.json")

router = APIRouter(prefix="/preview")

def get_job_by_id(job_id: str) -> dict[str, Any] | None:
    """Retrieve job by ID from stored state."""
    jobs = app_state.get("pipeline_results", [])
    for job in jobs:
        if job.get("id") == job_id:
            return job
    return None

def generate_output_files() -> None:
    pass

def run_tailoring_module() -> None:
    pass

@router.get("/{job_id}", response_class=HTMLResponse)
async def preview_job(request: Request, job_id: str) -> HTMLResponse:
    job = get_job_by_id(job_id)
    if not job:
        logger.warning("Failed to load preview: Job %s not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info("Previewing job: %s", job_id)
    return templates.TemplateResponse(request=request, name="preview.html", context={
        "request": request,
        "job": job
    })

@router.post("/{job_id}/approve")
async def approve_job(job_id: str) -> RedirectResponse:
    job = get_job_by_id(job_id)
    if not job:
        logger.warning("Approval failed: Job %s not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info("Job approved: %s", job_id)
    sheets_tracker.append_job(job)
    generate_output_files()

    return RedirectResponse(url="/results", status_code=302)

@router.post("/{job_id}/regenerate")
async def regenerate_job(job_id: str) -> JSONResponse:
    job = get_job_by_id(job_id)
    if not job:
        logger.warning("Regeneration failed: Job %s not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")

    logger.info("Regenerating tailored output for job: %s", job_id)
    run_tailoring_module()
    return JSONResponse(content={"status": "success"})
