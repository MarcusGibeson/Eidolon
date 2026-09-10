from __future__ import annotations

"""Strictly read-only v1143.9 Workload Coordination Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from workload_coordination_intake_checkpoint import build_workload_coordination_intake_checkpoint
from workload_coordination_execution_checkpoint import build_workload_coordination_execution_checkpoint
from workload_coordination_reliability_checkpoint import build_workload_coordination_reliability_checkpoint

CONTRACT_VERSION = "v1143.9"


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


def _false_across(components: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(component.get(field)) for component in components for field in fields)


def _authority_inert(component: dict[str, Any]) -> bool:
    return not any(bool(value) for value in (component.get("authority_boundary") or {}).values())


def build_workload_coordination_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = Path(runtime_root).expanduser().resolve() if runtime_root is not None else _runtime_root()
    source = Path(source_root).expanduser().resolve() if source_root is not None else Path(__file__).resolve().parents[1]
    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_workload_coordination_intake_checkpoint(runtime, source_root=source)
    execution = build_workload_coordination_execution_checkpoint(runtime, source_root=source)
    reliability = build_workload_coordination_reliability_checkpoint(runtime, source_root=source)

    eligibility = intake.get("eligibility") or {}
    candidates = intake.get("candidates") or {}
    arbitration = execution.get("arbitration") or {}
    continuity = execution.get("continuity") or {}
    review = reliability.get("review") or {}
    evidence = reliability.get("evidence") or {}
    components = (eligibility, candidates, arbitration, continuity, review, evidence)

    eligibility_rows = eligibility.get("recent_records") or []
    candidate_rows = candidates.get("recent_records") or []
    arbitration_rows = arbitration.get("recent_records") or []
    continuity_rows = continuity.get("recent_records") or []
    review_rows = review.get("recent_reviews") or []
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
        "execution_started",
        "underlying_work_executed",
        "schedule_mutated",
        "scheduler_mutated",
        "preemption_executed",
        "provider_contacted",
        "message_sent",
        "source_modified",
        "approval_created",
        "authorization_created",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
    )

    checks = [
        (
            "workload_coordination_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and reliability.get("ok")
            and intake.get("contract_version") == "v1143.2"
            and execution.get("contract_version") == "v1143.5"
            and reliability.get("contract_version") == "v1143.8",
        ),
        (
            "cognition_conversation_inquiry_and_development_workload_classes",
            _passed(intake, "all_workload_classes")
            and all(
                row.get("workload_kind") in {"cognition", "conversation", "inquiry", "development"}
                for row in eligibility_rows + candidate_rows + arbitration_rows + review_rows + evidence_rows
            ),
        ),
        (
            "exact_cpu_memory_latency_and_token_budget_binding",
            _passed(intake, "bounded_budgets")
            and _passed(execution, "budget_binding")
            and all(
                all(int(row.get(key) or 0) >= 0 for key in ("cpu_budget_ms", "memory_budget_mb", "latency_budget_ms", "token_budget"))
                for row in eligibility_rows + candidate_rows + arbitration_rows + continuity_rows
            ),
        ),
        (
            "eligibility_candidate_arbitration_continuity_review_and_evidence_separation",
            all(row.get("eligibility_id") for row in candidate_rows)
            and all(row.get("candidate_id") and row.get("eligibility_id") for row in arbitration_rows)
            and all(row.get("arbitration_id") for row in continuity_rows + review_rows)
            and all(row.get("review_id") for row in evidence_rows),
        ),
        (
            "bounded_priority_action_and_fairness_class_visibility",
            _passed(intake, "bounded_priority")
            and _passed(intake, "recognized_actions")
            and all(0 <= int(row.get("priority") or 0) <= 100 for row in eligibility_rows + candidate_rows),
        ),
        (
            "advisory_intake_does_not_schedule_or_execute",
            _passed(intake, "advisory_only")
            and _passed(intake, "no_execution")
            and _passed(intake, "no_schedule_mutation"),
        ),
        (
            "deterministic_admission_reservation_deferral_and_operator_review",
            _passed(execution, "recognized_arbitration_states")
            and all(
                row.get("state")
                in {"admitted", "reserved", "deferred", "preemption_requested", "operator_review_required", "cancelled", "completed", "suppressed", "expired"}
                for row in arbitration_rows
            ),
        ),
        (
            "stale_revision_and_missing_confirmation_fail_closed",
            _passed(execution, "stale_revision_fail_closed"),
        ),
        (
            "preemption_is_structural_and_authority_inert",
            _passed(execution, "preemption_structural")
            and all(row.get("state") != "preemption_requested" or not row.get("underlying_work_executed") for row in arbitration_rows),
        ),
        (
            "restart_continuity_stale_claim_release_and_bounded_lifecycle",
            _passed(execution, "restart_continuity")
            and _passed(execution, "stale_claim_release")
            and _passed(execution, "recognized_continuity_states"),
        ),
        (
            "cpu_memory_latency_and_token_budget_enforcement",
            _passed(execution, "budget_enforcement"),
        ),
        (
            "fairness_starvation_latency_contention_preemption_and_resource_drift_review",
            _passed(reliability, "recognized_outcomes")
            and _passed(reliability, "starvation_visible")
            and _passed(reliability, "resource_drift_visible"),
        ),
        (
            "exact_reliability_and_visible_evidence_lineage",
            _passed(reliability, "exact_review_lineage")
            and _passed(reliability, "exact_evidence_lineage"),
        ),
        (
            "restrained_content_free_operator_visibility",
            _passed(reliability, "operator_visibility_content_free")
            and _passed(reliability, "advisory_evidence")
            and all(row.get("advisory_only") for row in evidence_rows),
        ),
        (
            "privacy_and_hidden_reasoning_boundaries",
            _passed(intake, "privacy")
            and _passed(execution, "privacy")
            and _false_across(components, privacy_fields),
        ),
        (
            "scheduler_policy_and_underlying_work_authority_separation",
            _passed(reliability, "no_scheduler_mutation")
            and _passed(execution, "no_underlying_execution")
            and _passed(reliability, "no_underlying_execution")
            and all(_authority_inert(component) for component in components),
        ),
        (
            "no_provider_message_source_approval_authorization_installation_promotion_or_certification",
            _false_across((intake, execution, reliability), forbidden_authority_fields[5:]),
        ),
        (
            "checkpoint_is_strictly_read_only",
            runtime_before == _tree_signature(runtime) and source_before == _tree_signature(source),
        ),
        ("source_runtime_separation", runtime != source),
        ("desktop_verification_pending", True),
    ]

    passed = sum(bool(value) for _, value in checks)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": identifier, "status": "pass" if value else "fail"} for identifier, value in checks],
        "intake": intake,
        "execution": execution,
        "reliability": reliability,
        "summary": {
            "eligibility_record_count": int(eligibility.get("record_count") or 0),
            "coordination_candidate_count": int(candidates.get("record_count") or 0),
            "arbitration_record_count": int(arbitration.get("record_count") or 0),
            "continuity_record_count": int(continuity.get("record_count") or 0),
            "reliability_review_count": int(review.get("review_count") or 0),
            "visible_evidence_count": int(evidence.get("evidence_count") or 0),
        },
        "runtime_mutated": runtime_before != _tree_signature(runtime),
        "source_modified": source_before != _tree_signature(source),
        "raw_content_exposed": False,
        "workload_payload_exposed": False,
        "conversation_exposed": False,
        "prompt_exposed": False,
        "reasoning_text_exposed": False,
        "source_content_exposed": False,
        "command_log_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "schedule_mutated": False,
        "scheduler_mutated": False,
        "underlying_work_executed": False,
        "preemption_executed": False,
        "provider_contacted": False,
        "message_sent": False,
        "approval_created": False,
        "authorization_created": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "eligibility_created_by_checkpoint": False,
        "candidate_created_by_checkpoint": False,
        "arbitration_created_by_checkpoint": False,
        "continuity_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "visible_evidence_created_by_checkpoint": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
