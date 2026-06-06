"""Smoke test the installed novel2script Web server."""

from __future__ import annotations

import argparse
import json
from http.client import HTTPConnection
import queue
import re
import subprocess
import sys
import threading
import time
from typing import Any

from novel2script import DEFAULT_MODEL, __version__


MANUSCRIPT = """
Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Start the installed Web server and verify health, static assets, preview, "
            "conversion, and exports."
        )
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run `-m novel2script.web`.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for the smoke server.")
    parser.add_argument(
        "--startup-timeout",
        type=float,
        default=10,
        help="Seconds to wait for the server URL to be printed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    process = subprocess.Popen(
        [
            args.python,
            "-m",
            "novel2script.web",
            "--host",
            args.host,
            "--port",
            "0",
            "--no-open",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    try:
        base_url = _read_server_url(process, timeout_seconds=args.startup_timeout)
        _check_health(base_url)
        _check_static_assets(base_url)
        _check_preview(base_url)
        _check_conversion(base_url)
    finally:
        _terminate(process)

    print(f"Web server smoke passed at {base_url}")
    return 0


def _read_server_url(process: subprocess.Popen[str], *, timeout_seconds: float) -> str:
    assert process.stdout is not None
    lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"Web server exited before startup: {stderr.strip()}")
        wait_seconds = max(0.01, min(0.05, deadline - time.monotonic()))
        try:
            line = lines.get(timeout=wait_seconds)
        except queue.Empty:
            continue
        if line is None:
            break
        line = line.strip()
        if not line:
            continue
        match = re.search(r"http://[^\s]+", line)
        if match:
            return match.group(0)
    raise TimeoutError("Timed out waiting for Web server startup URL.")


def _check_health(base_url: str) -> None:
    status, payload = _request_json(base_url, "GET", "/api/health")
    if status != 200 or payload.get("status") != "ok":
        raise AssertionError(f"Unexpected health response: {status} {payload!r}")
    if payload.get("version") != __version__ or payload.get("default_model") != DEFAULT_MODEL:
        raise AssertionError(f"Unexpected health metadata: {payload!r}")
    if payload.get("max_request_bytes") != 2_000_000:
        raise AssertionError(f"Unexpected health request limit: {payload!r}")


def _check_static_assets(base_url: str) -> None:
    status, body = _request_text(base_url, "GET", "/")
    missing = _missing_static_shell_markers(body)
    if status != 200 or missing:
        raise AssertionError(
            f"Unexpected Web shell response: {status}; missing markers: {missing!r}"
        )

    status, body = _request_text(base_url, "GET", "/app.js")
    missing = _missing_static_app_markers(body)
    if status != 200 or missing:
        raise AssertionError(
            f"Unexpected app.js response: {status}; missing markers: {missing!r}"
        )


def _missing_static_shell_markers(body: str) -> list[str]:
    required = [
        "<h1>小说改编工作台</h1>",
        'id="fileInput"',
        'accept=".txt,.md,.markdown,text/plain,text/markdown"',
        'id="inputDropZone"',
        'id="dropOverlay"',
        'role="status" aria-live="polite" aria-atomic="true"',
        'class="chapter-preview" aria-label="章节预检" role="status" aria-live="polite"',
        'role="tablist"',
        'role="tab"',
        'id="outputBox"',
        'role="tabpanel"',
        'aria-busy="false"',
        'aria-labelledby="viewYamlButton"',
        'id="exportManifestList"',
        'id="bundleButton"',
        'id="remoteConfirmPanel"',
        'id="sceneFilterInput"',
        'class="quality-overview"',
        'id="qualityOverviewState"',
        'id="qualityCoverageMeter"',
    ]
    return [marker for marker in required if marker not in body]


def _missing_static_app_markers(body: str) -> list[str]:
    required = [
        "fetch(\"/api/preview\"",
        "providerStatusSummary",
        "localDraftStorageKey",
        "localDraftCleared",
        "isSeedSampleDraft",
        "isSeedSampleState",
        "markDraftUserOwned",
        "hasDraftContent",
        "Revision brief",
        "maxRequestBytes",
        "updateRuntimeRequestLimit",
        "max_request_bytes",
        "AbortController",
        "abortPreviewRequest",
        "isPreviewReady",
        "showPreflightBlockedConversion",
        "setConversionStatus(\"预检中\", pendingDetail, \"active\")",
        "preserveCurrentInputAfterImportError",
        "当前手稿和章节预检已保留。",
        "showFileImportSizeError",
        "showFileImportTypeError",
        "showFileImportReadError",
        "showFileImportEmptyError",
        "if (!text.trim())",
        "stripLeadingByteOrderMark",
        "已导入 ${file.name}，正在等待章节预检。",
        "replaceManuscriptText",
        "handleDropZoneDrop",
        "setDropZoneActive",
        "elements.dropOverlay.setAttribute(\"aria-hidden\", String(!isActive))",
        "requestClearWorkbench",
        "dismissClearConfirmation",
        "restoreConversionStatusAfterClearDismiss",
        "dismissRemoteConfirmation({ quiet: true })",
        "确认清空",
        "clearWorkbench",
        "setConversionStatus(\"待输入\", \"工作台已清空，等待手稿输入。\", \"neutral\")",
        "renderOutputTabs",
        "handleOutputTabKeydown",
        "elements.output.setAttribute(\"aria-busy\", \"true\")",
        "elements.output.setAttribute(\"aria-labelledby\", selectedTab.id)",
        "renderExportManifest",
        "downloadBundle",
        "createZipBlob",
        "currentOutputStaleReason",
        "renderQualityOverview",
        "qualityHealthLabel",
        "lowestCoverageScore",
        "riskMeterPercent",
        "arrayItems",
        "setConversionInputLock",
    ]
    return [marker for marker in required if marker not in body]


def _check_preview(base_url: str) -> None:
    payload = json.dumps({"text": MANUSCRIPT}).encode("utf-8")
    status, response = _request_json(
        base_url,
        "POST",
        "/api/preview",
        body=payload,
        headers={"Content-Type": "application/json"},
    )
    if status != 200:
        raise AssertionError(f"Preview failed with status {status}: {response!r}")
    if response.get("ready") is not True or response.get("chapter_count") != 3:
        raise AssertionError(f"Unexpected preview payload: {response!r}")


def _check_conversion(base_url: str) -> None:
    payload = json.dumps(
        {
            "text": MANUSCRIPT,
            "title": "The Locked Room",
            "format": "markdown",
            "provider": "local",
            "validate": True,
        }
    ).encode("utf-8")
    status, response = _request_json(
        base_url,
        "POST",
        "/api/convert",
        body=payload,
        headers={"Content-Type": "application/json"},
    )
    if status != 200:
        raise AssertionError(f"Conversion failed with status {status}: {response!r}")

    exports = response.get("exports")
    manifest = response.get("export_manifest")
    summary = response.get("summary")
    provider_status = response.get("provider_status")
    if not isinstance(exports, dict):
        raise AssertionError(f"Conversion exports missing or invalid: {response!r}")
    if not isinstance(manifest, dict):
        raise AssertionError(f"Conversion export manifest missing or invalid: {response!r}")
    if not isinstance(summary, dict):
        raise AssertionError(f"Conversion summary missing or invalid: {response!r}")
    if not isinstance(provider_status, dict):
        raise AssertionError(f"Conversion provider status missing or invalid: {response!r}")

    required_exports = ["yaml", "fountain", "markdown", "draft_json", "summary_json"]
    if set(exports) != set(required_exports):
        raise AssertionError(f"Unexpected export keys: {sorted(exports)!r}")
    if response.get("format") != "markdown" or response.get("output") != exports["markdown"]:
        raise AssertionError(f"Unexpected selected conversion output: {response!r}")
    if summary.get("scene_count") != 3 or len(summary.get("scenes", [])) != 3:
        raise AssertionError(f"Unexpected conversion summary: {summary!r}")
    if provider_status.get("actual") != "local" or provider_status.get("remote") is not False:
        raise AssertionError(f"Unexpected provider status: {provider_status!r}")

    if manifest.get("selected") != "markdown":
        raise AssertionError(f"Unexpected selected export manifest entry: {manifest!r}")
    bundle = manifest.get("bundle")
    files = manifest.get("files")
    if not isinstance(bundle, dict) or bundle.get("file_count") != 5:
        raise AssertionError(f"Unexpected export manifest bundle: {manifest!r}")
    if not isinstance(files, list) or [file.get("key") for file in files] != required_exports:
        raise AssertionError(f"Unexpected export manifest files: {manifest!r}")

    draft_json = json.loads(exports["draft_json"])
    summary_json = json.loads(exports["summary_json"])
    if draft_json.get("title") != "The Locked Room":
        raise AssertionError(f"Unexpected draft JSON export: {draft_json!r}")
    if summary_json.get("scene_count") != summary.get("scene_count"):
        raise AssertionError(f"Unexpected summary JSON export: {summary_json!r}")
    if "title: The Locked Room" not in exports["yaml"]:
        raise AssertionError("YAML export did not include the smoke title.")
    if "Title: The Locked Room" not in exports["fountain"]:
        raise AssertionError("Fountain export did not include the smoke title.")
    if "# The Locked Room 修订简报" not in exports["markdown"]:
        raise AssertionError("Markdown export did not include the smoke title.")


def _request_json(
    base_url: str,
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    status, text = _request_text(base_url, method, path, body=body, headers=headers)
    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise AssertionError(f"Expected JSON object from {path}, got {type(loaded).__name__}")
    return status, loaded


def _request_text(
    base_url: str,
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, str]:
    host, port = _parse_http_url(base_url)
    connection = HTTPConnection(host, port, timeout=10)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8")
    finally:
        connection.close()


def _parse_http_url(url: str) -> tuple[str, int]:
    match = re.fullmatch(r"http://(?P<host>\[[^\]]+\]|[^:/]+):(?P<port>\d+)", url)
    if not match:
        raise ValueError(f"Unsupported server URL: {url}")
    return match.group("host").strip("[]"), int(match.group("port"))


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
