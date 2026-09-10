from __future__ import annotations

"""Receipt-bound execution truth for conversational action surfaces.

Generated prose is never authoritative evidence that an action ran.  This module
builds and validates content-free receipts from persisted governed-action state and
renders bounded user-facing status text from those receipts.
"""

import hashlib
import json
import re
from typing import Any, Iterable


CONTRACT_VERSION = "v1489-trial2"
_TERMINAL_SUCCESS = {"executed", "completed"}
_TERMINAL_FAILURE = {"failed", "timed_out", "cancelled", "canceled", "interrupted"}
_PENDING = {"proposed", "running", "claimed"}
_APPROVAL = {"approval_created", "approval_required", "awaiting_approval"}
_BLOCKED = {"blocked"}
_INFO = {"info"}

_CAPABILITY_BY_INTENT = {
    "run_diagnostics": "diagnostics",
    "maintenance_scan": "maintenance",
    "settings_health": "settings_health",
    "attention_center": "attention_center",
    "approval_inbox": "approvals",
    "list_notifications": "notifications",
    "watch_once": "notifications",
    "task_status": "task_project",
    "next_task": "task_project",
    "project_status": "task_project",
    "memory_status": "memory",
    "plan_session": "planning",
    "review_file": "file_review",
}

_PATHISH = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|mnt|tmp|var|usr|opt)/|\\\\|\.\./|\./)")
_SECRETISH = re.compile(r"\b(?:token|secret|password|credential|api[_ -]?key)\b", re.I)
_MAINTENANCE_ITEM = re.compile(r"^\s*\d+\.\s*\[(HIGH|MEDIUM|LOW|INFO)\]\s*(.+?)\s*$", re.I)
_DIAGNOSTIC_OVERALL = re.compile(r"^\s*Overall status:\s*([A-Z_ -]+)\s*$", re.I)
_DIAGNOSTIC_CHECK = re.compile(r"^\s*\[(FAIL|WARN)\]\s*([^:]{1,100})(?::\s*(.{1,180}))?\s*$", re.I)
_PAST_EXECUTION_CLAIM = re.compile(r"\b(?:I|we)\s+(?:ran|executed|performed|completed|finished|checked|inspected|scanned|applied|modified|updated|installed|deleted|created|built|fixed|verified|reviewed)\b|\b(?:all|system|maintenance|diagnostics?)\b.{0,40}\b(?:normal|optimal|completed|successful)\b", re.I)
_FUTURE_EXECUTION_CLAIM = re.compile(r"\b(?:I(?:'ll| will)|we(?:'ll| will))\s+(?:run|execute|perform|check|inspect|scan|apply|modify|update|install|delete|create|build|fix|verify|review)\b", re.I)


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


def capability_id_for_action(action: dict[str, Any] | None) -> str:
    if not isinstance(action, dict):
        return ""
    explicit = str(action.get("capability_id") or "").strip()
    if explicit:
        return explicit[:80]
    return _CAPABILITY_BY_INTENT.get(str(action.get("intent") or "").strip(), "governed_action")


def _completion_state(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in _TERMINAL_SUCCESS:
        return "completed"
    if normalized in {"timed_out"}:
        return "timed_out"
    if normalized in {"cancelled", "canceled"}:
        return "cancelled"
    if normalized in {"failed", "interrupted"}:
        return "failed"
    if normalized in _BLOCKED:
        return "blocked"
    if normalized in _APPROVAL:
        return "approval_required"
    if normalized in _INFO:
        return "information_only"
    if normalized == "proposed":
        return "proposed"
    if normalized in {"running", "claimed"}:
        return "running"
    return "pending"


def _action_state_payload(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": str(action.get("id") or "")[:160],
        "intent": str(action.get("intent") or "")[:80],
        "execution_mode": str(action.get("execution_mode") or "")[:40],
        "risk_level": str(action.get("risk_level") or "")[:20],
        "status": str(action.get("status") or "")[:40],
        "execution_attempt": int(action.get("execution_attempt") or 0),
        "active_attempt_id": str(action.get("active_attempt_id") or "")[:160],
        "result_summary_status": str(action.get("result_summary_status") or "")[:40],
        "event_count": len([row for row in action.get("events", []) if isinstance(row, dict)]),
    }


def build_execution_truth_receipt(action: dict[str, Any] | None) -> dict[str, Any]:
    """Build a content-free receipt from persisted action state."""
    if not isinstance(action, dict) or not str(action.get("id") or "").strip():
        return {}
    state_payload = _action_state_payload(action)
    status = str(state_payload["status"] or "proposed").lower()
    result = action.get("result") if isinstance(action.get("result"), dict) else {}
    evidence_payload = {
        "status": status,
        "result_ok": bool(result.get("ok")) if result else False,
        "result_summary_status": str(action.get("result_summary_status") or "")[:40],
        "execution_attempt": int(action.get("execution_attempt") or 0),
    }
    receipt = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "authoritative": True,
        "content_free": True,
        "raw_output_included": False,
        "action_id": state_payload["action_id"],
        "capability_id": capability_id_for_action(action),
        "intent": state_payload["intent"],
        "execution_mode": state_payload["execution_mode"],
        "risk_level": state_payload["risk_level"],
        "status": status,
        "completion_state": _completion_state(status),
        "succeeded": bool(status in _TERMINAL_SUCCESS and result and result.get("ok", True) is not False),
        "execution_attempt": state_payload["execution_attempt"],
        "action_state_digest": _digest(state_payload),
        "result_evidence_digest": _digest(evidence_payload),
    }
    receipt["receipt_digest"] = _digest(receipt)
    return receipt


