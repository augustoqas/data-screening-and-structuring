"""Tests for the data contract: normalisation, rejection rules and the strict JSON schema."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from triage.schemas import MAX_SUMMARY_CHARS, TriageResult, to_openai_json_schema


def test_valid_payload_parses(payload: dict[str, Any]) -> None:
    result = TriageResult.model_validate(payload)
    assert result.category == "damaged_or_defective"
    assert result.amounts_brl == [199.9]


def test_order_ids_are_normalised(payload: dict[str, Any]) -> None:
    payload["order_ids"] = ["#48213", " 48213 ", "ab-9 1", ""]
    result = TriageResult.model_validate(payload)
    assert result.order_ids == ["48213", "AB-91"]


def test_products_are_normalised(payload: dict[str, Any]) -> None:
    payload["products"] = ["Fone  Bluetooth", "fone bluetooth", "  "]
    assert TriageResult.model_validate(payload).products == ["fone bluetooth"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "shipping"),  # not in the enum
        ("priority", "critical"),  # not in the enum
        ("summary", "   "),  # blank
        ("summary", "x" * (MAX_SUMMARY_CHARS + 1)),  # too long
        ("amounts_brl", [-10.0]),  # negative amount
        ("order_ids", "48213"),  # string instead of list
    ],
)
def test_invalid_values_are_rejected(payload: dict[str, Any], field: str, value: Any) -> None:
    payload[field] = value
    with pytest.raises(ValidationError):
        TriageResult.model_validate(payload)


def test_missing_field_is_rejected(payload: dict[str, Any]) -> None:
    del payload["priority"]
    with pytest.raises(ValidationError):
        TriageResult.model_validate(payload)


def test_unknown_field_is_rejected(payload: dict[str, Any]) -> None:
    payload["confidence"] = 0.9
    with pytest.raises(ValidationError):
        TriageResult.model_validate(payload)


def _walk(node: Any):
    """Yield every dict nested anywhere inside ``node``."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def test_openai_schema_is_strict() -> None:
    schema = to_openai_json_schema(TriageResult)
    assert "$defs" not in schema
    for node in _walk(schema):
        assert "$ref" not in node
        assert "default" not in node
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])


def test_openai_schema_keeps_enums_and_descriptions() -> None:
    category = to_openai_json_schema(TriageResult)["properties"]["category"]
    assert "out_of_scope" in category["enum"]
    assert "delivery_issue" in category["description"]
