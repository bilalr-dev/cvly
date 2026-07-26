from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes import dashboard, pipeline, preview, results, settings, ws

app = FastAPI(title="Cvly")

_static_dir = Path(__file__).resolve().parent.parent / "frontend" / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(pipeline.router)
app.include_router(results.router)
app.include_router(preview.router)
app.include_router(ws.router)
