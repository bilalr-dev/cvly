from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.state import app_state, templates

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard."""
    pipeline_results: list[dict[str, Any]] = app_state.get("pipeline_results", [])
    jobs_count = len(pipeline_results)
    avg_score = 0.0
    above_threshold = 0

    if jobs_count > 0:
        scores = [job.get("score", 0) for job in pipeline_results]
        avg_score = sum(scores) / jobs_count
        above_threshold = sum(1 for score in scores if score >= 80)

    logger.info("Dashboard accessed. Showing %d jobs.", jobs_count)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "request": request,
        "last_run": app_state.get("last_run"),
        "jobs_count": jobs_count,
        "avg_score": round(avg_score, 1),
        "above_threshold": above_threshold,
    })
