from __future__ import annotations

"""Request/response parsing boundary extracted from api_server.py in v1276.

This module contains only transport-adjacent parsing/validation helpers. It does not
dispatch routes, execute tools, contact providers, mutate source, or grant authority.
"""

import json
import zipfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

CONTRACT_VERSION = "v1276.5"
AUTHORITY_FLAGS = {
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "release_authorized": False,
}

class ApiError(Exception):
    def __init__(self, status: int, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return _to_jsonable(dict(value.__dict__))
    return value


def _query_release_zip_path(query: dict[str, list[str]]) -> str | None:
    raw = (query.get("zip_path", [None])[0] or "").strip()
    if not raw:
        return None
    try:
        path = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise ApiError(400, "Invalid release zip path.", {"error_type": type(error).__name__})
    if path.suffix.lower() != ".zip":
        raise ApiError(400, "release zip path must point to a .zip file.")
    if not path.exists() or not path.is_file():
        raise ApiError(404, "release zip path was not found.")
    if not zipfile.is_zipfile(path):
        raise ApiError(400, "release zip path is not a valid zip archive.")
    return str(path)


def _query_path(query: dict[str, list[str]], name: str) -> str | None:
    raw = (query.get(name, [None])[0] or "").strip()
    if not raw:
        return None
    try:
        path = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise ApiError(400, f"Invalid {name}.", {"error_type": type(error).__name__})
    if not path.exists() or not path.is_file():
        raise ApiError(404, f"{name} was not found.")
    return str(path)


def _query_signature_options(query: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "signature_path": _query_path(query, "signature_path"),
        "public_key_path": _query_path(query, "public_key_path"),
        "trusted_fingerprint": (query.get("trusted_fingerprint", [None])[0] or None),
    }


def _path_parts(path: str) -> list[str]:
    parts = [part for part in path.strip("/").split("/") if part]
    if parts and parts[0] == "api":
        return parts[1:]
    return parts


def _query_bool(query: dict[str, list[str]], key: str, default: bool = False) -> bool:
    raw = query.get(key, [str(default)])[0]
    return str(raw).lower() in {"1", "true", "yes", "on"}


def _body_bool(data: dict[str, Any], key: str, default: bool = False) -> bool:
    if key not in data:
        return default
    raw = data.get(key)
    if isinstance(raw, bool):
        return raw
    return str(raw).lower() in {"1", "true", "yes", "on"}


def _require_confirmation(body: dict[str, Any], expected: str) -> None:
    if str(body.get("confirm", "")) != expected:
        raise ApiError(400, f"Live controlled work requires JSON field confirm={expected!r}.")


def parse_request_body(body: bytes, content_type: str = "") -> dict[str, Any]:
    if not body:
        return {}
    text = body.decode("utf-8")
    if "application/json" in content_type.lower():
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ApiError(400, f"Invalid JSON body: {error}") from error
        if not isinstance(data, dict):
            raise ApiError(400, "JSON body must be an object.")
        return data
    parsed = parse_qs(text)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


__all__ = ["CONTRACT_VERSION", "AUTHORITY_FLAGS", "ApiError", "_now", "_to_jsonable", "_query_release_zip_path", "_query_path", "_query_signature_options", "_path_parts", "_query_bool", "_body_bool", "_require_confirmation", "parse_request_body"]
