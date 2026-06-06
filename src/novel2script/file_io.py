"""Filesystem helpers used by CLI exporters."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def write_text_atomic(output_path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write text through a same-directory temp file before replacing the target."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            delete=False,
            dir=output_path.parent,
            encoding=encoding,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(output_path)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
        raise
