from __future__ import annotations

"""Bounded, operator-reviewed revisions to an approved execution plan.

v1231 prepares append-only, content-free revision evidence when sealed reality
for an active or paused v1226-v1228 execution session no longer matches the
approved v1225 plan. A proposal and every review are evidence only. They do not
launch, resume, pause, cancel, contact providers, execute commands or tests,
materialize workspaces, mutate projects/queues/schedules/source/cognition, retry
work, reuse authority, install, promote, certify, release, or manage models.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from supervised_work_dispatch_execution_session_preparation import inspect_prepared_development_execution_session
from execution_session_authorization_bounded_launch import inspect_bounded_development_execution_session
from live_execution_monitoring_operator_intervention import inspect_live_execution_monitoring
from execution_session_pause_resume_cancel_recovery import inspect_execution_session_control

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1231.8"
MAX_REVISION_PROPOSALS = 100
MAX_REVISION_REVIEWS = 200
MAX_CHANGE_CODES = 8

VERIFIED_CHANGE_CODES = {
    "dependency_state_changed",
    "requirement_interpretation_changed",
    "environment_capability_changed",
    "test_evidence_changed",
    "rollback_precondition_changed",
    "resource_constraint_changed",
    "risk_profile_changed",
    "operator_goal_clarified",
    "contradictory_evidence",
    "scope_contraction_required",
    "scope_expansion_required",
    "unknown_verified_change",
}
REVIEW_DISPOSITIONS = {"accept", "reject", "defer", "request_changes"}
CONTRADICTORY_CHANGE_PAIRS = {
    frozenset({"scope_contraction_required", "scope_expansion_required"}),
}
AUTHORITY_FLAGS = {
    "revision_evidence_authorized": True,
    "revision_review_authorized": True,
    "scope_expansion_authorized": False,
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
    r"^prepare dynamic execution plan revision for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24}) digest (?P<launch_digest>[a-f0-9]{64}) "
    r"monitor digest (?P<monitor_digest>[a-f0-9]{64}) control digest (?P<control_digest>[a-f0-9]{64}) "
    r"with verified changes (?P<codes>[a-z0-9_, -]+)[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review dynamic execution plan revision (?P<decision>accept|reject|defer|request changes) "
    r"for revision (?P<revision>plan_revision_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show dynamic execution plan revisions[.!?]*$", re.I)
_SHOW_ONE = re.compile(r"^show dynamic execution plan revision (?P<revision>plan_revision_[a-f0-9]{24})[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show dynamic execution plan revision reviews[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _proposal_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "dynamic_execution_plan_revisions"


def _proposal_path(revision_id: str, runtime_root=None) -> Path:
    return _proposal_root(runtime_root) / f"{str(revision_id or '').lower()}.json"


def _index_path(launch_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "dynamic_execution_plan_revision_indexes" / f"{str(launch_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "dynamic_execution_plan_revision_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(revision_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "dynamic_execution_plan_revision_review_indexes" / f"{str(revision_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "dynamic-execution-plan-revision.lock"
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
                raise TimeoutError("Timed out waiting for dynamic execution plan revision lock")
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
        "verified_reality_required": True,
        "original_plan_immutable": True,
        "historical_receipts_immutable": True,
        "revision_is_not_execution_authority": True,
        "accepted_revision_is_not_execution_authority": True,
        "fresh_launch_authorization_required": True,
        "fresh_resume_authorization_required": True,
        "separate_step_authority_required": True,
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
    row["dynamic_execution_plan_revision_result_digest"] = _digest(row)
    return row


def _normalize_codes(values: Iterable[str] | str) -> tuple[str, ...]:
    source = values.replace("-", "_").split(",") if isinstance(values, str) else values
    result: list[str] = []
    for value in source:
        token = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
        if not token:
            continue
        if token not in VERIFIED_CHANGE_CODES:
            raise ValueError(f"unsupported_verified_change_code:{token}")
        if token not in result:
            result.append(token)
    if not result:
        raise ValueError("verified_change_codes_required")
    if len(result) > MAX_CHANGE_CODES:
        raise ValueError("verified_change_code_limit_exceeded")
    if any(pair.issubset(result) for pair in CONTRADICTORY_CHANGE_PAIRS):
        raise ValueError("contradictory_verified_change_codes")
    return tuple(sorted(result))


def _explanation(codes: tuple[str, ...]) -> dict[str, Any]:
    assumptions: set[str] = set()
    scope: set[str] = set()
    dependencies: set[str] = set()
    risks: set[str] = set()
    tests: set[str] = set()
    rollback: set[str] = set()
    insufficiency: set[str] = set()
    mapping = {
        "dependency_state_changed": ("dependency_assumption_invalid", "split_at_dependency_boundary", "dependency_review_changed", "dependency_blockage", "rerun_dependency_integration_tests", "review_dependency_rollback_order", "approved_dependency_state_is_stale"),
        "requirement_interpretation_changed": ("requirement_assumption_invalid", "narrow_or_restate_scope", "requirement_source_changed", "requirement_scope_mismatch", "update_acceptance_tests", "preserve_original_scope_rollback_point", "approved_requirement_interpretation_is_stale"),
        "environment_capability_changed": ("environment_assumption_invalid", "defer_incompatible_work", "environment_dependency_changed", "environment_mismatch", "update_compatibility_tests", "preserve_environment_recovery_path", "approved_environment_capability_is_stale"),
        "test_evidence_changed": ("test_assumption_invalid", "add_validation_scope", "test_adapter_review_changed", "test_coverage_gap", "broaden_focused_and_regression_tests", "require_test_verified_rollback", "approved_test_plan_no_longer_covers_verified_risk"),
        "rollback_precondition_changed": ("rollback_assumption_invalid", "limit_mutation_until_rollback_ready", "rollback_dependency_changed", "rollback_path_unverified", "add_rollback_precondition_tests", "rebuild_rollback_evidence", "approved_rollback_plan_is_not_current"),
        "resource_constraint_changed": ("resource_assumption_invalid", "reduce_or_sequence_work", "resource_availability_changed", "resource_exhaustion", "add_resource_boundary_tests", "preserve_partial_work_rollback", "approved_resource_budget_is_stale"),
        "risk_profile_changed": ("risk_assumption_invalid", "reduce_or_gate_risky_scope", "risk_dependency_review_changed", "risk_profile_increased", "add_risk_regression_tests", "strengthen_rollback_gate", "approved_risk_review_is_stale"),
        "operator_goal_clarified": ("goal_assumption_clarified", "realign_scope_to_goal", "goal_dependency_review_changed", "goal_misalignment", "update_goal_acceptance_tests", "retain_preclarification_rollback_point", "approved_plan_does_not_reflect_current_operator_goal"),
        "contradictory_evidence": ("evidence_assumption_conflicted", "pause_conflicting_scope", "evidence_resolution_dependency", "contradictory_evidence_risk", "add_disambiguation_tests", "preserve_last_verified_rollback_point", "approved_plan_relies_on_unresolved_contradictory_evidence"),
        "scope_contraction_required": ("scope_assumption_too_broad", "contract_scope", "remove_unneeded_dependencies", "excess_scope_risk", "focus_tests_on_retained_scope", "retain_removed_scope_rollback_point", "approved_scope_exceeds_verified_need"),
        "scope_expansion_required": ("scope_assumption_too_narrow", "propose_scope_expansion_only", "add_proposed_dependencies", "scope_expansion_risk", "add_tests_for_proposed_scope", "require_new_rollback_plan_before_expansion", "approved_scope_cannot_satisfy_verified_need"),
        "unknown_verified_change": ("unclassified_assumption_invalid", "hold_scope_for_operator_review", "dependency_state_uncertain", "unknown_change_risk", "add_evidence_resolution_tests", "preserve_current_rollback_point", "approved_plan_cannot_account_for_verified_unclassified_change"),
    }
    for code in codes:
        a, s, d, r, t, rb, why = mapping[code]
        assumptions.add(a); scope.add(s); dependencies.add(d); risks.add(r); tests.add(t); rollback.add(rb); insufficiency.add(why)
    uncertainty = "high" if {"contradictory_evidence", "unknown_verified_change"}.intersection(codes) else "medium"
    return {
        "changed_assumption_codes": sorted(assumptions),
        "proposed_scope_change_codes": sorted(scope),
        "new_or_changed_dependency_codes": sorted(dependencies),
        "risk_codes": sorted(risks),
        "test_implication_codes": sorted(tests),
        "rollback_implication_codes": sorted(rollback),
        "goal_alignment": "preserved_with_operator_revalidation",
        "uncertainty": uncertainty,
        "original_plan_insufficiency_codes": sorted(insufficiency),
    }


def _load_index(launch_id: str, runtime_root=None) -> dict[str, Any]:
    path = _index_path(launch_id, runtime_root)
    if not path.is_file():
        return {"launch_id": launch_id, "revision_ids": [], "generation": 0}
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("launch_id") != launch_id:
        raise ValueError("invalid_revision_index")
    return row


def _load_review_index(revision_id: str, runtime_root=None) -> dict[str, Any] | None:
    path = _review_index_path(revision_id, runtime_root)
    if not path.is_file():
        return None
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("revision_id") != revision_id:
        raise ValueError("invalid_revision_review_index")
    return row


def load_dynamic_execution_plan_revision(revision_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _proposal_path(revision_id, runtime_root)
    if not path.is_file():
        return _failure("dynamic_execution_plan_revision_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("revision_id") != str(revision_id or "").lower() or not _valid(row, "revision_digest"):
        return _failure("dynamic_execution_plan_revision_integrity_blocked")
    return row


def load_dynamic_execution_plan_revision_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    path = _review_path(review_id, runtime_root)
    if not path.is_file():
        return _failure("dynamic_execution_plan_revision_review_not_found")
    row = _read_json(path)
    if not isinstance(row, dict) or row.get("review_id") != str(review_id or "").lower() or not _valid(row, "review_digest"):
        return _failure("dynamic_execution_plan_revision_review_integrity_blocked")
    return row


def _accepted_scope_direction(launch_id: str, runtime_root=None) -> set[str]:
    directions: set[str] = set()
    index = _load_index(launch_id, runtime_root)
    for revision_id in index.get("revision_ids", []):
        proposal = load_dynamic_execution_plan_revision(revision_id, runtime_root=runtime_root)
        if not proposal.get("ok"):
            raise ValueError("revision_history_integrity_blocked")
        review_index = _load_review_index(revision_id, runtime_root)
        if not review_index:
            continue
        review = load_dynamic_execution_plan_revision_review(review_index.get("review_id"), runtime_root=runtime_root)
        if not review.get("ok"):
            raise ValueError("revision_review_history_integrity_blocked")
        if review.get("disposition") == "accept":
            codes = set(proposal.get("verified_change_codes") or [])
            if "scope_contraction_required" in codes: directions.add("contraction")
            if "scope_expansion_required" in codes: directions.add("expansion")
    return directions


def prepare_dynamic_execution_plan_revision(
    launch_id: str,
    *,
    expected_launch_digest: str,
    expected_monitor_digest: str,
    expected_control_digest: str,
    verified_change_codes: Iterable[str] | str,
    runtime_root=None,
) -> dict[str, Any]:
    launch_id = str(launch_id or "").lower()
    try:
        codes = _normalize_codes(verified_change_codes)
    except ValueError as exc:
        return _failure("dynamic_execution_plan_revision_change_codes_blocked", str(exc))
    try:
        with _lock(runtime_root):
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            if not launch.get("ok"):
                return _failure("dynamic_execution_plan_revision_launch_evidence_unavailable")
            if launch.get("launch_digest") != str(expected_launch_digest or "").lower():
                return _failure("dynamic_execution_plan_revision_stale_launch_digest")
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not control.get("ok"):
                return _failure("dynamic_execution_plan_revision_control_evidence_unavailable")
            if control.get("control_digest") != str(expected_control_digest or "").lower():
                return _failure("dynamic_execution_plan_revision_stale_control_digest")
            session_state = str(control.get("session_state") or "")
            if session_state not in {"active", "paused"}:
                return _failure("dynamic_execution_plan_revision_session_state_blocked", session_state)
            monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            if not monitor.get("ok"):
                return _failure("dynamic_execution_plan_revision_monitor_evidence_unavailable")
            if monitor.get("monitor_digest") != str(expected_monitor_digest or "").lower():
                return _failure("dynamic_execution_plan_revision_stale_monitor_digest")
            if str(monitor.get("current_stage") or "") in {"completed_pending_review", "completed", "cancelled"}:
                return _failure("dynamic_execution_plan_revision_terminal_monitor_state_blocked")
            if monitor.get("launch_digest") != launch.get("launch_digest") or control.get("launch_digest") != launch.get("launch_digest"):
                return _failure("dynamic_execution_plan_revision_lineage_blocked")
            source_session_id = str(launch.get("source_session_id") or "")
            prepared = inspect_prepared_development_execution_session(source_session_id, runtime_root=runtime_root)
            if not prepared.get("ok"):
                return _failure("dynamic_execution_plan_revision_original_plan_unavailable")
            if prepared.get("session_digest") != launch.get("source_session_digest"):
                return _failure("dynamic_execution_plan_revision_original_plan_lineage_blocked")

            index = _load_index(launch_id, runtime_root)
            revision_ids = list(index.get("revision_ids") or [])
            latest: dict[str, Any] | None = None
            latest_review: dict[str, Any] | None = None
            if revision_ids:
                latest = load_dynamic_execution_plan_revision(revision_ids[-1], runtime_root=runtime_root)
                if not latest.get("ok"):
                    return _failure("dynamic_execution_plan_revision_history_integrity_blocked")
                review_index = _load_review_index(latest["revision_id"], runtime_root)
                if review_index:
                    latest_review = load_dynamic_execution_plan_revision_review(review_index.get("review_id"), runtime_root=runtime_root)
                    if not latest_review.get("ok"):
                        return _failure("dynamic_execution_plan_revision_review_history_integrity_blocked")
                same = (
                    latest.get("launch_digest") == launch.get("launch_digest")
                    and latest.get("monitor_digest") == monitor.get("monitor_digest")
                    and latest.get("control_digest") == control.get("control_digest")
                    and tuple(latest.get("verified_change_codes") or []) == codes
                )
                if same and latest_review is None:
                    replay = dict(latest); replay["operation_status"] = "replayed"; return replay
                if latest_review is None:
                    return _failure("dynamic_execution_plan_revision_pending_review")
                if same:
                    return _failure("dynamic_execution_plan_revision_fresh_evidence_required")

            accepted_directions = _accepted_scope_direction(launch_id, runtime_root)
            if ("contraction" in accepted_directions and "scope_expansion_required" in codes) or (
                "expansion" in accepted_directions and "scope_contraction_required" in codes
            ):
                return _failure("dynamic_execution_plan_revision_contradiction_blocked")

            generation = int(index.get("generation") or 0) + 1
            identity = {
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "monitor_digest": monitor.get("monitor_digest"),
                "control_digest": control.get("control_digest"),
                "verified_change_codes": list(codes),
                "generation": generation,
            }
            revision_id = f"plan_revision_{_digest(identity)[:24]}"
            explanation = _explanation(codes)
            row = {
                "ok": True,
                "status": "dynamic_execution_plan_revision_ready_for_operator_review",
                "revision_id": revision_id,
                "generation": generation,
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "monitor_id": monitor.get("monitor_id"),
                "monitor_digest": monitor.get("monitor_digest"),
                "monitor_generation": monitor.get("generation"),
                "control_id": control.get("control_id"),
                "control_digest": control.get("control_digest"),
                "control_generation": control.get("generation"),
                "session_state_at_proposal": session_state,
                "source_session_id": prepared.get("session_id"),
                "original_plan_digest": prepared.get("session_digest"),
                "source_schedule_digest": prepared.get("source_schedule_digest"),
                "source_queue_digest": prepared.get("source_queue_digest"),
                "proposal_id": launch.get("proposal_id"),
                "project_reference": launch.get("project_reference"),
                "queue_item_id": launch.get("queue_item_id"),
                "verified_change_codes": list(codes),
                "scope_expansion_proposed": "scope_expansion_required" in codes,
                "previous_revision_id": latest.get("revision_id", "") if latest else "",
                "previous_revision_digest": latest.get("revision_digest", "") if latest else "",
                "operation_status": "created",
                **explanation,
                **_base(),
            }
            row = _sealed(row, "revision_digest")
            path = _proposal_path(revision_id, runtime_root)
            if path.exists():
                existing = load_dynamic_execution_plan_revision(revision_id, runtime_root=runtime_root)
                if existing.get("revision_digest") == row.get("revision_digest"):
                    existing = dict(existing); existing["operation_status"] = "replayed"; return existing
                return _failure("dynamic_execution_plan_revision_identity_collision")
            _atomic_json(path, row)
            revision_ids.append(revision_id)
            _atomic_json(_index_path(launch_id, runtime_root), {
                "launch_id": launch_id,
                "revision_ids": revision_ids[-MAX_REVISION_PROPOSALS:],
                "generation": generation,
                "latest_revision_id": revision_id,
                "latest_revision_digest": row["revision_digest"],
            })
            return row
    except TimeoutError as exc:
        return _failure("dynamic_execution_plan_revision_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("dynamic_execution_plan_revision_internal_blocked", type(exc).__name__)


def review_dynamic_execution_plan_revision(
    revision_id: str,
    *,
    expected_revision_digest: str,
    disposition: str,
    runtime_root=None,
) -> dict[str, Any]:
    revision_id = str(revision_id or "").lower()
    decision = str(disposition or "").strip().lower().replace(" ", "_").replace("-", "_")
    if decision not in REVIEW_DISPOSITIONS:
        return _failure("dynamic_execution_plan_revision_review_disposition_blocked")
    try:
        with _lock(runtime_root):
            proposal = load_dynamic_execution_plan_revision(revision_id, runtime_root=runtime_root)
            if not proposal.get("ok"):
                return _failure("dynamic_execution_plan_revision_review_proposal_blocked")
            if proposal.get("revision_digest") != str(expected_revision_digest or "").lower():
                return _failure("dynamic_execution_plan_revision_review_stale_digest")
            existing_index = _load_review_index(revision_id, runtime_root)
            if existing_index:
                existing = load_dynamic_execution_plan_revision_review(existing_index.get("review_id"), runtime_root=runtime_root)
                if not existing.get("ok"):
                    return _failure("dynamic_execution_plan_revision_review_integrity_blocked")
                if existing.get("disposition") == decision and existing.get("revision_digest") == proposal.get("revision_digest"):
                    replay = dict(existing); replay["operation_status"] = "replayed"; return replay
                return _failure("dynamic_execution_plan_revision_review_conflict_blocked")

            launch_id = proposal.get("launch_id")
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
            if not launch.get("ok") or launch.get("launch_digest") != proposal.get("launch_digest"):
                return _failure("dynamic_execution_plan_revision_review_launch_lineage_blocked")
            if not control.get("ok") or str(control.get("session_state") or "") not in {"active", "paused"}:
                return _failure("dynamic_execution_plan_revision_review_session_state_blocked")

            identity = {"revision_id": revision_id, "revision_digest": proposal.get("revision_digest"), "disposition": decision}
            review_id = f"plan_revision_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"dynamic_execution_plan_revision_{decision}_recorded",
                "review_id": review_id,
                "revision_id": revision_id,
                "revision_digest": proposal.get("revision_digest"),
                "launch_id": launch_id,
                "project_reference": proposal.get("project_reference"),
                "generation": proposal.get("generation"),
                "disposition": decision,
                "revision_accepted": decision == "accept",
                "revision_rejected": decision == "reject",
                "revision_deferred": decision == "defer",
                "revision_changes_requested": decision == "request_changes",
                "accepted_revision_requires_fresh_future_authority": decision == "accept",
                "accepted_revision_does_not_resume_session": decision == "accept",
                "accepted_revision_does_not_replace_original_plan": decision == "accept",
                "reviewed_session_state": control.get("session_state"),
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "review_digest")
            path = _review_path(review_id, runtime_root)
            if path.exists():
                existing = load_dynamic_execution_plan_revision_review(review_id, runtime_root=runtime_root)
                if existing.get("review_digest") == row.get("review_digest"):
                    existing = dict(existing); existing["operation_status"] = "replayed"; return existing
                return _failure("dynamic_execution_plan_revision_review_identity_collision")
            _atomic_json(path, row)
            _atomic_json(_review_index_path(revision_id, runtime_root), {
                "revision_id": revision_id,
                "revision_digest": proposal.get("revision_digest"),
                "review_id": review_id,
                "review_digest": row["review_digest"],
                "disposition": decision,
            })
            return row
    except TimeoutError as exc:
        return _failure("dynamic_execution_plan_revision_review_lock_timeout", str(exc))
    except Exception as exc:
        return _failure("dynamic_execution_plan_revision_review_internal_blocked", type(exc).__name__)


def _public_proposal(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "revision_id", "revision_digest", "generation", "launch_id", "launch_digest",
        "monitor_id", "monitor_digest", "monitor_generation", "control_id", "control_digest", "control_generation",
        "session_state_at_proposal", "source_session_id", "original_plan_digest", "source_schedule_digest",
        "source_queue_digest", "proposal_id", "project_reference", "queue_item_id", "verified_change_codes",
        "scope_expansion_proposed", "previous_revision_id", "previous_revision_digest", "changed_assumption_codes",
        "proposed_scope_change_codes", "new_or_changed_dependency_codes", "risk_codes", "test_implication_codes",
        "rollback_implication_codes", "goal_alignment", "uncertainty", "original_plan_insufficiency_codes",
        "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_dynamic_execution_plan_revision_digest"] = _digest(result)
    return result


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok", "status", "review_id", "review_digest", "revision_id", "revision_digest", "launch_id",
        "project_reference", "generation", "disposition", "revision_accepted", "revision_rejected",
        "revision_deferred", "revision_changes_requested", "accepted_revision_requires_fresh_future_authority",
        "accepted_revision_does_not_resume_session", "accepted_revision_does_not_replace_original_plan",
        "reviewed_session_state", "operation_status",
    }
    result = {key: row.get(key) for key in allowed if key in row}
    result.update(_base())
    result["public_dynamic_execution_plan_revision_review_digest"] = _digest(result)
    return result


def inspect_dynamic_execution_plan_revision(revision_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_dynamic_execution_plan_revision(revision_id, runtime_root=runtime_root)
    return _public_proposal(row) if row.get("ok") else row


def public_dynamic_execution_plan_revisions(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _proposal_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("plan_revision_*.json"))[-MAX_REVISION_PROPOSALS:]:
            row = load_dynamic_execution_plan_revision(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("dynamic_execution_plan_revision_list_blocked")
            rows.append(_public_proposal(row))
    result = {"ok": True, "status": "dynamic_execution_plan_revision_list_ready", "revision_count": len(rows), "revisions": rows, **_base()}
    result["public_dynamic_execution_plan_revision_list_digest"] = _digest(result)
    return result


def public_dynamic_execution_plan_revision_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if root.is_dir():
        for path in sorted(root.glob("plan_revision_review_*.json"))[-MAX_REVISION_REVIEWS:]:
            row = load_dynamic_execution_plan_revision_review(path.stem, runtime_root=runtime_root)
            if not row.get("ok"):
                return _failure("dynamic_execution_plan_revision_review_list_blocked")
            rows.append(_public_review(row))
    result = {"ok": True, "status": "dynamic_execution_plan_revision_review_list_ready", "review_count": len(rows), "reviews": rows, **_base()}
    result["public_dynamic_execution_plan_revision_review_list_digest"] = _digest(result)
    return result


def dynamic_execution_plan_revision_response(row: Mapping[str, Any]) -> str:
    if row.get("ok") is not True:
        return f"Dynamic execution plan revision was blocked: {row.get('reason') or row.get('status') or 'invalid evidence'}."
    status = str(row.get("status") or "")
    if status == "dynamic_execution_plan_revision_ready_for_operator_review":
        return f"Revision {row.get('revision_id')} is ready for exact operator review. The original plan remains immutable and no execution or resume authority was granted."
    if status.endswith("_recorded"):
        return f"Revision review {row.get('review_id')} recorded {row.get('disposition')}. Fresh separately governed authority is still required for any later execution or resume."
    if status == "dynamic_execution_plan_revision_list_ready":
        return f"There are {row.get('revision_count', 0)} dynamic execution plan revisions."
    if status == "dynamic_execution_plan_revision_review_list_ready":
        return f"There are {row.get('review_count', 0)} dynamic execution plan revision reviews."
    return f"Dynamic execution plan revision recorded: {status}."


def process_dynamic_execution_plan_revision_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE.fullmatch(text)
    review = _REVIEW.fullmatch(text)
    show_one = _SHOW_ONE.fullmatch(text)
    if prepare:
        result = _public_proposal(prepare_dynamic_execution_plan_revision(
            prepare.group("launch").lower(),
            expected_launch_digest=prepare.group("launch_digest").lower(),
            expected_monitor_digest=prepare.group("monitor_digest").lower(),
            expected_control_digest=prepare.group("control_digest").lower(),
            verified_change_codes=prepare.group("codes"),
            runtime_root=runtime_root,
        ))
    elif review:
        result = _public_review(review_dynamic_execution_plan_revision(
            review.group("revision").lower(),
            expected_revision_digest=review.group("digest").lower(),
            disposition=review.group("decision").lower().replace(" ", "_"),
            runtime_root=runtime_root,
        ))
    elif _SHOW_ALL.fullmatch(text):
        result = public_dynamic_execution_plan_revisions(runtime_root=runtime_root)
    elif show_one:
        result = inspect_dynamic_execution_plan_revision(show_one.group("revision").lower(), runtime_root=runtime_root)
    elif _SHOW_REVIEWS.fullmatch(text):
        result = public_dynamic_execution_plan_revision_reviews(runtime_root=runtime_root)
    else:
        return {"active": False}
    return {"active": True, "response": dynamic_execution_plan_revision_response(result), "dynamic_execution_plan_revision": result}


def build_dynamic_execution_plan_revision_contract() -> dict[str, Any]:
    result = {
        "ok": True,
        "status": "dynamic_execution_plan_revision_contract_ready",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Dynamic Execution Plan Revision with Operator Review",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "active_or_paused_session_required": True,
        "verified_reality_required": True,
        "operator_review_required": True,
        "original_plan_immutable": True,
        "historical_receipts_immutable": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "proposal_explanation_fields": [
            "changed_assumption_codes", "proposed_scope_change_codes", "new_or_changed_dependency_codes",
            "risk_codes", "test_implication_codes", "rollback_implication_codes", "goal_alignment",
            "uncertainty", "original_plan_insufficiency_codes",
        ],
        "verified_change_codes": sorted(VERIFIED_CHANGE_CODES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        **_base(),
    }
    result["dynamic_execution_plan_revision_contract_digest"] = _digest(result)
    return result
