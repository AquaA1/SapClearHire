"""
Unit tests for Argon2id password hashing and validation.
"""

import pytest

from app.core.exceptions import ValidationError
from app.core.password import (
    dummy_verify,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_password_produces_argon2id_format():
    hashed = hash_password("SecurePassword123!")
    assert hashed.startswith("$argon2id$")
    assert len(hashed) > 50


def test_verify_password_success():
    pwd = "MyCorrectPassword2026!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True


def test_verify_password_mismatch():
    hashed = hash_password("RightPassword123")
    assert verify_password("WrongPassword123", hashed) is False


def test_verify_password_empty_or_none():
    assert verify_password("", "$argon2id$v=19$m=19456,t=2,p=1$fake$fake") is False
    assert verify_password("Password123", None) is False
    assert verify_password("Password123", "") is False


def test_verify_password_invalid_hash():
    assert verify_password("Password123", "not_a_valid_argon2_hash") is False


def test_validate_password_strength_valid():
    validate_password_strength("validpassword123")


def test_validate_password_strength_too_short():
    with pytest.raises(ValidationError) as exc:
        validate_password_strength("short")
    assert "at least 8 characters" in str(exc.value)


def test_validate_password_strength_too_long():
    with pytest.raises(ValidationError) as exc:
        validate_password_strength("a" * 129)
    assert "cannot exceed 128" in str(exc.value)


def test_validate_password_strength_whitespace_only():
    with pytest.raises(ValidationError) as exc:
        validate_password_strength("        ")
    assert "empty or whitespace" in str(exc.value)


def test_dummy_verify_executes_without_exception():
    dummy_verify()
