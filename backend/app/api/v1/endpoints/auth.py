"""
Authentication endpoints for ClearHire.
Handles first-party candidate registration, credential login, administrative provisioning, and profile retrieval.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.core.password import dummy_verify, hash_password, verify_password
from app.core.security import (
    CurrentUser,
    UserRole,
    create_access_token,
    get_current_user,
    require_roles,
)
from app.db.session import get_db_session
from app.repositories.audit import AuditEventRepository
from app.repositories.domain import UserRepository
from app.schemas.auth import (
    AdminUserProvisionRequest,
    CandidateRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Candidate Account",
    description="Public candidate registration. Always assigns the candidate role.",
)
async def register_candidate(
    request: CandidateRegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    user_repo = UserRepository(db)
    normalized_email = user_repo.normalize_email(request.email)

    existing_user = await user_repo.get_by_email(normalized_email)
    if existing_user:
        raise ConflictError("An account with this email already exists")

    hashed_pw = hash_password(request.password)
    user = await user_repo.create_user_with_credentials(
        email=normalized_email,
        full_name=request.full_name,
        password_hash=hashed_pw,
        role=UserRole.CANDIDATE,
        employer_id=None,
        email_verified=False,
        is_active=True,
    )

    audit_repo = AuditEventRepository(db)
    await audit_repo.log_event(
        action="USER_REGISTERED",
        resource_type="user",
        resource_id=str(user.id),
        actor_id=str(user.id),
        actor_role=UserRole.CANDIDATE.value,
        details={"email": normalized_email, "role": UserRole.CANDIDATE.value},
    )
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/provision",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision Privileged User Account",
    description=(
        "Administrative provisioning for employer_admin, reviewer, or system_auditor accounts. "
        "Requires EMPLOYER_ADMIN or SYSTEM_AUDITOR role."
    ),
)
async def provision_user(
    request: AdminUserProvisionRequest,
    current_user: CurrentUser = Depends(
        require_roles(UserRole.EMPLOYER_ADMIN, UserRole.SYSTEM_AUDITOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    # Employer admins can only provision reviewers or employer_admins within their own tenant
    if current_user.role == UserRole.EMPLOYER_ADMIN:
        if request.role == UserRole.SYSTEM_AUDITOR:
            raise AuthorizationError("Employer admins cannot provision system auditor accounts")
        target_employer_id = current_user.employer_id or str(current_user.id)
        if request.employer_id and request.employer_id != target_employer_id:
            raise AuthorizationError("Cannot provision user for a different employer tenant")
        assigned_employer_id = target_employer_id
    else:
        assigned_employer_id = request.employer_id

    user_repo = UserRepository(db)
    normalized_email = user_repo.normalize_email(request.email)

    existing_user = await user_repo.get_by_email(normalized_email)
    if existing_user:
        raise ConflictError("An account with this email already exists")

    hashed_pw = hash_password(request.password)
    user = await user_repo.create_user_with_credentials(
        email=normalized_email,
        full_name=request.full_name,
        password_hash=hashed_pw,
        role=request.role,
        employer_id=assigned_employer_id,
        email_verified=True,
        is_active=True,
    )

    audit_repo = AuditEventRepository(db)
    await audit_repo.log_event(
        action="USER_PROVISIONED",
        resource_type="user",
        resource_id=str(user.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        details={
            "email": normalized_email,
            "role": request.role.value,
            "employer_id": assigned_employer_id,
        },
    )
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate User and Issue JWT",
    description="Validates email and Argon2id password hash, returning a signed JWT access token.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    user_repo = UserRepository(db)
    normalized_email = user_repo.normalize_email(request.email)
    user = await user_repo.get_by_email(normalized_email)

    # Timing-safe failure path for non-existent account or missing password hash
    if not user or not user.password_hash:
        dummy_verify()
        raise AuthenticationError("Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is inactive")

    settings = get_settings()
    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        employer_id=user.employer_id,
        email=user.email,
    )

    audit_repo = AuditEventRepository(db)
    await audit_repo.log_event(
        action="USER_LOGGED_IN",
        resource_type="user",
        resource_id=str(user.id),
        actor_id=str(user.id),
        actor_role=user.role.value,
        details={"email": user.email},
    )
    await db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Authenticated User Profile",
    description="Retrieves the current authenticated user's profile context.",
)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    try:
        user_uuid = uuid.UUID(current_user.id)
    except ValueError as e:
        raise AuthenticationError("Malformed user ID in token subject") from e

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_uuid)
    if not user:
        raise NotFoundError(f"User account {current_user.id} not found")

    return UserResponse.model_validate(user)
