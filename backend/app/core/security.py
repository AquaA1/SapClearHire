from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError


class UserRole(str, Enum):
    """System roles defining permission boundaries."""

    CANDIDATE = "candidate"
    REVIEWER = "reviewer"
    EMPLOYER_ADMIN = "employer_admin"
    SYSTEM_AUDITOR = "system_auditor"


class CurrentUser(BaseModel):
    """Authenticated user context for the active request."""

    id: str
    email: str
    role: UserRole
    employer_id: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


# Standard HTTP Bearer scheme (auto_error=False to allow structured exception handling)
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    subject: str,
    role: UserRole,
    employer_id: str | None = None,
    email: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generates a cryptographically signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "employer_id": employer_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": "clearhire-auth",
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer="clearhire-auth",
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Access token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError("Invalid authentication token") from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency extracting the authenticated user.

    SECURITY NOTE & EXTENSION POINT:
    - Never trusts client-supplied headers (e.g. X-User-Role) for identity.
    - Decodes and verifies signed JWT tokens.
    - For Phase 1 foundation, unauthenticated requests raise HTTP 401.
    - In future phases, connect this interface to corporate identity providers
      (e.g., SAP Cloud Identity Services / SAML 2.0 / OIDC).
    """
    if credentials is None:
        raise AuthenticationError("Authentication credentials were not provided")

    payload = decode_access_token(credentials.credentials)

    user_id = payload.get("sub")
    role_str = payload.get("role")
    if not user_id or not role_str:
        raise AuthenticationError("Token payload missing subject or role claims")

    try:
        role = UserRole(role_str)
    except ValueError as e:
        raise AuthenticationError(f"Invalid role claim in token: {role_str}") from e

    return CurrentUser(
        id=user_id,
        email=payload.get("email", f"{user_id}@clearhire.internal"),
        role=role,
        employer_id=payload.get("employer_id"),
        is_active=True,
    )


def require_roles(*allowed_roles: UserRole):
    """Role-based authorization dependency factory."""

    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role.value}' is not authorized to access this resource"
            )
        return current_user

    return role_checker
