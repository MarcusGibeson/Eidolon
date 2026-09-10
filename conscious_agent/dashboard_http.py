from __future__ import annotations

"""Lightweight HTTP payload helpers for dashboard and conversation routes."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any
from urllib.parse import parse_qs


class DashboardRequestError(ValueError):
    pass


def dashboard_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return dashboard_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): dashboard_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [dashboard_jsonable(item) for item in value]
    if hasattr(value, "public_dict") and callable(value.public_dict):
        return dashboard_jsonable(value.public_dict())
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return dashboard_jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return dashboard_jsonable(dict(value.__dict__))
    return value


def parse_dashboard_request_body(body: bytes, content_type: str = "") -> dict[str, Any]:
    if not body:
        return {}
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DashboardRequestError("Request body must be valid UTF-8.") from error
    if "application/json" in str(content_type or "").lower():
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise DashboardRequestError(f"Invalid JSON body: {error}") from error
        if not isinstance(data, dict):
            raise DashboardRequestError("JSON body must be an object.")
        return data
    parsed = parse_qs(text)
    return {key: values[-1] if values else "" for key, values in parsed.items()}
