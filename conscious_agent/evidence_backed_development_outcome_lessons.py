from __future__ import annotations

"""Evidence-backed lessons from supervised development outcomes.

v1235 derives bounded, content-free, project-scoped lesson candidates from an
exact v1234 requirement/quality assessment and its exact operator review.
Candidates, reviews, and later-evidence reconsiderations are append-only
external evidence. They never write cognition, mutate a project, execute work,
run tests, contact providers, or grant/reuse authority.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from requirement_quality_assessment import (
    load_requirement_quality_assessment,
    load_requirement_quality_assessment_review,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1235.8"
MAX_CANDIDATES = 100
MAX_REVIEWS = 200
MAX_RECONSIDERATIONS = 200
MAX_LESSON_CODES = 8

LESSON_CODES = {
    "retain_verified_approach",
    "strengthen_partial_coverage",
    "repair_requirement_gap",
    "collect_missing_evidence",
    "resolve_evidence_contradiction",
    "clarify_acceptance_criteria",
    "preserve_rollback_validation",
    "strengthen_rollback_evidence",
    "preserve_goal_alignment",
    "realign_with_project_goal",
    "constrain_out_of_scope_work",
    "require_more_evidence",
    "no_durable_lesson",
}
REVIEW_DISPOSITIONS = {"accept", "reject", "defer", "revise", "suspend"}
RECONSIDERATION_DECISIONS = {"retain", "revise", "suspend", "reopen", "unresolved"}
ELIGIBLE_QUALITY_REVIEW_DISPOSITIONS = {"accept_assessment", "request_remediation", "request_changes"}
CONTRADICTORY_LESSON_PAIRS = (
    frozenset({"retain_verified_approach", "repair_requirement_gap"}),
    frozenset({"preserve_rollback_validation", "strengthen_rollback_evidence"}),
    frozenset({"preserve_goal_alignment", "realign_with_project_goal"}),
)

AUTHORITY_FLAGS = {
    "evidence_backed_lesson_candidate_authorized": True,
    "evidence_backed_lesson_review_authorized": True,
    "evidence_backed_lesson_reconsideration_authorized": True,
    "lesson_is_cognition": False,
    "lesson_writes_cognition": False,
    "lesson_is_execution_authority": False,
    "lesson_is_project_mutation_authority": False,
    "lesson_is_requirement_mutation_authority": False,
    "lesson_is_test_execution_authority": False,
    "lesson_is_queue_or_schedule_authority": False,
    "execution_session_launch_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "requirement_mutation_authorized": False,
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
    r"^prepare evidence-backed development lesson for quality assessment "
    r"(?P<assessment>quality_assessment_[a-f0-9]{24}) digest (?P<assessment_digest>[a-f0-9]{64}) "
    r"review (?P<review>quality_review_[a-f0-9]{24}) digest (?P<review_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVIEW = re.compile(
    r"^review evidence-backed development lesson (?P<decision>accept|reject|defer|suspend) "
    r"for candidate (?P<candidate>development_lesson_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_REVISE = re.compile(
    r"^review evidence-backed development lesson revise for candidate "
    r"(?P<candidate>development_lesson_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64}) "
    r"with lessons (?P<codes>[a-z0-9_; -]+)[.!?]*$",
    re.I,
)
_RECONSIDER = re.compile(
    r"^reconsider evidence-backed development lesson (?P<decision>retain|revise|suspend|reopen|unresolved) "
    r"for review (?P<review>development_lesson_review_[a-f0-9]{24}) digest (?P<review_digest>[a-f0-9]{64}) "
    r"using later assessment (?P<assessment>quality_assessment_[a-f0-9]{24}) digest (?P<assessment_digest>[a-f0-9]{64}) "
    r"review (?P<quality_review>quality_review_[a-f0-9]{24}) digest (?P<quality_review_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show evidence-backed development lessons[.!?]*$", re.I)
_SHOW_ONE = re.compile(r"^show evidence-backed development lesson (?P<candidate>development_lesson_[a-f0-9]{24})[.!?]*$", re.I)
_SHOW_REVIEWS = re.compile(r"^show evidence-backed development lesson reviews[.!?]*$", re.I)
_SHOW_RECONSIDERATIONS = re.compile(r"^show evidence-backed development lesson reconsiderations[.!?]*$", re.I)


def _root(runtime_root=None) -> Path:
    return _store_root(runtime_root)


def _candidate_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "evidence_backed_development_lesson_candidates"


def _candidate_path(candidate_id: str, runtime_root=None) -> Path:
    return _candidate_root(runtime_root) / f"{str(candidate_id or '').lower()}.json"


def _candidate_index_path(assessment_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "evidence_backed_development_lesson_candidate_indexes" / f"{str(assessment_id or '').lower()}.json"


def _review_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "evidence_backed_development_lesson_reviews"


def _review_path(review_id: str, runtime_root=None) -> Path:
    return _review_root(runtime_root) / f"{str(review_id or '').lower()}.json"


def _review_index_path(candidate_id: str, runtime_root=None) -> Path:
    return _root(runtime_root) / "evidence_backed_development_lesson_review_indexes" / f"{str(candidate_id or '').lower()}.json"


def _reconsideration_root(runtime_root=None) -> Path:
    return _root(runtime_root) / "evidence_backed_development_lesson_reconsiderations"


def _reconsideration_path(reconsideration_id: str, runtime_root=None) -> Path:
    return _reconsideration_root(runtime_root) / f"{str(reconsideration_id or '').lower()}.json"


def _reconsideration_index_path(review_id: str, later_assessment_id: str, runtime_root=None) -> Path:
    name = f"{str(review_id or '').lower()}--{str(later_assessment_id or '').lower()}.json"
    return _root(runtime_root) / "evidence_backed_development_lesson_reconsideration_indexes" / name


@contextmanager
def _lock(runtime_root=None):
    path = _root(runtime_root) / "locks" / "evidence-backed-development-lessons.lock"
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
                raise TimeoutError("Timed out waiting for evidence-backed lesson lock")
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
        "historical_assessment_immutable": True,
        "historical_review_immutable": True,
        "evidence_backed_only": True,
        "generalization_beyond_evidence": False,
        "accepted_lesson_remains_revisable": True,
        "fresh_separate_authority_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "requirements_modified": False,
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
    row["evidence_backed_development_lesson_result_digest"] = _digest(row)
    return row


def _quality_basis(
    assessment_id: str,
    assessment_digest: str,
    review_id: str,
    review_digest: str,
    runtime_root=None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    assessment = load_requirement_quality_assessment(str(assessment_id or "").lower(), runtime_root=runtime_root)
    review = load_requirement_quality_assessment_review(str(review_id or "").lower(), runtime_root=runtime_root)
    if not assessment.get("ok") or assessment.get("assessment_digest") != str(assessment_digest or "").lower():
        raise ValueError("stale_or_invalid_quality_assessment")
    if not review.get("ok") or review.get("review_digest") != str(review_digest or "").lower():
        raise ValueError("stale_or_invalid_quality_review")
    if review.get("assessment_id") != assessment.get("assessment_id") or review.get("assessment_digest") != assessment.get("assessment_digest"):
        raise ValueError("quality_review_lineage_mismatch")
    if review.get("project_reference") != assessment.get("project_reference"):
        raise ValueError("quality_review_project_mismatch")
    return assessment, review


def _normalize_codes(values: Iterable[str]) -> list[str]:
    codes = [str(value or "").strip().lower().replace("-", "_").replace(" ", "_") for value in values]
    codes = [code for code in codes if code]
    if not codes or len(codes) > MAX_LESSON_CODES or len(codes) != len(set(codes)):
        raise ValueError("invalid_lesson_codes")
    if any(code not in LESSON_CODES for code in codes):
        raise ValueError("unsupported_lesson_code")
    if "no_durable_lesson" in codes and len(codes) != 1:
        raise ValueError("no_durable_lesson_must_stand_alone")
    for pair in CONTRADICTORY_LESSON_PAIRS:
        if pair.issubset(set(codes)):
            raise ValueError("contradictory_lesson_codes")
    return codes


def _candidate_codes(assessment: Mapping[str, Any], review: Mapping[str, Any]) -> tuple[list[str], list[str], str]:
    counts = dict(assessment.get("classification_counts") or {})
    remediation = set(assessment.get("remediation_proposal_codes") or [])
    risks = set(assessment.get("quality_risk_categories") or [])
    codes: list[str] = []
    uncertainty: list[str] = []
    if assessment.get("all_required_requirements_satisfied") is True:
        codes.append("retain_verified_approach")
    if counts.get("partially_satisfied"):
        codes.append("strengthen_partial_coverage")
    if counts.get("unsatisfied"):
        codes.append("repair_requirement_gap")
    if counts.get("blocked_by_missing_evidence"):
        codes.extend(["collect_missing_evidence", "require_more_evidence"])
        uncertainty.append("required_evidence_missing")
    if counts.get("contradictory"):
        codes.append("resolve_evidence_contradiction")
        uncertainty.append("evidence_contradictory")
    if counts.get("unverified") or assessment.get("ambiguous_criterion_count"):
        codes.extend(["clarify_acceptance_criteria", "require_more_evidence"])
        uncertainty.append("acceptance_or_evidence_unverified")
    if counts.get("out_of_scope"):
        codes.append("constrain_out_of_scope_work")
    if assessment.get("rollback_expectation_present"):
        if "rollback" in risks or "repair_unsatisfied_requirements" in remediation:
            codes.append("strengthen_rollback_evidence")
        elif assessment.get("all_required_requirements_satisfied") is True:
            codes.append("preserve_rollback_validation")
    if assessment.get("goal_alignment_expectation_present"):
        if "goal_alignment" in risks:
            codes.append("realign_with_project_goal")
        elif assessment.get("all_required_requirements_satisfied") is True:
            codes.append("preserve_goal_alignment")
    if review.get("disposition") in {"request_remediation", "request_changes"} and not codes:
        codes.append("require_more_evidence")
        uncertainty.append("operator_requested_further_work")
    codes = list(dict.fromkeys(codes))
    if not codes:
        codes = ["no_durable_lesson"]
    codes = _normalize_codes(codes[:MAX_LESSON_CODES])
    severe = sum(int(counts.get(key) or 0) for key in ("unsatisfied", "contradictory", "blocked_by_missing_evidence"))
    if severe or uncertainty:
        confidence = "low"
    elif counts.get("partially_satisfied") or counts.get("unverified"):
        confidence = "medium"
    else:
        confidence = "high"
    return codes, sorted(set(uncertainty)), confidence


def _load_candidate(candidate_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_candidate_path(candidate_id, runtime_root))
    if not row or not _valid(row, "evidence_backed_development_lesson_candidate_record_digest"):
        return _failure("evidence_backed_lesson_candidate_integrity_blocked")
    return row


def _load_review(review_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_review_path(review_id, runtime_root))
    if not row or not _valid(row, "evidence_backed_development_lesson_review_record_digest"):
        return _failure("evidence_backed_lesson_review_integrity_blocked")
    return row


def _load_reconsideration(reconsideration_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_reconsideration_path(reconsideration_id, runtime_root))
    if not row or not _valid(row, "evidence_backed_development_lesson_reconsideration_record_digest"):
        return _failure("evidence_backed_lesson_reconsideration_integrity_blocked")
    return row


def _active_contradiction(project_reference: str, codes: Iterable[str], runtime_root=None) -> bool:
    proposed = set(codes)
    root = _review_root(runtime_root)
    if not root.exists():
        return False
    for path in sorted(root.glob("*.json")):
        row = _read_json(path)
        if not row or not _valid(row, "evidence_backed_development_lesson_review_record_digest"):
            continue
        if row.get("project_reference") != project_reference or row.get("lesson_active") is not True:
            continue
        existing = set(row.get("lesson_codes") or [])
        for pair in CONTRADICTORY_LESSON_PAIRS:
            if pair.issubset(proposed | existing) and proposed != existing:
                return True
    return False


def prepare_evidence_backed_development_lesson(
    assessment_id: str,
    *,
    expected_assessment_digest: str,
    quality_review_id: str,
    expected_quality_review_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            assessment, quality_review = _quality_basis(
                assessment_id, expected_assessment_digest,
                quality_review_id, expected_quality_review_digest,
                runtime_root,
            )
            disposition = str(quality_review.get("disposition") or "")
            if disposition not in ELIGIBLE_QUALITY_REVIEW_DISPOSITIONS:
                return _failure("evidence_backed_lesson_quality_review_not_eligible", disposition)
            index = _read_json(_candidate_index_path(assessment["assessment_id"], runtime_root))
            if index:
                existing = _load_candidate(str(index.get("candidate_id") or ""), runtime_root)
                if existing.get("ok"):
                    if (
                        existing.get("assessment_digest") == assessment.get("assessment_digest")
                        and existing.get("quality_review_digest") == quality_review.get("review_digest")
                    ):
                        return {**existing, "operation_status": "replayed"}
                    return _failure("evidence_backed_lesson_candidate_history_conflict")
                return _failure("evidence_backed_lesson_candidate_history_integrity_blocked")
            codes, uncertainty, confidence = _candidate_codes(assessment, quality_review)
            deliberate_silence = codes == ["no_durable_lesson"]
            evidence_basis = {
                "assessment_digest": assessment.get("assessment_digest"),
                "quality_review_digest": quality_review.get("review_digest"),
                "requirement_spec_digest": assessment.get("requirement_spec_digest"),
                "evidence_spec_digest": assessment.get("evidence_spec_digest"),
                "outcome_digest": assessment.get("outcome_digest", ""),
                "classification_counts": dict(assessment.get("classification_counts") or {}),
                "overall_assessment_state": assessment.get("overall_assessment_state"),
            }
            identity = {**evidence_basis, "lesson_codes": codes, "project_reference": assessment.get("project_reference")}
            candidate_id = f"development_lesson_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": "evidence_backed_development_lesson_deliberate_silence" if deliberate_silence else "evidence_backed_development_lesson_ready_for_operator_review",
                "candidate_id": candidate_id,
                "candidate_digest": _digest(identity),
                "assessment_id": assessment.get("assessment_id"),
                "assessment_digest": assessment.get("assessment_digest"),
                "quality_review_id": quality_review.get("review_id"),
                "quality_review_digest": quality_review.get("review_digest"),
                "quality_review_disposition": disposition,
                "resource_assessment_id": assessment.get("resource_assessment_id"),
                "resource_review_id": assessment.get("resource_review_id"),
                "launch_id": assessment.get("launch_id"),
                "project_reference": assessment.get("project_reference"),
                "outcome_id": assessment.get("outcome_id", ""),
                "outcome_digest": assessment.get("outcome_digest", ""),
                "outcome_type": assessment.get("outcome_type", ""),
                "overall_assessment_state": assessment.get("overall_assessment_state"),
                "classification_counts": dict(assessment.get("classification_counts") or {}),
                "evidence_basis_digest": _digest(evidence_basis),
                "candidate_lesson_codes": codes,
                "lesson_confidence": confidence,
                "uncertainty_codes": uncertainty,
                "deliberate_silence": deliberate_silence,
                "lesson_review_required": not deliberate_silence,
                "durable_project_scoped_learning_recorded": False,
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "evidence_backed_development_lesson_candidate_record_digest")
            _atomic_json(_candidate_path(candidate_id, runtime_root), row)
            _atomic_json(_candidate_index_path(assessment["assessment_id"], runtime_root), {
                "assessment_id": assessment["assessment_id"],
                "candidate_id": candidate_id,
                "candidate_digest": row["candidate_digest"],
                "content_free": True,
            })
            return row
    except (OSError, TimeoutError, ValueError) as exc:
        return _failure("evidence_backed_development_lesson_blocked", str(exc))


def review_evidence_backed_development_lesson(
    candidate_id: str,
    *,
    expected_candidate_digest: str,
    disposition: str,
    revised_lesson_codes: Iterable[str] | None = None,
    runtime_root=None,
) -> dict[str, Any]:
    disposition = str(disposition or "").strip().lower().replace(" ", "_").replace("-", "_")
    if disposition not in REVIEW_DISPOSITIONS:
        return _failure("evidence_backed_lesson_review_blocked", "unsupported_review_disposition")
    try:
        with _lock(runtime_root):
            candidate = _load_candidate(str(candidate_id or "").lower(), runtime_root)
            if not candidate.get("ok"):
                return _failure("evidence_backed_lesson_review_candidate_integrity_blocked")
            if candidate.get("candidate_digest") != str(expected_candidate_digest or "").lower():
                return _failure("evidence_backed_lesson_review_stale_candidate_digest")
            _quality_basis(
                candidate["assessment_id"], candidate["assessment_digest"],
                candidate["quality_review_id"], candidate["quality_review_digest"], runtime_root,
            )
            index = _read_json(_review_index_path(candidate["candidate_id"], runtime_root))
            if index:
                existing = _load_review(str(index.get("review_id") or ""), runtime_root)
                if existing.get("ok") and existing.get("disposition") == disposition:
                    return {**existing, "operation_status": "replayed"}
                if existing.get("ok"):
                    return _failure("evidence_backed_lesson_conflicting_review")
                return _failure("evidence_backed_lesson_review_history_integrity_blocked")
            if candidate.get("deliberate_silence") is True and disposition in {"accept", "revise"}:
                return _failure("evidence_backed_lesson_review_blocked", "no_lesson_candidate_to_accept")
            codes = list(candidate.get("candidate_lesson_codes") or [])
            if disposition == "revise":
                codes = _normalize_codes(revised_lesson_codes or [])
            else:
                codes = _normalize_codes(codes)
            if disposition in {"accept", "revise"} and _active_contradiction(str(candidate.get("project_reference") or ""), codes, runtime_root):
                return _failure("evidence_backed_lesson_review_blocked", "contradictory_active_project_lesson")
            identity = {
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "disposition": disposition,
                "lesson_codes": codes,
            }
            review_id = f"development_lesson_review_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"evidence_backed_development_lesson_{disposition}_recorded",
                "review_id": review_id,
                "review_digest": _digest(identity),
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "assessment_id": candidate["assessment_id"],
                "assessment_digest": candidate["assessment_digest"],
                "quality_review_id": candidate["quality_review_id"],
                "quality_review_digest": candidate["quality_review_digest"],
                "project_reference": candidate["project_reference"],
                "outcome_id": candidate.get("outcome_id", ""),
                "outcome_digest": candidate.get("outcome_digest", ""),
                "disposition": disposition,
                "lesson_codes": codes,
                "lesson_confidence": candidate.get("lesson_confidence"),
                "durable_project_scoped_learning_recorded": disposition in {"accept", "revise"},
                "lesson_active": disposition in {"accept", "revise"},
                "lesson_rejected": disposition == "reject",
                "lesson_deferred": disposition == "defer",
                "lesson_suspended": disposition == "suspend",
                "reconsideration_required_if_evidence_changes": disposition in {"accept", "revise", "suspend"},
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "evidence_backed_development_lesson_review_record_digest")
            _atomic_json(_review_path(review_id, runtime_root), row)
            _atomic_json(_review_index_path(candidate["candidate_id"], runtime_root), {
                "candidate_id": candidate["candidate_id"],
                "review_id": review_id,
                "review_digest": row["review_digest"],
                "content_free": True,
            })
            return row
    except (OSError, TimeoutError, ValueError) as exc:
        return _failure("evidence_backed_lesson_review_blocked", str(exc))


def reconsider_evidence_backed_development_lesson(
    review_id: str,
    *,
    expected_review_digest: str,
    later_assessment_id: str,
    expected_later_assessment_digest: str,
    later_quality_review_id: str,
    expected_later_quality_review_digest: str,
    decision: str,
    runtime_root=None,
) -> dict[str, Any]:
    decision = str(decision or "").strip().lower().replace("-", "_").replace(" ", "_")
    if decision not in RECONSIDERATION_DECISIONS:
        return _failure("evidence_backed_lesson_reconsideration_blocked", "unsupported_reconsideration_decision")
    try:
        with _lock(runtime_root):
            review = _load_review(str(review_id or "").lower(), runtime_root)
            if not review.get("ok") or review.get("review_digest") != str(expected_review_digest or "").lower():
                return _failure("evidence_backed_lesson_reconsideration_stale_review")
            if review.get("disposition") not in {"accept", "revise", "suspend"}:
                return _failure("evidence_backed_lesson_reconsideration_ineligible_review")
            later, later_review = _quality_basis(
                later_assessment_id, expected_later_assessment_digest,
                later_quality_review_id, expected_later_quality_review_digest,
                runtime_root,
            )
            if later.get("project_reference") != review.get("project_reference"):
                return _failure("evidence_backed_lesson_cross_project_reconsideration_blocked")
            if later.get("assessment_id") == review.get("assessment_id"):
                return _failure("evidence_backed_lesson_later_evidence_required")
            index_path = _reconsideration_index_path(review["review_id"], later["assessment_id"], runtime_root)
            existing_index = _read_json(index_path)
            if existing_index:
                existing = _load_reconsideration(str(existing_index.get("reconsideration_id") or ""), runtime_root)
                if existing.get("ok") and existing.get("decision") == decision:
                    return {**existing, "operation_status": "replayed"}
                if existing.get("ok"):
                    return _failure("evidence_backed_lesson_conflicting_reconsideration")
                return _failure("evidence_backed_lesson_reconsideration_history_integrity_blocked")
            later_codes, later_uncertainty, later_confidence = _candidate_codes(later, later_review)
            changed = (
                set(later_codes) != set(review.get("lesson_codes") or [])
                or later.get("assessment_digest") != review.get("assessment_digest")
            )
            identity = {
                "review_id": review["review_id"],
                "review_digest": review["review_digest"],
                "later_assessment_digest": later["assessment_digest"],
                "later_quality_review_digest": later_review["review_digest"],
                "decision": decision,
            }
            reconsideration_id = f"development_lesson_reconsideration_{_digest(identity)[:24]}"
            row = {
                "ok": True,
                "status": f"evidence_backed_development_lesson_reconsideration_{decision}_recorded",
                "reconsideration_id": reconsideration_id,
                "reconsideration_digest": _digest(identity),
                "review_id": review["review_id"],
                "review_digest": review["review_digest"],
                "candidate_id": review["candidate_id"],
                "project_reference": review["project_reference"],
                "original_assessment_id": review["assessment_id"],
                "original_assessment_digest": review["assessment_digest"],
                "later_assessment_id": later["assessment_id"],
                "later_assessment_digest": later["assessment_digest"],
                "later_quality_review_id": later_review["review_id"],
                "later_quality_review_digest": later_review["review_digest"],
                "decision": decision,
                "later_candidate_lesson_codes": later_codes,
                "later_lesson_confidence": later_confidence,
                "later_uncertainty_codes": later_uncertainty,
                "evidence_changed": changed,
                "historical_lesson_preserved": True,
                "new_operator_review_required_for_revision": decision in {"revise", "reopen", "unresolved"},
                "lesson_active_after_reconsideration": decision == "retain",
                "lesson_suspended_after_reconsideration": decision == "suspend",
                "operation_status": "created",
                **_base(),
            }
            row = _sealed(row, "evidence_backed_development_lesson_reconsideration_record_digest")
            _atomic_json(_reconsideration_path(reconsideration_id, runtime_root), row)
            _atomic_json(index_path, {
                "review_id": review["review_id"],
                "later_assessment_id": later["assessment_id"],
                "reconsideration_id": reconsideration_id,
                "reconsideration_digest": row["reconsideration_digest"],
                "content_free": True,
            })
            return row
    except (OSError, TimeoutError, ValueError) as exc:
        return _failure("evidence_backed_lesson_reconsideration_blocked", str(exc))


def _public_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "candidate_id", "candidate_digest", "assessment_id", "assessment_digest",
        "quality_review_id", "quality_review_digest", "project_reference", "outcome_id", "outcome_digest",
        "overall_assessment_state", "classification_counts", "candidate_lesson_codes", "lesson_confidence",
        "uncertainty_codes", "deliberate_silence", "lesson_review_required", "content_free", "project_scoped",
        "durable_project_scoped_learning_recorded", "lesson_is_cognition", "lesson_writes_cognition",
        "lesson_is_execution_authority", "project_mutation_authorized", "test_execution_authorized",
        "cognition_write_authorized", "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def _public_review(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "review_id", "review_digest", "candidate_id", "candidate_digest",
        "assessment_id", "assessment_digest", "project_reference", "disposition", "lesson_codes",
        "lesson_confidence", "durable_project_scoped_learning_recorded", "lesson_active", "lesson_rejected",
        "lesson_deferred", "lesson_suspended", "content_free", "project_scoped", "lesson_is_cognition",
        "lesson_writes_cognition", "lesson_is_execution_authority", "project_mutation_authorized",
        "test_execution_authorized", "cognition_write_authorized", "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def _public_reconsideration(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "ok", "status", "reconsideration_id", "reconsideration_digest", "review_id", "review_digest",
        "project_reference", "original_assessment_id", "later_assessment_id", "decision",
        "later_candidate_lesson_codes", "later_lesson_confidence", "evidence_changed",
        "historical_lesson_preserved", "new_operator_review_required_for_revision",
        "content_free", "project_scoped", "lesson_is_cognition", "lesson_writes_cognition",
        "lesson_is_execution_authority", "project_mutation_authorized", "cognition_write_authorized",
        "old_authority_reusable",
    )
    return {key: row.get(key) for key in keys}


def inspect_evidence_backed_development_lesson(candidate_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _load_candidate(str(candidate_id or "").lower(), runtime_root)
    return _public_candidate(row) if row.get("ok") else row


def _public_rows(root: Path, field: str, projector, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(root.glob("*.json"))[-limit:]:
            row = _read_json(path)
            if row and _valid(row, field):
                rows.append(projector(row))
    return rows


def public_evidence_backed_development_lessons(*, runtime_root=None) -> dict[str, Any]:
    rows = _public_rows(_candidate_root(runtime_root), "evidence_backed_development_lesson_candidate_record_digest", _public_candidate, MAX_CANDIDATES)
    return {"ok": True, "status": "evidence_backed_development_lesson_list_ready", "candidate_count": len(rows), "candidates": rows, **_base()}


def public_evidence_backed_development_lesson_reviews(*, runtime_root=None) -> dict[str, Any]:
    rows = _public_rows(_review_root(runtime_root), "evidence_backed_development_lesson_review_record_digest", _public_review, MAX_REVIEWS)
    return {"ok": True, "status": "evidence_backed_development_lesson_review_list_ready", "review_count": len(rows), "reviews": rows, **_base()}


def public_evidence_backed_development_lesson_reconsiderations(*, runtime_root=None) -> dict[str, Any]:
    rows = _public_rows(_reconsideration_root(runtime_root), "evidence_backed_development_lesson_reconsideration_record_digest", _public_reconsideration, MAX_RECONSIDERATIONS)
    return {"ok": True, "status": "evidence_backed_development_lesson_reconsideration_list_ready", "reconsideration_count": len(rows), "reconsiderations": rows, **_base()}


def evidence_backed_development_lesson_response(row: Mapping[str, Any]) -> str:
    if not row.get("ok"):
        return f"Evidence-backed development lesson was blocked: {row.get('status', 'unknown')} ({row.get('reason', '')})."
    status = str(row.get("status") or "")
    if "ready_for_operator_review" in status:
        return (
            f"Prepared evidence-backed development lesson {row.get('candidate_id')} with confidence {row.get('lesson_confidence')}. "
            "It is project-scoped external evidence and grants no cognition, project, test, or execution authority."
        )
    if "deliberate_silence" in status:
        return "The reviewed evidence supports deliberate silence rather than a durable lesson. No cognition or authority was created."
    if "reconsideration" in status:
        return (
            f"Recorded evidence-backed lesson reconsideration {row.get('decision')}. Historical evidence remains immutable and any revision requires new operator review."
        )
    if "recorded" in status:
        return (
            f"Recorded evidence-backed development lesson review {row.get('disposition')}. "
            "No project change, test, command, provider call, cognition write, launch, or resume occurred."
        )
    return "Evidence-backed development lesson records are ready for inspection."


def process_evidence_backed_development_lesson_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    match = _PREPARE.fullmatch(text)
    if match:
        row = prepare_evidence_backed_development_lesson(
            match.group("assessment"), expected_assessment_digest=match.group("assessment_digest"),
            quality_review_id=match.group("review"), expected_quality_review_digest=match.group("review_digest"),
            runtime_root=runtime_root,
        )
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    match = _REVISE.fullmatch(text)
    if match:
        row = review_evidence_backed_development_lesson(
            match.group("candidate"), expected_candidate_digest=match.group("digest"), disposition="revise",
            revised_lesson_codes=[part for part in re.split(r"[; ]+", match.group("codes")) if part], runtime_root=runtime_root,
        )
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    match = _REVIEW.fullmatch(text)
    if match:
        row = review_evidence_backed_development_lesson(
            match.group("candidate"), expected_candidate_digest=match.group("digest"),
            disposition=match.group("decision"), runtime_root=runtime_root,
        )
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    match = _RECONSIDER.fullmatch(text)
    if match:
        row = reconsider_evidence_backed_development_lesson(
            match.group("review"), expected_review_digest=match.group("review_digest"),
            later_assessment_id=match.group("assessment"), expected_later_assessment_digest=match.group("assessment_digest"),
            later_quality_review_id=match.group("quality_review"), expected_later_quality_review_digest=match.group("quality_review_digest"),
            decision=match.group("decision"), runtime_root=runtime_root,
        )
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    if _SHOW_ALL.fullmatch(text):
        row = public_evidence_backed_development_lessons(runtime_root=runtime_root)
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    match = _SHOW_ONE.fullmatch(text)
    if match:
        row = inspect_evidence_backed_development_lesson(match.group("candidate"), runtime_root=runtime_root)
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    if _SHOW_REVIEWS.fullmatch(text):
        row = public_evidence_backed_development_lesson_reviews(runtime_root=runtime_root)
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    if _SHOW_RECONSIDERATIONS.fullmatch(text):
        row = public_evidence_backed_development_lesson_reconsiderations(runtime_root=runtime_root)
        return {"active": True, "response": evidence_backed_development_lesson_response(row), "evidence_backed_development_lesson": row}
    return {"active": False}


def build_evidence_backed_development_outcome_lessons_contract() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "evidence_backed_development_outcome_lessons_contract_ready",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "milestone_name": "Evidence-Backed Lessons from Development Outcomes",
        "roadmap_path": "Balanced Mind-and-Action Path 3",
        "exact_quality_assessment_and_review_binding": True,
        "optional_sealed_outcome_lineage_retained": True,
        "deterministic_lesson_derivation": True,
        "evidence_strength_and_uncertainty_visible": True,
        "project_scoped_external_revisable_learning": True,
        "later_evidence_reconsideration": True,
        "deliberate_silence_supported": True,
        "ordinary_chat_exact_controls": True,
        "restart_replay_stale_tamper_privacy_contradiction_hardening_required": True,
        "accepted_lessons_do_not_write_cognition": True,
        "accepted_lessons_do_not_grant_execution_authority": True,
        "lesson_codes": sorted(LESSON_CODES),
        "review_dispositions": sorted(REVIEW_DISPOSITIONS),
        "reconsideration_decisions": sorted(RECONSIDERATION_DECISIONS),
        "max_lesson_codes": MAX_LESSON_CODES,
        **_base(),
    }
