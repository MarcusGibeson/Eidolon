from __future__ import annotations

"""v1090.2 explicit operator review findings for registered candidates."""

from datetime import datetime, timezone
from typing import Any, Mapping
import hashlib
import json
import re
import uuid

from conversation_evaluation_finding import EvaluationFindingError, mutate_evaluation_finding
from repair_candidate_registration import build_repair_candidate_registrations, load_registered_repair_candidate_private
from repair_candidate_review_protocol import (
    MAX_CANDIDATE_REVIEW_NOTE_CHARS,
    MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
    REPAIR_CANDIDATE_REVIEW_AREAS,
    REPAIR_CANDIDATE_REVIEW_STATES,
)

REPAIR_CANDIDATE_REVIEW_SCHEMA_VERSION = "1"
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_ALLOWED_TRANSITIONS = {
    "registered": {"reviewing", "rejected", "superseded"},
    "reviewing": {"needs_changes", "acceptable_for_testing", "rejected", "superseded"},
    "needs_changes": {"reviewing", "rejected", "superseded"},
    "acceptable_for_testing": {"reviewing", "rejected", "superseded"},
    "rejected": set(),
    "superseded": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _private_note(value: str) -> str:
    note = str(value or "").strip()
    if len(note) > MAX_CANDIDATE_REVIEW_NOTE_CHARS:
        raise EvaluationFindingError(f"Candidate review note exceeds the {MAX_CANDIDATE_REVIEW_NOTE_CHARS}-character limit.")
    return note


def _evidence(value: str) -> str:
    token = str(value or "").strip().upper()
    if token and not _SHA256_RE.fullmatch(token):
        raise EvaluationFindingError("Candidate review evidence digest must be a SHA-256 hexadecimal digest.")
    return token


def _public_event(event: Mapping[str, Any]) -> dict[str, Any]:
    note = str(event.get("private_note") or "")
    return {
        "review_event_id": str(event.get("review_event_id") or ""),
        "review_area": str(event.get("review_area") or ""),
        "review_outcome": str(event.get("review_outcome") or ""),
        "evidence_digest": str(event.get("evidence_digest") or ""),
        "recorded_at": str(event.get("recorded_at") or ""),
        "private_note_present": bool(note),
        "private_note_digest": _digest(note) if note else "",
        "private_note_returned": False,
    }


def build_repair_candidate_review(finding_id: str, candidate_id: str) -> dict[str, Any]:
    finding, candidate = load_registered_repair_candidate_private(finding_id, candidate_id)
    events = [_public_event(event) for event in list(candidate.get("review_events") or ()) if isinstance(event, Mapping)]
    stable = {
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
        "review_state": str(candidate.get("review_state") or "registered"),
        "review_event_count": len(events),
        "maximum_review_events": MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
        "review_events": events,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_review",
        "schema_version": REPAIR_CANDIDATE_REVIEW_SCHEMA_VERSION,
        **stable,
        "review_digest": _digest(stable),
        "most_favorable_state": "acceptable_for_testing",
        "application_approval_state_exists": False,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "private_notes_returned": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_prioritization": False,
        "candidate_ranked": False,
        "patch_generated": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "provider_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def record_repair_candidate_review(
    finding_id: str,
    candidate_id: str,
    *,
    review_area: str,
    review_outcome: str,
    evidence_digest: str = "",
    note: str = "",
    expected_revision: int | None,
    operator_confirmed: bool,
) -> dict[str, Any]:
    area = str(review_area or "").strip().lower()
    outcome = str(review_outcome or "").strip().lower()
    if area not in REPAIR_CANDIDATE_REVIEW_AREAS:
        raise EvaluationFindingError("Unsupported repair candidate review area.")
    if outcome not in REPAIR_CANDIDATE_REVIEW_STATES or outcome == "registered":
        raise EvaluationFindingError("Unsupported repair candidate review outcome.")
    evidence = _evidence(evidence_digest)
    private_note = _private_note(note)

    class _Idempotent(Exception):
        pass

    def apply(record: dict[str, Any]) -> None:
        rows = [dict(row) for row in list(record.get("repair_candidate_review_records") or ()) if isinstance(row, Mapping)]
        candidate = next((row for row in rows if str(row.get("candidate_id") or "") == str(candidate_id or "")), None)
        if candidate is None:
            raise EvaluationFindingError("Repair candidate registration not found.")
        current = str(candidate.get("review_state") or "registered")
        events = [dict(event) for event in list(candidate.get("review_events") or ()) if isinstance(event, Mapping)]
        signature = (area, outcome, evidence, private_note)
        for event in events:
            if (event.get("review_area"), event.get("review_outcome"), event.get("evidence_digest"), event.get("private_note")) == signature:
                raise _Idempotent
        if outcome not in _ALLOWED_TRANSITIONS.get(current, set()):
            raise EvaluationFindingError(f"Repair candidate review cannot transition from {current} to {outcome}.")
        if len(events) >= MAX_REPAIR_CANDIDATE_REVIEW_EVENTS:
            raise EvaluationFindingError("The repair candidate has reached the review-event limit.")
        now = _now()
        events.append({
            "review_event_id": f"candidate_review_{uuid.uuid4().hex[:16]}",
            "review_area": area,
            "review_outcome": outcome,
            "evidence_digest": evidence,
            "private_note": private_note,
            "recorded_at": now,
        })
        candidate["review_events"] = events
        candidate["review_state"] = outcome
        candidate["updated_at"] = now
        record["repair_candidate_review_records"] = rows

    try:
        mutate_evaluation_finding(
            finding_id,
            expected_revision=expected_revision,
            operator_confirmed=operator_confirmed,
            mutator=apply,
        )
    except _Idempotent:
        result = build_repair_candidate_review(finding_id, candidate_id)
        result["duplicate_review_event"] = True
        return result
    result = build_repair_candidate_review(finding_id, candidate_id)
    result["duplicate_review_event"] = False
    return result


def repair_candidate_review_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {"private_note", "note", "notes", "private_label", "private_reference", "content", "text", "transcript", "prompt", "provider_payload", "credentials", "vectors", "hidden_reasoning", "chain_of_thought"}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
