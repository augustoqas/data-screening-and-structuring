"""Versioned prompts and message construction.

Prompts live as plain files (``v1.md``, ``v2.md``...) instead of strings in code, so:

* each version is immutable once evaluated - a change means a new file, and the eval
  harness can compare ``v1`` against ``v2`` on the same golden set;
* every pipeline outcome records which ``prompt_version`` produced it;
* diffs between versions are readable in a pull request.
"""

from __future__ import annotations

import re
from importlib import resources

CUSTOMER_TAG = "customer_message"
_VERSION_PATTERN = re.compile(r"^v\d+$")


def load_prompt(version: str) -> str:
    """Return the system prompt text for ``version`` (e.g. ``"v1"``).

    Raises ``ValueError`` for a malformed version name and ``FileNotFoundError`` if the
    version does not exist.
    """
    if not _VERSION_PATTERN.match(version):
        raise ValueError(f"invalid prompt version {version!r}; expected e.g. 'v1'")
    path = resources.files(__package__).joinpath(f"{version}.md")
    if not path.is_file():
        raise FileNotFoundError(f"prompt version {version!r} not found")
    return path.read_text(encoding="utf-8")


def available_versions() -> list[str]:
    """List the prompt versions shipped with the package, sorted by number."""
    names = [
        entry.name.removesuffix(".md")
        for entry in resources.files(__package__).iterdir()
        if entry.name.endswith(".md")
    ]
    return sorted((n for n in names if _VERSION_PATTERN.match(n)), key=lambda n: int(n[1:]))


def build_messages(system_prompt: str, customer_message: str) -> list[dict[str, str]]:
    """Build the chat messages for one triage call.

    The customer's text is wrapped in ``<customer_message>`` tags so the model can tell
    data from instructions. Any copy of the closing tag inside the text is removed first:
    otherwise a message could "close" the data block early and append text that looks
    like it came from us - a basic prompt-injection trick.
    """
    closing_tag = re.compile(rf"</\s*{CUSTOMER_TAG}\s*>", re.IGNORECASE)
    sanitised = closing_tag.sub("", customer_message)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"<{CUSTOMER_TAG}>\n{sanitised}\n</{CUSTOMER_TAG}>"},
    ]
