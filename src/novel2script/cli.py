"""Command line interface for novel2script."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from novel2script.ai_provider import convert_with_optional_ai
from novel2script.schema import validate_script
from novel2script.yaml_io import draft_to_yaml, write_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novel2script",
        description="Convert a 3+ chapter novel manuscript into structured screenplay YAML.",
    )
    parser.add_argument("input", type=Path, help="UTF-8 novel manuscript path.")
    parser.add_argument("-o", "--output", type=Path, help="Output YAML path. Defaults to stdout.")
    parser.add_argument("--title", help="Screenplay title. Defaults to the first chapter title.")
    parser.add_argument(
        "--provider",
        choices=["local", "openai"],
        default="local",
        help="Use local heuristics or optional OpenAI enhancement.",
    )
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI-compatible model name.")
    parser.add_argument("--validate", action="store_true", help="Validate generated YAML with Schema.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = args.input.read_text(encoding="utf-8")
        draft = convert_with_optional_ai(
            text=text,
            title=args.title,
            provider=args.provider,
            model=args.model,
        )
        data = draft.to_dict()
        if args.validate:
            validate_script(data)

        if args.output:
            write_yaml(draft, args.output)
        else:
            sys.stdout.write(draft_to_yaml(draft))
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(1, f"novel2script: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
