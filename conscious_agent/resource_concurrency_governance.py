from __future__ import annotations

"""Bounded resource and concurrency governance for supervised execution.

v1233 evaluates sealed, content-free resource claims for an active or paused
bounded development execution session after exact v1232 dependency review.
Assessments and operator decisions are append-only evidence. Admissibility is
not launch, resume, pause, cancel, preemption, provider, command, test,
workspace, project, queue, schedule, cognition, installation, promotion,
certification, release, or model-management authority.
"""

import os
import re
import shutil
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from supervised_work_dispatch_execution_session_preparation import inspect_prepared_development_execution_session
from execution_session_authorization_bounded_launch import inspect_bounded_development_execution_session
from live_execution_monitoring_operator_intervention import inspect_live_execution_monitoring
from execution_session_pause_resume_cancel_recovery import inspect_execution_session_control
from dependency_aware_execution import (
    load_dependency_aware_execution_assessment,
    load_dependency_aware_execution_review,
    public_dependency_aware_execution_assessments,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1233.8"
MAX_ASSESSMENTS = 100
MAX_REVIEWS = 200
MAX_RESOURCE_CLAIMS = 24
MAX_RESOURCE_UNITS = 64
MAX_CONCURRENCY_LIMIT = 16

RESOURCE_TYPES = {
    "execution_slot",
    "cpu_slot",
    "memory_budget",
    "workspace",
    "project",
    "provider_slot",
    "test_adapter",
    "browser_runtime",
    "node_runtime",
    "python_runtime",
    "filesystem_write_lock",
    "rollback_target",
    "operator_attention",
}
CLAIM_MODES = {"shared", "exclusive"}
RESOURCE_STATES = {"available", "degraded", "unavailable", "stale", "contradictory", "unknown"}
REVIEW_DISPOSITIONS = {"confirm_admissible", "hold", "reject", "request_changes", "propose_preemption"}
ADMISSION_STATES = {
    "admissible_pending_operator_review",
    "blocked_dependency_readiness",
    "blocked_resource_unavailable",
    "blocked_resource_stale",
    "blocked_resource_contradictory",
    "blocked_resource_unknown",
    "blocked_exclusive_conflict",
    "blocked_capacity",
    "blocked_concurrency_limit",
    "blocked_stale_existing_claim",
}

AUTHORITY_FLAGS = {
    "resource_assessment_authorized": True,
    "resource_review_authorized": True,
    "resource_admissibility_is_execution_authority": False,
    "resource_claim_is_lease_authority": False,
    "resource_preemption_authorized": False,
    "execution_session_launch_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "resume_authorized": False,
    "pause_authorized": False,
    "cancel_authorized": False,
    "background_execution_authorized": False,
    "cognition_write_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE = re.compile(
    r"^prepare resource and concurrency governance assessment for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24}) digest (?P<launch_digest>[a-f0-9]{64}) "
    r"monitor digest (?P<monitor_digest>[a-f0-9]{64}) control digest (?P<control_digest>[a-f0-9]{64}) "
    r"dependency assessment (?P<dependency_assessment>dependency_assessment_[a-f0-9]{24}) digest "
    r"(?P<dependency_assessment_digest>[a-f0-9]{64}) dependency review "
    r"(?P<dependency_review>dependency_review_[a-f0-9]{24}) digest (?P<dependency_review_digest>[a-f0-9]{64}) "
    r"concurrency limit (?P<limit>[0-9]{1,2}) with resource claims (?P<specs>[a-z0-9_:;+ -]+)[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review resource and concurrency governance assessment "
    r"(?P<decision>confirm admissible|hold|reject|request changes|propose preemption) "
    r"for assessment (?P<assessment>resource_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show resource and concurrency governance assessments[.!?]*$", re.I)
_SHOW_ONE = re.compile(
    r"^show resource and concurrency governance assessment (?P<assessment>resource_assessment_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_SHOW_REVIEWS = re.compile(r"^show resource and concurrency governance reviews[.!?]*$", re.I)
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _assessment_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "resource_concurrency_governance_assessments"


def _assessment_path(assessment_id: str, runtime_root=None) -> Path:
    return _assessment_root(runtime_root) / f"{str(assessment_id or '').lower()}.json"


def _index_path(launch_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "resource_concurrency_governance_indexes" / f"{str(launch_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "resource_concurrency_governance_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(assessment_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "resource_concurrency_governance_review_indexes" / f"{str(assessment_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "resource-concurrency-governance.lock"
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
                raise TimeoutError("Timed out waiting for resource-concurrency governance lock")
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
        "operator_review_required": True,
        "active_or_paused_session_required": True,
        "exact_resource_evidence_required": True,
        "exact_dependency_review_required": True,
        "resource_admission_is_not_execution_authority": True,
        "resource_claims_are_not_os_leases": True,
        "fresh_execution_authorization_required": True,
        "fresh_resume_authorization_required": True,
        "separate_step_authority_required": True,
        "original_plan_immutable": True,
        "historical_receipts_immutable": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "session_preempted": False,
        "resource_lease_created": False,
        "cognition_written": False,
        "source_modified": False,
        "hidden_retry_created": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["resource_concurrency_governance_result_digest"] = _digest(row)
    return row


def _normalize_token(value: Any) -> str:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not _TOKEN.fullmatch(token):
        raise ValueError("invalid_resource_code")
    return token


def _parse_positive_int(value: Any, *, name: str, maximum: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid_{name}") from None
    if result < 1 or result > maximum:
        raise ValueError(f"invalid_{name}")
    return result


def _parse_resource_claims(values: Iterable[Mapping[str, Any]] | str) -> tuple[list[dict[str, Any]], str]:
    raw_rows: list[dict[str, Any]] = []
    if isinstance(values, str):
        chunks = [chunk.strip() for chunk in values.split(";") if chunk.strip()]
        for chunk in chunks:
            parts = [part.strip() for part in chunk.split(":")]
            if len(parts) != 7:
                raise ValueError("invalid_resource_claim_spec")
            raw_rows.append({
                "code": parts[0],
                "resource_type": parts[1],
                "claim_mode": parts[2],
                "requested_units": parts[3],
                "available_capacity": parts[4],
                "resource_state": parts[5],
                "evidence_digest": parts[6],
            })
    else:
        for value in values:
            if not isinstance(value, Mapping):
                raise ValueError("invalid_resource_claim_spec")
            raw_rows.append(dict(value))
    if not raw_rows:
        raise ValueError("resource_claims_required")
    if len(raw_rows) > MAX_RESOURCE_CLAIMS:
        raise ValueError("resource_claim_limit_exceeded")

    rows: list[dict[str, Any]] = []
    references: set[str] = set()
    for raw in raw_rows:
        code = _normalize_token(raw.get("code"))
        resource_type = _normalize_token(raw.get("resource_type"))
        claim_mode = _normalize_token(raw.get("claim_mode"))
        state = _normalize_token(raw.get("resource_state"))
        if resource_type not in RESOURCE_TYPES:
            raise ValueError("unsupported_resource_type")
        if claim_mode not in CLAIM_MODES:
            raise ValueError("unsupported_claim_mode")
        if state not in RESOURCE_STATES:
            raise ValueError("unsupported_resource_state")
        units = _parse_positive_int(raw.get("requested_units"), name="requested_units", maximum=MAX_RESOURCE_UNITS)
        capacity = _parse_positive_int(raw.get("available_capacity"), name="available_capacity", maximum=MAX_RESOURCE_UNITS)
        digest = str(raw.get("evidence_digest") or "").strip().lower()
        if not _DIGEST.fullmatch(digest):
            raise ValueError("invalid_resource_evidence_digest")
        reference = f"resource_{_digest({'resource_code': code, 'resource_type': resource_type})[:24]}"
        if reference in references:
            raise ValueError("duplicate_resource_reference")
        references.add(reference)
        rows.append({
            "resource_reference": reference,
            "resource_code_digest": _digest({"resource_code": code}),
            "resource_type": resource_type,
            "claim_mode": claim_mode,
            "requested_units": units,
            "available_capacity": capacity,
            "resource_state": state,
            "evidence_digest": digest,
            "claim_digest": _digest({
                "resource_reference": reference,
                "resource_type": resource_type,
                "claim_mode": claim_mode,
                "requested_units": units,
                "available_capacity": capacity,
                "resource_state": state,
                "evidence_digest": digest,
            }),
        })
    rows.sort(key=lambda row: row["resource_reference"])
    return rows, _digest(rows)


def _load_index(launch_id: str, runtime_root=None) -> dict[str, Any]:
    path = _index_path(launch_id, runtime_root)
    if not path.is_file():
        return {"launch_id": launch_id, "assessment_ids": [], "generation": 0}
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("launch_id") != launch_id:
        raise ValueError("invalid_resource_assessment_index")
    return row


def _load_review_index(assessment_id: str, runtime_root=None) -> dict[str, Any] | None:
    path = _review_index_path(assessment_id, runtime_root)
    if not path.is_file():
        return None
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("assessment_id") != assessment_id:
        raise ValueError("invalid_resource_review_index")
    return row


def load_resource_concurrency_governance_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _assessment_path(assessment_id, runtime_root)
    if not path.is_file():
        return _failure("resource_concurrency_governance_assessment_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("assessment_id") != str(assessment_id or "").lower() or not _valid(row, "assessment_digest"):
        return _failure("resource_concurrency_governance_assessment_integrity_blocked")
    return row


def load_resource_concurrency_governance_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _review_path(review_id, runtime_root)
    if not path.is_file():
        return _failure("resource_concurrency_governance_review_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("review_id") != str(review_id or "").lower() or not _valid(row, "review_digest"):
        return _failure("resource_concurrency_governance_review_integrity_blocked")
    return row


def _dependency_basis(
    launch_id: str,
    *,
    dependency_assessment_id: str,
    expected_dependency_assessment_digest: str,
    dependency_review_id: str,
    expected_dependency_review_digest: str,
    launch_digest: str,
    monitor_digest: str,
    control_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    assessment = load_dependency_aware_execution_assessment(dependency_assessment_id, runtime_root=runtime_root)
    if not assessment.get("ok"):
        raise ValueError("dependency_assessment_integrity_blocked")
    if assessment.get("assessment_digest") != str(expected_dependency_assessment_digest or "").lower():
        raise ValueError("stale_dependency_assessment_digest")
    if assessment.get("launch_id") != launch_id or assessment.get("launch_digest") != launch_digest:
        raise ValueError("dependency_launch_lineage_blocked")
    if assessment.get("monitor_digest") != monitor_digest or assessment.get("control_digest") != control_digest:
        raise ValueError("dependency_runtime_lineage_stale")
    public_rows = public_dependency_aware_execution_assessments(runtime_root=runtime_root)
    if not public_rows.get("ok"):
        raise ValueError("dependency_history_integrity_blocked")
    candidates = [row for row in public_rows.get("assessments", []) if row.get("launch_id") == launch_id]
    if not candidates or max(int(row.get("generation") or 0) for row in candidates) != int(assessment.get("generation") or 0):
        raise ValueError("dependency_assessment_not_latest")
    review = load_dependency_aware_execution_review(dependency_review_id, runtime_root=runtime_root)
    if not review.get("ok"):
        raise ValueError("dependency_review_integrity_blocked")
    if review.get("review_digest") != str(expected_dependency_review_digest or "").lower():
        raise ValueError("stale_dependency_review_digest")
    if review.get("assessment_id") != assessment.get("assessment_id") or review.get("assessment_digest") != assessment.get("assessment_digest"):
        raise ValueError("dependency_review_lineage_blocked")
    disposition = str(review.get("disposition") or "")
    ready = disposition == "confirm_ready" and assessment.get("readiness_confirmable") is True
    return {
        "dependency_assessment": assessment,
        "dependency_review": review,
        "dependency_readiness_confirmed": ready,
        "dependency_disposition": disposition,
    }


def _prior_review_counts(launch_id: str, runtime_root=None) -> Counter:
    counts: Counter = Counter()
    root = _review_root(runtime_root)
    if not root.is_dir():
        return counts
    for path in sorted(root.glob("resource_review_*.json")):
        review = load_resource_concurrency_governance_review(path.stem, runtime_root=runtime_root)
        if not review.get("ok"):
            raise ValueError("resource_review_history_integrity_blocked")
        if review.get("launch_id") == launch_id:
            counts[str(review.get("disposition") or "unknown")] += 1
    return counts


def _confirmed_other_admissions(launch_id: str, runtime_root=None) -> dict[str, Any]:
    active: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    abandoned: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if not root.is_dir():
        return {"active": active, "stale": stale, "abandoned": abandoned}
    for path in sorted(root.glob("resource_review_*.json")):
        review = load_resource_concurrency_governance_review(path.stem, runtime_root=runtime_root)
        if not review.get("ok"):
            raise ValueError("resource_review_history_integrity_blocked")
        if review.get("disposition") != "confirm_admissible" or review.get("launch_id") == launch_id:
            continue
        assessment = load_resource_concurrency_governance_assessment(str(review.get("assessment_id") or ""), runtime_root=runtime_root)
        if not assessment.get("ok") or assessment.get("assessment_digest") != review.get("assessment_digest"):
            raise ValueError("resource_assessment_history_integrity_blocked")
        control = inspect_execution_session_control(str(assessment.get("launch_id") or ""), runtime_root=runtime_root, reconcile_runtime=False)
        if not control.get("ok"):
            raise ValueError("existing_resource_claim_control_integrity_blocked")
        state = str(control.get("session_state") or "")
        entry = {
            "launch_id": assessment.get("launch_id"),
            "assessment_id": assessment.get("assessment_id"),
            "assessment_digest": assessment.get("assessment_digest"),
            "control_digest_at_assessment": assessment.get("control_digest"),
            "current_control_digest": control.get("control_digest"),
            "session_state": state,
            "priority_rank": assessment.get("priority_rank"),
            "priority_level": assessment.get("priority_level"),
            "project_reference": assessment.get("project_reference"),
            "claims": assessment.get("resource_claims") or [],
        }
        if state not in {"active", "paused"}:
            abandoned.append(entry)
        elif control.get("control_digest") != assessment.get("control_digest"):
            stale.append(entry)
        else:
            active.append(entry)
    return {"active": active, "stale": stale, "abandoned": abandoned}


def _evaluate(
    claims: list[dict[str, Any]],
    *,
    dependency_ready: bool,
    concurrency_limit: int,
    priority_rank: int,
    other_admissions: Mapping[str, Any],
    prior_reviews: Counter,
) -> dict[str, Any]:
    state_counts = Counter(str(row.get("resource_state") or "unknown") for row in claims)
    type_counts = Counter(str(row.get("resource_type") or "unknown") for row in claims)
    active = list(other_admissions.get("active") or [])
    stale = list(other_admissions.get("stale") or [])
    abandoned = list(other_admissions.get("abandoned") or [])
    by_reference = {row["resource_reference"]: row for row in claims}
    exclusive_conflicts: set[str] = set()
    capacity_conflicts: set[str] = set()
    capacity_disagreements: set[str] = set()
    stale_conflicts: set[str] = set()
    conflicting_launches: set[str] = set()
    preemption_candidates: set[str] = set()

    for reference, current in by_reference.items():
        if int(current.get("requested_units") or 0) > int(current.get("available_capacity") or 0):
            capacity_conflicts.add(reference)

    for entry in stale:
        for existing in entry.get("claims") or []:
            if existing.get("resource_reference") in by_reference:
                stale_conflicts.add(str(existing.get("resource_reference")))
                conflicting_launches.add(str(entry.get("launch_id") or ""))

    for entry in active:
        existing_by_reference = {
            str(row.get("resource_reference")): row for row in (entry.get("claims") or [])
        }
        for reference, current in by_reference.items():
            existing = existing_by_reference.get(reference)
            if not existing:
                continue
            conflicting_launches.add(str(entry.get("launch_id") or ""))
            if int(existing.get("available_capacity") or 0) != int(current.get("available_capacity") or 0):
                capacity_disagreements.add(reference)
            if current.get("claim_mode") == "exclusive" or existing.get("claim_mode") == "exclusive":
                exclusive_conflicts.add(reference)
            elif int(current.get("requested_units") or 0) + int(existing.get("requested_units") or 0) > int(current.get("available_capacity") or 0):
                capacity_conflicts.add(reference)
            if int(priority_rank or 0) > 0 and int(entry.get("priority_rank") or 0) > int(priority_rank or 0):
                preemption_candidates.add(str(entry.get("launch_id") or ""))

    prospective_concurrency = len({str(row.get("launch_id") or "") for row in active}) + 1
    if not dependency_ready:
        state = "blocked_dependency_readiness"
    elif state_counts["contradictory"] or capacity_disagreements:
        state = "blocked_resource_contradictory"
    elif state_counts["unavailable"]:
        state = "blocked_resource_unavailable"
    elif state_counts["stale"]:
        state = "blocked_resource_stale"
    elif state_counts["unknown"]:
        state = "blocked_resource_unknown"
    elif stale_conflicts:
        state = "blocked_stale_existing_claim"
    elif exclusive_conflicts:
        state = "blocked_exclusive_conflict"
    elif capacity_conflicts:
        state = "blocked_capacity"
    elif prospective_concurrency > concurrency_limit:
        state = "blocked_concurrency_limit"
    else:
        state = "admissible_pending_operator_review"

    held_count = int(prior_reviews.get("hold", 0))
    changes_count = int(prior_reviews.get("request_changes", 0))
    starvation_risk = held_count + changes_count >= 2 and state != "admissible_pending_operator_review"
    preemption_eligible = bool(preemption_candidates) and state in {
        "blocked_exclusive_conflict", "blocked_capacity", "blocked_concurrency_limit"
    }
    return {
        "admission_state": state,
        "admission_confirmable": state == "admissible_pending_operator_review",
        "dependency_readiness_confirmed": dependency_ready,
        "resource_claim_count": len(claims),
        "resource_state_counts": dict(sorted(state_counts.items())),
        "resource_type_counts": dict(sorted(type_counts.items())),
        "active_confirmed_admission_count": len(active),
        "prospective_concurrency": prospective_concurrency,
        "concurrency_limit": concurrency_limit,
        "concurrency_limit_exceeded": prospective_concurrency > concurrency_limit,
        "exclusive_conflict_count": len(exclusive_conflicts),
        "capacity_conflict_count": len(capacity_conflicts),
        "capacity_disagreement_count": len(capacity_disagreements),
        "stale_existing_claim_conflict_count": len(stale_conflicts),
        "conflicting_resource_references": sorted(exclusive_conflicts | capacity_conflicts | capacity_disagreements | stale_conflicts),
        "conflicting_launch_ids": sorted(item for item in conflicting_launches if item),
        "stale_existing_admission_count": len(stale),
        "abandoned_admission_count": len(abandoned),
        "abandoned_claim_cleanup_recommended": bool(abandoned),
        "preemption_proposal_eligible": preemption_eligible,
        "preemption_candidate_launch_ids": sorted(item for item in preemption_candidates if item),
        "preemption_performed": False,
        "prior_hold_count": held_count,
        "prior_request_changes_count": changes_count,
        "starvation_risk_detected": starvation_risk,
        "fairness_review_required": starvation_risk or bool(conflicting_launches),
        "fairness_policy": "priority_then_operator_review_no_automatic_preemption",
    }


def prepare_resource_concurrency_governance_assessment(
    launch_id: str,
    *,
    expected_launch_digest: str,
    expected_monitor_digest: str,
    expected_control_digest: str,
    dependency_assessment_id: str,
    expected_dependency_assessment_digest: str,
    dependency_review_id: str,
    expected_dependency_review_digest: str,
    concurrency_limit: int,
    resource_claims: Iterable[Mapping[str, Any]] | str,
    runtime_root=None,
) -> dict[str, Any]:
    launch_id = str(launch_id or "").lower()
    try:
        claims, resource_claim_spec_digest = _parse_resource_claims(resource_claims)
        limit = _parse_positive_int(concurrency_limit, name="concurrency_limit", maximum=MAX_CONCURRENCY_LIMIT)
    except ValueError as exc:
        return _failure("resource_concurrency_governance_evidence_blocked", str(exc))
    try:
        with _lock(runtime_root):
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            if not launch.get("ok"):
                return _failure("resource_concurrency_governance_launch_evidence_unavailable")
            if launch.get("launch_digest") != str(expected_launch_digest or "").lower():
                return _failure("resource_concurrency_governance_stale_launch_digest")
            monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            if not monitor.get("ok"):
                return _failure("resource_concurrency_governance_monitor_evidence_unavailable")
            if monitor.get("monitor_digest") != str(expected_monitor_digest or "").lower():
                return _failure("resource_concurrency_governance_stale_monitor_digest")
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not control.get("ok"):
                return _failure("resource_concurrency_governance_control_evidence_unavailable")
            if control.get("control_digest") != str(expected_control_digest or "").lower():
                return _failure("resource_concurrency_governance_stale_control_digest")
            session_state = str(control.get("session_state") or "")
            if session_state not in {"active", "paused"}:
                return _failure("resource_concurrency_governance_session_state_blocked", session_state)
            if monitor.get("launch_digest") != launch.get("launch_digest") or control.get("launch_digest") != launch.get("launch_digest"):
                return _failure("resource_concurrency_governance_lineage_blocked")
            if str(monitor.get("current_stage") or "") in {"completed_pending_review", "completed", "cancelled"}:
                return _failure("resource_concurrency_governance_terminal_monitor_state_blocked")
            prepared = inspect_prepared_development_execution_session(str(launch.get("source_session_id") or ""), runtime_root=runtime_root)
            if not prepared.get("ok") or prepared.get("session_digest") != launch.get("source_session_digest"):
                return _failure("resource_concurrency_governance_original_plan_lineage_blocked")
            try:
                dependency = _dependency_basis(
                    launch_id,
                    dependency_assessment_id=str(dependency_assessment_id or "").lower(),
                    expected_dependency_assessment_digest=expected_dependency_assessment_digest,
                    dependency_review_id=str(dependency_review_id or "").lower(),
                    expected_dependency_review_digest=expected_dependency_review_digest,
                    launch_digest=str(launch.get("launch_digest") or ""),
                    monitor_digest=str(monitor.get("monitor_digest") or ""),
                    control_digest=str(control.get("control_digest") or ""),
                    runtime_root=runtime_root,
                )
            except ValueError as exc:
                return _failure("resource_concurrency_governance_dependency_lineage_blocked", str(exc))

            index = _load_index(launch_id, runtime_root)
            assessment_ids = list(index.get("assessment_ids") or [])
            latest: dict[str, Any] | None = None
            latest_review: dict[str, Any] | None = None
            if assessment_ids:
                latest = load_resource_concurrency_governance_assessment(assessment_ids[-1], runtime_root=runtime_root)
                if not latest.get("ok"):
                    return _failure("resource_concurrency_governance_history_integrity_blocked")
                review_index = _load_review_index(latest["assessment_id"], runtime_root)
                if review_index:
                    latest_review = load_resource_concurrency_governance_review(review_index.get("review_id"), runtime_root=runtime_root)
                    if not latest_review.get("ok"):
                        return _failure("resource_concurrency_governance_review_history_integrity_blocked")
                same = (
                    latest.get("launch_digest") == launch.get("launch_digest")
                    and latest.get("monitor_digest") == monitor.get("monitor_digest")
                    and latest.get("control_digest") == control.get("control_digest")
                    and latest.get("dependency_assessment_digest") == dependency["dependency_assessment"].get("assessment_digest")
                    and latest.get("dependency_review_digest") == dependency["dependency_review"].get("review_digest")
                    and latest.get("resource_claim_spec_digest") == resource_claim_spec_digest
                    and int(latest.get("concurrency_limit") or 0) == limit
                )
                if same and latest_review is None:
                    replay = dict(latest)
                    replay["operation_status"] = "replayed"
                    return replay
                if latest_review is None:
                    return _failure("resource_concurrency_governance_pending_review")
                if same:
                    return _failure("resource_concurrency_governance_fresh_evidence_required")

            try:
                other_admissions = _confirmed_other_admissions(launch_id, runtime_root)
                prior_reviews = _prior_review_counts(launch_id, runtime_root)
            except ValueError as exc:
                return _failure("resource_concurrency_governance_history_integrity_blocked", str(exc))
            evaluation = _evaluate(
                claims,
                dependency_ready=bool(dependency.get("dependency_readiness_confirmed")),
                concurrency_limit=limit,
                priority_rank=int(prepared.get("priority_rank") or 0),
                other_admissions=other_admissions,
                prior_reviews=prior_reviews,
            )
            generation = int(index.get("generation") or 0) + 1
            identity = {
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "monitor_digest": monitor.get("monitor_digest"),
                "control_digest": control.get("control_digest"),
                "dependency_assessment_digest": dependency["dependency_assessment"].get("assessment_digest"),
                "dependency_review_digest": dependency["dependency_review"].get("review_digest"),
                "resource_claim_spec_digest": resource_claim_spec_digest,
                "concurrency_limit": limit,
                "generation": generation,
            }
            assessment_id = f"resource_assessment_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "resource_concurrency_governance_assessment_ready_for_operator_review",
                "assessment_id": assessment_id,
                "generation": generation,
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "monitor_id": monitor.get("monitor_id"),
                "monitor_digest": monitor.get("monitor_digest"),
                "monitor_generation": monitor.get("generation"),
                "control_id": control.get("control_id"),
                "control_digest": control.get("control_digest"),
                "control_generation": control.get("generation"),
                "session_state_at_assessment": session_state,
                "source_session_id": prepared.get("session_id"),
                "original_plan_digest": prepared.get("session_digest"),
                "source_schedule_digest": prepared.get("source_schedule_digest"),
                "source_schedule_slot_digest": prepared.get("source_schedule_slot_digest"),
                "source_queue_digest": prepared.get("source_queue_digest"),
                "source_prioritization_digest": prepared.get("source_prioritization_digest"),
                "queue_item_id": prepared.get("queue_item_id"),
                "project_reference": prepared.get("project_reference"),
                "priority_rank": prepared.get("priority_rank"),
                "priority_level": prepared.get("priority_level"),
                "dependency_assessment_id": dependency["dependency_assessment"].get("assessment_id"),
                "dependency_assessment_digest": dependency["dependency_assessment"].get("assessment_digest"),
                "dependency_assessment_generation": dependency["dependency_assessment"].get("generation"),
                "dependency_review_id": dependency["dependency_review"].get("review_id"),
                "dependency_review_digest": dependency["dependency_review"].get("review_digest"),
                "dependency_disposition": dependency.get("dependency_disposition"),
                "resource_claim_spec_digest": resource_claim_spec_digest,
                "resource_claims": claims,
                "resource_references": [claim["resource_reference"] for claim in claims],
                "previous_assessment_id": latest.get("assessment_id", "") if latest else "",
                "previous_assessment_digest": latest.get("assessment_digest", "") if latest else "",
                "safe_boundary_pause_recommended": session_state == "active" and not evaluation["admission_confirmable"],
                "fresh_resume_review_eligible": session_state == "paused" and evaluation["admission_confirmable"],
                "operator_intervention_required": not evaluation["admission_confirmable"],
                "admission_confirmation_granted": False,
                "operation_status": "created",
                **evaluation,
                **_base(),
            }
            row = _sealed(row, "assessment_digest")
            path = _assessment_path(assessment_id, runtime_root)
            if path.exists():
                existing = load_resource_concurrency_governance_assessment(assessment_id, runtime_root=runtime_root)
                if existing.get("assessment_digest") == row.get("assessment_digest"):
                    replay = dict(existing)
                    replay["operation_status"] = "replayed"
                    return replay
                return _failure("resource_concurrency_governance_identity_collision")
            _atomic_json(path, row)
            assessment_ids.append(assessment_id)
            _atomic_json(_index_path(launch_id, runtime_root), {
                "launch_id": launch_id,
                "assessment_ids": assessment_ids[-MAX_ASSESSMENTS:],
                "generation": generation,
                "latest_assessment_id": assessment_id,
                "latest_assessment_digest": row["assessment_digest"],
            })
            return row
    except TimeoutError as exc:
        return _failure("resource_concurrency_governance_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("resource_concurrency_governance_internal_blocked", type(exc).__name__)


def review_resource_concurrency_governance_assessment(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    runtime_root=None,
) -> dict[str, Any]:
    assessment_id = str(assessment_id or "").lower()
    decision = str(disposition or "").strip().lower().replace("-", "_").replace(" ", "_")
    if decision not in REVIEW_DISPOSITIONS:
        return _failure("resource_concurrency_governance_review_disposition_blocked")
    try:
        with _lock(runtime_root):
            assessment = load_resource_concurrency_governance_assessment(assessment_id, runtime_root=runtime_root)
            if not assessment.get("ok"):
                return _failure("resource_concurrency_governance_review_assessment_blocked")
            if assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
                return _failure("resource_concurrency_governance_review_stale_digest")
            existing_index = _load_review_index(assessment_id, runtime_root)
            if existing_index:
                existing = load_resource_concurrency_governance_review(existing_index.get("review_id"), runtime_root=runtime_root)
                if not existing.get("ok"):
                    return _failure("resource_concurrency_governance_review_integrity_blocked")
                if existing.get("disposition") == decision and existing.get("assessment_digest") == assessment.get("assessment_digest"):
                    replay = dict(existing)
                    replay["operation_status"] = "replayed"
                    return replay
                return _failure("resource_concurrency_governance_review_conflict_blocked")
            if decision == "confirm_admissible" and assessment.get("admission_confirmable") is not True:
                return _failure("resource_concurrency_governance_admission_confirmation_blocked")
            if decision == "propose_preemption" and assessment.get("preemption_proposal_eligible") is not True:
                return _failure("resource_concurrency_governance_preemption_proposal_blocked")

            launch_id = str(assessment.get("launch_id") or "")
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not launch.get("ok") or launch.get("launch_digest") != assessment.get("launch_digest"):
                return _failure("resource_concurrency_governance_review_launch_lineage_blocked")
            if not monitor.get("ok") or monitor.get("monitor_digest") != assessment.get("monitor_digest"):
                return _failure("resource_concurrency_governance_review_monitor_lineage_blocked")
            if not control.get("ok") or control.get("control_digest") != assessment.get("control_digest"):
                return _failure("resource_concurrency_governance_review_control_lineage_blocked")
            if str(control.get("session_state") or "") not in {"active", "paused"}:
                return _failure("resource_concurrency_governance_review_session_state_blocked")
            try:
                dependency = _dependency_basis(
                    launch_id,
                    dependency_assessment_id=str(assessment.get("dependency_assessment_id") or ""),
                    expected_dependency_assessment_digest=str(assessment.get("dependency_assessment_digest") or ""),
                    dependency_review_id=str(assessment.get("dependency_review_id") or ""),
                    expected_dependency_review_digest=str(assessment.get("dependency_review_digest") or ""),
                    launch_digest=str(launch.get("launch_digest") or ""),
                    monitor_digest=str(monitor.get("monitor_digest") or ""),
                    control_digest=str(control.get("control_digest") or ""),
                    runtime_root=runtime_root,
                )
            except ValueError as exc:
                return _failure("resource_concurrency_governance_review_dependency_lineage_blocked", str(exc))
            if dependency.get("dependency_disposition") != assessment.get("dependency_disposition"):
                return _failure("resource_concurrency_governance_review_dependency_disposition_blocked")

            identity = {
                "assessment_id": assessment_id,
                "assessment_digest": assessment.get("assessment_digest"),
                "disposition": decision,
            }
            review_id = f"resource_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"resource_concurrency_governance_{decision}_recorded",
                "review_id": review_id,
                "assessment_id": assessment_id,
                "assessment_digest": assessment.get("assessment_digest"),
                "launch_id": launch_id,
                "project_reference": assessment.get("project_reference"),
                "generation": assessment.get("generation"),
                "disposition": decision,
                "admission_state": assessment.get("admission_state"),
                "admission_confirmed": decision == "confirm_admissible",
                "assessment_held": decision == "hold",
                "assessment_rejected": decision == "reject",
                "assessment_changes_requested": decision == "request_changes",
                "preemption_proposal_recorded": decision == "propose_preemption",
                "preemption_candidate_launch_ids": assessment.get("preemption_candidate_launch_ids") or [],
                "preemption_performed": False,
                "resource_lease_created": False,
                "confirmed_admissibility_requires_fresh_execution_authority": decision == "confirm_admissible",
                "confirmed_admissibility_does_not_launch_session": decision == "confirm_admissible",
                "confirmed_admissibility_does_not_resume_session": decision == "confirm_admissible",
                "reviewed_session_state": control.get("session_state"),
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "review_digest")
            path = _review_path(review_id, runtime_root)
            if path.exists():
                existing = load_resource_concurrency_governance_review(review_id, runtime_root=runtime_root)
                if existing.get("review_digest") == row.get("review_digest"):
                    replay = dict(existing)
                    replay["operation_status"] = "replayed"
                    return replay
                return _failure("resource_concurrency_governance_review_identity_collision")
            _atomic_json(path, row)
            _atomic_json(_review_index_path(assessment_id, runtime_root), {
                "assessment_id": assessment_id,
                "assessment_digest": assessment.get("assessment_digest"),
                "review_id": review_id,
                "review_digest": row["review_digest"],
                "disposition": decision,
            })
            return row
    except TimeoutError as exc:
        return _failure("resource_concurrency_governance_review_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("resource_concurrency_governance_review_internal_blocked", type(exc).__name__)


def _public_assessment(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "assessment_id", "assessment_digest", "generation", "launch_id", "launch_digest",
        "monitor_id", "monitor_digest", "monitor_generation", "control_id", "control_digest", "control_generation",
        "session_state_at_assessment", "source_session_id", "original_plan_digest", "source_schedule_digest",
        "source_schedule_slot_digest", "source_queue_digest", "source_prioritization_digest", "queue_item_id",
        "project_reference", "priority_rank", "priority_level", "dependency_assessment_id",
        "dependency_assessment_digest", "dependency_assessment_generation", "dependency_review_id",
        "dependency_review_digest", "dependency_disposition", "dependency_readiness_confirmed",
        "resource_claim_spec_digest", "resource_claims", "resource_references", "resource_claim_count",
        "resource_state_counts", "resource_type_counts", "admission_state", "admission_confirmable",
        "active_confirmed_admission_count", "prospective_concurrency", "concurrency_limit",
        "concurrency_limit_exceeded", "exclusive_conflict_count", "capacity_conflict_count",
        "capacity_disagreement_count", "stale_existing_claim_conflict_count", "conflicting_resource_references",
        "conflicting_launch_ids", "stale_existing_admission_count", "abandoned_admission_count",
        "abandoned_claim_cleanup_recommended", "preemption_proposal_eligible", "preemption_candidate_launch_ids",
        "preemption_performed", "prior_hold_count", "prior_request_changes_count", "starvation_risk_detected",
        "fairness_review_required", "fairness_policy", "safe_boundary_pause_recommended",
        "fresh_resume_review_eligible", "operator_intervention_required", "admission_confirmation_granted",
        "previous_assessment_id", "previous_assessment_digest", "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_resource_concurrency_governance_assessment_digest"] = _digest(result)
    return result


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "review_id", "review_digest", "assessment_id", "assessment_digest", "launch_id",
        "project_reference", "generation", "disposition", "admission_state", "admission_confirmed",
        "assessment_held", "assessment_rejected", "assessment_changes_requested", "preemption_proposal_recorded",
        "preemption_candidate_launch_ids", "preemption_performed", "resource_lease_created",
        "confirmed_admissibility_requires_fresh_execution_authority",
        "confirmed_admissibility_does_not_launch_session", "confirmed_admissibility_does_not_resume_session",
        "reviewed_session_state", "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_resource_concurrency_governance_review_digest"] = _digest(result)
    return result


def inspect_resource_concurrency_governance_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_resource_concurrency_governance_assessment(assessment_id, runtime_root=runtime_root)
    return _public_assessment(row) if row.get("ok") else row


def public_resource_concurrency_governance_assessments(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _assessment_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("resource_assessment_*.json"))[-MAX_ASSESSMENTS:]:
            row = load_resource_concurrency_governance_assessment(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("resource_concurrency_governance_assessment_list_blocked")
            rows.append(_public_assessment(row))
    rows.sort(key=lambda row: (str(row.get("launch_id") or ""), int(row.get("generation") or 0)))
    result = {
        "ok": True,
        "status": "resource_concurrency_governance_assessment_list_ready",
        "assessment_count": len(rows),
        "assessments": rows,
        **_base(),
    }
    result["public_resource_concurrency_governance_assessment_list_digest"] = _digest(result)
    return result


def public_resource_concurrency_governance_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("resource_review_*.json"))[-MAX_REVIEWS:]:
            row = load_resource_concurrency_governance_review(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("resource_concurrency_governance_review_list_blocked")
            rows.append(_public_review(row))
    rows.sort(key=lambda row: (str(row.get("launch_id") or ""), int(row.get("generation") or 0)))
    result = {
        "ok": True,
        "status": "resource_concurrency_governance_review_list_ready",
        "review_count": len(rows),
        "reviews": rows,
        **_base(),
    }
    result["public_resource_concurrency_governance_review_list_digest"] = _digest(result)
    return result


def resource_concurrency_governance_response(row: Mapping[str, Any]) -> str:
    if row.get("ok") is not True:
        return f"Resource and concurrency governance was blocked: {row.get('reason') or row.get('status') or 'invalid evidence'}."
    status = str(row.get("status") or "")
    if status == "resource_concurrency_governance_assessment_ready_for_operator_review":
        return (
            f"Resource assessment {row.get('assessment_id')} is ready for exact operator review with state "
            f"{row.get('admission_state')}. Admissibility grants no launch, resume, lease, or preemption authority."
        )
    if status.endswith("_recorded"):
        return (
            f"Resource review {row.get('review_id')} recorded {row.get('disposition')}. "
            "Fresh separately governed authority is still required for execution, resume, or preemption."
        )
    if status == "resource_concurrency_governance_assessment_list_ready":
        return f"There are {row.get('assessment_count', 0)} resource and concurrency governance assessments."
    if status == "resource_concurrency_governance_review_list_ready":
        return f"There are {row.get('review_count', 0)} resource and concurrency governance reviews."
    return f"Resource and concurrency governance evidence recorded: {status}."


def process_resource_concurrency_governance_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE.fullmatch(text)
    review = _REVIEW.fullmatch(text)
    show_one = _SHOW_ONE.fullmatch(text)
    if prepare:
        result = _public_assessment(prepare_resource_concurrency_governance_assessment(
            prepare.group("launch").lower(),
            expected_launch_digest=prepare.group("launch_digest").lower(),
            expected_monitor_digest=prepare.group("monitor_digest").lower(),
            expected_control_digest=prepare.group("control_digest").lower(),
            dependency_assessment_id=prepare.group("dependency_assessment").lower(),
            expected_dependency_assessment_digest=prepare.group("dependency_assessment_digest").lower(),
            dependency_review_id=prepare.group("dependency_review").lower(),
            expected_dependency_review_digest=prepare.group("dependency_review_digest").lower(),
            concurrency_limit=int(prepare.group("limit")),
            resource_claims=prepare.group("specs"),
            runtime_root=runtime_root,
        ))
    elif review:
        result = _public_review(review_resource_concurrency_governance_assessment(
            review.group("assessment").lower(),
            expected_assessment_digest=review.group("digest").lower(),
            disposition=review.group("decision").lower().replace(" ", "_"),
            runtime_root=runtime_root,
        ))
    elif _SHOW_ALL.fullmatch(text):
        result = public_resource_concurrency_governance_assessments(runtime_root=runtime_root)
    elif show_one:
        result = inspect_resource_concurrency_governance_assessment(show_one.group("assessment").lower(), runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        result = public_resource_concurrency_governance_reviews(runtime_root=runtime_root)
    else:
        return {"active": False}
    return {
        "active": True,
        "response": resource_concurrency_governance_response(result),
        "resource_concurrency_governance": result,
    }


def build_resource_concurrency_governance_contract() -> dict[str, Any]:
    result = {
        "ok": True,
        "status": "resource_concurrency_governance_contract_ready",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Resource and Concurrency Governance",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "active_or_paused_session_required": True,
        "exact_resource_evidence_required": True,
        "exact_dependency_review_required": True,
        "operator_review_required": True,
        "immutable_resource_claim_lineage": True,
        "queue_priority_binding": True,
        "schedule_binding": True,
        "dependency_readiness_binding": True,
        "bounded_concurrency_limit": True,
        "shared_and_exclusive_claims": True,
        "capacity_conflict_detection": True,
        "stale_and_abandoned_claim_detection": True,
        "fairness_and_starvation_evidence": True,
        "preemption_proposal_only": True,
        "automatic_preemption_forbidden": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_conflict_hardening_required": True,
        "resource_types": sorted(RESOURCE_TYPES),
        "claim_modes": sorted(CLAIM_MODES),
        "resource_states": sorted(RESOURCE_STATES),
        "admission_states": sorted(ADMISSION_STATES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        **_base(),
    }
    result["resource_concurrency_governance_contract_digest"] = _digest(result)
    return result
