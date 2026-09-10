from __future__ import annotations

"""Exact, content-free approval decisions for persisted action proposals.

Approval decisions are lifecycle evidence only. They never grant execution
admission, invoke tools, store request text, or call the general approval manager.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1177.5"
MAX_DECISION_BYTES = 2048
_DECISION_RE = re.compile(r"^(approve|reject)\s+proposal\s+([a-z0-9_-]{1,80})[.!?]*$", re.I)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("records"), list):
            return value
    except Exception:
        pass
    return {"schema_version": "1", "contract_version": "v1177.2", "revision": 0, "records": []}


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def decide_action_proposal(
    path: Path | str,
    *,
    proposal_id: str,
    proposal_digest: str,
    approval_request_digest: str,
    explicit_operator_text: str,
    operator_authority: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Apply one exact operator approve/reject decision without execution authority."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    pid = str(proposal_id or "")[:80]
    pd = str(proposal_digest or "")
    ard = str(approval_request_digest or "")
    match = _DECISION_RE.fullmatch(str(explicit_operator_text or "").strip())
    decision = match.group(1).lower() if match else ""
    referenced = match.group(2) if match else ""
    authority = str(operator_authority or "").strip().lower()
    row = next((r for r in reversed(state["records"]) if r.get("proposal_id") == pid), None)
    base = {
        "ok": False, "proposal_id": pid, "approval_decided": False,
        "approval_granted": False, "authorization_granted": False,
        "execution_admitted": False, "execution_performed": False,
        "raw_content_stored": False, "argument_values_stored": False,
    }
    if not row:
        return {**base, "state": "missing", "reason": "proposal_not_found"}
    if row.get("state") in {"approved", "rejected", "cancelled", "expired", "superseded"}:
        return {**base, "state": "replayed", "reason": "proposal_already_terminal"}
    if row.get("state") != "awaiting_approval":
        return {**base, "state": str(row.get("state") or "rejected"), "reason": "proposal_not_awaiting_approval"}
    if now > float(row.get("expires_at", 0)):
        row["state"] = "expired"; row["updated_at"] = now
        state["revision"] = int(state.get("revision", 0)) + 1; _save(p, state)
        return {**base, "state": "expired", "reason": "proposal_expired"}
    exact = bool(
        match and referenced == pid and authority == "operator"
        and re.fullmatch(r"[0-9a-f]{64}", pd or "") and pd == row.get("proposal_digest")
        and re.fullmatch(r"[0-9a-f]{64}", ard or "") and ard == row.get("approval_request_digest")
    )
    if not exact:
        return {**base, "state": "rejected", "reason": "exact_operator_decision_required"}
    decision_digest = _digest({
        "proposal_id": pid, "proposal_digest": pd, "approval_request_digest": ard,
        "decision": decision, "authority": authority, "decided_at": now,
    })
    row["state"] = "approved" if decision == "approve" else "rejected"
    row["approval_decision"] = decision
    row["approval_decision_digest"] = decision_digest
    row["approval_decided"] = True
    row["approval_granted"] = decision == "approve"
    row["authorization_granted"] = False
    row["execution_admitted"] = False
    row["execution_performed"] = False
    row["updated_at"] = now
    state["contract_version"] = CONTRACT_VERSION
    state["revision"] = int(state.get("revision", 0)) + 1
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > MAX_DECISION_BYTES + 3072:
        raise ValueError("Approval-decision record exceeded bounded size")
    _save(p, state)
    return {
        "ok": True, "state": row["state"], "proposal_id": pid,
        "proposal_digest": pd, "approval_request_digest": ard,
        "approval_decision": decision, "approval_decision_digest": decision_digest,
        "approval_decided": True, "approval_granted": decision == "approve",
        "authorization_granted": False, "execution_admitted": False,
        "execution_performed": False, "raw_content_stored": False,
        "argument_values_stored": False,
    }
