"""Dashboard route: pipeline summary stats and recent activity."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import get_settings
from backend.state import app_state, get_translations, templates

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request) -> HTMLResponse:
    t = get_translations()
    pipeline_results = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})

    jobs_count = len(pipeline_results)
    scores = [mr.overall_score for mr in match_results.values()]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    above_threshold = sum(1 for s in scores if s >= 50)

    last_run_raw = app_state.get("last_run")
    if last_run_raw:
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(last_run_raw)
            lang = app_state.get("language", "fr")
            if lang == "fr":
                last_run_display = dt.strftime("%d/%m/%Y à %H:%M")
            else:
                last_run_display = dt.strftime("%B %d, %Y at %H:%M")
        except ValueError:
            last_run_display = last_run_raw
    else:
        last_run_display = None

    duration = app_state.get("pipeline_duration") or 0
    if duration > 0:
        minutes, seconds = divmod(duration, 60)
        pipeline_duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    else:
        pipeline_duration_str = ""

    logger.debug("Dashboard accessed. Showing %d jobs.", jobs_count)
    settings = get_settings()
    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{settings.google_sheet_id}/edit"
        if settings.google_sheet_id
        else None
    )
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "request": request,
        "last_run": last_run_display,
        "last_run_utc": app_state.get("last_run", ""),
        "pipeline_duration_str": pipeline_duration_str,
        "jobs_count": jobs_count,
        "avg_score": avg_score,
        "above_threshold": above_threshold,
        "language": app_state.get("language", "fr"),
        "t": t,
        "step": app_state.get("pipeline_step", 0),
        "total": app_state.get("pipeline_total_steps", 5),
        "step_label": "",
        "step_detail": app_state.get("pipeline_step_detail", ""),
        "active_page": "dashboard",
        "pipeline_status": app_state.get("pipeline_status", "idle"),
        "sheet_url": sheet_url,
    })
