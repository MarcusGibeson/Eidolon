from __future__ import annotations

"""v1146.3 governed activation, conflict arbitration, rollback, and restart continuity.

This module changes only durable cognitive-control configuration state. An active
control is an input to a later bounded consumer; activation itself cannot start
cognition, contact providers, send messages, create proposals, or grant release
authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from understandable_cognitive_control_configuration import build_cognitive_control_configuration_inspection
from understandable_cognitive_control_definitions import AUTHORITY_BOUNDARY, CONTROL_DOMAINS, SAFE_DEFAULTS

CONTRACT_VERSION = "v1146.3"
SCHEMA_VERSION = "1"
CONFIRMATION_PHRASE = "APPLY EXACT COGNITIVE CONTROL PREVIEW"
ROLLBACK_CONFIRMATION_PHRASE = "ROLL BACK EXACT COGNITIVE CONTROL ACTIVATION"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _identifier(value: Any) -> str:
    token = " ".join(str(value or "").split())[:240]
    return token if _IDENTIFIER.fullmatch(token) else ""


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _path(root: Path) -> Path:
    return root / "understandable_cognitive_control_activation.json"


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "active_controls": {},
        "receipts": [],
        "processed_request_ids": {},
        "updated_at": "",
        "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
    }


def _preview_by_exact_lineage(root: Path, preview_id: str, preview_digest: str) -> dict[str, Any] | None:
    inspection = build_cognitive_control_configuration_inspection(root)
    for row in inspection.get("recent_records") or []:
        if row.get("configuration_id") == preview_id and row.get("structural_digest") == preview_digest:
            return row
    return None


def activate_cognitive_control_preview(
    *, runtime_root: Path | str, preview_id: str, preview_digest: str,
    confirmation: str, operator_id: str, request_id: str,
) -> dict[str, Any]:
    root = Path(runtime_root).resolve()
    operator, request = _identifier(operator_id), _identifier(request_id)
    if not operator or not request:
        raise ValueError("valid operator and request identifiers are required")
    path = _path(root); root.mkdir(parents=True, exist_ok=True)
    with metadata_mutation_lock(path):
        state = load_json_file(path, default=_default()) or _default()
        existing = (state.get("processed_request_ids") or {}).get(request)
        if existing:
            return {"ok": True, "idempotent": True, "receipt": deepcopy(existing)}
        preview = _preview_by_exact_lineage(root, _identifier(preview_id), _identifier(preview_digest))
        status = "activated"
        reason_code = "exact_preview_confirmed"
        if confirmation != CONFIRMATION_PHRASE:
            status, reason_code = "rejected", "confirmation_mismatch"
        elif not preview:
            status, reason_code = "rejected", "preview_lineage_mismatch"
        elif preview.get("state") != "preview_only" or preview.get("applied") or preview.get("active"):
            status, reason_code = "rejected", "preview_not_eligible"
        domain = (preview or {}).get("domain", "")
        prior = deepcopy((state.get("active_controls") or {}).get(domain, {})) if domain else {}
        revision = int(state.get("revision") or 0) + 1
        receipt = {
            "receipt_id": f"control-activation:{request}:{revision}",
            "revision": revision,
            "request_id": request,
            "operator_id": operator,
            "preview_id": (preview or {}).get("configuration_id", _identifier(preview_id)),
            "preview_digest": (preview or {}).get("structural_digest", _identifier(preview_digest)),
            "domain": domain,
            "requested_mode": (preview or {}).get("requested_mode", ""),
            "requested_intensity": (preview or {}).get("requested_intensity", 0.0),
            "prior_activation_id": prior.get("activation_id", ""),
            "prior_activation_digest": prior.get("structural_digest", ""),
            "status": status,
            "reason_code": reason_code,
            "configuration_changed": status == "activated",
            "cognition_mutated": False,
            "provider_contacted": False,
            "message_sent": False,
            "proposal_created": False,
            "authorization_created": False,
            "occurred_at": _now(),
            "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        }
        receipt["structural_digest"] = _digest(receipt)
        if status == "activated":
            active = {
                "activation_id": receipt["receipt_id"],
                "activation_revision": revision,
                "domain": domain,
                "mode": receipt["requested_mode"],
                "intensity": receipt["requested_intensity"],
                "preview_id": receipt["preview_id"],
                "preview_digest": receipt["preview_digest"],
                "operator_id": operator,
                "activated_at": receipt["occurred_at"],
                "state": "active",
                "prior_activation_id": receipt["prior_activation_id"],
                "prior_activation_digest": receipt["prior_activation_digest"],
                "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
            }
            active["structural_digest"] = _digest(active)
            state.setdefault("active_controls", {})[domain] = active
        state.setdefault("receipts", []).append(receipt)
        state["receipts"] = state["receipts"][-300:]
        state.setdefault("processed_request_ids", {})[request] = receipt
        state["processed_request_ids"] = dict(list(state["processed_request_ids"].items())[-600:])
        state["revision"] = revision; state["updated_at"] = receipt["occurred_at"]
        write_json_atomic(path, state)
    return {"ok": status == "activated", "idempotent": False, "receipt": deepcopy(receipt)}


def rollback_cognitive_control_activation(
    *, runtime_root: Path | str, domain: str, activation_id: str,
    confirmation: str, operator_id: str, request_id: str,
) -> dict[str, Any]:
    root = Path(runtime_root).resolve(); path = _path(root); root.mkdir(parents=True, exist_ok=True)
    operator, request, domain_id = _identifier(operator_id), _identifier(request_id), _identifier(domain)
    if not operator or not request or domain_id not in CONTROL_DOMAINS:
        raise ValueError("valid rollback identifiers are required")
    with metadata_mutation_lock(path):
        state = load_json_file(path, default=_default()) or _default()
        existing = (state.get("processed_request_ids") or {}).get(request)
        if existing:
            return {"ok": existing.get("status") == "rolled_back", "idempotent": True, "receipt": deepcopy(existing)}
        active = deepcopy((state.get("active_controls") or {}).get(domain_id, {}))
        status, reason = "rolled_back", "exact_activation_confirmed"
        if confirmation != ROLLBACK_CONFIRMATION_PHRASE:
            status, reason = "rejected", "confirmation_mismatch"
        elif not active or active.get("activation_id") != _identifier(activation_id):
            status, reason = "rejected", "activation_lineage_mismatch"
        revision = int(state.get("revision") or 0) + 1
        receipt = {
            "receipt_id": f"control-rollback:{request}:{revision}", "revision": revision,
            "request_id": request, "operator_id": operator, "domain": domain_id,
            "activation_id": _identifier(activation_id), "activation_digest": active.get("structural_digest", ""),
            "status": status, "reason_code": reason, "configuration_changed": status == "rolled_back",
            "restored_safe_default": deepcopy(SAFE_DEFAULTS[domain_id]) if status == "rolled_back" else {},
            "cognition_mutated": False, "provider_contacted": False, "message_sent": False,
            "proposal_created": False, "authorization_created": False, "occurred_at": _now(),
            "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        }
        receipt["structural_digest"] = _digest(receipt)
        if status == "rolled_back":
            state.setdefault("active_controls", {}).pop(domain_id, None)
        state.setdefault("receipts", []).append(receipt); state["receipts"] = state["receipts"][-300:]
        state.setdefault("processed_request_ids", {})[request] = receipt
        state["revision"] = revision; state["updated_at"] = receipt["occurred_at"]
        write_json_atomic(path, state)
    return {"ok": status == "rolled_back", "idempotent": False, "receipt": deepcopy(receipt)}


def build_cognitive_control_activation_inspection(runtime_root: Path | str) -> dict[str, Any]:
    root = Path(runtime_root).resolve(); state = load_json_file(_path(root), default=_default()) or _default()
    active = deepcopy(state.get("active_controls") or {})
    receipts = deepcopy(state.get("receipts") or [])[-40:]
    return {
        "contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION,
        "revision": int(state.get("revision") or 0), "active_control_count": len(active),
        "active_controls": active, "recent_receipts": receipts,
        "confirmation_required": True, "rollback_supported": True,
        "restart_continuity": True, "content_free": True,
        "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        "structural_digest": _digest({"revision": state.get("revision", 0), "active": active, "receipts": receipts}),
    }
