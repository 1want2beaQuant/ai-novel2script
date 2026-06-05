from novel2script.converter import convert_text_to_script
from novel2script.markdown import draft_to_markdown


def test_draft_to_markdown_exports_revision_brief_sections() -> None:
    draft = convert_text_to_script(
        """
第 1 章 雨夜
林晚在书房里发现一封旧信。

林晚说：这不是父亲的笔迹。

第 2 章 空屋
周岚说：我们不能再等了。

第 3 章 码头
两人在码头找到最后的线索。
""",
        title="雾城来信",
    )

    markdown = draft_to_markdown(draft)

    assert markdown.startswith("# 雾城来信 修订简报\n")
    assert "## Coverage" in markdown
    assert "- Verdict:" in markdown
    assert "- Chapter coverage: 3/3 (100%)" in markdown
    assert "## Scorecard" in markdown
    assert "- **premise**:" in markdown
    assert "## Priority Actions" in markdown
    assert "## Structure Beats" in markdown
    assert "开场意象" in markdown
    assert "## Scene Index" in markdown
    assert "**S001** chapter 1" in markdown
    assert "## Revision Checklist" in markdown
