"""Optional OpenAI-compatible enhancement layer."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from novel2script.chapter_parser import parse_chapters
from novel2script.converter import convert_text_to_script
from novel2script.models import ScriptDraft
from novel2script.schema import validate_script


SYSTEM_PROMPT = """你是专业编剧助理。请把小说改编为可编辑剧本 YAML 数据。
必须保持 JSON 对象字段与用户提供的 baseline 完全兼容，不要输出 Markdown。"""


@dataclass(frozen=True)
class ProviderStatus:
    requested: str
    actual: str
    model: str
    remote: bool
    reason: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "actual": self.actual,
            "model": self.model,
            "remote": self.remote,
            "reason": self.reason,
            "message": self.message,
        }


@dataclass(frozen=True)
class ConversionResult:
    draft: ScriptDraft
    provider_status: ProviderStatus


def convert_with_optional_ai(
    text: str,
    title: str | None,
    provider: str,
    model: str,
) -> ScriptDraft:
    """Use AI enhancement when requested and configured, otherwise return local draft."""

    return convert_with_provider_status(
        text=text,
        title=title,
        provider=provider,
        model=model,
    ).draft


def convert_with_provider_status(
    text: str,
    title: str | None,
    provider: str,
    model: str,
) -> ConversionResult:
    """Convert text and report which provider actually produced the final draft."""

    local_draft = convert_text_to_script(text, title=title)
    if provider != "openai":
        return ConversionResult(
            draft=local_draft,
            provider_status=ProviderStatus(
                requested=provider,
                actual="local",
                model=model,
                remote=False,
                reason="local_selected",
                message="Used the local heuristic provider.",
            ),
        )

    if not os.environ.get("OPENAI_API_KEY"):
        return ConversionResult(
            draft=local_draft,
            provider_status=ProviderStatus(
                requested=provider,
                actual="local",
                model=model,
                remote=False,
                reason="missing_api_key",
                message="OPENAI_API_KEY is not set; used the local heuristic provider.",
            ),
        )

    try:
        enhanced = _enhance_with_openai(text=text, baseline=local_draft.to_dict(), model=model)
        validate_script(enhanced)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"OpenAI enhancement failed: {exc}") from exc
    return ConversionResult(
        draft=_dict_to_draft(enhanced, fallback=local_draft),
        provider_status=ProviderStatus(
            requested=provider,
            actual="openai",
            model=model,
            remote=True,
            reason="openai_enhanced",
            message="Used OpenAI-compatible remote enhancement.",
        ),
    )


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
    fenced = re.search(r"```(?:\s*json)?\s*\n(?P<body>.*?)\n```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        stripped = fenced.group("body").strip()

    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI enhancement must return valid JSON.") from exc
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
