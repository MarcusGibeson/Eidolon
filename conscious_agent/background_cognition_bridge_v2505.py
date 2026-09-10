from __future__ import annotations

"""v2505.7 bridge from retained Era-6 scheduler tickets to unified cognition.

Accepts only exact prepared, non-authorizing scheduler evidence. It never marks
the scheduler ticket complete and never infers execution authority from it.
"""

import hashlib
from typing import Any, Mapping

CONTRACT_VERSION = "v2505.7"
_ALLOWED = {
    "read_only_inspection": {"trigger_type": "background_inspection", "new_experience": False},
    "memory_consolidation_review": {"trigger_type": "background_memory_review", "new_experience": True},
    "plan_review": {"trigger_type": "background_plan_review", "new_experience": False},
}


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def validate_background_scheduler_ticket(ticket: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(ticket, Mapping):
        raise ValueError("scheduler ticket required")
    ticket_id = str(ticket.get("ticket_id") or "").strip()
    work_kind = str(ticket.get("work_kind") or "").strip().lower()
    status = str(ticket.get("status") or "").strip().lower()
    evidence_digest = str(ticket.get("evidence_digest") or "").strip().lower()
    execution_authorized = bool(ticket.get("execution_authorized"))
    if not ticket_id:
        raise ValueError("scheduler ticket_id required")
    if status != "prepared_not_executed":
        raise ValueError("scheduler ticket must be prepared_not_executed")
    if work_kind not in _ALLOWED:
        raise ValueError("scheduler work_kind is not background-cognition safe")
    if execution_authorized:
        raise ValueError("scheduler ticket must not carry execution authority")
    if len(evidence_digest) != 64 or any(ch not in "0123456789abcdef" for ch in evidence_digest):
        raise ValueError("scheduler evidence digest required")
    spec = _ALLOWED[work_kind]
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "ticket_id": ticket_id,
        "ticket_ref": "scheduler-ticket-digest:" + _sha(ticket_id)[:32],
        "work_kind": work_kind,
        "trigger_type": spec["trigger_type"],
        "new_experience": bool(spec["new_experience"]),
        "subject_ref": "background-evidence:" + evidence_digest,
        "scheduler_ticket_completion_implied": False,
        "execution_authority_inferred": False,
        "provider_authority_inferred": False,
        "message_authority_inferred": False,
    }


__all__ = ["CONTRACT_VERSION", "validate_background_scheduler_ticket"]
