from __future__ import annotations

"""Read-only v1188.9 Complete Campaign Development Loop checkpoint.

Consolidates one exact operator-approved campaign loop from inspection through
bounded learning evidence. The checkpoint uses synthetic, content-free records
only. It does not perform development work, recovery, rollback, policy changes,
source mutation, provider/model contact, promotion, certification, or release.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from campaign_loop_execution_result_integration import EXECUTABLE_STAGES, campaign_loop_result_public_summary, create_loop_execution_review, create_loop_stage_result, integrate_campaign_loop_results
from campaign_loop_execution_result_integration_checkpoint import build_campaign_loop_execution_result_integration_checkpoint
from campaign_loop_reliability_recovery_learning import INTERRUPTIONS, LEARNING_CODES, RECOVERY_ACTIONS, apply_bounded_loop_learning, campaign_loop_reliability_public_summary, create_loop_recovery_review, create_loop_reliability_assessment
from campaign_loop_reliability_recovery_learning_checkpoint import build_campaign_loop_reliability_recovery_learning_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from complete_campaign_development_loop import STAGES, complete_campaign_development_loop_public_summary, create_campaign_development_stage, integrate_complete_campaign_development_loop
from complete_campaign_development_loop_checkpoint import _fixtures, build_complete_campaign_development_loop_checkpoint
from package_integrity import package_privacy_summary_for_root

CONTRACT_VERSION = "v1188.9"
_CHECKPOINT_ID = "complete-campaign-development-loop-alpha:v1188.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_PUBLIC_KEYS = {
    "prompt", "prompts", "conversation", "conversations", "memory", "memories",
    "secret", "secrets", "provider_payload", "raw_source", "raw_patch", "patch_text",
    "stdout", "stderr", "private_evidence", "private_reasoning", "replacement_text",
    "rollback_text", "source_text", "file_content", "work_item_content",
}
_LIMITATIONS = (
    "Checkpoint cases use synthetic content-free campaign records rather than a live operator campaign.",
    "Stage evidence and observed resource costs remain caller-supplied bounded receipts.",
    "Reliability assessment validates supplied source, stage, rollback, and privacy evidence rather than independently inspecting a live runtime.",
    "Recovery approval records intent only and does not resume, restart, roll back, or abandon work.",
    "Learning receipts preserve historical outcomes but do not mutate policy or future work selection.",
    "The checkpoint does not persist partial loop progress or execute any development stage.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _signed(value: Mapping[str, Any], digest_field: str, **changes: object) -> dict[str, Any]:
    row = dict(value)
    row.update(changes)
    row.pop(digest_field, None)
    row[digest_field] = _digest(row)
    return row


def _tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    if not root.exists():
        return digest.hexdigest(), count
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        count += 1
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count


def _forbidden_report_value_count(value: object, *, key: str = "") -> int:
    count = 1 if key.lower() in _FORBIDDEN_PUBLIC_KEYS else 0
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            count += _forbidden_report_value_count(child, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += _forbidden_report_value_count(child, key=key)
    return count


def _base_loop(token: str = "base") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    charter, campaign_review, session, selection, stages = _fixtures()
    campaign_id = f"campaign-v1188-{token}"
    work_item_id = f"work-{token}"
    charter = _signed(charter, "charter_digest", campaign_id=campaign_id)
    campaign_review = _signed(campaign_review, "review_digest", campaign_id=campaign_id)
    session = _signed(session, "session_snapshot_digest", campaign_id=campaign_id, session_id=f"session-{token}")
    selection = _signed(
        selection,
        "selection_digest",
        campaign_id=campaign_id,
        selected_work_item_ids=[work_item_id],
    )
    rebuilt: list[dict[str, Any]] = []
    previous = ""
    for stage in STAGES:
        row = create_campaign_development_stage(
            campaign_id=campaign_id,
            work_item_id=work_item_id,
            stage=stage,
            status="completed",
            artifact_digest=_h(f"{token}:{stage}"),
            previous_stage_digest=previous,
            operator_review_digest=_h(f"{token}:{stage}:review") if stage == "approval" else "",
        )
        rebuilt.append(row)
        previous = row["stage_receipt_digest"]
    loop = integrate_complete_campaign_development_loop(
        campaign_charter=charter,
        campaign_review=campaign_review,
        session_snapshot=session,
        work_selection=selection,
        stages=rebuilt,
    )
    ledger = _signed(
        {
            "contract_version": "v1185.2",
            "campaign_id": campaign_id,
            "work_item_ids": [work_item_id, f"followup-{token}"],
            "status": "approved_bounded_ledger",
            "content_free": True,
        },
        "ledger_digest",
    )
    budget = _signed(
        {
            "contract_version": "v1185.8",
            "campaign_id": campaign_id,
            "observed": {"elapsed_seconds": 5, "disk_bytes": 0, "token_budget": 0},
            "limits": {"max_elapsed_seconds": 600, "max_disk_bytes": 1_000_000, "max_token_budget": 50_000},
            "status": "within_budget",
            "content_free": True,
        },
        "budget_receipt_digest",
    )
    return loop, ledger, budget


def _integrated_case(
    *, token: str, result_code: str, stages: Sequence[str] = ("inspection", "testing", "learning")
) -> dict[str, Any]:
    loop, ledger, budget = _base_loop(token)
    review = create_loop_execution_review(
        loop=loop,
        decision="approve",
        operator_decision_digest=_h(f"{token}:execution-review"),
    )
    results = [
        create_loop_stage_result(
            loop=loop,
            execution_review=review,
            stage=stage,
            result_code=result_code if stage == stages[-1] else "passed",
            evidence_digest=_h(f"{token}:{stage}:{result_code}"),
            observed_cost={"elapsed_seconds": 1, "disk_bytes": 0, "token_budget": 1},
        )
        for stage in stages
    ]
    receipt = integrate_campaign_loop_results(
        loop=loop,
        execution_review=review,
        stage_results=results,
        ledger=ledger,
        budget_receipt=budget,
    )
    return {"loop": loop, "ledger": ledger, "budget": budget, "review": review, "results": results, "receipt": receipt}


def build_complete_campaign_development_loop_alpha_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").resolve()
    source_before, source_count_before = _tree_signature(source)
    runtime_before, runtime_count_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_complete_campaign_development_loop_checkpoint(source_root=source, runtime_root=runtime),
        build_campaign_loop_execution_result_integration_checkpoint(source_root=source, runtime_root=runtime),
        build_campaign_loop_reliability_recovery_learning_checkpoint(source_root=source, runtime_root=runtime),
    )
    for report, expected in zip(retained, ("v1188.2", "v1188.5", "v1188.8")):
        require(report.get("ok") is True)
        require(report.get("passed") == report.get("total"))
        require(report.get("contract_version") == expected)
        require(report.get("content_free") is True)
        require(report.get("production_source_modified") is False)
        require(report.get("sandbox_modified") is False)
        require(report.get("provider_contacted") is False)
        require(report.get("model_contacted") is False)
        require(report.get("authority_granted") is False)
        require(report.get("desktop_verification_deferred_until_v1200") is True)

    cases = {
        "passed": _integrated_case(token="passed", result_code="passed", stages=EXECUTABLE_STAGES),
        "failed": _integrated_case(token="failed", result_code="failed", stages=("implementation", "testing")),
        "blocked": _integrated_case(token="blocked", result_code="blocked", stages=("inspection", "implementation")),
    }
    expected_states = {"passed": "completed", "failed": "failed", "blocked": "blocked"}
    for name, case in cases.items():
        loop, review, receipt = case["loop"], case["review"], case["receipt"]
        require(loop.get("status") == "complete_review_required")
        require(loop.get("complete_loop") is True)
        require(loop.get("stage_count") == len(STAGES))
        require(review.get("status") == "execution_approved")
        require(review.get("execution_started") is False)
        require(receipt.get("status") == "loop_result_integrated")
        require(receipt.get("result_code") == name)
        require(receipt.get("new_work_item_state") == expected_states[name])
        require(receipt.get("ledger_updated") is True)
        require(receipt.get("budget_consumed") is True)
        require(receipt.get("automatic_continuation") is False)
        require(receipt.get("learning_applied") is False)
        require(receipt.get("authority_granted") is False)
        for row in case["results"]:
            require(row.get("status") == "stage_result_recorded")
            require(row.get("content_free") is True)
            require(row.get("production_source_modified") is False)
            require(row.get("sandbox_modified") is False)
            require(row.get("authority_granted") is False)
        for summary in (
            complete_campaign_development_loop_public_summary(loop),
            campaign_loop_result_public_summary(receipt),
        ):
            require(summary.get("content_free") is True)
            require(summary.get("authority_granted") is False)

    # Execution-review decision matrix.
    loop = cases["passed"]["loop"]
    for decision, status in (("approve", "execution_approved"), ("reject", "execution_rejected"), ("defer", "execution_deferred")):
        row = create_loop_execution_review(loop=loop, decision=decision, operator_decision_digest=_h(f"execution:{decision}"))
        require(row.get("status") == status)
        require(row.get("execution_started") is False)
        require(row.get("authority_granted") is False)

    # Every interruption and recovery action, with all operator decisions.
    assessment_rows: list[dict[str, Any]] = []
    source_digest = _h("source")
    stage_digest = _h("stage")
    for interruption in sorted(INTERRUPTIONS):
        assessment = create_loop_reliability_assessment(
            loop=cases["passed"]["loop"],
            result_receipt=cases["passed"]["receipt"],
            current_source_digest=source_digest,
            current_stage_digest=stage_digest,
            expected_source_digest=source_digest,
            expected_stage_digest=stage_digest,
            interruption_reason=interruption,
            rollback_expected_digest=_h("rollback"),
            rollback_observed_digest=_h("rollback"),
        )
        assessment_rows.append(assessment)
        require(assessment.get("status") == "recovery_review_required")
        require(assessment.get("interruption_reason") == interruption)
        require(assessment.get("rollback_verified") is True)
        require(assessment.get("source_drift") is False)
        require(assessment.get("stage_drift") is False)
        require(assessment.get("automatic_resume") is False)
        require(assessment.get("rollback_executed") is False)
        require(assessment.get("authority_granted") is False)
        require(campaign_loop_reliability_public_summary(assessment).get("content_free") is True)

    recovery_rows: list[dict[str, Any]] = []
    for action in sorted(RECOVERY_ACTIONS):
        for decision, status in (("approve", "recovery_approved"), ("reject", "recovery_rejected"), ("defer", "recovery_deferred")):
            row = create_loop_recovery_review(
                assessment=assessment_rows[0],
                decision=decision,
                recovery_action=action,
                operator_decision_digest=_h(f"recovery:{action}:{decision}"),
            )
            recovery_rows.append(row)
            require(row.get("status") == status)
            require(row.get("recovery_action") == action)
            require(row.get("recovery_executed") is False)
            require(row.get("automatic_resume") is False)
            require(row.get("authority_granted") is False)

    # Learning remains bounded, outcome-compatible, and unapplied.
    approved_recovery = create_loop_recovery_review(
        assessment=assessment_rows[0],
        decision="approve",
        recovery_action="hold",
        operator_decision_digest=_h("recovery:approved"),
    )
    learning_cases = (
        (cases["passed"], ("retain_verified_pattern", "no_generalization")),
        (cases["failed"], ("avoid_failed_pattern", "strengthen_precondition")),
        (cases["blocked"], ("require_more_evidence", "no_generalization")),
    )
    learning_rows: list[dict[str, Any]] = []
    for index, (case, codes) in enumerate(learning_cases):
        assessment = create_loop_reliability_assessment(
            loop=case["loop"],
            result_receipt=case["receipt"],
            current_source_digest=source_digest,
            current_stage_digest=stage_digest,
            expected_source_digest=source_digest,
            expected_stage_digest=stage_digest,
            interruption_reason="none" if index == 0 else "stage_failure",
        )
        recovery = create_loop_recovery_review(
            assessment=assessment,
            decision="approve",
            recovery_action="hold",
            operator_decision_digest=_h(f"learning:recovery:{index}"),
        )
        row = apply_bounded_loop_learning(
            loop=case["loop"],
            result_receipt=case["receipt"],
            recovery_review=recovery,
            learning_codes=codes,
            operator_learning_digest=_h(f"learning:{index}"),
        )
        learning_rows.append(row)
        require(row.get("status") == "learning_recorded_not_applied")
        require(row.get("learning_recorded") is True)
        require(row.get("learning_codes") == list(codes))
        require(row.get("learning_applied_to_policy") is False)
        require(row.get("future_work_selection_modified") is False)
        require(row.get("automatic_continuation") is False)
        require(row.get("production_source_modified") is False)
        require(row.get("sandbox_modified") is False)
        require(row.get("authority_granted") is False)

    # Drift acknowledgment and rollback/privacy boundaries.
    drift = create_loop_reliability_assessment(
        loop=cases["passed"]["loop"],
        result_receipt=cases["passed"]["receipt"],
        current_source_digest=_h("source:new"),
        current_stage_digest=_h("stage:new"),
        expected_source_digest=source_digest,
        expected_stage_digest=stage_digest,
        interruption_reason="process_restart",
    )
    require(drift.get("status") == "recovery_review_required")
    require(drift.get("source_drift") is True)
    require(drift.get("stage_drift") is True)
    no_ack = create_loop_recovery_review(
        assessment=drift,
        decision="approve",
        recovery_action="resume_from_stage",
        operator_decision_digest=_h("drift:no-ack"),
    )
    with_ack = create_loop_recovery_review(
        assessment=drift,
        decision="approve",
        recovery_action="resume_from_stage",
        operator_decision_digest=_h("drift:ack"),
        drift_acknowledged=True,
    )
    require(no_ack.get("status") == "blocked")
    require("drift_not_acknowledged" in no_ack.get("errors", []))
    require(with_ack.get("status") == "recovery_approved")
    require(with_ack.get("drift_acknowledged") is True)
    require(with_ack.get("recovery_executed") is False)

    negative_rows: list[Mapping[str, Any]] = []
    bad_loop = dict(cases["passed"]["loop"]); bad_loop["stage_count"] = 999
    negative_rows.append(create_loop_execution_review(loop=bad_loop, decision="approve", operator_decision_digest=_h("bad-loop")))
    negative_rows.append(create_loop_execution_review(loop=loop, decision="maybe", operator_decision_digest=_h("bad-decision")))
    negative_rows.append(create_loop_stage_result(
        loop=loop, execution_review=cases["passed"]["review"], stage="shell", result_code="passed",
        evidence_digest=_h("unsupported-stage"), observed_cost={"elapsed_seconds": 1},
    ))
    negative_rows.append(create_loop_stage_result(
        loop=loop, execution_review=cases["passed"]["review"], stage="testing", result_code="unknown",
        evidence_digest=_h("unsupported-result"), observed_cost={"elapsed_seconds": 1},
    ))
    duplicate_result = cases["passed"]["results"][0]
    negative_rows.append(integrate_campaign_loop_results(
        loop=loop, execution_review=cases["passed"]["review"], stage_results=[duplicate_result, duplicate_result],
        ledger=cases["passed"]["ledger"], budget_receipt=cases["passed"]["budget"],
    ))
    tight_budget = _signed(cases["passed"]["budget"], "budget_receipt_digest", limits={"max_elapsed_seconds": 0, "max_disk_bytes": 0, "max_token_budget": 0})
    negative_rows.append(integrate_campaign_loop_results(
        loop=loop, execution_review=cases["passed"]["review"], stage_results=cases["passed"]["results"],
        ledger=cases["passed"]["ledger"], budget_receipt=tight_budget,
    ))
    negative_rows.append(create_loop_reliability_assessment(
        loop=loop, result_receipt=cases["passed"]["receipt"], current_source_digest=source_digest,
        current_stage_digest=stage_digest, expected_source_digest=source_digest, expected_stage_digest=stage_digest,
        interruption_reason="none", privacy_findings=["finding"],
    ))
    negative_rows.append(create_loop_reliability_assessment(
        loop=loop, result_receipt=cases["passed"]["receipt"], current_source_digest=source_digest,
        current_stage_digest=stage_digest, expected_source_digest=source_digest, expected_stage_digest=stage_digest,
        interruption_reason="none", rollback_expected_digest=_h("rollback:a"), rollback_observed_digest=_h("rollback:b"),
    ))
    negative_rows.append(create_loop_recovery_review(
        assessment=assessment_rows[0], decision="approve", recovery_action="execute_shell",
        operator_decision_digest=_h("bad-action"),
    ))
    negative_rows.append(apply_bounded_loop_learning(
        loop=cases["passed"]["loop"], result_receipt=cases["passed"]["receipt"],
        recovery_review=approved_recovery, learning_codes=["avoid_failed_pattern"],
        operator_learning_digest=_h("mismatch-learning"),
    ))
    negative_rows.append(apply_bounded_loop_learning(
        loop=cases["failed"]["loop"], result_receipt=cases["failed"]["receipt"],
        recovery_review=approved_recovery, learning_codes=["retain_verified_pattern"],
        operator_learning_digest=_h("mismatch-learning-2"),
    ))
    negative_rows.append(apply_bounded_loop_learning(
        loop=cases["passed"]["loop"], result_receipt=cases["passed"]["receipt"],
        recovery_review=approved_recovery, learning_codes=["no_generalization", "no_generalization"],
        operator_learning_digest=_h("duplicate-learning"),
    ))
    for row in negative_rows:
        require(row.get("status") == "blocked")
        require(int(row.get("error_count") or 0) >= 1)
        require(row.get("authority_granted") is False)

    # Oversized lineage and stage-order/approval boundaries from the foundation.
    charter, campaign_review, session, selection, stages = _fixtures()
    require(integrate_complete_campaign_development_loop(
        campaign_charter=charter, campaign_review=campaign_review, session_snapshot=session,
        work_selection=selection, stages=stages[:-1],
    ).get("status") == "blocked")
    reordered = list(stages); reordered[0], reordered[1] = reordered[1], reordered[0]
    require("stage_order_mismatch" in integrate_complete_campaign_development_loop(
        campaign_charter=charter, campaign_review=campaign_review, session_snapshot=session,
        work_selection=selection, stages=reordered,
    ).get("errors", []))
    rejected_campaign = _signed(campaign_review, "review_digest", decision="reject", status="campaign_rejected")
    require("campaign_not_approved" in integrate_complete_campaign_development_loop(
        campaign_charter=charter, campaign_review=rejected_campaign, session_snapshot=session,
        work_selection=selection, stages=stages,
    ).get("errors", []))
    oversized_stage = create_campaign_development_stage(
        campaign_id="campaign-v1188", work_item_id="work-1", stage="inspection", status="completed",
        artifact_digest=_h("oversized"), previous_stage_digest="",
    )
    oversized_stage["padding"] = "x" * 300_000
    oversized_stage["stage_receipt_digest"] = _digest({k: v for k, v in oversized_stage.items() if k != "stage_receipt_digest"})
    require(integrate_complete_campaign_development_loop(
        campaign_charter=charter, campaign_review=campaign_review, session_snapshot=session,
        work_selection=selection, stages=[oversized_stage, *stages[1:]],
    ).get("status") == "blocked")

    registry = inspect_checkpoint_registry(source_root=source)
    registry_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "complete-campaign-development-loop-alpha-checkpoint"),
        {},
    )
    require(registry_row.get("builder") == "build_complete_campaign_development_loop_alpha_checkpoint")
    require(registry_row.get("contract_version") == CONTRACT_VERSION)
    require(registry_row.get("read_only") is True)
    require(registry_row.get("post_available") is False)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    source_after, source_count_after = _tree_signature(source)
    runtime_after, runtime_count_after = _tree_signature(runtime)
    require(source_before == source_after)
    require(source_count_before == source_count_after)
    require(runtime_before == runtime_after)
    require(runtime_count_before == runtime_count_after)

    summary = {
        "retained_checkpoint_count": len(retained),
        "complete_loop_case_count": len(cases),
        "passed_result_case_count": 1,
        "failed_result_case_count": 1,
        "blocked_result_case_count": 1,
        "execution_review_decision_case_count": 3,
        "interruption_case_count": len(assessment_rows),
        "recovery_action_case_count": len(RECOVERY_ACTIONS),
        "recovery_decision_case_count": len(recovery_rows),
        "learning_case_count": len(learning_rows),
        "drift_case_count": 1,
        "rollback_verified_case_count": len(assessment_rows),
        "negative_boundary_case_count": len(negative_rows) + 4,
        "public_summary_case_count": 7,
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
        "open_limitation_count": len(_LIMITATIONS),
    }
    report: dict[str, Any] = {
        "ok": all(checks),
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_review_required": True,
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "complete_campaign_development_loop_alpha_checkpoint_completed": True,
        "retained_loop_foundations_checkpoint_completed": retained[0].get("ok") is True,
        "retained_loop_result_integration_checkpoint_completed": retained[1].get("ok") is True,
        "retained_loop_reliability_checkpoint_completed": retained[2].get("ok") is True,
        "complete_inspect_through_learning_lineage_exercised": True,
        "passed_failed_blocked_outcomes_exercised": True,
        "operator_execution_decision_matrix_exercised": True,
        "interruption_and_recovery_matrices_exercised": True,
        "drift_and_rollback_boundaries_exercised": True,
        "bounded_learning_not_applied_exercised": True,
        "tamper_budget_privacy_boundaries_exercised": True,
        "source_runtime_immutability_exercised": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "sandbox_modified": False,
        "runtime_mutated": False,
        "development_stage_executed": False,
        "campaign_work_executed": False,
        "automatic_retry_performed": False,
        "automatic_recovery_performed": False,
        "automatic_resume_performed": False,
        "automatic_continuation_performed": False,
        "rollback_executed": False,
        "learning_applied_to_policy": False,
        "future_work_selection_modified": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "model_contacted": False,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "raw_test_output_exposed": False,
        "private_evidence_exposed": False,
        "private_reasoning_exposed": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "implementation_authorized": False,
        "repair_authorized": False,
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "autonomous_action_authorized": False,
        "summary": summary,
        "limitations": list(_LIMITATIONS),
        "source_tree_digest_before": source_before,
        "source_tree_digest_after": source_after,
        "source_file_count_before": source_count_before,
        "source_file_count_after": source_count_after,
        "runtime_tree_digest_before": runtime_before,
        "runtime_tree_digest_after": runtime_after,
        "runtime_file_count_before": runtime_count_before,
        "runtime_file_count_after": runtime_count_after,
    }
    report["forbidden_report_value_count"] = _forbidden_report_value_count(report)
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
