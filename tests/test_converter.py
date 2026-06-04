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
    assert data["source"]["chapter_count"] == 3
    assert len(data["acts"]) == 3
    scenes = [scene for act in data["acts"] for scene in act["scenes"]]
    assert [scene["source_chapter"] for scene in scenes] == [1, 2, 3]
    assert data["characters"][0]["name"] == "林晚"
    assert scenes[0]["location"] == "书房"
    assert any(block["type"] == "dialogue" for scene in scenes for block in scene["blocks"])
