from __future__ import annotations

"""Explicit v1089.4 operator finding triage and review disposition."""

from typing import Any, Mapping
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError, load_evaluation_finding_private, mutate_evaluation_finding

FINDING_TRIAGE_SCHEMA_VERSION = "1"
FINDING_TRIAGE_STATES = ("not_started", "in_review", "completed")
FINDING_TRIAGE_DISPOSITIONS = ("acknowledged", "reproduction_required", "repair_candidate_review", "deferred", "dismissed")
MAX_TRIAGE_NOTE_CHARS = 2000


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _record(record: Mapping[str, Any]) -> dict[str, Any]:
    value = record.get("triage") if isinstance(record.get("triage"), Mapping) else {}
    return {"state": str(value.get("state") or "not_started"), "disposition": str(value.get("disposition") or ""), "private_note": str(value.get("private_note") or ""), "started_at": str(value.get("started_at") or ""), "completed_at": str(value.get("completed_at") or "")}


def build_evaluation_finding_triage(finding_id: str) -> dict[str, Any]:
    finding = load_evaluation_finding_private(finding_id); triage = _record(finding); note = triage["private_note"]
    stable = {"finding_id": str(finding.get("finding_id") or ""), "finding_revision": int(finding.get("revision") or 0), "triage_state": triage["state"], "triage_disposition": triage["disposition"], "triage_note_present": bool(note), "triage_note_digest": _digest(note) if note else "", "started_at": triage["started_at"], "completed_at": triage["completed_at"], "completion_ready": triage["state"] == "in_review" and triage["disposition"] in FINDING_TRIAGE_DISPOSITIONS}
    return {"ok": True, "type": "desktop_alpha_evaluation_finding_triage", "schema_version": FINDING_TRIAGE_SCHEMA_VERSION, **stable, "triage_digest": _digest(stable), "private_note_returned": False, "operator_confirmation_required": True, "optimistic_revision_required": True, "priority_assigned": False, "autonomous_prioritization": False, "automatic_task_created": False, "automatic_work_item_created": False, "patch_generated": False, "patch_reviewed": False, "patch_applied": False, "approval_granted": False, "rollback_authorized": False, "installation_performed": False, "promotion_performed": False, "release_recommendation_produced": False, "release_certified": False, "provider_invoked": False, "writes_state": False, "content_free": True, "redacted": True}


def _bounded_note(value: str) -> str:
    note = str(value or "").strip()
    if len(note) > MAX_TRIAGE_NOTE_CHARS: raise EvaluationFindingError(f"Triage note exceeds the {MAX_TRIAGE_NOTE_CHARS}-character limit.")
    return note


def start_evaluation_finding_triage(finding_id: str, *, note: str = "", expected_revision: int | None, operator_confirmed: bool) -> dict[str, Any]:
    private_note = _bounded_note(note)
    def apply(record: dict[str, Any]) -> None:
        triage = _record(record)
        if triage["state"] == "in_review": raise EvaluationFindingError("Finding triage is already in review.")
        from conversation_evaluation_finding import _now
        record["triage"] = {"state": "in_review", "disposition": triage["disposition"], "private_note": private_note, "started_at": _now(), "completed_at": ""}
        record["state"] = "under_review"
    mutate_evaluation_finding(finding_id, expected_revision=expected_revision, operator_confirmed=operator_confirmed, mutator=apply)
    return build_evaluation_finding_triage(finding_id)


def set_evaluation_finding_triage_disposition(finding_id: str, *, disposition: str, note: str | None = None, expected_revision: int | None, operator_confirmed: bool) -> dict[str, Any]:
    token = str(disposition or "").strip().lower()
    if token not in FINDING_TRIAGE_DISPOSITIONS: raise EvaluationFindingError("Unsupported finding triage disposition.")
    def apply(record: dict[str, Any]) -> None:
        triage = _record(record)
        if triage["state"] != "in_review": raise EvaluationFindingError("Only an in-progress finding triage may set a disposition.")
        triage["disposition"] = token
        if note is not None: triage["private_note"] = _bounded_note(note)
        record["triage"] = triage
    mutate_evaluation_finding(finding_id, expected_revision=expected_revision, operator_confirmed=operator_confirmed, mutator=apply)
    return build_evaluation_finding_triage(finding_id)


def complete_evaluation_finding_triage(finding_id: str, *, expected_revision: int | None, operator_confirmed: bool) -> dict[str, Any]:
    def apply(record: dict[str, Any]) -> None:
        triage = _record(record)
        if triage["state"] != "in_review": raise EvaluationFindingError("Only an in-progress finding triage may be completed.")
        if triage["disposition"] not in FINDING_TRIAGE_DISPOSITIONS: raise EvaluationFindingError("An explicit triage disposition is required before completion.")
        from conversation_evaluation_finding import _now
        triage["state"] = "completed"; triage["completed_at"] = _now(); record["triage"] = triage
    mutate_evaluation_finding(finding_id, expected_revision=expected_revision, operator_confirmed=operator_confirmed, mutator=apply)
    return build_evaluation_finding_triage(finding_id)


def reopen_evaluation_finding_triage(finding_id: str, *, expected_revision: int | None, operator_confirmed: bool) -> dict[str, Any]:
    def apply(record: dict[str, Any]) -> None:
        triage = _record(record)
        if triage["state"] != "completed": raise EvaluationFindingError("Only a completed finding triage may be reopened.")
        triage["state"] = "in_review"; triage["completed_at"] = ""; record["triage"] = triage; record["state"] = "under_review"
    mutate_evaluation_finding(finding_id, expected_revision=expected_revision, operator_confirmed=operator_confirmed, mutator=apply)
    return build_evaluation_finding_triage(finding_id)
