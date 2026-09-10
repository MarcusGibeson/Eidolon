from __future__ import annotations

"""Content-free persisted action proposals and explicit approval-request foundations.

This module persists only bounded proposal identity and governance metadata. It
never stores request text, argument values, conversations, prompts, memories,
provider payloads, approval decisions, or execution authority.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1177.8"
MAX_RECORDS = 64
MAX_RECORD_BYTES = 3072
MAX_AGE_SECONDS = 7 * 86400
PROPOSAL_STATES = {"proposed", "awaiting_approval", "approved", "rejected", "cancelled", "expired", "superseded", "execution_admitted", "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"}
TERMINAL_STATES = {"approved", "rejected", "cancelled", "expired", "superseded", "execution_admitted", "execution_succeeded", "execution_failed", "execution_cancelled", "execution_timed_out"}
_EXPLICIT_APPROVAL_REQUEST = re.compile(
    r"^(?:please\s+)?request\s+approval\s+for\s+(?:the\s+)?([a-z0-9_-]{1,80})(?:\s+proposal)?[.!?]*$",
    re.I,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _clean_digest(value: Any) -> str:
    text = str(value or "")
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _bounded_id(value: Any, limit: int = 80) -> str:
    text = str(value or "").strip().lower()
    return text[:limit] if re.fullmatch(r"[a-z0-9_-]{1,80}", text) else ""


def _default() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "records": []}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("records"), list):
            return _default()
        return value
    except Exception:
        return _default()


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def _proposal_source(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = dict(candidate or {})
    proposal = dict(candidate.get("proposal") or candidate.get("proposal_handoff", {}).get("proposal") or {})
    binding = dict(candidate.get("proposal_binding") or {})
    return proposal, binding


def persist_action_proposal(
    path: Path | str,
    candidate: Mapping[str, Any],
    *,
    expected_proposal_digest: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Persist an exact, content-free proposal candidate without creating approval."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    proposal, binding = _proposal_source(candidate)
    capability_id = _bounded_id(proposal.get("capability_id") or binding.get("capability_id"))
    proposal_digest = _clean_digest(proposal.get("proposal_digest") or binding.get("proposal_digest"))
    expected = _clean_digest(expected_proposal_digest)
    source_projection_digest = _clean_digest(proposal.get("source_projection_digest"))
    argument_binding_digest = _clean_digest(binding.get("argument_binding_digest"))
    clarification_digest = _clean_digest(binding.get("clarification_digest"))
    bound_names = sorted({_bounded_id(v) for v in list(binding.get("bound_argument_names") or []) if _bounded_id(v)})[:4]
    eligible_state = proposal.get("proposal_state") == "ready_for_operator_review" or binding.get("state") == "ready_for_separate_persistence"
    exact = bool(capability_id and proposal_digest and expected == proposal_digest and eligible_state)
    if not exact:
        return {
            "ok": False, "state": "rejected", "reason": "proposal_candidate_not_exact",
            "persisted": False, "approval_requested": False, "approval_created": False,
            "authorization_granted": False, "execution_performed": False,
        }
    duplicate = next((r for r in state["records"] if r.get("proposal_digest") == proposal_digest and r.get("state") in {"proposed", "awaiting_approval"}), None)
    if duplicate:
        return {
            "ok": True, "state": "duplicate", "proposal_id": duplicate["proposal_id"],
            "proposal_digest": proposal_digest, "persisted": False,
            "approval_requested": duplicate.get("state") == "awaiting_approval",
            "approval_created": False, "authorization_granted": False, "execution_performed": False,
        }
    for row in state["records"]:
        if row.get("capability_id") == capability_id and row.get("state") == "proposed":
            row["state"] = "superseded"
            row["updated_at"] = now
    proposal_id = "action_proposal_" + _digest({"proposal_digest": proposal_digest, "created_at": now})[:24]
    record = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_digest": proposal_digest,
        "capability_id": capability_id,
        "source_projection_digest": source_projection_digest,
        "argument_binding_digest": argument_binding_digest,
        "clarification_digest": clarification_digest,
        "bound_argument_names": bound_names,
        "risk_level": str(proposal.get("risk_level") or "unknown")[:20],
        "reversible": bool(proposal.get("reversible")),
        "required_authority": str(proposal.get("required_authority") or "operator")[:120],
        "state": "proposed",
        "created_at": now,
        "updated_at": now,
        "expires_at": now + MAX_AGE_SECONDS,
        "approval_request_digest": "",
        "approval_requested": False,
        "approval_created": False,
        "approval_granted": False,
        "approval_decided": False,
        "approval_decision": "",
        "approval_decision_digest": "",
        "authorization_granted": False,
        "authorization_digest": "",
        "operation_digest": "",
        "execution_admission_digest": "",
        "execution_admitted": False,
        "execution_performed": False,
        "raw_content_stored": False,
        "argument_values_stored": False,
    }
    if len(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()) > MAX_RECORD_BYTES:
        raise ValueError("Persisted action proposal exceeded bounded record size")
    state["records"].append(record)
    state["records"] = state["records"][-MAX_RECORDS:]
    state["revision"] = int(state.get("revision", 0)) + 1
    _save(p, state)
    return {
        "ok": True, "state": "proposed", "proposal_id": proposal_id,
        "proposal_digest": proposal_digest, "persisted": True,
        "approval_requested": False, "approval_created": False,
        "authorization_granted": False, "execution_performed": False,
    }


def request_action_proposal_approval(
    path: Path | str,
    *,
    proposal_id: str,
    proposal_digest: str,
    explicit_control_text: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Record an explicit request for operator approval; never create or grant it."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    pid = str(proposal_id or "")[:80]
    digest = _clean_digest(proposal_digest)
    row = next((r for r in reversed(state["records"]) if r.get("proposal_id") == pid), None)
    if not row:
        return {"ok": False, "state": "missing", "approval_requested": False, "approval_created": False, "authorization_granted": False, "execution_performed": False}
    if row.get("state") == "proposed" and now > float(row.get("expires_at", 0)):
        row["state"] = "expired"; row["updated_at"] = now; state["revision"] = int(state.get("revision", 0)) + 1; _save(p, state)
    match = _EXPLICIT_APPROVAL_REQUEST.fullmatch(str(explicit_control_text or "").strip())
    referenced = _bounded_id(match.group(1)) if match else ""
    exact = bool(match and referenced == row.get("capability_id") and digest == row.get("proposal_digest"))
    if row.get("state") == "awaiting_approval":
        return {"ok": False, "state": "replayed", "approval_requested": True, "approval_created": False, "authorization_granted": False, "execution_performed": False}
    if row.get("state") != "proposed" or not exact:
        return {"ok": False, "state": str(row.get("state") or "rejected"), "reason": "explicit_exact_request_required", "approval_requested": False, "approval_created": False, "authorization_granted": False, "execution_performed": False}
    request_digest = _digest({"proposal_id": pid, "proposal_digest": digest, "capability_id": referenced, "requested_at": now})
    row["state"] = "awaiting_approval"
    row["approval_request_digest"] = request_digest
    row["approval_requested"] = True
    row["updated_at"] = now
    state["revision"] = int(state.get("revision", 0)) + 1
    _save(p, state)
    return {
        "ok": True, "state": "awaiting_approval", "proposal_id": pid,
        "proposal_digest": digest, "approval_request_digest": request_digest,
        "approval_requested": True, "approval_created": False, "approval_granted": False,
        "approval_decided": False,
        "approval_decision": "",
        "approval_decision_digest": "",
        "authorization_granted": False, "execution_admitted": False, "execution_performed": False,
        "go_ahead_is_approval": False,
    }


def inspect_persisted_action_proposals(path: Path | str, *, now: float | None = None) -> dict[str, Any]:
    now = float(time.time() if now is None else now)
    state = _load(Path(path))
    counts: dict[str, int] = {}
    for row in state["records"]:
        status = str(row.get("state") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    result = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision", 0)), "record_count": len(state["records"]),
        "state_counts": counts, "proposed_count": counts.get("proposed", 0),
        "awaiting_approval_count": counts.get("awaiting_approval", 0),
        "expired_due_count": sum(1 for r in state["records"] if r.get("state") == "proposed" and now > float(r.get("expires_at", 0))),
        "raw_content_exposed": False, "argument_values_exposed": False,
        "approval_created": False, "approval_granted": False,
        "approval_decided": False,
        "approval_decision": "",
        "approval_decision_digest": "",
        "authorization_granted": False, "execution_performed": False,
    }
    result["inspection_digest"] = _digest(result)
    return result
