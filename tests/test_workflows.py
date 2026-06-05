from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_workflow(name: str) -> dict[str, Any]:
    with (ROOT / ".github" / "workflows" / name).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    if True in data and "on" not in data:
        data["on"] = data[True]
    return data


def step_runs(job: dict[str, Any], expected: str) -> bool:
    return any(step.get("run") == expected for step in job["steps"])


def step_uses(job: dict[str, Any], expected: str) -> bool:
    return any(step.get("uses") == expected for step in job["steps"])


def test_release_workflow_requires_tagged_releases_and_trusted_publishing() -> None:
    workflow = load_workflow("release.yml")

    assert workflow["on"]["push"]["tags"] == ["v*.*.*"]
    assert workflow["on"]["workflow_dispatch"] is None

    jobs = workflow["jobs"]
    test_job = jobs["test"]
    tag_check = next(
        step
        for step in test_job["steps"]
        if step.get("run") == 'python scripts/check_release_tag.py "${{ github.ref_name }}"'
    )
    assert tag_check["if"] == "github.event_name == 'push'"
    assert step_runs(test_job, "python -m pip_audit --skip-editable")
    assert step_runs(test_job, "python -m pytest")
    assert step_runs(
        test_job,
        "novel2script examples/three_chapters.txt --format markdown --output outputs/release-smoke.revision.md",
    )
    web_smoke = next(step for step in test_job["steps"] if step["name"] == "Smoke test Web entrypoint")
    assert "novel2script-web --version" in web_smoke["run"]
    assert "novel2script-web --help" in web_smoke["run"]
    assert "python -m novel2script.web --version" in web_smoke["run"]
    assert "python -m novel2script.web --help" in web_smoke["run"]

    publish_job = jobs["publish"]
    assert publish_job["needs"] == "build"
    assert publish_job["if"] == "github.event_name == 'push'"
    assert publish_job["environment"]["name"] == "pypi"
    assert publish_job["permissions"]["id-token"] == "write"
    assert step_uses(publish_job, "pypa/gh-action-pypi-publish@release/v1")


def test_release_workflow_smokes_web_entrypoints_in_distributions() -> None:
    workflow = load_workflow("release.yml")
    build_job = workflow["jobs"]["build"]

    wheel_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed wheel")
    assert ".venv-wheel/bin/novel2script-web --version" in wheel_smoke["run"]
    assert ".venv-wheel/bin/novel2script-web --help" in wheel_smoke["run"]
    assert ".venv-wheel/bin/python -m novel2script.web --version" in wheel_smoke["run"]
    assert ".venv-wheel/bin/python -m novel2script.web --help" in wheel_smoke["run"]
    assert (
        ".venv-wheel/bin/python scripts/smoke_web_server.py --python .venv-wheel/bin/python"
        in wheel_smoke["run"]
    )
    assert (
        ".venv-wheel/bin/novel2script examples/three_chapters.txt --format markdown "
        "--output outputs/wheel-smoke.revision.md"
        in wheel_smoke["run"]
    )

    sdist_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed sdist")
    assert ".venv-sdist/bin/novel2script-web --version" in sdist_smoke["run"]
    assert ".venv-sdist/bin/novel2script-web --help" in sdist_smoke["run"]
    assert ".venv-sdist/bin/python -m novel2script.web --version" in sdist_smoke["run"]
    assert ".venv-sdist/bin/python -m novel2script.web --help" in sdist_smoke["run"]
    assert (
        ".venv-sdist/bin/python scripts/smoke_web_server.py --python .venv-sdist/bin/python"
        in sdist_smoke["run"]
    )
    assert (
        ".venv-sdist/bin/novel2script examples/three_chapters.txt --format markdown "
        "--output outputs/sdist-smoke.revision.md"
        in sdist_smoke["run"]
    )


