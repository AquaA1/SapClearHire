"""
ClearHire WebSocket Connection & Real-Time Event Hub.

Provides:
- Short-lived, single-use ticket generation and validation for secure WebSocket authentication.
- In-memory connection manager maintaining per-tab isolated active connections.
- Minimalist event envelope broadcasting for candidate-employer clarification workflows.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import secrets
import uuid
from typing import Any

from fastapi import WebSocket

from app.core.security import CurrentUser, UserRole

logger = logging.getLogger(__name__)


@dataclass
class WebSocketTicket:
    ticket: str
    user_id: str
    email: str
    role: UserRole
    employer_id: str | None
    created_at: datetime
    expires_at: datetime
    is_used: bool = False


class WebSocketConnectionManager:
    """
    Manages active WebSocket connections and short-lived tickets.
    Thread-safe and async-compatible within a single process.
    """

    def __init__(self, ticket_ttl_seconds: int = 60) -> None:
        self.ticket_ttl_seconds = ticket_ttl_seconds
        self._tickets: dict[str, WebSocketTicket] = {}
        # Map user_id -> set of active WebSockets (supports multiple browser tabs)
        self._user_connections: dict[str, set[WebSocket]] = {}
        # Map WebSocket -> CurrentUser
        self._socket_users: dict[WebSocket, CurrentUser] = {}

    def create_ticket(self, user: CurrentUser) -> tuple[str, datetime]:
        """
        Issues a cryptographically random, short-lived single-use ticket.
        Never exposes the user's long-lived JWT in WebSocket URLs.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.ticket_ttl_seconds)
        token_str = secrets.token_urlsafe(32)

        ticket = WebSocketTicket(
            ticket=token_str,
            user_id=user.id,
            email=user.email,
            role=user.role,
            employer_id=user.employer_id,
            created_at=now,
            expires_at=expires_at,
            is_used=False,
        )
        self._tickets[token_str] = ticket
        self._cleanup_expired_tickets()
        return token_str, expires_at

    def validate_and_consume_ticket(self, ticket_str: str) -> CurrentUser | None:
        """
        Validates the ticket. If valid, consumes it immediately (single-use)
        and returns the CurrentUser context. Rejects expired or reused tickets.
        """
        self._cleanup_expired_tickets()
        ticket = self._tickets.get(ticket_str)
        if not ticket:
            logger.warning("WebSocket ticket not found")
            return None

        if ticket.is_used:
            logger.warning("Attempted reuse of single-use WebSocket ticket")
            self._tickets.pop(ticket_str, None)
            return None

        now = datetime.now(UTC)
        if now > ticket.expires_at:
            logger.warning("WebSocket ticket has expired")
            self._tickets.pop(ticket_str, None)
            return None

        # Consume ticket immediately
        ticket.is_used = True
        self._tickets.pop(ticket_str, None)

        return CurrentUser(
            id=ticket.user_id,
            email=ticket.email,
            role=ticket.role,
            employer_id=ticket.employer_id,
            is_active=True,
        )

    def _cleanup_expired_tickets(self) -> None:
        """Purges expired tickets from memory."""
        now = datetime.now(UTC)
        expired = [t_str for t_str, t in self._tickets.items() if now > t.expires_at or t.is_used]
        for t_str in expired:
            self._tickets.pop(t_str, None)

    async def connect(self, websocket: WebSocket, user: CurrentUser) -> None:
        """Accepts and registers an authenticated WebSocket connection."""
        await websocket.accept()
        if user.id not in self._user_connections:
            self._user_connections[user.id] = set()
        self._user_connections[user.id].add(websocket)
        self._socket_users[websocket] = user
        logger.info(
            "WebSocket connected: user_id=%s role=%s active_tabs=%d",
            user.id,
            user.role.value,
            len(self._user_connections[user.id]),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Removes a disconnected WebSocket from the connection pool."""
        user = self._socket_users.pop(websocket, None)
        if user and user.id in self._user_connections:
            self._user_connections[user.id].discard(websocket)
            if not self._user_connections[user.id]:
                self._user_connections.pop(user.id, None)
            logger.info("WebSocket disconnected: user_id=%s", user.id)

    async def broadcast_to_user(self, user_id: str, envelope: dict[str, Any]) -> int:
        """Sends an event envelope to all active tabs belonging to a specific user."""
        sockets = self._user_connections.get(str(user_id), set()).copy()
        sent_count = 0
        for ws in sockets:
            try:
                await ws.send_json(envelope)
                sent_count += 1
            except Exception as exc:
                logger.warning("Failed to send message to user %s: %s", user_id, exc)
                self.disconnect(ws)
        return sent_count

    async def broadcast_to_users(self, user_ids: list[str], envelope: dict[str, Any]) -> int:
        """Sends an event envelope to multiple target users."""
        total_sent = 0
        for uid in set(user_ids):
            if uid:
                total_sent += await self.broadcast_to_user(str(uid), envelope)
        return total_sent

    async def broadcast_clarification_event(
        self,
        event: str,
        application_id: str | uuid.UUID,
        clarification_id: str | uuid.UUID | None,
        candidate_id: str | uuid.UUID,
        employer_ids: list[str | uuid.UUID],
    ) -> dict[str, Any]:
        """
        Creates a standardized event envelope and broadcasts to the candidate
        and authorized employer(s) associated with the application.
        """
        envelope = {
            "event_id": str(uuid.uuid4()),
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "application_id": str(application_id),
                "clarification_id": str(clarification_id) if clarification_id else None,
            },
        }

        target_users = [str(candidate_id)] + [str(eid) for eid in employer_ids if eid]
        delivered = await self.broadcast_to_users(target_users, envelope)
        logger.info(
            "Broadcasted %s for application %s to %d active connection(s)",
            event,
            application_id,
            delivered,
        )
        return envelope


# Global singleton instance
ws_manager = WebSocketConnectionManager()
