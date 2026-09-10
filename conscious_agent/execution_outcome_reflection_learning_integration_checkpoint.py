from __future__ import annotations

"""Read-only v1229.9 Execution Outcome Reflection and Learning checkpoint."""

import hashlib
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from execution_outcome_reflection_learning_integration import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    LESSON_CODES,
    LESSON_DISPOSITIONS,
    MAX_LESSON_CODES,
    MAX_LESSON_REVIEWS,
    MAX_RECONSIDERATIONS,
    MAX_OUTCOMES,
    MAX_REFLECTIONS,
    OUTCOME_TYPES,
    RECONSIDERATION_DECISIONS,
    _base,
    _public,
    _sealed,
    _validate_outcome,
    _validate_reflection,
    _validate_review,
    _validate_reconsideration,
)
from ordinary_chat_development_campaign import _digest

CONTRACT_VERSION = "v1229.9"


def _tree_signature(root: Path) -> tuple[str, int]:
    rows: list[str] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
        count += 1
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), count


def _synthetic_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    outcome_identity = {
        "launch_id": "launch_" + "1" * 24,
        "launch_digest": "2" * 64,
        "monitor_digest": "3" * 64,
        "control_digest": "4" * 64,
        "outcome_type": "recovered",
    }
    outcome = {
        "ok": True,
        "status": "execution_outcome_ready_for_reflection",
        "outcome_id": "outcome_" + _digest(outcome_identity)[:24],
        "outcome_digest": _digest(outcome_identity),
        "outcome_type": "recovered",
        "achievement_classification": "partially_achieved",
        "launch_id": outcome_identity["launch_id"],
        "launch_digest": outcome_identity["launch_digest"],
        "monitor_id": "monitor_" + "5" * 24,
        "monitor_digest": outcome_identity["monitor_digest"],
        "control_id": "control_" + "6" * 24,
        "control_digest": outcome_identity["control_digest"],
        "project_reference": "project_" + "7" * 16,
        "queue_item_id": "work_" + "8" * 24,
        "proposal_id": "devc_" + "9" * 24,
        "source_session_id": "session_" + "a" * 24,
        "observed_fact_codes": ["control_state:paused", "monitor_stage:operator_review_required", "progress_bucket:50"],
        "uncertainty_codes": [],
        "evidence_complete": True,
        "reflection_review_required": True,
        "operation_status": "created",
        **_base(),
    }
    outcome = _sealed(outcome, "execution_outcome_record_digest")
    reflection_identity = {
        "outcome_id": outcome["outcome_id"],
        "outcome_digest": outcome["outcome_digest"],
        "codes": ["strengthen_recovery_checks", "preserve_operator_intervention"],
    }
    reflection = {
        "ok": True,
        "status": "execution_outcome_reflection_ready_for_review",
        "reflection_id": "reflection_" + _digest(reflection_identity)[:24],
        "reflection_digest": _digest(reflection_identity),
        "reflection_status": "candidate_ready",
        "outcome_id": outcome["outcome_id"],
        "outcome_digest": outcome["outcome_digest"],
        "outcome_type": outcome["outcome_type"],
        "achievement_classification": outcome["achievement_classification"],
        "project_reference": outcome["project_reference"],
        "candidate_lesson_codes": reflection_identity["codes"],
        "supporting_fact_codes": outcome["observed_fact_codes"],
        "uncertainty_codes": [],
        "lesson_review_required": True,
        "deliberate_silence": False,
        "operation_status": "created",
        **_base(),
    }
    reflection = _sealed(reflection, "execution_outcome_reflection_record_digest")
    review_identity = {
        "reflection_id": reflection["reflection_id"],
        "reflection_digest": reflection["reflection_digest"],
        "disposition": "accept",
        "lesson_codes": reflection["candidate_lesson_codes"],
    }
    review = {
        "ok": True,
        "status": "execution_outcome_lesson_accepted",
        "review_id": "lesson_review_" + _digest(review_identity)[:24],
        "review_digest": _digest(review_identity),
        "reflection_id": reflection["reflection_id"],
        "reflection_digest": reflection["reflection_digest"],
        "outcome_id": outcome["outcome_id"],
        "outcome_digest": outcome["outcome_digest"],
        "project_reference": outcome["project_reference"],
        "disposition": "accept",
        "lesson_codes": reflection["candidate_lesson_codes"],
        "durable_project_scoped_learning_recorded": True,
        "lesson_active": True,
        "lesson_suspended": False,
        "lesson_deferred": False,
        "lesson_rejected": False,
        "reconsideration_required_if_evidence_changes": True,
        "operation_status": "created",
        **_base(),
    }
    review["durable_project_scoped_learning_authorized"] = True
    review = _sealed(review, "execution_outcome_lesson_review_record_digest")
    return outcome, reflection, review


