"""Chapter detection for Chinese and English novel manuscripts."""

from __future__ import annotations

import re

from novel2script.models import Chapter


CHINESE_NUMBER = r"[一二三四五六七八九十百千万零〇两\d]+"
CHINESE_SPECIAL_HEADING = r"(?:序章|序幕|楔子|引子|终章|尾声|后记)"
ENGLISH_NUMBER = (
    r"\d+|[ivxlcdm]+|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)"
    r"(?:[-\s](?:one|two|three|four|five|six|seven|eight|nine))?"
)
ENGLISH_SPECIAL_HEADING = r"(?:prologue|epilogue)"

CHAPTER_HEADING_RE = re.compile(
    rf"""
    ^[^\S\n]*(?:\#{{1,6}}[^\S\n]*)?
    (?P<title>
        第[^\S\n]*{CHINESE_NUMBER}[^\S\n]*[章节回幕卷][^\n]*
        |{CHINESE_SPECIAL_HEADING}(?:[：:、.\-—][^\S\n]*.+|[^\S\n]+.+)?
        |(?:chapter|ch\.)\s+(?:{ENGLISH_NUMBER})(?=$|[\s:.\-—])[^\n]*
        |{ENGLISH_SPECIAL_HEADING}(?:[:.\-—][^\S\n]*.+)?
    )
    [^\S\n]*$
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


def parse_chapters(text: str) -> list[Chapter]:
    """Parse a manuscript into chapters.

    The tool intentionally requires explicit chapter boundaries. A screenplay adapted from a
    multi-chapter novel needs source traceability, and silent paragraph splitting makes that
    traceability unreliable.
    """

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip().lstrip("\ufeff")
    if not cleaned:
        raise ValueError("输入文本为空，无法转换。")

    matches = list(CHAPTER_HEADING_RE.finditer(cleaned))
    if not matches:
        raise ValueError("未识别到章节标题，请使用“第 1 章”“序章”或“Chapter One”等格式。")

    chapters: list[Chapter] = []
    for index, match in enumerate(matches, start=1):
        body_start = match.end()
        body_end = matches[index].start() if index < len(matches) else len(cleaned)
        title = _normalize_spaces(match.group("title"))
        body = cleaned[body_start:body_end].strip()
        if body:
            chapters.append(Chapter(index=len(chapters) + 1, title=title, body=body))

    if len(chapters) < 3:
        raise ValueError("至少需要 3 个包含正文的章节才能生成结构化剧本。")

    return chapters


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
