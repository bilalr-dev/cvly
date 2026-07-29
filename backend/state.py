from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

from backend.utils.constants import TRANSLATIONS

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

_templates_dir = BASE_DIR / "frontend" / "templates"
_templates_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(_templates_dir))


import os  # noqa: E402
if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in os.environ.get("_", "").lower():
    import tempfile
    _STATE_DIR = Path(tempfile.gettempdir()) / "cvly_test_cache"
else:
    _STATE_DIR = Path(__file__).resolve().parent.parent / "cache"

_RESUME_FILE = _STATE_DIR / "resume_profile.json"
_PREFERENCES_FILE = _STATE_DIR / "preferences.json"


def save_resume_profile(profile: object) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _RESUME_FILE.write_text(
        json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_resume_profile() -> dict | None:
    if _RESUME_FILE.exists():
        return json.loads(_RESUME_FILE.read_text(encoding="utf-8"))
    return None


def delete_resume_profile() -> None:
    app_state["resume_profile"] = None
    if _RESUME_FILE.exists():
        _RESUME_FILE.unlink()


def save_preferences(prefs: dict) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _PREFERENCES_FILE.write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_preferences() -> dict | None:
    if _PREFERENCES_FILE.exists():
        return json.loads(_PREFERENCES_FILE.read_text(encoding="utf-8"))
    return None


app_state: dict[str, Any] = {
    "resume_profile": None,
    "preferences": None,
    "pipeline_results": [],
    "tailored_outputs": {},
    "match_results": {},
    "parsed_jds": {},
    "last_run": None,
    "language": "fr",
}

_saved_prefs = load_preferences()
if _saved_prefs:
    app_state["preferences"] = _saved_prefs

_saved_resume = load_resume_profile()
if _saved_resume:
    from backend.models.resume import ResumeProfile
    try:
        app_state["resume_profile"] = ResumeProfile.model_validate(_saved_resume)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to load resume profile: %s", e)


_PIPELINE_RESULTS_FILE = _STATE_DIR / "pipeline_results.json"
_MATCH_RESULTS_FILE = _STATE_DIR / "match_results.json"
_PARSED_JDS_FILE = _STATE_DIR / "parsed_jds.json"
_PIPELINE_META_FILE = _STATE_DIR / "pipeline_meta.json"

def save_pipeline_data() -> None:
    """Save pipeline results, match results, and parsed JDs to disk."""
    _STATE_DIR.mkdir(parents=True, exist_ok=True)

    postings = app_state.get("pipeline_results", [])
    _PIPELINE_RESULTS_FILE.write_text(
        json.dumps([p.model_dump() for p in postings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    matches = app_state.get("match_results", {})
    _MATCH_RESULTS_FILE.write_text(
        json.dumps({k: v.model_dump() for k, v in matches.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    jds = app_state.get("parsed_jds", {})
    _PARSED_JDS_FILE.write_text(
        json.dumps({k: v.model_dump() for k, v in jds.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = {
        "last_run": app_state.get("last_run"),
        "pipeline_status": app_state.get("pipeline_status", "idle"),
        "pipeline_duration": app_state.get("pipeline_duration"),
        "pipeline_error": app_state.get("pipeline_error")
    }
    _PIPELINE_META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_pipeline_data() -> None:
    """Load pipeline data from disk if it exists."""
    if _PIPELINE_RESULTS_FILE.exists():
        try:
            from backend.models.job import RawJobPosting
            raw = json.loads(_PIPELINE_RESULTS_FILE.read_text(encoding="utf-8"))
            app_state["pipeline_results"] = [RawJobPosting.model_validate(p) for p in raw]
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load pipeline results: %s", e)

    if _MATCH_RESULTS_FILE.exists():
        try:
            from backend.models.match import MatchResult
            raw = json.loads(_MATCH_RESULTS_FILE.read_text(encoding="utf-8"))
            app_state["match_results"] = {k: MatchResult.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load match results: %s", e)

    if _PARSED_JDS_FILE.exists():
        try:
            from backend.models.job import ParsedJobDescription
            raw = json.loads(_PARSED_JDS_FILE.read_text(encoding="utf-8"))
            app_state["parsed_jds"] = {k: ParsedJobDescription.model_validate(v) for k, v in raw.items()}
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load parsed JDs: %s", e)

    if _PIPELINE_META_FILE.exists():
        try:
            meta = json.loads(_PIPELINE_META_FILE.read_text(encoding="utf-8"))
            app_state["last_run"] = meta.get("last_run")
            status = meta.get("pipeline_status", "idle")
            app_state["pipeline_status"] = "complete" if status == "running" else status
            app_state["pipeline_duration"] = meta.get("pipeline_duration")
            app_state["pipeline_error"] = meta.get("pipeline_error")
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to load pipeline meta: %s", e)


load_pipeline_data()


def get_translations() -> dict[str, str]:
    lang = app_state.get("language", "fr")
    return TRANSLATIONS.get(lang, TRANSLATIONS["fr"])
