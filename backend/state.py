from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent

_templates_dir = BASE_DIR / "frontend" / "templates"
_templates_dir.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(_templates_dir))

app_state: dict[str, Any] = {
    "resume_profile": None,
    "preferences": None,
    "pipeline_results": [],
    "tailored_outputs": {},
    "match_results": {},
    "parsed_jds": {},
    "last_run": None,
    "translations": {
        "fr": {
            "dashboard_title": "Tableau de Bord",
            "jobs_found": "Offres trouvées",
            "run_pipeline": "Lancer l'agent",
        },
        "en": {
            "dashboard_title": "Dashboard",
            "jobs_found": "Jobs Found",
            "run_pipeline": "Run Pipeline",
        },
    },
}
