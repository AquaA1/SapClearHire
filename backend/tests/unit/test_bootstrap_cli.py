"""
Automated unit tests for the first-administrator bootstrap CLI and service.
"""

import os
import sys
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cli.bootstrap import (
    bootstrap_employer_admin,
    resolve_password,
    validate_email_format,
    validate_employer_id,
)
from app.core.exceptions import ConflictError, ValidationError
from app.core.password import verify_password
from app.core.security import UserRole
from app.db.models.audit import AuditEvent
from app.db.models.user import User


@pytest.mark.asyncio
async def test_bootstrap_employer_admin_success(test_engine):
    """Bootstrap successfully creates an EMPLOYER_ADMIN account with Argon2id password hash."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    admin_email = f"bootstrap_{uuid.uuid4().hex[:8]}@clearhire.internal"
    admin_name = "System Administrator"
    tenant_id = "tenant-clearhire-hq"
    raw_password = "SuperSecretAdminPass123!"

    user = await bootstrap_employer_admin(
        email=admin_email,
        full_name=admin_name,
        employer_id=tenant_id,
        password=raw_password,
        session_factory=session_factory,
    )

    assert user.id is not None
    assert user.email == admin_email.lower()
    assert user.full_name == admin_name
    assert user.role == UserRole.EMPLOYER_ADMIN
    assert user.employer_id == tenant_id
    assert user.is_active is True
    assert user.email_verified is True
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2id$")

    # Verify password verification succeeds with correct password
    assert verify_password(raw_password, user.password_hash) is True
    assert verify_password("WrongPassword123!", user.password_hash) is False

    # Verify database persistence and audit log creation
    async with session_factory() as session:
        db_user = await session.get(User, user.id)
        assert db_user is not None
        assert db_user.role == UserRole.EMPLOYER_ADMIN

        audit_query = select(AuditEvent).where(
            AuditEvent.action == "ADMIN_BOOTSTRAPPED",
            AuditEvent.resource_id == str(user.id),
        )
        audit_event = (await session.execute(audit_query)).scalar_one_or_none()
        assert audit_event is not None
        assert audit_event.actor_role == UserRole.EMPLOYER_ADMIN.value
        assert audit_event.details["employer_id"] == tenant_id


@pytest.mark.asyncio
async def test_bootstrap_idempotency_refuses_to_overwrite_existing_user(test_engine):
    """Repeated bootstrap attempt with an existing email raises ConflictError and does not alter account."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    admin_email = f"idempotent_{uuid.uuid4().hex[:8]}@clearhire.internal"

    # First bootstrap
    user1 = await bootstrap_employer_admin(
        email=admin_email,
        full_name="Original Admin",
        employer_id="tenant-alpha",
        password="FirstAdminPassword123!",
        session_factory=session_factory,
    )

    # Second bootstrap attempt with same email must fail
    with pytest.raises(ConflictError) as exc:
        await bootstrap_employer_admin(
            email=admin_email,
            full_name="Impostor Admin",
            employer_id="tenant-beta",
            password="SecondAdminPassword123!",
            session_factory=session_factory,
        )

    assert "already exists" in str(exc.value)
    assert "Refusing to overwrite" in str(exc.value)

    # Verify that the original user was NOT overwritten
    async with session_factory() as session:
        db_user = await session.get(User, user1.id)
        assert db_user is not None
        assert db_user.full_name == "Original Admin"
        assert db_user.employer_id == "tenant-alpha"
        assert verify_password("FirstAdminPassword123!", db_user.password_hash) is True


def test_validate_employer_id_valid_and_invalid():
    """Validates alphanumeric tenant slugs and rejects empty, excessive, or malicious values."""
    assert validate_employer_id("acme-corp") == "acme-corp"
    assert validate_employer_id("tenant_123.corp") == "tenant_123.corp"
    assert (
        validate_employer_id("550e8400-e29b-41d4-a716-446655440000")
        == "550e8400-e29b-41d4-a716-446655440000"
    )

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_employer_id("")

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_employer_id("   ")

    with pytest.raises(ValidationError, match="cannot exceed 128 characters"):
        validate_employer_id("a" * 129)

    with pytest.raises(ValidationError, match="alphanumeric"):
        validate_employer_id("acme/corp")

    with pytest.raises(ValidationError, match="alphanumeric"):
        validate_employer_id("acme; DROP TABLE users;")


