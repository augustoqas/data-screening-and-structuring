"""Runtime configuration, loaded from environment variables and an optional ``.env`` file.

``pydantic-settings`` reads each field from the environment (prefix ``TRIAGE_``), converts
it to the declared type and fails fast with a clear message if a value is invalid - so a
typo in ``TRIAGE_REQUEST_TIMEOUT_S`` is caught at startup, not mid-request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All tunable knobs of the pipeline. See ``.env.example`` for the variable names."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRIAGE_", extra="ignore")

    # The API key keeps the standard OpenAI variable name so existing setups just work.
    # SecretStr prevents it from showing up in logs or reprs by accident.
    openai_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "TRIAGE_OPENAI_API_KEY")
    )
    model: str = "gpt-5.4-mini"
    prompt_version: str = "v1"
    request_timeout_s: float = Field(default=30.0, gt=0)
    # Reasoning models reject a custom temperature, so it is only sent when set.
    temperature: float | None = Field(default=None, ge=0, le=2)
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once and cached."""
    return Settings()
