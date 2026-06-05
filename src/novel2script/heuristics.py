"""Local adaptation heuristics used when no external AI provider is configured."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

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
    logline = _build_logline(inferred_title, scenes, character_names)
    themes = _infer_themes(chapters)
    acts = _group_scenes_into_acts(scenes)
    structure_map = _build_structure_map(scenes)
    story_bible = _build_story_bible(chapters, scenes, characters)
    adaptation_report = _build_adaptation_report(chapters, scenes)

    return ScriptDraft(
        title=inferred_title,
        source={
            "type": "novel",
            "chapter_count": len(chapters),
            "chapters": [{"index": chapter.index, "title": chapter.title} for chapter in chapters],
        },
        logline=logline,
        themes=themes,
        characters=characters,
        acts=acts,
        structure_map=structure_map,
        story_bible=story_bible,
        adaptation_report=adaptation_report,
        coverage_report=_build_coverage_report(
            logline=logline,
            themes=themes,
            scenes=scenes,
            characters=characters,
            structure_map=structure_map,
            story_bible=story_bible,
            adaptation_report=adaptation_report,
        ),
        revision_notes=[
            "本稿由本地启发式改编引擎生成，建议作者重点复核人物动机和对白语气。",
            "每个场景保留 source_chapter，便于回到原小说章节继续打磨。",
            "structure_map 标记开端、诱发事件、中点、高潮和结局，便于检查三幕结构。",
            "story_bible 汇总人物、地点、道具/线索和待解问题，可作为后续改编资料库。",
            "adaptation_report 汇总章节覆盖、场景映射和质量风险，可作为下一轮修订清单。",
            "coverage_report 按专业 coverage 思路给出分项评分、强弱项和优先修订动作。",
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
    if paragraph.startswith(("旁白：", "旁白:")):
        return ScriptBlock(type="voice_over", text=_strip_voice_over_prefix(paragraph))

    dialogue = DIALOGUE_RE.match(paragraph)
    if dialogue:
        speaker = _normalize_speaker(dialogue.group("speaker"))
        return ScriptBlock(
            type="dialogue",
            character=speaker,
            text=_strip_quotes(dialogue.group("line")),
        )

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


def _build_structure_map(scenes: list[Scene]) -> dict[str, object]:
    beat_specs = [
        ("opening_image", "开场意象", 0, "建立主角处境、基调和世界入口。"),
        ("inciting_incident", "诱发事件", 0.25, "确认打破日常秩序的事件是否足够明确。"),
        ("midpoint", "中点转折", 0.5, "检查冲突是否升级，主角是否获得新认知。"),
        ("climax", "高潮", 0.8, "确认最终对抗或关键选择是否集中呈现。"),
        ("resolution", "结局", 1, "检查主要悬念是否回收，并留下可修订余地。"),
    ]
    beats = []
    for beat_id, label, ratio, purpose in beat_specs:
        scene = _pick_scene_for_ratio(scenes, ratio)
        beats.append(
            {
                "id": beat_id,
                "label": label,
                "scene_id": scene.id,
                "source_chapter": scene.source_chapter,
                "summary": scene.summary,
                "purpose": purpose,
                "revision_hint": _structure_revision_hint(beat_id, scene),
            }
        )
    return {
        "model": "five_point_screenplay_map",
        "beats": beats,
        "diagnostics": _structure_diagnostics(beats, len(scenes)),
    }


def _pick_scene_for_ratio(scenes: list[Scene], ratio: float) -> Scene:
    if ratio >= 1:
        return scenes[-1]
    index = round((len(scenes) - 1) * ratio)
    return scenes[max(0, min(index, len(scenes) - 1))]


def _structure_revision_hint(beat_id: str, scene: Scene) -> str:
    hints = {
        "opening_image": "强化第一场的视觉动作，减少背景说明。",
        "inciting_incident": "让该场明确出现迫使主角行动的变化。",
        "midpoint": "补足反转、发现或关系变化，避免只是过场。",
        "climax": "集中主要冲突，让主角做出不可逆选择。",
        "resolution": "回收关键线索，并标记仍需续写的余味。",
    }
    return f"{hints[beat_id]} 当前映射到 {scene.id}。"


def _structure_diagnostics(beats: list[dict[str, object]], scene_count: int) -> list[str]:
    diagnostics = []
    unique_scene_count = len({beat["scene_id"] for beat in beats})
    if unique_scene_count < len(beats):
        diagnostics.append("多个关键节拍落在同一场，建议扩写或重排章节以增强结构层次。")
    if scene_count < 5:
        diagnostics.append("场景数量少于五个，五点结构中的部分节拍会共用场景。")
    return diagnostics or ["关键节拍已分布到不同场景，可继续细化每个节拍的冲突强度。"]


def _build_story_bible(
    chapters: list[Chapter],
    scenes: list[Scene],
    characters: list[Character],
) -> dict[str, object]:
    return {
        "characters": [
            {
                "name": character.name,
                "role": character.role,
                "first_seen_scene": character.first_seen_scene,
                "continuity_note": f"复核{character.name}在各章节中的目标、关系和称呼是否一致。",
            }
            for character in characters
        ],
        "locations": _story_locations(scenes),
        "props": _story_props(chapters),
        "open_questions": _story_open_questions(chapters, scenes),
    }


def _story_locations(scenes: list[Scene]) -> list[dict[str, object]]:
    locations: dict[str, list[str]] = {}
    for scene in scenes:
        locations.setdefault(scene.location, []).append(scene.id)
    return [
        {
            "name": location,
            "scene_ids": scene_ids,
            "note": "待补充空间特征和可拍摄视觉元素。" if location == "待定场景" else "可作为场景调度和美术设定线索。",
        }
        for location, scene_ids in locations.items()
    ]


def _story_props(chapters: list[Chapter]) -> list[dict[str, object]]:
    prop_keywords = ("信", "照片", "录音笔", "钥匙", "钟", "线索", "日记", "戒指", "地图", "刀")
    props: dict[str, set[int]] = {}
    for chapter in chapters:
        for keyword in prop_keywords:
            if keyword in chapter.body:
                props.setdefault(keyword, set()).add(chapter.index)
    return [
        {
            "name": name,
            "source_chapters": sorted(chapter_indexes),
            "dramatic_function": "承载线索、关系或转折，需要在后续剧本中保持出现和回收。",
        }
        for name, chapter_indexes in props.items()
    ]


def _story_open_questions(chapters: list[Chapter], scenes: list[Scene]) -> list[str]:
    questions = [
        "主角在每一幕的外在目标和内在需求是否已经明确？",
        "关键道具或线索是否在结尾前完成回收？",
    ]
    if any(scene.location == "待定场景" for scene in scenes):
        questions.append("仍为待定的场景地点是否会影响视觉化改写？")
    if not any("真相" in chapter.body or "秘密" in chapter.body for chapter in chapters):
        questions.append("故事核心秘密或最终真相是否需要在剧本版中显性化？")
    return questions


def _build_adaptation_report(chapters: list[Chapter], scenes: list[Scene]) -> dict[str, object]:
    covered_chapters = sorted({scene.source_chapter for scene in scenes})
    missing_chapters = [
        chapter.index for chapter in chapters if chapter.index not in set(covered_chapters)
    ]
    action_blocks = sum(1 for scene in scenes for block in scene.blocks if block.type == "action")
    dialogue_blocks = sum(1 for scene in scenes for block in scene.blocks if block.type == "dialogue")
    total_blocks = sum(len(scene.blocks) for scene in scenes)
    dialogue_ratio = round(dialogue_blocks / total_blocks, 2) if total_blocks else 0
    quality_flags = _quality_flags(
        missing_chapters=missing_chapters,
        scenes=scenes,
        action_blocks=action_blocks,
        dialogue_blocks=dialogue_blocks,
        dialogue_ratio=dialogue_ratio,
    )

    return {
        "chapter_coverage": {
            "total_chapters": len(chapters),
            "adapted_chapters": len(covered_chapters),
            "coverage_ratio": round(len(covered_chapters) / len(chapters), 2),
            "missing_chapters": missing_chapters,
        },
        "scene_map": [
            {
                "chapter_index": scene.source_chapter,
                "chapter_title": chapters[scene.source_chapter - 1].title,
                "scene_id": scene.id,
                "scene_title": scene.title,
            }
            for scene in scenes
        ],
        "metrics": {
            "scene_count": len(scenes),
            "block_count": total_blocks,
            "action_blocks": action_blocks,
            "dialogue_blocks": dialogue_blocks,
            "dialogue_ratio": dialogue_ratio,
        },
        "quality_flags": quality_flags,
        "revision_checklist": _revision_checklist(quality_flags),
    }


def _quality_flags(
    missing_chapters: list[int],
    scenes: list[Scene],
    action_blocks: int,
    dialogue_blocks: int,
    dialogue_ratio: float,
) -> list[str]:
    flags: list[str] = []
    if missing_chapters:
        flags.append("存在未生成场景的源章节，请复核章节拆分。")
    if any(scene.location == "待定场景" for scene in scenes):
        flags.append("部分场景地点仍为待定，需要作者补充可拍摄空间。")
    if dialogue_blocks == 0:
        flags.append("未检测到对白块，剧本可能仍偏小说叙述。")
    elif dialogue_ratio < 0.2 and action_blocks > dialogue_blocks:
        flags.append("对白占比偏低，建议补充人物目标冲突和台词推进。")
    if len(scenes) < 3:
        flags.append("场景数量偏少，可能不足以覆盖完整三幕改编。")
    return flags or ["未发现结构性风险，建议进入人物动机和对白语气复核。"]


def _revision_checklist(quality_flags: list[str]) -> list[str]:
    checklist = [
        "逐项核对 scene_map，确认每个小说章节都有对应剧本场景。",
        "检查每场的 location、time 和 characters 是否足以指导后续拍摄化改写。",
        "对照 beats 扩写动作与对白，避免只保留小说摘要。",
    ]
    if any("对白" in flag for flag in quality_flags):
        checklist.append("为关键角色补充更明确的对白目标、潜台词和情绪转折。")
    if any("地点" in flag for flag in quality_flags):
        checklist.append("把待定地点改成具体、可视觉化的内景或外景。")
    return checklist


def _build_coverage_report(
    *,
    logline: str,
    themes: list[str],
    scenes: list[Scene],
    characters: list[Character],
    structure_map: dict[str, object],
    story_bible: dict[str, object],
    adaptation_report: dict[str, object],
) -> dict[str, object]:
    scores = _coverage_scores(
        logline=logline,
        themes=themes,
        scenes=scenes,
        characters=characters,
        structure_map=structure_map,
        story_bible=story_bible,
        adaptation_report=adaptation_report,
    )
    overall_score = round(sum(score["score"] for score in scores) / len(scores))
    lowest_score = min(int(score["score"]) for score in scores)

    return {
        "model": "screenplay_coverage_v1",
        "verdict": _coverage_verdict(overall_score, lowest_score),
        "overall_score": overall_score,
        "scores": scores,
        "strengths": _coverage_strengths(scores, structure_map, story_bible, adaptation_report),
        "weaknesses": _coverage_weaknesses(scores, structure_map, story_bible, adaptation_report),
        "action_items": _coverage_action_items(scores, structure_map, story_bible, adaptation_report),
        "review_notes": [
            "该报告模拟专业 coverage 的读稿反馈结构，用于初稿自检，不等同于人工行业评估。",
            "分数来自本地启发式指标，建议优先处理低于 70 分的维度后再进入对白和场面细修。",
        ],
    }


def _coverage_scores(
    *,
    logline: str,
    themes: list[str],
    scenes: list[Scene],
    characters: list[Character],
    structure_map: dict[str, object],
    story_bible: dict[str, object],
    adaptation_report: dict[str, object],
) -> list[dict[str, object]]:
    metrics = _as_dict(adaptation_report["metrics"])
    chapter_coverage = _as_dict(adaptation_report["chapter_coverage"])
    diagnostics = _as_list(structure_map["diagnostics"])
    beats = [_as_dict(beat) for beat in _as_list(structure_map["beats"])]
    locations = [_as_dict(location) for location in _as_list(story_bible["locations"])]
    open_questions = _as_list(story_bible["open_questions"])
    props = _as_list(story_bible["props"])

    premise_score = _clamp_score(58 + (12 if logline else 0) + min(len(themes), 3) * 4)
    structure_score = _clamp_score(
        82
        - max(0, 5 - len({beat["scene_id"] for beat in beats})) * 8
        - (8 if len(scenes) < 5 else 0)
        - max(0, len(diagnostics) - 1) * 4
    )
    character_score = _clamp_score(
        55
        + min(len(characters), 4) * 6
        + (8 if any(character.role == "protagonist" for character in characters) else 0)
        - max(0, len(open_questions) - 2) * 3
    )
    dialogue_ratio = float(metrics["dialogue_ratio"])  # type: ignore[index]
    dialogue_score = _clamp_score(
        48
        + min(int(dialogue_ratio * 100), 35)
        + (8 if metrics["dialogue_blocks"] else 0)
    )
    visuality_score = _clamp_score(
        50
        + min(int(metrics["action_blocks"]) * 4, 20)
        + min(len([location for location in locations if location["name"] != "待定场景"]), 4) * 5
        + min(len(props), 3) * 3
        - (12 if any(scene.location == "待定场景" for scene in scenes) else 0)
    )
    fidelity_score = _clamp_score(
        45
        + round(float(chapter_coverage["coverage_ratio"]) * 40)
        + (6 if not chapter_coverage["missing_chapters"] else 0)
    )

    return [
        _coverage_score("premise", premise_score, "故事前提、类型信号和一句话卖点的清晰度。"),
        _coverage_score("structure", structure_score, "关键结构节拍是否分布清楚并能支撑三幕推进。"),
        _coverage_score("character", character_score, "人物功能、连续性和可继续深化的目标关系。"),
        _coverage_score("dialogue", dialogue_score, "对白存在感、台词推进和小说叙述转剧本语言的程度。"),
        _coverage_score("visuality", visuality_score, "场景地点、动作块和道具线索的可拍摄程度。"),
        _coverage_score("adaptation_fidelity", fidelity_score, "源章节覆盖、场景映射和改编可追溯性。"),
    ]


def _coverage_score(area: str, score: int, rationale: str) -> dict[str, object]:
    return {
        "area": area,
        "score": score,
        "rationale": rationale,
    }


def _coverage_verdict(overall_score: int, lowest_score: int) -> str:
    if overall_score >= 80 and lowest_score >= 70:
        return "consider"
    if overall_score >= 60:
        return "revise"
    return "draft"


def _coverage_strengths(
    scores: list[dict[str, object]],
    structure_map: dict[str, object],
    story_bible: dict[str, object],
    adaptation_report: dict[str, object],
) -> list[str]:
    strengths: list[str] = []
    strong_areas = [score["area"] for score in scores if int(score["score"]) >= 75]
    if "adaptation_fidelity" in strong_areas:
        strengths.append("章节覆盖和场景映射完整，便于作者逐章回到原文复核。")
    if "structure" in strong_areas:
        strengths.append("关键结构节拍已经映射到具体场景，可继续深化冲突强度。")
    if "visuality" in strong_areas:
        strengths.append("动作、地点和道具线索具备初步可拍摄性。")
    if story_bible["characters"]:
        strengths.append("人物和改编资料已独立沉淀，适合后续连续性维护。")
    if adaptation_report["revision_checklist"]:
        strengths.append("修订清单已经把自动质检结果转化为下一轮打磨入口。")
    if not strengths:
        strengths.append("初稿已建立基本场景序列，可以在此基础上继续做人工扩写。")
    if structure_map["diagnostics"]:
        return strengths[:4]
    return strengths


def _coverage_weaknesses(
    scores: list[dict[str, object]],
    structure_map: dict[str, object],
    story_bible: dict[str, object],
    adaptation_report: dict[str, object],
) -> list[str]:
    weaknesses: list[str] = []
    low_areas = [score["area"] for score in scores if int(score["score"]) < 70]
    if "dialogue" in low_areas:
        weaknesses.append("对白维度偏弱，部分场景仍可能停留在小说摘要而非角色交锋。")
    if "visuality" in low_areas:
        weaknesses.append("可拍摄信息不足，需要补充具体地点、动作调度和视觉线索。")
    if "structure" in low_areas:
        weaknesses.append("结构节拍可能过度集中或场景数量偏少，需要扩写转折层次。")
    if "character" in low_areas:
        weaknesses.append("人物目标和关系仍需明确，否则后续对白和冲突会缺少驱动力。")
    quality_flags = _as_list(adaptation_report["quality_flags"])
    for flag in quality_flags:
        if len(weaknesses) >= 4:
            break
        if "未发现" in str(flag):
            continue
        if flag not in weaknesses:
            weaknesses.append(str(flag))
    if len(_as_list(story_bible["open_questions"])) > 2:
        weaknesses.append("待回答问题较多，建议先收束核心悬念和主角选择。")
    if not weaknesses:
        weaknesses.append("当前未发现单项硬伤，下一步应由作者进行人物动机和语气复核。")
    if structure_map["diagnostics"]:
        return weaknesses[:5]
    return weaknesses


def _coverage_action_items(
    scores: list[dict[str, object]],
    structure_map: dict[str, object],
    story_bible: dict[str, object],
    adaptation_report: dict[str, object],
) -> list[dict[str, str]]:
    low_scores = sorted(scores, key=lambda score: int(score["score"]))
    items = [
        _coverage_action_for_area(str(score["area"]), int(score["score"]))
        for score in low_scores
        if int(score["score"]) < 75
    ]

    if any("同一场" in str(diagnostic) for diagnostic in _as_list(structure_map["diagnostics"])):
        items.append(
            {
                "priority": "high",
                "area": "structure",
                "note": "拆分或重排共用关键节拍的场景，让诱发事件、中点和高潮形成更清楚的递进。",
            }
        )
    if any("待定场景" in str(question) for question in _as_list(story_bible["open_questions"])):
        items.append(
            {
                "priority": "medium",
                "area": "visuality",
                "note": "把待定地点改写为具体内景或外景，并补充能被镜头捕捉的动作细节。",
            }
        )
    chapter_coverage = _as_dict(adaptation_report["chapter_coverage"])
    if chapter_coverage["missing_chapters"]:
        items.append(
            {
                "priority": "high",
                "area": "adaptation_fidelity",
                "note": "先补齐缺失源章节的场景，再进入对白和节奏调整。",
            }
        )

    if not items:
        items.append(
            {
                "priority": "medium",
                "area": "character",
                "note": "逐场检查主角外在目标、阻碍和情绪变化，让已生成场景更具戏剧推进。",
            }
        )
    return items[:5]


def _coverage_action_for_area(area: str, score: int) -> dict[str, str]:
    priority = "high" if score < 60 else "medium"
    notes = {
        "premise": "重写 logline，明确主角、目标、阻碍和类型承诺。",
        "structure": "对照 structure_map 扩写缺少独立场景承载的关键节拍。",
        "character": "为主要人物补充本幕目标、关系变化和选择代价。",
        "dialogue": "为每场加入角色带目标的对白，避免只用动作摘要传递信息。",
        "visuality": "补充可拍摄地点、动作调度和可回收的视觉道具。",
        "adaptation_fidelity": "核对 scene_map 和 chapter_coverage，确保源章节没有被跳过。",
    }
    return {
        "priority": priority,
        "area": area,
        "note": notes[area],
    }


def _clamp_score(score: int) -> int:
    return max(0, min(100, score))


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _strip_voice_over_prefix(text: str) -> str:
    return re.sub(r"^旁白[：:]\s*", "", text, count=1).strip()


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
