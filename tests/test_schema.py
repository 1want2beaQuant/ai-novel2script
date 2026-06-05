from novel2script.converter import convert_text_to_script
from novel2script.schema import validate_script


def test_generated_script_matches_schema() -> None:
    text = """
第 1 章 雨夜
林晚在书房里发现一封旧信。

第 2 章 空屋
周岚说：我们不能再等了。

第 3 章 码头
两人在码头找到最后的线索。
"""

    draft = convert_text_to_script(text, title="雾城来信")
    data = draft.to_dict()

    validate_script(data)
    assert data["schema_version"] == "1.4.0"
    assert len(data["structure_map"]["beats"]) == 5
    assert data["story_bible"]["locations"]
    assert data["adaptation_report"]["chapter_coverage"]["adapted_chapters"] == 3
    assert data["coverage_report"]["overall_score"] >= 0
    assert len(data["coverage_report"]["scores"]) == 6
