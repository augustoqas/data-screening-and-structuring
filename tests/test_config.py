"""Tests for settings parsing: defaults, environment overrides and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from triage.config import Settings

ENV_VARS = [
    "OPENAI_API_KEY",
    "TRIAGE_OPENAI_API_KEY",
    "TRIAGE_MODEL",
    "TRIAGE_PROMPT_VERSION",
    "TRIAGE_REQUEST_TIMEOUT_S",
    "TRIAGE_TEMPERATURE",
    "TRIAGE_REASONING_EFFORT",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every test from the developer's real environment."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def load() -> Settings:
    """Build settings from the environment only, ignoring any local .env file."""
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_defaults() -> None:
    settings = load()
    assert settings.openai_api_key is None
    assert settings.prompt_version == "v1"
    assert settings.request_timeout_s == 30.0
    assert settings.temperature is None
    assert settings.reasoning_effort is None


def test_reads_standard_openai_key_and_hides_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    settings = load()
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "sk-secret"
    assert "sk-secret" not in repr(settings)  # never leaks into logs


def test_prefixed_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_MODEL", "gpt-other")
    monkeypatch.setenv("TRIAGE_REQUEST_TIMEOUT_S", "12.5")
    monkeypatch.setenv("TRIAGE_REASONING_EFFORT", "low")
    settings = load()
    assert settings.model == "gpt-other"
    assert settings.request_timeout_s == 12.5
    assert settings.reasoning_effort == "low"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TRIAGE_REQUEST_TIMEOUT_S", "0"),  # must be > 0
        ("TRIAGE_REQUEST_TIMEOUT_S", "abc"),  # not a number
        ("TRIAGE_TEMPERATURE", "3"),  # outside 0..2
        ("TRIAGE_REASONING_EFFORT", "extreme"),  # not an allowed value
    ],
)
def test_invalid_values_fail_fast(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        load()


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_api_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", value)
    assert load().openai_api_key is None
