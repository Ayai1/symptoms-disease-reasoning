"""Environment-based configuration. All variables use the ``APP_`` prefix."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
SAFETY_DATA_DIR = PACKAGE_DIR / "safety" / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Comma-separated list in the environment, e.g.
    # APP_CORS_ORIGINS=https://example.vercel.app,http://localhost:3000
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    # Set to true only behind a proxy that overwrites X-Forwarded-For
    # (e.g. Hugging Face Spaces). Used for rate limiting, never logged.
    trust_forwarded_for: bool = False

    session_idle_ttl_seconds: int = Field(default=1800, gt=0)
    session_absolute_ttl_seconds: int = Field(default=7200, gt=0)
    max_sessions: int = Field(default=10_000, gt=0)

    max_body_bytes: int = Field(default=16_384, gt=0)
    rate_limit_turns_per_minute: int = Field(default=30, gt=0)
    rate_limit_sessions_per_minute: int = Field(default=5, gt=0)

    red_flag_rules_path: Path = SAFETY_DATA_DIR / "red_flags.yaml"
    medication_rules_path: Path = SAFETY_DATA_DIR / "medication_guard.yaml"
    emergency_resources_path: Path = SAFETY_DATA_DIR / "emergency_resources.yaml"

    # Salt for hashing session IDs in logs. Random per process by default,
    # so log hashes cannot be linked across restarts.
    log_salt: str = Field(default_factory=lambda: secrets.token_hex(16), repr=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard CORS origin is not allowed; list origins explicitly.")
        return value
