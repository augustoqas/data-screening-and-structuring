# 0004. Failures are returned as outcomes, not raised

**Status:** Accepted

## Context

The pipeline will process messages in batches (the eval harness runs dozens of cases per configuration; a production system would run thousands per day). Some calls will fail: the network drops, the provider rate-limits, the model refuses or returns something that does not validate.

If these failures raise exceptions, every caller has to remember to catch them, and a forgotten `try` stops a whole batch because of one message. Information is also lost: an exception rarely carries the raw model output, the tokens spent or the time taken.

On the other hand, some errors really are bugs in the calling code (an empty message, a prompt version that does not exist) and should fail loudly.

## Decision

Two categories, handled differently:

| Category | Examples | Handling |
|---|---|---|
| **Runtime failures** caused by the model or provider | Network error, rate limit, refusal, truncation, invalid JSON, schema violation | `TriagePipeline.run()` returns a `TriageOutcome` with `status="failed"`, a one-line `error`, the `raw_output` when there is one, and the tokens and latency spent |
| **Caller errors** | Blank or oversized message, unknown prompt version | Raised as `ValueError` / `FileNotFoundError` |

The CLI maps these to exit codes: `0` success, `1` failed outcome, `2` usage or configuration error.

## Consequences

- A batch always completes, and every message ends with a recorded result. Failures can be counted, inspected and sent for review.
- Cost and latency metrics include failed calls, which matters: a failed call is still billed.
- Callers must check `outcome.status` instead of assuming success. The type makes this explicit, since `result` is `None` unless the status is `success`.
- Phase 3 extends the same model with a `needs_review` status rather than introducing exceptions.
