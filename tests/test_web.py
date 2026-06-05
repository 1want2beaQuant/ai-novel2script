from http import HTTPStatus
from http.client import HTTPConnection
import json
import shutil
import subprocess
import sys
from threading import Thread

import pytest

import novel2script
from novel2script.web import convert_payload, create_server, preview_payload
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
    assert result["provider_status"] == {
        "requested": "local",
        "actual": "local",
        "model": "gpt-4.1-mini",
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
    assert result["summary"]["action_items"][0]["priority"] in {"high", "medium", "low"}
    assert result["summary"]["strengths"]
    assert result["summary"]["weaknesses"]
    assert result["summary"]["quality_flags"]
    assert result["summary"]["scenes"][0]["summary"]
    assert isinstance(result["summary"]["scenes"][0]["characters"], list)


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
    assert result["chapters"] == [
        {"index": 1, "title": "第 1 章"},
        {"index": 2, "title": "第 2 章"},
    ]
    assert "至少需要 3 个" in result["message"]

    ready = preview_payload({"text": MANUSCRIPT})

    assert ready["ready"] is True
    assert ready["chapter_count"] == 3
    assert ready["chapters"][0]["title"] == "Chapter 1 The Locked Room"


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
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Referrer-Policy") == "no-referrer"
        assert response.getheader("Cache-Control") == "no-store"
        assert "default-src 'self'" in (response.getheader("Content-Security-Policy") or "")
        assert "novel2script Studio" in body
        assert 'id="fileButton"' in body
        assert "Adaptation Inspector" in body
        assert 'aria-label="转换状态"' in body
        assert 'id="inputSize"' in body
        assert 'id="providerMode"' in body
        assert 'id="conversionState"' in body
        assert 'id="exportState"' in body
        assert 'class="pane input-pane"' in body
        assert 'id="chapterPreviewState"' in body
        assert 'id="chapterPreviewList"' in body
        assert "章节预检" in body
        assert 'id="scoresList"' in body
        assert 'id="actionItems"' in body

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
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Referrer-Policy") == "no-referrer"
        assert response.getheader("Cache-Control") == "no-store"
        assert data["format"] == "fountain"
        assert data["summary"]["scene_count"] == 3
        assert data["summary"]["chapter_coverage"]["coverage_ratio"] == 1
        assert data["summary"]["structure_beats"]
        assert data["summary"]["action_items"]
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

        assert response.status == HTTPStatus.OK
        assert 'fetch("/api/preview"' in script
        assert "function countCharacters" in script
        assert "function estimateChapterCount" not in script
        assert "function confirmRemoteProvider" in script
        assert "function remoteConfirmationKey" in script
        assert "function textFingerprint" in script
        assert 'const defaultModel = "gpt-4.1-mini"' in script
        assert "openAiConfirmedFor" in script
        assert "isPreviewPending" in script
        assert "isPreviewReady" in script
        assert "textFingerprint(text)" in script
        assert "function showPreflightBlockedConversion" in script
        assert "function renderChapterPreview" in script
        assert "chapterPreviewState" in script
        assert "chapterPreviewList" in script
        assert "preview.chapters || []" in script
        assert "还有 ${chapterItems.length - limit} 章未显示" in script
        assert "正在解析章节" in script
        assert "const payload = conversionPayload()" in script
        assert "state.lastConvertedInput = payload.text" in script
        assert "updateConversionFreshness()" in script
        assert "至少需要 3 章通过预检后才能转换。" in script
        assert "state.isPreviewPending || !state.isPreviewReady" in script
        assert "未确认远程发送" in script
        assert "需重新转换" in script
        assert "function currentOutputStaleReason" in script
        assert "setOutputActions(false)" in script
        assert "setOutputActions(true)" in script
        assert "model: normalizedModel()" in script
        assert "lastFormat" in script
        assert "lastValidate" in script
        assert "输出格式已变更" in script
        assert "当前导出可能不是最新" in script
        assert "Schema 校验设置已变更" in script
        assert "Schema 校验设置已变更，当前导出仍使用旧设置。" in script
        assert "转换前会按当前手稿、片名和模型确认远程发送。" in script
        assert "OpenAI 模型已变更" in script
        assert "return elements.model.value.trim() || defaultModel" in script
        assert "重新转换后再复制或下载。" in script
        assert "function renderProviderRunStatus" in script
        assert "function providerStatusSummary" in script
        assert "本地回退" in script
        assert "OPENAI_API_KEY 未设置，实际使用本地转换。" in script
        assert "const maxRequestBytes = 2000000" in script
        assert "new TextEncoder" in script
        assert "function isCurrentRequestTooLarge" in script
        assert "function importedFileRequestByteLength" in script
        assert "function showFileImportSizeError" in script
        assert "文件过大，未导入" in script
        assert "function showFileImportReadError" in script
        assert "文件读取失败，当前手稿已保留" in script
        assert "setConversionStatus(\"导入失败\"" in script
        assert "elements.file.value = \"\"" in script
        assert "function copyOutput" in script
        assert "navigator.clipboard?.writeText" in script
        assert "const staleReason = currentOutputStaleReason()" in script
        assert "复制失败" in script
        assert "浏览器未允许写入剪贴板，请手动选中结果复制。" in script
        assert "function downloadOutput" in script
        assert "downloadLabelTimer" in script
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
        assert ".status-card.is-warn strong" in stylesheet
        assert ".status-card.is-error strong" in stylesheet
        assert ".input-pane" in stylesheet
        assert ".chapter-preview" in stylesheet
        assert ".chapter-preview-list li" in stylesheet
        assert ".chapter-preview.is-ready .chapter-preview-head strong" in stylesheet
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
        assert response.getheader("Content-Length") == str(len(b'{"status": "ok"}'))
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("X-Content-Type-Options") == "nosniff"
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
        assert response.getheader("X-Content-Type-Options") == "nosniff"
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
            assert response.getheader("X-Content-Type-Options") == "nosniff"
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
        assert response.getheader("X-Content-Type-Options") == "nosniff"
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
        assert data == {"error": "Preview failed unexpectedly."}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
