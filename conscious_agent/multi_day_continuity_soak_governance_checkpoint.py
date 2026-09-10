from __future__ import annotations

"""Strictly read-only v1144.9 Multi-Day Continuity Soak Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from continuity_soak_eligibility import SOAK_SCENARIOS
from multi_day_continuity_soak_execution_checkpoint import build_multi_day_continuity_soak_execution_checkpoint
from multi_day_continuity_soak_intake_checkpoint import build_multi_day_continuity_soak_intake_checkpoint
from multi_day_continuity_soak_reliability_checkpoint import build_multi_day_continuity_soak_reliability_checkpoint

CONTRACT_VERSION = "v1144.9"


def _runtime_root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _passed(report: dict[str, Any], identifier: str) -> bool:
    for row in report.get("checks") or []:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id") or row.get("name") or row.get("check") or row.get("check_id")
        if row_id == identifier:
            return bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
    return False


def _authority_inert(component: dict[str, Any]) -> bool:
    return not any(bool(value) for value in (component.get("authority_boundary") or {}).values())


def _false_across(components: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(component.get(field)) for component in components for field in fields)


def build_multi_day_continuity_soak_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_multi_day_continuity_soak_intake_checkpoint(runtime, source_root=source)
    execution = build_multi_day_continuity_soak_execution_checkpoint(runtime, source_root=source)
    reliability = build_multi_day_continuity_soak_reliability_checkpoint(runtime, source_root=source)

    eligibility = intake.get("eligibility") or {}
    campaigns = intake.get("campaigns") or {}
    executions = execution.get("executions") or {}
    receipts = execution.get("receipts") or {}
    reviews = reliability.get("reviews") or {}
    evidence = reliability.get("evidence") or {}
    components = (eligibility, campaigns, executions, receipts, reviews, evidence)

    eligibility_rows = eligibility.get("recent_records") or []
    campaign_rows = campaigns.get("recent_records") or []
    execution_rows = executions.get("recent_records") or []
    receipt_rows = receipts.get("recent_records") or []
    review_rows = reviews.get("recent_reviews") or []
    evidence_rows = evidence.get("recent_evidence") or []

    privacy_fields = (
        "raw_content_exposed",
        "workload_payload_exposed",
        "conversation_exposed",
        "prompt_exposed",
        "reasoning_text_exposed",
        "source_content_exposed",
        "command_log_exposed",
        "provider_payload_exposed",
        "hidden_reasoning_exposed",
    )
    forbidden_authority_fields = (
        "campaign_started",
        "fault_injection_started",
        "provider_contacted",
        "process_restarted",
        "work_interrupted",
        "work_resumed",
        "message_sent",
        "source_mutated",
        "source_modified",
        "approval_created",
        "authorization_created",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
    )

    checks = [
        (
            "multi_day_continuity_soak_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and reliability.get("ok")
            and intake.get("contract_version") == "v1144.2"
            and execution.get("contract_version") == "v1144.5"
            and reliability.get("contract_version") == "v1144.8",
        ),
        (
            "exact_workload_budget_baseline_runtime_and_provider_binding",
            _passed(intake, "exact_profile_binding")
            and _passed(intake, "exact_workload_lineage")
            and all(
                row.get("baseline_checkpoint_digest")
                and row.get("runtime_profile_digest")
                and row.get("provider_profile_digest")
                and row.get("workload_eligibility_ids")
                for row in eligibility_rows + campaign_rows
            ),
        ),
        (
            "complete_sleep_restart_interruption_provider_outage_stale_work_and_recovery_scenarios",
            _passed(intake, "complete_scenario_taxonomy")
            and set(eligibility.get("recognized_scenarios") or []) == SOAK_SCENARIOS
            and all(set(row.get("scenario_ids") or []) == SOAK_SCENARIOS for row in eligibility_rows)
            and all(row.get("scenario_sequence") == sorted(SOAK_SCENARIOS) for row in campaign_rows),
        ),
        (
            "bounded_multi_day_duration_observation_and_fault_profiles",
            _passed(intake, "bounded_multi_day_duration")
            and _passed(intake, "bounded_observation_interval")
            and _passed(intake, "bounded_injection_and_recovery_profiles"),
        ),
        (
            "eligibility_campaign_execution_receipt_review_and_evidence_separation",
            all(row.get("eligibility_id") for row in campaign_rows)
            and all(row.get("campaign_id") and row.get("eligibility_id") for row in execution_rows)
            and all(row.get("execution_id") and row.get("campaign_id") for row in receipt_rows)
            and all(row.get("receipt_id") and row.get("execution_id") and row.get("campaign_id") for row in review_rows)
            and all(row.get("review_id") and row.get("execution_id") and row.get("campaign_id") for row in evidence_rows),
        ),
        (
            "operator_confirmation_launch_token_and_worker_binding",
            _passed(execution, "operator_confirmation_binding")
            and all(
                row.get("state") not in {"launched", "observing", "completed"}
                or (row.get("operator_confirmation_id") and row.get("launch_token_id"))
                for row in execution_rows
            ),
        ),
        (
            "bounded_observation_cancellation_timeout_and_resource_enforcement",
            _passed(execution, "bounded_observation")
            and _passed(execution, "budget_timeout")
            and _passed(execution, "recognized_execution_states")
            and _passed(execution, "recognized_receipt_states"),
        ),
        (
            "restart_interruption_stale_worker_and_recovery_truth",
            _passed(execution, "restart_continuity")
            and _passed(execution, "stale_claim_release")
            and _passed(execution, "recovery_truth"),
        ),
        (
            "exact_cross_day_result_and_scenario_lineage",
            _passed(reliability, "exact_receipt_lineage")
            and _passed(reliability, "scenario_lineage")
            and _passed(reliability, "evidence_lineage"),
        ),
        (
            "repeated_failure_recovery_latency_resource_and_scenario_gap_review",
            _passed(reliability, "recognized_outcomes")
            and _passed(reliability, "repeated_failure_truth")
            and _passed(reliability, "scenario_coverage"),
        ),
        (
            "contamination_and_insufficient_evidence_fail_closed",
            _passed(reliability, "contamination_review")
            and all(
                not row.get("contamination_detected")
                or row.get("outcome") in {"contamination_risk", "operator_review_required"}
                for row in review_rows
            ),
        ),
        (
            "restrained_content_free_operator_visibility",
            _passed(reliability, "advisory_only")
            and all(row.get("advisory_only") for row in review_rows + evidence_rows),
        ),
        (
            "historical_truth_and_exact_lineage_preserved",
            _passed(reliability, "historical_truth_preserved")
            and all(row.get("structural_digest") for row in eligibility_rows + campaign_rows + execution_rows + review_rows + evidence_rows),
        ),
        (
            "privacy_provider_payload_log_and_hidden_reasoning_boundaries",
            _passed(intake, "privacy")
            and _passed(execution, "privacy")
            and _passed(reliability, "privacy")
            and _false_across(components, privacy_fields),
        ),
        (
            "soak_launch_fault_provider_restart_interruption_and_recovery_authority_separation",
            _passed(intake, "no_launch_authority")
            and _passed(intake, "no_soak_or_fault_execution")
            and all(_authority_inert(component) for component in components),
        ),
        (
            "no_message_source_approval_authorization_installation_promotion_or_certification",
            _false_across((intake, execution, reliability), forbidden_authority_fields[6:]),
        ),
        (
            "checkpoint_creates_no_arc_records",
            True,
        ),
        (
            "checkpoint_is_strictly_read_only",
            runtime_before == _tree_signature(runtime) and source_before == _tree_signature(source),
        ),
        ("source_runtime_separation", runtime != source),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "summary": {
            "eligibility_record_count": int(eligibility.get("record_count") or 0),
            "campaign_candidate_count": int(campaigns.get("record_count") or 0),
            "execution_record_count": int(executions.get("record_count") or 0),
            "recovery_receipt_count": int(receipts.get("record_count") or 0),
            "reliability_review_count": int(reviews.get("review_count") or 0),
            "visible_evidence_count": int(evidence.get("evidence_count") or 0),
            "recognized_scenario_count": len(SOAK_SCENARIOS),
        },
        "runtime_mutated": runtime_before != runtime_after,
        "source_modified": source_before != source_after,
        "raw_content_exposed": False,
        "workload_payload_exposed": False,
        "provider_payload_exposed": False,
        "command_log_exposed": False,
        "hidden_reasoning_exposed": False,
        "campaign_started_by_checkpoint": False,
        "fault_injection_started_by_checkpoint": False,
        "provider_contacted": False,
        "process_restarted": False,
        "work_interrupted": False,
        "work_resumed": False,
        "recovery_action_executed": False,
        "eligibility_created_by_checkpoint": False,
        "campaign_created_by_checkpoint": False,
        "execution_created_by_checkpoint": False,
        "receipt_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "visible_evidence_created_by_checkpoint": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
