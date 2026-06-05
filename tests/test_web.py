from http import HTTPStatus
from http.client import HTTPConnection
import json
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


def test_convert_payload_rejects_missing_text() -> None:
    try:
        convert_payload({"text": "", "format": "yaml"})
    except ValueError as exc:
        assert "Manuscript text is required" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


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
        assert "default-src 'self'" in (response.getheader("Content-Security-Policy") or "")
        assert "novel2script Studio" in body
        assert 'id="fileButton"' in body
        assert "Adaptation Inspector" in body
        assert 'aria-label="转换状态"' in body
        assert 'id="inputSize"' in body
        assert 'id="providerMode"' in body
        assert 'id="conversionState"' in body
        assert 'id="exportState"' in body
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
        assert "openAiConfirmedFor" in script
        assert "textFingerprint(text)" in script
        assert "未确认远程发送" in script
        assert "需重新转换" in script
        assert "转换前会按当前手稿、片名和模型确认远程发送。" in script
        assert "OpenAI 模型已变更" in script
        assert "conversionSummary" in script

        connection.request("GET", "/app.css")
        response = connection.getresponse()
        stylesheet = response.read().decode("utf-8")

        assert response.status == HTTPStatus.OK
        assert ".status-grid" in stylesheet
        assert ".status-card.is-warn strong" in stylesheet
        assert ".status-card.is-error strong" in stylesheet
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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
        assert data == {"error": "Request Content-Type must be application/json."}
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
