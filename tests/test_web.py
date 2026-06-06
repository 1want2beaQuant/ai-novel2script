from http import HTTPStatus
from http.client import HTTPConnection
import json
import shutil
import subprocess
import sys
from threading import Thread

import pytest

import novel2script
from novel2script.web import convert_payload, create_server, health_payload, preview_payload
import novel2script.web as web_module


MANUSCRIPT = """
Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.
"""


def oversized_json_payload() -> bytes:
    return b'{"text":"' + (b"a" * (web_module.MAX_REQUEST_BYTES + 1)) + b'"}'


def oversized_content_length() -> str:
    return str(web_module.MAX_REQUEST_BYTES + 1)


def numbered_manuscript(chapter_count: int) -> str:
    return "\n\n".join(
        (
            f"Chapter {index} Case File\n"
            f"Mara and Jon investigate clue {index}. "
            f"The scene turns when the file points to room {index}."
        )
        for index in range(1, chapter_count + 1)
    )


def assert_security_headers(response) -> None:
    csp = response.getheader("Content-Security-Policy") or ""
    permissions = response.getheader("Permissions-Policy") or ""

    assert response.getheader("X-Content-Type-Options") == "nosniff"
    assert response.getheader("X-Frame-Options") == "DENY"
    assert response.getheader("Referrer-Policy") == "no-referrer"
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "camera=()" in permissions
    assert "microphone=()" in permissions
    assert "geolocation=()" in permissions


def test_web_version_option_reports_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        web_module.main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"novel2script-web {novel2script.__version__}"


def test_web_module_entrypoint_reports_package_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "novel2script.web", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == f"novel2script-web {novel2script.__version__}"
    assert result.stderr == ""


