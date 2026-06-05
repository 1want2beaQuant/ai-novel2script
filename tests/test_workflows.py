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
    assert step_runs(test_job, 'python scripts/check_release_tag.py "${{ github.ref_name }}"')
    assert step_runs(test_job, "python -m pip_audit --skip-editable")
    assert step_runs(test_job, "python -m pytest")

    publish_job = jobs["publish"]
    assert publish_job["needs"] == "build"
    assert publish_job["if"] == "github.event_name == 'push'"
    assert publish_job["environment"]["name"] == "pypi"
    assert publish_job["permissions"]["id-token"] == "write"
    assert step_uses(publish_job, "pypa/gh-action-pypi-publish@release/v1")


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

    build_job = jobs["build"]
    wheel_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed wheel")
    assert ".venv-wheel/bin/python -m novel2script --version" in wheel_smoke["run"]

    sdist_smoke = next(step for step in build_job["steps"] if step["name"] == "Smoke test installed sdist")
    assert ".venv-sdist/bin/python -m novel2script --version" in sdist_smoke["run"]

    windows_job = jobs["windows-smoke"]
    assert windows_job["runs-on"] == "windows-latest"
    assert step_runs(windows_job, "novel2script --version")
    assert step_runs(windows_job, "python -m novel2script --version")
    assert step_runs(
        windows_job,
        r"cmd /c fc /b schemas\script.schema.json src\novel2script\schemas\script.schema.json",
    )
