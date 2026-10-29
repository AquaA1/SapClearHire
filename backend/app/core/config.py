from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated via pydantic-settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application info
    PROJECT_NAME: str = "ClearHire API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False

    # Server binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL configuration
    POSTGRES_USER: str = "clearhire_user"
    POSTGRES_PASSWORD: str = "clearhire_secure_dev_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "clearhire_db"

    # Optional explicit database URL override (e.g. for testing with sqlite)
    DATABASE_URL_OVERRIDE: str | None = Field(default=None, alias="DATABASE_URL")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:  # noqa: N802
        """Returns explicitly provided DATABASE_URL or constructs async PostgreSQL URI."""
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="dev_secret_key_change_in_production_min_32_characters_long",
        min_length=32,
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # LLM Provider
    LLM_PROVIDER: Literal["fake", "openai", "anthropic", "gemini"] = "fake"
    LLM_API_KEY: str = "placeholder_api_key"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.0

    # Storage & Uploads
    STORAGE_LOCAL_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 15

    # Background Workers
    WORKER_CONCURRENCY: int = 2


@lru_cache
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()
