"""
Argon2id password hashing and constant-time verification utilities.
Adheres to OWASP recommendations for secure credential storage.
"""

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.exceptions import ValidationError

# OWASP Recommended Parameters for Argon2id
# time_cost: 2 iterations
# memory_cost: 19456 KiB (~19 MiB)
# parallelism: 1 thread
# hash_len: 32 bytes
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    type=Type.ID,
)

# Precomputed dummy hash for timing-attack mitigation when a user is not found
_DUMMY_HASH = _hasher.hash("clearhire_dummy_timing_protection_value")


def validate_password_strength(password: str) -> None:
    """
    Validates password length and basic security requirements.
    Rejects empty, whitespace-only, excessively short, or excessively long passwords.
    """
    settings = get_settings()
    min_length = getattr(settings, "PASSWORD_MIN_LENGTH", 8)
    max_length = 128

    if not password or not password.strip():
        raise ValidationError("Password cannot be empty or whitespace only")

    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long")

    if len(password) > max_length:
        raise ValidationError(f"Password cannot exceed {max_length} characters")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain text password using Argon2id after validating strength requirements.
    """
    validate_password_strength(plain_password)
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """
    Verifies a plain password against an Argon2id hash in constant time.
    Returns False if hash is missing, invalid, or does not match.
    """
    if not hashed_password or not plain_password:
        return False

    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_verify() -> None:
    """
    Executes a dummy verification cycle against a precomputed Argon2id hash.
    Ensures execution timing remains indistinguishable when authenticating non-existent accounts.
    """
    try:
        _hasher.verify(_DUMMY_HASH, "incorrect_dummy_guess")
    except Exception:
        pass
