"""Tests for OpenAIClient, with the OpenAI SDK replaced by a stub.

The stub records the keyword arguments of each ``chat.completions.create`` call and
returns a real ``ChatCompletion`` object (or raises), so the tests check both what we
send to the API and how we interpret what comes back, without any network access.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import openai
import pytest
from openai.types.chat import ChatCompletion

from triage.llm import LLMError, OpenAIClient

MESSAGES = [{"role": "user", "content": "oi"}]
SCHEMA = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


def make_completion(
    content: str | None = '{"ok": true}',
    *,
    refusal: str | None = None,
    finish_reason: str = "stop",
    usage: dict[str, int] | None = None,
) -> ChatCompletion:
    """Build a real ChatCompletion, as the SDK would return it."""
    if usage is None:
        usage = {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-test-2026-01-01",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish_reason,
                    "logprobs": None,
                    "message": {"role": "assistant", "content": content, "refusal": refusal},
                }
            ],
            "usage": usage or None,
        }
    )


class StubCompletions:
    """Stands in for ``client.chat.completions``."""

    def __init__(self, outcome: ChatCompletion | Exception) -> None:
        self.outcome = outcome
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> ChatCompletion:
        self.kwargs = kwargs
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def client_with(
    outcome: ChatCompletion | Exception, **options: Any
) -> tuple[OpenAIClient, StubCompletions]:
    """An OpenAIClient whose SDK calls go to a stub instead of the network."""
    client = OpenAIClient("gpt-test", api_key="sk-test", **options)
    stub = StubCompletions(outcome)
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=stub))  # type: ignore[assignment]
    return client, stub


def test_successful_call_returns_content_and_usage() -> None:
    client, _ = client_with(make_completion('{"category": "refund_issue"}'))
    response = client.complete(MESSAGES, SCHEMA, "triage_result")

    assert response.content == '{"category": "refund_issue"}'
    assert response.model == "gpt-test-2026-01-01"  # the exact model version the API used
    assert (response.input_tokens, response.output_tokens) == (120, 30)
    assert response.latency_ms >= 0


def test_request_uses_strict_structured_outputs() -> None:
    client, stub = client_with(make_completion())
    client.complete(MESSAGES, SCHEMA, "triage_result")

    assert stub.kwargs["model"] == "gpt-test"
    assert stub.kwargs["messages"] == MESSAGES
    assert stub.kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "triage_result", "strict": True, "schema": SCHEMA},
    }


def test_optional_parameters_are_omitted_by_default() -> None:
    client, stub = client_with(make_completion())
    client.complete(MESSAGES, SCHEMA, "triage_result")
    assert "temperature" not in stub.kwargs
    assert "reasoning_effort" not in stub.kwargs


def test_optional_parameters_are_sent_when_set() -> None:
    client, stub = client_with(make_completion(), temperature=0.0, reasoning_effort="low")
    client.complete(MESSAGES, SCHEMA, "triage_result")
    assert stub.kwargs["temperature"] == 0.0
    assert stub.kwargs["reasoning_effort"] == "low"


def test_provider_error_becomes_llm_error() -> None:
    client, _ = client_with(openai.OpenAIError("rate limit reached"))
    with pytest.raises(LLMError, match="OpenAIError: rate limit reached") as info:
        client.complete(MESSAGES, SCHEMA, "triage_result")
    assert info.value.latency_ms >= 0
    assert isinstance(info.value.__cause__, openai.OpenAIError)  # original error kept


def test_refusal_becomes_llm_error() -> None:
    client, _ = client_with(make_completion(None, refusal="I can't help with that."))
    with pytest.raises(LLMError, match="model refused"):
        client.complete(MESSAGES, SCHEMA, "triage_result")


def test_truncated_output_becomes_llm_error() -> None:
    client, _ = client_with(make_completion('{"category": "ref', finish_reason="length"))
    with pytest.raises(LLMError, match="truncated"):
        client.complete(MESSAGES, SCHEMA, "triage_result")


def test_missing_usage_counts_as_zero_tokens() -> None:
    client, _ = client_with(make_completion(usage={}))
    response = client.complete(MESSAGES, SCHEMA, "triage_result")
    assert (response.input_tokens, response.output_tokens) == (0, 0)


def test_missing_credentials_become_llm_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="could not create OpenAI client"):
        OpenAIClient("gpt-test", api_key=None)