def validate_execution_truth_receipt(
    receipt: dict[str, Any] | None,
    action: dict[str, Any] | None = None,
    *,
    expected_capability_id: str = "",
) -> tuple[bool, str]:
    if not isinstance(receipt, dict) or not receipt:
        return False, "missing_receipt"
    if receipt.get("authoritative") is not True or receipt.get("content_free") is not True or receipt.get("raw_output_included") is not False:
        return False, "receipt_contract_invalid"
    supplied_digest = str(receipt.get("receipt_digest") or "")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    if not supplied_digest or supplied_digest != _digest(unsigned):
        return False, "receipt_digest_invalid"
    if expected_capability_id and str(receipt.get("capability_id") or "") != str(expected_capability_id):
        return False, "capability_mismatch"
    if isinstance(action, dict):
        if str(receipt.get("action_id") or "") != str(action.get("id") or ""):
            return False, "action_id_mismatch"
        if str(receipt.get("capability_id") or "") != capability_id_for_action(action):
            return False, "action_capability_mismatch"
        state_payload = _action_state_payload(action)
        if str(receipt.get("action_state_digest") or "") != _digest(state_payload):
            return False, "action_state_tampered"
        if str(receipt.get("status") or "") != str(state_payload.get("status") or "").lower():
            return False, "action_status_mismatch"
        result = action.get("result") if isinstance(action.get("result"), dict) else {}
        evidence_payload = {
            "status": str(state_payload.get("status") or "").lower(),
            "result_ok": bool(result.get("ok")) if result else False,
            "result_summary_status": str(action.get("result_summary_status") or "")[:40],
            "execution_attempt": int(action.get("execution_attempt") or 0),
        }
        if str(receipt.get("result_evidence_digest") or "") != _digest(evidence_payload):
            return False, "result_evidence_tampered"
        expected_succeeded = bool(
            str(state_payload.get("status") or "").lower() in _TERMINAL_SUCCESS
            and result
            and result.get("ok", True) is not False
        )
        if bool(receipt.get("succeeded")) != expected_succeeded:
            return False, "success_state_mismatch"
    return True, "valid"


def _safe_fragment(value: str, limit: int = 160) -> str:
    text = " ".join(str(value or "").split()).strip(" -:;")
    if not text or _PATHISH.search(text) or _SECRETISH.search(text):
        return ""
    return text[:limit]


def summarize_verified_read_only_output(action: dict[str, Any], output: str) -> str:
    """Return a bounded, path/secret-free deterministic summary of verified output."""
    intent = str(action.get("intent") or "")
    lines = [line.rstrip() for line in str(output or "").splitlines()]
    if intent == "maintenance_scan":
        findings: list[tuple[str, str]] = []
        for line in lines:
            match = _MAINTENANCE_ITEM.match(line)
            if not match:
                continue
            title = _safe_fragment(match.group(2), 120)
            if title:
                findings.append((match.group(1).upper(), title))
        if findings:
            top = findings[:3]
            rendered = "; ".join(f"{severity}: {title}" for severity, title in top)
            suffix = f" There are {len(findings) - len(top)} additional governed findings." if len(findings) > len(top) else ""
            return f"The verified maintenance report flagged {len(findings)} item(s): {rendered}.{suffix}".strip()
        return "The verified maintenance action completed; detailed findings remain in the governed action record."
    if intent == "run_diagnostics":
        overall = ""
        findings: list[str] = []
        for line in lines:
            match = _DIAGNOSTIC_OVERALL.match(line)
            if match:
                overall = _safe_fragment(match.group(1), 40)
                continue
            match = _DIAGNOSTIC_CHECK.match(line)
            if match:
                name = _safe_fragment(match.group(2), 90)
                detail = _safe_fragment(match.group(3) or "", 120)
                if name:
                    findings.append(f"{match.group(1).upper()}: {name}" + (f" ({detail})" if detail else ""))
        lead = f"The verified diagnostic status was {overall}." if overall else "The verified diagnostic action completed."
        if findings:
            return f"{lead} Attention items: {'; '.join(findings[:3])}."
        return lead
    return "The governed action reached a verified terminal state; detailed output remains in its action record."


