"""Local browser interface for novel2script."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import unquote
import webbrowser

from novel2script.ai_provider import convert_with_optional_ai
from novel2script.fountain import draft_to_fountain
from novel2script.schema import validate_script
from novel2script.yaml_io import draft_to_yaml


MAX_REQUEST_BYTES = 2_000_000
STATIC_FILES = {"index.html", "app.css", "app.js"}


def convert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = _required_string(payload, "text").strip()
    if not text:
        raise ValueError("Manuscript text is required.")

    title = payload.get("title")
    title = title.strip() if isinstance(title, str) and title.strip() else None

    output_format = payload.get("format", "yaml")
    if output_format not in {"yaml", "fountain"}:
        raise ValueError("Format must be yaml or fountain.")

    provider = payload.get("provider", "local")
    if provider not in {"local", "openai"}:
        raise ValueError("Provider must be local or openai.")

    model = payload.get("model", "gpt-4.1-mini")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must be a non-empty string.")

    draft = convert_with_optional_ai(
        text=text,
        title=title,
        provider=provider,
        model=model.strip(),
    )
    data = draft.to_dict()
    if bool(payload.get("validate", True)):
        validate_script(data)

    output = draft_to_fountain(draft) if output_format == "fountain" else draft_to_yaml(draft)
    return {
        "format": output_format,
        "output": output,
        "summary": summarize_script(data),
        "draft": data,
    }


def summarize_script(data: dict[str, Any]) -> dict[str, Any]:
    acts = data.get("acts", [])
    scenes = [
        scene
        for act in acts
        for scene in act.get("scenes", [])
        if isinstance(scene, dict)
    ]
    coverage = data.get("coverage_report", {})
    source = data.get("source", {})
    return {
        "title": data.get("title", ""),
        "logline": data.get("logline", ""),
        "chapter_count": source.get("chapter_count", 0),
        "act_count": len(acts),
        "scene_count": len(scenes),
        "character_count": len(data.get("characters", [])),
        "coverage_score": coverage.get("overall_score", 0),
        "verdict": coverage.get("verdict", ""),
        "scenes": [
            {
                "id": scene.get("id", ""),
                "title": scene.get("title", ""),
                "location": scene.get("location", ""),
                "source_chapter": scene.get("source_chapter", ""),
            }
            for scene in scenes[:8]
        ],
    }


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Novel2ScriptWebHandler)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    server = create_server(host, port)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"novel2script web UI running at {url}")
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
    args = parser.parse_args(argv)

    serve(host=args.host, port=args.port, open_browser=not args.no_open)
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
        if self.path.split("?", 1)[0] != "/api/convert":
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json_payload()
            result = convert_payload(payload)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception:
            self._send_json(
                {"error": "Conversion failed unexpectedly."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json_payload(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length.") from exc
        if content_length > MAX_REQUEST_BYTES:
            raise ValueError("Request body is too large.")

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8"))
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
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value
