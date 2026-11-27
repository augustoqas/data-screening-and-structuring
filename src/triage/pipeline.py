"""The triage pipeline: customer message in, validated :class:`TriageOutcome` out.

Current flow (phase 1):

    message -> build prompt -> LLM (structured output) -> Pydantic validation -> outcome

The pipeline never raises for problems caused by the model or the provider. Those become
an outcome with ``status=failed`` and a readable ``error``, because in production a bad
answer to one message must not crash a batch of thousands. It *does* raise for caller
mistakes (an empty message), which are bugs to fix rather than conditions to handle.

Later phases add business-rule checks, grounding, retries with error feedback and a
human-review route between validation and the outcome.
"""

from __future__ import annotations

from pydantic import ValidationError

from triage.llm import LLMClient, LLMError
from triage.prompts import build_messages, load_prompt
from triage.schemas import Status, TriageOutcome, TriageResult, to_openai_json_schema

MAX_MESSAGE_CHARS = 5_000
SCHEMA_NAME = "triage_result"


class TriagePipeline:
    """Turns one customer message into a :class:`TriageOutcome`.

    Args:
        client: Any :class:`~triage.llm.LLMClient` - the real OpenAI client in
            production, a fake in tests.
        prompt_version: Which file under ``triage/prompts`` to use as the system prompt.
    """

    def __init__(self, client: LLMClient, prompt_version: str = "v1") -> None:
        self.client = client
        self.prompt_version = prompt_version
        self._system_prompt = load_prompt(prompt_version)
        # The schema never changes at runtime, so build it once.
        self._json_schema = to_openai_json_schema(TriageResult)

    def run(self, message: str) -> TriageOutcome:
        """Triage one message.

        Raises:
            ValueError: if ``message`` is blank or longer than ``MAX_MESSAGE_CHARS``.
        """
        text = message.strip()
        if not text:
            raise ValueError("message must not be empty")
        if len(text) > MAX_MESSAGE_CHARS:
            raise ValueError(f"message exceeds {MAX_MESSAGE_CHARS} characters")

        messages = build_messages(self._system_prompt, text)

        try:
            response = self.client.complete(messages, self._json_schema, SCHEMA_NAME)
        except LLMError as exc:
            return self._failed(f"llm_error: {exc}", latency_ms=exc.latency_ms)

        try:
            result = TriageResult.model_validate_json(response.content)
        except ValidationError as exc:
            return self._failed(
                f"validation_error: {_format_validation_error(exc)}",
                raw_output=response.content,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )

        return TriageOutcome(
            status=Status.SUCCESS,
            result=result,
            raw_output=response.content,
            model=response.model,
            prompt_version=self.prompt_version,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )

    def _failed(
        self,
        error: str,
        *,
        raw_output: str | None = None,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> TriageOutcome:
        """Build a ``failed`` outcome, keeping whatever metadata is available."""
        return TriageOutcome(
            status=Status.FAILED,
            error=error,
            raw_output=raw_output,
            model=model or self.client.model,
            prompt_version=self.prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )


def _format_validation_error(exc: ValidationError) -> str:
    """Compress a Pydantic error into one line, e.g. ``summary: must not be empty``.

    Kept short and field-specific on purpose: in phase 3 this exact text is fed back to
    the model on retry, telling it precisely what to fix.
    """
    parts = []
    for err in exc.errors():
        location = ".".join(str(piece) for piece in err["loc"]) or "<root>"
        parts.append(f"{location}: {err['msg']}")
    return "; ".join(parts)
