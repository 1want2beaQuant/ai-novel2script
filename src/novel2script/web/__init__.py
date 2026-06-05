"""Local browser interface for novel2script."""

from __future__ import annotations

import argparse
import json
import mimetypes
from ipaddress import ip_address
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import unquote, urlsplit
import webbrowser

from novel2script import __version__
from novel2script.ai_provider import convert_with_provider_status
from novel2script.chapter_parser import parse_chapter_candidates
from novel2script.fountain import draft_to_fountain
from novel2script.schema import validate_script
from novel2script.yaml_io import draft_to_yaml


MAX_REQUEST_BYTES = 2_000_000
STATIC_FILES = {"index.html", "app.css", "app.js"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class RequestTooLargeError(ValueError):
    pass


def convert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_string(payload, "text").strip()
    if not text:
        raise ValueError("Manuscript text is required.")

    title_value = _optional_string(payload, "title")
    title = title_value.strip() if title_value and title_value.strip() else None

    output_format = _optional_string(payload, "format", default="yaml")
    if output_format not in {"yaml", "fountain"}:
        raise ValueError("Format must be yaml or fountain.")

    provider = _optional_string(payload, "provider", default="local")
    if provider not in {"local", "openai"}:
        raise ValueError("Provider must be local or openai.")

    model = payload.get("model", "gpt-4.1-mini")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must be a non-empty string.")

    conversion = convert_with_provider_status(
        text=text,
        title=title,
        provider=provider,
        model=model.strip(),
    )
    draft = conversion.draft
    data = draft.to_dict()
    if _optional_bool(payload, "validate", default=True):
        validate_script(data)

    output = draft_to_fountain(draft) if output_format == "fountain" else draft_to_yaml(draft)
    return {
        "format": output_format,
        "output": output,
        "summary": summarize_script(data),
        "draft": data,
        "provider_status": conversion.provider_status.to_dict(),
    }


def preview_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_string(payload, "text").strip()
    character_count = len("".join(text.split()))
    if not text:
        return {
            "ready": False,
            "character_count": 0,
            "chapter_count": 0,
            "chapters": [],
            "message": "至少 3 章后开始转换。",
        }

    try:
        chapters = parse_chapter_candidates(text)
    except ValueError as exc:
        return {
            "ready": False,
            "character_count": character_count,
            "chapter_count": 0,
            "chapters": [],
            "message": str(exc),
        }

    ready = len(chapters) >= 3
    return {
        "ready": ready,
        "character_count": character_count,
        "chapter_count": len(chapters),
        "chapters": [
            {"index": chapter.index, "title": chapter.title} for chapter in chapters
        ],
        "message": (
            "符合三章以上输入要求。"
            if ready
            else "至少需要 3 个包含正文的章节才能生成结构化剧本。"
        ),
    }


def summarize_script(data: dict[str, Any]) -> dict[str, Any]:
    acts = [act for act in data.get("acts", []) if isinstance(act, dict)]
    scenes = [
        (act, scene)
        for act in acts
        for scene in act.get("scenes", [])
        if isinstance(scene, dict)
    ]
    coverage = _as_dict(data.get("coverage_report"))
    adaptation = _as_dict(data.get("adaptation_report"))
    structure = _as_dict(data.get("structure_map"))
    source = _as_dict(data.get("source"))
    chapter_coverage = _as_dict(adaptation.get("chapter_coverage"))
    metrics = _as_dict(adaptation.get("metrics"))
    return {
        "title": data.get("title", ""),
        "logline": data.get("logline", ""),
        "chapter_count": source.get("chapter_count", 0),
        "act_count": len(acts),
        "scene_count": len(scenes),
        "character_count": len(data.get("characters", [])),
        "coverage_score": coverage.get("overall_score", 0),
        "verdict": coverage.get("verdict", ""),
        "scores": [
            {
                "area": score.get("area", ""),
                "score": score.get("score", 0),
                "rationale": score.get("rationale", ""),
            }
            for score in _dict_list(coverage.get("scores"))
        ],
        "strengths": _string_list(coverage.get("strengths")),
        "weaknesses": _string_list(coverage.get("weaknesses")),
        "action_items": [
            {
                "priority": item.get("priority", ""),
                "area": item.get("area", ""),
                "note": item.get("note", ""),
            }
            for item in _dict_list(coverage.get("action_items"))
        ],
        "chapter_coverage": {
            "total_chapters": chapter_coverage.get("total_chapters", 0),
            "adapted_chapters": chapter_coverage.get("adapted_chapters", 0),
            "coverage_ratio": chapter_coverage.get("coverage_ratio", 0),
            "missing_chapters": _number_list(chapter_coverage.get("missing_chapters")),
        },
        "adaptation_metrics": {
            "block_count": metrics.get("block_count", 0),
            "action_blocks": metrics.get("action_blocks", 0),
            "dialogue_blocks": metrics.get("dialogue_blocks", 0),
            "dialogue_ratio": metrics.get("dialogue_ratio", 0),
        },
        "quality_flags": _string_list(adaptation.get("quality_flags")),
        "revision_checklist": _string_list(adaptation.get("revision_checklist")),
        "structure_beats": [
            {
                "id": beat.get("id", ""),
                "label": beat.get("label", ""),
                "scene_id": beat.get("scene_id", ""),
                "source_chapter": beat.get("source_chapter", ""),
                "summary": beat.get("summary", ""),
                "purpose": beat.get("purpose", ""),
                "revision_hint": beat.get("revision_hint", ""),
            }
            for beat in _dict_list(structure.get("beats"))
        ],
        "structure_diagnostics": _string_list(structure.get("diagnostics")),
        "scenes": [
            {
                "act_id": act.get("id", ""),
                "id": scene.get("id", ""),
                "title": scene.get("title", ""),
                "location": scene.get("location", ""),
                "time": scene.get("time", ""),
                "summary": scene.get("summary", ""),
                "characters": _string_list(scene.get("characters")),
                "source_chapter": scene.get("source_chapter", ""),
            }
            for act, scene in scenes[:12]
        ],
    }


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _number_list(value: object) -> list[int | float]:
    return [item for item in value if isinstance(item, int | float)] if isinstance(value, list) else []


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    allow_remote: bool = False,
) -> ThreadingHTTPServer:
    _validate_bind_host(host, allow_remote=allow_remote)
    return ThreadingHTTPServer((host, port), Novel2ScriptWebHandler)


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    allow_remote: bool = False,
) -> None:
    server = create_server(host, port, allow_remote=allow_remote)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"novel2script web UI running at {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="novel2script-web",
        description="Run the local browser interface for novel2script.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on.")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser tab.")
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow binding the Web UI to a non-loopback host.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        serve(
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
            allow_remote=args.allow_remote,
        )
    except ValueError as exc:
        parser.exit(status=2, message=f"{parser.prog}: error: {exc}\n")
    return 0


