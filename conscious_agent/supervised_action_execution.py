from __future__ import annotations

"""Governed execution admission and bounded authoritative result foundations.

Conversation may inspect this contract, but cannot invoke execution. Execution is
available only to a separate supervised control surface that supplies an exact,
digest-bound approval record and a registered executor callable.
"""

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable, Iterable, Mapping

from chat_action_router import SUPERVISED_CAPABILITY_REGISTRY

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1177.8"
MAX_RESULT_BYTES = 3072
MAX_TIMEOUT_SECONDS = 30.0
EXECUTION_ELIGIBLE_CAPABILITIES = frozenset({"diagnostics", "maintenance", "settings_health"})
_CAPABILITIES = {str(row["id"]): dict(row) for row in SUPERVISED_CAPABILITY_REGISTRY}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").lower()
    return text if len(text) == 64 and all(c in "0123456789abcdef" for c in text) else ""


def _bounded_token(value: Any, limit: int = 96) -> str:
    text = str(value or "").strip().lower()
    return text[:limit] if text and all(c.isalnum() or c in "_-:." for c in text[:limit]) else ""


def build_supervised_execution_projection(
    action_handoff: Mapping[str, Any],
    *,
    approval_receipt: Mapping[str, Any] | None = None,
    prior_result_receipts: Iterable[Mapping[str, Any]] = (),
    operation_id: str = "",
) -> dict[str, Any]:
    proposal = dict(action_handoff.get("proposal") or {})
    capability_id = _bounded_token(proposal.get("capability_id"), 80)
    proposal_digest = _hex64(proposal.get("proposal_digest"))
    operation_digest = _digest(str(operation_id)[:160]) if operation_id else ""
    approval = dict(approval_receipt or {})
    approval_valid = bool(
        approval.get("authoritative") is True
        and approval.get("status") == "approved"
        and approval.get("authority") == "operator"
        and _bounded_token(approval.get("capability_id"), 80) == capability_id
        and _hex64(approval.get("proposal_digest")) == proposal_digest
        and _hex64(approval.get("approval_digest"))
        and approval.get("revoked") is not True
        and approval.get("expired") is not True
    )
    prior = [dict(row) for row in prior_result_receipts if isinstance(row, Mapping)]
    replay = bool(operation_digest and any(
        _hex64(row.get("operation_digest")) == operation_digest
        and row.get("terminal") is True
        for row in prior[-32:]
    ))
    registry = _CAPABILITIES.get(capability_id, {})
    registered = capability_id in _CAPABILITIES
    eligible = bool(
        registered
        and capability_id in EXECUTION_ELIGIBLE_CAPABILITIES
        and proposal.get("proposal_state") in {"ready_for_operator_review", "proposed", "awaiting_approval", "approved"}
        and proposal.get("reversible") is True
        and str(proposal.get("risk_level") or "") in {"low", "none"}
    )
    admitted = bool(eligible and approval_valid and operation_digest and not replay)
    reason_codes = []
    if not registered: reason_codes.append("capability_not_registered")
    elif capability_id not in EXECUTION_ELIGIBLE_CAPABILITIES: reason_codes.append("capability_not_execution_eligible")
    if not approval_valid: reason_codes.append("exact_authoritative_approval_required")
    if not operation_digest: reason_codes.append("operation_identity_required")
    if replay: reason_codes.append("terminal_operation_replay_blocked")
    if eligible and approval_valid and operation_digest and not replay: reason_codes.append("admission_requirements_satisfied")
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "capability_id": capability_id if registered else "",
        "registered_capability": registered,
        "registry_boundary": str(registry.get("boundary") or "")[:80],
        "execution_eligible": eligible,
        "approval_verified": approval_valid,
        "operation_digest": operation_digest,
        "replay_detected": replay,
        "admitted": admitted,
        "executed": False,
        "terminal": False,
        "state": "admitted_not_started" if admitted else "not_admitted",
        "reason_codes": reason_codes[:8],
        "conversation_can_execute": False,
        "automatic_approval_allowed": False,
        "raw_arguments_included": False,
        "raw_output_included": False,
        "content_free": True,
        "authority_free_projection": True,
    }
    result["projection_digest"] = _digest(result)
    return result


