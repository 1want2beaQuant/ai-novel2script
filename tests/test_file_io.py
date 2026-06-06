from pathlib import Path

import pytest

import novel2script.file_io as file_io
from novel2script.file_io import write_text_atomic


def test_write_text_atomic_creates_parent_and_replaces_target(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "draft.yaml"

    write_text_atomic(output_path, "first\n")
    write_text_atomic(output_path, "second\n")

    assert output_path.read_text(encoding="utf-8") == "second\n"
    assert list(output_path.parent.glob(".draft.yaml.*.tmp")) == []


def test_write_text_atomic_cleans_temp_and_preserves_target_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "draft.yaml"
    output_path.write_text("original\n", encoding="utf-8")

    def fail_replace(self: Path, target: Path) -> None:
        raise OSError(f"cannot replace {target}")

    monkeypatch.setattr(file_io.Path, "replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        write_text_atomic(output_path, "new\n")

    assert output_path.read_text(encoding="utf-8") == "original\n"
    assert list(tmp_path.glob(".draft.yaml.*.tmp")) == []
