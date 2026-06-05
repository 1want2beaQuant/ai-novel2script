from importlib.metadata import version

import pytest

import novel2script
from novel2script.cli import build_parser


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
