# 0003. Prompts are immutable, versioned files

**Status:** Accepted

## Context

The prompt has as much effect on output quality as the code, but it is usually treated as a string that gets edited in place. That makes it impossible to answer simple questions: which prompt produced this output? Did last week's prompt edit help or hurt? The project's eval harness (phase 2) needs to compare prompt variants on the same dataset, which requires each variant to exist side by side.

## Decision

- Each prompt version is a Markdown file in `src/triage/prompts/` named `vN.md`.
- A version is **immutable once it has been evaluated**: changing the prompt means adding a new file, not editing the old one.
- `load_prompt(version)` reads files through `importlib.resources`, so prompts ship inside the installed package. Version names must match `vN`, which also prevents path traversal.
- The pipeline records `prompt_version` in every outcome; the active version is chosen with `TRIAGE_PROMPT_VERSION` or `--prompt-version`.

## Consequences

- Every result can be traced to the exact prompt that produced it, and any two versions can be compared by the eval harness.
- Prompt changes are reviewed in pull requests as readable text diffs.
- Old versions accumulate in the repository. That is intended: they are the history of what was tried and measured.
- Per-field rules live in the schema descriptions ([ADR 0001](0001-single-schema-for-prompt-and-validation.md)), not in the prompt file, so a schema change also changes what the model sees. Eval runs must therefore record the code revision as well as the prompt version.
