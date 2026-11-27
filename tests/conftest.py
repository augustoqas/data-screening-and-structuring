"""Shared test fixtures."""

from __future__ import annotations

from typing import Any

import pytest


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
