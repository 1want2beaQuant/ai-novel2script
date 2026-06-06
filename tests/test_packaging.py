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
    assert project["scripts"]["novel2script-web"] == "novel2script.web:main"
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
    assert pyproject["tool"]["setuptools"]["package-data"]["novel2script.web"] == [
        "static/*.html",
        "static/*.css",
        "static/*.js",
    ]
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
        "recursive-include src/novel2script/web/static *.html *.css *.js",
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


def test_local_web_workbench_is_documented_for_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "novel2script-web --host 127.0.0.1 --port 8765" in readme
    assert "python -m novel2script.web --host 127.0.0.1 --port 8765 --no-open" in readme
    assert "默认本地模式不会把手稿发送到外部服务" in readme
    assert "--allow-remote" in readme
    assert "预检章节识别和每章素材规模" in readme
    assert "显示每章字数，并标记正文偏短的章节" in readme
    assert "短章提示不会阻止满足 3 章要求的手稿继续转换" in readme
    assert "章节到场景映射" in readme
    assert "场景块预览" in readme
    assert "每场的剧本块统计和动作/对白/旁白/转场预览" in readme
    assert "coverage 分项评分" in readme
    assert "下一轮修订重点" in readme
    assert "聚合优先级、分项分数和评分理由" in readme
    assert "结构节拍" in readme
    assert "优先修订动作" in readme
    assert "人物连续性" in readme
    assert "地点资产" in readme
    assert "道具/线索" in readme
    assert "待解问题" in readme
    assert "实际处理方式" in readme
    assert "Draft JSON" in readme
    assert "Summary JSON" in readme
    assert "Markdown 修订简报" in readme
    assert "结果区可在 YAML、Fountain、Markdown 修订简报、Draft JSON 和 Summary JSON 之间切换" in readme
    assert "打包下载会生成包含全部导出文件的 zip" in readme
    assert "自动保存当前手稿、片名、输出格式、处理模式、模型和 Schema 开关到本机浏览器" in readme
    assert "刷新页面后自动恢复" in readme
    assert "清空按钮会移除当前手稿、标题、生成结果、诊断状态、选中文件引用和远程确认状态" in readme
    assert "Web 页面会在开始远程转换前按当前手稿、片名和模型要求确认" in readme
    assert "Web 工作台会在处理模式卡片显示“本地回退”" in readme
    assert "转换 API 只接受 JSON 请求" in readme
    assert "Local browser workbench" in changelog
    assert "Markdown revision brief" in changelog
    assert "Local Web adaptation inspector" in changelog
    assert "next revision focus" in changelog
    assert "priority, score, note, and coverage rationale" in changelog
    assert "chapter-to-scene mapping" in changelog
    assert "scene block counts" in changelog
    assert "action/dialogue/voice-over/transition previews" in changelog
    assert "Story Bible panels" in changelog
    assert "four-step workflow progress strip" in changelog
    assert "per-chapter manuscript size" in changelog
    assert "non-blocking short-chapter warnings" in changelog
    assert "inline remote confirmation panel" in changelog
    assert "pending confirmations are invalidated" in changelog
