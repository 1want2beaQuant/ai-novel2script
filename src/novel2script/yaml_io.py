"""YAML serialization helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from novel2script.file_io import write_text_atomic
from novel2script.models import ScriptDraft


def draft_to_yaml(draft: ScriptDraft) -> str:
    """Serialize a screenplay draft as stable, human-editable YAML."""

    return yaml.safe_dump(
        draft.to_dict(),
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )


def write_yaml(draft: ScriptDraft, output_path: Path) -> None:
    write_text_atomic(output_path, draft_to_yaml(draft))


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} 不是有效的 YAML 对象。")
    return loaded
