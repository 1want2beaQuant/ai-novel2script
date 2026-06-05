"""Typed screenplay data structures used before YAML serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


BlockType = Literal["action", "dialogue", "voice_over", "transition"]


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    body: str


@dataclass(frozen=True)
class ScriptBlock:
    type: BlockType
    text: str
    character: str | None = None
    parenthetical: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"type": self.type}
        if self.character:
            data["character"] = self.character
        if self.parenthetical:
            data["parenthetical"] = self.parenthetical
        data["text"] = self.text
        return data


@dataclass(frozen=True)
class Scene:
    id: str
    title: str
    location: str
    time: str
    summary: str
    source_chapter: int
    characters: list[str] = field(default_factory=list)
    beats: list[str] = field(default_factory=list)
    blocks: list[ScriptBlock] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "location": self.location,
            "time": self.time,
            "summary": self.summary,
            "source_chapter": self.source_chapter,
            "characters": self.characters,
            "beats": self.beats,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(frozen=True)
class Act:
    id: str
    title: str
    purpose: str
    scenes: list[Scene]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "purpose": self.purpose,
            "scenes": [scene.to_dict() for scene in self.scenes],
        }


@dataclass(frozen=True)
class Character:
    name: str
    role: str
    description: str
    first_seen_scene: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "first_seen_scene": self.first_seen_scene,
        }


@dataclass(frozen=True)
class ScriptDraft:
    title: str
    source: dict[str, Any]
    logline: str
    themes: list[str]
    characters: list[Character]
    acts: list[Act]
    story_bible: dict[str, Any]
    adaptation_report: dict[str, Any]
    revision_notes: list[str]
    schema_version: str = "1.2.0"
    language: str = "zh-CN"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "language": self.language,
            "generated_at": self.generated_at,
            "source": self.source,
            "logline": self.logline,
            "themes": self.themes,
            "characters": [character.to_dict() for character in self.characters],
            "acts": [act.to_dict() for act in self.acts],
            "story_bible": self.story_bible,
            "adaptation_report": self.adaptation_report,
            "revision_notes": self.revision_notes,
        }
