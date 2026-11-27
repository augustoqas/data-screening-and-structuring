"""Tests for the command-line interface.

The real settings and OpenAI client are replaced: ``get_settings`` returns settings with
a dummy key, and ``OpenAIClient`` is swapped for a factory that hands out a
:class:`FakeLLMClient`. The CLI code itself runs unchanged.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest
from conftest import FakeLLMClient, valid_payload
from pydantic import SecretStr

from triage import cli
from triage.config import Settings
from triage.llm import LLMError


class FakeTTY(io.StringIO):
    """An interactive terminal with nothing piped in."""

    def isatty(self) -> bool:
        return True


@pytest.fixture
def fake_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch settings and the client factory; return what the CLI built, for inspection."""
    built: dict[str, Any] = {"script": [valid_payload()]}

    def make_client(model: str, **kwargs: Any) -> FakeLLMClient:
        built["model"] = model
        built["kwargs"] = kwargs
        return FakeLLMClient(*built["script"], model=model)

    settings = Settings(_env_file=None, openai_api_key=SecretStr("sk-test"), model="gpt-default")  # type: ignore[call-arg]
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "OpenAIClient", make_client)
    monkeypatch.setattr("sys.stdin", FakeTTY())
    return built


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def test_message_argument_prints_success_json(fake_env: dict[str, Any], capsys) -> None:
    code, out, _ = run(["pedido #48213 chegou quebrado"], capsys)
    outcome = json.loads(out)
    assert code == 0
    assert outcome["status"] == "success"
    assert outcome["result"]["order_ids"] == ["48213"]


def test_message_from_file(fake_env: dict[str, Any], capsys, tmp_path: Path) -> None:
    message = tmp_path / "mensagem.txt"
    message.write_text("cadê meu pedido?", encoding="utf-8")
    code, out, _ = run(["--file", str(message)], capsys)
    assert code == 0
    assert json.loads(out)["status"] == "success"


def test_message_from_stdin(fake_env: dict[str, Any], capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("cadê meu pedido?"))
    code, _, _ = run([], capsys)
    assert code == 0


def test_no_message_is_a_usage_error(fake_env: dict[str, Any], capsys) -> None:
    with pytest.raises(SystemExit, match="provide a message"):
        cli.main([])


def test_blank_message_exits_2(fake_env: dict[str, Any], capsys) -> None:
    code, out, err = run(["   "], capsys)
    assert code == 2
    assert out == ""
    assert "must not be empty" in err


def test_failed_outcome_exits_1(fake_env: dict[str, Any], capsys) -> None:
    fake_env["script"] = ['{"not": "valid"}']
    code, out, _ = run(["oi"], capsys)
    assert code == 1
    assert json.loads(out)["status"] == "failed"


def test_missing_api_key_exits_2(fake_env: dict[str, Any], capsys, monkeypatch) -> None:
    no_key = Settings(_env_file=None, openai_api_key=None)  # type: ignore[call-arg]
    monkeypatch.setattr(cli, "get_settings", lambda: no_key)
    code, out, err = run(["oi"], capsys)
    assert code == 2
    assert out == ""
    assert "OPENAI_API_KEY" in err


def test_overrides_are_applied(fake_env: dict[str, Any], capsys) -> None:
    code, out, _ = run(["oi", "--model", "gpt-other", "--prompt-version", "v1"], capsys)
    assert code == 0
    assert fake_env["model"] == "gpt-other"
    assert fake_env["kwargs"]["api_key"] == "sk-test"
    assert json.loads(out)["prompt_version"] == "v1"


def test_default_model_comes_from_settings(fake_env: dict[str, Any], capsys) -> None:
    run(["oi"], capsys)
    assert fake_env["model"] == "gpt-default"


def test_missing_file_exits_2(fake_env: dict[str, Any], capsys, tmp_path: Path) -> None:
    code, out, err = run(["--file", str(tmp_path / "nope.txt")], capsys)
    assert (code, out) == (2, "")
    assert err.startswith("error:")


def test_unknown_prompt_version_exits_2(fake_env: dict[str, Any], capsys) -> None:
    code, _, err = run(["oi", "--prompt-version", "v999"], capsys)
    assert code == 2
    assert "v999" in err


def test_invalid_configuration_exits_2(fake_env: dict[str, Any], capsys, monkeypatch) -> None:
    def broken_settings() -> Settings:
        return Settings(_env_file=None, request_timeout_s=0)  # type: ignore[call-arg]

    monkeypatch.setattr(cli, "get_settings", broken_settings)
    code, _, err = run(["oi"], capsys)
    assert code == 2
    assert "invalid configuration" in err


def test_client_creation_error_exits_2(fake_env: dict[str, Any], capsys, monkeypatch) -> None:
    def failing_client(model: str, **kwargs: Any) -> FakeLLMClient:
        raise LLMError("could not create OpenAI client: missing credentials")

    monkeypatch.setattr(cli, "OpenAIClient", failing_client)
    code, _, err = run(["oi"], capsys)
    assert code == 2
    assert "could not create OpenAI client" in err
