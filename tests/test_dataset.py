"""Tests for the golden set and its loader.

Two kinds of test: the loader behaves correctly (parsing, errors, de-duplication), and the
committed dataset itself is healthy (valid labels, normalised entities, tag coverage).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from triage.eval.dataset import (
    MIN_PER_TAG,
    CaseTag,
    GoldenCase,
    iter_tag_counts,
    load_golden_set,
)

VALID_LINE = (
    '{"id": "x1", "message": "meu pedido 55 não chegou", "tags": ["simple"], '
    '"expected": {"category": "delivery_issue", "requested_action": "delivery_update", '
    '"priority": "high", "sentiment": "neutral", "order_ids": ["55"], "products": [], '
    '"amounts_brl": []}, "notes": ""}'
)


def write(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "set.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --- loader behaviour ----------------------------------------------------------------


def test_loads_valid_file_ignoring_comments_and_blanks(tmp_path: Path) -> None:
    cases = load_golden_set(write(tmp_path, "# a section", "", VALID_LINE))
    assert len(cases) == 1
    assert cases[0].id == "x1"
    assert cases[0].expected.category == "delivery_issue"


def test_invalid_category_reports_line_number(tmp_path: Path) -> None:
    bad = VALID_LINE.replace("delivery_issue", "shipping")
    with pytest.raises(ValueError, match="line 2"):
        load_golden_set(write(tmp_path, "# header", bad))


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    bad = VALID_LINE.replace('"notes": ""', '"confidence": 0.9, "notes": ""')
    with pytest.raises(ValueError, match="invalid golden case"):
        load_golden_set(write(tmp_path, bad))


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate case id"):
        load_golden_set(write(tmp_path, VALID_LINE, VALID_LINE))


def test_empty_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no golden cases"):
        load_golden_set(write(tmp_path, "# only a comment"))


def test_case_needs_at_least_one_tag(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_golden_set(write(tmp_path, VALID_LINE.replace('["simple"]', "[]")))


# --- the committed dataset -----------------------------------------------------------


@pytest.fixture(scope="module")
def golden() -> list[GoldenCase]:
    return load_golden_set()


def test_dataset_has_enough_cases(golden: list[GoldenCase]) -> None:
    assert len(golden) >= 30


def test_every_tag_has_minimum_examples(golden: list[GoldenCase]) -> None:
    counts = iter_tag_counts(golden)
    below = {tag.value: n for tag, n in counts.items() if n < MIN_PER_TAG}
    assert not below, f"tags below {MIN_PER_TAG}: {below}"


def test_all_seven_tags_are_used(golden: list[GoldenCase]) -> None:
    used = {tag for case in golden for tag in case.tags}
    assert used == set(CaseTag)


def test_labels_are_valid_pipeline_outputs_and_normalised(golden: list[GoldenCase]) -> None:
    """Every label builds a valid TriageResult, and entities are already normalised."""
    for case in golden:
        result = case.as_triage_result()  # raises if a label is not schema-valid
        assert result.order_ids == case.expected.order_ids, case.id
        assert result.products == case.expected.products, case.id


def test_ids_are_unique(golden: list[GoldenCase]) -> None:
    ids = [case.id for case in golden]
    assert len(ids) == len(set(ids))
