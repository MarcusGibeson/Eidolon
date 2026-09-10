from __future__ import annotations

"""Era 7 portable local-tool contracts and supervised handoff.

This layer does not create a new executor or authority path.  It defines typed
capabilities, deterministic previews, allowlist/rollback requirements, and
truthful terminal-result reconciliation for the existing supervised action
boundary.  Native execution remains external to this module.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Iterable, Mapping

from tool_capability_registry import CONTRACT_VERSION as RETAINED_TOOL_REGISTRY_VERSION, TOOL_CLASSES as RETAINED_TOOL_CLASSES
from authoritative_action_results import CONTRACT_VERSION as AUTHORITATIVE_RESULT_CONTRACT_VERSION

CONTRACT_VERSION = "v2125.9"
SCHEMA_VERSION = "1"
MAX_TIMEOUT_SECONDS = 60
MAX_EFFECTS = 16
MAX_ALLOWLIST = 32
RETAINED_TOOL_MAPPING = {
    "read": ("file_read", "search"),
    "write": ("file_patch",),
    "process": ("shell", "service"),
    "application": ("browser", "service"),
    "file": ("file_read", "file_patch"),
    "clipboard": (),
    "notification": (),
}

_DENIED = {
    "tool_executed": False,
    "process_started": False,
    "application_started": False,
    "file_modified": False,
    "clipboard_modified": False,
    "notification_sent": False,
    "provider_contacted": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}

# High-level classes requested by the Era 7 roadmap. Operations are deliberately
# typed; arbitrary shell text is not part of the contract.
TOOL_CONTRACTS: dict[str, dict[str, Any]] = {
    "read": {
        "operations": ("file_read", "directory_list", "process_inspect", "application_status"),
        "argument_schema": {"target": "scoped_identifier", "encoding": "optional_encoding"},
        "risk": "low", "reversible": True, "confirmation": "scope_policy",
        "effect_codes": (),
    },
    "write": {
        "operations": ("file_create", "file_replace", "file_append"),
        "argument_schema": {"target": "allowlisted_path", "content_digest": "sha256", "precondition_digest": "optional_sha256"},
        "risk": "medium", "reversible": True, "confirmation": "exact_operator_approval",
        "effect_codes": ("file_mutation",),
    },
    "process": {
        "operations": ("process_status", "process_start_declared", "process_stop_declared"),
        "argument_schema": {"process_code": "registered_process", "argv_digest": "sha256", "cwd_scope": "allowlisted_scope"},
        "risk": "medium", "reversible": True, "confirmation": "exact_operator_approval",
        "effect_codes": ("process_state_change",),
    },
    "application": {
        "operations": ("application_status", "application_launch_declared", "application_close_declared"),
        "argument_schema": {"application_code": "registered_application", "target_digest": "optional_sha256"},
        "risk": "medium", "reversible": True, "confirmation": "exact_operator_approval",
        "effect_codes": ("application_state_change",),
    },
    "file": {
        "operations": ("file_metadata", "file_copy", "file_move", "file_delete_to_recovery"),
        "argument_schema": {"source": "allowlisted_path", "destination": "optional_allowlisted_path", "precondition_digest": "optional_sha256"},
        "risk": "medium", "reversible": True, "confirmation": "exact_operator_approval",
        "effect_codes": ("filesystem_change",),
    },
    "clipboard": {
        "operations": ("clipboard_read", "clipboard_write"),
        "argument_schema": {"content_digest": "optional_sha256", "sensitivity": "classification_code"},
        "risk": "medium", "reversible": True, "confirmation": "exact_operator_approval",
        "effect_codes": ("clipboard_access",),
    },
    "notification": {
        "operations": ("notification_preview", "notification_send_declared"),
        "argument_schema": {"message_digest": "sha256", "channel": "registered_channel", "urgency": "bounded_priority"},
        "risk": "medium", "reversible": False, "confirmation": "exact_operator_approval",
        "effect_codes": ("external_attention_effect",),
    },
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _token(value: Any, limit: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text or len(text) > limit or not re.fullmatch(r"[a-z0-9_.:-]+", text):
        return ""
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _preview_digest(preview: Mapping[str, Any]) -> str:
    return _digest({
        key: value for key, value in preview.items()
        if key not in {"prepared_at", "preview_digest"}
    })


def tool_contract_registry() -> dict[str, Any]:
    rows = []
    for code, spec in TOOL_CONTRACTS.items():
        row = {
            "tool_class": code,
            "operations": list(spec["operations"]),
            "argument_schema": dict(spec["argument_schema"]),
            "risk": spec["risk"],
            "reversible": bool(spec["reversible"]),
            "confirmation": spec["confirmation"],
            "effect_codes": list(spec["effect_codes"]),
            "arbitrary_shell_allowed": False,
            "native_executor_bound": False,
            "retained_tool_codes": [tool_code for tool_code in RETAINED_TOOL_MAPPING.get(code, ()) if tool_code in RETAINED_TOOL_CLASSES],
        }
        row["contract_digest"] = _digest(row)
        rows.append(row)
    result = {
        "ok": True,
        "status": "era7_tool_contract_registry",
        "contract_version": CONTRACT_VERSION,
        "tool_classes": rows,
        "tool_class_count": len(rows),
        "typed_arguments_required": True,
        "raw_shell_contract_present": False,
        "uses_existing_supervised_action_boundary": True,
        "retained_tool_registry_contract_version": RETAINED_TOOL_REGISTRY_VERSION,
        "retained_tool_registry_codes": list(RETAINED_TOOL_CLASSES),
        "new_executor_created": False,
        "native_execution_deferred": True,
        **_DENIED,
    }
    result["registry_digest"] = _digest(result)
    return result


def build_tool_preview(
    *, tool_class: str, operation: str, argument_metadata: Mapping[str, Any] | None,
    target_scope: str, allowlist: Iterable[str] = (), timeout_seconds: int | float = 10,
    rollback_code: str = "", request_id: str = "",
) -> dict[str, Any]:
    """Build a content-minimized review packet; never execute the operation."""
    tclass = _token(tool_class, 40)
    op = _token(operation, 80)
    spec = TOOL_CONTRACTS.get(tclass)
    if not spec or op not in spec["operations"]:
        return {"ok": False, "status": "unknown_or_unregistered_tool_operation", **_DENIED}
    scope = _token(target_scope, 120)
    if not scope:
        return {"ok": False, "status": "typed_target_scope_required", **_DENIED}
    metadata = dict(argument_metadata or {})
    # Values remain private to an eventual native executor. The portable preview
    # stores only argument names, type labels, and digests supplied by the caller.
    schema = dict(spec["argument_schema"])
    unknown = sorted(set(metadata) - set(schema))
    if unknown:
        return {"ok": False, "status": "undeclared_argument_metadata_rejected", "unknown_argument_names": unknown[:16], **_DENIED}
    missing = [name for name, kind in schema.items() if not kind.startswith("optional_") and name not in metadata]
    if missing:
        return {"ok": False, "status": "required_argument_metadata_missing", "missing_argument_names": missing[:16], **_DENIED}
    normalized: dict[str, str] = {}
    for name, value in metadata.items():
        if name.endswith("digest") or "digest" in str(schema.get(name) or ""):
            dig = _hex64(value)
            if not dig and value not in {None, ""}:
                return {"ok": False, "status": "invalid_argument_digest", "argument_name": name, **_DENIED}
            normalized[name] = dig
        else:
            normalized[name] = _token(value, 120)
            if not normalized[name] and not str(schema.get(name) or "").startswith("optional_"):
                return {"ok": False, "status": "invalid_typed_argument_metadata", "argument_name": name, **_DENIED}
    allow = sorted({_token(x, 160) for x in allowlist if _token(x, 160)})[:MAX_ALLOWLIST]
    if spec["effect_codes"] and scope not in allow:
        return {"ok": False, "status": "mutating_target_scope_not_allowlisted", **_DENIED}
    rollback = _token(rollback_code, 80)
    reversible = bool(spec["reversible"])
    if reversible and spec["effect_codes"] and not rollback:
        return {"ok": False, "status": "rollback_contract_required", **_DENIED}
    try:
        timeout_value = float(timeout_seconds)
        if not math.isfinite(timeout_value):
            raise ValueError
        timeout = max(1, min(int(timeout_value), MAX_TIMEOUT_SECONDS))
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "invalid_tool_timeout", **_DENIED}
    risk = str(spec["risk"])
    preview = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "request_digest": _digest(str(request_id or "")[:200]),
        "tool_class": tclass,
        "operation": op,
        "argument_schema_digest": _digest(schema),
        "argument_metadata": normalized,
        "argument_values_included": False,
        "target_scope": scope,
        "allowlist": allow,
        "allowlist_digest": _digest(allow),
        "risk": risk,
        "reversible": reversible,
        "rollback_code": rollback,
        "confirmation_required": str(spec["confirmation"]),
        "timeout_seconds": timeout,
        "effect_codes": list(spec["effect_codes"])[:MAX_EFFECTS],
        "prepared_at": _now(),
        "state": "preview_only",
        "conversation_can_authorize": False,
        "native_executor_bound": False,
        **_DENIED,
    }
    preview["preview_digest"] = _preview_digest(preview)
    return {"ok": True, "status": "tool_preview_ready", "preview": preview, **_DENIED}


def prepare_existing_execution_handoff(
    preview: Mapping[str, Any], *, authority_policy: Mapping[str, Any] | None = None,
    authority_request: Mapping[str, Any] | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    """Describe what the retained action boundary must bind before execution.

    Era 8 may supply a fine-grained permission ceiling.  That ceiling can only
    deny or further constrain this handoff; it can never replace the existing
    proposal, approval, or execution-admission requirements.
    """
    row = deepcopy(dict(preview or {}))
    digest = _hex64(row.get("preview_digest"))
    if row.get("state") != "preview_only" or not digest or digest != _preview_digest(row):
        return {"ok": False, "status": "valid_tool_preview_required", **_DENIED}
    policy_decision = None
    if authority_policy is not None:
        try:
            from fine_grained_authority_v2200 import evaluate_policy_ceiling
            request = dict(authority_request or {})
            policy_decision = evaluate_policy_ceiling(authority_policy, request, runtime_root=runtime_root)
        except Exception:
            return {"ok": False, "status": "authority_policy_evaluation_failed_closed", **_DENIED}
        if policy_decision.get("allowed_by_policy_ceiling") is not True:
            return {
                "ok": False,
                "status": "authority_policy_ceiling_denied_tool_handoff",
                "authority_policy_decision_digest": str(policy_decision.get("decision_digest") or ""),
                "reason_codes": list(policy_decision.get("reason_codes") or [])[:16],
                **_DENIED,
            }
    packet = {
        "contract_version": CONTRACT_VERSION,
        "preview_digest": digest,
        "tool_class": _token(row.get("tool_class"), 40),
        "operation": _token(row.get("operation"), 80),
        "risk": str(row.get("risk") or "unknown"),
        "reversible": bool(row.get("reversible")),
        "allowlist_digest": _hex64(row.get("allowlist_digest")),
        "rollback_code": _token(row.get("rollback_code"), 80),
        "timeout_seconds": int(row.get("timeout_seconds") or 0),
        "requires_existing_action_proposal": True,
        "requires_exact_operator_approval": True,
        "requires_existing_execution_admission": True,
        "required_terminal_result_contract_version": AUTHORITATIVE_RESULT_CONTRACT_VERSION,
        "native_adapter_must_bind_tool_preview_digest": True,
        "authority_policy_decision_digest": str((policy_decision or {}).get("decision_digest") or ""),
        "authority_policy_can_only_restrict": True,
        "execution_admitted": False,
        "native_executor_bound": False,
        "conversation_can_authorize": False,
        "conversation_can_execute": False,
        **_DENIED,
    }
    packet["handoff_digest"] = _digest(packet)
    return {"ok": True, "status": "existing_supervised_action_handoff_ready", "handoff": packet, **_DENIED}


def reconcile_tool_result(preview: Mapping[str, Any], result_receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Truthfully project a terminal result from the retained v1178 boundary.

    Era 7 requires the native adapter to bind the tool preview digest into the
    authoritative result receipt. Generated prose or an arbitrary mapping with
    ``authoritative=True`` is insufficient.
    """
    preview_row = dict(preview or {})
    pd = _hex64(preview_row.get("preview_digest"))
    if not pd or pd != _preview_digest(preview_row):
        return {"ok": False, "status": "valid_tool_preview_required", "truth_state": "unknown", "success_claim_allowed": False, **_DENIED}
    receipt = dict(result_receipt or {})
    bound_preview = _hex64(receipt.get("tool_preview_digest"))
    operation_digest = _hex64(receipt.get("operation_digest"))
    terminal_digest = _hex64(receipt.get("terminal_result_digest"))
    contract_ok = str(receipt.get("contract_version") or "") == AUTHORITATIVE_RESULT_CONTRACT_VERSION
    terminal_ok = receipt.get("terminal") is True and bool(terminal_digest) and bool(operation_digest)
    binding_ok = bool(pd and bound_preview == pd)
    canonical_states = {
        "execution_succeeded": "succeeded",
        "execution_failed": "failed",
        "execution_cancelled": "cancelled",
        "execution_timed_out": "timed_out",
    }
    raw_state = str(receipt.get("state") or "")
    state = canonical_states.get(raw_state, "uncertain")
    authoritative = bool(contract_ok and terminal_ok and binding_ok and raw_state in canonical_states)
    if not authoritative:
        return {
            "ok": False, "status": "matching_retained_terminal_result_required",
            "truth_state": "unknown", "success_claim_allowed": False,
            "generated_mapping_is_authoritative": False,
            "required_contract_version": AUTHORITATIVE_RESULT_CONTRACT_VERSION,
            "raw_output_included": False, **_DENIED,
        }
    result = {
        "ok": state == "succeeded",
        "status": "tool_result_reconciled",
        "truth_state": state,
        "preview_digest": pd,
        "operation_digest": operation_digest,
        "terminal_result_digest": terminal_digest,
        "outcome_digest": _hex64(receipt.get("outcome_digest")),
        "rollback_performed": bool(receipt.get("rollback_performed")),
        "success_claim_allowed": state == "succeeded",
        "failure_claim_allowed": state in {"failed", "timed_out", "cancelled"},
        "uncertain_result_must_remain_uncertain": False,
        "raw_output_included": False,
        "result_is_retained_authoritative_receipt_projection": True,
        **_DENIED,
    }
    result["reconciliation_digest"] = _digest(result)
    return result


def process_era7_tool_control(text: str) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {"show local tool contracts", "inspect local tool contracts", "show era7 tool contracts"}
    if raw in exact:
        return {"active": True, **tool_contract_registry()}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era7_tool_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "TOOL_CONTRACTS", "tool_contract_registry", "build_tool_preview",
    "prepare_existing_execution_handoff", "reconcile_tool_result", "process_era7_tool_control",
]
