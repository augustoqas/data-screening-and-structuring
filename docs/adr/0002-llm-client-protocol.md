# 0002. The pipeline depends on an LLM client protocol

**Status:** Accepted

## Context

The pipeline needs an LLM, but calling a real one in tests is slow, costs money, needs a secret, and is non-deterministic. Worse, the most important paths to test are the failure paths (invalid JSON, a missing field, a rate limit, a refusal), which a real model produces rarely and unpredictably.

Calling the OpenAI SDK directly from the pipeline would also tie the whole project to one provider's types and exceptions.

## Decision

`llm.py` defines a minimal `LLMClient` protocol:

```python
class LLMClient(Protocol):
    model: str
    def complete(self, messages, json_schema, schema_name) -> LLMResponse: ...
```

- `OpenAIClient` implements it with Chat Completions and Structured Outputs. It is the only module that imports `openai`.
- Every provider problem (connection errors, rate limits, refusals, truncated output, missing credentials) is translated into a single `LLMError`, so callers handle one exception type.
- Tests use `FakeLLMClient`, which returns scripted outputs or raises scripted errors and records every call.

A `Protocol` (structural typing) was chosen over an abstract base class: any object with a matching `complete` method qualifies, without inheriting from anything.

## Consequences

- Pipeline and CLI tests run offline, in milliseconds, for free, and can reproduce any failure on demand.
- Supporting another provider means writing one class, without touching the pipeline.
- The interface is deliberately small. Provider-specific features (streaming, tool calls) are not exposed; if they are ever needed, the protocol has to grow.
- `OpenAIClient` itself still needs testing; those tests replace only the SDK call with a stub returning real `ChatCompletion` objects.
