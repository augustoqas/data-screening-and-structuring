# Architecture decision records

Short documents that capture an important decision, the context that led to it and its consequences. They explain *why* the code looks the way it does, which the code itself cannot.

Format: **Context** (the problem and the forces at play), **Decision** (what we chose), **Consequences** (what gets easier, what gets harder). A decision that is later replaced is marked as superseded, not deleted.

| # | Decision | Status |
|---|---|---|
| [0001](0001-single-schema-for-prompt-and-validation.md) | One Pydantic model is both the output schema sent to the LLM and the validator of its answer | Accepted |
| [0002](0002-llm-client-protocol.md) | The pipeline depends on a small `LLMClient` protocol, not on the OpenAI SDK | Accepted |
| [0003](0003-versioned-prompt-files.md) | Prompts are immutable, versioned files | Accepted |
| [0004](0004-failures-as-outcomes.md) | Model and provider failures are returned as outcomes, not raised | Accepted |
