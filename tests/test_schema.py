from importlib import resources
import json

from novel2script.converter import convert_text_to_script
import novel2script.schema as schema_module
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
    assert data["schema_version"] == "1.5.0"
    scene = data["acts"][0]["scenes"][0]
    assert scene["objective"]
    assert scene["conflict"]
    assert scene["turning_point"]
    assert len(data["structure_map"]["beats"]) == 5
    assert data["story_bible"]["locations"]
    assert data["adaptation_report"]["chapter_coverage"]["adapted_chapters"] == 3
    assert data["coverage_report"]["overall_score"] >= 0
    assert len(data["coverage_report"]["scores"]) == 6


def test_load_schema_falls_back_to_packaged_resource(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(schema_module, "PROJECT_SCHEMA_PATH", tmp_path / "missing.json")

    loaded = schema_module.load_schema()
    packaged = json.loads(
        resources.files("novel2script")
        .joinpath("schemas/script.schema.json")
        .read_text(encoding="utf-8")
    )

    assert loaded == packaged
    assert loaded["$schema"] == "https://json-schema.org/draft/2020-12/schema"
