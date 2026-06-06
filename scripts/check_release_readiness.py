"""Run the local release-readiness dry run without publishing anything."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
OUTPUT_DIR = ROOT / "outputs"
DEFAULT_PYTEST_BASETEMP = ".pytest-tmp-release-readiness"
EXAMPLE_MANUSCRIPT = ROOT / "examples" / "three_chapters.txt"
PUBLIC_SCHEMA = ROOT / "schemas" / "script.schema.json"
PACKAGE_SCHEMA = ROOT / "src" / "novel2script" / "schemas" / "script.schema.json"


@dataclass(frozen=True)
class Check:
    label: str
    command: list[str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local release-readiness checks used before tagging a novel2script release. "
            "This script does not publish to PyPI and does not create Git tags."
        )
    )
    parser.add_argument(
        "--tag",
        default="",
        help="Release tag to validate. Defaults to v<installed package version>.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for module and script checks.",
    )
    parser.add_argument(
        "--pytest-basetemp",
        default=DEFAULT_PYTEST_BASETEMP,
        help=(
            "Workspace-local pytest temporary directory. "
            f"Defaults to {DEFAULT_PYTEST_BASETEMP}."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned checks without executing them.",
    )
    parser.add_argument(
        "--skip-audit",
        action="store_true",
        help="Skip pip-audit for offline local dry runs. Full release readiness should run it.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip distribution build and twine checks for faster local iteration.",
    )
    parser.add_argument(
        "--skip-web-smoke",
        action="store_true",
        help="Skip starting the local Web server smoke test.",
    )
    parser.add_argument("--schema-only", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--twine-check-only", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.schema_only:
        _compare_schema_copies()
        print("Schema copies match.")
        return 0
    if args.twine_check_only:
        _twine_check_distributions(args.python)
        return 0

    python = str(Path(args.python))
    pytest_basetemp = _resolve_workspace_path(args.pytest_basetemp, "--pytest-basetemp")
    release_tag = args.tag or f"v{version('novel2script')}"
    cli_console = _resolve_console_script("novel2script", strict=not args.dry_run)
    web_console = _resolve_console_script("novel2script-web", strict=not args.dry_run)
    checks = release_checks(
        python=python,
        release_tag=release_tag,
        pytest_basetemp=str(pytest_basetemp),
        cli_console=cli_console,
        web_console=web_console,
        include_audit=not args.skip_audit,
        include_build=not args.skip_build,
        include_web_smoke=not args.skip_web_smoke,
    )

    print("Release readiness dry run:")
    for check in checks:
        print(f"- {check.label}: {_format_command(check.command)}")

    if args.dry_run:
        print("Dry run only; no checks were executed.")
        return 0

    _prepare_outputs()
    if not args.skip_build:
        _clean_dist()

    for check in checks:
        print(f"\n==> {check.label}")
        subprocess.run(check.command, cwd=ROOT, check=True)

    print("\nRelease readiness checks passed. No package was published and no Git tag was created.")
    return 0


def release_checks(
    *,
    python: str,
    release_tag: str,
    pytest_basetemp: str,
    cli_console: str = "novel2script",
    web_console: str = "novel2script-web",
    include_audit: bool = True,
    include_build: bool = True,
    include_web_smoke: bool = True,
) -> list[Check]:
    checks = [
        Check("pytest", [python, "-m", "pytest", "--basetemp", pytest_basetemp]),
        Check("ruff", [python, "-m", "ruff", "check", "."]),
    ]
    if include_audit:
        checks.append(Check("dependency audit", [python, "-m", "pip_audit", "--skip-editable"]))

    checks.extend(
        [
            Check(
                "release tag matches installed version",
                [python, "scripts/check_release_tag.py", release_tag],
            ),
            Check("CLI console version", [cli_console, "--version"]),
            Check("CLI module version", [python, "-m", "novel2script", "--version"]),
            Check("Web console version", [web_console, "--version"]),
            Check("Web console help", [web_console, "--help"]),
            Check("Web module version", [python, "-m", "novel2script.web", "--version"]),
            Check("Web module help", [python, "-m", "novel2script.web", "--help"]),
        ]
    )
    if include_web_smoke:
        checks.append(Check("Web server smoke", [python, "scripts/smoke_web_server.py"]))

    checks.extend(
        [
            Check(
                "YAML CLI smoke",
                [
                    python,
                    "-m",
                    "novel2script",
                    str(EXAMPLE_MANUSCRIPT),
                    "--output",
                    str(OUTPUT_DIR / "release-readiness.yaml"),
                    "--validate",
                ],
            ),
            Check(
                "Fountain CLI smoke",
                [
                    python,
                    "-m",
                    "novel2script",
                    str(EXAMPLE_MANUSCRIPT),
                    "--format",
                    "fountain",
                    "--output",
                    str(OUTPUT_DIR / "release-readiness.fountain"),
                ],
            ),
            Check(
                "Markdown CLI smoke",
                [
                    python,
                    "-m",
                    "novel2script",
                    str(EXAMPLE_MANUSCRIPT),
                    "--format",
                    "markdown",
                    "--output",
                    str(OUTPUT_DIR / "release-readiness.revision.md"),
                ],
            ),
        ]
    )

    if include_build:
        checks.extend(
            [
                Check("build distributions", [python, "-m", "build"]),
                Check(
                    "twine check distributions",
                    [python, "scripts/check_release_readiness.py", "--twine-check-only"],
                ),
            ]
        )

    checks.append(
        Check("schema copies match", [python, "scripts/check_release_readiness.py", "--schema-only"])
    )
    return checks


def _prepare_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _clean_dist() -> None:
    resolved = DIST_DIR.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to remove unexpected dist path: {resolved}")
    shutil.rmtree(resolved, ignore_errors=True)


def _resolve_workspace_path(value: str, option_name: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root not in resolved.parents:
        raise RuntimeError(f"{option_name} must point inside the repository workspace: {resolved}")
    return resolved


def _resolve_console_script(script_name: str, *, strict: bool) -> str:
    for candidate in _console_script_candidates(script_name):
        if found := shutil.which(candidate):
            return found

    scripts_dir = sysconfig.get_path("scripts")
    if scripts_dir:
        for candidate in _console_script_candidates(script_name):
            path = Path(scripts_dir) / candidate
            if path.exists():
                return str(path.resolve())

    try:
        package = distribution("novel2script")
    except PackageNotFoundError:
        package = None
    if package is not None:
        expected = set(_console_script_candidates(script_name))
        for file in package.files or []:
            if file.name not in expected:
                continue
            path = Path(package.locate_file(file))
            if path.exists():
                return str(path.resolve())

    if not strict:
        return script_name
    raise RuntimeError(
        f"Console script {script_name!r} is not installed or is not discoverable. "
        'Run `python -m pip install -e ".[dev,release,security]"` before the full '
        "release-readiness check."
    )


def _console_script_candidates(script_name: str) -> list[str]:
    candidates = [script_name]
    if os.name == "nt":
        candidates.extend([f"{script_name}.exe", f"{script_name}.cmd", f"{script_name}.bat"])
    return candidates


def _compare_schema_copies() -> None:
    if PUBLIC_SCHEMA.read_bytes() != PACKAGE_SCHEMA.read_bytes():
        raise AssertionError(f"Schema copies differ: {PUBLIC_SCHEMA} != {PACKAGE_SCHEMA}")


def _twine_check_distributions(python: str) -> None:
    distributions = sorted(
        str(path)
        for path in DIST_DIR.iterdir()
        if path.suffix in {".whl", ".gz", ".zip"} or path.name.endswith(".tar.gz")
    )
    if not distributions:
        raise RuntimeError("No built distributions found in dist/. Run build first.")
    subprocess.run([python, "-m", "twine", "check", *distributions], cwd=ROOT, check=True)


def _format_command(command: list[str]) -> str:
    return " ".join(_quote(part) for part in command)


def _quote(part: str) -> str:
    if not part or any(character.isspace() for character in part):
        return f'"{part}"'
    return part


if __name__ == "__main__":
    raise SystemExit(main())
