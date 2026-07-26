from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.modules import resume_parser
from backend.state import app_state, templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings")

@router.get("", response_class=HTMLResponse)
async def get_settings(request: Request) -> HTMLResponse:
    logger.info("Settings page accessed")
    return templates.TemplateResponse(request=request, name="settings.html", context={
        "request": request,
        "resume_profile": app_state.get("resume_profile"),
        "preferences": app_state.get("preferences")
    })

@router.post("/upload")
async def upload_resume(file: UploadFile) -> Any:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
        logger.warning("Invalid file type uploaded: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are supported")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:
        profile = resume_parser.parse_resume(temp_path)
        app_state["resume_profile"] = profile
        logger.info("Resume parsed successfully for %s", file.filename)
        return profile
    finally:
        os.remove(temp_path)

@router.post("/preferences")
async def save_preferences(request: Request) -> Any:
    data = await request.json()
    if "titles" not in data:
        logger.warning("Preferences save failed: Missing titles")
        raise HTTPException(status_code=400, detail="Missing required field: titles")

    app_state["preferences"] = data
    logger.info("Preferences saved")
    return {"status": "success"}
