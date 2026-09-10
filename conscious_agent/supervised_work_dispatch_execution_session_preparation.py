from __future__ import annotations

"""Supervised work dispatch and bounded execution-session preparation.

v1225 converts one item from an accepted, current v1224 schedule into a
content-free prepared execution session. Preparation and operator review never
launch work, reuse authority, contact a provider, run tests, create a real
workspace, or modify a project. Path 3's mindful-execution requirements are
recorded as review obligations only.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from operator_governed_work_prioritization_scheduling import (
    _schedule_review_path,
    _valid as _valid_v1224,
    build_operator_governed_work_prioritization,
    load_operator_governed_work_schedule,
)
from unified_development_work_queue import build_unified_development_work_queue

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1225.8"
MAX_PREPARED_SESSIONS = 100
REVIEW_DECISIONS = ("accept", "reject", "defer", "cancel")
TERMINAL_REVIEW_DECISIONS = ("reject", "cancel")
PREPARABLE_QUEUE_STATES = ("active", "awaiting_approval", "resumable")

AUTHORITY_FLAGS = {
    "execution_session_prepared": True,
    "execution_session_launch_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "background_execution_authorized": False,
    "old_authority_reusable": False,
}

_SHOW = re.compile(r"^show prepared development execution sessions[.!?]*$", re.I)
_PREPARE = re.compile(
    r"^prepare development execution session for item (?P<item>work_[a-f0-9]{24}) "
    r"schedule (?P<schedule>[a-f0-9]{64})[.!?]*$", re.I,
)
_REVIEW = re.compile(
    r"^(?P<decision>accept|reject|defer|cancel) prepared development execution session "
    r"(?P<session>session_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$", re.I,
)


def _sessions_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "prepared_development_execution_sessions"


def _session_path(session_id: str, runtime_root=None) -> Path:
    return _sessions_root(runtime_root) / f"{session_id}.json"


def _session_snapshot_path(session_id: str, generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "prepared_development_execution_session_snapshots" / session_id / f"generation-{generation:06d}.json"


def _review_path(session_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "prepared_development_execution_session_reviews" / f"{session_id}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _store_root(runtime_root) / "locks" / "supervised-work-dispatch-session-preparation.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for prepared-session lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "prepared_session_is_planning_evidence_only": True,
        "accepted_schedule_preserved_as_authority_source": True,
        "fresh_launch_authorization_required": True,
        "goal_alignment_review_required": True,
        "uncertainty_review_required": True,
        "outcome_reflection_required": True,
        "runtime_records_external": True,
        "operator_review_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_created": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "cognition_written": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["supervised_work_dispatch_result_digest"] = _digest(row)
    return row


def _requirements() -> dict[str, bool]:
    return {
        "fresh_isolated_workspace_required": True,
        "provider_plan_review_required": True,
        "test_plan_review_required": True,
        "risk_review_required": True,
        "rollback_plan_review_required": True,
        "execution_budget_review_required": True,
        "goal_alignment_review_required": True,
        "uncertainty_review_required": True,
        "outcome_reflection_required": True,
        "fresh_launch_authorization_required": True,
    }


def _validate_session(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "prepared_execution_session_record_digest"):
        return False
    expected = _digest({
        "session_id": str(record.get("session_id") or ""),
        "generation": int(record.get("generation") or 0),
        "source_schedule_digest": str(record.get("source_schedule_digest") or ""),
        "source_schedule_slot_digest": str(record.get("source_schedule_slot_digest") or ""),
        "source_queue_digest": str(record.get("source_queue_digest") or ""),
        "queue_item_id": str(record.get("queue_item_id") or ""),
        "project_reference": str(record.get("project_reference") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "requirements_digest": str(record.get("requirements_digest") or ""),
    })
    return (
        str(record.get("session_digest") or "") == expected
        and str(record.get("session_id") or "").startswith("session_")
        and bool(record.get("queue_item_id"))
        and bool(record.get("project_reference"))
    )


def _load_schedule_review(schedule_digest: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_schedule_review_path(schedule_digest, runtime_root))
    if not row or not _valid_v1224(row, "operator_governed_work_schedule_review_record_digest"):
        return {}
    return row


def _current_accepted_schedule(expected_schedule_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    schedule = load_operator_governed_work_schedule(runtime_root=runtime_root)
    if not schedule:
        raise ValueError("schedule_missing_or_invalid")
    if str(schedule.get("schedule_digest") or "") != str(expected_schedule_digest or ""):
        raise ValueError("stale_schedule_digest")
    review = _load_schedule_review(expected_schedule_digest, runtime_root)
    if not review:
        raise ValueError("accepted_schedule_review_required")
    if str(review.get("decision") or "") != "accept":
        raise ValueError("schedule_not_accepted")
    current_priority = build_operator_governed_work_prioritization(runtime_root=runtime_root)
    if current_priority.get("ok") is not True:
        raise ValueError("current_prioritization_unavailable")
    if str(current_priority.get("prioritization_digest") or "") != str(schedule.get("source_prioritization_digest") or ""):
        raise ValueError("stale_schedule_prioritization")
    queue = build_unified_development_work_queue(runtime_root=runtime_root)
    if queue.get("ok") is not True:
        raise ValueError("current_queue_unavailable")
    if str(queue.get("queue_digest") or "") != str(schedule.get("source_queue_digest") or ""):
        raise ValueError("stale_schedule_queue")
    return schedule, review, queue


def _session_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _sessions_root(runtime_root)
    if not root.exists():
        return []
    rows=[]
    for path in sorted(root.glob("session_*.json"))[:MAX_PREPARED_SESSIONS + 1]:
        row = _read_json(path)
        if not row or not _validate_session(row) or path.stem != row.get("session_id"):
            raise ValueError("prepared_session_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_PREPARED_SESSIONS:
        raise ValueError("prepared_session_limit_exceeded")
    return rows


def prepare_development_execution_session(
    queue_item_id: str, *, expected_schedule_digest: str, exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            schedule, review, queue = _current_accepted_schedule(expected_schedule_digest, runtime_root)
            item_id = str(queue_item_id or "").lower()
            slot = next((dict(row) for row in schedule.get("slots") or [] if row.get("queue_item_id") == item_id), None)
            if not slot:
                raise ValueError("schedule_item_missing")
            queue_item = next((dict(row) for row in queue.get("items") or [] if row.get("queue_item_id") == item_id), None)
            if not queue_item:
                raise ValueError("queue_item_missing")
            if str(queue_item.get("state") or "") not in PREPARABLE_QUEUE_STATES:
                raise ValueError("queue_item_not_preparable")
            if bool(queue_item.get("duplicate_active_conflict")):
                raise ValueError("queue_item_conflict")
            if str(queue_item.get("project_reference") or "") != str(slot.get("project_reference") or ""):
                raise ValueError("schedule_project_binding_invalid")
            if slot.get("execution_authorized") is not False or slot.get("fresh_authority_required") is not True:
                raise ValueError("schedule_authority_boundary_invalid")
            requirements = _requirements()
            requirements_digest = _digest(requirements)
            seed = _digest({
                "source_schedule_digest": expected_schedule_digest,
                "source_schedule_slot_digest": str(slot.get("schedule_slot_digest") or ""),
                "queue_item_id": item_id,
                "project_reference": str(slot.get("project_reference") or ""),
            })
            session_id = "session_" + seed[:24]
            path = _session_path(session_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _validate_session(existing):
                    raise ValueError("prepared_session_tampered_or_malformed")
                return {**existing, "operation_status": "resumed"}
            for other in _session_rows(runtime_root):
                if (
                    str(other.get("project_reference") or "") == str(slot.get("project_reference") or "")
                    and str(other.get("session_id") or "") != session_id
                ):
                    other_review = _read_json(_review_path(str(other.get("session_id") or ""), runtime_root))
                    disposition = str((other_review or {}).get("decision") or "")
                    if disposition not in TERMINAL_REVIEW_DECISIONS:
                        raise ValueError("conflicting_prepared_session_for_project")
            generation = 1
            session_digest = _digest({
                "session_id": session_id,
                "generation": generation,
                "source_schedule_digest": expected_schedule_digest,
                "source_schedule_slot_digest": str(slot.get("schedule_slot_digest") or ""),
                "source_queue_digest": str(schedule.get("source_queue_digest") or ""),
                "queue_item_id": item_id,
                "project_reference": str(slot.get("project_reference") or ""),
                "proposal_id": str(queue_item.get("proposal_id") or ""),
                "requirements_digest": requirements_digest,
            })
            row = {
                "ok": True,
                "status": "prepared_development_execution_session_ready",
                "session_id": session_id,
                "session_digest": session_digest,
                "generation": generation,
                "source_schedule_generation": int(schedule.get("generation") or 0),
                "source_schedule_digest": expected_schedule_digest,
                "source_schedule_review_digest": str(review.get("operator_governed_work_schedule_review_record_digest") or ""),
                "source_schedule_slot": int(slot.get("slot") or 0),
                "source_schedule_slot_digest": str(slot.get("schedule_slot_digest") or ""),
                "source_prioritization_digest": str(schedule.get("source_prioritization_digest") or ""),
                "source_queue_digest": str(schedule.get("source_queue_digest") or ""),
                "queue_item_id": item_id,
                "project_reference": str(slot.get("project_reference") or ""),
                "proposal_id": str(queue_item.get("proposal_id") or ""),
                "current_stage": str(queue_item.get("current_stage") or ""),
                "safe_next_step": str(queue_item.get("safe_next_step") or ""),
                "priority_rank": int(slot.get("priority_rank") or 0),
                "priority_level": str(slot.get("priority_level") or "normal"),
                "dependency_item_ids": list(slot.get("dependency_item_ids") or []),
                "requirements": requirements,
                "requirements_digest": requirements_digest,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "accept_phrase": f"Accept prepared development execution session {session_id} digest {session_digest}.",
                "reject_phrase": f"Reject prepared development execution session {session_id} digest {session_digest}.",
                "defer_phrase": f"Defer prepared development execution session {session_id} digest {session_digest}.",
                "cancel_phrase": f"Cancel prepared development execution session {session_id} digest {session_digest}.",
                **_base(),
            }
            row = _sealed(row, "prepared_execution_session_record_digest")
            _atomic_json(_session_snapshot_path(session_id, generation, runtime_root), row)
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("prepared_development_execution_session_blocked", str(exc))


def load_prepared_development_execution_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_session_path(str(session_id or "").lower(), runtime_root))
    return row if row and _validate_session(row) else {}


def inspect_prepared_development_execution_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    try:
        row = load_prepared_development_execution_session(session_id, runtime_root=runtime_root)
        if not row:
            raise ValueError("prepared_session_missing_or_invalid")
        schedule, _, queue = _current_accepted_schedule(str(row.get("source_schedule_digest") or ""), runtime_root)
        slot = next((x for x in schedule.get("slots") or [] if x.get("queue_item_id") == row.get("queue_item_id")), None)
        item = next((x for x in queue.get("items") or [] if x.get("queue_item_id") == row.get("queue_item_id")), None)
        if not slot or not item:
            raise ValueError("prepared_session_source_missing")
        if str(slot.get("schedule_slot_digest") or "") != str(row.get("source_schedule_slot_digest") or ""):
            raise ValueError("prepared_session_slot_stale")
        return row
    except (OSError, ValueError) as exc:
        return _failure("prepared_development_execution_session_expired", str(exc))


def record_prepared_execution_session_review(
    decision: str, *, session_id: str, expected_session_digest: str, exact_phrase: str = "", runtime_root=None,
) -> dict[str, Any]:
    decision = str(decision or "").lower()
    if decision not in REVIEW_DECISIONS:
        return _failure("prepared_execution_session_review_invalid", "unsupported_decision")
    try:
        with _lock(runtime_root):
            session = inspect_prepared_development_execution_session(session_id, runtime_root=runtime_root)
            if session.get("ok") is not True:
                raise ValueError(str(session.get("reason") or "prepared_session_stale"))
            if str(session.get("session_digest") or "") != str(expected_session_digest or ""):
                raise ValueError("stale_session_digest")
            path = _review_path(str(session.get("session_id") or ""), runtime_root)
            existing = _read_json(path)
            if existing:
                if not _valid(existing, "prepared_execution_session_review_record_digest"):
                    raise ValueError("prepared_session_review_tampered")
                if existing.get("decision") == decision:
                    return {**existing, "operation_status": "replayed"}
                raise ValueError("conflicting_prepared_session_review")
            status = {
                "accept": "prepared_development_execution_session_accepted",
                "reject": "prepared_development_execution_session_rejected",
                "defer": "prepared_development_execution_session_deferred",
                "cancel": "prepared_development_execution_session_cancelled",
            }[decision]
            row = {
                "ok": True,
                "status": status,
                "decision": decision,
                "session_id": str(session.get("session_id") or ""),
                "source_session_digest": str(session.get("session_digest") or ""),
                "source_schedule_digest": str(session.get("source_schedule_digest") or ""),
                "queue_item_id": str(session.get("queue_item_id") or ""),
                "project_reference": str(session.get("project_reference") or ""),
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "launch_readiness_established": decision == "accept",
                "fresh_launch_authorization_required": True,
                "execution_session_launch_authorized": False,
                **_base(),
            }
            row = _sealed(row, "prepared_execution_session_review_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("prepared_execution_session_review_blocked", str(exc))


def _public_session(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    allowed = {
        "ok", "status", "session_id", "session_digest", "generation", "source_schedule_generation",
        "source_schedule_digest", "source_schedule_slot", "source_schedule_slot_digest",
        "source_prioritization_digest", "source_queue_digest", "queue_item_id", "project_reference",
        "proposal_id", "current_stage", "safe_next_step", "priority_rank", "priority_level",
        "dependency_item_ids", "requirements", "requirements_digest", "accept_phrase", "reject_phrase",
        "defer_phrase", "cancel_phrase", "operation_status",
    }
    row = {key: record.get(key) for key in allowed if key in record}
    row.update(_base())
    row["public_prepared_execution_session_digest"] = _digest(row)
    return row


def public_prepared_development_execution_sessions(*, runtime_root=None) -> dict[str, Any]:
    try:
        sessions = [_public_session(row) for row in _session_rows(runtime_root)]
        reviews=[]
        for row in sessions:
            review = _read_json(_review_path(str(row.get("session_id") or ""), runtime_root))
            reviews.append({
                "session_id": str(row.get("session_id") or ""),
                "decision": str((review or {}).get("decision") or "pending"),
                "launch_readiness_established": bool((review or {}).get("launch_readiness_established")),
                "execution_session_launch_authorized": False,
            })
        result = {
            "ok": True,
            "status": "prepared_development_execution_session_list_ready",
            "session_count": len(sessions),
            "sessions": sessions,
            "reviews": reviews,
            **_base(),
        }
        result["public_prepared_execution_session_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("prepared_development_execution_session_list_blocked", str(exc))


def prepared_execution_session_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if record.get("ok") is not True:
        return f"Execution-session preparation was blocked: {record.get('reason', status or 'invalid evidence')}."
    if status == "prepared_development_execution_session_ready":
        return (
            f"Prepared execution session {record.get('session_id')} for queue item {record.get('queue_item_id')}. "
            "It requires operator review and fresh launch authorization; no work was launched."
        )
    if status == "prepared_development_execution_session_list_ready":
        return f"There are {record.get('session_count', 0)} prepared execution sessions. None is launch authority."
    return f"The prepared execution-session control recorded: {status}. No development work was launched."


def process_supervised_work_dispatch_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE.fullmatch(text)
    review = _REVIEW.fullmatch(text)
    if _SHOW.fullmatch(text):
        result = public_prepared_development_execution_sessions(runtime_root=runtime_root)
    elif prepare:
        result = _public_session(prepare_development_execution_session(
            prepare.group("item").lower(),
            expected_schedule_digest=prepare.group("schedule").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif review:
        result = record_prepared_execution_session_review(
            review.group("decision").lower(),
            session_id=review.group("session").lower(),
            expected_session_digest=review.group("digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        )
        result.update(_base())
    else:
        return {"active": False, "event": "inactive"}
    return {
        "active": True,
        "event": str(result.get("status") or "prepared_development_execution_session_blocked"),
        "supervised_work_dispatch": result,
        "conversation_response": prepared_execution_session_response(result),
    }
