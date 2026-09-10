from __future__ import annotations

"""Dependency-aware readiness evidence for supervised execution sessions.

v1232 evaluates sealed, content-free prerequisite evidence for an active or
paused bounded development execution session. Assessments and exact operator
reviews are append-only evidence. A ready result establishes readiness only. It
does not launch, resume, pause, cancel, contact a provider, execute commands or
tests, materialize a workspace, mutate a project/queue/schedule/source/cognition,
retry work, reuse authority, install, promote, certify, release, or manage models.
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
from dynamic_execution_plan_revision import (
    public_dynamic_execution_plan_revisions,
    public_dynamic_execution_plan_revision_reviews,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1232.8"
MAX_ASSESSMENTS = 100
MAX_REVIEWS = 200
MAX_DEPENDENCIES = 24
MAX_PARENT_DEPENDENCIES = 8

DEPENDENCY_TYPES = {
    "task",
    "file",
    "tool",
    "approval",
    "environment",
    "test_result",
    "operator_decision",
    "project_state",
    "rollback_precondition",
}
DEPENDENCY_STATES = {
    "satisfied",
    "pending",
    "blocked",
    "failed",
    "stale",
    "contradictory",
    "unknown",
}
REVIEW_DISPOSITIONS = {"confirm_ready", "hold", "reject", "request_changes"}
READINESS_STATES = {
    "ready_pending_operator_review",
    "blocked_cycle",
    "blocked_contradictory",
    "blocked_failed",
    "blocked_stale",
    "blocked_dependency",
    "blocked_pending",
    "blocked_unknown",
}
AUTHORITY_FLAGS = {
    "dependency_assessment_authorized": True,
    "dependency_review_authorized": True,
    "dependency_readiness_is_execution_authority": False,
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
    r"^prepare dependency-aware execution assessment for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24}) digest (?P<launch_digest>[a-f0-9]{64}) "
    r"monitor digest (?P<monitor_digest>[a-f0-9]{64}) control digest (?P<control_digest>[a-f0-9]{64}) "
    r"revision digest (?P<revision_digest>none|[a-f0-9]{64}) with dependency evidence "
    r"(?P<specs>[a-z0-9_:;+ -]+)[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review dependency-aware execution assessment (?P<decision>confirm ready|hold|reject|request changes) "
    r"for assessment (?P<assessment>dependency_assessment_[a-f0-9]{24}) digest "
    r"(?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show dependency-aware execution assessments[.!?]*$", re.I)
_SHOW_ONE = re.compile(
    r"^show dependency-aware execution assessment (?P<assessment>dependency_assessment_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_SHOW_REVIEWS = re.compile(r"^show dependency-aware execution reviews[.!?]*$", re.I)
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _assessment_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "dependency_aware_execution_assessments"


def _assessment_path(assessment_id: str, runtime_root=None) -> Path:
    return _assessment_root(runtime_root) / f"{str(assessment_id or '').lower()}.json"


def _index_path(launch_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "dependency_aware_execution_indexes" / f"{str(launch_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "dependency_aware_execution_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(assessment_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "dependency_aware_execution_review_indexes" / f"{str(assessment_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "dependency-aware-execution.lock"
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
                raise TimeoutError("Timed out waiting for dependency-aware execution lock")
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
        "exact_dependency_evidence_required": True,
        "dependency_graph_evaluated": True,
        "readiness_only": True,
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
    row["dependency_aware_execution_result_digest"] = _digest(row)
    return row


def _normalize_token(value: Any) -> str:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not _TOKEN.fullmatch(token):
        raise ValueError("invalid_dependency_code")
    return token


def _parse_dependency_specs(values: Iterable[Mapping[str, Any]] | str, launch_id: str) -> tuple[list[dict[str, Any]], str]:
    raw_rows: list[dict[str, Any]] = []
    if isinstance(values, str):
        chunks = [chunk.strip() for chunk in values.split(";") if chunk.strip()]
        for chunk in chunks:
            parts = [part.strip() for part in chunk.split(":")]
            if len(parts) not in {4, 5}:
                raise ValueError("invalid_dependency_spec")
            raw_rows.append({
                "code": parts[0],
                "dependency_type": parts[1],
                "dependency_state": parts[2],
                "evidence_digest": parts[3],
                "depends_on": [item for item in parts[4].split("+") if item] if len(parts) == 5 else [],
            })
    else:
        for value in values:
            if not isinstance(value, Mapping):
                raise ValueError("invalid_dependency_spec")
            raw_rows.append(dict(value))
    if not raw_rows:
        raise ValueError("dependency_evidence_required")
    if len(raw_rows) > MAX_DEPENDENCIES:
        raise ValueError("dependency_limit_exceeded")

    normalized: list[dict[str, Any]] = []
    codes: list[str] = []
    for raw in raw_rows:
        code = _normalize_token(raw.get("code"))
        if code in codes:
            raise ValueError("duplicate_dependency_code")
        codes.append(code)
        dependency_type = _normalize_token(raw.get("dependency_type"))
        state = _normalize_token(raw.get("dependency_state"))
        digest = str(raw.get("evidence_digest") or "").strip().lower()
        if dependency_type not in DEPENDENCY_TYPES:
            raise ValueError("unsupported_dependency_type")
        if state not in DEPENDENCY_STATES:
            raise ValueError("unsupported_dependency_state")
        if not _DIGEST.fullmatch(digest):
            raise ValueError("invalid_dependency_evidence_digest")
        parents = [_normalize_token(item) for item in (raw.get("depends_on") or [])]
        parents = list(dict.fromkeys(parents))
        if len(parents) > MAX_PARENT_DEPENDENCIES:
            raise ValueError("dependency_parent_limit_exceeded")
        normalized.append({
            "code": code,
            "dependency_type": dependency_type,
            "dependency_state": state,
            "evidence_digest": digest,
            "depends_on": parents,
        })

    references = {
        code: f"dependency_{_digest({'launch_id': launch_id, 'dependency_code': code})[:24]}"
        for code in codes
    }
    rows: list[dict[str, Any]] = []
    for raw in normalized:
        missing = sorted(parent for parent in raw["depends_on"] if parent not in references)
        if missing:
            raise ValueError("unknown_dependency_parent")
        rows.append({
            "dependency_reference": references[raw["code"]],
            "dependency_code_digest": _digest({"dependency_code": raw["code"]}),
            "dependency_type": raw["dependency_type"],
            "dependency_state": raw["dependency_state"],
            "evidence_digest": raw["evidence_digest"],
            "depends_on_references": sorted(references[parent] for parent in raw["depends_on"]),
            "required": True,
        })
    rows.sort(key=lambda row: row["dependency_reference"])
    return rows, _digest(rows)


def _has_cycle(rows: list[dict[str, Any]]) -> bool:
    graph = {row["dependency_reference"]: tuple(row.get("depends_on_references") or []) for row in rows}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for parent in graph.get(node, ()):
            if visit(parent):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cycle = _has_cycle(rows)
    state_counts = Counter(str(row.get("dependency_state") or "unknown") for row in rows)
    type_counts = Counter(str(row.get("dependency_type") or "unknown") for row in rows)
    if cycle:
        readiness = "blocked_cycle"
    elif state_counts["contradictory"]:
        readiness = "blocked_contradictory"
    elif state_counts["failed"]:
        readiness = "blocked_failed"
    elif state_counts["stale"]:
        readiness = "blocked_stale"
    elif state_counts["blocked"]:
        readiness = "blocked_dependency"
    elif state_counts["pending"]:
        readiness = "blocked_pending"
    elif state_counts["unknown"]:
        readiness = "blocked_unknown"
    else:
        readiness = "ready_pending_operator_review"
    unresolved = sum(count for state, count in state_counts.items() if state != "satisfied")
    blocking = unresolved + (1 if cycle and unresolved == 0 else 0)
    return {
        "readiness_state": readiness,
        "readiness_confirmable": readiness == "ready_pending_operator_review",
        "all_required_dependencies_satisfied": readiness == "ready_pending_operator_review",
        "dependency_cycle_detected": cycle,
        "dependency_count": len(rows),
        "satisfied_dependency_count": state_counts["satisfied"],
        "unresolved_dependency_count": unresolved,
        "blocking_dependency_count": blocking,
        "dependency_state_counts": dict(sorted(state_counts.items())),
        "dependency_type_counts": dict(sorted(type_counts.items())),
    }


def _load_index(launch_id: str, runtime_root=None) -> dict[str, Any]:
    path = _index_path(launch_id, runtime_root)
    if not path.is_file():
        return {"launch_id": launch_id, "assessment_ids": [], "generation": 0}
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("launch_id") != launch_id:
        raise ValueError("invalid_dependency_assessment_index")
    return row


def _load_review_index(assessment_id: str, runtime_root=None) -> dict[str, Any] | None:
    path = _review_index_path(assessment_id, runtime_root)
    if not path.is_file():
        return None
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("assessment_id") != assessment_id:
        raise ValueError("invalid_dependency_review_index")
    return row


def load_dependency_aware_execution_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _assessment_path(assessment_id, runtime_root)
    if not path.is_file():
        return _failure("dependency_aware_execution_assessment_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("assessment_id") != str(assessment_id or "").lower() or not _valid(row, "assessment_digest"):
        return _failure("dependency_aware_execution_assessment_integrity_blocked")
    return row


def load_dependency_aware_execution_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _review_path(review_id, runtime_root)
    if not path.is_file():
        return _failure("dependency_aware_execution_review_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("review_id") != str(review_id or "").lower() or not _valid(row, "review_digest"):
        return _failure("dependency_aware_execution_review_integrity_blocked")
    return row


def _current_plan_revision_basis(launch_id: str, runtime_root=None) -> dict[str, Any]:
    proposals = public_dynamic_execution_plan_revisions(runtime_root=runtime_root)
    reviews = public_dynamic_execution_plan_revision_reviews(runtime_root=runtime_root)
    if not proposals.get("ok") or not reviews.get("ok"):
        raise ValueError("plan_revision_history_integrity_blocked")
    candidates = sorted(
        [row for row in proposals.get("revisions", []) if row.get("launch_id") == launch_id],
        key=lambda row: int(row.get("generation") or 0),
    )
    review_by_revision = {row.get("revision_id"): row for row in reviews.get("reviews", [])}
    accepted: dict[str, Any] | None = None
    unresolved: dict[str, Any] | None = None
    for proposal in candidates:
        review = review_by_revision.get(proposal.get("revision_id"))
        if review is None:
            unresolved = proposal
            continue
        disposition = review.get("disposition")
        if disposition == "accept":
            accepted = proposal
            unresolved = None
        elif disposition in {"defer", "request_changes"}:
            unresolved = proposal
        elif disposition == "reject":
            unresolved = None
    if unresolved is not None:
        return {
            "ok": False,
            "status": "dependency_aware_execution_plan_revision_unresolved",
            "revision_id": unresolved.get("revision_id"),
            "revision_digest": unresolved.get("revision_digest"),
        }
    if accepted is None:
        return {
            "ok": True,
            "status": "dependency_aware_execution_original_plan_basis",
            "plan_basis": "original_approved_plan",
            "accepted_revision_id": "",
            "accepted_revision_digest": "",
            "accepted_revision_generation": 0,
            "revision_dependency_change_count": 0,
        }
    return {
        "ok": True,
        "status": "dependency_aware_execution_accepted_revision_basis",
        "plan_basis": "accepted_dynamic_plan_revision",
        "accepted_revision_id": accepted.get("revision_id"),
        "accepted_revision_digest": accepted.get("revision_digest"),
        "accepted_revision_generation": accepted.get("generation"),
        "revision_dependency_change_count": len(accepted.get("new_or_changed_dependency_codes") or []),
    }


def _expected_revision_matches(basis: Mapping[str, Any], expected_revision_digest: str) -> bool:
    expected = str(expected_revision_digest or "").strip().lower()
    actual = str(basis.get("accepted_revision_digest") or "").lower()
    if actual:
        return expected == actual
    return expected in {"", "none"}


def prepare_dependency_aware_execution_assessment(
    launch_id: str,
    *,
    expected_launch_digest: str,
    expected_monitor_digest: str,
    expected_control_digest: str,
    expected_revision_digest: str,
    dependency_evidence: Iterable[Mapping[str, Any]] | str,
    runtime_root=None,
) -> dict[str, Any]:
    launch_id = str(launch_id or "").lower()
    try:
        dependencies, dependency_spec_digest = _parse_dependency_specs(dependency_evidence, launch_id)
    except ValueError as exc:
        return _failure("dependency_aware_execution_evidence_blocked", str(exc))
    try:
        with _lock(runtime_root):
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            if not launch.get("ok"):
                return _failure("dependency_aware_execution_launch_evidence_unavailable")
            if launch.get("launch_digest") != str(expected_launch_digest or "").lower():
                return _failure("dependency_aware_execution_stale_launch_digest")
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not control.get("ok"):
                return _failure("dependency_aware_execution_control_evidence_unavailable")
            if control.get("control_digest") != str(expected_control_digest or "").lower():
                return _failure("dependency_aware_execution_stale_control_digest")
            session_state = str(control.get("session_state") or "")
            if session_state not in {"active", "paused"}:
                return _failure("dependency_aware_execution_session_state_blocked", session_state)
            monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            if not monitor.get("ok"):
                return _failure("dependency_aware_execution_monitor_evidence_unavailable")
            if monitor.get("monitor_digest") != str(expected_monitor_digest or "").lower():
                return _failure("dependency_aware_execution_stale_monitor_digest")
            if str(monitor.get("current_stage") or "") in {"completed_pending_review", "completed", "cancelled"}:
                return _failure("dependency_aware_execution_terminal_monitor_state_blocked")
            if monitor.get("launch_digest") != launch.get("launch_digest") or control.get("launch_digest") != launch.get("launch_digest"):
                return _failure("dependency_aware_execution_lineage_blocked")
            prepared = inspect_prepared_development_execution_session(str(launch.get("source_session_id") or ""), runtime_root=runtime_root)
            if not prepared.get("ok") or prepared.get("session_digest") != launch.get("source_session_digest"):
                return _failure("dependency_aware_execution_original_plan_lineage_blocked")
            basis = _current_plan_revision_basis(launch_id, runtime_root=runtime_root)
            if not basis.get("ok"):
                return _failure(str(basis.get("status") or "dependency_aware_execution_plan_revision_blocked"))
            if not _expected_revision_matches(basis, expected_revision_digest):
                return _failure("dependency_aware_execution_stale_revision_digest")

            index = _load_index(launch_id, runtime_root)
            assessment_ids = list(index.get("assessment_ids") or [])
            latest: dict[str, Any] | None = None
            latest_review: dict[str, Any] | None = None
            if assessment_ids:
                latest = load_dependency_aware_execution_assessment(assessment_ids[-1], runtime_root=runtime_root)
                if not latest.get("ok"):
                    return _failure("dependency_aware_execution_history_integrity_blocked")
                review_index = _load_review_index(latest["assessment_id"], runtime_root)
                if review_index:
                    latest_review = load_dependency_aware_execution_review(review_index.get("review_id"), runtime_root=runtime_root)
                    if not latest_review.get("ok"):
                        return _failure("dependency_aware_execution_review_history_integrity_blocked")
                same = (
                    latest.get("launch_digest") == launch.get("launch_digest")
                    and latest.get("monitor_digest") == monitor.get("monitor_digest")
                    and latest.get("control_digest") == control.get("control_digest")
                    and latest.get("accepted_revision_digest", "") == basis.get("accepted_revision_digest", "")
                    and latest.get("dependency_spec_digest") == dependency_spec_digest
                )
                if same and latest_review is None:
                    replay = dict(latest)
                    replay["operation_status"] = "replayed"
                    return replay
                if latest_review is None:
                    return _failure("dependency_aware_execution_pending_review")
                if same:
                    return _failure("dependency_aware_execution_fresh_evidence_required")

            evaluation = _evaluate(dependencies)
            generation = int(index.get("generation") or 0) + 1
            identity = {
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "monitor_digest": monitor.get("monitor_digest"),
                "control_digest": control.get("control_digest"),
                "accepted_revision_digest": basis.get("accepted_revision_digest", ""),
                "dependency_spec_digest": dependency_spec_digest,
                "generation": generation,
            }
            assessment_id = f"dependency_assessment_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "dependency_aware_execution_assessment_ready_for_operator_review",
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
                "source_queue_digest": prepared.get("source_queue_digest"),
                "proposal_id": launch.get("proposal_id"),
                "project_reference": launch.get("project_reference"),
                "queue_item_id": launch.get("queue_item_id"),
                "plan_basis": basis.get("plan_basis"),
                "accepted_revision_id": basis.get("accepted_revision_id", ""),
                "accepted_revision_digest": basis.get("accepted_revision_digest", ""),
                "accepted_revision_generation": basis.get("accepted_revision_generation", 0),
                "revision_dependency_change_count": basis.get("revision_dependency_change_count", 0),
                "dependency_spec_digest": dependency_spec_digest,
                "dependencies": dependencies,
                "dependency_references": [row["dependency_reference"] for row in dependencies],
                "previous_assessment_id": latest.get("assessment_id", "") if latest else "",
                "previous_assessment_digest": latest.get("assessment_digest", "") if latest else "",
                "safe_boundary_pause_recommended": session_state == "active" and not evaluation["readiness_confirmable"],
                "operator_intervention_required": not evaluation["readiness_confirmable"],
                "fresh_resume_review_eligible": session_state == "paused" and evaluation["readiness_confirmable"],
                "readiness_confirmation_granted": False,
                "operation_status": "created",
                **evaluation,
                **_base(),
            }
            row = _sealed(row, "assessment_digest")
            path = _assessment_path(assessment_id, runtime_root)
            if path.exists():
                existing = load_dependency_aware_execution_assessment(assessment_id, runtime_root=runtime_root)
                if existing.get("assessment_digest") == row.get("assessment_digest"):
                    existing = dict(existing)
                    existing["operation_status"] = "replayed"
                    return existing
                return _failure("dependency_aware_execution_identity_collision")
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
        return _failure("dependency_aware_execution_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("dependency_aware_execution_internal_blocked", type(exc).__name__)


def review_dependency_aware_execution_assessment(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    disposition: str,
    runtime_root=None,
) -> dict[str, Any]:
    assessment_id = str(assessment_id or "").lower()
    decision = str(disposition or "").strip().lower().replace("-", "_").replace(" ", "_")
    if decision not in REVIEW_DISPOSITIONS:
        return _failure("dependency_aware_execution_review_disposition_blocked")
    try:
        with _lock(runtime_root):
            assessment = load_dependency_aware_execution_assessment(assessment_id, runtime_root=runtime_root)
            if not assessment.get("ok"):
                return _failure("dependency_aware_execution_review_assessment_blocked")
            if assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
                return _failure("dependency_aware_execution_review_stale_digest")
            existing_index = _load_review_index(assessment_id, runtime_root)
            if existing_index:
                existing = load_dependency_aware_execution_review(existing_index.get("review_id"), runtime_root=runtime_root)
                if not existing.get("ok"):
                    return _failure("dependency_aware_execution_review_integrity_blocked")
                if existing.get("disposition") == decision and existing.get("assessment_digest") == assessment.get("assessment_digest"):
                    replay = dict(existing)
                    replay["operation_status"] = "replayed"
                    return replay
                return _failure("dependency_aware_execution_review_conflict_blocked")
            if decision == "confirm_ready" and assessment.get("readiness_confirmable") is not True:
                return _failure("dependency_aware_execution_readiness_confirmation_blocked")

            launch_id = str(assessment.get("launch_id") or "")
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not launch.get("ok") or launch.get("launch_digest") != assessment.get("launch_digest"):
                return _failure("dependency_aware_execution_review_launch_lineage_blocked")
            if not monitor.get("ok") or monitor.get("monitor_digest") != assessment.get("monitor_digest"):
                return _failure("dependency_aware_execution_review_monitor_lineage_blocked")
            if not control.get("ok") or control.get("control_digest") != assessment.get("control_digest"):
                return _failure("dependency_aware_execution_review_control_lineage_blocked")
            if str(control.get("session_state") or "") not in {"active", "paused"}:
                return _failure("dependency_aware_execution_review_session_state_blocked")
            basis = _current_plan_revision_basis(launch_id, runtime_root=runtime_root)
            if not basis.get("ok") or basis.get("accepted_revision_digest", "") != assessment.get("accepted_revision_digest", ""):
                return _failure("dependency_aware_execution_review_plan_revision_lineage_blocked")

            identity = {
                "assessment_id": assessment_id,
                "assessment_digest": assessment.get("assessment_digest"),
                "disposition": decision,
            }
            review_id = f"dependency_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"dependency_aware_execution_{decision}_recorded",
                "review_id": review_id,
                "assessment_id": assessment_id,
                "assessment_digest": assessment.get("assessment_digest"),
                "launch_id": launch_id,
                "project_reference": assessment.get("project_reference"),
                "generation": assessment.get("generation"),
                "disposition": decision,
                "readiness_state": assessment.get("readiness_state"),
                "readiness_confirmed": decision == "confirm_ready",
                "assessment_held": decision == "hold",
                "assessment_rejected": decision == "reject",
                "assessment_changes_requested": decision == "request_changes",
                "confirmed_readiness_requires_fresh_execution_authority": decision == "confirm_ready",
                "confirmed_readiness_does_not_launch_session": decision == "confirm_ready",
                "confirmed_readiness_does_not_resume_session": decision == "confirm_ready",
                "reviewed_session_state": control.get("session_state"),
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "review_digest")
            path = _review_path(review_id, runtime_root)
            if path.exists():
                existing = load_dependency_aware_execution_review(review_id, runtime_root=runtime_root)
                if existing.get("review_digest") == row.get("review_digest"):
                    existing = dict(existing)
                    existing["operation_status"] = "replayed"
                    return existing
                return _failure("dependency_aware_execution_review_identity_collision")
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
        return _failure("dependency_aware_execution_review_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("dependency_aware_execution_review_internal_blocked", type(exc).__name__)


def _public_assessment(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "assessment_id", "assessment_digest", "generation", "launch_id", "launch_digest",
        "monitor_id", "monitor_digest", "monitor_generation", "control_id", "control_digest", "control_generation",
        "session_state_at_assessment", "source_session_id", "original_plan_digest", "source_schedule_digest",
        "source_queue_digest", "proposal_id", "project_reference", "queue_item_id", "plan_basis",
        "accepted_revision_id", "accepted_revision_digest", "accepted_revision_generation",
        "revision_dependency_change_count", "dependency_spec_digest", "dependencies", "dependency_references",
        "dependency_count", "satisfied_dependency_count", "unresolved_dependency_count", "blocking_dependency_count",
        "dependency_state_counts", "dependency_type_counts", "dependency_cycle_detected", "readiness_state",
        "readiness_confirmable", "all_required_dependencies_satisfied", "safe_boundary_pause_recommended",
        "operator_intervention_required", "fresh_resume_review_eligible", "readiness_confirmation_granted",
        "previous_assessment_id", "previous_assessment_digest", "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_dependency_aware_execution_assessment_digest"] = _digest(result)
    return result


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "review_id", "review_digest", "assessment_id", "assessment_digest", "launch_id",
        "project_reference", "generation", "disposition", "readiness_state", "readiness_confirmed",
        "assessment_held", "assessment_rejected", "assessment_changes_requested",
        "confirmed_readiness_requires_fresh_execution_authority", "confirmed_readiness_does_not_launch_session",
        "confirmed_readiness_does_not_resume_session", "reviewed_session_state", "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_dependency_aware_execution_review_digest"] = _digest(result)
    return result


def inspect_dependency_aware_execution_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_dependency_aware_execution_assessment(assessment_id, runtime_root=runtime_root)
    return _public_assessment(row) if row.get("ok") else row


def public_dependency_aware_execution_assessments(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _assessment_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("dependency_assessment_*.json"))[-MAX_ASSESSMENTS:]:
            row = load_dependency_aware_execution_assessment(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("dependency_aware_execution_assessment_list_blocked")
            rows.append(_public_assessment(row))
    rows.sort(key=lambda row: (str(row.get("launch_id") or ""), int(row.get("generation") or 0)))
    result = {
        "ok": True,
        "status": "dependency_aware_execution_assessment_list_ready",
        "assessment_count": len(rows),
        "assessments": rows,
        **_base(),
    }
    result["public_dependency_aware_execution_assessment_list_digest"] = _digest(result)
    return result


def public_dependency_aware_execution_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("dependency_review_*.json"))[-MAX_REVIEWS:]:
            row = load_dependency_aware_execution_review(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("dependency_aware_execution_review_list_blocked")
            rows.append(_public_review(row))
    rows.sort(key=lambda row: (str(row.get("launch_id") or ""), int(row.get("generation") or 0)))
    result = {
        "ok": True,
        "status": "dependency_aware_execution_review_list_ready",
        "review_count": len(rows),
        "reviews": rows,
        **_base(),
    }
    result["public_dependency_aware_execution_review_list_digest"] = _digest(result)
    return result


def dependency_aware_execution_response(row: Mapping[str, Any]) -> str:
    if row.get("ok") is not True:
        return f"Dependency-aware execution was blocked: {row.get('reason') or row.get('status') or 'invalid evidence'}."
    status = str(row.get("status") or "")
    if status == "dependency_aware_execution_assessment_ready_for_operator_review":
        return (
            f"Dependency assessment {row.get('assessment_id')} is ready for exact operator review with state "
            f"{row.get('readiness_state')}. Readiness grants no launch or resume authority."
        )
    if status.endswith("_recorded"):
        return (
            f"Dependency review {row.get('review_id')} recorded {row.get('disposition')}. "
            "Fresh separately governed authority is still required for execution or resume."
        )
    if status == "dependency_aware_execution_assessment_list_ready":
        return f"There are {row.get('assessment_count', 0)} dependency-aware execution assessments."
    if status == "dependency_aware_execution_review_list_ready":
        return f"There are {row.get('review_count', 0)} dependency-aware execution reviews."
    return f"Dependency-aware execution evidence recorded: {status}."


def process_dependency_aware_execution_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE.fullmatch(text)
    review = _REVIEW.fullmatch(text)
    show_one = _SHOW_ONE.fullmatch(text)
    if prepare:
        result = _public_assessment(prepare_dependency_aware_execution_assessment(
            prepare.group("launch").lower(),
            expected_launch_digest=prepare.group("launch_digest").lower(),
            expected_monitor_digest=prepare.group("monitor_digest").lower(),
            expected_control_digest=prepare.group("control_digest").lower(),
            expected_revision_digest=prepare.group("revision_digest").lower(),
            dependency_evidence=prepare.group("specs"),
            runtime_root=runtime_root,
        ))
    elif review:
        result = _public_review(review_dependency_aware_execution_assessment(
            review.group("assessment").lower(),
            expected_assessment_digest=review.group("digest").lower(),
            disposition=review.group("decision").lower().replace(" ", "_"),
            runtime_root=runtime_root,
        ))
    elif _SHOW_ALL.fullmatch(text):
        result = public_dependency_aware_execution_assessments(runtime_root=runtime_root)
    elif show_one:
        result = inspect_dependency_aware_execution_assessment(show_one.group("assessment").lower(), runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        result = public_dependency_aware_execution_reviews(runtime_root=runtime_root)
    else:
        return {"active": False}
    return {
        "active": True,
        "response": dependency_aware_execution_response(result),
        "dependency_aware_execution": result,
    }


def build_dependency_aware_execution_contract() -> dict[str, Any]:
    result = {
        "ok": True,
        "status": "dependency_aware_execution_contract_ready",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Dependency-Aware Execution",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "active_or_paused_session_required": True,
        "exact_dependency_evidence_required": True,
        "operator_review_required": True,
        "original_plan_immutable": True,
        "historical_receipts_immutable": True,
        "accepted_plan_revision_binding": True,
        "dependency_graph_cycle_detection": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "dependency_types": sorted(DEPENDENCY_TYPES),
        "dependency_states": sorted(DEPENDENCY_STATES),
        "readiness_states": sorted(READINESS_STATES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        **_base(),
    }
    result["dependency_aware_execution_contract_digest"] = _digest(result)
    return result