def render_receipt_bound_action_response(
    action: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
    *,
    verified_output: str = "",
) -> str:
    valid, _reason = validate_execution_truth_receipt(receipt, action if isinstance(action, dict) else None)
    if not valid:
        return "I recognized that as an operator action, but I do not have a valid execution receipt, so I cannot claim it ran."
    assert isinstance(receipt, dict)
    action_id = str(receipt.get("action_id") or "")
    status = str(receipt.get("status") or "")
    completion = str(receipt.get("completion_state") or "")
    reference = f" Action ID: {action_id}." if action_id else ""
    if completion == "completed" and receipt.get("succeeded") is True:
        summary = summarize_verified_read_only_output(action or {}, verified_output)
        return f"I ran the requested supervised read-only action and its receipt confirms successful completion.{reference} {summary}".strip()
    if completion == "timed_out":
        return f"The requested action reached its bounded timeout and did not produce a successful completion receipt.{reference}".strip()
    if completion == "cancelled":
        return f"The requested action was cancelled; I am not treating it as completed.{reference}".strip()
    if completion == "blocked":
        return f"The requested action is blocked by the supervised-operation boundary and did not run.{reference}".strip()
    if completion == "approval_required":
        return f"The requested action requires operator approval before execution; it has not run.{reference}".strip()
    if completion == "failed":
        return f"The requested action failed safely, so I am not reporting a successful system result.{reference}".strip()
    if completion == "information_only":
        return f"The governed action is informational only; no execution occurred.{reference}".strip()
    if completion == "proposed":
        return f"The requested action is proposed but has not started.{reference}".strip()
    if completion == "running":
        return f"The requested action has started under the governed runtime but is not complete yet.{reference}".strip()
    return f"The requested action is still pending and has no successful completion receipt yet.{reference}".strip()


def public_execution_receipt(receipt: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        return {}
    allowed = {
        "schema_version", "contract_version", "authoritative", "content_free", "raw_output_included",
        "action_id", "capability_id", "intent", "execution_mode", "risk_level", "status",
        "completion_state", "succeeded", "execution_attempt", "action_state_digest",
        "result_evidence_digest", "receipt_digest",
    }
    return {key: receipt.get(key) for key in allowed if key in receipt}


def receipt_allows_success_claim(receipt: dict[str, Any] | None, action: dict[str, Any] | None = None) -> bool:
    valid, _ = validate_execution_truth_receipt(receipt, action)
    return bool(valid and receipt and receipt.get("completion_state") == "completed" and receipt.get("succeeded") is True)


def public_action_truth_projection(action: dict[str, Any] | None, receipt: dict[str, Any] | None) -> dict[str, Any]:
    """Content-free state used by reconnect/UI surfaces; never trusts generated prose."""
    valid, reason = validate_execution_truth_receipt(receipt, action if isinstance(action, dict) else None)
    r = public_execution_receipt(receipt) if valid else {}
    status = str(r.get("completion_state") or "unverified")
    projection = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "receipt_valid": bool(valid),
        "validation_state": "valid" if valid else str(reason),
        "action_identifier_present": bool(str(r.get("action_id") or "")),
        "completion_state": status,
        "succeeded": bool(r.get("succeeded")) if valid else False,
        "execution_attempt": int(r.get("execution_attempt") or 0) if valid else 0,
        "action_state_digest": str(r.get("action_state_digest") or ""),
        "receipt_digest": str(r.get("receipt_digest") or ""),
        "raw_output_exposed": False,
        "generated_prose_authoritative": False,
        "content_free": True,
    }
    projection["projection_digest"] = _digest({k:v for k,v in projection.items() if k!="projection_digest"})
    return projection

def execution_claim_requires_receipt(text: str) -> bool:
    """Detect prose that claims actual execution or system-state completion."""
    cleaned=" ".join(str(text or "").split())
    return bool(_PAST_EXECUTION_CLAIM.search(cleaned) or _FUTURE_EXECUTION_CLAIM.search(cleaned))

def enforce_execution_claim_truth(text: str, action: dict[str, Any] | None, receipt: dict[str, Any] | None, *, verified_output: str="") -> str:
    """Central prose guard: execution-shaped claims become receipt-derived status."""
    if not execution_claim_requires_receipt(text):
        return str(text or "")
    valid,_ = validate_execution_truth_receipt(receipt, action if isinstance(action,dict) else None)
    if not valid:
        return render_receipt_bound_action_response(action, receipt)
    return render_receipt_bound_action_response(action, receipt, verified_output=verified_output)
