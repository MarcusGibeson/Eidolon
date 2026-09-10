from __future__ import annotations

"""Era 8 fine-grained authority and permission policy contracts.

Policies are ceilings and revocation surfaces, never grants by themselves.  The
module deliberately reuses existing approval/execution owners by producing
content-free, digest-bound policy decisions that those owners may inspect.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import Any, Iterable, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2225.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era8_authority_policy.json"
POLICY_MODES = ("deny", "read_only", "reversible_workspace", "reviewed_installation")
PROTECTED_CAPABILITIES = frozenset({
    "secret_access", "model_management", "destructive_system", "authority_change",
    "account_change", "financial_action", "release_promotion", "external_publish",
})
ALLOWED_ENVIRONMENTS = frozenset({"source_read", "isolated_workspace", "reviewed_candidate", "installed_source"})
MAX_HISTORY = 256

_DENIED = {
    "execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "secret_access_authorized": False,
    "destructive_operation_authorized": False,
    "authority_expanded": False,
    "source_modified": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _bounded_int(value: Any, *, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _bounded_float(value: Any, *, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return round(max(minimum, min(maximum, number)), 4)


def _strict_nonnegative_number(value: Any, *, integer: bool = False) -> int | float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or number < 0 or (integer and not number.is_integer()):
        return None
    return int(number) if integer else round(number, 4)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "authority" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "revocations": {},
        "history": [],
        "raw_content_persisted": False,
        "authority_effect": "restrict_or_revoke_only",
    }


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    if not isinstance(state.get("revocations"), dict):
        state["revocations"] = {}
    if not isinstance(state.get("history"), list):
        state["history"] = []
    state["raw_content_persisted"] = False
    state["authority_effect"] = "restrict_or_revoke_only"
    return state


def _read_policy_state_checked(*, runtime_root: str | Path | None = None) -> tuple[dict[str, Any], bool]:
    path = _state_path(runtime_root)
    if not path.exists():
        return _default_state(), True
    try:
        value = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _default_state(), False
    if not isinstance(value, dict) or not isinstance(value.get("revocations"), dict) or not isinstance(value.get("history"), list):
        return _default_state(), False
    try:
        revision = int(value.get("revision", 0))
    except (TypeError, ValueError, OverflowError):
        return _default_state(), False
    integrity_ok = revision >= 0
    for digest, record in value["revocations"].items():
        integrity_ok = integrity_ok and bool(_hex64(digest)) and isinstance(record, Mapping) and bool(_hex64(record.get("event_digest")))
    return _valid_state(value), bool(integrity_ok)


def read_policy_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, _ = _read_policy_state_checked(runtime_root=runtime_root)
    return state


def build_permission_policy(
    *, policy_id: str, capability: str, target_digest: str, scope: Iterable[str] = (),
    mode: str = "deny", duration_seconds: int = 0, command_budget: int = 0,
    file_budget: int = 0, network_budget: int = 0, disk_mb_budget: float = 0.0,
    environment: str = "isolated_workspace", provenance_digest: str = "", issued_epoch: float | None = None,
) -> dict[str, Any]:
    pid = str(policy_id or "").strip()[:120]
    cap = str(capability or "").strip().lower()[:120]
    target = _hex64(target_digest)
    provenance = _hex64(provenance_digest) or _digest({"policy_id": pid, "capability": cap, "target": target})
    policy_mode = str(mode or "deny").strip().lower()
    env = str(environment or "isolated_workspace").strip().lower()
    if not pid or not cap or not target:
        raise ValueError("policy_id_capability_and_target_digest_required")
    if policy_mode not in POLICY_MODES:
        raise ValueError("invalid_policy_mode")
    if env not in ALLOWED_ENVIRONMENTS:
        raise ValueError("invalid_policy_environment")
    scope_codes = sorted({str(item or "").strip().lower()[:120] for item in scope if str(item or "").strip()})[:64]
    if cap in PROTECTED_CAPABILITIES:
        policy_mode = "deny"
    issued = _strict_nonnegative_number(time.time() if issued_epoch is None else issued_epoch)
    if issued is None:
        raise ValueError("invalid_policy_issue_time")
    duration = _bounded_int(duration_seconds, minimum=0, maximum=86400, default=0)
    policy = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "policy_id": pid,
        "capability": cap,
        "target_digest": target,
        "scope": scope_codes,
        "mode": policy_mode,
        "duration_seconds": duration,
        "issued_epoch": round(issued, 6),
        "expires_epoch": round(issued + duration, 6) if duration > 0 else 0.0,
        "budgets": {
            "commands": _bounded_int(command_budget, minimum=0, maximum=10000, default=0),
            "files": _bounded_int(file_budget, minimum=0, maximum=10000, default=0),
            "network_requests": _bounded_int(network_budget, minimum=0, maximum=10000, default=0),
            "disk_mb": _bounded_float(disk_mb_budget, minimum=0.0, maximum=1024 * 1024.0, default=0.0),
        },
        "environment": env,
        "provenance_digest": provenance,
        "revocable": True,
        "policy_is_authority_grant": False,
        "activation_requires_external_authority_receipt": True,
        "protected_capability": cap in PROTECTED_CAPABILITIES,
        **_DENIED,
    }
    policy["policy_digest"] = _digest(policy)
    return policy


def validate_permission_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(policy or {})
    supplied = _hex64(row.pop("policy_digest", ""))
    scope = policy.get("scope")
    budgets = policy.get("budgets")
    issued = _strict_nonnegative_number(policy.get("issued_epoch"))
    expires = _strict_nonnegative_number(policy.get("expires_epoch"))
    duration = _strict_nonnegative_number(policy.get("duration_seconds"), integer=True)
    budget_values = {
        key: _strict_nonnegative_number((budgets or {}).get(key), integer=key != "disk_mb")
        for key in ("commands", "files", "network_requests", "disk_mb")
    } if isinstance(budgets, Mapping) else {}
    checks = {
        "digest": bool(supplied) and supplied == _digest(row),
        "schema": policy.get("schema_version") == SCHEMA_VERSION and policy.get("contract_version") == CONTRACT_VERSION,
        "identity": bool(str(policy.get("policy_id") or "").strip()) and bool(str(policy.get("capability") or "").strip()),
        "mode": str(policy.get("mode") or "") in POLICY_MODES,
        "target": bool(_hex64(policy.get("target_digest"))),
        "provenance": bool(_hex64(policy.get("provenance_digest"))),
        "environment": str(policy.get("environment") or "") in ALLOWED_ENVIRONMENTS,
        "ceiling_only": policy.get("policy_is_authority_grant") is False,
        "revocable": policy.get("revocable") is True,
        "protected_denied": not (str(policy.get("capability") or "") in PROTECTED_CAPABILITIES and str(policy.get("mode") or "") != "deny"),
        "no_authority": not any(bool(policy.get(key)) for key in _DENIED),
        "scope": isinstance(scope, list) and len(scope) <= 64 and all(isinstance(item, str) and item == item.strip().lower() and bool(item) for item in scope),
        "budgets": len(budget_values) == 4 and all(value is not None for value in budget_values.values()),
        "timing": issued is not None and expires is not None and duration is not None and ((duration == 0 and expires == 0) or (duration > 0 and abs(float(expires) - (float(issued) + duration)) < 0.001)),
    }
    return {"ok": all(checks.values()), "checks": checks, "policy_digest": supplied}


def _request_usage(request: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    usage: dict[str, Any] = {}
    invalid: list[str] = []
    for key in ("commands", "files", "network_requests", "disk_mb"):
        value = request.get(key, 0)
        parsed = _strict_nonnegative_number(value, integer=key != "disk_mb")
        if parsed is None:
            invalid.append(f"{key}_usage_invalid")
            parsed = 0
        usage[key] = parsed
    return usage, invalid


def evaluate_policy_ceiling(
    policy: Mapping[str, Any], request: Mapping[str, Any], *, runtime_root: str | Path | None = None, now_epoch: float | None = None,
) -> dict[str, Any]:
    validation = validate_permission_policy(policy)
    if not validation["ok"]:
        return {"ok": False, "status": "authority_policy_invalid", "allowed_by_policy_ceiling": False, **_DENIED}
    state, state_integrity_ok = _read_policy_state_checked(runtime_root=runtime_root)
    policy_digest = validation["policy_digest"]
    if policy_digest in state.get("revocations", {}):
        return {"ok": True, "status": "authority_policy_revoked", "allowed_by_policy_ceiling": False, "policy_digest": policy_digest, **_DENIED}
    mode = str(policy.get("mode") or "deny")
    current = _strict_nonnegative_number(time.time() if now_epoch is None else now_epoch)
    capability = str(request.get("capability") or "").strip().lower()
    target = _hex64(request.get("target_digest"))
    environment = str(request.get("environment") or "").strip().lower()
    raw_scope = request.get("scope")
    scope_valid = isinstance(raw_scope, (list, tuple, set, frozenset))
    requested_scope = {str(item or "").strip().lower() for item in raw_scope or [] if str(item or "").strip()} if scope_valid else set()
    allowed_scope = set(policy.get("scope") or [])
    usage, usage_reasons = _request_usage(request)
    budgets = policy.get("budgets") if isinstance(policy.get("budgets"), Mapping) else {}
    reasons: list[str] = []
    if not state_integrity_ok:
        reasons.append("authority_state_integrity_invalid")
    if current is None:
        reasons.append("evaluation_time_invalid")
        current = 0.0
    if not scope_valid:
        reasons.append("scope_shape_invalid")
    reasons.extend(usage_reasons)
    if mode == "deny":
        reasons.append("policy_mode_deny")
    expires = float(policy.get("expires_epoch") or 0.0)
    if expires > 0.0 and current > expires:
        reasons.append("policy_expired")
    if capability != str(policy.get("capability") or ""):
        reasons.append("capability_mismatch")
    if not target or target != str(policy.get("target_digest") or ""):
        reasons.append("target_mismatch")
    if environment != str(policy.get("environment") or ""):
        reasons.append("environment_mismatch")
    if not requested_scope.issubset(allowed_scope):
        reasons.append("scope_expansion")
    for key, amount in usage.items():
        limit = _strict_nonnegative_number(budgets.get(key), integer=key != "disk_mb")
        if limit is None:
            reasons.append(f"{key}_budget_invalid")
            continue
        if amount > limit:
            reasons.append(f"{key}_budget_exceeded")
    if capability in PROTECTED_CAPABILITIES:
        reasons.append("protected_capability_requires_separate_authority")
    effect = str(request.get("effect") or "read").strip().lower()
    if mode == "read_only" and effect != "read":
        reasons.append("read_only_policy")
    if mode == "reversible_workspace" and effect in {"install", "promote", "secret", "destructive", "external_publish"}:
        reasons.append("effect_outside_reversible_workspace")
    if mode == "reviewed_installation" and effect in {"promote", "secret", "destructive", "external_publish", "authority_change"}:
        reasons.append("effect_outside_reviewed_installation")
    allowed = not reasons
    result = {
        "ok": True,
        "status": "authority_policy_ceiling_allows" if allowed else "authority_policy_ceiling_denies",
        "allowed_by_policy_ceiling": allowed,
        "policy_digest": policy_digest,
        "request_digest": _digest({
            "capability": capability, "target_digest": target, "environment": environment,
            "scope": sorted(requested_scope), "usage": usage, "effect": effect,
        }),
        "reason_codes": sorted(set(reasons)),
        "external_authority_receipt_still_required": allowed,
        "policy_decision_is_not_execution_authorization": True,
        **_DENIED,
    }
    result["decision_digest"] = _digest(result)
    return result


def revoke_policy(
    *, policy_digest: str, reason_code: str, event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    pd = _hex64(policy_digest)
    token = str(event_id or "").strip()[:160]
    reason = str(reason_code or "operator_revocation").strip().lower()[:120]
    if not pd or not token:
        return {"ok": False, "status": "policy_digest_and_event_id_required", **_DENIED}
    path = _state_path(runtime_root)
    try:
        with metadata_mutation_lock(f"era8_authority:{_digest(str(path))[:24]}"):
            state, state_integrity_ok = _read_policy_state_checked(runtime_root=runtime_root)
            if not state_integrity_ok:
                return {"ok": False, "status": "authority_policy_state_integrity_invalid", **_DENIED}
            event_digest = _digest({"event_id": token, "policy_digest": pd, "action": "revoke"})
            for row in state.get("history", []):
                if isinstance(row, Mapping) and row.get("event_digest") == event_digest:
                    return {"ok": True, "status": "authority_policy_revocation_replayed", "idempotent": True, "policy_digest": pd, **_DENIED}
            state["revocations"][pd] = {"reason_code": reason, "revoked_at": _now(), "event_digest": event_digest}
            state["history"] = (state.get("history", []) + [{"event_digest": event_digest, "policy_digest": pd, "action": "revoke", "reason_code": reason}])[-MAX_HISTORY:]
            state["revision"] = int(state.get("revision") or 0) + 1
            state["contract_version"] = CONTRACT_VERSION
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "authority_policy_revoked", "idempotent": False, "policy_digest": pd, "event_digest": event_digest, "revision": state["revision"], **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError):
        return {"ok": False, "status": "authority_policy_revocation_write_blocked", **_DENIED}


def public_policy_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state, state_integrity_ok = _read_policy_state_checked(runtime_root=runtime_root)
    return {
        "ok": state_integrity_ok,
        "status": "authority_policy_state" if state_integrity_ok else "authority_policy_state_integrity_invalid",
        "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision") or 0),
        "revoked_policy_count": len(state.get("revocations") or {}),
        "history_count": len(state.get("history") or []),
        "raw_content_exposed": False,
        "authority_effect": "restrict_or_revoke_only",
        "fail_closed_required": not state_integrity_ok,
        **_DENIED,
    }


__all__ = [
    "CONTRACT_VERSION", "POLICY_MODES", "PROTECTED_CAPABILITIES", "build_permission_policy",
    "validate_permission_policy", "evaluate_policy_ceiling", "revoke_policy", "read_policy_state",
    "public_policy_state",
]
