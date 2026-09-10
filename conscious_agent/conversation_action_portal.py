from __future__ import annotations

"""Redacted, persistent presentation state for supervised chat actions.

The full action and command receipts remain in their governed stores. Conversation
sessions keep only this bounded summary so reload, navigation, and prompt continuity
can understand action state without retaining commands, raw output, prompts, or
private receipt data.
"""

import os
import socket
import time
from datetime import datetime
from typing import Any, Mapping

PORTAL_SCHEMA_VERSION = "3"
TERMINAL_ACTION_STATES = {"completed", "failed", "timed_out", "interrupted", "blocked", "cancelled"}
_ALLOWED_STATES = {
    "proposed", "running", "completed", "failed", "timed_out", "interrupted", "blocked", "cancelled", "awaiting_approval",
}
_STATE_LABELS = {
    "proposed": "Proposed",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
    "timed_out": "Timed out",
    "interrupted": "Interrupted",
    "blocked": "Blocked",
    "cancelled": "Cancelled",
    "awaiting_approval": "Awaiting approval",
}

_CLAIMANT_LABELS = {
    "dashboard": "the dashboard",
    "api": "the local API",
    "cli": "the command line",
    "conversation": "the conversation console",
    "process": "another Eidolon process",
}
_DEFAULT_INTERRUPTED_CLAIM_SECONDS = 240.0


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[: max(0, int(limit))]


def claim_owner_label(scope: str) -> str:
    token = _clean(scope, 40).lower() or "process"
    return _CLAIMANT_LABELS.get(token, "another Eidolon process")


def _process_is_alive(pid: int) -> bool | None:
    if pid <= 0:
        return None
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
            if not handle:
                error = int(ctypes.windll.kernel32.GetLastError())
                if error in {87, 1168}:  # invalid parameter / element not found
                    return False
                if error == 5:  # access denied still proves a process occupies the pid
                    return True
                return None
            try:
                exit_code = ctypes.c_ulong()
                if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return None
                return int(exit_code.value) == still_active
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def running_claim_is_interrupted(
    action: Mapping[str, Any] | None,
    *,
    max_age_seconds: float = _DEFAULT_INTERRUPTED_CLAIM_SECONDS,
) -> tuple[bool, str]:
    action = action or {}
    if _clean(action.get("status"), 40).lower() != "running":
        return False, ""
    owner = action.get("claim_owner") if isinstance(action.get("claim_owner"), Mapping) else {}
    scope = _clean(owner.get("scope"), 40) or "process"
    host = _clean(owner.get("host"), 160)
    pid = int(owner.get("pid") or 0)
    claimed_epoch = float(owner.get("claimed_epoch") or 0.0)
    lease_expires_epoch = float(owner.get("lease_expires_epoch") or 0.0)
    now = time.time()
    age = max(0.0, now - claimed_epoch) if claimed_epoch else 0.0
    if lease_expires_epoch and lease_expires_epoch <= now:
        return True, f"The execution claim from {claim_owner_label(scope)} expired without terminal evidence."
    same_host = bool(host and host.lower() == socket.gethostname().lower())
    if same_host and pid:
        alive = _process_is_alive(pid)
        if alive is False:
            return True, f"The execution owner in {claim_owner_label(scope)} is no longer running."
        if alive is True:
            return False, ""
    if claimed_epoch and age >= max(1.0, float(max_age_seconds)):
        return True, f"The execution claim from {claim_owner_label(scope)} exceeded its recovery window without terminal evidence."
    return False, ""


