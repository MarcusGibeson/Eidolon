from __future__ import annotations

"""v2513 general capability adapter registry.

Registry records describe *how* a manifest-bound capability could be reached.
They never contain live callables, secrets, raw arguments, credentials, or an
authority grant. Adapters are disabled by default and enabling remains a
separate explicit configuration fact, not execution authorization.
"""

import hashlib, json, re
from copy import deepcopy
from typing import Any, Mapping

from general_capability_manifest_v2509 import validate_capability_manifest

CONTRACT_VERSION = "v2513.0"
ADAPTER_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,95}$")
KINDS = frozenset({"local_read", "local_reversible", "external_read", "external_reversible", "external_write", "protected"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def build_adapter_descriptor(*, manifest: Mapping[str, Any], adapter_id: str, adapter_kind: str,
                             handler_code: str, enabled: bool = False, supports_preview: bool = True,
                             supports_cancellation: bool = False, supports_rollback: bool = False) -> dict[str, Any]:
    if not validate_capability_manifest(manifest).get("ok"):
        raise ValueError("valid_manifest_required")
    aid = str(adapter_id or "").strip().lower()
    kind = str(adapter_kind or "").strip().lower()
    handler = str(handler_code or "").strip().lower()[:120]
    if not ADAPTER_ID_RE.fullmatch(aid): raise ValueError("invalid_adapter_id")
    if kind not in KINDS: raise ValueError("invalid_adapter_kind")
    if not handler: raise ValueError("handler_code_required")
    if supports_rollback and not manifest.get("rollback_supported"): raise ValueError("rollback_exceeds_manifest")
    if supports_cancellation and not manifest.get("cancellation_supported"): raise ValueError("cancellation_exceeds_manifest")
    row = {
        "contract_version": CONTRACT_VERSION,
        "adapter_id": aid,
        "adapter_kind": kind,
        "capability_id": manifest["capability_id"],
        "manifest_digest": manifest["manifest_digest"],
        "handler_code": handler,
        "enabled": bool(enabled),
        "supports_preview": bool(supports_preview),
        "supports_cancellation": bool(supports_cancellation),
        "supports_rollback": bool(supports_rollback),
        "callable_embedded": False,
        "credentials_embedded": False,
        "raw_arguments_stored": False,
        "registration_is_authority_grant": False,
        "execution_authorized": False,
        "adapter_invoked": False,
    }
    row["adapter_digest"] = _digest(row)
    return row


def validate_adapter_descriptor(row: Mapping[str, Any]) -> dict[str, Any]:
    body = deepcopy(dict(row or {})); supplied = str(body.pop("adapter_digest", ""))
    checks = {
        "contract": body.get("contract_version") == CONTRACT_VERSION,
        "adapter_id": bool(ADAPTER_ID_RE.fullmatch(str(body.get("adapter_id") or ""))),
        "kind": body.get("adapter_kind") in KINDS,
        "capability": bool(str(body.get("capability_id") or "")),
        "manifest_digest": bool(re.fullmatch(r"[0-9a-f]{64}", str(body.get("manifest_digest") or ""))),
        "handler": bool(str(body.get("handler_code") or "")),
        "digest": supplied == _digest(body),
        "content_minimized": body.get("callable_embedded") is False and body.get("credentials_embedded") is False and body.get("raw_arguments_stored") is False,
        "not_authority": body.get("registration_is_authority_grant") is False and body.get("execution_authorized") is False and body.get("adapter_invoked") is False,
    }
    return {"ok": all(checks.values()), "checks": checks, "adapter_id": str(body.get("adapter_id") or "")}


def register_adapter(registry: Mapping[str, Any] | None, descriptor: Mapping[str, Any]) -> dict[str, Any]:
    if not validate_adapter_descriptor(descriptor).get("ok"): raise ValueError("valid_adapter_descriptor_required")
    state = deepcopy(dict(registry or {"contract_version": CONTRACT_VERSION, "revision": 0, "adapters": []}))
    rows = [dict(x) for x in state.get("adapters", []) if isinstance(x, Mapping)]
    aid = descriptor["adapter_id"]
    rows = [x for x in rows if x.get("adapter_id") != aid]
    rows.append(deepcopy(dict(descriptor))); rows.sort(key=lambda x: x.get("adapter_id", ""))
    state.update({"contract_version": CONTRACT_VERSION, "revision": int(state.get("revision", 0)) + 1, "adapters": rows})
    state["registry_digest"] = _digest({k:v for k,v in state.items() if k != "registry_digest"})
    return state


def resolve_adapter(registry: Mapping[str, Any], *, capability_id: str, require_enabled: bool = True) -> dict[str, Any]:
    matches = [dict(x) for x in registry.get("adapters", []) if isinstance(x, Mapping) and x.get("capability_id") == capability_id]
    valid = [x for x in matches if validate_adapter_descriptor(x).get("ok") and (x.get("enabled") is True or not require_enabled)]
    if len(valid) != 1:
        return {"ok": False, "status": "adapter_unavailable" if not valid else "adapter_ambiguous", "match_count": len(valid), "execution_authorized": False, "adapter_invoked": False}
    row = deepcopy(valid[0]); row.update({"ok": True, "status": "adapter_resolved", "execution_authorized": False, "adapter_invoked": False})
    return row

__all__ = ["CONTRACT_VERSION","KINDS","build_adapter_descriptor","validate_adapter_descriptor","register_adapter","resolve_adapter"]
