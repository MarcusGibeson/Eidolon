from __future__ import annotations

"""Bounded capability-argument binding and clarification foundations.

The contract binds only public, allowlisted argument shapes to already registered
capabilities. It never executes, approves, persists, or exposes raw requests.
"""

import hashlib
import json
import re
from typing import Any, Mapping

from chat_action_router import SUPERVISED_CAPABILITY_REGISTRY

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1176.2"
MAX_ARGUMENTS = 4
MAX_VALUE_CHARS = 160
MAX_RECEIPT_BYTES = 2048
_CAPABILITIES = {str(row["id"]): dict(row) for row in SUPERVISED_CAPABILITY_REGISTRY}

# Only bounded public argument names are allowed. Defaults are safe, read-only,
# and never broaden scope beyond the user's explicit request.
ARGUMENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "diagnostics": {"allowed": {"scope": {"values": ("system", "runtime", "provider"), "default": "system"}}, "required": ()},
    "maintenance": {"allowed": {"scope": {"values": ("system", "storage", "runtime"), "default": "system"}}, "required": ()},
    "settings_health": {"allowed": {"section": {"values": ("all", "model", "provider", "privacy"), "default": "all"}}, "required": ()},
    "approvals": {"allowed": {"state": {"values": ("pending", "all"), "default": "pending"}}, "required": ()},
    "task_project": {"allowed": {"view": {"values": ("status", "next", "summary"), "default": "status"}}, "required": ()},
    "memory": {"allowed": {"view": {"values": ("status", "summary"), "default": "status"}}, "required": ()},
    "attention_center": {"allowed": {"view": {"values": ("summary", "open"), "default": "summary"}}, "required": ()},
    "notifications": {"allowed": {"view": {"values": ("summary", "pending"), "default": "summary"}}, "required": ()},
    "planning": {"allowed": {"mode": {"values": ("outline", "review"), "default": "outline"}}, "required": ()},
    "file_review": {"allowed": {"target_ref": {"pattern": r"^[A-Za-z0-9_.\-/]{1,160}$"}}, "required": ("target_ref",)},
    "patch_proposal": {"allowed": {"target_ref": {"pattern": r"^[A-Za-z0-9_.\-/]{1,160}$"}}, "required": ("target_ref",)},
    "self_development": {"allowed": {"scope_ref": {"pattern": r"^[A-Za-z0-9_.:\-/]{1,160}$"}}, "required": ("scope_ref",)},
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _token(value: Any, limit: int = MAX_VALUE_CHARS) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _unsafe_reference(value: str) -> bool:
    normalized = str(value or "").replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    return bool(
        normalized.startswith("/")
        or normalized.startswith("//")
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part == ".." for part in parts)
    )


def _extract_candidates(text: str, capability_id: str) -> dict[str, str]:
    lower = text.lower()
    result: dict[str, str] = {}
    schema = ARGUMENT_SCHEMAS.get(capability_id, {})
    for name, spec in dict(schema.get("allowed") or {}).items():
        for value in spec.get("values", ()):
            if re.search(rf"\b{re.escape(value)}\b", lower):
                result[name] = value
                break
    if capability_id in {"file_review", "patch_proposal"}:
        match = re.search(r"(?:review|inspect|change|modify|update|patch|fix)\s+([A-Za-z0-9_.\-/]+)", text, re.I)
        if match and ("/" in match.group(1) or "." in match.group(1)):
            result["target_ref"] = match.group(1)[:MAX_VALUE_CHARS]
    if capability_id == "self_development":
        match = re.search(r"(?:scope|project|area)\s+([A-Za-z0-9_.:\-/]+)", text, re.I)
        if match:
            result["scope_ref"] = match.group(1)[:MAX_VALUE_CHARS]
    return result


def bind_bounded_action_arguments(
    user_text: str,
    grounding: Mapping[str, Any],
    *,
    supplied_arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    capability_id = _token(grounding.get("capability_id"), 80)
    registered = capability_id in _CAPABILITIES
    schema = ARGUMENT_SCHEMAS.get(capability_id)
    candidates = _extract_candidates(_token(user_text, 12000), capability_id) if registered and schema else {}
    supplied = dict(supplied_arguments or {})
    unknown = sorted(str(k)[:80] for k in supplied if k not in dict((schema or {}).get("allowed") or {}))[:8]
    values: dict[str, str] = {}
    invalid: list[str] = []
    defaults: list[str] = []
    if schema:
        for name, spec in dict(schema.get("allowed") or {}).items():
            raw = supplied.get(name, candidates.get(name, ""))
            value = _token(raw)
            if not value and "default" in spec:
                value = str(spec["default"])
                defaults.append(name)
            if value:
                allowed = tuple(spec.get("values") or ())
                pattern = str(spec.get("pattern") or "")
                if allowed and value not in allowed:
                    invalid.append(name)
                elif pattern and (not re.fullmatch(pattern, value) or _unsafe_reference(value)):
                    invalid.append(name)
                else:
                    values[name] = value
    required = tuple((schema or {}).get("required") or ())
    missing = [name for name in required if name not in values]
    available = bool(registered and schema)
    exact = bool(available and not unknown and not invalid and not missing)
    clarification = ""
    if not registered:
        clarification = "Name a registered capability."
    elif not schema:
        clarification = "This registered capability has no bounded conversational argument schema."
    elif unknown:
        clarification = "Remove unsupported argument names: " + ", ".join(unknown) + "."
    elif invalid:
        clarification = "Provide valid bounded values for: " + ", ".join(invalid) + "."
    elif missing:
        clarification = "Provide the required target explicitly: " + ", ".join(missing) + "."
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "capability_id": capability_id if registered else "",
        "registered_capability": registered,
        "schema_available": bool(schema),
        "binding_state": "bound" if exact else "clarification_required",
        "bound_argument_names": sorted(values)[:MAX_ARGUMENTS],
        "argument_values": values,
        "safe_default_names": sorted(defaults)[:MAX_ARGUMENTS],
        "missing_required": missing[:MAX_ARGUMENTS],
        "invalid_argument_names": invalid[:MAX_ARGUMENTS],
        "unknown_argument_names": unknown[:MAX_ARGUMENTS],
        "requires_clarification": not exact,
        "suggested_clarification": clarification,
        "exact_capability_argument_binding": exact,
        "authorization_inferred": False,
        "approval_created": False,
        "execution_admitted": False,
        "execution_performed": False,
        "raw_request_included": False,
        "raw_tool_arguments_included": False,
        "content_free_receipt": True,
    }
    result["binding_digest"] = _digest({k: v for k, v in result.items() if k != "binding_digest"})
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "capability_id": result["capability_id"],
        "binding_state": result["binding_state"],
        "bound_argument_names": result["bound_argument_names"],
        "binding_digest": result["binding_digest"],
        "authority_state": "not_granted",
        "execution_state": "not_executed",
        "content_free": True,
    }
    receipt["receipt_digest"] = _digest(receipt)
    size = len(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode())
    if size > MAX_RECEIPT_BYTES:
        raise ValueError("Bounded action-argument receipt exceeded size limit")
    result["receipt"] = receipt
    result["receipt_bytes"] = size
    return result
