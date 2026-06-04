"""Local adaptation heuristics used when no external AI provider is configured."""

from __future__ import annotations

import re
from collections import Counter

from novel2script.models import Act, Chapter, Character, Scene, ScriptBlock, ScriptDraft


SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
DIALOGUE_RE = re.compile(r"(?P<speaker>[\u4e00-\u9fffA-Za-z0-9_·]{1,16})[：:]\s*(?P<line>.+)")
LOCATION_HINT_RE = re.compile(r"(?:在|到|回到|走进|来到)(?P<place>[^，。！？!?；;\n]{2,16})")
NAME_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")
STOP_NAMES = {
    "他们",
    "她们",
    "我们",
    "你们",
    "这里",
    "那里",
    "时候",
    "声音",
    "城市",
    "屋里",
    "窗外",
    "夜色",
    "清晨",
    "突然",
}


def build_script_from_chapters(chapters: list[Chapter], title: str | None = None) -> ScriptDraft:
    """Convert parsed chapters into a structured screenplay draft."""

    inferred_title = title or _derive_title(chapters)
    scenes = [_chapter_to_scene(chapter) for chapter in chapters]
    characters = _build_characters(scenes)
    character_names = [character.name for character in characters]
    acts = _group_scenes_into_acts(scenes)

    return ScriptDraft(
        title=inferred_title,
        source={
            "type": "novel",
            "chapter_count": len(chapters),
            "chapters": [{"index": chapter.index, "title": chapter.title} for chapter in chapters],
        },
        logline=_build_logline(inferred_title, scenes, character_names),
        themes=_infer_themes(chapters),
        characters=characters,
        acts=acts,
        revision_notes=[
            "本稿由本地启发式改编引擎生成，建议作者重点复核人物动机和对白语气。",
            "每个场景保留 source_chapter，便于回到原小说章节继续打磨。",
        ],
    )


def _chapter_to_scene(chapter: Chapter) -> Scene:
    paragraphs = _paragraphs(chapter.body)
    blocks: list[ScriptBlock] = []
    beats: list[str] = []
    characters: list[str] = []

    for paragraph in paragraphs:
        block = _paragraph_to_block(paragraph)
        blocks.append(block)
        if block.character and block.character not in characters:
            characters.append(block.character)
        if len(beats) < 4:
            beats.append(_shorten(paragraph, 38))

    if not blocks:
        blocks.append(ScriptBlock(type="action", text=_shorten(chapter.body, 90)))

    if blocks[-1].type != "transition":
        blocks.append(ScriptBlock(type="transition", text="切至下一场。"))

    return Scene(
        id=f"S{chapter.index:03d}",
        title=chapter.title,
        location=_infer_location(chapter.body),
        time=_infer_time(chapter.body),
        summary=_summarize(chapter.body),
        source_chapter=chapter.index,
        characters=characters or _guess_names(chapter.body, limit=3),
        beats=beats,
        blocks=blocks,
    )


def _paragraph_to_block(paragraph: str) -> ScriptBlock:
    dialogue = DIALOGUE_RE.match(paragraph)
    if dialogue:
        speaker = _normalize_speaker(dialogue.group("speaker"))
        return ScriptBlock(
            type="dialogue",
            character=speaker,
            text=_strip_quotes(dialogue.group("line")),
        )

    if paragraph.startswith(("旁白：", "旁白:")):
        return ScriptBlock(type="voice_over", text=paragraph.split(":", 1)[-1].strip())

    return ScriptBlock(type="action", text=_rewrite_action(paragraph))


def _group_scenes_into_acts(scenes: list[Scene]) -> list[Act]:
    act_count = 3 if len(scenes) >= 6 else min(2, len(scenes))
    if len(scenes) == 3:
        act_count = 3

    acts: list[Act] = []
    for act_index in range(act_count):
        start = round(act_index * len(scenes) / act_count)
        end = round((act_index + 1) * len(scenes) / act_count)
        chunk = scenes[start:end]
        if not chunk:
            continue
        acts.append(
            Act(
                id=f"A{act_index + 1}",
                title=["开端", "发展", "结局"][act_index] if act_count == 3 else f"第 {act_index + 1} 幕",
                purpose=_act_purpose(act_index, act_count),
                scenes=chunk,
            )
        )
    return acts