def test_release_workflow_creates_github_release_after_pypi_publish() -> None:
    workflow = load_workflow("release.yml")

    release_job = workflow["jobs"]["github-release"]
    assert set(release_job["needs"]) == {"build", "publish"}
    assert release_job["if"] == "github.event_name == 'push'"
    assert release_job["permissions"]["contents"] == "write"
    assert step_uses(release_job, "softprops/action-gh-release@v2")

    create_release_step = next(
        step for step in release_job["steps"] if step.get("uses") == "softprops/action-gh-release@v2"
    )
    assert create_release_step["with"]["files"] == "dist/*"
    assert create_release_step["with"]["fail_on_unmatched_files"] is True


def test_ci_workflow_smokes_linux_distributions_and_windows_cli() -> None:
    workflow = load_workflow("ci.yml")
    jobs = workflow["jobs"]

    assert jobs["test"]["strategy"]["matrix"]["python-version"] == [
        "3.10",
        "3.11",
        "3.12",
        "3.13",
        "3.14",
    ]
    assert step_runs(
        jobs["test"],
        "novel2script examples/three_chapters.txt --format markdown --output outputs/ci-smoke.revision.md",
    )

    build_job = jobs["build"]
    wheel_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed wheel")
    assert ".venv-wheel/bin/novel2script --help" in wheel_smoke["run"]
    assert ".venv-wheel/bin/novel2script-web --version" in wheel_smoke["run"]
    assert ".venv-wheel/bin/novel2script-web --help" in wheel_smoke["run"]
    assert ".venv-wheel/bin/python -m novel2script --version" in wheel_smoke["run"]
    assert ".venv-wheel/bin/python -m novel2script.web --version" in wheel_smoke["run"]
    assert ".venv-wheel/bin/python -m novel2script.web --help" in wheel_smoke["run"]
    assert (
        ".venv-wheel/bin/python scripts/smoke_web_server.py --python .venv-wheel/bin/python"
        in wheel_smoke["run"]
    )
    assert (
        ".venv-wheel/bin/novel2script examples/three_chapters.txt --format markdown "
        "--output outputs/wheel-smoke.revision.md"
        in wheel_smoke["run"]
    )

    sdist_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed sdist")
    assert ".venv-sdist/bin/novel2script --help" in sdist_smoke["run"]
    assert ".venv-sdist/bin/novel2script-web --version" in sdist_smoke["run"]
    assert ".venv-sdist/bin/novel2script-web --help" in sdist_smoke["run"]
    assert ".venv-sdist/bin/python -m novel2script --version" in sdist_smoke["run"]
    assert ".venv-sdist/bin/python -m novel2script.web --version" in sdist_smoke["run"]
    assert ".venv-sdist/bin/python -m novel2script.web --help" in sdist_smoke["run"]
    assert (
        ".venv-sdist/bin/python scripts/smoke_web_server.py --python .venv-sdist/bin/python"
        in sdist_smoke["run"]
    )
    assert (
        ".venv-sdist/bin/novel2script examples/three_chapters.txt --format markdown "
        "--output outputs/sdist-smoke.revision.md"
        in sdist_smoke["run"]
    )

    windows_job = jobs["windows-smoke"]
    assert windows_job["runs-on"] == "windows-latest"
    assert step_runs(windows_job, "novel2script --version")
    assert step_runs(windows_job, "python -m novel2script --version")
    assert step_runs(
        windows_job,
        r"novel2script examples\three_chapters.txt --format markdown --output outputs\windows-smoke.revision.md",
    )
    windows_web_smoke = next(
        step for step in windows_job["steps"] if step["name"] == "Smoke test Web entrypoint"
    )
    assert "novel2script-web --version" in windows_web_smoke["run"]
    assert "novel2script-web --help" in windows_web_smoke["run"]
    assert "python -m novel2script.web --version" in windows_web_smoke["run"]
    assert "python -m novel2script.web --help" in windows_web_smoke["run"]
    assert step_runs(
        windows_job,
        r"cmd /c fc /b schemas\script.schema.json src\novel2script\schemas\script.schema.json",
    )
