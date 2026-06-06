from pathlib import Path

from novel2script.converter import convert_text_to_script
from novel2script.schema import validate_script


ROOT = Path(__file__).resolve().parents[1]


def _scenes(data: dict[str, object]) -> list[dict[str, object]]:
    return [
        scene
        for act in data["acts"]  # type: ignore[index]
        for scene in act["scenes"]  # type: ignore[index]
    ]


def _score_map(data: dict[str, object]) -> dict[str, int]:
    return {
        str(score["area"]): int(score["score"])
        for score in data["coverage_report"]["scores"]  # type: ignore[index]
    }


def _quality_check_map(data: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(check["id"]): check
        for check in data["adaptation_report"]["quality_checks"]  # type: ignore[index]
    }


def test_long_form_realistic_input_produces_auditable_adaptation_quality() -> None:
    text = (ROOT / "examples" / "long_adaptation_case.txt").read_text(encoding="utf-8")

    draft = convert_text_to_script(text, title="灯塔回声")
    data = draft.to_dict()

    validate_script(data)
    scenes = _scenes(data)
    metrics = data["adaptation_report"]["metrics"]  # type: ignore[index]
    story_bible = data["story_bible"]  # type: ignore[index]
    quality_checks = _quality_check_map(data)

    assert len(scenes) == 6
    assert [scene["source_chapter"] for scene in scenes] == [1, 2, 3, 4, 5, 6]
    assert data["adaptation_report"]["chapter_coverage"]["coverage_ratio"] == 1  # type: ignore[index]
    assert metrics["dialogue_blocks"] >= 12  # type: ignore[index]
    assert metrics["dialogue_ratio"] >= 0.3  # type: ignore[index]

    character_names = {character["name"] for character in data["characters"]}  # type: ignore[index]
    assert {"叶舟", "沈泊", "梁知予", "许曼"}.issubset(character_names)

    location_names = {location["name"] for location in story_bible["locations"]}  # type: ignore[index]
    assert {"修表铺", "档案馆地下库", "旧钟楼", "码头仓库", "天台", "灯塔控制室"}.issubset(
        location_names
    )
    assert all(scene["location"] != "待定场景" for scene in scenes)

    prop_names = {prop["name"] for prop in story_bible["props"]}  # type: ignore[index]
    assert {"铜钥匙", "蓝皮账本", "船票", "旧怀表", "银色录音带"}.issubset(prop_names)

    assert "铜钥匙" in scenes[0]["objective"]
    assert "许曼" in scenes[3]["conflict"]
    assert "灯塔" in scenes[-1]["turning_point"]
    assert all("背后的选择和后果" not in scene["objective"] for scene in scenes)

    assert {check["status"] for check in quality_checks.values()} == {"pass"}
    assert quality_checks["dialogue_density"]["value"].endswith("%")
    assert quality_checks["visual_specificity"]["detail"]
    assert data["coverage_report"]["verdict"] == "consider"  # type: ignore[index]
    assert min(_score_map(data).values()) >= 70


def test_quality_checks_flag_narrative_only_drafts_as_revision_risks() -> None:
    draft = convert_text_to_script(
        """
第 1 章 空白记录
有人把一份记录藏起来，屋外没有可辨认的地点，所有经过都只被概述。

第 2 章 模糊追踪
事情继续发展，主角知道必须寻找答案，但文本没有给出可拍摄空间。

第 3 章 无声结尾
线索似乎出现又消失，结尾仍然只保留叙述，没有角色之间的直接交锋。
""",
        title="无声样本",
    )

    data = draft.to_dict()
    checks = _quality_check_map(data)
    flags = data["adaptation_report"]["quality_flags"]  # type: ignore[index]

    assert checks["dialogue_density"]["status"] == "fail"
    assert checks["visual_specificity"]["status"] == "fail"
    assert checks["character_presence"]["status"] in {"warn", "fail"}
    assert any("对白" in flag for flag in flags)