def _build_characters(scenes: list[Scene]) -> list[Character]:
    first_seen: dict[str, str] = {}
    counter: Counter[str] = Counter()
    for scene in scenes:
        for name in scene.characters:
            if name in STOP_NAMES:
                continue
            counter[name] += 1
            first_seen.setdefault(name, scene.id)

    if not counter:
        return [
            Character(
                name="主角",
                role="protagonist",
                description="需要作者在后续修订中补充姓名、目标与关系。",
                first_seen_scene=scenes[0].id,
            )
        ]

    characters: list[Character] = []
    for idx, (name, _) in enumerate(counter.most_common(8)):
        characters.append(
            Character(
                name=name,
                role="protagonist" if idx == 0 else "supporting",
                description=f"在 {first_seen[name]} 首次出现，参与推动主要情节。",
                first_seen_scene=first_seen[name],
            )
        )
    return characters


def _build_logline(title: str, scenes: list[Scene], character_names: list[str]) -> str:
    lead = character_names[0] if character_names else "主角"
    first_goal = scenes[0].summary if scenes else "面对新的命运转折"
    last_turn = scenes[-1].summary if scenes else "完成关键选择"
    return f"《{title}》讲述{lead}在{first_goal}后，被迫面对{last_turn}的故事。"


def _infer_themes(chapters: list[Chapter]) -> list[str]:
    joined = "\n".join(chapter.body for chapter in chapters)
    candidates = [
        ("亲情", ("母亲", "父亲", "家", "妹妹", "哥哥")),
        ("悬疑", ("线索", "秘密", "调查", "真相", "失踪")),
        ("成长", ("选择", "决定", "离开", "改变", "未来")),
        ("爱情", ("喜欢", "爱", "拥抱", "婚", "心跳")),
        ("冒险", ("出发", "森林", "远方", "逃", "追")),
        ("权力", ("王", "公司", "命令", "权", "会议")),
    ]
    themes = [theme for theme, words in candidates if any(word in joined for word in words)]
    return themes[:4] or ["人物选择", "命运转折"]


def _derive_title(chapters: list[Chapter]) -> str:
    first = chapters[0].title
    return re.sub(r"^第\s*[\w一二三四五六七八九十百千万零〇两]+\s*[章节回幕卷]\s*", "", first).strip() or "未命名剧本"


def _paragraphs(text: str) -> list[str]:
    raw_parts = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    if len(raw_parts) >= 2:
        return raw_parts[:10]
    sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(text) if match.group(0).strip()]
    return sentences[:10]


def _summarize(text: str) -> str:
    sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(text) if match.group(0).strip()]
    if not sentences:
        return _shorten(text, 60)
    return _shorten("".join(sentences[:2]), 80)


def _rewrite_action(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return _shorten(compact, 120)


def _infer_location(text: str) -> str:
    for place in ("书房", "旧宅", "码头", "街口", "屋里", "客厅", "学校", "公司", "医院", "城门", "森林"):
        if place in text:
            return place

    match = LOCATION_HINT_RE.search(text)
    if match:
        place = match.group("place")
        place = re.split(r"(发现|找到|看见|听见|只剩|停下|拿出|推开|穿过)", place, maxsplit=1)[0]
        return place.strip(" 的里中外前后上下") or "待定场景"
    return "待定场景"


def _infer_time(text: str) -> str:
    for label, hints in (
        ("夜", ("夜", "深夜", "月光", "凌晨")),
        ("晨", ("清晨", "早晨", "黎明")),
        ("日", ("午后", "阳光", "白天")),
        ("傍晚", ("黄昏", "傍晚", "晚霞")),
    ):
        if any(hint in text for hint in hints):
            return label
    return "未定"


def _guess_names(text: str, limit: int) -> list[str]:
    names = [name for name in NAME_RE.findall(text) if name not in STOP_NAMES]
    counts = Counter(names)
    return [name for name, _ in counts.most_common(limit)]


def _strip_quotes(text: str) -> str:
    return text.strip().strip("“”\"'")


def _normalize_speaker(text: str) -> str:
    speaker = text.strip()
    for suffix in ("低声说", "轻声说", "说道", "说", "问", "喊", "道", "答"):
        if speaker.endswith(suffix) and len(speaker) > len(suffix):
            return speaker[: -len(suffix)]
    return speaker


def _shorten(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _act_purpose(index: int, total: int) -> str:
    if total == 3:
        return ["建立人物、目标与改编世界。", "推进冲突并制造不可逆转折。", "收束选择，形成可继续打磨的结局。"][index]
    return "承接小说章节，整理为可拍摄的连续场景。"