def execute_supervised_action(
    projection: Mapping[str, Any],
    *,
    executor: Callable[[], Mapping[str, Any]],
    cancel_event: threading.Event | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    started = time.monotonic()
    capability_id = _bounded_token(projection.get("capability_id"), 80)
    admitted = bool(projection.get("admitted"))
    timeout = max(0.01, min(float(timeout_seconds), MAX_TIMEOUT_SECONDS))
    state = "blocked"
    ok = False
    outcome_digest = ""
    error_kind = "not_admitted"
    if admitted and capability_id in EXECUTION_ELIGIBLE_CAPABILITIES and callable(executor):
        if cancel_event is not None and cancel_event.is_set():
            state, error_kind = "cancelled", "cancelled_before_start"
        else:
            pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eidolon-supervised-action")
            future = pool.submit(executor)
            try:
                payload = future.result(timeout=timeout)
                if cancel_event is not None and cancel_event.is_set():
                    state, error_kind = "cancelled", "cancelled_during_execution"
                elif not isinstance(payload, Mapping):
                    state, error_kind = "failed", "malformed_executor_result"
                else:
                    sanitized = {
                        "ok": bool(payload.get("ok")),
                        "status": str(payload.get("status") or "completed")[:40],
                        "result_kind": str(payload.get("result_kind") or capability_id)[:60],
                        "item_count": max(0, min(int(payload.get("item_count") or 0), 100000)),
                    }
                    outcome_digest = _digest(sanitized)
                    ok = sanitized["ok"]
                    state = "succeeded" if ok else "failed"
                    error_kind = "" if ok else "executor_reported_failure"
            except FutureTimeout:
                future.cancel()
                state, error_kind = "timed_out", "bounded_timeout"
            except Exception:
                state, error_kind = "failed", "executor_exception"
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "capability_id": capability_id,
        "operation_digest": _hex64(projection.get("operation_digest")),
        "admission_projection_digest": _hex64(projection.get("projection_digest")),
        "state": state,
        "ok": ok,
        "executed": bool(admitted and state not in {"blocked", "cancelled"}),
        "terminal": True,
        "elapsed_ms": min(elapsed_ms, 120000),
        "outcome_digest": outcome_digest,
        "error_kind": error_kind,
        "replay_safe": True,
        "content_free": True,
        "raw_output_included": False,
        "raw_arguments_included": False,
        "authority_granted": False,
        "source_modified": False,
    }
    receipt["result_digest"] = _digest(receipt)
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError("Supervised action result exceeded bounded contract")
    receipt["receipt_bytes"] = len(encoded)
    return receipt


def supervised_execution_prompt(projection: Mapping[str, Any]) -> str:
    return "\n".join([
        "Supervised action execution boundary (authoritative control remains external):",
        f"- Capability: {projection.get('capability_id') or 'none'}; eligible: {str(bool(projection.get('execution_eligible'))).lower()}.",
        f"- Exact approval verified: {str(bool(projection.get('approval_verified'))).lower()}; admitted: {str(bool(projection.get('admitted'))).lower()}.",
        "- Conversation cannot invoke execution or create approval. Do not claim success without an authoritative terminal result receipt.",
        "- Raw arguments and raw tool output must not be exposed in conversation diagnostics.",
    ])


def supervised_execution_public(projection: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "schema_version", "contract_version", "capability_id", "registered_capability",
        "registry_boundary", "execution_eligible", "approval_verified", "operation_digest",
        "replay_detected", "admitted", "executed", "terminal", "state", "reason_codes",
        "conversation_can_execute", "automatic_approval_allowed", "raw_arguments_included",
        "raw_output_included", "content_free", "authority_free_projection", "projection_digest",
    )
    return {key: projection.get(key) for key in allowed}
