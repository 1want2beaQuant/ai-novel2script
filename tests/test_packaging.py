from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import sys
from typing import Any

import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


def load_pyproject() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def load_workflow(name: str) -> dict[str, Any]:
    with (ROOT / ".github" / "workflows" / name).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    if True in data and "on" not in data:
        data["on"] = data[True]
    return data


def test_python_support_metadata_tracks_ci_matrix() -> None:
    pyproject = load_pyproject()
    project = pyproject["project"]
    ci_workflow = load_workflow("ci.yml")

    supported_versions = ci_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    python_classifiers = [
        classifier.removeprefix("Programming Language :: Python :: ")
        for classifier in project["classifiers"]
        if classifier.startswith("Programming Language :: Python :: 3.")
    ]

    assert project["requires-python"] == f">={supported_versions[0]}"
    assert python_classifiers == supported_versions


def test_distribution_metadata_exposes_publishable_project_details() -> None:
    pyproject = load_pyproject()
    project = pyproject["project"]

    assert project["name"] == "novel2script"
    assert project["version"] == version("novel2script")
    assert project["readme"] == "README.md"
    assert project["license"] == "MIT"
    assert project["description"]
    assert set(project["keywords"]) >= {
        "novel",
        "screenplay",
        "fountain",
        "yaml",
        "adaptation",
    }
    assert project["dependencies"] == [
        "jsonschema>=4.22.0",
        "PyYAML>=6.0.1",
    ]
    assert project["scripts"]["novel2script"] == "novel2script.cli:main"
    assert project["urls"] == {
        "Homepage": "https://github.com/1want2beaQuant/ai-novel2script",
        "Repository": "https://github.com/1want2beaQuant/ai-novel2script",
        "Documentation": "https://github.com/1want2beaQuant/ai-novel2script#readme",
        "Issues": "https://github.com/1want2beaQuant/ai-novel2script/issues",
    }


def test_package_data_and_manifest_include_release_assets() -> None:
    pyproject = load_pyproject()
    manifest_entries = {
        line.strip()
        for line in (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    assert pyproject["tool"]["setuptools"]["package-data"]["novel2script"] == ["schemas/*.json"]
    assert {
        "include LICENSE",
        "include README.md",
        "include CHANGELOG.md",
        "include CODE_OF_CONDUCT.md",
        "include CONTRIBUTING.md",
        "include PRIVACY.md",
        "include SECURITY.md",
        "include schemas/script.schema.json",
        "recursive-include docs *.md",
        "recursive-include examples *.txt",
        "recursive-include scripts *.py",
    } <= manifest_entries


def test_openai_validation_behavior_is_documented_for_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "返回内容会按 JSON 对象解析" in readme
    assert "fenced JSON" in readme
    assert "内置 Schema 校验" in readme
    assert "OpenAI-compatible enhancement responses are parsed as JSON objects" in changelog
    assert "tolerate fenced JSON blocks" in changelog
    assert "validated against the bundled schema" in changelog
