"""Settings page: resume upload and search preferences."""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from backend.config import get_settings as get_app_settings
from backend.modules.resume_parser import ResumeParser
from backend.services.gemini_llm import GeminiAPIError
from backend.state import (
    app_state,
    delete_resume_profile,
    get_translations,
    save_preferences,
    save_resume_profile,
    templates,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings")


@router.post("/language/{lang}")
async def set_language(lang: str) -> HTMLResponse:
    if lang not in ("fr", "en"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    app_state["language"] = lang
    return HTMLResponse(status_code=200, headers={"HX-Refresh": "true"})


def _build_resume_summary(profile: Any) -> dict:
    """Build a UI-friendly summary dictionary from a ResumeProfile."""
    profile_labels_fr = {
        "experienced": "Professionnel expérimenté",
        "student_stage": "Étudiant / Stage",
        "student_alternance": "Étudiant / Alternance",
    }
    profile_labels_en = {
        "experienced": "Experienced Professional",
        "student_stage": "Student / Internship",
        "student_alternance": "Student / Alternance",
    }

    lang = app_state.get("language", "fr")
    labels = profile_labels_fr if lang == "fr" else profile_labels_en

    skills_count = (
        len(profile.skills.technical)
        + len(profile.skills.soft)
        + len(profile.skills.tools)
        + len(profile.skills.certifications)
    )

    education_summary = ""
    if profile.education:
        edu = profile.education[0]
        education_summary = f"{edu.degree}, {edu.institution}"

    return {
        "name": profile.name,
        "profile_type": labels.get(profile.detected_profile, profile.detected_profile),
        "skills_count": skills_count,
        "experience_count": len(profile.experience),
        "education": education_summary,
    }


@router.get("", response_class=HTMLResponse)
async def get_settings(request: Request) -> HTMLResponse:
    logger.debug("Settings page accessed")

    resume_summary = None
    profile = app_state.get("resume_profile")
    if profile:
        resume_summary = _build_resume_summary(profile)

    return templates.TemplateResponse(request=request, name="settings.html", context={
        "request": request,
        "resume_profile": profile,
        "resume_summary": resume_summary,
        "preferences": app_state.get("preferences"),
        "language": app_state.get("language", "fr"),
        "t": get_translations(),
        "active_page": "settings",
    })


@router.post("/upload")
async def upload_resume(file: UploadFile, request: Request) -> Any:
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
        settings = get_app_settings()
        parser = ResumeParser(api_key=settings.gemini_api_key)
        profile = parser.parse_resume(str(temp_path))
        app_state["resume_profile"] = profile
        save_resume_profile(profile)
        logger.debug("Resume parsed successfully for %s", file.filename)

        resume_summary = _build_resume_summary(profile)

        return templates.TemplateResponse(
            request=request,
            name="partials/upload_success.html",
            context={
                "request": request,
                "resume_summary": resume_summary,
                "t": get_translations(),
            },
        )
    except GeminiAPIError as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            user_message = get_translations().get("error_rate_limit", "API rate limit reached. Please wait 30 seconds and try again.")
            html_msg = f'<div class="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800 flex items-center gap-2"><span>{user_message}</span></div>'
        else:
            user_message = get_translations().get("error_parsing", "Failed to parse resume. Please try again.")
            html_msg = f'<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800 flex items-center gap-2"><span>{user_message}</span></div>'

        logger.warning("Resume parsing failed: %s", error_msg)
        return HTMLResponse(
            content=html_msg,
            status_code=200,
        )
    finally:
        os.remove(temp_path)


@router.post("/upload/reset")
async def reset_resume(request: Request) -> HTMLResponse:
    delete_resume_profile()
    t = get_translations()
    return HTMLResponse(
        content=f'''
        <label id="upload-zone" class="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl p-9 cursor-pointer text-slate-500 hover:bg-slate-50 transition-colors">
            <input type="file" accept=".pdf,.docx"
                   hx-post="/settings/upload"
                   hx-target="#upload-feedback"
                   hx-swap="innerHTML"
                   hx-encoding="multipart/form-data"
                   name="file"
                   class="hidden"
                   onchange="document.getElementById('hidden-upload-btn').click();" />
            <div class="text-sm font-semibold text-slate-700">{t.get("drop_zone_title", "Drop your resume here")}</div>
            <div class="text-xs">{t.get("drop_zone_sub", "Accepts .pdf and .docx")}</div>
        </label>
        <form id="resume-form" class="hidden">
             <button id="hidden-upload-btn" type="submit" hx-post="/settings/upload" hx-encoding="multipart/form-data" hx-target="#upload-feedback" hx-swap="innerHTML" class="hidden"></button>
        </form>
        ''',
        status_code=200,
    )


@router.post("/preferences")
async def post_save_preferences(request: Request) -> Any:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        titles_raw = form.get("titles", "")
        titles = [t.strip() for t in titles_raw.split(",") if t.strip()] if titles_raw else []

        raw_radius = form.get("radius_km", "30")
        try:
            parsed_radius = max(0.0, float(str(raw_radius).replace(",", ".")))
        except ValueError:
            parsed_radius = 30.0

        data = {
            "titles": titles,
            "location": form.get("location", ""),
            "radius_km": parsed_radius,
            "remote_ok": form.get("remote_ok") == "on",
            "seniority": form.getlist("seniority"),
            "contract": form.getlist("contract"),
            "exclude_keywords": form.get("exclude_keywords", ""),
            "language": form.get("language", "fr"),
        }

    if "titles" not in data or not data["titles"]:
        logger.warning("Preferences save failed: Missing titles")
        raise HTTPException(status_code=400, detail="Missing required field: titles")

    app_state["preferences"] = data
    save_preferences(data)
    logger.debug("Preferences saved")

    t = get_translations()
    return HTMLResponse(
        content=f'<div class="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">✓ {t.get("prefs_saved", "Preferences saved")}</div>',
        status_code=200,
    )
