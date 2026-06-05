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


def test_parse_chinese_special_headings() -> None:
    chapters = parse_chapters(
        """
序章：雨声
林晚在书房里发现一封旧信。

第一章 回声
周岚说：我们不能再等了。

尾声
两人在码头找到最后的线索。
"""
    )

    assert [chapter.title for chapter in chapters] == ["序章：雨声", "第一章 回声", "尾声"]
    assert [chapter.index for chapter in chapters] == [1, 2, 3]


def test_parse_english_word_roman_and_abbreviated_headings() -> None:
    chapters = parse_chapters(
        """
Prologue: Rain
Mara found a sealed letter on the desk.

Chapter One The Empty Hall
Jon arrived before dawn and saw footprints.

CHAPTER IV - The Last Tape
Mara and Jon played the tape together.

Ch. 5 Aftermath
The hidden name finally connected every clue.
"""
    )

    assert [chapter.title for chapter in chapters] == [
        "Prologue: Rain",
        "Chapter One The Empty Hall",
        "CHAPTER IV - The Last Tape",
        "Ch. 5 Aftermath",
    ]


def test_parse_utf8_bom_before_first_heading() -> None:
    chapters = parse_chapters(
        "\ufeffPrologue: Rain\n"
        "Mara found a sealed letter on the desk.\n\n"
        "Chapter One The Empty Hall\n"
        "Jon arrived before dawn.\n\n"
        "Chapter Two The Last Tape\n"
        "Mara and Jon played the tape together.\n"
    )

    assert chapters[0].title == "Prologue: Rain"
    assert len(chapters) == 3


def test_does_not_treat_inline_chapter_words_as_headings() -> None:
    chapters = parse_chapters(
        """
Chapter One Opening
Mara said chapter one was only a label, not a new heading inside this paragraph.

Chapter Two Middle
Jon wrote "chapter three" in his notebook without starting a new section.

Chapter Three Ending
The final room stayed silent.
"""
    )

    assert len(chapters) == 3
    assert "chapter one was only a label" in chapters[0].body


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


def test_missing_heading_error_mentions_supported_flexible_formats() -> None:
    with pytest.raises(ValueError, match="Chapter One"):
        parse_chapters("只有普通段落，没有明确标题。")