def _sanitize_activity_timeline(action: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
    events = action.get("action_events") if isinstance(action.get("action_events"), list) else []
    cleaned: list[dict[str, Any]] = []
    for item in events[-12:]:
        if not isinstance(item, Mapping):
            continue
        cleaned.append({
            "sequence": max(0, int(item.get("sequence") or 0)),
            "type": _clean(item.get("type"), 48),
            "status": _clean(item.get("status"), 40),
            "summary": _clean(item.get("summary"), 280),
            "occurred_at": _clean(item.get("occurred_at"), 40),
            "attempt_number": max(0, int(item.get("attempt_number") or 0)),
            "owner_scope": _clean(item.get("owner_scope"), 40),
            "redacted": True,
        })
    history = action.get("event_history_summary") if isinstance(action.get("event_history_summary"), Mapping) else {}
    pruned = max(0, int(history.get("pruned_event_count") or 0))
    return cleaned, pruned + len(cleaned), pruned


def normalized_action_state(action: Mapping[str, Any] | None, execution: Mapping[str, Any] | None = None) -> str:
    action = action or {}
    execution = execution or {}
    raw = _clean(execution.get("status") or action.get("status"), 40).lower()
    message = _clean(execution.get("message") or execution.get("error") or "", 240).lower()
    mode = _clean(action.get("execution_mode"), 40).lower()
    if raw in _ALLOWED_STATES:
        if raw == "running" and running_claim_is_interrupted(action)[0]:
            return "interrupted"
        return raw
    if "timed out" in message or raw in {"timeout", "timedout"}:
        return "timed_out"
    if raw in {"executed", "complete", "completed", "success", "succeeded"}:
        return "completed"
    if raw in {"approval_required", "approval_created", "pending_approval"} or mode == "approval":
        return "awaiting_approval"
    if raw == "info" or mode == "info":
        return "completed"
    if raw == "blocked" or mode == "blocked":
        return "blocked"
    if raw in {"cancelled", "canceled"}:
        return "cancelled"
    if raw in {"running", "executing", "claimed"}:
        if running_claim_is_interrupted(action)[0]:
            return "interrupted"
        return "running"
    if raw in {"failed", "error"} or execution.get("ok") is False:
        return "failed"
    return "proposed"


def build_action_portal_state(
    action: Mapping[str, Any] | None,
    execution: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(action, Mapping) or not _clean(action.get("id"), 120):
        return None
    execution = execution if isinstance(execution, Mapping) else {}
    state = normalized_action_state(action, execution)
    raw_status = _clean(execution.get("status") or action.get("status"), 40).lower()
    mode = _clean(action.get("execution_mode"), 40)
    risk = _clean(action.get("risk_level"), 24) or "unknown"
    summary_status = _clean(action.get("result_summary_status"), 40).lower()
    stored_summary = action.get("result_summary") if summary_status in {raw_status, state} else ""
    message = _clean(
        stored_summary
        or execution.get("message")
        or execution.get("error")
        or action.get("blocked_reason")
        or action.get("explanation")
        or action.get("summary"),
        360,
    )
    interrupted, interrupted_reason = running_claim_is_interrupted(action)
    if state == "interrupted" and interrupted_reason:
        message = _clean(interrupted_reason + " A safe retry requires an explicit request.", 360)
    if state == "running" and not execution.get("message") and not execution.get("error"):
        owner = action.get("claim_owner") if isinstance(action.get("claim_owner"), Mapping) else {}
        message = f"Execution is currently owned by {claim_owner_label(str(owner.get('scope') or 'process'))}; no terminal result has been persisted yet."
    retry_allowed = bool(
        state in {"failed", "timed_out", "interrupted"}
        and mode == "direct_command"
        and risk == "low"
    )
    attempts = action.get("execution_attempts") if isinstance(action.get("execution_attempts"), list) else []
    latest_attempt = attempts[-1] if attempts and isinstance(attempts[-1], Mapping) else {}
    attempt_number = max(0, int(action.get("execution_attempt") or latest_attempt.get("attempt_number") or 0))
    owner = action.get("claim_owner") if isinstance(action.get("claim_owner"), Mapping) else {}
    owner_scope = _clean(owner.get("scope"), 40)
    timeline, timeline_total, timeline_pruned = _sanitize_activity_timeline(action)
    timeline_total = max(timeline_total, int(action.get("event_sequence") or 0))
    return {
        "schema_version": PORTAL_SCHEMA_VERSION,
        "action_id": _clean(action.get("id"), 120),
        "intent": _clean(action.get("intent"), 80),
        "title": _clean(action.get("title"), 140) or "Supervised action",
        "summary": _clean(action.get("summary"), 360),
        "execution_mode": mode or "review",
        "risk_level": risk,
        "status": state,
        "status_label": _STATE_LABELS[state],
        "message": message,
        "approval_id": _clean(action.get("approval_id") or execution.get("approval_id"), 120),
        "target_action_id": _clean(action.get("target_action_id"), 120),
        "retry_allowed": retry_allowed,
        "execution_attempt": attempt_number,
        "latest_attempt_id": _clean(latest_attempt.get("attempt_id"), 140),
        "prior_attempt_count": max(0, attempt_number - 1),
        "claim_owner_scope": owner_scope,
        "claim_owner_label": claim_owner_label(owner_scope) if owner_scope else "",
        "claim_generation": max(0, int(owner.get("claim_generation") or attempt_number or 0)),
        "claim_heartbeat_at": _clean(owner.get("heartbeat_at"), 40),
        "claim_expires_at": _clean(owner.get("lease_expires_at"), 40),
        "running_elsewhere": bool(state == "running" and owner_scope),
        "activity_timeline": timeline,
        "timeline_total": timeline_total,
        "timeline_pruned": timeline_pruned,
        "evidence_preserved": True,
        "updated_at": _clean(action.get("updated_at"), 40) or _now(),
        "redacted": True,
    }


def sanitize_action_portal_state(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    synthetic_action = {
        "id": value.get("action_id"),
        "intent": value.get("intent"),
        "title": value.get("title"),
        "summary": value.get("summary"),
        "execution_mode": value.get("execution_mode"),
        "risk_level": value.get("risk_level"),
        "status": value.get("status"),
        "approval_id": value.get("approval_id"),
        "target_action_id": value.get("target_action_id"),
        "updated_at": value.get("updated_at"),
        "execution_attempt": value.get("execution_attempt"),
        "execution_attempts": [
            {
                "attempt_id": value.get("latest_attempt_id"),
                "attempt_number": value.get("execution_attempt"),
            }
        ] if value.get("latest_attempt_id") else [],
        "claim_owner": {
            "scope": value.get("claim_owner_scope"),
            "claim_generation": value.get("claim_generation"),
            "heartbeat_at": value.get("claim_heartbeat_at"),
            "lease_expires_at": value.get("claim_expires_at"),
        },
        "action_events": value.get("activity_timeline") if isinstance(value.get("activity_timeline"), list) else [],
        "event_history_summary": {"pruned_event_count": value.get("timeline_pruned")},
        "result_summary": value.get("message"),
        "result_summary_status": value.get("status"),
    }
    synthetic_execution = {
        "status": value.get("status"),
        "message": value.get("message"),
        "ok": value.get("status") == "completed",
        "approval_id": value.get("approval_id"),
    }
    result = build_action_portal_state(synthetic_action, synthetic_execution)
    if result:
        result["retry_allowed"] = bool(value.get("retry_allowed") and result["retry_allowed"])
        result["prior_attempt_count"] = max(0, int(value.get("prior_attempt_count") or 0))
        result["timeline_total"] = max(int(value.get("timeline_total") or 0), len(result.get("activity_timeline") or []))
        result["timeline_pruned"] = max(0, int(value.get("timeline_pruned") or 0))
        result["running_elsewhere"] = bool(value.get("running_elsewhere") and result.get("status") == "running")
    return result


def action_context_summary(value: Mapping[str, Any] | None) -> str:
    portal = sanitize_action_portal_state(value)
    if not portal:
        return ""
    state = portal["status_label"].lower()
    title = portal["title"]
    message = portal.get("message") or portal.get("summary") or ""
    parts = [f"Latest supervised action '{title}' is {state}."]
    if message:
        parts.append(message)
    if portal.get("approval_id"):
        parts.append("An approval item exists and remains operator-controlled.")
    if portal.get("execution_attempt"):
        parts.append(f"Persisted execution attempt {portal['execution_attempt']} is the latest attempt.")
    if portal.get("prior_attempt_count"):
        parts.append(f"{portal['prior_attempt_count']} earlier attempt record(s) remain preserved.")
    if portal.get("status") == "running" and portal.get("claim_owner_label"):
        parts.append(f"The current execution owner is {portal['claim_owner_label']}.")
    parts.append("Persisted evidence exists; do not claim any different outcome without a newer result.")
    return _clean(" ".join(parts), 520)


def portal_update_is_safe(existing: Mapping[str, Any] | None, incoming: Mapping[str, Any] | None) -> bool:
    """Prevent stale reloads from replacing a terminal or running state with a proposal."""
    old = sanitize_action_portal_state(existing)
    new = sanitize_action_portal_state(incoming)
    if not new:
        return False
    if not old:
        return True
    if old.get("action_id") != new.get("action_id"):
        return False
    old_status = str(old.get("status") or "")
    new_status = str(new.get("status") or "")
    old_attempt = max(0, int(old.get("execution_attempt") or 0))
    new_attempt = max(0, int(new.get("execution_attempt") or 0))
    if old_attempt and new_attempt and new_attempt < old_attempt:
        return False
    if old_status in {"failed", "timed_out", "interrupted"} and new_status == "running":
        return new_attempt > old_attempt
    allowed = {
        "proposed": _ALLOWED_STATES,
        "awaiting_approval": {"awaiting_approval", "completed", "failed", "blocked", "cancelled"},
        "running": {"running", "completed", "failed", "timed_out", "interrupted", "blocked", "awaiting_approval"},
        "failed": {"failed", "timed_out", "interrupted", "completed"},
        "timed_out": {"timed_out", "failed", "interrupted", "completed"},
        "interrupted": {"interrupted", "failed", "timed_out", "completed", "running"},
        "blocked": {"blocked"},
        "cancelled": {"cancelled"},
        "completed": {"completed"},
    }
    return new_status in allowed.get(old_status, {old_status})
