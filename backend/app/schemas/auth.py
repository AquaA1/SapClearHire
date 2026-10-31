"""
Authentication request and response schemas for ClearHire.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import UserRole


class CandidateRegisterRequest(BaseModel):
    """Public registration request strictly restricted to candidate role."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain text password (minimum 8 characters, maximum 128 characters)",
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Candidate's full name",
    )


class AdminUserProvisionRequest(BaseModel):
    """Administrative user provisioning request for privileged roles."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Initial temporary or permanent password",
    )
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name of user")
    role: UserRole = Field(
        ...,
        description="Assigned role: employer_admin, reviewer, or system_auditor",
    )
    employer_id: str | None = Field(
        default=None,
        description="Tenant / employer identifier required for employer_admin",
    )


class LoginRequest(BaseModel):
    """User login credential payload."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, description="Account password")


class TokenResponse(BaseModel):
    """Successful authentication token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")


class UserResponse(BaseModel):
    """Safe public representation of user profile (never exposes password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    employer_id: str | None = None
    is_active: bool
    email_verified: bool
    created_at: datetime
