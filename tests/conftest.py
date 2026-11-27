"""Shared test fixtures.

:class:`FakeLLMClient` stands in for OpenAI: it returns pre-scripted outputs (or raises
pre-scripted errors) and records every call, so tests can exercise any pipeline path,
including the failure paths that are hard to trigger with a real model, deterministically
and for free.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from triage.llm import LLMResponse


class FakeLLMClient:
    """Scripted :class:`~triage.llm.LLMClient`. Each call consumes the next script item.

    A script item is either a ``str`` (returned as the model output), a ``dict``
    (serialised to JSON first) or an :class:`Exception` (raised).
    """

    def __init__(self, *script: str | dict[str, Any] | Exception, model: str = "fake-model"):
        self.model = model
        self._script = list(script)
        self.calls: list[dict[str, Any]] = []

    def complete(
        self, messages: list[dict[str, str]], json_schema: dict[str, Any], schema_name: str
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "schema": json_schema, "name": schema_name})
        if not self._script:
            raise AssertionError("FakeLLMClient called more times than scripted")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        content = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
        return LLMResponse(
            content=content, model=self.model, input_tokens=100, output_tokens=50, latency_ms=12.5
        )


def valid_payload(**overrides: Any) -> dict[str, Any]:
    """A well-formed model output; override fields to build variants."""
    payload: dict[str, Any] = {
        "category": "damaged_or_defective",
        "requested_action": "refund",
        "priority": "high",
        "priority_reason": "Produto chegou quebrado e cliente pede reembolso.",
        "sentiment": "frustrated",
        "summary": "Cliente recebeu fone quebrado no pedido 48213 e quer reembolso.",
        "order_ids": ["#48213"],
        "products": ["Fone Bluetooth"],
        "amounts_brl": [199.9],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def payload() -> dict[str, Any]:
    """A fresh valid payload for each test, safe to mutate."""
    return valid_payload()
