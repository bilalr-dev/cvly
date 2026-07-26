from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws")

@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        await websocket.send_json({"status": "connected"})
    except (WebSocketDisconnect, RuntimeError) as e:
        logger.error("WebSocket error: %s", e)