def build_execution_outcome_reflection_learning_integration_checkpoint(*, source_root=None, runtime_root=None) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))
    outcome, reflection, review = _synthetic_records()
    public_outcome = _public(outcome, kind="outcome")
    public_reflection = _public(reflection, kind="reflection")
    public_review = _public(review, kind="review")

    for value in (
        _validate_outcome(outcome), _validate_reflection(reflection), _validate_review(review),
        public_outcome["ok"] is True, public_reflection["ok"] is True, public_review["ok"] is True,
        public_outcome["outcome_type"] == "recovered",
        public_reflection["reflection_status"] == "candidate_ready",
        "strengthen_recovery_checks" in public_reflection["candidate_lesson_codes"],
        public_review["disposition"] == "accept",
        public_review["durable_project_scoped_learning_recorded"] is True,
        public_review["durable_project_scoped_learning_authorized"] is True,
        public_review["reconsideration_required_if_evidence_changes"] is True,
        RETAINED_CONTRACT_VERSION == "v1229.8",
        OUTCOME_TYPES == {"completed", "failed", "cancelled", "paused", "recovered", "abandoned", "inconclusive"},
        LESSON_DISPOSITIONS == {"accept", "reject", "defer", "revise", "suspend"},
        "no_durable_lesson" in LESSON_CODES,
        MAX_OUTCOMES == 100, MAX_REFLECTIONS == 100, MAX_LESSON_REVIEWS == 200, MAX_RECONSIDERATIONS == 200, MAX_LESSON_CODES == 4,
        RECONSIDERATION_DECISIONS == {"retain", "revise", "suspend", "reopen", "unresolved"},
    ):
        check(value)

    for record in (public_outcome, public_reflection, public_review):
        for key in (
            "provider_execution_authorized", "command_execution_authorized", "test_execution_authorized",
            "workspace_materialization_authorized", "project_mutation_authorized", "queue_mutation_authorized",
            "schedule_mutation_authorized", "launch_authorized", "background_execution_authorized",
            "cognition_write_authorized", "installation_authorized", "promotion_authorized",
            "release_authorized", "model_management_authorized", "old_authority_reusable",
        ):
            check(record.get(key) is False)
        for key in (
            "provider_contacted", "commands_executed", "tests_executed", "workspace_materialized",
            "project_modified", "selected_project_modified", "source_modified", "cognition_written",
            "private_request_exposed", "private_path_exposed", "private_content_exposed",
            "project_name_exposed", "raw_provider_output_exposed", "raw_test_output_exposed",
        ):
            check(record.get(key) is False)
        check(record.get("content_free") is True)
        check(record.get("runtime_records_external") is True)
        check(record.get("facts_separated_from_interpretation") is True)
        check(record.get("uncertainty_preserved") is True)
        check(record.get("project_scoped_only") is True)
        check(record.get("generalized_beyond_project") is False)
        check(record.get("historical_truth_preserved") is True)
        check(record.get("reflection_is_not_cognition_write") is True)
        check(record.get("learning_is_revisable") is True)

    reconsideration_identity = {
        "review_id": review["review_id"], "review_digest": review["review_digest"],
        "later_outcome_id": "outcome_" + "b" * 24, "later_outcome_digest": "c" * 64,
        "decision": "revise",
    }
    reconsideration = {
        "ok": True, "status": "execution_outcome_lesson_reconsideration_revise",
        "reconsideration_id": "reconsideration_" + _digest(reconsideration_identity)[:24],
        "reconsideration_digest": _digest(reconsideration_identity),
        "review_id": review["review_id"], "review_digest": review["review_digest"],
        "later_outcome_id": reconsideration_identity["later_outcome_id"],
        "later_outcome_digest": reconsideration_identity["later_outcome_digest"],
        "project_reference": review["project_reference"], "decision": "revise",
        "prior_lesson_codes": review["lesson_codes"], "later_outcome_type": "failed",
        "later_uncertainty_codes": [], "lesson_retained": False, "lesson_revision_required": True,
        "lesson_suspended": False, "lesson_reopened_for_review": False, "lesson_unresolved": False,
        "new_operator_review_required": True, "operation_status": "created", **_base(),
    }
    reconsideration = _sealed(reconsideration, "execution_outcome_lesson_reconsideration_record_digest")
    check(_validate_reconsideration(reconsideration))
    public_reconsideration = _public(reconsideration, kind="reconsideration")
    for value in (
        public_reconsideration["ok"] is True, public_reconsideration["decision"] == "revise",
        public_reconsideration["new_operator_review_required"] is True,
        public_reconsideration["cognition_written"] is False,
        public_reconsideration["project_mutation_authorized"] is False,
    ):
        check(value)

    tampered_outcome = dict(outcome); tampered_outcome["outcome_type"] = "completed"
    tampered_reflection = dict(reflection); tampered_reflection["candidate_lesson_codes"] = ["retain_bounded_approach"]
    tampered_review = dict(review); tampered_review["disposition"] = "reject"
    check(_validate_outcome(tampered_outcome) is False)
    check(_validate_reflection(tampered_reflection) is False)
    check(_validate_review(tampered_review) is False)

    module = (source / "conscious_agent" / "execution_outcome_reflection_learning_integration.py").read_text(encoding="utf-8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    release = (source / "tools" / "release_verify.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    for value in (
        "process_execution_outcome_reflection_learning_control" in ordinary,
        "execution-outcome-reflection-learning-integration-checkpoint" in api,
        "execution-outcome-reflection-learning-integration-checkpoint" in cli,
        "v1229.9-execution-outcome-reflection-learning-integration-checkpoint" in release,
        'WORKING_SOURCE_VERSION = "1229.9"' in metadata,
        'NEXT_RECOMMENDED_ARC = "v1230.0-v1230.9 Mindful Execution Alpha Integration Benchmark"' in metadata,
        "LocalModelClient" not in module,
        '"cognition_write_authorized": False' in module,
        '"project_mutation_authorized": False' in module,
        "deliberate_silence" in module,
        "reconsideration_required_if_evidence_changes" in module,
        "reconsider_execution_outcome_lesson" in module,
        "cross_project_reconsideration_rejected" in module,
    ):
        check(value)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "execution-outcome-reflection-learning-integration-checkpoint"), None)
    for value in (
        descriptor is not None,
        (descriptor or {}).get("contract_version") == CONTRACT_VERSION,
        (descriptor or {}).get("read_only") is True,
        (descriptor or {}).get("post_available") is False,
        (descriptor or {}).get("required_input_count") == 0,
        registry.get("duplicate_checkpoint_ids") == [],
    ):
        check(value)

    after, after_count = _tree_signature(source)
    check(before == after and count == after_count)
    ok = all(checks)
    return {
        "ok": ok,
        "status": "execution_outcome_reflection_learning_integration_checkpoint_ready" if ok else "execution_outcome_reflection_learning_integration_checkpoint_failed",
        "checkpoint_id": "execution-outcome-reflection-learning-integration-checkpoint",
        "contract_version": CONTRACT_VERSION,
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "content_free": True,
        "source_file_count_before": count,
        "source_file_count_after": after_count,
        "source_signature_unchanged": before == after,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "project_modified": False,
        "cognition_written": False,
        "authority_granted": False,
        "release_authorized": False,
        "public_outcome": public_outcome,
        "public_reflection": public_reflection,
        "public_review": public_review,
        "public_reconsideration": public_reconsideration,
    }
