"""Schema loading and validation."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "script.schema.json"


def load_schema() -> dict[str, Any]:
    if PROJECT_SCHEMA_PATH.exists():
        return json.loads(PROJECT_SCHEMA_PATH.read_text(encoding="utf-8"))

    schema_resource = resources.files("novel2script").joinpath("schemas/script.schema.json")
    return json.loads(schema_resource.read_text(encoding="utf-8"))


def validate_script(data: dict[str, Any]) -> None:
    validator = Draft202012Validator(load_schema())
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"YAML Schema 校验失败：{location}: {first.message}")