def test_web_rejects_remote_bind_without_explicit_allow(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        web_module.main(["--host", "0.0.0.0", "--port", "0", "--no-open"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "non-loopback host without --allow-remote" in captured.err


def test_create_server_rejects_remote_bind_without_explicit_allow() -> None:
    with pytest.raises(ValueError, match="non-loopback host without --allow-remote"):
        create_server(host="0.0.0.0", port=0)


def test_create_server_allows_remote_bind_when_explicit() -> None:
    server = create_server(host="0.0.0.0", port=0, allow_remote=True)

    try:
        assert server.server_address[1] > 0
    finally:
        server.server_close()


def test_web_loopback_host_detection() -> None:
    assert web_module._is_loopback_host("127.0.0.1")
    assert web_module._is_loopback_host("localhost")
    assert web_module._is_loopback_host("[::1]")
    assert not web_module._is_loopback_host("0.0.0.0")
    assert not web_module._is_loopback_host("192.168.1.10")


def test_web_same_origin_detection() -> None:
    assert web_module._is_same_origin("http://127.0.0.1:8765", "127.0.0.1:8765")
    assert web_module._is_same_origin("http://localhost:8765", "localhost:8765")
    assert not web_module._is_same_origin("https://127.0.0.1:8765", "127.0.0.1:8765")
    assert not web_module._is_same_origin("http://example.test", "127.0.0.1:8765")


def test_convert_payload_returns_output_and_summary() -> None:
    result = convert_payload(
        {
            "text": MANUSCRIPT,
            "title": "The Locked Room",
            "format": "yaml",
            "provider": "local",
            "validate": True,
        }
    )

    assert result["format"] == "yaml"
    assert "title: The Locked Room" in result["output"]
    assert result["exports"]["yaml"] == result["output"]
    assert "Title: The Locked Room" in result["exports"]["fountain"]
    assert "# The Locked Room 修订简报" in result["exports"]["markdown"]
    assert "## Priority Actions" in result["exports"]["markdown"]
    assert json.loads(result["exports"]["draft_json"])["title"] == "The Locked Room"
    assert json.loads(result["exports"]["summary_json"])["scene_count"] == 3
    assert result["export_manifest"]["selected"] == "yaml"
    assert [file["key"] for file in result["export_manifest"]["files"]] == [
        "yaml",
        "fountain",
        "markdown",
        "draft_json",
        "summary_json",
    ]
    assert result["export_manifest"]["files"][0]["label"] == "YAML"
    assert result["export_manifest"]["files"][0]["extension"] == "yaml"
    assert result["export_manifest"]["files"][0]["byte_size"] == len(
        result["exports"]["yaml"].encode("utf-8")
    )
    assert result["export_manifest"]["bundle"] == {
        "file_count": 5,
        "content_bytes": sum(
            len(content.encode("utf-8")) for content in result["exports"].values()
        ),
    }
    assert result["provider_status"] == {
        "requested": "local",
        "actual": "local",
        "model": novel2script.DEFAULT_MODEL,
        "remote": False,
        "reason": "local_selected",
        "message": "Used the local heuristic provider.",
    }
    assert result["summary"]["title"] == "The Locked Room"
    assert result["summary"]["chapter_count"] == 3
    assert result["summary"]["scene_count"] == 3
    assert result["summary"]["character_count"] >= 1
    assert result["summary"]["chapter_coverage"]["coverage_ratio"] == 1
    assert result["summary"]["adaptation_metrics"]["block_count"] >= 3
    assert [score["area"] for score in result["summary"]["scores"]] == [
        "premise",
        "structure",
        "character",
        "dialogue",
        "visuality",
        "adaptation_fidelity",
    ]
    assert result["summary"]["structure_beats"][0]["id"] == "opening_image"
    assert result["summary"]["scene_map"][0] == {
        "chapter_index": 1,
        "chapter_title": "Chapter 1 The Locked Room",
        "scene_id": "S001",
        "scene_title": "Chapter 1 The Locked Room",
    }
    assert result["summary"]["action_items"][0]["priority"] in {"high", "medium", "low"}
    assert result["summary"]["revision_focus"] == {
        "area": result["summary"]["action_items"][0]["area"],
        "priority": result["summary"]["action_items"][0]["priority"],
        "score": next(
            score["score"]
            for score in result["summary"]["scores"]
            if score["area"] == result["summary"]["action_items"][0]["area"]
        ),
        "note": result["summary"]["action_items"][0]["note"],
        "rationale": next(
            score["rationale"]
            for score in result["summary"]["scores"]
            if score["area"] == result["summary"]["action_items"][0]["area"]
        ),
    }
    assert result["summary"]["strengths"]
    assert result["summary"]["weaknesses"]
    assert result["summary"]["quality_flags"]
    assert result["summary"]["scenes"][0]["summary"]
    assert result["summary"]["scenes"][0]["objective"]
    assert result["summary"]["scenes"][0]["conflict"]
    assert result["summary"]["scenes"][0]["turning_point"]
    assert isinstance(result["summary"]["scenes"][0]["characters"], list)
    assert result["summary"]["scenes"][0]["block_counts"]["total"] >= 1
    assert result["summary"]["scenes"][0]["block_counts"]["action"] >= 1
    assert result["summary"]["scenes"][0]["blocks_preview"][0]["type"] == "action"
    assert result["summary"]["scenes"][0]["blocks_preview"][0]["text"]
    story_bible = result["summary"]["story_bible"]
    assert story_bible["characters"][0]["name"]
    assert story_bible["characters"][0]["continuity_note"]
    assert story_bible["locations"][0]["scene_ids"]
    assert isinstance(story_bible["props"], list)
    assert story_bible["open_questions"]


def test_convert_payload_summary_includes_all_scene_index_entries() -> None:
    result = convert_payload(
        {
            "text": numbered_manuscript(13),
            "title": "Long Case",
            "format": "yaml",
            "provider": "local",
        }
    )

    assert result["summary"]["scene_count"] == 13
    assert len(result["summary"]["scenes"]) == result["summary"]["scene_count"]
    assert result["summary"]["scenes"][-1]["source_chapter"] == 13


def test_convert_payload_supports_fountain_output() -> None:
    result = convert_payload(
        {
            "text": MANUSCRIPT,
            "title": "The Locked Room",
            "format": "fountain",
            "provider": "local",
        }
    )

    assert result["format"] == "fountain"
    assert "Title: The Locked Room" in result["output"]
    assert "// source_chapter: 3" in result["output"]
    assert "title: The Locked Room" in result["exports"]["yaml"]
    assert result["exports"]["fountain"] == result["output"]


def test_convert_payload_supports_markdown_revision_brief() -> None:
    result = convert_payload(
        {
            "text": MANUSCRIPT,
            "title": "The Locked Room",
            "format": "markdown",
            "provider": "local",
        }
    )

    assert result["format"] == "markdown"
    assert result["output"] == result["exports"]["markdown"]
    assert result["output"].startswith("# The Locked Room 修订简报\n")
    assert "## Coverage" in result["output"]
    assert "## Structure Beats" in result["output"]
    assert "Title: The Locked Room" in result["exports"]["fountain"]
    assert "title: The Locked Room" in result["exports"]["yaml"]


def test_convert_payload_reports_openai_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = convert_payload(
        {
            "text": MANUSCRIPT,
            "title": "The Locked Room",
            "format": "yaml",
            "provider": "openai",
            "model": "gpt-test",
        }
    )

    assert result["provider_status"] == {
        "requested": "openai",
        "actual": "local",
        "model": "gpt-test",
        "remote": False,
        "reason": "missing_api_key",
        "message": "OPENAI_API_KEY is not set; used the local heuristic provider.",
    }
    assert result["summary"]["title"] == "The Locked Room"


def test_health_payload_reports_runtime_metadata() -> None:
    assert health_payload() == {
        "status": "ok",
        "version": novel2script.__version__,
        "default_model": novel2script.DEFAULT_MODEL,
        "max_request_bytes": web_module.MAX_REQUEST_BYTES,
    }


def test_convert_payload_rejects_missing_text() -> None:
    try:
        convert_payload({"text": "", "format": "yaml"})
    except ValueError as exc:
        assert "Manuscript text is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_convert_payload_rejects_non_boolean_validate() -> None:
    with pytest.raises(ValueError, match="validate must be a boolean"):
        convert_payload({"text": MANUSCRIPT, "format": "yaml", "validate": "false"})


def test_convert_payload_rejects_non_string_title() -> None:
    with pytest.raises(ValueError, match="title must be a string"):
        convert_payload({"text": MANUSCRIPT, "format": "yaml", "title": 123})


def test_convert_payload_rejects_non_string_format() -> None:
    with pytest.raises(ValueError, match="format must be a string"):
        convert_payload({"text": MANUSCRIPT, "format": ["yaml"]})


def test_convert_payload_rejects_non_string_provider() -> None:
    with pytest.raises(ValueError, match="provider must be a string"):
        convert_payload({"text": MANUSCRIPT, "format": "yaml", "provider": 1})


def test_convert_payload_rejects_non_string_model() -> None:
    with pytest.raises(ValueError, match="Model must be a non-empty string"):
        convert_payload({"text": MANUSCRIPT, "format": "yaml", "model": 1})


def test_convert_payload_rejects_blank_model() -> None:
    with pytest.raises(ValueError, match="Model must be a non-empty string"):
        convert_payload({"text": MANUSCRIPT, "format": "yaml", "model": "  "})


def test_preview_payload_reports_authoritative_chapter_preflight() -> None:
    two_chapters = """
第 1 章
只有一章。

第 2 章
只有两章。
"""

    result = preview_payload({"text": two_chapters})

    assert result["ready"] is False
    assert result["chapter_count"] == 2
    assert result["short_chapter_count"] == 2
    assert result["chapters"] == [
        {
            "index": 1,
            "title": "第 1 章",
            "character_count": 5,
            "status": "short",
            "warning": "正文偏短，转换结果可能只有概要。",
        },
        {
            "index": 2,
            "title": "第 2 章",
            "character_count": 5,
            "status": "short",
            "warning": "正文偏短，转换结果可能只有概要。",
        },
    ]
    assert result["preflight_warnings"] == ["有 2 个章节正文偏短，建议补充素材后再转换。"]
    assert "至少需要 3 个" in result["message"]

    ready = preview_payload({"text": MANUSCRIPT})

    assert ready["ready"] is True
    assert ready["chapter_count"] == 3
    assert ready["short_chapter_count"] == 0
    assert ready["chapters"][0]["title"] == "Chapter 1 The Locked Room"
    assert ready["chapters"][0]["status"] == "ready"
    assert ready["chapters"][0]["character_count"] == 76
    assert ready["preflight_warnings"] == []


def test_web_server_serves_static_assets_and_conversion_api() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request("GET", "/")
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        assert response.status == HTTPStatus.OK
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert "novel2script Studio" in body
        assert f'id="modelInput" type="text" value="{novel2script.DEFAULT_MODEL}"' in body
        assert 'id="draftStatus"' in body
        assert "示例草稿" in body
        assert 'id="fileButton"' in body
        assert 'id="clearButton"' in body
        assert "清空当前工作台" in body
        assert "Adaptation Inspector" in body
        assert 'aria-label="转换状态"' in body
        assert 'id="inputSize"' in body
        assert 'id="providerMode"' in body
        assert 'id="conversionState"' in body
        assert 'id="exportState"' in body
        assert 'id="remoteConfirmPanel"' in body
        assert 'aria-label="OpenAI 远程转换确认"' in body
        assert 'id="remoteConfirmModel"' in body
        assert 'id="remoteConfirmTitle"' in body
        assert 'id="remoteConfirmSize"' in body
        assert 'id="remoteConfirmCancel"' in body
        assert 'id="remoteConfirmProceed"' in body
        assert "确认发送" in body
        assert 'aria-label="工作流进度"' in body
        assert 'data-workflow-step="input"' in body
        assert 'data-workflow-step="preview"' in body
        assert 'data-workflow-step="convert"' in body
        assert 'data-workflow-step="export"' in body
        assert 'id="inputStepMeta"' in body
        assert 'id="previewStepMeta"' in body
        assert 'id="convertStepMeta"' in body
        assert 'id="exportStepMeta"' in body
        assert 'class="pane input-pane"' in body
        assert 'id="inputDropZone"' in body
        assert 'class="manuscript-drop-area"' in body
        assert 'id="dropOverlay"' in body
        assert 'class="drop-overlay"' in body
        assert "放开导入手稿" in body
        assert 'id="chapterPreviewState"' in body
        assert 'id="chapterPreviewList"' in body
        assert "章节预检" in body
        assert 'id="bundleButton"' in body
        assert "打包下载所有导出文件" in body
        assert 'class="export-manifest"' in body
        assert 'id="exportBundleMeta"' in body
        assert 'id="exportManifestList"' in body
        assert "导出清单" in body
        assert 'class="output-tabs"' in body
        assert 'data-output-format="yaml"' in body
        assert 'data-output-format="fountain"' in body
        assert 'value="markdown"' in body
        assert 'data-output-format="markdown"' in body
        assert "Revision" in body
        assert 'data-output-format="draftJson"' in body
        assert 'data-output-format="summaryJson"' in body
        assert 'id="scoresList"' in body
        assert 'id="actionItems"' in body
        assert 'class="revision-focus"' in body
        assert 'id="revisionFocusArea"' in body
        assert 'id="revisionFocusPriority"' in body
        assert 'id="revisionFocusScore"' in body
        assert 'id="revisionFocusNote"' in body
        assert "下一轮修订重点" in body
        assert 'class="scene-map-panel"' in body
        assert 'id="sceneMapList"' in body
        assert "章节映射" in body
        assert 'class="scene-filter"' in body
        assert 'id="sceneFilterInput"' in body
        assert 'id="sceneFilterClear"' in body
        assert 'id="sceneFilterMeta"' in body
        assert "筛选场景索引" in body
        assert 'class="story-bible-grid"' in body
        assert 'id="storyCharactersList"' in body
        assert 'id="storyLocationsList"' in body
        assert 'id="storyPropsList"' in body
        assert 'id="storyQuestionsList"' in body
        assert "人物连续性" in body
        assert "道具 / 线索" in body

        preview_payload_bytes = json.dumps({"text": MANUSCRIPT}).encode("utf-8")
        connection.request(
            "POST",
            "/api/preview",
            body=preview_payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://{host}:{port}",
            },
        )
        response = connection.getresponse()
        preview = json.loads(response.read().decode("utf-8"))
        assert response.status == HTTPStatus.OK
        assert response.getheader("Cache-Control") == "no-store"
        assert preview["ready"] is True
        assert preview["chapter_count"] == 3
        assert preview["chapters"][0]["title"] == "Chapter 1 The Locked Room"
        assert preview["chapters"][0]["status"] == "ready"
        assert preview["chapters"][0]["character_count"] == 76

        payload = json.dumps({"text": MANUSCRIPT, "format": "fountain"}).encode("utf-8")
        connection.request(
            "POST",
            "/api/convert",
            body=payload,
            headers={
                "Content-Type": "application/json",
                "Origin": f"http://{host}:{port}",
            },
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        assert response.status == HTTPStatus.OK
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert data["format"] == "fountain"
        assert data["summary"]["scene_count"] == 3
        assert data["summary"]["chapter_coverage"]["coverage_ratio"] == 1
        assert data["summary"]["structure_beats"]
        assert data["summary"]["scene_map"][0]["scene_id"] == "S001"
        assert data["summary"]["scenes"][0]["block_counts"]["total"] >= 1
        assert data["summary"]["scenes"][0]["blocks_preview"][0]["text"]
        assert data["summary"]["scenes"][0]["objective"]
        assert data["summary"]["scenes"][0]["conflict"]
        assert data["summary"]["scenes"][0]["turning_point"]
        assert data["summary"]["action_items"]
        assert data["summary"]["revision_focus"]["note"] == data["summary"]["action_items"][0]["note"]
        assert data["summary"]["story_bible"]["characters"]
        assert data["summary"]["story_bible"]["locations"]
        assert data["summary"]["story_bible"]["open_questions"]
        assert data["export_manifest"]["selected"] == "fountain"
        assert data["export_manifest"]["bundle"]["file_count"] == 5
        assert data["export_manifest"]["bundle"]["content_bytes"] > 0
        assert "title:" in data["exports"]["yaml"]
        assert data["exports"]["fountain"] == data["output"]
        assert "# Chapter 1 The Locked Room 修订简报" in data["exports"]["markdown"]
        assert json.loads(data["exports"]["draft_json"])["source"]["chapter_count"] == 3
        assert json.loads(data["exports"]["summary_json"])["scene_count"] == 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_static_assets_include_conversion_status_ui() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request("GET", "/app.js")
        response = connection.getresponse()
        script = response.read().decode("utf-8")
        normalized_script = script.replace("\r\n", "\n")

        assert response.status == HTTPStatus.OK
        assert 'fetch("/api/preview"' in script
        assert "function countCharacters" in script
        assert "function estimateChapterCount" not in script
        assert "window.confirm" not in script
        assert "function confirmRemoteProvider" in script
        assert "function requestRemoteConfirmation" in script
        assert "function resolveRemoteConfirmation" in script
        assert "function dismissRemoteConfirmation" in script
        assert "remoteConfirmationResolve" in script
        assert "remoteConfirmProceed" in script
        assert "function remoteConfirmationKey" in script
        assert "function textFingerprint" in script
        assert f'const defaultModel = "{novel2script.DEFAULT_MODEL}"' in script
        assert 'fetch("/api/health")' in script
        assert "Ready v${health.version}" in script
        assert 'readJsonResponse(response, "服务状态响应无法解析。")' in script
        assert 'setStatusTone(elements.serverStatus, "ready")' in script
        assert 'const localDraftStorageKey = "novel2script:web:local-draft:v1"' in script
        assert "const localDraftVersion = 1" in script
        assert "draftSaveTimer" in script
        assert "function initializeWorkbench" in script
        assert "function restoreLocalDraft" in script
        assert "function isLocalDraft" in script
        assert "function scheduleLocalDraftSave" in script
        assert "function saveLocalDraft" in script
        assert "function localDraftStorage" in script
        assert "window.localStorage" in script
        assert "function removeLocalDraft" in script
        assert "function setDraftStatus" in script
        assert "已恢复浏览器本地草稿，等待章节预检。" in script
        assert "本地草稿为空，等待手稿输入。" in script
        assert "草稿已保存" in script
        assert "保存不可用" in script
        assert "保存失败" in script
        assert "saveLocalDraft()" in script
        assert "scheduleLocalDraftSave()" in script
        assert "openAiConfirmedFor" in script
        assert "isPreviewPending" in script
        assert "isPreviewReady" in script
        assert "previewAbortController" in script
        assert "new AbortController" in script
        assert "function abortPreviewRequest" in script
        assert "state.previewAbortController.abort()" in script
        assert "signal," in script
        assert 'error.name === "AbortError"' in script
        assert "workflowSteps" in script
        assert "function updateWorkflowSteps" in script
        assert "function setWorkflowStep" in script
        assert 'document.querySelectorAll("[data-workflow-step]")' in script
        assert "解析章节中" in script
        assert "结果已过期" in script
        assert "selectedOutputLabel()} 可用" in script
        assert "等待远程确认" in script
        assert "textFingerprint(text)" in script
        assert "function showPreflightBlockedConversion" in script
        assert "function renderChapterPreview" in script
        assert "function renderSceneMap" in script
        assert "sceneMapList" in script
        assert "转换后显示源章节到生成场景的逐章映射。" in script
        assert "转换后显示全部场景的章节来源、地点和人物。" in script
        assert "function appendSceneDramaticItem" in script
        assert "scene-dramatic-list" in script
        assert "scene.objective" in script
        assert "scene.conflict" in script
        assert "scene.turning_point" in script
        assert "function blockTypeLabel" in script
        assert "blocks_preview" in script
        assert "scene-block-preview" in script
        assert "block-type-dialogue" in script
        assert "sceneFilterInput" in script
        assert "sceneFilterClear" in script
        assert "sceneFilterMeta" in script
        assert "visibleScenes" in script
        assert "sceneFilter" in script
        assert "function sceneMatchesFilter" in script
        assert "function sceneSearchText" in script
        assert "function renderSceneFilterMeta" in script
        assert "function updateSceneFilter" in script
        assert "function clearSceneFilter" in script
        assert "没有匹配" in script
        assert "匹配 ${filteredCount} / ${totalCount} 场" in script
        assert 'elements.sceneFilterInput.addEventListener("input", updateSceneFilter)' in script
        assert 'elements.sceneFilterClear.addEventListener("click", clearSceneFilter)' in script
        assert "function renderStoryBible" in script
        assert "function renderStoryCharacters" in script
        assert "function renderStoryLocations" in script
        assert "function renderStoryProps" in script
        assert "storyCharactersList" in script
        assert "storyLocationsList" in script
        assert "storyPropsList" in script
        assert "storyQuestionsList" in script
        assert "转换后显示主要人物的首次出场和连续性复核提示。" in script
        assert "转换后显示地点资产和关联场景。" in script
        assert "转换后显示道具、线索和来源章节。" in script
        assert "chapterPreviewState" in script
        assert "chapterPreviewList" in script
        assert "preview.chapters || []" in script
        assert "previewWarningCount" in script
        assert "short_chapter_count" in script
        assert "可转换 / 需补素材" in script
        assert "章需补素材" in script
        assert "素材偏短" in script
        assert "chapter-preview-content" in script
        assert "还有 ${chapterItems.length - limit} 章未显示" in script
        assert "正在解析章节" in script
        assert "const payload = conversionPayload()" in script
        assert "state.lastConvertedInput = payload.text" in script
        assert "updateConversionFreshness()" in script
        assert "至少需要 3 章通过预检后才能转换。" in script
        assert "state.isPreviewPending" in script
        assert "!state.isPreviewReady" in script
        assert "Boolean(state.remoteConfirmationResolve)" in script
        assert "remoteConfirmationReturnFocus" in script
        assert "function handleRemoteConfirmationKeydown" in script
        assert 'event.key !== "Escape"' in script
        assert "resolveRemoteConfirmation(false, { restoreFocus: true })" in script
        assert "function restoreRemoteConfirmationFocus" in script
        assert "elements.convert.focus()" in script
        assert (
            'elements.remoteConfirmPanel?.addEventListener("keydown", '
            "handleRemoteConfirmationKeydown)"
        ) in script
        assert "未确认远程发送" in script
        assert "需重新转换" in script
        assert "function currentOutputStaleReason" in script
        assert (
            "function refreshExportReadiness() {\n"
            "  updateExportStatus();\n"
            "  renderExportManifest();\n"
            "}" in normalized_script
        )
        assert "setOutputActions(false)" in script
        assert "setOutputActions(true)" in script
        assert "elements.bundle.disabled = !isEnabled" in script
        assert "button.disabled = !isEnabled" not in script
        assert "model: normalizedModel()" in script
        assert "lastValidate" in script
        assert "当前导出可能不是最新" in script
        assert "Schema 校验设置已变更" in script
        assert "Schema 校验设置已变更，当前导出仍使用旧设置。" in script
        assert "转换前会按当前手稿、片名和模型确认远程发送。" in script
        assert "请确认 OpenAI 远程发送后再开始转换" in script
        assert "手稿、片名、模型或模式已变化，请重新检查后再确认远程发送。" in script
        assert "OpenAI 模型已变更" in script
        assert "return elements.model.value.trim() || defaultModel" in script
        assert "重新转换后再复制、下载或打包。" in script
        assert "正在生成新结果，完成后再复制、下载或打包。" in script
        assert "const downloadsDisabled = state.isWorking || isStale" in script
        assert "downloadButton.disabled = downloadsDisabled" in script
        assert "if (state.isWorking || !state.output)" in script
        assert "if (state.isWorking || !state.output || !state.exports)" in script
        assert "function renderProviderRunStatus" in script
        assert "function providerStatusSummary" in script
        assert "本地回退" in script
        assert "OPENAI_API_KEY 未设置，实际使用本地转换。" in script
        assert "const defaultMaxRequestBytes = 2000000" in script
        assert "let maxRequestBytes = defaultMaxRequestBytes" in script
        assert "function updateRuntimeRequestLimit" in script
        assert "health?.max_request_bytes" in script
        assert "maxRequestBytes = normalizedLimit" in script
        assert "new TextEncoder" in script
        assert "function isCurrentRequestTooLarge" in script
        assert "function importedFileRequestByteLength" in script
        assert "function importFile" in script
        assert "function isImportableTextFile" in script
        assert "name.endsWith(\".txt\") || type === \"text/plain\"" in script
        assert "type.startsWith(\"text/\")" not in script
        assert "function showFileImportTypeError" in script
        assert "仅支持 .txt 或 text/plain 文本文件，当前手稿已保留。" in script
        assert "请选择 .txt 文本手稿" in script
        assert "不是可导入的文本手稿。" in script
        assert "await importFile(file, { resetPicker: true })" in script
        assert "function handleDropZoneDragEnter" in script
        assert "function handleDropZoneDragOver" in script
        assert "function handleDropZoneDragLeave" in script
        assert "function handleDropZoneDrop" in script
        assert "function setDropZoneActive" in script
        assert "state.dragDepth += 1" in script
        assert "event.dataTransfer.dropEffect = \"copy\"" in script
        assert "event.dataTransfer.dropEffect = \"none\"" in script
        assert "if (state.isWorking)" in script
        assert "state.dragDepth = 0" in script
        assert "void importFile(file)" in script
        assert "没有检测到可导入的文本文件。" in script
        assert "elements.inputDropZone?.classList.toggle(\"is-drop-active\", isActive)" in script
        assert "elements.dropOverlay.setAttribute(\"aria-hidden\", String(!isActive))" in script
        assert 'elements.inputDropZone?.addEventListener("dragenter", handleDropZoneDragEnter)' in script
        assert 'elements.inputDropZone?.addEventListener("dragover", handleDropZoneDragOver)' in script
        assert 'elements.inputDropZone?.addEventListener("dragleave", handleDropZoneDragLeave)' in script
        assert 'elements.inputDropZone?.addEventListener("drop", handleDropZoneDrop)' in script
        assert "function showFileImportSizeError" in script
        assert "文件过大，未导入" in script
        assert "function showFileImportReadError" in script
        assert "文件读取失败，当前手稿已保留" in script
        assert "setConversionStatus(\"导入失败\"" in script
        assert "elements.file.value = \"\"" in script
        assert "function clearWorkbench" in script
        assert "function clearLocalDraft" in script
        assert "elements.clear.addEventListener(\"click\", clearWorkbench)" in script
        assert "elements.clear.disabled = isWorking" in script
        assert "setDropZoneActive(false)" in script
        assert "state.openAiConfirmedFor = \"\"" in script
        assert "state.exports = null" in script
        assert "state.previewRequestId += 1" in script
        assert "elements.manuscript.value = \"\"" in script
        assert "elements.title.value = \"\"" in script
        assert "clearLocalDraft()" in script
        assert "草稿已清除" in script
        assert "storage.removeItem(localDraftStorageKey)" in script
        assert "工作台已清空，等待手稿输入。" in script
        assert (
            'elements.manuscript.value = text;\n  if (options.resetPicker) {\n    elements.file.value = "";'
            in normalized_script
        )
        assert "function copyOutput" in script
        assert "navigator.clipboard?.writeText" in script
        assert "const staleReason = currentOutputStaleReason()" in script
        assert "复制失败" in script
        assert "浏览器未允许写入剪贴板，请手动选中结果复制。" in script
        assert "function downloadOutput" in script
        assert "function downloadExportFile" in script
        assert "downloadExportFile(state.selectedOutput, { updatePrimaryButton: true })" in script
        assert "downloadLabelTimer" in script
        assert "selectedOutput" in script
        assert "function selectedOutputLabel" in script
        assert "function outputForSelection" in script
        assert "function selectOutput" in script
        assert "function selectOutputFromTab" in script
        assert "function renderOutputTabs" in script
        assert "function handleOutputTabKeydown" in script
        assert "function outputExtension" in script
        assert "data-output-format" in script
        assert "button.dataset.outputFormat" in script
        assert "button.tabIndex = state.exports && isSelected ? 0 : -1" in script
        assert "ArrowLeft" in script
        assert "ArrowRight" in script
        assert 'event.key === "Home"' in script
        assert 'event.key === "End"' in script
        assert "event.preventDefault()" in script
        assert 'button.addEventListener("keydown", handleOutputTabKeydown)' in script
        assert "function outputSelectionForFormat" in script
        assert 'format === "fountain" || format === "markdown"' in script
        assert "state.output = outputForSelection(state.selectedOutput)" in script
        assert "selectOutput(selection)" in script
        assert "const isStale = Boolean(currentOutputStaleReason())" in script
        assert 'isStale ? "is-stale" : ""' in script
        assert "downloadButton.disabled = downloadsDisabled" in script
        assert "refreshExportReadiness()" in script
        assert "item.dataset.exportKey = file.key" in script
        assert 'item.setAttribute("aria-current", "true")' in script
        assert 'viewButton.dataset.exportAction = "view"' in script
        assert 'downloadButton.dataset.exportAction = "download"' in script
        assert 'viewButton.addEventListener("click", () => selectOutput(file.key))' in script
        assert (
            'downloadButton.addEventListener("click", () => downloadExportFile(file.key))'
            in script
        )
        assert "export-file-detail" in script
        assert "export-file-actions" in script
        assert "已开始下载。" in script
        assert "markdown" in script
        assert "Revision brief" in script
        assert "draftJson" in script
        assert "summaryJson" in script
        assert 'return "revision.md"' in script
        assert 'return "draft.json"' in script
        assert 'return "summary.json"' in script
        assert "function downloadBundle" in script
        assert "function createZipBlob" in script
        assert "function exportBundleFiles" in script
        assert "function buildCrc32Table" in script
        assert "function crc32" in script
        assert "const crc32Table = buildCrc32Table()" in script
        assert "state.exports = normalizeExports(result)" in script
        assert "state.exports = null" in script
        assert 'link.download = `${downloadBaseName()}-export.zip`' in script
        assert 'name: `${baseName}.revision.md`' in script
        assert 'new Blob(chunks, { type: "application/zip" })' in script
        assert "localView.setUint16(6, 0x0800, true)" in script
        assert "centralView.setUint16(8, 0x0800, true)" in script
        assert "elements.bundle.addEventListener(\"click\", downloadBundle)" in script
        assert "浏览器未能生成打包文件，请分别下载或复制结果。" in script
        assert "function downloadBaseName" in script
        assert "function safeFilenameSegment" in script
        assert 'safeTitle || "novel2script-draft"' in script
        assert ".replace(/[<>:\"/\\\\|?*\\u0000-\\u001f]/g, \"-\")" in script
        assert "link.download = `${downloadBaseName()}.${extension}`" in script
        assert "下载失败" in script
        assert "浏览器未能启动下载，请复制结果后手动保存。" in script
        assert "function syncConvertAvailability" in script
        assert "手稿过大，请拆分后再预检或转换。" in script
        assert "function readJsonResponse" in script
        assert "服务返回了无法解析的转换响应。" in script
        assert "服务返回了无法解析的预检响应。" in script
        assert "预检失败：" in script
        assert "setConversionStatus(\"预检失败\"" in script
        assert "conversionSummary" in script

        connection.request("GET", "/app.css")
        response = connection.getresponse()
        stylesheet = response.read().decode("utf-8")

        assert response.status == HTTPStatus.OK
        assert ".status-grid" in stylesheet
        assert ".remote-confirmation" in stylesheet
        assert ".remote-confirmation.is-hidden" in stylesheet
        assert ".remote-confirmation-facts" in stylesheet
        assert ".remote-confirmation-actions" in stylesheet
        assert ".workflow-steps" in stylesheet
        assert ".workflow-step" in stylesheet
        assert ".workflow-step.is-ready .step-index" in stylesheet
        assert ".workflow-step.is-error .step-index" in stylesheet
        assert ".topbar-status" in stylesheet
        assert ".status-pill.is-ready" in stylesheet
        assert ".status-pill.is-warn" in stylesheet
        assert ".status-card.is-warn strong" in stylesheet
        assert ".status-card.is-error strong" in stylesheet
        assert ".input-pane" in stylesheet
        assert ".manuscript-drop-area" in stylesheet
        assert ".manuscript-drop-area.is-drop-active textarea" in stylesheet
        assert ".drop-overlay" in stylesheet
        assert ".manuscript-drop-area.is-drop-active .drop-overlay" in stylesheet
        assert ".chapter-preview" in stylesheet
        assert ".chapter-preview-list li" in stylesheet
        assert ".chapter-preview-list li.is-short" in stylesheet
        assert ".chapter-preview-content" in stylesheet
        assert ".chapter-preview.is-ready .chapter-preview-head strong" in stylesheet
        assert ".scene-block-meta" in stylesheet
        assert ".scene-dramatic-list" in stylesheet
        assert ".scene-dramatic-list dt" in stylesheet
        assert ".scene-dramatic-list dd" in stylesheet
        assert ".scene-block-preview" in stylesheet
        assert ".block-type-dialogue" in stylesheet
        assert ".scene-filter" in stylesheet
        assert ".scene-filter input" in stylesheet
        assert ".scene-filter button" in stylesheet
        assert ".scene-filter-meta" in stylesheet
        assert ".output-tabs" in stylesheet
        assert ".output-tabs button.is-selected" in stylesheet
        assert ".export-file-detail" in stylesheet
        assert ".export-file-actions" in stylesheet
        assert ".export-file-actions button" in stylesheet
        assert ".export-manifest-list li.is-stale" in stylesheet
        assert ".scene-map-panel" in stylesheet
        assert ".scene-map-list" in stylesheet
        assert ".story-bible-grid" in stylesheet
        assert ".story-bible-panel" in stylesheet
        assert ".asset-list" in stylesheet
        assert ".story-question-list" in stylesheet
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_static_javascript_is_parseable() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available for static JavaScript syntax checks.")

    result = subprocess.run(
        [node, "--check", "src/novel2script/web/static/app.js"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_web_server_rejects_non_json_convert_request() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request(
            "POST",
            "/api/convert",
            body=b"text=not-json",
            headers={"Content-Type": "text/plain"},
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.BAD_REQUEST
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert data == {"error": "Request Content-Type must be application/json."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_supports_head_without_body() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request("HEAD", "/api/health")
        response = connection.getresponse()
        body = response.read()

        assert response.status == HTTPStatus.OK
        assert response.getheader("Content-Type") == "application/json; charset=utf-8"
        expected_length = len(json.dumps(health_payload(), ensure_ascii=False).encode("utf-8"))
        assert response.getheader("Content-Length") == str(expected_length)
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert body == b""
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_options_reports_allowed_methods() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request("OPTIONS", "/api/convert")
        response = connection.getresponse()
        body = response.read()

        assert response.status == HTTPStatus.NO_CONTENT
        assert response.getheader("Allow") == web_module.ALLOWED_METHODS_HEADER
        assert response.getheader("Content-Length") == "0"
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert body == b""
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_unsupported_methods_with_json() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for method in ("PUT", "PATCH", "DELETE", "TRACE"):
            connection = HTTPConnection(host, port, timeout=10)
            connection.request(method, "/api/convert")
            response = connection.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            assert response.status == HTTPStatus.METHOD_NOT_ALLOWED
            assert response.getheader("Allow") == web_module.ALLOWED_METHODS_HEADER
            assert response.getheader("Content-Type") == "application/json; charset=utf-8"
            assert response.getheader("Cache-Control") == "no-store"
            assert_security_headers(response)
            assert data == {"error": "Method not allowed."}
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_unknown_methods_with_json() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        connection.request("BREW", "/api/convert")
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.METHOD_NOT_ALLOWED
        assert response.getheader("Allow") == web_module.ALLOWED_METHODS_HEADER
        assert response.getheader("Content-Type") == "application/json; charset=utf-8"
        assert response.getheader("Cache-Control") == "no-store"
        assert_security_headers(response)
        assert data == {"error": "Method not allowed."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_accepts_utf8_bom_json_payload() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        payload = json.dumps({"text": MANUSCRIPT, "format": "yaml"}).encode("utf-8-sig")
        connection.request(
            "POST",
            "/api/convert",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.OK
        assert_security_headers(response)
        assert data["summary"]["chapter_count"] == 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_invalid_content_length() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for content_length in ("not-a-number", "-1"):
            connection = HTTPConnection(host, port, timeout=10)
            connection.putrequest("POST", "/api/preview")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", content_length)
            connection.endheaders()
            response = connection.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            assert response.status == HTTPStatus.BAD_REQUEST
            assert response.getheader("Cache-Control") == "no-store"
            assert data == {"error": "Invalid request length."}
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_empty_json_payload() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for path in ("/api/convert", "/api/preview"):
            connection = HTTPConnection(host, port, timeout=10)
            connection.request("POST", path, body=b"", headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            assert response.status == HTTPStatus.BAD_REQUEST
            assert_security_headers(response)
            assert data == {"error": "Request body is required."}
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_non_object_json_payload() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for path, payload in (
            ("/api/convert", b'["text"]'),
            ("/api/preview", b'"text"'),
            ("/api/preview", b"null"),
        ):
            connection = HTTPConnection(host, port, timeout=10)
            connection.request(
                "POST",
                path,
                body=payload,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            assert response.status == HTTPStatus.BAD_REQUEST
            assert_security_headers(response)
            assert data == {"error": "Request body must be a JSON object."}
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_oversized_json_payload() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        for path in ("/api/convert", "/api/preview"):
            connection = HTTPConnection(host, port, timeout=10)
            connection.putrequest("POST", path)
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", oversized_content_length())
            connection.endheaders()
            response = connection.getresponse()
            data = json.loads(response.read().decode("utf-8"))

            assert response.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            assert_security_headers(response)
            assert data == {"error": "Request body is too large."}
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_rejects_cross_origin_convert_request() -> None:
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        payload = json.dumps({"text": MANUSCRIPT, "format": "yaml"}).encode("utf-8")
        connection.request(
            "POST",
            "/api/convert",
            body=payload,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://example.test",
            },
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.BAD_REQUEST
        assert_security_headers(response)
        assert data == {"error": "Request Origin must match the local Web UI host."}

        connection.request(
            "POST",
            "/api/preview",
            body=payload,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://example.test",
            },
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.BAD_REQUEST
        assert_security_headers(response)
        assert data == {"error": "Request Origin must match the local Web UI host."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_reports_unexpected_conversion_error(
    monkeypatch,
) -> None:
    def fail_conversion(payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(web_module, "convert_payload", fail_conversion)
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        payload = json.dumps({"text": MANUSCRIPT, "format": "yaml"}).encode("utf-8")
        connection.request(
            "POST",
            "/api/convert",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert_security_headers(response)
        assert data == {"error": "Conversion failed unexpectedly."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_server_reports_unexpected_preview_error(
    monkeypatch,
) -> None:
    def fail_preview(payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(web_module, "preview_payload", fail_preview)
    server = create_server(port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        connection = HTTPConnection(host, port, timeout=10)
        payload = json.dumps({"text": MANUSCRIPT}).encode("utf-8")
        connection.request(
            "POST",
            "/api/preview",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        assert response.status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert_security_headers(response)
        assert data == {"error": "Preview failed unexpectedly."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
