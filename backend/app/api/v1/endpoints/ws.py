"""
WebSocket connection endpoint for real-time live events.
Requires a valid short-lived ticket obtained via POST /api/v1/auth/ws-ticket.
"""

import logging
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.websocket import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Real-Time Sync"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: str | None = Query(default=None, description="Short-lived single-use auth ticket"),
) -> None:
    """
    Real-time synchronization WebSocket connection.
    Authenticates using a single-use ticket to prevent exposing JWTs in query parameters.
    """
    if not ticket:
        logger.warning("WebSocket connection attempted without ticket. Rejecting with 4401.")
        await websocket.close(code=4401, reason="Authentication ticket required")
        return

    user = ws_manager.validate_and_consume_ticket(ticket)
    if not user:
        logger.warning("Invalid, expired, or reused ticket. Rejecting with 4401.")
        await websocket.close(code=4401, reason="Invalid or expired ticket")
        return

    await ws_manager.connect(websocket, user)

    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "event": "connection.acknowledged",
            "user_id": user.id,
            "role": user.role.value,
        })

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.info("WebSocket connection ended: %s", exc)
        ws_manager.disconnect(websocket)