def test_validate_email_format():
    """Validates email formatting and lowercases clean email."""
    assert validate_email_format("Admin@Company.COM") == "admin@company.com"

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_email_format("")

    with pytest.raises(ValidationError, match="Invalid email"):
        validate_email_format("invalid-email-string")


@pytest.mark.asyncio
async def test_bootstrap_weak_password_rejected(test_engine):
    """Passwords failing complexity/length requirements are rejected before database creation."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    with pytest.raises(ValidationError, match="at least 8 characters"):
        await bootstrap_employer_admin(
            email="admin@test.com",
            full_name="Admin",
            employer_id="tenant-1",
            password="short",
            session_factory=session_factory,
        )

    with pytest.raises(ValidationError, match="cannot be empty or whitespace"):
        await bootstrap_employer_admin(
            email="admin@test.com",
            full_name="Admin",
            employer_id="tenant-1",
            password="        ",
            session_factory=session_factory,
        )


def test_resolve_password_sources():
    """Resolves password from argument, environment variable, or raises if non-interactive."""
    # From CLI argument
    assert resolve_password("ArgPassword123!") == "ArgPassword123!"

    # From environment variable
    with patch.dict(os.environ, {"CLEARHIRE_BOOTSTRAP_PASSWORD": "EnvPassword123!"}):
        assert resolve_password(None) == "EnvPassword123!"

    # Non-interactive without env raises ValidationError
    with patch.dict(os.environ, {}, clear=True):
        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(ValidationError, match="Password must be provided via"):
                resolve_password(None)


@pytest.mark.asyncio
async def test_cli_async_main_entrypoint_exit_codes(test_engine):
    """Tests CLI async_main() entrypoint exit codes: 0 for success, 1 for conflict, 2 for validation error."""
    import app.db.session as session_module
    from app.cli.bootstrap import async_main

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    old_engine = session_module._engine
    old_sessionmaker = session_module._sessionmaker
    session_module._engine = test_engine
    session_module._sessionmaker = session_factory

    unique_email = f"cli_{uuid.uuid4().hex[:8]}@clearhire.internal"

    try:
        # 1. Success exit code 0
        code = await async_main(
            [
                "--email",
                unique_email,
                "--full-name",
                "CLI Admin",
                "--employer-id",
                "tenant-cli",
                "--password",
                "ValidAdminPass123!",
            ]
        )
        assert code == 0

        # 2. Duplicate exit code 1 (Idempotent conflict)
        code_dup = await async_main(
            [
                "--email",
                unique_email,
                "--full-name",
                "CLI Admin Duplicate",
                "--employer-id",
                "tenant-cli",
                "--password",
                "ValidAdminPass123!",
            ]
        )
        assert code_dup == 1

        # 3. Validation failure exit code 2 (Invalid employer-id)
        code_val = await async_main(
            [
                "--email",
                "another_admin@clearhire.internal",
                "--full-name",
                "CLI Admin",
                "--employer-id",
                "invalid id with spaces!",
                "--password",
                "ValidAdminPass123!",
            ]
        )
        assert code_val == 2

    finally:
        session_module._engine = old_engine
        session_module._sessionmaker = old_sessionmaker


def test_cli_subprocess_help_invocation():
    """Verify python -m app.cli.bootstrap --help executes in a real subprocess with exit code 0."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "app.cli.bootstrap", "--help"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    )
    assert result.returncode == 0
    assert "Bootstrap the initial ClearHire EMPLOYER_ADMIN" in result.stdout
    assert "--email" in result.stdout
    assert "--employer-id" in result.stdout
