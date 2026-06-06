from importlib.metadata import version
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import novel2script
import novel2script.cli as cli_module
from novel2script.cli import build_parser, main


MANUSCRIPT = """
Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.
"""


def test_package_version_matches_installed_metadata() -> None:
    assert novel2script.__version__ == version("novel2script")


def test_cli_version_option_reports_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"novel2script {novel2script.__version__}"


def test_module_entrypoint_reports_package_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "novel2script", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"novel2script {novel2script.__version__}"
    assert result.stderr == ""


def test_cli_configures_stdout_and_stderr_as_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStream:
        def __init__(self) -> None:
            self.encodings: list[str] = []

        def reconfigure(self, *, encoding: str) -> None:
            self.encodings.append(encoding)

    stdout = FakeStream()
    stderr = FakeStream()
    monkeypatch.setattr(cli_module.sys, "stdout", stdout)
    monkeypatch.setattr(cli_module.sys, "stderr", stderr)

    cli_module._configure_stdio()

    assert stdout.encodings == ["utf-8"]
    assert stderr.encodings == ["utf-8"]


def test_cli_normalizes_blank_model_to_default() -> None:
    assert cli_module._normalize_model("  ") == novel2script.DEFAULT_MODEL
    assert cli_module._normalize_model(" custom-model ") == "custom-model"


def test_cli_sends_normalized_model_to_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDraft:
        def to_dict(self) -> dict[str, object]:
            return {"title": "The Locked Room"}

    class FakeProviderStatus:
        remote = True
        message = ""

    class FakeConversion:
        draft = FakeDraft()
        provider_status = FakeProviderStatus()

    captured: dict[str, str] = {}

    def convert_with_status(
        *,
        text: str,
        title: str | None,
        provider: str,
        model: str,
    ) -> FakeConversion:
        captured["model"] = model
        captured["provider"] = provider
        return FakeConversion()

    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")
    monkeypatch.setattr(cli_module, "convert_with_provider_status", convert_with_status)

    exit_code = main([str(input_path), "--provider", "openai", "--model", "  "])

    assert exit_code == 0
    assert captured == {"model": novel2script.DEFAULT_MODEL, "provider": "openai"}


def test_cli_writes_validated_yaml_to_nested_output_path(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    output_path = tmp_path / "build" / "draft.yaml"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main([str(input_path), "--title", "The Locked Room", "--output", str(output_path), "--validate"])

    assert exit_code == 0
    assert output_path.exists()
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.5.0"
    assert data["title"] == "The Locked Room"
    assert data["source"]["chapter_count"] == 3
    assert [scene["source_chapter"] for act in data["acts"] for scene in act["scenes"]] == [1, 2, 3]


def test_cli_writes_fountain_output(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    output_path = tmp_path / "drafts" / "draft.fountain"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main(
        [
            str(input_path),
            "--title",
            "The Locked Room",
            "--format",
            "fountain",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    fountain = output_path.read_text(encoding="utf-8")
    assert "Title: The Locked Room" in fountain
    assert "// source_chapter: 1" in fountain
    assert "// source_chapter: 3" in fountain
    assert "The hidden name finally connected every clue." in fountain


def test_cli_writes_markdown_revision_brief(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    output_path = tmp_path / "drafts" / "revision.md"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main(
        [
            str(input_path),
            "--title",
            "The Locked Room",
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    markdown = output_path.read_text(encoding="utf-8")
    assert markdown.startswith("# The Locked Room 修订简报\n")
    assert "## Coverage" in markdown
    assert "## Priority Actions" in markdown
    assert "## Scene Index" in markdown


def test_cli_writes_markdown_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main([str(input_path), "--title", "The Locked Room", "--format", "markdown"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "# The Locked Room 修订简报" in captured.out
    assert "## Scorecard" in captured.out


def test_cli_writes_yaml_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main([str(input_path), "--title", "The Locked Room"])

    assert exit_code == 0
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)
    assert captured.err == ""
    assert data["title"] == "The Locked Room"
    assert data["adaptation_report"]["chapter_coverage"]["coverage_ratio"] == 1


def test_cli_warns_when_openai_falls_back_without_api_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main([str(input_path), "--provider", "openai", "--title", "The Locked Room"])

    assert exit_code == 0
    captured = capsys.readouterr()
    data = yaml.safe_load(captured.out)
    assert data["title"] == "The Locked Room"
    assert "novel2script: warning:" in captured.err
    assert "OPENAI_API_KEY is not set; used the local heuristic provider." in captured.err


def test_cli_reports_conversion_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "too-short.txt"
    input_path.write_text("Chapter 1 Opening\nOnly one chapter has body text.", encoding="utf-8")

    exit_code = main([str(input_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error:" in captured.err
    assert "至少需要 3 个包含正文的章节" in captured.err


def test_cli_reports_missing_input_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "missing.txt"

    exit_code = main([str(input_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Input file does not exist:" in captured.err
    assert str(input_path) in captured.err


def test_cli_reports_directory_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(tmp_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Input path is a directory" in captured.err
    assert str(tmp_path) in captured.err


def test_cli_reports_non_utf8_input_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "latin1.txt"
    input_path.write_bytes("caf\xe9".encode("latin-1"))

    exit_code = main([str(input_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Input file must be UTF-8 text:" in captured.err
    assert str(input_path) in captured.err


def test_cli_reports_directory_yaml_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    exit_code = main([str(input_path), "--output", str(output_dir)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Output path is a directory" in captured.err
    assert str(output_dir) in captured.err


def test_cli_validates_output_path_before_conversion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def fail_conversion(*args: object, **kwargs: object) -> object:
        raise AssertionError("conversion should not run for invalid output paths")

    monkeypatch.setattr(cli_module, "convert_with_provider_status", fail_conversion)

    exit_code = main([str(input_path), "--output", str(output_dir)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Output path is a directory" in captured.err


def test_cli_reports_invalid_output_parent_before_conversion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")
    output_parent = tmp_path / "not-a-directory"
    output_parent.write_text("occupied", encoding="utf-8")
    output_path = output_parent / "draft.yaml"

    def fail_conversion(*args: object, **kwargs: object) -> object:
        raise AssertionError("conversion should not run for invalid output paths")

    monkeypatch.setattr(cli_module, "convert_with_provider_status", fail_conversion)

    exit_code = main([str(input_path), "--output", str(output_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Output parent path is not a directory:" in captured.err
    assert str(output_parent) in captured.err


def test_cli_reports_directory_fountain_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = tmp_path / "novel.txt"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    exit_code = main(
        [str(input_path), "--format", "fountain", "--output", str(output_dir)]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "novel2script: error: Output path is a directory" in captured.err
    assert str(output_dir) in captured.err
