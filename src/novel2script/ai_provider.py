"""Optional OpenAI-compatible enhancement layer."""

from __future__ import annotations

import json
import os
from typing import Any

from novel2script.chapter_parser import parse_chapters
from novel2script.converter import convert_text_to_script
from novel2script.models import ScriptDraft
from novel2script.schema import validate_script


SYSTEM_PROMPT = """你是专业编剧助理。请把小说改编为可编辑剧本 YAML 数据。
必须保持 JSON 对象字段与用户提供的 baseline 完全兼容，不要输出 Markdown。"""


def convert_with_optional_ai(
    text: str,
    title: str | None,
    provider: str,
    model: str,
) -> ScriptDraft:
    """Use AI enhancement when requested and configured, otherwise return local draft."""

    local_draft = convert_text_to_script(text, title=title)
    if provider != "openai" or not os.environ.get("OPENAI_API_KEY"):
        return local_draft

    try:
        enhanced = _enhance_with_openai(text=text, baseline=local_draft.to_dict(), model=model)
        validate_script(enhanced)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"OpenAI enhancement failed: {exc}") from exc
    return _dict_to_draft(enhanced, fallback=local_draft)


def _enhance_with_openai(text: str, baseline: dict[str, Any], model: str) -> dict[str, Any]:
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise ValueError(
            "OpenAI provider requires the optional AI dependency. "
            "Install it with: python -m pip install \"novel2script[ai]\""
        ) from exc

    chapters = parse_chapters(text)
    chapter_digest = "\n\n".join(
        f"{chapter.title}\n{chapter.body[:1600]}" for chapter in chapters[:8]
    )
    client = OpenAI()
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "请在保持字段结构不变的前提下，增强下面 baseline 剧本 JSON："
                    "补强 logline、人物描述、场景 summary、beats 和 blocks 文本。"
                    "\n\n小说章节摘要：\n"
                    f"{chapter_digest}\n\nbaseline JSON:\n{json.dumps(baseline, ensure_ascii=False)}"
                ),
            },
        ],
    )
    content = response.output_text.strip()
    return _parse_response_json(content)


def _parse_response_json(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    loaded = json.loads(stripped)
    if not isinstance(loaded, dict):
        raise ValueError("OpenAI enhancement must return a JSON object.")
    return loaded


def _dict_to_draft(data: dict[str, Any], fallback: ScriptDraft) -> ScriptDraft:
    """Keep AI integration isolated; schema validation will verify the final dict later.

    Rehydrating every nested dataclass would add brittle duplication. Instead, we attach a small
    adapter with the same public `to_dict` contract as `ScriptDraft`.
    """

    if not isinstance(data, dict):
        return fallback

    class EnhancedDraft:
        def to_dict(self) -> dict[str, Any]:
            return data

    return EnhancedDraft()  # type: ignore[return-value]
