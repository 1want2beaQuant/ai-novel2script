"""Local adaptation heuristics used when no external AI provider is configured."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from novel2script.models import Act, Chapter, Character, Scene, ScriptBlock, ScriptDraft


SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+[。！？!?；;]?")
DIALOGUE_RE = re.compile(r"(?P<speaker>[\u4e00-\u9fffA-Za-z0-9_·]{1,16})[：:]\s*(?P<line>.+)")
LOCATION_HINT_RE = re.compile(r"(?:在|到|回到|走进|来到)(?P<place>[^，。！？!?；;\n]{2,16})")
CHINESE_SURNAME = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平"
    "黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋庞熊纪舒屈项祝董"
    "梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田胡凌"
    "霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣邓郁单杭洪包诸左石崔吉龚"
    "程邢裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧"
    "隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹龙叶幸"
    "司黎溥印怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳"
    "逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀浦尚农温别庄晏柴瞿阎"
    "连习容向古易廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越"
    "夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查"
    "后荆红游竺权逯盖益桓公"
)
COMPOUND_CHINESE_SURNAMES = (
    "欧阳",
    "司马",
    "上官",
    "诸葛",
    "东方",
    "夏侯",
    "尉迟",
    "公孙",
    "慕容",
    "司徒",
    "令狐",
    "皇甫",
    "宇文",
    "长孙",
    "闻人",
    "独孤",
    "南宫",
    "轩辕",
)
COMPOUND_SURNAME_PATTERN = "|".join(COMPOUND_CHINESE_SURNAMES)
SURNAME_NAME_RE = re.compile(
    rf"(?<![\u4e00-\u9fff])"
    rf"(?P<name>(?:{COMPOUND_SURNAME_PATTERN})[\u4e00-\u9fff]{{1,2}}|"
    rf"[{CHINESE_SURNAME}][\u4e00-\u9fff]{{1,2}})"
    rf"(?=(?:在|说|问|喊|道|答|想|看|听|拿|把|将|走|来到|回到|发现|找到|没有|决定|"
    rf"把|低声|轻声|抬头|转身|推开|藏|写|追|离开|出现|站|坐|望|来到|回头|$|[，。！？!?；;、\s]))"
)
LATIN_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_·-]{0,31}")
STOP_NAMES = {
    "他们",
    "她们",
    "我们",
    "你们",
    "这里",
    "那里",
    "那就",
    "时候",
    "声音",
    "黎明前",
    "城市",
    "屋里",
    "窗外",
    "夜色",
    "清晨",
    "突然",
}
LOCATION_KEYWORDS = (
    "档案馆地下库",
    "灯塔控制室",
    "码头仓库",
    "修表铺",
    "旧钟楼",
    "天台",
    "书房",
    "旧宅",
    "码头",
    "街口",
    "屋里",
    "客厅",
    "学校",
    "公司",
    "医院",
    "城门",
    "森林",
    "灯塔",
)
LOCATION_SUFFIXES = ("门口", "里面", "内", "里", "外", "前", "后", "上", "下")
PROP_KEYWORDS = (
    "蓝皮账本",
    "银色录音带",
    "铜钥匙",
    "旧怀表",
    "路线图",
    "录音带",
    "船票",
    "胶片",
    "账本",
    "怀表",
    "信",
    "照片",
    "录音笔",
    "钥匙",
    "钟",
    "线索",
    "日记",
    "戒指",
    "地图",
    "刀",
)
SPEAKER_SPLIT_CHARS = set("从低轻冷问说答喊道提追推带拿把将坐站走看听")
SPEAKER_SUFFIXES = (
    "低声说",
    "轻声说",
    "说道",
    "冷笑",
    "提醒",
    "追问",
    "威胁",
    "说",
    "问",
    "喊",
    "道",
    "答",
)


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

    for name in _guess_names(chapter.body, limit=4):
        if name not in characters:
            characters.append(name)

    if blocks[-1].type != "transition":
        blocks.append(ScriptBlock(type="transition", text="切至下一场。"))

    scene_characters = characters[:5]
    location = _infer_location(chapter.body)
    summary = _summarize(chapter.body)
    lead = scene_characters[0] if scene_characters else "主角"
    turning_point = _scene_turning_point(paragraphs, summary)

    return Scene(
        id=f"S{chapter.index:03d}",
        title=chapter.title,
        location=location,
        time=_infer_time(chapter.body),
        summary=summary,
        objective=_scene_objective(lead, chapter.title, chapter.body, summary),
        conflict=_scene_conflict(lead, location, chapter.body),
        turning_point=turning_point,
        source_chapter=chapter.index,
        characters=scene_characters,
        beats=beats,
        blocks=blocks,
    )


def _paragraph_to_block(paragraph: str) -> ScriptBlock:
    if paragraph.startswith(("旁白：", "旁白:")):
        return ScriptBlock(type="voice_over", text=_strip_voice_over_prefix(paragraph))

    dialogue = _match_dialogue(paragraph)
    if dialogue:
        return ScriptBlock(
            type="dialogue",
            character=dialogue[0],
            text=dialogue[1],
        )

    return ScriptBlock(type="action", text=_rewrite_action(paragraph))


def _scene_objective(lead: str, chapter_title: str, body: str, summary: str) -> str:
    clue = _primary_scene_prop(body, chapter_title) or _first_keyword(summary, PROP_KEYWORDS) or _clean_chapter_title(chapter_title)
    action = _objective_action(summary)
    return f"{lead}要{action}{clue}，确认它如何改变下一步选择。"


def _scene_conflict(lead: str, location: str, body: str) -> str:
    obstacle = "信息不完整"
    antagonist = _first_name_before_marker(body, ("堵住", "威胁", "要求", "冷笑", "追到"))
    if antagonist:
        obstacle = f"{antagonist}的阻拦和交换条件"
    elif "秘密" in body or "真相" in body or "线索" in body or "证据" in body:
        obstacle = "关键线索仍被隐瞒"
    elif "雨" in body or "夜" in body or "黑" in body:
        obstacle = "环境压迫让判断变得困难"
    elif "问" in body or "说" in body or "：" in body or ":" in body:
        obstacle = "人物之间的信息和立场并不一致"
    place = location if location != "待定场景" else "当前场景"
    return f"{lead}在{place}面对{obstacle}，需要用行动或对白推进局面。"


def _scene_turning_point(paragraphs: list[str], summary: str) -> str:
    candidates = [paragraph for paragraph in paragraphs if paragraph.strip()]
    source = _select_turning_source(candidates) or summary
    turn = _shorten(source, 52).rstrip("。！？!?；;，, ")
    return f"场景转向：{turn}。"


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
            if name in STOP_NAMES or not _is_plausible_character_name(name):
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
    first_turn = _logline_clause(scenes[0].summary, lead) if scenes else "命运被打破"
    final_turn = _logline_clause(scenes[-1].summary, lead) if scenes else "完成关键选择"
    return f"《{title}》讲述{lead}经历{first_turn}，并被迫面对{final_turn}。"


def _logline_clause(summary: str, lead: str) -> str:
    clause = summary.strip().strip("。！？!?；;，, ")
    if lead and clause.startswith(lead):
        clause = clause[len(lead) :].lstrip("在把将和与、，, ")
    return clause or "新的命运转折"


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
    props: dict[str, set[int]] = {}
    for chapter in chapters:
        for keyword in PROP_KEYWORDS:
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
    quality_checks = _quality_checks(
        missing_chapters=missing_chapters,
        scenes=scenes,
        action_blocks=action_blocks,
        dialogue_blocks=dialogue_blocks,
        dialogue_ratio=dialogue_ratio,
    )
    quality_flags = _quality_flags(quality_checks)

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
        "quality_checks": quality_checks,
        "quality_flags": quality_flags,
        "revision_checklist": _revision_checklist(quality_flags),
    }


def _quality_checks(
    missing_chapters: list[int],
    scenes: list[Scene],
    action_blocks: int,
    dialogue_blocks: int,
    dialogue_ratio: float,
) -> list[dict[str, str]]:
    scene_count = len(scenes)
    specific_locations = [
        scene.location for scene in scenes if scene.location and scene.location != "待定场景"
    ]
    scenes_with_dialogue = [
        scene
        for scene in scenes
        if any(block.type == "dialogue" for block in scene.blocks)
    ]
    scenes_with_characters = [scene for scene in scenes if scene.characters]
    generic_objectives = [scene.id for scene in scenes if "背后的选择和后果" in scene.objective]

    checks = [
        _quality_check(
            "chapter_coverage",
            "章节覆盖",
            "pass" if not missing_chapters else "fail",
            f"{scene_count - len(missing_chapters)}/{scene_count} 场",
            "所有源章节都有可追溯场景。" if not missing_chapters else "存在未映射为场景的源章节。",
        ),
        _quality_check(
            "dialogue_density",
            "对白密度",
            "pass" if dialogue_ratio >= 0.3 else "warn" if dialogue_ratio >= 0.18 else "fail",
            f"{round(dialogue_ratio * 100)}%",
            (
                f"{len(scenes_with_dialogue)}/{scene_count} 场包含对白，"
                f"共 {dialogue_blocks} 个对白块。"
            ),
        ),
        _quality_check(
            "visual_specificity",
            "可拍摄地点",
            "pass"
            if len(specific_locations) == scene_count
            else "warn"
            if specific_locations
            else "fail",
            f"{len(specific_locations)}/{scene_count} 场",
            "地点已具体到可用于场面调度。" if len(specific_locations) == scene_count else "仍有场景地点待定。",
        ),
        _quality_check(
            "character_presence",
            "人物识别",
            "pass"
            if len(scenes_with_characters) == scene_count
            else "warn"
            if scenes_with_characters
            else "fail",
            f"{len(scenes_with_characters)}/{scene_count} 场",
            "每场都有明确角色进入改编资料。" if len(scenes_with_characters) == scene_count else "部分场景缺少明确角色。",
        ),
        _quality_check(
            "dramatic_function",
            "场景功能",
            "pass" if not generic_objectives and action_blocks else "warn",
            f"{scene_count - len(generic_objectives)}/{scene_count} 场",
            "目标、冲突和转折已从原文线索生成。" if not generic_objectives else "部分场景功能仍偏模板化。",
        ),
    ]
    return checks


def _quality_check(
    check_id: str,
    label: str,
    status: str,
    value: str,
    detail: str,
) -> dict[str, str]:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "value": value,
        "detail": detail,
    }


def _quality_flags(quality_checks: list[dict[str, str]]) -> list[str]:
    flags: list[str] = []
    status_by_id = {check["id"]: check["status"] for check in quality_checks}
    if status_by_id.get("chapter_coverage") == "fail":
        flags.append("存在未生成场景的源章节，请复核章节拆分。")
    if status_by_id.get("visual_specificity") in {"warn", "fail"}:
        flags.append("部分场景地点仍为待定，需要作者补充可拍摄空间。")
    if status_by_id.get("dialogue_density") == "fail":
        flags.append("未检测到对白块，剧本可能仍偏小说叙述。")
    elif status_by_id.get("dialogue_density") == "warn":
        flags.append("对白占比偏低，建议补充人物目标冲突和台词推进。")
    if status_by_id.get("character_presence") in {"warn", "fail"}:
        flags.append("部分场景缺少明确人物，建议补齐角色称谓和关系功能。")
    if status_by_id.get("dramatic_function") == "warn":
        flags.append("部分场景目标或转折仍偏模板化，需要从原文线索中强化戏剧功能。")
    if status_by_id.get("chapter_coverage") == "fail":
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


def _match_dialogue(paragraph: str) -> tuple[str, str] | None:
    compact = paragraph.strip()
    dialogue = DIALOGUE_RE.match(compact)
    if dialogue:
        speaker = _normalize_speaker(dialogue.group("speaker"))
        line = _strip_quotes(dialogue.group("line"))
        return (speaker, line) if speaker and line else None

    narrated = re.match(
        r"(?P<speaker>[\u4e00-\u9fffA-Za-z0-9_·]{2,18}(?:低声说|轻声说|说道|冷笑|提醒|追问|威胁|说|问|喊|道|答))[：:]\s*(?P<line>.+)",
        compact,
    )
    if narrated:
        speaker = _normalize_speaker(narrated.group("speaker"))
        line = _strip_quotes(narrated.group("line"))
        return (speaker, line) if speaker and line else None

    return None


def _infer_location(text: str) -> str:
    keyword_hits = [
        (index, -len(place), place)
        for place in LOCATION_KEYWORDS
        if (index := text.find(place)) >= 0
    ]
    if keyword_hits:
        return sorted(keyword_hits)[0][2]

    match = LOCATION_HINT_RE.search(text)
    if match:
        place = match.group("place")
        place = re.split(r"(发现|找到|看见|听见|只剩|停下|拿出|推开|穿过|堆满)", place, maxsplit=1)[0]
        return _clean_location(place)
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
    names: list[str] = [
        match.group("name")
        for match in SURNAME_NAME_RE.finditer(text)
        if _is_plausible_character_name(match.group("name"))
    ]
    for dialogue in re.finditer(r"(?P<speaker>[\u4e00-\u9fffA-Za-z0-9_·]{2,18})[：:]", text):
        speaker = _normalize_speaker(dialogue.group("speaker"))
        if _is_plausible_character_name(speaker):
            names.append(speaker)
    counts = Counter(names)
    return [name for name, _ in counts.most_common(limit)]


def _is_plausible_character_name(name: str) -> bool:
    cleaned = name.strip()
    if cleaned in STOP_NAMES:
        return False
    if LATIN_NAME_RE.fullmatch(cleaned):
        return True
    if not all("\u4e00" <= char <= "\u9fff" for char in cleaned):
        return False
    if any(
        cleaned.startswith(surname) and len(surname) < len(cleaned) <= len(surname) + 2
        for surname in COMPOUND_CHINESE_SURNAMES
    ):
        return True
    return 2 <= len(cleaned) <= 3 and cleaned[0] in CHINESE_SURNAME


def _strip_quotes(text: str) -> str:
    return text.strip().strip("“”\"'")


def _strip_voice_over_prefix(text: str) -> str:
    return re.sub(r"^旁白[：:]\s*", "", text, count=1).strip()


def _normalize_speaker(text: str) -> str:
    speaker = text.strip()
    for suffix in SPEAKER_SUFFIXES:
        if speaker.endswith(suffix) and len(speaker) > len(suffix):
            speaker = speaker[: -len(suffix)]
            break
    speaker = re.sub(r"^(?:旁白|对讲机里|录音带里传出|屏幕里)", "", speaker).strip()
    speaker = re.sub(r"的声音$", "", speaker).strip()
    for index in range(1, len(speaker)):
        if speaker[index] in SPEAKER_SPLIT_CHARS:
            candidate = speaker[:index]
            if _is_plausible_character_name(candidate):
                return candidate
    return speaker


def _clean_location(place: str) -> str:
    cleaned = re.sub(r"\s+", "", place).strip(" ，。！？!?；;的里中外前后上下")
    for suffix in LOCATION_SUFFIXES:
        if cleaned.endswith(suffix) and len(cleaned) > len(suffix) + 1:
            cleaned = cleaned[: -len(suffix)]
            break
    return cleaned or "待定场景"


def _first_keyword(text: str, keywords: tuple[str, ...]) -> str:
    for keyword in keywords:
        if keyword in text:
            return keyword
    return ""


def _clean_chapter_title(title: str) -> str:
    cleaned = re.sub(r"^第\s*[\w一二三四五六七八九十百千万零〇两]+\s*[章节回幕卷]\s*", "", title)
    return cleaned.strip() or title.strip() or "关键线索"


def _objective_action(text: str) -> str:
    if any(word in text for word in ("救", "绑", "计时器", "活")):
        return "救出"
    if any(word in text for word in ("证明", "证据", "账本", "录音")):
        return "保住并验证"
    if any(word in text for word in ("找到", "发现", "打开", "线索")):
        return "追查"
    return "确认"


def _primary_scene_prop(body: str, chapter_title: str) -> str:
    title_props = [keyword for keyword in PROP_KEYWORDS if keyword in chapter_title]
    if title_props:
        title_candidates = [
            keyword
            for keyword in PROP_KEYWORDS
            if keyword in body and any(keyword.endswith(title_prop) for title_prop in title_props)
        ]
        if title_candidates:
            return max(title_candidates, key=len)

    for keyword in PROP_KEYWORDS:
        if keyword in chapter_title and keyword in body:
            return keyword

    matches = [
        (
            body.count(keyword),
            len(keyword),
            -body.find(keyword),
            keyword,
        )
        for keyword in PROP_KEYWORDS
        if keyword in body
    ]
    if not matches:
        return ""
    return max(matches)[3]


def _first_name_before_marker(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        index = text.find(marker)
        if index <= 0:
            continue
        names = _guess_names(text[max(0, index - 8) : index], limit=1)
        if names:
            return names[0]
    return ""


def _select_turning_source(paragraphs: list[str]) -> str:
    turn_markers = (
        "听到这里",
        "不要相信",
        "天台见",
        "一个人来",
        "只剩十五分钟",
        "所有人听见",
        "传向码头",
        "唯一的入口",
        "露出",
        "威胁",
        "证据",
    )
    for paragraph in reversed(paragraphs):
        if any(marker in paragraph for marker in turn_markers):
            return paragraph
    return paragraphs[-1] if paragraphs else ""


def _shorten(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _act_purpose(index: int, total: int) -> str:
    if total == 3:
        return ["建立人物、目标与改编世界。", "推进冲突并制造不可逆转折。", "收束选择，形成可继续打磨的结局。"][index]
    return "承接小说章节，整理为可拍摄的连续场景。"
