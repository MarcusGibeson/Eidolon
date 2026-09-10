from __future__ import annotations

"""Exact approval-to-execution admission for persisted action proposals.

This layer binds one approved proposal to one explicit operator authorization and
one stable operation identity. It may record execution admission, but it never
invokes an executor, tool, provider, source mutation, or approval manager.
"""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from supervised_action_execution import build_supervised_execution_projection

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1177.8"
MAX_RECEIPT_BYTES = 3072
_AUTHORIZE_RE = re.compile(
    r"^authorize\s+execution\s+for\s+proposal\s+([a-z0-9_-]{1,80})[.!?]*$", re.I
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("records"), list):
            return value
    except Exception:
        pass
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "records": []}


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


def authorize_action_proposal_execution(
    path: Path | str,
    *,
    proposal_id: str,
    proposal_digest: str,
    approval_decision_digest: str,
    explicit_operator_text: str,
    operator_authority: str,
    operation_id: str,
    prior_result_receipts: Iterable[Mapping[str, Any]] = (),
    now: float | None = None,
) -> dict[str, Any]:
    """Admit one approved proposal for execution without performing execution."""
    now = float(time.time() if now is None else now)
    p = Path(path)
    state = _load(p)
    pid = str(proposal_id or "")[:80]
    pd = _hex64(proposal_digest)
    add = _hex64(approval_decision_digest)
    match = _AUTHORIZE_RE.fullmatch(str(explicit_operator_text or "").strip())
    referenced = match.group(1) if match else ""
    authority = str(operator_authority or "").strip().lower()
    row = next((r for r in reversed(state["records"]) if r.get("proposal_id") == pid), None)
    base = {
        "ok": False,
        "proposal_id": pid,
        "authorization_granted": False,
        "execution_admitted": False,
        "execution_performed": False,
        "executor_invoked": False,
        "raw_content_stored": False,
        "argument_values_stored": False,
    }
    if not row:
        return {**base, "state": "missing", "reason": "proposal_not_found"}
    if row.get("state") == "execution_admitted" or row.get("execution_admitted") is True:
        return {**base, "state": "replayed", "reason": "operation_already_admitted"}
    if row.get("state") != "approved" or row.get("approval_granted") is not True:
        return {**base, "state": str(row.get("state") or "rejected"), "reason": "approved_proposal_required"}
    if now > float(row.get("expires_at", 0)):
        row["state"] = "expired"
        row["updated_at"] = now
        state["revision"] = int(state.get("revision", 0)) + 1
        _save(p, state)
        return {**base, "state": "expired", "reason": "proposal_expired"}
    exact = bool(
        match
        and referenced == pid
        and authority == "operator"
        and pd == row.get("proposal_digest")
        and add == row.get("approval_decision_digest")
        and row.get("approval_decision") == "approve"
    )
    if not exact:
        return {**base, "state": "rejected", "reason": "exact_operator_authorization_required"}

    handoff = {
        "proposal": {
            "capability_id": row.get("capability_id"),
            "proposal_digest": row.get("proposal_digest"),
            "proposal_state": "approved",
            "risk_level": row.get("risk_level"),
            "reversible": row.get("reversible"),
        }
    }
    approval_receipt = {
        "authoritative": True,
        "status": "approved",
        "authority": "operator",
        "capability_id": row.get("capability_id"),
        "proposal_digest": row.get("proposal_digest"),
        "approval_digest": row.get("approval_decision_digest"),
        "revoked": False,
        "expired": False,
    }
    projection = build_supervised_execution_projection(
        handoff,
        approval_receipt=approval_receipt,
        prior_result_receipts=prior_result_receipts,
        operation_id=str(operation_id or "")[:160],
    )
    if not projection.get("admitted"):
        return {
            **base,
            "state": "not_admitted",
            "reason": "execution_admission_requirements_not_satisfied",
            "reason_codes": list(projection.get("reason_codes") or [])[:8],
            "operation_digest": projection.get("operation_digest") or "",
        }

    authorization_digest = _digest({
        "proposal_id": pid,
        "proposal_digest": pd,
        "approval_decision_digest": add,
        "operation_digest": projection["operation_digest"],
        "authority": authority,
        "authorized_at": now,
    })
    row["state"] = "execution_admitted"
    row["authorization_granted"] = True
    row["authorization_digest"] = authorization_digest
    row["operation_digest"] = projection["operation_digest"]
    row["execution_admission_digest"] = projection["projection_digest"]
    row["execution_admitted"] = True
    row["execution_performed"] = False
    row["updated_at"] = now
    state["contract_version"] = CONTRACT_VERSION
    state["revision"] = int(state.get("revision", 0)) + 1
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > MAX_RECEIPT_BYTES + 3072:
        raise ValueError("Execution-admission record exceeded bounded size")
    _save(p, state)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "state": "execution_admitted",
        "proposal_id": pid,
        "proposal_digest": pd,
        "capability_id": row.get("capability_id"),
        "approval_decision_digest": add,
        "authorization_digest": authorization_digest,
        "operation_digest": projection["operation_digest"],
        "execution_admission_digest": projection["projection_digest"],
        "authorization_granted": True,
        "execution_admitted": True,
        "execution_performed": False,
        "executor_invoked": False,
        "conversation_can_authorize": False,
        "conversation_can_execute": False,
        "automatic_authorization_allowed": False,
        "raw_content_stored": False,
        "argument_values_stored": False,
        "raw_output_included": False,
        "content_free": True,
    }
    receipt["receipt_digest"] = _digest(receipt)
    if len(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()) > MAX_RECEIPT_BYTES:
        raise ValueError("Execution-admission receipt exceeded bounded size")
    return receipt