class Novel2ScriptWebHandler(BaseHTTPRequestHandler):
    server_version = "novel2script-web"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in {"", "/", "/index.html"}:
            self._send_static("index.html")
            return
        if path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if path.startswith("/"):
            filename = unquote(path.lstrip("/"))
            if filename in STATIC_FILES:
                self._send_static(filename)
                return
        self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path not in {"/api/convert", "/api/preview"}:
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            self._validate_convert_request()
            payload = self._read_json_payload()
            result = preview_payload(payload) if path == "/api/preview" else convert_payload(payload)
        except RequestTooLargeError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception:
            message = (
                "Preview failed unexpectedly."
                if path == "/api/preview"
                else "Conversion failed unexpectedly."
            )
            self._send_json(
                {"error": message},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _validate_convert_request(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise ValueError("Request Content-Type must be application/json.")

        origin = self.headers.get("Origin")
        if origin and not _is_same_origin(origin, self.headers.get("Host", "")):
            raise ValueError("Request Origin must match the local Web UI host.")

    def _read_json_payload(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length.") from exc
        if content_length < 0:
            raise ValueError("Invalid request length.")
        if content_length > MAX_REQUEST_BYTES:
            raise RequestTooLargeError("Request body is too large.")

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid UTF-8 JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _send_static(self, filename: str) -> None:
        try:
            content = resources.files(__package__).joinpath("static", filename).read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'",
        )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _optional_string(payload: dict[str, Any], key: str, *, default: str | None = None) -> str | None:
    value = payload.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean.")
    return value


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower().strip("[]")
    if normalized in LOCAL_HOSTS:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def _validate_bind_host(host: str, *, allow_remote: bool) -> None:
    if allow_remote or _is_loopback_host(host):
        return
    raise ValueError(
        "Refusing to bind the Web UI to a non-loopback host without --allow-remote. "
        "Use --host 127.0.0.1 for local-only access."
    )


def _is_same_origin(origin: str, host_header: str) -> bool:
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme != "http" or not parsed.netloc:
        return False
    return _normalize_host_port(parsed.netloc) == _normalize_host_port(host_header)


def _normalize_host_port(value: str) -> str:
    return value.strip().lower().rstrip(".")
