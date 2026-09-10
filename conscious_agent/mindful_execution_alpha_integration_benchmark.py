from __future__ import annotations

"""Read-only integration contract for the v1230 Mindful Execution Alpha milestone.

This module consolidates the already-governed v1225-v1229 execution arc.  It
never reads operator runtime records and never grants execution authority.  Its
purpose is to prove that the five retained checkpoints still form one coherent
Path 3 lifecycle with explicit goal, uncertainty, intervention, recovery, and
revisable-learning boundaries.
"""

from pathlib import Path
from typing import Any, Callable

CONTRACT_VERSION = "v1230.8"
MILESTONE_NAME = "Mindful Execution Alpha"
ROADMAP_PATH = "Balanced Mind-and-Action Path 3"
RETAINED_CHECKPOINTS = (
    ("prepare", "v1225.9", "supervised-work-dispatch-execution-session-preparation-checkpoint"),
    ("authorize_and_launch", "v1226.9", "execution-session-authorization-bounded-launch-checkpoint"),
    ("monitor_and_intervene", "v1227.9", "live-execution-monitoring-operator-intervention-checkpoint"),
    ("pause_resume_cancel_recover", "v1228.9", "execution-session-pause-resume-cancel-recovery-checkpoint"),
    ("outcome_reflect_learn", "v1229.9", "execution-outcome-reflection-learning-integration-checkpoint"),
)

AUTHORITY_FLAGS = {
    "benchmark_evidence_authorized": True,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "queue_mutation_authorized": False,
    "schedule_mutation_authorized": False,
    "launch_authorized": False,
    "pause_authorized": False,
    "resume_authorized": False,
    "cancel_authorized": False,
    "cognition_write_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}


def _builders() -> tuple[tuple[str, str, str, Callable[..., dict[str, Any]]], ...]:
    try:
        from supervised_work_dispatch_execution_session_preparation_checkpoint import build_supervised_work_dispatch_execution_session_preparation_checkpoint
        from execution_session_authorization_bounded_launch_checkpoint import build_execution_session_authorization_bounded_launch_checkpoint
        from live_execution_monitoring_operator_intervention_checkpoint import build_live_execution_monitoring_operator_intervention_checkpoint
        from execution_session_pause_resume_cancel_recovery_checkpoint import build_execution_session_pause_resume_cancel_recovery_checkpoint
        from execution_outcome_reflection_learning_integration_checkpoint import build_execution_outcome_reflection_learning_integration_checkpoint
    except ImportError:
        from supervised_work_dispatch_execution_session_preparation_checkpoint import (
            build_supervised_work_dispatch_execution_session_preparation_checkpoint,
        )
        from execution_session_authorization_bounded_launch_checkpoint import (
            build_execution_session_authorization_bounded_launch_checkpoint,
        )
        from live_execution_monitoring_operator_intervention_checkpoint import (
            build_live_execution_monitoring_operator_intervention_checkpoint,
        )
        from execution_session_pause_resume_cancel_recovery_checkpoint import (
            build_execution_session_pause_resume_cancel_recovery_checkpoint,
        )
        from execution_outcome_reflection_learning_integration_checkpoint import (
            build_execution_outcome_reflection_learning_integration_checkpoint,
        )

    functions = (
        build_supervised_work_dispatch_execution_session_preparation_checkpoint,
        build_execution_session_authorization_bounded_launch_checkpoint,
        build_live_execution_monitoring_operator_intervention_checkpoint,
        build_execution_session_pause_resume_cancel_recovery_checkpoint,
        build_execution_outcome_reflection_learning_integration_checkpoint,
    )
    return tuple((*descriptor, function) for descriptor, function in zip(RETAINED_CHECKPOINTS, functions))


def build_mindful_execution_alpha_contract(*, source_root: str | Path | None = None) -> dict[str, Any]:
    """Consolidate the retained checkpoint contracts without reading runtime data."""

    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    stages: list[dict[str, Any]] = []
    for stage_id, expected_version, checkpoint_id, builder in _builders():
        report = builder(source_root=source)
        stages.append({
            "stage_id": stage_id,
            "checkpoint_id": checkpoint_id,
            "expected_contract_version": expected_version,
            "reported_contract_version": str(report.get("contract_version") or ""),
            "ok": bool(report.get("ok")),
            "read_only": bool(report.get("read_only")),
            "content_free": bool(report.get("content_free")),
            "runtime_data_read": bool(report.get("runtime_data_read")),
            "source_modified": bool(report.get("source_modified")),
            "authority_granted": bool(report.get("authority_granted")),
            "provider_contacted": bool(report.get("provider_contacted")),
            "commands_executed": bool(report.get("commands_executed")),
            "tests_executed": bool(report.get("tests_executed")),
            "project_modified": bool(report.get("project_modified")),
            "cognition_written": bool(report.get("cognition_written")),
            "passed_checks": int(report.get("passed") or 0),
        })

    versions_match = all(row["reported_contract_version"] == row["expected_contract_version"] for row in stages)
    retained_ok = all(
        row["ok"]
        and row["read_only"]
        and row["content_free"]
        and not row["runtime_data_read"]
        and not row["source_modified"]
        and not row["authority_granted"]
        and not row["provider_contacted"]
        and not row["commands_executed"]
        and not row["tests_executed"]
        and not row["project_modified"]
        and not row["cognition_written"]
        for row in stages
    )
    complete_stage_order = [row["stage_id"] for row in stages] == [row[0] for row in RETAINED_CHECKPOINTS]
    ok = versions_match and retained_ok and complete_stage_order
    return {
        "ok": ok,
        "status": "mindful_execution_alpha_contract_ready" if ok else "mindful_execution_alpha_contract_blocked",
        "contract_version": CONTRACT_VERSION,
        "milestone_name": MILESTONE_NAME,
        "roadmap_path": ROADMAP_PATH,
        "stage_count": len(stages),
        "stages": stages,
        "complete_stage_order": complete_stage_order,
        "retained_versions_match": versions_match,
        "retained_checkpoints_pass": retained_ok,
        "ordinary_chat_required": True,
        "restart_recovery_required": True,
        "adversarial_authority_testing_required": True,
        "goal_alignment_preserved": True,
        "uncertainty_preserved": True,
        "operator_intervention_preserved": True,
        "outcome_reflection_preserved": True,
        "learning_revisable": True,
        "historical_receipts_remain_authoritative": True,
        "runtime_data_read": False,
        "runtime_data_written": False,
        "source_modified": False,
        "content_free": True,
        "read_only": True,
        **AUTHORITY_FLAGS,
    }
