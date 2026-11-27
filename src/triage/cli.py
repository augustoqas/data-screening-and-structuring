"""Command-line entry point: ``triage "message"``.

Examples::

    triage "comprei um fone, pedido #48213, chegou quebrado"
    triage --file mensagem.txt
    echo "cadê meu pedido??" | triage

Prints the full :class:`~triage.schemas.TriageOutcome` as JSON. Exit code is 0 on
success, 1 when the pipeline returns ``failed``, 2 for usage/configuration errors.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from triage.config import get_settings
from triage.llm import LLMError, OpenAIClient
from triage.pipeline import TriagePipeline
from triage.schemas import Status


def _read_message(args: argparse.Namespace) -> str:
    """Take the message from the argument, a file, or stdin - in that order."""
    if args.message:
        return args.message
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("error: provide a message, --file, or pipe text via stdin")


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline once and print the outcome."""
    # Customer messages are Portuguese; make sure accents print correctly on any console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="triage", description="Triage one e-commerce support message with an LLM."
    )
    parser.add_argument("message", nargs="?", help="the customer message to triage")
    parser.add_argument("-f", "--file", help="read the message from a UTF-8 text file")
    parser.add_argument("--model", help="override TRIAGE_MODEL")
    parser.add_argument("--prompt-version", help="override TRIAGE_PROMPT_VERSION")
    args = parser.parse_args(argv)

    # Everything up to running the pipeline is setup: any failure here is a usage or
    # configuration problem, reported in one line with exit code 2, never a traceback.
    try:
        settings = get_settings()
        if settings.openai_api_key is None:
            return _usage_error("OPENAI_API_KEY is not set (see .env.example)")
        client = OpenAIClient(
            model=args.model or settings.model,
            api_key=settings.openai_api_key.get_secret_value(),
            timeout_s=settings.request_timeout_s,
            temperature=settings.temperature,
            reasoning_effort=settings.reasoning_effort,
        )
        pipeline = TriagePipeline(
            client, prompt_version=args.prompt_version or settings.prompt_version
        )
        message = _read_message(args)
        outcome = pipeline.run(message)
    except ValidationError as exc:
        return _usage_error(f"invalid configuration:\n{exc}")
    except (LLMError, ValueError, OSError) as exc:
        return _usage_error(str(exc))

    print(outcome.model_dump_json(indent=2))
    return 0 if outcome.status is Status.SUCCESS else 1


def _usage_error(message: str) -> int:
    """Print ``message`` to stderr and return the usage-error exit code."""
    print(f"error: {message}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
