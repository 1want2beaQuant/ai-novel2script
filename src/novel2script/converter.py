"""High-level conversion entry points."""

from __future__ import annotations

from novel2script.chapter_parser import parse_chapters
from novel2script.heuristics import build_script_from_chapters
from novel2script.models import ScriptDraft


def convert_text_to_script(text: str, title: str | None = None) -> ScriptDraft:
    """Convert a novel manuscript into a screenplay draft."""

    chapters = parse_chapters(text)
    return build_script_from_chapters(chapters, title=title)
