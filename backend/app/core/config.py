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
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "clearhire_db"
    POSTGRES_POOL_SIZE: int = 15
    POSTGRES_MAX_OVERFLOW: int = 25
    POSTGRES_POOL_RECYCLE: int = 300
    POSTGRES_POOL_TIMEOUT: int = 10

    # Optional explicit database URL override (e.g. for testing with sqlite)
    DATABASE_URL_OVERRIDE: str | None = Field(default=None, alias="DATABASE_URL")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:  # noqa: N802
        """Returns explicitly provided DATABASE_URL, SAP BTP VCAP_SERVICES URI, or constructs async PostgreSQL URI."""
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        # Auto-detect SAP BTP managed PostgreSQL binding if available
        try:
            from app.core.sap import get_sap_postgres_uri

            sap_uri = get_sap_postgres_uri()
            if sap_uri:
                return sap_uri
        except Exception:
            pass

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
    PASSWORD_MIN_LENGTH: int = 8

    # LLM Provider
    LLM_PROVIDER: Literal["fake", "openai", "anthropic", "gemini"] = "fake"
    LLM_API_KEY: str = "placeholder_api_key"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.0

    # Document OCR & Vision
    OCR_PROVIDER: Literal["auto", "vision_llm", "local", "disabled"] = "auto"

    # Storage & Uploads
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_DIR: str = "./storage"
    S3_BUCKET_NAME: str = "clearhire-documents"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION_NAME: str = "us-east-1"
    MAX_UPLOAD_SIZE_MB: int = 15
    MAX_PDF_PAGES: int = 30

    # Background Workers
    WORKER_BACKEND: Literal["local", "redis"] = "local"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    WORKER_CONCURRENCY: int = 2


@lru_cache
def get_settings() -> Settings:
    """Returns cached Settings instance."""
    return Settings()
