"""Evaluation harness: measure the pipeline against a labelled golden set.

Phase 2 builds this up in steps. The first piece is the dataset:

* :class:`triage.eval.dataset.GoldenCase` - one labelled test case.
* :func:`triage.eval.dataset.load_golden_set` - load and validate the whole set.
"""

from triage.eval.dataset import CaseTag, ExpectedTriage, GoldenCase, load_golden_set

__all__ = ["CaseTag", "ExpectedTriage", "GoldenCase", "load_golden_set"]
