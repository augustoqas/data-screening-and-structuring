"""LLM client abstraction.

The pipeline depends on the small :class:`LLMClient` protocol, not on the OpenAI SDK.
That buys two things:

* **Testability** - tests plug in a fake client that returns canned (or deliberately
  broken) outputs, so every failure path is exercised without network calls or cost.
* **Swappability** - another provider only needs a class with a ``complete`` method.

Every provider error is translated into :class:`LLMError`, so the pipeline handles one
exception type regardless of what went wrong underneath.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol

import openai


@dataclass(frozen=True)
class LLMResponse:
    """A completed LLM call: the raw text plus what it cost."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class LLMError(Exception):
    """The LLM call failed (network, auth, rate limit, refusal, truncation...).

    ``latency_ms`` records how long we waited before failing, so the time is still
    accounted for in metrics.
    """

    def __init__(self, message: str, *, latency_ms: float = 0.0) -> None:
        super().__init__(message)
        self.latency_ms = latency_ms


class LLMClient(Protocol):
    """Anything that can turn chat messages into a JSON string matching a schema."""

    model: str

    def complete(
        self, messages: list[dict[str, str]], json_schema: dict[str, Any], schema_name: str
    ) -> LLMResponse:
        """Send ``messages`` and return a response constrained to ``json_schema``."""
        ...


class OpenAIClient:
    """:class:`LLMClient` backed by OpenAI Chat Completions with Structured Outputs.

    ``response_format`` with ``strict: True`` makes the API constrain generation to the
    schema, which all but eliminates malformed JSON. It does *not* guarantee the values
    are correct - that is what the pipeline's validation (and later, the business-rule
    and grounding checks) is for.
    """

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        timeout_s: float = 30.0,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._reasoning_effort = reasoning_effort
        # The SDK already retries transient failures (connection errors, 429, 5xx) with
        # exponential backoff; max_retries tunes that. Retrying *bad outputs* is a
        # different concern, handled by the pipeline.
        self._client = openai.OpenAI(api_key=api_key, timeout=timeout_s, max_retries=max_retries)

    def complete(
        self, messages: list[dict[str, str]], json_schema: dict[str, Any], schema_name: str
    ) -> LLMResponse:
        """Call the API and return the raw JSON text. Raises :class:`LLMError` on failure."""
        optional: dict[str, Any] = {}
        if self._temperature is not None:
            optional["temperature"] = self._temperature
        if self._reasoning_effort is not None:
            optional["reasoning_effort"] = self._reasoning_effort

        start = time.perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
                },
                **optional,
            )
        except openai.OpenAIError as exc:
            raise LLMError(f"{type(exc).__name__}: {exc}", latency_ms=_elapsed_ms(start)) from exc
        latency_ms = _elapsed_ms(start)

        choice = response.choices[0]
        if choice.message.refusal:
            raise LLMError(f"model refused: {choice.message.refusal}", latency_ms=latency_ms)
        if choice.finish_reason == "length":
            raise LLMError("output truncated (finish_reason=length)", latency_ms=latency_ms)

        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )


def _elapsed_ms(start: float) -> float:
    """Milliseconds since ``start`` (a ``time.perf_counter()`` value)."""
    return (time.perf_counter() - start) * 1000
