import builtins

import pytest

import novel2script.ai_provider as ai_provider
from novel2script.ai_provider import convert_with_optional_ai


SAMPLE = """
第 1 章 雨夜
林晚在书房里发现一封旧信。

第 2 章 空屋
周岚说：我们不能再等了。

第 3 章 码头
两人在码头找到最后的线索。
"""


def test_openai_provider_without_key_uses_local_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    draft = convert_with_optional_ai(SAMPLE, title="雾城来信", provider="openai", model="test")

    data = draft.to_dict()
    assert data["title"] == "雾城来信"
    assert data["coverage_report"]["model"] == "screenplay_coverage_v1"


def test_openai_provider_without_optional_dependency_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def import_without_openai(name: str, *args: object, **kwargs: object) -> object:
        if name == "openai":
            raise ModuleNotFoundError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(builtins, "__import__", import_without_openai)

    with pytest.raises(ValueError, match=r"novel2script\[ai\]"):
        convert_with_optional_ai(SAMPLE, title="雾城来信", provider="openai", model="test")


def test_openai_provider_wraps_sdk_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_enhancement(*args: object, **kwargs: object) -> dict[str, object]:
        raise RuntimeError("upstream unavailable")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_provider, "_enhance_with_openai", fail_enhancement)

    with pytest.raises(ValueError, match="OpenAI enhancement failed: upstream unavailable"):
        convert_with_optional_ai(SAMPLE, title="雾城来信", provider="openai", model="test")
