from importlib.metadata import version
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import novel2script
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


def test_cli_writes_validated_yaml_to_nested_output_path(tmp_path: Path) -> None:
    input_path = tmp_path / "novel.txt"
    output_path = tmp_path / "build" / "draft.yaml"
    input_path.write_text(MANUSCRIPT, encoding="utf-8")

    exit_code = main([str(input_path), "--title", "The Locked Room", "--output", str(output_path), "--validate"])

    assert exit_code == 0
    assert output_path.exists()
    data = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.4.0"
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
