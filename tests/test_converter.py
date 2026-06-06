from novel2script.converter import convert_text_to_script


SAMPLE = """
第 1 章 雨夜来信
林晚在书房里发现一封旧信，窗外的雨敲着玻璃。

林晚说：这不是父亲的笔迹。

第 2 章 空屋
清晨，周岚来到旧宅，发现屋里只剩一只停止的钟。

周岚问：昨晚还有谁来过？

第 3 章 码头
夜色里，两人在码头找到最后的线索，真相终于逼近。

林晚说：如果这是答案，我要亲自说出来。
"""


def test_convert_text_to_script_contains_traceable_scenes() -> None:
    draft = convert_text_to_script(SAMPLE, title="雾城来信")
    data = draft.to_dict()

    assert data["title"] == "雾城来信"
    assert "林晚在林晚" not in data["logline"]
    assert "后的故事" not in data["logline"]
    assert data["logline"].startswith("《雾城来信》讲述林晚")
    assert data["source"]["chapter_count"] == 3
    assert len(data["acts"]) == 3
    scenes = [scene for act in data["acts"] for scene in act["scenes"]]
    assert [scene["source_chapter"] for scene in scenes] == [1, 2, 3]
    assert data["characters"][0]["name"] == "林晚"
    assert scenes[0]["location"] == "书房"
    assert scenes[0]["objective"]
    assert scenes[0]["conflict"]
    assert scenes[0]["turning_point"].startswith("场景转向：")
    assert any(block["type"] == "dialogue" for scene in scenes for block in scene["blocks"])
    structure = data["structure_map"]
    assert structure["model"] == "five_point_screenplay_map"
    assert [beat["id"] for beat in structure["beats"]] == [
        "opening_image",
        "inciting_incident",
        "midpoint",
        "climax",
        "resolution",
    ]
    assert structure["diagnostics"]
    bible = data["story_bible"]
    assert bible["characters"][0]["name"] == "林晚"
    assert bible["locations"][0]["scene_ids"] == ["S001"]
    assert any(prop["name"] == "信" for prop in bible["props"])
    assert bible["open_questions"]
    report = data["adaptation_report"]
    assert report["chapter_coverage"]["coverage_ratio"] == 1
    assert report["scene_map"][0]["scene_id"] == "S001"
    assert report["metrics"]["scene_count"] == 3
    assert report["revision_checklist"]
    coverage = data["coverage_report"]
    assert coverage["model"] == "screenplay_coverage_v1"
    assert coverage["verdict"] in {"draft", "revise", "consider"}
    assert [score["area"] for score in coverage["scores"]] == [
        "premise",
        "structure",
        "character",
        "dialogue",
        "visuality",
        "adaptation_fidelity",
    ]
    assert 0 <= coverage["overall_score"] <= 100
    if min(score["score"] for score in coverage["scores"]) < 70:
        assert coverage["verdict"] != "consider"
    assert coverage["strengths"]
    assert coverage["weaknesses"]
    assert coverage["action_items"][0]["priority"] in {"high", "medium", "low"}


def test_convert_text_to_script_keeps_voice_over_blocks() -> None:
    draft = convert_text_to_script(
        """
第 1 章 雨夜
旁白：雨声盖住了旧宅里的脚步。

第 2 章 空屋
林晚说：我们不能再等了。

第 3 章 码头
两人在码头找到最后的线索。
""",
        title="雾城来信",
    )

    blocks = [
        block
        for act in draft.to_dict()["acts"]
        for scene in act["scenes"]
        for block in scene["blocks"]
    ]

    assert {"type": "voice_over", "text": "雨声盖住了旧宅里的脚步。"} in blocks


def test_convert_text_to_script_does_not_promote_action_phrases_to_characters() -> None:
    draft = convert_text_to_script(
        """
序章：雨声
林晚在书房里发现一封旧信。

第一章 回声
周岚说：我们不能再等了。

尾声
两人在码头找到最后的线索。
""",
        title="雾城来信",
    )

    data = draft.to_dict()
    character_names = [character["name"] for character in data["characters"]]
    scene_characters = [
        character
        for act in data["acts"]
        for scene in act["scenes"]
        for character in scene["characters"]
    ]

    assert "林晚" in character_names
    assert "周岚" in character_names
    assert "房里发现" not in character_names
    assert "最后的线索" not in character_names
    assert "房里发现" not in scene_characters
    assert "后的线索" not in scene_characters


def test_convert_text_to_script_uses_fallback_character_when_names_are_unknown() -> None:
    draft = convert_text_to_script(
        """
第 1 章 雨夜
书房里发现一封旧信。

第 2 章 空屋
屋里只剩一只停止的钟。

第 3 章 码头
码头找到最后的线索。
""",
        title="无名线索",
    )

    data = draft.to_dict()

    assert [character["name"] for character in data["characters"]] == ["主角"]
    assert all(
        scene["characters"] == []
        for act in data["acts"]
        for scene in act["scenes"]
    )


def test_convert_text_to_script_keeps_english_and_compound_surname_speakers() -> None:
    draft = convert_text_to_script(
        """
Chapter One Opening
Mara: We cannot wait any longer.

Chapter Two Middle
欧阳娜娜说：线索就在书房。

Chapter Three Ending
Jon: Then we go tonight.
""",
        title="Mixed Names",
    )

    names = [character["name"] for character in draft.to_dict()["characters"]]

    assert "Mara" in names
    assert "欧阳娜娜" in names
    assert "Jon" in names
