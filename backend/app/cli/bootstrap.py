"""
ClearHire First-Administrator Bootstrap Utility.

Provisions the initial EMPLOYER_ADMIN account safely from the command line without
exposing unrestricted public endpoints. Uses existing Argon2id password hashing,
validates tenant ownership / employer IDs, and records an immutable audit log.
"""

import argparse
import asyncio
import getpass
import os
import re
import sys

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import ConflictError, ValidationError
from app.core.logging import logger
from app.core.password import hash_password, validate_password_strength
from app.core.security import UserRole
from app.db.models.user import User
from app.db.session import get_session_factory
from app.repositories.audit import AuditEventRepository
from app.repositories.domain import UserRepository


def validate_employer_id(employer_id: str) -> str:
    r"""
    Validates that employer_id is a non-empty, sanitized alphanumeric slug or UUID string.
    Max 128 characters matching ^[a-zA-Z0-9_\-\.]+$
    """
    cleaned = employer_id.strip()
    if not cleaned:
        raise ValidationError("Employer ID cannot be empty or whitespace only.")
    if len(cleaned) > 128:
        raise ValidationError("Employer ID cannot exceed 128 characters.")
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", cleaned):
        raise ValidationError(
            "Employer ID must contain only alphanumeric characters, dashes, underscores, and dots."
        )
    return cleaned


def validate_email_format(email: str) -> str:
    """
    Validates email format using Pydantic EmailStr and normalizes to lowercase.
    """
    cleaned = email.strip()
    if not cleaned:
        raise ValidationError("Email cannot be empty.")
    try:
        validated = TypeAdapter(EmailStr).validate_python(cleaned)
        return str(validated).lower()
    except Exception as exc:
        raise ValidationError(f"Invalid email address '{cleaned}': {str(exc)}") from exc


async def bootstrap_employer_admin(
    email: str,
    full_name: str,
    employer_id: str,
    password: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> User:
    """
    Idempotently creates the first EMPLOYER_ADMIN account with Argon2id password hashing
    and logs an append-only audit event.
    """
    clean_email = validate_email_format(email)

    clean_name = full_name.strip()
    if not clean_name:
        raise ValidationError("Full name cannot be empty or whitespace only.")
    if len(clean_name) > 255:
        raise ValidationError("Full name cannot exceed 255 characters.")

    clean_employer_id = validate_employer_id(employer_id)

    # Validate and hash password using Argon2id
    validate_password_strength(password)
    hashed_password = hash_password(password)

    factory = session_factory or get_session_factory()
    async with factory() as session:
        user_repo = UserRepository(session)

        # Idempotency check: refuse to overwrite existing user
        existing_user = await user_repo.get_by_email(clean_email)
        if existing_user:
            raise ConflictError(
                f"An account with email '{clean_email}' already exists. Refusing to overwrite."
            )

        # Create user with EMPLOYER_ADMIN role and verified status
        user = await user_repo.create_user_with_credentials(
            email=clean_email,
            full_name=clean_name,
            password_hash=hashed_password,
            role=UserRole.EMPLOYER_ADMIN,
            employer_id=clean_employer_id,
            email_verified=True,
            is_active=True,
        )

        # Record immutable audit event
        audit_repo = AuditEventRepository(session)
        await audit_repo.log_event(
            action="ADMIN_BOOTSTRAPPED",
            resource_type="user",
            resource_id=str(user.id),
            actor_id=str(user.id),
            actor_role=UserRole.EMPLOYER_ADMIN.value,
            details={
                "email": user.email,
                "role": user.role.value,
                "employer_id": user.employer_id,
            },
        )

        await session.commit()
        await session.refresh(user)
        logger.info(
            "Bootstrapped EMPLOYER_ADMIN user %s for tenant %s",
            user.id,
            user.employer_id,
        )
        return user


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the initial ClearHire EMPLOYER_ADMIN user account.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Administrator email address.",
    )
    parser.add_argument(
        "--full-name",
        required=True,
        help="Administrator full name.",
    )
    parser.add_argument(
        "--employer-id",
        required=True,
        help="Tenant / employer identifier slug (alphanumeric, dashes, dots, underscores).",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Plain administrator password. If omitted, prompts securely or reads CLEARHIRE_BOOTSTRAP_PASSWORD.",
    )
    return parser.parse_args(args)


def resolve_password(cli_password: str | None) -> str:
    """
    Resolves password from CLI argument, environment variable, or secure interactive prompt.
    """
    if cli_password:
        return cli_password

    env_pw = os.environ.get("CLEARHIRE_BOOTSTRAP_PASSWORD")
    if env_pw:
        return env_pw

    if sys.stdin.isatty():
        pw1 = getpass.getpass("Enter administrator password: ")
        pw2 = getpass.getpass("Confirm administrator password: ")
        if pw1 != pw2:
            raise ValidationError("Passwords do not match.")
        return pw1

    raise ValidationError(
        "Password must be provided via --password, CLEARHIRE_BOOTSTRAP_PASSWORD environment variable, "
        "or an interactive terminal."
    )


async def async_main(args: list[str] | None = None) -> int:
    """
    Asynchronous execution logic for the bootstrap command.
    """
    parsed = parse_args(args)
    try:
        password = resolve_password(parsed.password)
        user = await bootstrap_employer_admin(
            email=parsed.email,
            full_name=parsed.full_name,
            employer_id=parsed.employer_id,
            password=password,
        )
        print("\n[SUCCESS] EMPLOYER_ADMIN account bootstrapped successfully:")
        print(f"  User ID:     {user.id}")
        print(f"  Email:       {user.email}")
        print(f"  Full Name:   {user.full_name}")
        print(f"  Role:        {user.role.value}")
        print(f"  Employer ID: {user.employer_id}")
        print(f"  Active:      {user.is_active}")
        print(f"  Verified:    {user.email_verified}\n")
        return 0
    except ConflictError as exc:
        sys.stderr.write(f"\n[IDEMPOTENCY ERROR] {exc.message}\n\n")
        return 1
    except ValidationError as exc:
        sys.stderr.write(f"\n[VALIDATION ERROR] {exc.message}\n\n")
        return 2
    except Exception as exc:
        sys.stderr.write(f"\n[UNEXPECTED ERROR] {str(exc)}\n\n")
        return 3


def main(args: list[str] | None = None) -> int:
    """
    Synchronous CLI entrypoint.
    """
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
