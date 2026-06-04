import pytest

from novel2script.chapter_parser import parse_chapters


def test_parse_chinese_chapters() -> None:
    text = """
第 1 章 雨夜
林晚在书房里发现一封旧信。

第 2 章 回声
周岚说：我们不能再等了。

第 3 章 真相
两人在码头找到最后的线索。
"""

    chapters = parse_chapters(text)

    assert len(chapters) == 3
    assert chapters[0].title == "第 1 章 雨夜"
    assert "旧信" in chapters[0].body


def test_requires_at_least_three_body_chapters() -> None:
    with pytest.raises(ValueError, match="至少需要 3 个"):
        parse_chapters(
            """
第 1 章
只有一章。

第 2 章
只有两章。
"""
        )
