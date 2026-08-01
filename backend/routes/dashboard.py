"""Dashboard route: pipeline summary stats and recent activity."""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import get_settings
from backend.state import app_state, get_translations, templates
from backend.utils.constants import GOOGLE_SHEETS_EDIT_URL, PIPELINE_TOTAL_STEPS

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_last_run(last_run_raw: str | None, lang: str) -> str | None:
    """Format an ISO datetime string for display in the given language."""
    if not last_run_raw:
        return None
    try:
        dt = datetime.fromisoformat(last_run_raw)
        if lang == "fr":
            return dt.strftime("%d/%m/%Y à %H:%M")
        return dt.strftime("%B %d, %Y at %H:%M")
    except ValueError:
        return last_run_raw


def _format_duration(duration: int) -> str:
    """Return a human-readable duration string from seconds."""
    if duration <= 0:
        return ""
    minutes, seconds = divmod(duration, 60)
    return f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"


@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request) -> HTMLResponse:
    t = get_translations()
    pipeline_results = app_state.get("pipeline_results", [])
    match_results = app_state.get("match_results", {})

    jobs_count = len(pipeline_results)
    scores = [mr.overall_score for mr in match_results.values()]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    settings = get_settings()
    above_threshold = sum(1 for s in scores if s >= settings.match_threshold)

    lang = app_state.get("language") or settings.default_language
    last_run_display = _format_last_run(app_state.get("last_run"), lang)
    pipeline_duration_str = _format_duration(app_state.get("pipeline_duration") or 0)

    logger.debug("Dashboard accessed. Showing %d jobs.", jobs_count)
    sheet_url = (
        GOOGLE_SHEETS_EDIT_URL.format(sheet_id=settings.google_sheet_id)
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
        "language": lang,
        "t": t,
        "step": app_state.get("pipeline_step", 0),
        "total": app_state.get("pipeline_total_steps", PIPELINE_TOTAL_STEPS),
        "step_label": "",
        "step_detail": app_state.get("pipeline_step_detail", ""),
        "active_page": "dashboard",
        "pipeline_status": app_state.get("pipeline_status", "idle"),
        "sheet_url": sheet_url,
    })
