"""Markdown revision brief export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from novel2script.file_io import write_text_atomic
from novel2script.models import ScriptDraft


def draft_to_markdown(draft: ScriptDraft) -> str:
    """Render a concise human-readable revision brief for a screenplay draft."""

    data = draft.to_dict()
    coverage = _as_dict(data.get("coverage_report"))
    adaptation = _as_dict(data.get("adaptation_report"))
    chapter_coverage = _as_dict(adaptation.get("chapter_coverage"))
    metrics = _as_dict(adaptation.get("metrics"))
    structure = _as_dict(data.get("structure_map"))
    story_bible = _as_dict(data.get("story_bible"))

    lines = [
        f"# {data.get('title', '未命名剧本')} 修订简报",
        "",
        f"**Logline:** {data.get('logline', '')}",
        "",
        "## Coverage",
        "",
        f"- Verdict: {coverage.get('verdict', 'draft')}",
        f"- Overall score: {coverage.get('overall_score', 0)}",
        f"- Chapter coverage: {chapter_coverage.get('adapted_chapters', 0)}/"
        f"{chapter_coverage.get('total_chapters', 0)} "
        f"({round(float(chapter_coverage.get('coverage_ratio', 0)) * 100)}%)",
        f"- Scenes: {metrics.get('scene_count', 0)}",
        f"- Dialogue blocks: {metrics.get('dialogue_blocks', 0)}",
        "",
        "## Scorecard",
        "",
    ]
    for score in _dict_list(coverage.get("scores")):
        lines.append(
            f"- **{score.get('area', 'unknown')}**: {score.get('score', 0)} - "
            f"{score.get('rationale', '')}"
        )

    _append_section(lines, "Strengths", _string_list(coverage.get("strengths")))
    _append_section(lines, "Weaknesses", _string_list(coverage.get("weaknesses")))

    lines.extend(["", "## Priority Actions", ""])
    for item in _dict_list(coverage.get("action_items")):
        lines.append(
            f"- **{item.get('priority', 'medium')} / {item.get('area', 'revision')}**: "
            f"{item.get('note', '')}"
        )

    lines.extend(["", "## Structure Beats", ""])
    for beat in _dict_list(structure.get("beats")):
        lines.append(
            f"- **{beat.get('label', beat.get('id', 'beat'))}** -> "
            f"{beat.get('scene_id', 'S???')} / chapter {beat.get('source_chapter', '?')}: "
            f"{beat.get('revision_hint', beat.get('summary', ''))}"
        )

    lines.extend(["", "## Scene Index", ""])
    for scene in _scenes(data):
        characters = ", ".join(_string_list(scene.get("characters"))) or "待补充"
        lines.append(
            f"- **{scene.get('id', 'S???')}** chapter {scene.get('source_chapter', '?')} - "
            f"{scene.get('title', '')} / {scene.get('location', '待定场景')} / {characters}"
        )
        lines.append(f"  - Objective: {scene.get('objective', '待补充')}")
        lines.append(f"  - Conflict: {scene.get('conflict', '待补充')}")
        lines.append(f"  - Turning point: {scene.get('turning_point', '待补充')}")

    _append_section(lines, "Quality Flags", _string_list(adaptation.get("quality_flags")))
    _append_section(lines, "Revision Checklist", _string_list(adaptation.get("revision_checklist")))

    open_questions = _string_list(story_bible.get("open_questions"))
    _append_section(lines, "Open Questions", open_questions)

    return "\n".join(lines).rstrip() + "\n"


def write_markdown(draft: ScriptDraft, output_path: Path) -> None:
    write_text_atomic(output_path, draft_to_markdown(draft))


def _append_section(lines: list[str], title: str, items: list[str]) -> None:
    lines.extend(["", f"## {title}", ""])
    for item in items or ["待补充。"]:
        lines.append(f"- {item}")


def _scenes(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        scene
        for act in _dict_list(data.get("acts"))
        for scene in _dict_list(act.get("scenes"))
    ]


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
