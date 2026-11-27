# 0001. One schema for the prompt and for validation

**Status:** Accepted

## Context

The pipeline has to tell the LLM which fields to return and then check what comes back. The usual approaches each have a problem:

- **Describe the format in the prompt text** and validate separately. The two drift apart: someone adds a field to the validator and forgets the prompt, or the other way round.
- **Rely only on Structured Outputs.** OpenAI's strict mode guarantees the response matches the JSON schema, which all but eliminates malformed JSON. It does not check anything a JSON schema cannot express (a summary that is only whitespace, duplicate order IDs) and it does not normalise values.
- **Use the SDK's `parse()` helper**, which validates for us. On a validation error it raises and the raw output is harder to keep, but the raw output is exactly what we need for debugging, for the review queue and, later, for the retry prompt.

## Decision

`TriageResult` (Pydantic) is the single source of truth:

1. `to_openai_json_schema(TriageResult)` produces the schema sent with `response_format={"type": "json_schema", "strict": true}`. Field descriptions are part of the schema and act as per-field instructions.
2. The pipeline requests the raw JSON text and validates it itself with `TriageResult.model_validate_json()`, keeping the raw output on failure.

Every field is required and unknown keys are forbidden (`extra="forbid"`), so the contract is closed in both directions.

## Consequences

- Adding or changing a field is a single edit; the model's instructions and the validation cannot disagree.
- Strict mode only accepts a subset of JSON Schema, so we maintain a small converter (closed objects, all properties required, `$ref`s inlined, defaults removed). A test walks the generated schema to enforce these rules.
- Some Pydantic features (custom validators, string length limits) are not visible to the model through the schema. They still run on the answer, and the descriptions state the limits in words.
- We own the parsing step, so we control the error message format, which phase 3 reuses to tell the model what to fix.
