"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key (required for agents)",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model for agent reasoning",
    )

    # Looker
    looker_base_url: str = Field(
        default="https://looker.example.com",
        description="Looker instance base URL",
    )
    looker_client_id: str = Field(
        default="",
        description="Looker API client ID",
    )
    looker_client_secret: str = Field(
        default="",
        description="Looker API client secret",
    )
    looker_verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates for Looker API",
    )

    # Redis (for local event queue)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # OpenTelemetry
    otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint (e.g., http://localhost:4317)",
    )
    jaeger_endpoint: str | None = Field(
        default="http://localhost:14268/api/traces",
        description="Jaeger collector endpoint for trace export",
    )
    service_name: str = Field(
        default="nl2sql-agent-pipeline",
        description="Service name for tracing",
    )
    trace_level: Literal["debug", "info", "warn", "error"] = Field(
        default="info",
        description="Logging/trace level",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
