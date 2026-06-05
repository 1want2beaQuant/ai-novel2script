from novel2script.converter import convert_text_to_script
from novel2script.fountain import draft_to_fountain


def test_draft_to_fountain_exports_scene_headings_and_dialogue() -> None:
    text = """
第 1 章 雨夜
林晚在书房里发现一封旧信。

林晚说：这不是父亲的笔迹。

第 2 章 空屋
周岚说：我们不能再等了。

第 3 章 码头
两人在码头找到最后的线索。
"""
    draft = convert_text_to_script(text, title="雾城来信")

    fountain = draft_to_fountain(draft)

    assert "Title: 雾城来信" in fountain
    assert "INT. 书房 - 未定" in fountain
    assert "// source_chapter: 1" in fountain
    assert "林晚" in fountain
    assert "这不是父亲的笔迹。" in fountain
