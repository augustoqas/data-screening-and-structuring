"""E-commerce support triage: turn messy customer messages into validated structured data.

Public entry points:

* :class:`triage.pipeline.TriagePipeline` - runs one message through the LLM and validation.
* :class:`triage.schemas.TriageResult` - the structured record the pipeline produces.
* :class:`triage.schemas.TriageOutcome` - the result plus metadata (status, tokens, latency).
"""

from triage.pipeline import TriagePipeline
from triage.schemas import TriageOutcome, TriageResult

__all__ = ["TriageOutcome", "TriagePipeline", "TriageResult"]
__version__ = "0.1.0"
