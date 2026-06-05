import pytest

from scripts.check_release_tag import expected_release_tag, validate_release_tag


def test_expected_release_tag_prefixes_package_version() -> None:
    assert expected_release_tag("0.1.0") == "v0.1.0"


def test_validate_release_tag_accepts_matching_version() -> None:
    validate_release_tag("v0.1.0", "0.1.0")


def test_validate_release_tag_rejects_mismatched_version() -> None:
    with pytest.raises(ValueError, match="does not match package version"):
        validate_release_tag("v0.2.0", "0.1.0")
