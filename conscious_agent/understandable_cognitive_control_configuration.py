from __future__ import annotations

"""v1146.1 durable content-free cognitive-control configuration lineage."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from understandable_cognitive_control_definitions import ALLOWED_MODES, AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS

CONTRACT_VERSION = "v1146.1"
SCHEMA_VERSION = "1"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")
FORBIDDEN_KEYS = {"text", "content", "prompt", "message", "reasoning", "memory", "relationship", "patch", "source_code", "provider_payload"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _root() -> Path:
    return (Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition")


def _path(root: Path) -> Path:
    return root / "understandable_cognitive_control_configuration.json"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _default() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "records": [], "updated_at": "", "authority_boundary": deepcopy(AUTHORITY_BOUNDARY)}


def _identifier(value: Any) -> str:
    token = " ".join(str(value or "").split())[:240]
    return token if _IDENTIFIER.fullmatch(token) else ""


def _validate_requested(requested: dict[str, Any]) -> dict[str, Any]:
    if FORBIDDEN_KEYS.intersection(requested):
        raise ValueError("raw or private control content is not accepted")
    domain = _identifier(requested.get("domain"))
    if domain not in CONTROL_DOMAINS:
        raise ValueError("unknown control domain")
    mode = _identifier(requested.get("mode"))
    if mode not in ALLOWED_MODES[domain]:
        raise ValueError("unsupported control mode")
    intensity = round(max(0.0, min(float(requested.get("intensity", SAFE_DEFAULTS[domain]["intensity"])), 1.0)), 4)
    return {"domain": domain, "mode": mode, "intensity": intensity}


def create_cognitive_control_configuration_preview(
    requested: dict[str, Any], *, runtime_root: Path | str | None = None,
    operator_id: str = "operator", source_event_id: str = "preview"
) -> dict[str, Any]:
    """Persist a preview lineage record only; it cannot apply the control."""
    root = Path(runtime_root).resolve() if runtime_root else _root()
    normalized = _validate_requested(requested)
    operator = _identifier(operator_id)
    event = _identifier(source_event_id)
    if not operator or not event:
        raise ValueError("valid operator and event identifiers are required")
    path = _path(root)
    root.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path):
        state = load_json_file(path, default=_default()) or _default()
        revision = int(state.get("revision") or 0) + 1
        prior = next((row for row in reversed(state.get("records") or []) if row.get("domain") == normalized["domain"]), None)
        record = {
            "configuration_id": f"control-preview:{normalized['domain']}:{revision}",
            "revision": revision,
            "domain": normalized["domain"],
            "requested_mode": normalized["mode"],
            "requested_intensity": normalized["intensity"],
            "safe_default": deepcopy(SAFE_DEFAULTS[normalized["domain"]]),
            "operator_id": operator,
            "source_event_id": event,
            "prior_configuration_id": (prior or {}).get("configuration_id", ""),
            "prior_structural_digest": (prior or {}).get("structural_digest", ""),
            "state": "preview_only",
            "applied": False,
            "active": False,
            "requires_explicit_confirmation": True,
            "created_at": _now(),
            "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        }
        record["structural_digest"] = _digest(record)
        state.setdefault("records", []).append(record)
        state["records"] = state["records"][-200:]
        state["revision"] = revision
        state["updated_at"] = record["created_at"]
        write_json_atomic(path, state)
    return deepcopy(record)


def build_cognitive_control_configuration_inspection(runtime_root: Path | str | None = None) -> dict[str, Any]:
    root = Path(runtime_root).resolve() if runtime_root else _root()
    state = load_json_file(_path(root), default=_default()) or _default()
    records = deepcopy(state.get("records") or [])[-25:]
    return {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "revision": int(state.get("revision") or 0),
        "record_count": len(state.get("records") or []),
        "recent_records": records,
        "safe_defaults": deepcopy(SAFE_DEFAULTS),
        "preview_only": True,
        "mutation_route_available": False,
        "apply_authority_available": False,
        "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        "structural_digest": _digest({"revision": state.get("revision", 0), "records": records}),
    }
