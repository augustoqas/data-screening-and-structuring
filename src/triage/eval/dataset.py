"""The golden set: a fixed, hand-labelled dataset that turns opinions into measurements.

Each case pairs a realistic customer message with the output a correct run should
produce. The runner (next task) feeds every message through the pipeline and compares the
result against ``expected``; the metrics task scores the comparison.

Only the fields that can be judged objectively are labelled. ``summary`` and
``priority_reason`` are free text, so there is no single correct string and they are left
out of :class:`ExpectedTriage`. The structured fields reuse the exact enums and types of
:class:`~triage.schemas.TriageResult`, so a label that is not a valid pipeline output is
impossible: it would fail to load.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from triage.schemas import Category, Priority, RequestedAction, Sentiment, TriageResult

# The dataset lives at the repository root (it is development data, not shipped with the
# package). From src/triage/eval/dataset.py, three parents up is the repo root.
DEFAULT_GOLDEN_SET = Path(__file__).resolve().parents[3] / "evals" / "golden_set.jsonl"

# Minimum examples required per tag, enforced by the tests.
MIN_PER_TAG = 3


class CaseTag(StrEnum):
    """The kind of challenge a case represents, so results can be sliced by type.

    A case may carry several tags (a slangy message with two problems is both
    ``SLANG_TYPOS`` and ``MULTIPLE_ISSUES``).
    """

    SIMPLE = "simple"
    AMBIGUOUS = "ambiguous"
    MULTIPLE_ISSUES = "multiple_issues"
    SLANG_TYPOS = "slang_typos"
    MALFORMED = "malformed"
    PROMPT_INJECTION = "prompt_injection"
    OUT_OF_SCOPE = "out_of_scope"


class ExpectedTriage(BaseModel):
    """The objectively checkable part of a correct output.

    The structured fields only; the free-text fields are not labelled. Values reuse the
    pipeline's own enums and are stored already normalised (order IDs without ``#``,
    products lowercased), so comparison against the pipeline output is like for like.
    """

    model_config = ConfigDict(extra="forbid")

    category: Category
    requested_action: RequestedAction
    priority: Priority
    sentiment: Sentiment
    order_ids: list[str]
    products: list[str]
    amounts_brl: list[float]


class GoldenCase(BaseModel):
    """One labelled test case."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    tags: list[CaseTag] = Field(min_length=1)
    expected: ExpectedTriage
    notes: str = ""

    def as_triage_result(self) -> TriageResult:
        """Build a full :class:`~triage.schemas.TriageResult` from the labels.

        Free-text fields get placeholder values. This proves every label is a valid
        pipeline output and, because ``TriageResult`` re-runs normalisation, lets the
        tests confirm the stored labels are already normalised.
        """
        return TriageResult(
            summary="(golden placeholder)",
            priority_reason="(golden placeholder)",
            **self.expected.model_dump(),
        )


def load_golden_set(path: Path | None = None) -> list[GoldenCase]:
    """Load and validate the golden set from a JSONL file.

    One JSON object per line; blank lines and lines starting with ``#`` are ignored, so
    the file can carry section comments. Raises ``ValueError`` with the line number on the
    first invalid case, and on a duplicate ``id``.
    """
    path = path or DEFAULT_GOLDEN_SET
    cases: list[GoldenCase] = []
    seen: set[str] = set()

    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            case = GoldenCase.model_validate_json(line)
        except ValidationError as exc:
            raise ValueError(f"invalid golden case on line {line_number}: {exc}") from exc
        if case.id in seen:
            raise ValueError(f"duplicate case id {case.id!r} on line {line_number}")
        seen.add(case.id)
        cases.append(case)

    if not cases:
        raise ValueError(f"no golden cases found in {path}")
    return cases


def iter_tag_counts(cases: list[GoldenCase]) -> dict[CaseTag, int]:
    """Count how many cases carry each tag."""
    counts: dict[CaseTag, int] = dict.fromkeys(CaseTag, 0)
    for case in cases:
        for tag in set(case.tags):
            counts[tag] += 1
    return counts


def _as_jsonl_line(case: GoldenCase) -> str:
    """Serialise a case to a single JSONL line (used by the dataset builder)."""
    data = {
        "id": case.id,
        "message": case.message,
        "tags": [tag.value for tag in case.tags],
        "expected": case.expected.model_dump(),
        "notes": case.notes,
    }
    return json.dumps(data, ensure_ascii=False)
