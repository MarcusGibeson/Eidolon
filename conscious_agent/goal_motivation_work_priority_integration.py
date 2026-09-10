from __future__ import annotations

"""Goal, motivation, and work-priority integration.

v1236 binds one exact operator-governed work-priority item to a sanitized,
content-free snapshot of established goal and motivation state and, optionally,
an exact accepted v1235 development lesson. The result is append-only advisory
evidence for operator review. It cannot change a goal, motivation, queue,
priority, schedule, project, cognition, or execution authority.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from operator_governed_work_prioritization_scheduling import (
    PRIORITY_LEVELS,
    load_operator_governed_work_prioritization,
)
from persistent_motivation import MotivationStore
from evidence_backed_development_outcome_lessons import _load_review as _load_lesson_review

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1236.8"
MAX_ASSESSMENTS = 200
MAX_REVIEWS = 300
GOAL_KINDS = {"enduring_goal", "temporary_goal"}
REVIEW_DISPOSITIONS = {"accept_alignment", "hold", "reject", "request_changes", "propose_priority_change"}
ALIGNMENT_STATES = {
    "strongly_aligned", "aligned", "mixed", "weakly_aligned", "conflicted", "insufficient_evidence"
}
RECOMMENDATION_CODES = {
    "raise_priority", "maintain_priority", "lower_priority", "defer_for_goal_conflict",
    "clarify_goal_alignment", "preserve_operator_priority", "apply_verified_lesson",
    "preserve_current_order", "no_priority_change",
}
PRIORITY_ORDER = ("low", "normal", "high", "critical")

AUTHORITY_FLAGS = {
    "goal_motivation_priority_assessment_authorized": True,
    "goal_motivation_priority_review_authorized": True,
    "goal_state_mutation_authorized": False,
    "motivation_state_mutation_authorized": False,
    "priority_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "project_mutation_authorized": False,
    "requirement_mutation_authorized": False,
    "lesson_mutation_authorized": False,
    "cognition_write_authorized": False,
    "integration_is_execution_authority": False,
    "integration_is_priority_authority": False,
    "execution_session_launch_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "resume_authorized": False,
    "pause_authorized": False,
    "cancel_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE = re.compile(
    r"^prepare goal motivation work priority integration for item (?P<item>work_[a-f0-9]{24}) "
    r"prioritization (?P<priority>[a-f0-9]{64})"
    r"(?: lesson review (?P<lesson>development_lesson_review_[a-f0-9]{24}) digest (?P<lesson_digest>[a-f0-9]{64}))?[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review goal motivation work priority integration (?P<decision>accept_alignment|hold|reject|request_changes) "
    r"for assessment (?P<assessment>goal_priority_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_PROPOSE = re.compile(
    r"^review goal motivation work priority integration propose_priority_change for assessment "
    r"(?P<assessment>goal_priority_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64}) "
    r"to (?P<level>low|normal|high|critical)[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show goal motivation work priority integrations[.!?]*$", re.I)
_SHOW_ONE = re.compile(
    r"^show goal motivation work priority integration (?P<assessment>goal_priority_assessment_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_SHOW_REVIEWS = re.compile(r"^show goal motivation work priority integration reviews[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _assessment_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "goal_motivation_work_priority_assessments"


def _assessment_path(assessment_id: str, runtime_root=None) -> Path:
    return _assessment_root(runtime_root) / f"{str(assessment_id or '').lower()}.json"


def _assessment_index_path(queue_item_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "goal_motivation_work_priority_assessment_indexes" / f"{str(queue_item_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "goal_motivation_work_priority_reviews"


def _review_path(assessment_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(assessment_id or '').lower()}.json"


def _cognition_root(runtime_root=None) -> Path | None:
    if runtime_root is None:
        return None
    return Path(runtime_root).expanduser().resolve() / "cognition"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "goal-motivation-work-priority-integration.lock"
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
                raise TimeoutError("Timed out waiting for goal/motivation priority integration lock")
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
        "runtime_records_external": True,
        "project_scoped": True,
        "operator_review_required": True,
        "goal_and_motivation_state_read_only": True,
        "priority_recommendation_advisory_only": True,
        "historical_assessment_immutable": True,
        "historical_review_immutable": True,
        "fresh_separate_priority_authority_required": True,
        "fresh_separate_execution_authority_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "goals_modified": False,
        "motivations_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "requirements_modified": False,
        "lessons_modified": False,
        "cognition_written": False,
        "source_modified": False,
        "hidden_retry_created": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "goal_summary_exposed": False,
        "motivation_summary_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["goal_motivation_work_priority_result_digest"] = _digest(row)
    return row


def _priority_basis(queue_item_id: str, expected_prioritization_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    prioritization = load_operator_governed_work_prioritization(runtime_root=runtime_root)
    if not prioritization or prioritization.get("prioritization_digest") != str(expected_prioritization_digest or "").lower():
        raise ValueError("stale_or_invalid_prioritization")
    item = next((dict(row) for row in prioritization.get("items") or [] if row.get("queue_item_id") == str(queue_item_id or "").lower()), None)
    if not item:
        raise ValueError("priority_item_missing")
    return prioritization, item


def _lesson_basis(review_id: str, review_digest: str, project_reference: str, runtime_root=None) -> dict[str, Any]:
    if not review_id and not review_digest:
        return {}
    if not review_id or not review_digest:
        raise ValueError("incomplete_lesson_review_reference")
    review = _load_lesson_review(str(review_id or "").lower(), runtime_root)
    if not review.get("ok") or review.get("review_digest") != str(review_digest or "").lower():
        raise ValueError("stale_or_invalid_lesson_review")
    if review.get("project_reference") != project_reference:
        raise ValueError("lesson_review_project_mismatch")
    if review.get("lesson_active") is not True or review.get("disposition") not in {"accept", "revise"}:
        raise ValueError("lesson_review_not_active")
    return review


def _sanitized_motivation_snapshot(project_reference: str, runtime_root=None) -> dict[str, Any]:
    store = MotivationStore(_cognition_root(runtime_root)) if runtime_root is not None else MotivationStore()
    state = store.snapshot()
    rows: list[dict[str, Any]] = []
    ignored_other_project = 0
    for raw in state.get("motivations") or []:
        if raw.get("lifecycle_state") != "active":
            continue
        scope = dict(raw.get("scope") or {})
        project_id = str(scope.get("project_id") or "")
        if project_id and project_id != project_reference:
            ignored_other_project += 1
            continue
        row = {
            "motivation_id": str(raw.get("motivation_id") or ""),
            "semantic_key": str(raw.get("semantic_key") or ""),
            "kind": str(raw.get("kind") or ""),
            "cognitive_state": str(raw.get("cognitive_state") or ""),
            "lifecycle_state": "active",
            "valence": round(float(raw.get("valence") or 0.0), 4),
            "urgency": round(float(raw.get("urgency") or 0.0), 4),
            "confidence": round(float(raw.get("confidence") or 0.0), 4),
            "project_scope_match": bool(project_id == project_reference),
            "global_scope": not bool(project_id),
            "relationship_types": sorted({str(item.get("type") or "") for item in raw.get("relationships") or [] if item.get("type")}),
            "authorizes_action": bool((raw.get("authority") or {}).get("authorizes_action")),
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["kind"], row["motivation_id"], row["semantic_key"]))
    goals = [row for row in rows if row.get("kind") in GOAL_KINDS]
    motivations = [row for row in rows if row.get("kind") not in GOAL_KINDS]
    basis = {
        "motivation_store_revision": int(state.get("revision") or 0),
        "project_reference": project_reference,
        "goal_rows": goals,
        "motivation_rows": motivations,
        "ignored_other_project_count": ignored_other_project,
    }
    return {
        **basis,
        "goal_count": len(goals),
        "motivation_count": len(motivations),
        "goal_snapshot_digest": _digest(goals),
        "motivation_snapshot_digest": _digest(motivations),
        "combined_snapshot_digest": _digest(basis),
        "raw_summary_exposed": False,
        "raw_origin_reference_exposed": False,
    }


def _weighted_signal(row: Mapping[str, Any]) -> float:
    scope_weight = 1.0 if row.get("project_scope_match") else 0.75
    return round(float(row.get("valence") or 0.0) * float(row.get("urgency") or 0.0) * float(row.get("confidence") or 0.0) * scope_weight, 6)


def _mean_signal(rows: Iterable[Mapping[str, Any]]) -> float:
    values = [_weighted_signal(row) for row in rows]
    if not values:
        return 0.0
    return round(max(-1.0, min(1.0, sum(values) / len(values))), 4)


def _next_priority(current: str, direction: int) -> str:
    index = PRIORITY_ORDER.index(current) if current in PRIORITY_ORDER else 1
    return PRIORITY_ORDER[max(0, min(len(PRIORITY_ORDER) - 1, index + direction))]


def _derive(snapshot: Mapping[str, Any], priority_item: Mapping[str, Any], lesson: Mapping[str, Any]) -> dict[str, Any]:
    goals = list(snapshot.get("goal_rows") or [])
    motivations = list(snapshot.get("motivation_rows") or [])
    goal_score = _mean_signal(goals)
    motivation_score = _mean_signal(motivations)
    combined = round((goal_score * 0.65) + (motivation_score * 0.35), 4)
    lesson_codes = set(lesson.get("lesson_codes") or [])
    lesson_adjustment = 0.0
    if "preserve_goal_alignment" in lesson_codes:
        lesson_adjustment += 0.15
    if "realign_with_project_goal" in lesson_codes:
        lesson_adjustment -= 0.25
    if "constrain_out_of_scope_work" in lesson_codes:
        lesson_adjustment -= 0.15
    if "retain_verified_approach" in lesson_codes:
        lesson_adjustment += 0.05
    adjusted = round(max(-1.0, min(1.0, combined + lesson_adjustment)), 4)
    positive = any(_weighted_signal(row) > 0.04 for row in goals + motivations)
    negative = any(_weighted_signal(row) < -0.04 for row in goals + motivations)
    if not goals and not motivations:
        state = "insufficient_evidence"
    elif adjusted <= -0.25:
        state = "conflicted"
    elif positive and negative:
        state = "mixed"
    elif adjusted >= 0.55:
        state = "strongly_aligned"
    elif adjusted >= 0.15:
        state = "aligned"
    else:
        state = "weakly_aligned"
    confidences = [float(row.get("confidence") or 0.0) for row in goals + motivations]
    average_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    if state in {"conflicted", "insufficient_evidence"} or average_confidence < 0.45:
        confidence = "low"
    elif state == "mixed" or average_confidence < 0.75:
        confidence = "medium"
    else:
        confidence = "high"
    max_urgency = max((float(row.get("urgency") or 0.0) * float(row.get("confidence") or 0.0) for row in goals + motivations), default=0.0)
    current = str(priority_item.get("priority_level") or "normal")
    pinned = bool(priority_item.get("pinned"))
    codes: list[str] = []
    uncertainty: list[str] = []
    target = current
    if pinned:
        codes.extend(["preserve_operator_priority", "maintain_priority"])
    elif state == "conflicted":
        codes.extend(["lower_priority", "defer_for_goal_conflict"])
        target = _next_priority(current, -1)
    elif state == "strongly_aligned" and max_urgency >= 0.70 and current in {"low", "normal"}:
        codes.append("raise_priority")
        target = _next_priority(current, 1)
    elif state in {"aligned", "strongly_aligned"}:
        codes.extend(["maintain_priority", "preserve_current_order"])
    elif state == "mixed":
        codes.extend(["maintain_priority", "clarify_goal_alignment"])
        uncertainty.append("supporting_and_conflicting_signals")
    elif state == "insufficient_evidence":
        codes.extend(["no_priority_change", "clarify_goal_alignment"])
        uncertainty.append("goal_and_motivation_evidence_missing")
    else:
        codes.extend(["no_priority_change", "clarify_goal_alignment"])
        uncertainty.append("alignment_signal_weak")
    if lesson:
        codes.append("apply_verified_lesson")
    if not priority_item.get("schedule_eligible"):
        codes.append("no_priority_change")
        target = current
        uncertainty.append("priority_item_not_schedule_eligible")
    codes = list(dict.fromkeys(codes))
    return {
        "alignment_state": state,
        "alignment_confidence": confidence,
        "goal_alignment_score": goal_score,
        "motivation_alignment_score": motivation_score,
        "lesson_alignment_adjustment": round(lesson_adjustment, 4),
        "combined_alignment_score": adjusted,
        "maximum_weighted_urgency": round(max_urgency, 4),
        "recommendation_codes": codes,
        "uncertainty_codes": sorted(set(uncertainty)),
        "current_priority_level": current,
        "recommended_priority_level": target,
        "priority_change_recommended": target != current,
    }


def _load_assessment(assessment_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_assessment_path(assessment_id, runtime_root))
    if not row or not _valid(row, "goal_motivation_work_priority_assessment_record_digest"):
        return _failure("goal_motivation_work_priority_assessment_integrity_blocked")
    return row


def _load_review(assessment_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_review_path(assessment_id, runtime_root))
    if not row or not _valid(row, "goal_motivation_work_priority_review_record_digest"):
        return _failure("goal_motivation_work_priority_review_integrity_blocked")
    return row


def _basis(queue_item_id: str, prioritization_digest: str, lesson_review_id: str, lesson_review_digest: str, runtime_root=None):
    prioritization, item = _priority_basis(queue_item_id, prioritization_digest, runtime_root)
    project_reference = str(item.get("project_reference") or "")
    snapshot = _sanitized_motivation_snapshot(project_reference, runtime_root)
    lesson = _lesson_basis(lesson_review_id, lesson_review_digest, project_reference, runtime_root)
    basis = {
        "queue_item_id": str(item.get("queue_item_id") or ""),
        "project_reference": project_reference,
        "prioritization_digest": str(prioritization.get("prioritization_digest") or ""),
        "priority_item_digest": str(item.get("priority_item_digest") or ""),
        "goal_snapshot_digest": snapshot.get("goal_snapshot_digest"),
        "motivation_snapshot_digest": snapshot.get("motivation_snapshot_digest"),
        "combined_snapshot_digest": snapshot.get("combined_snapshot_digest"),
        "lesson_review_id": str(lesson.get("review_id") or ""),
        "lesson_review_digest": str(lesson.get("review_digest") or ""),
    }
    return prioritization, item, snapshot, lesson, basis


def prepare_goal_motivation_work_priority_integration(
    queue_item_id: str,
    *,
    expected_prioritization_digest: str,
    lesson_review_id: str = "",
    expected_lesson_review_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            prioritization, item, snapshot, lesson, basis = _basis(
                str(queue_item_id or "").lower(), str(expected_prioritization_digest or "").lower(),
                str(lesson_review_id or "").lower(), str(expected_lesson_review_digest or "").lower(), runtime_root,
            )
            basis_digest = _digest(basis)
            index_path = _assessment_index_path(str(queue_item_id or "").lower(), runtime_root)
            index = _read_json(index_path)
            generation = 1
            previous_assessment_digest = ""
            if index:
                if not _valid(index, "goal_motivation_work_priority_assessment_index_record_digest"):
                    return _failure("goal_motivation_work_priority_assessment_index_integrity_blocked")
                existing = _load_assessment(str(index.get("assessment_id") or ""), runtime_root)
                if not existing.get("ok"):
                    return _failure("goal_motivation_work_priority_assessment_history_integrity_blocked")
                if existing.get("basis_digest") == basis_digest:
                    return {**existing, "operation_status": "replayed"}
                generation = int(existing.get("generation") or 0) + 1
                previous_assessment_digest = str(existing.get("assessment_digest") or "")
            derived = _derive(snapshot, item, lesson)
            identity = {
                "generation": generation,
                "previous_assessment_digest": previous_assessment_digest,
                "basis_digest": basis_digest,
                "derived": derived,
            }
            assessment_id = f"goal_priority_assessment_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "goal_motivation_work_priority_integration_ready_for_operator_review",
                "assessment_id": assessment_id,
                "assessment_digest": _digest(identity),
                "generation": generation,
                "previous_assessment_digest": previous_assessment_digest,
                "basis_digest": basis_digest,
                "queue_item_id": item.get("queue_item_id"),
                "project_reference": item.get("project_reference"),
                "prioritization_generation": int(prioritization.get("generation") or 0),
                "prioritization_digest": prioritization.get("prioritization_digest"),
                "priority_item_digest": item.get("priority_item_digest"),
                "priority_rank": int(item.get("rank") or 0),
                "priority_pinned": bool(item.get("pinned")),
                "schedule_eligible": bool(item.get("schedule_eligible")),
                "goal_snapshot_digest": snapshot.get("goal_snapshot_digest"),
                "motivation_snapshot_digest": snapshot.get("motivation_snapshot_digest"),
                "combined_snapshot_digest": snapshot.get("combined_snapshot_digest"),
                "motivation_store_revision": int(snapshot.get("motivation_store_revision") or 0),
                "goal_count": int(snapshot.get("goal_count") or 0),
                "motivation_count": int(snapshot.get("motivation_count") or 0),
                "ignored_other_project_count": int(snapshot.get("ignored_other_project_count") or 0),
                "lesson_review_id": str(lesson.get("review_id") or ""),
                "lesson_review_digest": str(lesson.get("review_digest") or ""),
                "lesson_codes": list(lesson.get("lesson_codes") or []),
                "lesson_evidence_applied": bool(lesson),
                **derived,
                "operator_review_phrase": f"Review goal motivation work priority integration accept_alignment for assessment {assessment_id} digest {_digest(identity)}.",
                "priority_change_phrase": f"Review goal motivation work priority integration propose_priority_change for assessment {assessment_id} digest {_digest(identity)} to {derived['recommended_priority_level']}.",
                "priority_change_proposal_only": True,
                **_base(),
            }
            row = _sealed(row, "goal_motivation_work_priority_assessment_record_digest")
            _atomic_json(_assessment_path(assessment_id, runtime_root), row)
            index_row = _sealed({
                "assessment_id": assessment_id,
                "assessment_digest": row["assessment_digest"],
                "generation": generation,
                "basis_digest": basis_digest,
                "queue_item_id": row["queue_item_id"],
                "project_reference": row["project_reference"],
            }, "goal_motivation_work_priority_assessment_index_record_digest")
            _atomic_json(index_path, index_row)
            return {**row, "operation_status": "created" if generation == 1 else "refreshed"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("goal_motivation_work_priority_integration_blocked", str(exc))


def review_goal_motivation_work_priority_integration(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    proposed_priority_level: str = "",
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    disposition = str(disposition or "").lower()
    proposed_priority_level = str(proposed_priority_level or "").lower()
    if disposition not in REVIEW_DISPOSITIONS:
        return _failure("goal_motivation_work_priority_review_invalid", "unsupported_disposition")
    if disposition == "propose_priority_change" and proposed_priority_level not in PRIORITY_LEVELS:
        return _failure("goal_motivation_work_priority_review_invalid", "priority_level_required")
    try:
        with _lock(runtime_root):
            assessment = _load_assessment(str(assessment_id or "").lower(), runtime_root)
            if not assessment.get("ok") or assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
                raise ValueError("stale_or_invalid_assessment")
            _, _, snapshot, lesson, basis = _basis(
                assessment["queue_item_id"], assessment["prioritization_digest"],
                assessment.get("lesson_review_id", ""), assessment.get("lesson_review_digest", ""), runtime_root,
            )
            if _digest(basis) != assessment.get("basis_digest"):
                raise ValueError("stale_goal_motivation_priority_or_lesson_state")
            if snapshot.get("combined_snapshot_digest") != assessment.get("combined_snapshot_digest"):
                raise ValueError("stale_goal_or_motivation_snapshot")
            if str(lesson.get("review_digest") or "") != str(assessment.get("lesson_review_digest") or ""):
                raise ValueError("stale_lesson_review")
            path = _review_path(assessment["assessment_id"], runtime_root)
            existing = _read_json(path)
            if existing:
                if not _valid(existing, "goal_motivation_work_priority_review_record_digest"):
                    raise ValueError("review_record_tampered")
                if existing.get("disposition") == disposition and existing.get("proposed_priority_level", "") == proposed_priority_level:
                    return {**existing, "operation_status": "replayed"}
                raise ValueError("conflicting_assessment_review")
            if disposition == "propose_priority_change" and proposed_priority_level == assessment.get("current_priority_level"):
                raise ValueError("proposed_priority_must_change")
            identity = {
                "assessment_digest": assessment["assessment_digest"],
                "disposition": disposition,
                "proposed_priority_level": proposed_priority_level,
            }
            review_id = f"goal_priority_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "goal_motivation_work_priority_review_recorded",
                "review_id": review_id,
                "review_digest": _digest(identity),
                "assessment_id": assessment["assessment_id"],
                "assessment_digest": assessment["assessment_digest"],
                "queue_item_id": assessment["queue_item_id"],
                "project_reference": assessment["project_reference"],
                "prioritization_digest": assessment["prioritization_digest"],
                "basis_digest": assessment["basis_digest"],
                "disposition": disposition,
                "alignment_state": assessment["alignment_state"],
                "alignment_confidence": assessment["alignment_confidence"],
                "current_priority_level": assessment["current_priority_level"],
                "recommended_priority_level": assessment["recommended_priority_level"],
                "proposed_priority_level": proposed_priority_level,
                "alignment_interpretation_accepted": disposition == "accept_alignment",
                "priority_change_proposal_recorded": disposition == "propose_priority_change",
                "priority_changed": False,
                "operator_follow_up_required": disposition in {"hold", "request_changes", "propose_priority_change"},
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row = _sealed(row, "goal_motivation_work_priority_review_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("goal_motivation_work_priority_review_blocked", str(exc))


def _public_assessment(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "assessment_id", "assessment_digest", "generation", "previous_assessment_digest",
        "queue_item_id", "project_reference", "prioritization_generation", "prioritization_digest",
        "priority_item_digest", "priority_rank", "priority_pinned", "schedule_eligible",
        "goal_snapshot_digest", "motivation_snapshot_digest", "combined_snapshot_digest",
        "motivation_store_revision", "goal_count", "motivation_count", "ignored_other_project_count",
        "lesson_review_id", "lesson_review_digest", "lesson_codes", "lesson_evidence_applied",
        "alignment_state", "alignment_confidence", "goal_alignment_score", "motivation_alignment_score",
        "lesson_alignment_adjustment", "combined_alignment_score", "maximum_weighted_urgency",
        "recommendation_codes", "uncertainty_codes", "current_priority_level", "recommended_priority_level",
        "priority_change_recommended", "priority_change_proposal_only", "operator_review_phrase",
        "priority_change_phrase", "content_free", "project_scoped", "goal_and_motivation_state_read_only",
        "priority_recommendation_advisory_only", "goal_state_mutation_authorized",
        "motivation_state_mutation_authorized", "priority_mutation_authorized", "queue_mutation_authorized",
        "schedule_mutation_authorized", "cognition_write_authorized", "integration_is_execution_authority",
        "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "review_id", "review_digest", "assessment_id", "assessment_digest",
        "queue_item_id", "project_reference", "prioritization_digest", "disposition", "alignment_state",
        "alignment_confidence", "current_priority_level", "recommended_priority_level", "proposed_priority_level",
        "alignment_interpretation_accepted", "priority_change_proposal_recorded", "priority_changed",
        "operator_follow_up_required", "content_free", "project_scoped", "goal_state_mutation_authorized",
        "motivation_state_mutation_authorized", "priority_mutation_authorized", "queue_mutation_authorized",
        "schedule_mutation_authorized", "cognition_write_authorized", "integration_is_execution_authority",
        "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def inspect_goal_motivation_work_priority_integration(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load_assessment(str(assessment_id or "").lower(), runtime_root)
    return _public_assessment(row) if row.get("ok") else row


def public_goal_motivation_work_priority_integrations(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _assessment_root(runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_ASSESSMENTS:]:
            row = _read_json(path)
            if row and _valid(row, "goal_motivation_work_priority_assessment_record_digest"):
                rows.append(_public_assessment(row))
    return {"ok": True, "status": "goal_motivation_work_priority_integration_list_ready", "assessment_count": len(rows), "assessments": rows, **_base()}


def public_goal_motivation_work_priority_integration_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_REVIEWS:]:
            row = _read_json(path)
            if row and _valid(row, "goal_motivation_work_priority_review_record_digest"):
                rows.append(_public_review(row))
    return {"ok": True, "status": "goal_motivation_work_priority_integration_review_list_ready", "review_count": len(rows), "reviews": rows, **_base()}


def goal_motivation_work_priority_integration_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Goal, motivation, and work-priority integration was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "ready_for_operator_review" in status:
        return (
            f"Prepared goal and motivation alignment assessment {row.get('assessment_id')} for {row.get('queue_item_id')}. "
            f"Alignment is {row.get('alignment_state')} with {row.get('alignment_confidence')} confidence. "
            "The recommendation is advisory and grants no goal, motivation, priority, queue, schedule, cognition, or execution authority."
        )
    if "review_recorded" in status:
        return (
            f"Recorded goal and motivation priority review {row.get('disposition')}. "
            "No priority, queue, schedule, goal, motivation, project, cognition, launch, or resume change occurred."
        )
    return "Goal, motivation, and work-priority integration records are ready for inspection."


def process_goal_motivation_work_priority_integration_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _PREPARE.fullmatch(text)
    if match:
        row = prepare_goal_motivation_work_priority_integration(
            match.group("item"), expected_prioritization_digest=match.group("priority"),
            lesson_review_id=match.group("lesson") or "",
            expected_lesson_review_digest=match.group("lesson_digest") or "",
            runtime_root=runtime_root,
        )
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    match = _PROPOSE.fullmatch(text)
    if match:
        row = review_goal_motivation_work_priority_integration(
            match.group("assessment"), expected_assessment_digest=match.group("digest"),
            disposition="propose_priority_change", proposed_priority_level=match.group("level"),
            exact_phrase=text, runtime_root=runtime_root,
        )
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    match = _REVIEW.fullmatch(text)
    if match:
        row = review_goal_motivation_work_priority_integration(
            match.group("assessment"), expected_assessment_digest=match.group("digest"),
            disposition=match.group("decision"), exact_phrase=text, runtime_root=runtime_root,
        )
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    if _SHOW_ALL.fullmatch(text):
        row = public_goal_motivation_work_priority_integrations(runtime_root=runtime_root)
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    match = _SHOW_ONE.fullmatch(text)
    if match:
        row = inspect_goal_motivation_work_priority_integration(match.group("assessment"), runtime_root=runtime_root)
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    if _SHOW_REVIEWS.fullmatch(text):
        row = public_goal_motivation_work_priority_integration_reviews(runtime_root=runtime_root)
        return {"active": True, "response": goal_motivation_work_priority_integration_response(row), "goal_motivation_work_priority_integration": row}
    return {"active": False}


def build_goal_motivation_work_priority_integration_contract() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "goal_motivation_work_priority_integration_contract_ready",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Goal, Motivation, and Work-Priority Integration",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "exact_operator_governed_priority_item_binding": True,
        "sanitized_goal_and_motivation_snapshot_binding": True,
        "optional_exact_active_lesson_review_binding": True,
        "deterministic_alignment_assessment": True,
        "goal_motivation_priority_conflict_visible": True,
        "operator_priority_and_pinning_preserved": True,
        "priority_change_is_proposal_only": True,
        "append_only_refresh_on_state_change": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "accepted_alignment_does_not_change_priority": True,
        "accepted_alignment_does_not_write_cognition": True,
        "accepted_alignment_does_not_grant_execution_authority": True,
        "alignment_states": sorted(ALIGNMENT_STATES),
        "recommendation_codes": sorted(RECOMMENDATION_CODES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        **_base(),
    }
