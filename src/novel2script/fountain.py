"""Fountain screenplay export helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from novel2script.models import ScriptDraft


def draft_to_fountain(draft: ScriptDraft) -> str:
    data = draft.to_dict()
    lines: list[str] = [
        f"Title: {data['title']}",
        "Credit: Adapted with novel2script",
        "",
        f"Logline: {data['logline']}",
        "",
    ]

    for act in data["acts"]:
        lines.extend([f"# {act['title']}", f"// {act['purpose']}", ""])
        for scene in act["scenes"]:
            lines.extend(_scene_to_fountain(scene))

    return "\n".join(lines).rstrip() + "\n"


def write_fountain(draft: ScriptDraft, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft_to_fountain(draft), encoding="utf-8")


def _scene_to_fountain(scene: dict[str, Any]) -> list[str]:
    heading = _scene_heading(scene)
    lines = [heading, f"// source_chapter: {scene['source_chapter']}", ""]
    for block in scene["blocks"]:
        block_type = block["type"]
        if block_type == "dialogue":
            lines.extend([_character_name(block["character"]), block["text"], ""])
        elif block_type == "transition":
            lines.extend([block["text"].upper(), ""])
        else:
            lines.extend([block["text"], ""])
    return lines


def _scene_heading(scene: dict[str, Any]) -> str:
    location = scene["location"]
    time = scene["time"]
    prefix = "INT./EXT."
    if re.search(r"(街|码头|森林|城门|外)", location):
        prefix = "EXT."
    elif location != "待定场景":
        prefix = "INT."
    return f"{prefix} {location} - {time}"


def _character_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().upper()
