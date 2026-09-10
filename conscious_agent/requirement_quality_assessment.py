from __future__ import annotations

"""Bounded requirement and quality assessment for supervised development.

v1234 evaluates content-free requirements and evidence against exact v1233
resource-admission lineage and, optionally, a sealed v1229 execution outcome.
Assessments and operator reviews are append-only evidence. They never approve,
apply, launch, resume, execute, test, mutate, learn, or write cognition.
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
from execution_session_authorization_bounded_launch import inspect_bounded_development_execution_session
from live_execution_monitoring_operator_intervention import inspect_live_execution_monitoring
from execution_session_pause_resume_cancel_recovery import inspect_execution_session_control
from supervised_work_dispatch_execution_session_preparation import inspect_prepared_development_execution_session
from resource_concurrency_governance import (
    load_resource_concurrency_governance_assessment,
    load_resource_concurrency_governance_review,
)
from execution_outcome_reflection_learning_integration import _load_outcome

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1234.8"
MAX_ASSESSMENTS = 100
MAX_REVIEWS = 200
MAX_REQUIREMENTS = 32
MAX_EVIDENCE = 96

REQUIREMENT_CATEGORIES = {
    "functional", "acceptance", "performance", "reliability", "security",
    "privacy", "usability", "compatibility", "rollback", "goal_alignment",
}
REQUIREMENT_PRIORITIES = {"required", "optional"}
CRITERION_STATES = {"defined", "ambiguous"}
EVIDENCE_TYPES = {"test", "inspection", "outcome", "receipt", "operator_observation", "static_analysis"}
EVIDENCE_STATES = {"supports", "partial", "contradicts", "missing", "stale", "inconclusive", "out_of_scope"}
CLASSIFICATIONS = {
    "satisfied", "partially_satisfied", "unsatisfied", "unverified",
    "contradictory", "out_of_scope", "blocked_by_missing_evidence",
}
REVIEW_DISPOSITIONS = {"accept_assessment", "hold", "reject", "request_remediation", "request_changes"}

AUTHORITY_FLAGS = {
    "requirement_quality_assessment_authorized": True,
    "requirement_quality_review_authorized": True,
    "assessment_is_work_approval_authority": False,
    "assessment_is_execution_authority": False,
    "remediation_proposal_is_execution_authority": False,
    "requirement_mutation_authorized": False,
    "acceptance_authorized": False,
    "apply_authorized": False,
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
    r"^prepare requirement and quality assessment for resource assessment "
    r"(?P<resource_assessment>resource_assessment_[a-f0-9]{24}) digest (?P<resource_assessment_digest>[a-f0-9]{64}) "
    r"resource review (?P<resource_review>resource_review_[a-f0-9]{24}) digest (?P<resource_review_digest>[a-f0-9]{64}) "
    r"with requirements (?P<requirements>[a-z0-9_:; -]+) and evidence (?P<evidence>[a-z0-9_:; -]+)[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review requirement and quality assessment (?P<decision>accept assessment|hold|reject|request remediation|request changes) "
    r"for assessment (?P<assessment>quality_assessment_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show requirement and quality assessments[.!?]*$", re.I)
_SHOW_ONE = re.compile(r"^show requirement and quality assessment (?P<assessment>quality_assessment_[a-f0-9]{24})[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show requirement and quality assessment reviews[.!?]*$", re.I)
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _assessment_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "requirement_quality_assessments"


def _assessment_path(assessment_id: str, runtime_root=None) -> Path:
    return _assessment_root(runtime_root) / f"{str(assessment_id or '').lower()}.json"


def _index_path(resource_assessment_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "requirement_quality_assessment_indexes" / f"{str(resource_assessment_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "requirement_quality_assessment_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(assessment_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "requirement_quality_assessment_review_indexes" / f"{str(assessment_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "requirement-quality-assessment.lock"
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
                raise TimeoutError("Timed out waiting for requirement-quality assessment lock")
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
        "exact_resource_review_required": True,
        "exact_outcome_required_when_supplied": True,
        "requirements_immutable": True,
        "historical_receipts_immutable": True,
        "evidence_does_not_run_tests": True,
        "assessment_does_not_approve_work": True,
        "fresh_separate_authority_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "queue_modified": False,
        "schedule_modified": False,
        "requirements_modified": False,
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
    row["requirement_quality_assessment_result_digest"] = _digest(row)
    return row


def _token(value: Any) -> str:
    result = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not _TOKEN.fullmatch(result):
        raise ValueError("invalid_code")
    return result


def _digest_value(value: Any, reason: str) -> str:
    result = str(value or "").strip().lower()
    if not _DIGEST.fullmatch(result):
        raise ValueError(reason)
    return result


def _parse_requirements(values: Iterable[Mapping[str, Any]] | str) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    if isinstance(values, str):
        for chunk in [part.strip() for part in values.split(";") if part.strip()]:
            parts = [part.strip() for part in chunk.split(":")]
            if len(parts) != 5:
                raise ValueError("invalid_requirement_spec")
            rows.append({"code": parts[0], "category": parts[1], "priority": parts[2], "criterion_state": parts[3], "criterion_digest": parts[4]})
    else:
        rows = [dict(item) for item in values]
    if not rows or len(rows) > MAX_REQUIREMENTS:
        raise ValueError("invalid_requirement_count")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        code = _token(raw.get("code"))
        category = _token(raw.get("category"))
        priority = _token(raw.get("priority"))
        criterion_state = _token(raw.get("criterion_state"))
        criterion_digest = _digest_value(raw.get("criterion_digest"), "invalid_criterion_digest")
        if code in seen:
            raise ValueError("duplicate_requirement_code")
        if category not in REQUIREMENT_CATEGORIES:
            raise ValueError("unsupported_requirement_category")
        if priority not in REQUIREMENT_PRIORITIES:
            raise ValueError("unsupported_requirement_priority")
        if criterion_state not in CRITERION_STATES:
            raise ValueError("unsupported_criterion_state")
        seen.add(code)
        normalized.append({
            "requirement_reference": f"requirement_{_digest({'code': code})[:24]}",
            "requirement_code_digest": _digest({"code": code}),
            "category": category,
            "priority": priority,
            "criterion_state": criterion_state,
            "criterion_digest": criterion_digest,
        })
    normalized.sort(key=lambda row: row["requirement_code_digest"])
    return normalized, _digest(normalized)


def _parse_evidence(values: Iterable[Mapping[str, Any]] | str, requirements: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    if isinstance(values, str):
        for chunk in [part.strip() for part in values.split(";") if part.strip()]:
            parts = [part.strip() for part in chunk.split(":")]
            if len(parts) != 5:
                raise ValueError("invalid_quality_evidence_spec")
            rows.append({"requirement_code": parts[0], "evidence_type": parts[1], "state": parts[2], "evidence_digest": parts[3], "source_digest": parts[4]})
    else:
        rows = [dict(item) for item in values]
    if not rows or len(rows) > MAX_EVIDENCE:
        raise ValueError("invalid_quality_evidence_count")
    code_map = {row["requirement_code_digest"]: row for row in requirements}
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in rows:
        code = _token(raw.get("requirement_code"))
        code_digest = _digest({"code": code})
        if code_digest not in code_map:
            raise ValueError("evidence_for_unknown_requirement")
        evidence_type = _token(raw.get("evidence_type"))
        state = _token(raw.get("state"))
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError("unsupported_evidence_type")
        if state not in EVIDENCE_STATES:
            raise ValueError("unsupported_evidence_state")
        evidence_digest = _digest_value(raw.get("evidence_digest"), "invalid_evidence_digest")
        source_digest = _digest_value(raw.get("source_digest"), "invalid_source_digest")
        key = (code_digest, evidence_type, evidence_digest)
        if key in seen:
            raise ValueError("duplicate_quality_evidence")
        seen.add(key)
        normalized.append({
            "requirement_reference": code_map[code_digest]["requirement_reference"],
            "requirement_code_digest": code_digest,
            "evidence_type": evidence_type,
            "evidence_state": state,
            "evidence_digest": evidence_digest,
            "source_receipt_digest": source_digest,
        })
    normalized.sort(key=lambda row: (row["requirement_code_digest"], row["evidence_type"], row["evidence_digest"]))
    return normalized, _digest(normalized)


def _classify(requirement: Mapping[str, Any], evidence: list[Mapping[str, Any]]) -> tuple[str, list[str]]:
    states = {str(row.get("evidence_state") or "") for row in evidence}
    reasons: list[str] = []
    if requirement.get("criterion_state") == "ambiguous":
        return "unverified", ["acceptance_criterion_ambiguous"]
    if not states or states <= {"missing", "stale", "inconclusive"}:
        if requirement.get("priority") == "required":
            return "blocked_by_missing_evidence", sorted(f"evidence_{state}" for state in states) or ["evidence_missing"]
        return "unverified", sorted(f"evidence_{state}" for state in states) or ["evidence_missing"]
    if "supports" in states and "contradicts" in states:
        return "contradictory", ["supporting_and_contradictory_evidence"]
    if "contradicts" in states:
        return "unsatisfied", ["contradictory_evidence"]
    if states == {"out_of_scope"}:
        return "out_of_scope", ["classified_out_of_scope"]
    if "supports" in states and states <= {"supports"}:
        return "satisfied", []
    if "supports" in states or "partial" in states:
        reasons.extend(f"evidence_{state}" for state in sorted(states - {"supports"}))
        return "partially_satisfied", reasons or ["partial_support"]
    if "out_of_scope" in states:
        return "out_of_scope", ["classified_out_of_scope"]
    return "unverified", ["evidence_inconclusive"]


def _evaluate(requirements: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in evidence:
        grouped.setdefault(row["requirement_code_digest"], []).append(row)
    results: list[dict[str, Any]] = []
    for req in requirements:
        classification, reason_codes = _classify(req, grouped.get(req["requirement_code_digest"], []))
        results.append({
            **req,
            "classification": classification,
            "reason_codes": reason_codes,
            "evidence_count": len(grouped.get(req["requirement_code_digest"], [])),
            "evidence_digest": _digest(grouped.get(req["requirement_code_digest"], [])),
        })
    counts = Counter(row["classification"] for row in results)
    required = [row for row in results if row["priority"] == "required"]
    severe = {"unsatisfied", "contradictory", "blocked_by_missing_evidence"}
    if any(row["classification"] in severe for row in required):
        overall = "requirements_not_met"
    elif any(row["classification"] in {"partially_satisfied", "unverified"} for row in required):
        overall = "requirements_partially_verified"
    elif required and all(row["classification"] == "satisfied" for row in required):
        overall = "requirements_satisfied_pending_operator_review"
    else:
        overall = "requirements_unverified"
    remediation_codes: list[str] = []
    if counts.get("unsatisfied"): remediation_codes.append("repair_unsatisfied_requirements")
    if counts.get("contradictory"): remediation_codes.append("resolve_contradictory_evidence")
    if counts.get("blocked_by_missing_evidence"): remediation_codes.append("collect_missing_evidence")
    if counts.get("unverified"): remediation_codes.append("clarify_or_verify_requirements")
    if counts.get("partially_satisfied"): remediation_codes.append("close_partial_coverage")
    categories = Counter(row["category"] for row in results if row["classification"] != "satisfied")
    return {
        "requirement_results": results,
        "classification_counts": dict(sorted(counts.items())),
        "overall_assessment_state": overall,
        "required_requirement_count": len(required),
        "all_required_requirements_satisfied": bool(required) and all(row["classification"] == "satisfied" for row in required),
        "quality_risk_categories": sorted(categories),
        "remaining_quality_risk_count": sum(categories.values()),
        "remediation_proposal_codes": remediation_codes,
        "remediation_proposal_required": bool(remediation_codes),
        "rollback_expectation_present": any(row["category"] == "rollback" for row in results),
        "goal_alignment_expectation_present": any(row["category"] == "goal_alignment" for row in results),
        "ambiguous_criterion_count": sum(row["criterion_state"] == "ambiguous" for row in results),
    }


def _load_index(resource_assessment_id: str, runtime_root=None) -> dict[str, Any]:
    return _read_json(_index_path(resource_assessment_id, runtime_root)) or {"generation": 0, "assessment_ids": []}


def _load_review_index(assessment_id: str, runtime_root=None) -> dict[str, Any] | None:
    return _read_json(_review_index_path(assessment_id, runtime_root))


def load_requirement_quality_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_assessment_path(assessment_id, runtime_root))
    if not row or not _valid(row, "requirement_quality_assessment_record_digest"):
        return _failure("requirement_quality_assessment_integrity_blocked")
    return row


def load_requirement_quality_assessment_review(review_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_review_path(review_id, runtime_root))
    if not row or not _valid(row, "requirement_quality_assessment_review_record_digest"):
        return _failure("requirement_quality_assessment_review_integrity_blocked")
    return row


def _resource_basis(resource_assessment_id: str, resource_assessment_digest: str, resource_review_id: str, resource_review_digest: str, runtime_root=None) -> tuple[dict[str, Any], dict[str, Any]]:
    assessment = load_resource_concurrency_governance_assessment(resource_assessment_id, runtime_root=runtime_root)
    review = load_resource_concurrency_governance_review(resource_review_id, runtime_root=runtime_root)
    if not assessment.get("ok") or assessment.get("assessment_digest") != str(resource_assessment_digest or "").lower():
        raise ValueError("stale_or_invalid_resource_assessment")
    if not review.get("ok") or review.get("review_digest") != str(resource_review_digest or "").lower():
        raise ValueError("stale_or_invalid_resource_review")
    if review.get("assessment_id") != assessment.get("assessment_id") or review.get("assessment_digest") != assessment.get("assessment_digest"):
        raise ValueError("resource_review_lineage_mismatch")
    return assessment, review


def prepare_requirement_quality_assessment(
    resource_assessment_id: str,
    *,
    expected_resource_assessment_digest: str,
    resource_review_id: str,
    expected_resource_review_digest: str,
    requirements: Iterable[Mapping[str, Any]] | str,
    evidence: Iterable[Mapping[str, Any]] | str,
    outcome_id: str = "",
    expected_outcome_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        requirement_rows, requirement_spec_digest = _parse_requirements(requirements)
        evidence_rows, evidence_spec_digest = _parse_evidence(evidence, requirement_rows)
        with _lock(runtime_root):
            resource_assessment, resource_review = _resource_basis(
                str(resource_assessment_id or "").lower(), expected_resource_assessment_digest,
                str(resource_review_id or "").lower(), expected_resource_review_digest, runtime_root,
            )
            launch_id = str(resource_assessment.get("launch_id") or "")
            launch = inspect_bounded_development_execution_session(launch_id, runtime_root=runtime_root)
            if not launch.get("ok") or launch.get("launch_digest") != resource_assessment.get("launch_digest"):
                return _failure("requirement_quality_launch_lineage_blocked")
            prepared = inspect_prepared_development_execution_session(str(resource_assessment.get("source_session_id") or ""), runtime_root=runtime_root)
            if not prepared.get("ok") or prepared.get("session_digest") != resource_assessment.get("original_plan_digest"):
                return _failure("requirement_quality_original_plan_lineage_blocked")
            outcome: dict[str, Any] | None = None
            subject_kind = "active_or_paused_session"
            if outcome_id:
                outcome = _load_outcome(str(outcome_id).lower(), runtime_root)
                if not outcome or outcome.get("outcome_digest") != str(expected_outcome_digest or "").lower():
                    return _failure("requirement_quality_outcome_lineage_blocked")
                if outcome.get("launch_id") != launch_id or outcome.get("launch_digest") != launch.get("launch_digest"):
                    return _failure("requirement_quality_cross_session_outcome_blocked")
                subject_kind = "sealed_execution_outcome"
            else:
                monitor = inspect_live_execution_monitoring(launch_id, runtime_root=runtime_root)
                control = inspect_execution_session_control(launch_id, runtime_root=runtime_root, reconcile_runtime=False)
                if not monitor.get("ok") or monitor.get("monitor_digest") != resource_assessment.get("monitor_digest"):
                    return _failure("requirement_quality_stale_monitor_digest")
                if not control.get("ok") or control.get("control_digest") != resource_assessment.get("control_digest"):
                    return _failure("requirement_quality_stale_control_digest")
                if str(control.get("session_state") or "") not in {"active", "paused"}:
                    return _failure("requirement_quality_session_state_blocked")

            index = _load_index(resource_assessment["assessment_id"], runtime_root)
            assessment_ids = list(index.get("assessment_ids") or [])
            latest = load_requirement_quality_assessment(assessment_ids[-1], runtime_root=runtime_root) if assessment_ids else None
            latest_review = None
            if latest:
                if not latest.get("ok"):
                    return _failure("requirement_quality_history_integrity_blocked")
                review_index = _load_review_index(latest["assessment_id"], runtime_root)
                if review_index:
                    latest_review = load_requirement_quality_assessment_review(review_index.get("review_id"), runtime_root=runtime_root)
                    if not latest_review.get("ok"):
                        return _failure("requirement_quality_review_history_integrity_blocked")
                same = (
                    latest.get("resource_assessment_digest") == resource_assessment.get("assessment_digest")
                    and latest.get("resource_review_digest") == resource_review.get("review_digest")
                    and latest.get("requirement_spec_digest") == requirement_spec_digest
                    and latest.get("evidence_spec_digest") == evidence_spec_digest
                    and latest.get("outcome_digest", "") == (outcome or {}).get("outcome_digest", "")
                )
                if same and latest_review is None:
                    return {**latest, "operation_status": "replayed"}
                if latest_review is None:
                    return _failure("requirement_quality_pending_review")
                if same:
                    return _failure("requirement_quality_fresh_evidence_required")

            evaluation = _evaluate(requirement_rows, evidence_rows)
            generation = int(index.get("generation") or 0) + 1
            identity = {
                "resource_assessment_digest": resource_assessment.get("assessment_digest"),
                "resource_review_digest": resource_review.get("review_digest"),
                "requirement_spec_digest": requirement_spec_digest,
                "evidence_spec_digest": evidence_spec_digest,
                "outcome_digest": (outcome or {}).get("outcome_digest", ""),
                "generation": generation,
            }
            assessment_id = f"quality_assessment_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "requirement_quality_assessment_ready_for_operator_review",
                "assessment_id": assessment_id,
                "assessment_digest": _digest(identity),
                "generation": generation,
                "subject_kind": subject_kind,
                "resource_assessment_id": resource_assessment.get("assessment_id"),
                "resource_assessment_digest": resource_assessment.get("assessment_digest"),
                "resource_review_id": resource_review.get("review_id"),
                "resource_review_digest": resource_review.get("review_digest"),
                "resource_review_disposition": resource_review.get("disposition"),
                "launch_id": launch_id,
                "launch_digest": launch.get("launch_digest"),
                "source_session_id": prepared.get("session_id"),
                "original_plan_digest": prepared.get("session_digest"),
                "project_reference": prepared.get("project_reference"),
                "queue_item_id": prepared.get("queue_item_id"),
                "outcome_id": (outcome or {}).get("outcome_id", ""),
                "outcome_digest": (outcome or {}).get("outcome_digest", ""),
                "outcome_type": (outcome or {}).get("outcome_type", ""),
                "achievement_classification": (outcome or {}).get("achievement_classification", ""),
                "requirement_count": len(requirement_rows),
                "evidence_count": len(evidence_rows),
                "requirement_spec_digest": requirement_spec_digest,
                "evidence_spec_digest": evidence_spec_digest,
                "requirements": requirement_rows,
                "evidence": evidence_rows,
                "previous_assessment_id": latest.get("assessment_id", "") if latest else "",
                "previous_assessment_digest": latest.get("assessment_digest", "") if latest else "",
                "operation_status": "created",
                **evaluation,
                **_base(),
            }
            row = _sealed(row, "requirement_quality_assessment_record_digest")
            _atomic_json(_assessment_path(assessment_id, runtime_root), row)
            _atomic_json(_index_path(resource_assessment["assessment_id"], runtime_root), {
                "resource_assessment_id": resource_assessment["assessment_id"],
                "generation": generation,
                "assessment_ids": (assessment_ids + [assessment_id])[-MAX_ASSESSMENTS:],
                "content_free": True,
            })
            return row
    except (OSError, TimeoutError, ValueError) as exc:
        return _failure("requirement_quality_assessment_blocked", str(exc))


def review_requirement_quality_assessment(
    assessment_id: str,
    *, expected_assessment_digest: str,
    disposition: str,
    runtime_root=None,
) -> dict[str, Any]:
    assessment_id = str(assessment_id or "").lower()
    disposition = str(disposition or "").strip().lower().replace(" ", "_").replace("-", "_")
    if disposition not in REVIEW_DISPOSITIONS:
        return _failure("requirement_quality_review_blocked", "unsupported_review_disposition")
    try:
        with _lock(runtime_root):
            assessment = load_requirement_quality_assessment(assessment_id, runtime_root=runtime_root)
            if not assessment.get("ok"):
                return _failure("requirement_quality_review_integrity_blocked")
            if assessment.get("assessment_digest") != str(expected_assessment_digest or "").lower():
                return _failure("requirement_quality_review_stale_assessment_digest")
            _resource_basis(
                assessment["resource_assessment_id"], assessment["resource_assessment_digest"],
                assessment["resource_review_id"], assessment["resource_review_digest"], runtime_root,
            )
            if assessment.get("outcome_id"):
                outcome = _load_outcome(assessment["outcome_id"], runtime_root)
                if not outcome or outcome.get("outcome_digest") != assessment.get("outcome_digest"):
                    return _failure("requirement_quality_review_outcome_integrity_blocked")
            existing_index = _load_review_index(assessment_id, runtime_root)
            if existing_index:
                existing = load_requirement_quality_assessment_review(existing_index.get("review_id"), runtime_root=runtime_root)
                if not existing.get("ok"):
                    return _failure("requirement_quality_review_history_integrity_blocked")
                if existing.get("disposition") == disposition:
                    return {**existing, "operation_status": "replayed"}
                return _failure("requirement_quality_conflicting_review")
            if disposition == "accept_assessment" and assessment.get("overall_assessment_state") != "requirements_satisfied_pending_operator_review":
                return _failure("requirement_quality_acceptance_blocked", "requirements_not_fully_satisfied")
            identity = {"assessment_id": assessment_id, "assessment_digest": assessment["assessment_digest"], "disposition": disposition}
            review_id = f"quality_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"requirement_quality_{disposition}_recorded",
                "review_id": review_id,
                "review_digest": _digest(identity),
                "assessment_id": assessment_id,
                "assessment_digest": assessment["assessment_digest"],
                "resource_assessment_id": assessment["resource_assessment_id"],
                "resource_review_id": assessment["resource_review_id"],
                "launch_id": assessment["launch_id"],
                "project_reference": assessment["project_reference"],
                "subject_kind": assessment["subject_kind"],
                "overall_assessment_state": assessment["overall_assessment_state"],
                "classification_counts": dict(assessment.get("classification_counts") or {}),
                "disposition": disposition,
                "assessment_accepted_as_operator_interpretation": disposition == "accept_assessment",
                "assessment_held": disposition == "hold",
                "assessment_rejected": disposition == "reject",
                "remediation_requested": disposition == "request_remediation",
                "changes_requested": disposition == "request_changes",
                "remediation_proposal_codes": list(assessment.get("remediation_proposal_codes") or []),
                "work_approved": False,
                "project_change_applied": False,
                "requirements_changed": False,
                "new_test_run_started": False,
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "requirement_quality_assessment_review_record_digest")
            _atomic_json(_review_path(review_id, runtime_root), row)
            _atomic_json(_review_index_path(assessment_id, runtime_root), {
                "assessment_id": assessment_id,
                "review_id": review_id,
                "review_digest": row["review_digest"],
                "content_free": True,
            })
            return row
    except (OSError, TimeoutError, ValueError) as exc:
        return _failure("requirement_quality_review_blocked", str(exc))


def _public_assessment(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "assessment_id", "assessment_digest", "generation", "subject_kind",
        "resource_assessment_id", "resource_assessment_digest", "resource_review_id", "resource_review_digest",
        "launch_id", "project_reference", "outcome_id", "outcome_digest", "outcome_type",
        "requirement_count", "evidence_count", "classification_counts", "overall_assessment_state",
        "all_required_requirements_satisfied", "quality_risk_categories", "remaining_quality_risk_count",
        "remediation_proposal_codes", "rollback_expectation_present", "goal_alignment_expectation_present",
        "ambiguous_criterion_count", "operator_review_required", "content_free", "runtime_records_external",
        "assessment_is_work_approval_authority", "assessment_is_execution_authority", "test_execution_authorized",
        "project_mutation_authorized", "cognition_write_authorized", "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "review_id", "review_digest", "assessment_id", "assessment_digest", "launch_id",
        "project_reference", "subject_kind", "overall_assessment_state", "classification_counts", "disposition",
        "assessment_accepted_as_operator_interpretation", "remediation_requested", "changes_requested",
        "work_approved", "project_change_applied", "new_test_run_started", "content_free",
        "assessment_is_work_approval_authority", "assessment_is_execution_authority", "test_execution_authorized",
        "project_mutation_authorized", "cognition_write_authorized", "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def inspect_requirement_quality_assessment(assessment_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = load_requirement_quality_assessment(assessment_id, runtime_root=runtime_root)
    return _public_assessment(row) if row.get("ok") else row


def public_requirement_quality_assessments(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _assessment_root(runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_ASSESSMENTS:]:
            row = _read_json(path)
            if row and _valid(row, "requirement_quality_assessment_record_digest"):
                rows.append(_public_assessment(row))
    return {"ok": True, "status": "requirement_quality_assessment_list_ready", "assessment_count": len(rows), "assessments": rows, **_base()}


def public_requirement_quality_assessment_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = _review_root(runtime_root)
    if root.exists():
        for path in sorted(root.glob("*.json"))[-MAX_REVIEWS:]:
            row = _read_json(path)
            if row and _valid(row, "requirement_quality_assessment_review_record_digest"):
                rows.append(_public_review(row))
    return {"ok": True, "status": "requirement_quality_assessment_review_list_ready", "review_count": len(rows), "reviews": rows, **_base()}


def requirement_quality_assessment_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Requirement and quality assessment was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "assessment_ready" in status:
        return (
            f"Prepared requirement and quality assessment {row.get('assessment_id')} with state "
            f"{row.get('overall_assessment_state')}. It is evidence only and grants no work approval or execution authority."
        )
    if "recorded" in status:
        return (
            f"Recorded requirement and quality review {row.get('disposition')} for {row.get('assessment_id')}. "
            "No work was approved, applied, launched, resumed, tested, or modified."
        )
    return "Requirement and quality assessment evidence is ready for inspection."


def process_requirement_quality_assessment_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _PREPARE.fullmatch(text)
    if match:
        row = prepare_requirement_quality_assessment(
            match.group("resource_assessment"),
            expected_resource_assessment_digest=match.group("resource_assessment_digest"),
            resource_review_id=match.group("resource_review"),
            expected_resource_review_digest=match.group("resource_review_digest"),
            requirements=match.group("requirements"), evidence=match.group("evidence"), runtime_root=runtime_root,
        )
        return {"active": True, "response": requirement_quality_assessment_response(row), "requirement_quality_assessment": row}
    match = _REVIEW.fullmatch(text)
    if match:
        row = review_requirement_quality_assessment(
            match.group("assessment"), expected_assessment_digest=match.group("digest"),
            disposition=match.group("decision"), runtime_root=runtime_root,
        )
        return {"active": True, "response": requirement_quality_assessment_response(row), "requirement_quality_assessment": row}
    if _SHOW_ALL.fullmatch(text):
        row = public_requirement_quality_assessments(runtime_root=runtime_root)
        return {"active": True, "response": requirement_quality_assessment_response(row), "requirement_quality_assessment": row}
    match = _SHOW_ONE.fullmatch(text)
    if match:
        row = inspect_requirement_quality_assessment(match.group("assessment"), runtime_root=runtime_root)
        return {"active": True, "response": requirement_quality_assessment_response(row), "requirement_quality_assessment": row}
    if _SHOW_REVIEWS.fullmatch(text):
        row = public_requirement_quality_assessment_reviews(runtime_root=runtime_root)
        return {"active": True, "response": requirement_quality_assessment_response(row), "requirement_quality_assessment": row}
    return {"active": False}


def build_requirement_quality_assessment_contract() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "requirement_quality_assessment_contract_ready",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Requirement and Quality Assessment",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "exact_resource_assessment_and_review_binding": True,
        "optional_sealed_outcome_binding": True,
        "structured_requirements_and_acceptance_criteria": True,
        "evidence_linkage_is_digest_bound": True,
        "deterministic_requirement_classification": True,
        "quality_risk_and_uncertainty_visible": True,
        "rollback_and_goal_alignment_visible": True,
        "remediation_proposal_only": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "requirement_categories": sorted(REQUIREMENT_CATEGORIES),
        "evidence_types": sorted(EVIDENCE_TYPES),
        "evidence_states": sorted(EVIDENCE_STATES),
        "classifications": sorted(CLASSIFICATIONS),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        "max_requirements": MAX_REQUIREMENTS,
        "max_evidence": MAX_EVIDENCE,
        **_base(),
    }
