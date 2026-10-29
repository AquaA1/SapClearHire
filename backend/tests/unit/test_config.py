import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_default_and_computed_uri():
    settings = Settings(
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_HOST="db.internal",
        POSTGRES_PORT=5433,
        POSTGRES_DB="test_clearhire",
        DATABASE_URL=None,
    )
    assert (
        "postgresql+asyncpg://test_user:test_password@db.internal:5433/test_clearhire"
        in settings.SQLALCHEMY_DATABASE_URI
    )
    assert settings.ENVIRONMENT in ["development", "staging", "production", "test"]


def test_settings_database_url_override():
    custom_uri = "sqlite+aiosqlite:////tmp/test.db"
    settings = Settings(DATABASE_URL=custom_uri)
    assert settings.SQLALCHEMY_DATABASE_URI == custom_uri


def test_settings_secret_key_validation():
    # Secret key shorter than 32 characters should fail validation
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="too_short_key")
