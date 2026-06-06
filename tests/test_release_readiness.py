from pathlib import Path

import pytest

from scripts import check_release_readiness as readiness


def test_release_checks_include_core_local_release_gates() -> None:
    checks = readiness.release_checks(
        python="python",
        release_tag="v0.1.0",
        pytest_basetemp=".pytest-tmp-release-readiness",
        cli_console="bin/novel2script",
        web_console="bin/novel2script-web",
        include_audit=True,
        include_build=True,
        include_web_smoke=True,
    )
    labels = [check.label for check in checks]
    commands = [" ".join(check.command) for check in checks]

    assert labels[:3] == ["pytest", "ruff", "dependency audit"]
    assert checks[0].command == [
        "python",
        "-m",
        "pytest",
        "--basetemp",
        ".pytest-tmp-release-readiness",
    ]
    assert ["bin/novel2script", "--version"] in [check.command for check in checks]
    assert ["bin/novel2script-web", "--version"] in [check.command for check in checks]
    assert "release tag matches installed version" in labels
    assert "Web server smoke" in labels
    assert "YAML CLI smoke" in labels
    assert "Fountain CLI smoke" in labels
    assert "Markdown CLI smoke" in labels
    assert "build distributions" in labels
    assert "twine check distributions" in labels
    assert "schema copies match" in labels
    assert any("--output" in command and "release-readiness.yaml" in command for command in commands)
    assert any("--format fountain" in command for command in commands)
    assert any("--format markdown" in command for command in commands)


def test_release_checks_support_fast_local_iteration_skips() -> None:
    checks = readiness.release_checks(
        python="python",
        release_tag="v0.1.0",
        pytest_basetemp=".pytest-tmp-release-readiness",
        cli_console="novel2script",
        web_console="novel2script-web",
        include_audit=False,
        include_build=False,
        include_web_smoke=False,
    )
    labels = [check.label for check in checks]

    assert "dependency audit" not in labels
    assert "build distributions" not in labels
    assert "twine check distributions" not in labels
    assert "Web server smoke" not in labels
    assert "schema copies match" in labels


def test_dry_run_prints_plan_without_executing_checks(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = readiness.main(
        ["--dry-run", "--skip-audit", "--skip-build", "--skip-web-smoke", "--tag", "v0.1.0"]
    )

    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Release readiness dry run:" in captured
    assert "--basetemp" in captured
    assert ".pytest-tmp-release-readiness" in captured
    assert "YAML CLI smoke" in captured
    assert "Markdown CLI smoke" in captured
    assert "Dry run only; no checks were executed." in captured


def test_pytest_basetemp_must_stay_inside_workspace() -> None:
    with pytest.raises(RuntimeError, match="--pytest-basetemp"):
        readiness.main(
            [
                "--dry-run",
                "--skip-audit",
                "--skip-build",
                "--skip-web-smoke",
                "--pytest-basetemp",
                str(Path.home()),
            ]
        )


def test_console_script_resolves_from_installed_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "Scripts" / "novel2script.exe"
    script.parent.mkdir()
    script.write_text("", encoding="utf-8")
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()

    class FakeDistribution:
        files = [Path("..") / "Scripts" / "novel2script.exe"]

        @staticmethod
        def locate_file(file: Path) -> Path:
            return site_packages / file

    monkeypatch.setattr(readiness.shutil, "which", lambda _: None)
    monkeypatch.setattr(readiness.sysconfig, "get_path", lambda _: str(tmp_path / "unused"))
    monkeypatch.setattr(readiness, "distribution", lambda _: FakeDistribution())

    assert readiness._resolve_console_script("novel2script", strict=True) == str(script.resolve())


def test_missing_console_script_returns_name_for_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(readiness.shutil, "which", lambda _: None)
    monkeypatch.setattr(readiness.sysconfig, "get_path", lambda _: "")
    monkeypatch.setattr(readiness, "distribution", lambda _: None)

    assert readiness._resolve_console_script("novel2script", strict=False) == "novel2script"


def test_missing_console_script_fails_full_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(readiness.shutil, "which", lambda _: None)
    monkeypatch.setattr(readiness.sysconfig, "get_path", lambda _: "")
    monkeypatch.setattr(readiness, "distribution", lambda _: None)

    with pytest.raises(RuntimeError, match="Console script 'novel2script'"):
        readiness._resolve_console_script("novel2script", strict=True)


def test_schema_only_checks_synchronized_schema_copies(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = readiness.main(["--schema-only"])

    assert exit_code == 0
    assert "Schema copies match." in capsys.readouterr().out


def test_twine_check_requires_built_distributions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(readiness, "DIST_DIR", tmp_path)

    with pytest.raises(RuntimeError, match="No built distributions"):
        readiness._twine_check_distributions("python")
