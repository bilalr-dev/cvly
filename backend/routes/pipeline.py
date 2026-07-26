from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.state import app_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline")

def get_session_state() -> dict[str, bool]:
    """Check if the session has required states."""
    return {
        "resume_loaded": app_state.get("resume_profile") is not None,
        "preferences_set": app_state.get("preferences") is not None
    }

def run_pipeline() -> None:
    """Mock pipeline worker trigger."""

@router.post("/run")
async def trigger_pipeline() -> JSONResponse:
    """Trigger the automated job discovery pipeline."""
    state = get_session_state()
    if not state.get("resume_loaded"):
        logger.warning("Pipeline trigger failed: No resume loaded")
        return JSONResponse(status_code=400, content={"error": "No resume loaded"})

    logger.info("Pipeline triggered successfully")
    run_pipeline()
    return JSONResponse(content={"status": "started"}, status_code=202)
