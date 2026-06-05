from pathlib import Path
import re
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    return data


def test_dependabot_covers_python_and_github_actions_weekly() -> None:
    dependabot = load_yaml(ROOT / ".github" / "dependabot.yml")

    updates = {
        (entry["package-ecosystem"], entry["directory"]): entry
        for entry in dependabot["updates"]
    }

    assert dependabot["version"] == 2
    assert set(updates) == {
        ("pip", "/"),
        ("github-actions", "/"),
    }
    for entry in updates.values():
        assert entry["schedule"]["interval"] == "weekly"
        assert entry["open-pull-requests-limit"] == 5


def test_pull_request_template_keeps_release_validation_prompts() -> None:
    template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Summary" in template
    assert "## Validation" in template
    assert "## Checklist" in template
    assert "`python -m pytest`" in template
    assert "`python -m ruff check .`" in template
    assert "`python -m pip_audit --skip-editable`" in template
    assert "`python -m build`" in template
    assert "`python -m twine check dist\\*`" in template
    assert "schemas\\script.schema.json src\\novel2script\\schemas\\script.schema.json" in template
    assert "`PRIVACY.md` is updated" in template
    assert "`CHANGELOG.md` is updated" in template


def test_issue_templates_collect_reproducible_bug_and_feature_context() -> None:
    bug_report = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").read_text(
        encoding="utf-8"
    )
    feature_request = (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md").read_text(
        encoding="utf-8"
    )

    assert "labels: bug" in bug_report
    assert "## Steps to Reproduce" in bug_report
    assert "## Input and Command" in bug_report
    assert "novel2script path\\to\\input.txt --output outputs\\script.yaml --validate" in bug_report
    assert "Remove private manuscript content before sharing." in bug_report
    assert "Python version" in bug_report
    assert "novel2script version" in bug_report

    assert "labels: enhancement" in feature_request
    assert "## Problem" in feature_request
    assert "## Proposed Behavior" in feature_request
    assert "## Alternatives Considered" in feature_request
    assert "## Output Impact" in feature_request
    assert "YAML schema" in feature_request
    assert "optional AI behavior" in feature_request


def test_documented_local_commands_are_cross_shell_safe() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    release_checklist = (ROOT / "docs" / "release_checklist.md").read_text(
        encoding="utf-8"
    )

    assert 'python -m pip install -e ".[dev]"' in readme
    assert "python -m pip install -e .[dev]" not in readme
    assert 'python -m pip install -e ".[dev,release,security]"' in release_checklist
    assert "python -m pip install -e .[dev,release,security]" not in release_checklist

    documented_commands = readme + "\n" + release_checklist
    assert "python -m novel2script.cli" not in documented_commands
    assert (
        "python -m novel2script examples/three_chapters.txt "
        "--output outputs/release-smoke.yaml --validate"
    ) in release_checklist
    assert (
        "python -m novel2script examples/three_chapters.txt "
        "--format fountain --output outputs/release-smoke.fountain"
    ) in release_checklist


def test_local_validation_docs_clean_stale_distribution_artifacts_before_build() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    release_checklist = (ROOT / "docs" / "release_checklist.md").read_text(
        encoding="utf-8"
    )

    cleanup = "Remove-Item -LiteralPath dist -Recurse -Force -ErrorAction SilentlyContinue"
    for document in (contributing, release_checklist):
        assert cleanup in document
        assert document.index(cleanup) < document.index("python -m build")


def test_readme_local_links_point_to_existing_files() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme):
        if target.startswith(("http://", "https://", "#")):
            continue

        path = target.split("#", 1)[0]
        assert (ROOT / path).exists(), target
