"""Validate that a Git release tag matches the installed package version."""

from __future__ import annotations

import argparse
import os
from importlib.metadata import version


def expected_release_tag(package_version: str) -> str:
    return f"v{package_version}"


def validate_release_tag(tag: str, package_version: str) -> None:
    expected = expected_release_tag(package_version)
    if tag != expected:
        raise ValueError(f"Release tag {tag!r} does not match package version {expected!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check that the release tag matches the installed package version."
    )
    parser.add_argument(
        "tag",
        nargs="?",
        default=os.environ.get("GITHUB_REF_NAME"),
        help="Release tag to validate. Defaults to GITHUB_REF_NAME.",
    )
    parser.add_argument(
        "--distribution",
        default="novel2script",
        help="Installed distribution name to inspect.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.tag:
        parser.error("tag argument or GITHUB_REF_NAME is required")

    package_version = version(args.distribution)
    try:
        validate_release_tag(args.tag, package_version)
    except ValueError as exc:
        parser.exit(1, f"{exc}\n")

    print(f"Release tag {args.tag} matches package version {package_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
