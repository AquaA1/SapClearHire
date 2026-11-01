"""
Integration tests for WebSocket authentication, connection lifecycle, and event broadcasting.
Verifies:
- Unauthenticated WebSocket rejection (no ticket)
- Single-use ticket enforcement (ticket cannot be reused)
- Expired ticket rejection
- Real-time event broadcasting to candidate and employer
"""

from datetime import UTC, datetime, timedelta
import uuid
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token, UserRole
from app.core.websocket import ws_manager
from app.main import create_application


@pytest.fixture
def app_client():
    app = create_application()
    return TestClient(app)


def test_websocket_rejects_without_ticket(app_client):
    """WebSocket connection without ticket must be rejected immediately."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect("/api/v1/ws"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_rejects_invalid_ticket(app_client):
    """WebSocket connection with random unissued ticket must be rejected."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect("/api/v1/ws?ticket=completely_invalid_random_ticket"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_single_use_ticket_enforcement(app_client):
    """WebSocket tickets must be strictly single-use; reuse attempts must be rejected."""
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, role=UserRole.CANDIDATE)
    
    # 1. Request ticket via authenticated REST endpoint
    res = app_client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    ticket = res.json()["ticket"]
    assert ticket is not None

    # 2. First connection succeeds
    with app_client.websocket_connect(f"/api/v1/ws?ticket={ticket}") as ws:
        ack = ws.receive_json()
        assert ack["event"] == "connection.acknowledged"
        assert ack["user_id"] == user_id
        
        ws.send_text("ping")
        assert ws.receive_text() == "pong"

    # 3. Second connection with same ticket must be rejected
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect(f"/api/v1/ws?ticket={ticket}"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_expired_ticket_rejection(app_client):
    """Expired tickets must be rejected."""
    user_id = str(uuid.uuid4())
    token = create_access_token(subject=user_id, role=UserRole.EMPLOYER_ADMIN)
    
    res = app_client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    ticket = res.json()["ticket"]

    # Manually backdate the ticket expiration in the manager
    if ticket in ws_manager._tickets:
        ws_manager._tickets[ticket].expires_at = datetime.now(UTC) - timedelta(seconds=10)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with app_client.websocket_connect(f"/api/v1/ws?ticket={ticket}"):
            pass
    assert exc_info.value.code == 4401


@pytest.mark.asyncio
async def test_websocket_event_broadcasting():
    """Verify event broadcasting delivers minimal payload to registered user sockets."""
    app = create_application()
    client = TestClient(app)

    cand_id = str(uuid.uuid4())
    emp_id = str(uuid.uuid4())
    app_id = str(uuid.uuid4())
    clar_id = str(uuid.uuid4())

    cand_token = create_access_token(subject=cand_id, role=UserRole.CANDIDATE)
    cand_ticket = client.post("/api/v1/auth/ws-ticket", headers={"Authorization": f"Bearer {cand_token}"}).json()["ticket"]

    with client.websocket_connect(f"/api/v1/ws?ticket={cand_ticket}") as cand_ws:
        ack = cand_ws.receive_json()
        assert ack["event"] == "connection.acknowledged"

        # Broadcast clarification.created event targeting cand_id
        envelope = await ws_manager.broadcast_clarification_event(
            event="clarification.created",
            application_id=app_id,
            clarification_id=clar_id,
            candidate_id=cand_id,
            employer_ids=[emp_id],
        )

        msg = cand_ws.receive_json()
        assert msg["event"] == "clarification.created"
        assert msg["data"]["application_id"] == app_id
        assert msg["data"]["clarification_id"] == clar_id
        assert "event_id" in msg
        assert "timestamp" in msg
