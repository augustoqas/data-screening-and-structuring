"""Tests for the pipeline's happy path and every failure path, using the fake client."""

from __future__ import annotations

from typing import Any

import pytest
from conftest import FakeLLMClient, valid_payload

from triage.llm import LLMError
from triage.pipeline import MAX_MESSAGE_CHARS, TriagePipeline
from triage.schemas import Status


def test_success_returns_normalised_result(payload: dict[str, Any]) -> None:
    client = FakeLLMClient(payload)
    outcome = TriagePipeline(client).run("pedido #48213 chegou quebrado")

    assert outcome.status is Status.SUCCESS
    assert outcome.result is not None
    assert outcome.result.order_ids == ["48213"]
    assert outcome.error is None
    assert (outcome.input_tokens, outcome.output_tokens) == (100, 50)
    assert outcome.prompt_version == "v1"


def test_message_is_wrapped_and_schema_sent() -> None:
    client = FakeLLMClient(valid_payload())
    TriagePipeline(client).run("  cadê meu pedido?  ")

    call = client.calls[0]
    system, user = call["messages"]
    assert system["role"] == "system"
    assert user["content"] == "<customer_message>\ncadê meu pedido?\n</customer_message>"
    assert call["name"] == "triage_result"
    assert call["schema"]["additionalProperties"] is False


def test_invalid_json_fails_and_keeps_raw_output() -> None:
    outcome = TriagePipeline(FakeLLMClient('{"category": ')).run("oi")
    assert outcome.status is Status.FAILED
    assert outcome.error is not None and outcome.error.startswith("validation_error")
    assert outcome.raw_output == '{"category": '
    assert outcome.input_tokens == 100  # a failed call still cost tokens


def test_schema_violation_reports_the_field() -> None:
    outcome = TriagePipeline(FakeLLMClient(valid_payload(priority="critical"))).run("oi")
    assert outcome.status is Status.FAILED
    assert outcome.error is not None and "priority" in outcome.error


def test_llm_error_becomes_failed_outcome() -> None:
    client = FakeLLMClient(LLMError("RateLimitError: slow down", latency_ms=800))
    outcome = TriagePipeline(client).run("oi")
    assert outcome.status is Status.FAILED
    assert outcome.error == "llm_error: RateLimitError: slow down"
    assert outcome.latency_ms == 800
    assert outcome.model == "fake-model"


@pytest.mark.parametrize("message", ["", "   \n "])
def test_blank_message_is_a_caller_error(message: str) -> None:
    with pytest.raises(ValueError):
        TriagePipeline(FakeLLMClient()).run(message)


def test_oversized_message_is_a_caller_error() -> None:
    with pytest.raises(ValueError):
        TriagePipeline(FakeLLMClient()).run("a" * (MAX_MESSAGE_CHARS + 1))


def test_unknown_prompt_version_fails_fast() -> None:
    with pytest.raises(FileNotFoundError):
        TriagePipeline(FakeLLMClient(), prompt_version="v999")
