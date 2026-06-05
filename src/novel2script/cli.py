"""Command line interface for novel2script."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from novel2script import __version__
from novel2script.ai_provider import convert_with_provider_status
from novel2script.fountain import draft_to_fountain, write_fountain
from novel2script.schema import validate_script
from novel2script.yaml_io import draft_to_yaml, write_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novel2script",
        description="Convert a 3+ chapter novel manuscript into structured screenplay YAML.",
    )
    parser.add_argument("input", type=Path, help="UTF-8 novel manuscript path.")
    parser.add_argument("-o", "--output", type=Path, help="Output path. Defaults to stdout.")
    parser.add_argument(
        "--format",
        choices=["yaml", "fountain"],
        default="yaml",
        help="Output format. YAML keeps the structured adaptation package; Fountain exports a screenplay text draft.",
    )
    parser.add_argument("--title", help="Screenplay title. Defaults to the first chapter title.")
    parser.add_argument(
        "--provider",
        choices=["local", "openai"],
        default="local",
        help="Use local heuristics or optional OpenAI enhancement.",
    )
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI-compatible model name.")
    parser.add_argument("--validate", action="store_true", help="Validate generated YAML with Schema.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.output:
            _validate_output_path(args.output)

        text = _read_input_text(args.input)
        conversion = convert_with_provider_status(
            text=text,
            title=args.title,
            provider=args.provider,
            model=args.model,
        )
        draft = conversion.draft
        if args.provider == "openai" and not conversion.provider_status.remote:
            sys.stderr.write(f"novel2script: warning: {conversion.provider_status.message}\n")
        data = draft.to_dict()
        if args.validate:
            validate_script(data)

        if args.output and args.format == "yaml":
            write_yaml(draft, args.output)
        elif args.output and args.format == "fountain":
            write_fountain(draft, args.output)
        elif args.format == "yaml":
            sys.stdout.write(draft_to_yaml(draft))
        else:
            sys.stdout.write(draft_to_fountain(draft))
        return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        sys.stderr.write(f"novel2script: error: {exc}\n")
        return 1


def _read_input_text(input_path: Path) -> str:
    if not input_path.exists():
        raise ValueError(f"Input file does not exist: {input_path}")
    if input_path.is_dir():
        raise ValueError(f"Input path is a directory, expected a UTF-8 text file: {input_path}")
    try:
        return input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input file must be UTF-8 text: {input_path}") from exc


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _validate_output_path(output_path: Path) -> None:
    if output_path.is_dir():
        raise ValueError(f"Output path is a directory, expected a file path: {output_path}")
    if output_path.parent.exists() and not output_path.parent.is_dir():
        raise ValueError(f"Output parent path is not a directory: {output_path.parent}")


if __name__ == "__main__":
    raise SystemExit(main())
