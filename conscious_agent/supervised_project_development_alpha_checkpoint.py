from __future__ import annotations

"""Read-only v1184.9 Supervised Project Development Alpha checkpoint.

Consolidates the complete v1184 governed project-development arc: exact stage
lineage from inspection through retest, operator-facing result presentation,
accountable outcome learning, and adversarial stale-source, drift, interruption,
rollback, and privacy review. The checkpoint uses synthetic digest-only contracts,
reads no private runtime state, performs no development stage, and grants no
approval, execution, source-application, installation, promotion, certification,
publication, release, or autonomous authority.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from supervised_project_development_foundations_checkpoint import build_supervised_project_development_foundations_checkpoint
from supervised_project_development_lineage import MAX_CONTRACT_BYTES, STAGES, create_project_stage_receipt, integrate_supervised_project_development, supervised_project_development_public_summary
from supervised_project_outcome_learning import create_accountable_outcome_learning, create_project_result_presentation, project_outcome_public_summary
from supervised_project_outcome_learning_checkpoint import build_supervised_project_outcome_learning_checkpoint
from supervised_project_reliability_recovery import create_project_reliability_receipt, supervised_project_reliability_public_summary
from supervised_project_reliability_recovery_checkpoint import build_supervised_project_reliability_recovery_checkpoint

CONTRACT_VERSION = "v1184.9"
_CHECKPOINT_ID = "supervised-project-development-alpha:v1184.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_PUBLIC_KEYS = {
    "prompt", "prompts", "conversation", "conversations", "memory", "memories",
    "secret", "secrets", "provider_payload", "raw_source", "raw_patch", "patch_text",
    "stdout", "stderr", "private_evidence", "private_reasoning", "replacement_text",
    "rollback_text", "source_text", "file_content",
}
_OUTCOME_LESSONS = {
    "accepted": ("retain_approach",),
    "rejected": ("avoid_rejected_approach",),
    "failed": ("strengthen_failure_checks",),
    "repaired": ("retain_repair_pattern",),
}
_LIMITATIONS = (
    "Checkpoint evidence is synthetic, content-free, and read-only; it does not execute the project-development loop.",
    "Outcome learning remains an operator-reviewed historical record and does not automatically change policy or work selection.",
    "Interruption recovery is represented by evidence contracts; durable resume execution remains separately governed.",
    "Rollback evidence is verified, but rollback execution is not performed or authorized by this checkpoint.",
    "The integrated lineage remains bounded to one ordered nine-stage project-development flow per contract.",
    "Historical verifier debt remains separately reportable and is not converted into a current checkpoint pass.",
    "Desktop Codex and native-provider review remain deferred until the v1200 decision gate.",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _h(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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


def _signed_copy(value: Mapping[str, Any], digest_field: str, **changes: object) -> dict[str, Any]:
    row = dict(value)
    row.update(changes)
    row.pop(digest_field, None)
    row[digest_field] = _digest(row)
    return row


def _complete_lineage(*, terminal_status: str = "completed", token: str = "complete") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    previous = ""
    for index, stage in enumerate(STAGES):
        status = terminal_status if index == len(STAGES) - 1 else "completed"
        row = create_project_stage_receipt(
            stage=stage,
            status=status,
            artifact_digest=_h(f"{token}:{stage}:artifact"),
            previous_receipt_digest=previous,
            operator_review_digest=_h(f"{token}:{stage}:review"),
            public_evidence_digest=_h(f"{token}:{stage}:evidence"),
        )
        rows.append(row)
        previous = row["receipt_digest"]
    return integrate_supervised_project_development(rows)


def _outcome_case(outcome: str) -> dict[str, Any]:
    lineage = _complete_lineage(token=outcome)
    presentation = create_project_result_presentation(
        lineage=lineage,
        outcome=outcome,
        operator_decision_digest=_h(f"{outcome}:operator-decision"),
        result_evidence_digest=_h(f"{outcome}:result-evidence"),
        rollback_available=outcome in {"failed", "repaired"},
    )
    learning = create_accountable_outcome_learning(
        presentation=presentation,
        lesson_codes=_OUTCOME_LESSONS[outcome],
        operator_learning_review_digest=_h(f"{outcome}:learning-review"),
    )
    reliability = create_project_reliability_receipt(
        lineage=lineage,
        presentation=presentation,
        learning=learning,
        expected_source_digest=_h(f"{outcome}:source"),
        observed_source_digest=_h(f"{outcome}:source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"],
        interruption_state="resumed" if outcome == "repaired" else "not_interrupted",
        interruption_receipt_digest=_h(f"{outcome}:interruption"),
        rollback_expected_digest=_h(f"{outcome}:rollback") if presentation["rollback_available"] else "",
        rollback_observed_digest=_h(f"{outcome}:rollback") if presentation["rollback_available"] else "",
    )
    return {
        "outcome": outcome,
        "lineage": lineage,
        "presentation": presentation,
        "learning": learning,
        "reliability": reliability,
        "lineage_public": supervised_project_development_public_summary(lineage),
        "outcome_public": project_outcome_public_summary(presentation, learning),
        "reliability_public": supervised_project_reliability_public_summary(reliability),
    }


def _forbidden_report_value_count(value: object, *, key: str = "") -> int:
    count = 0
    lowered_key = key.lower()
    if lowered_key in _FORBIDDEN_PUBLIC_KEYS:
        count += 1
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            count += _forbidden_report_value_count(child, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += _forbidden_report_value_count(child, key=key)
    return count


def build_supervised_project_development_alpha_checkpoint(
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").resolve()
    source_before, source_file_count_before = _tree_signature(source)
    runtime_before, runtime_file_count_before = _tree_signature(runtime)
    runtime_existed_before = runtime.exists()
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_supervised_project_development_foundations_checkpoint(source_root=source, runtime_root=runtime),
        build_supervised_project_outcome_learning_checkpoint(source_root=source, runtime_root=runtime),
        build_supervised_project_reliability_recovery_checkpoint(source_root=source, runtime_root=runtime),
    )
    expected_versions = ("v1184.2", "v1184.5", "v1184.8")
    for report, expected_version in zip(retained, expected_versions):
        require(report.get("ok") is True)
        require(report.get("passed") == report.get("total"))
        require(report.get("contract_version") == expected_version)
        require(report.get("read_only") is True)
        require(report.get("content_free") is True)
        for key in (
            "production_source_modified", "sandbox_modified", "execution_invoked",
            "provider_contacted", "model_contacted", "approval_created", "authority_granted",
            "release_authorized",
        ):
            require(report.get(key) is False)
        require(report.get("desktop_verification_deferred_until_v1200") is True)

    cases = [_outcome_case(outcome) for outcome in ("accepted", "rejected", "failed", "repaired")]
    for case in cases:
        lineage = case["lineage"]
        presentation = case["presentation"]
        learning = case["learning"]
        reliability = case["reliability"]
        require(lineage.get("status") == "complete_review_required")
        require(lineage.get("complete_lineage") is True)
        require(lineage.get("stage_count") == len(STAGES))
        require(lineage.get("completed_stage_count") == len(STAGES))
        require(lineage.get("current_stage") == "retest")
        require(lineage.get("next_stage") == "")
        require(lineage.get("error_count") == 0)
        require(presentation.get("status") == "ready_for_operator_review")
        require(presentation.get("outcome") == case["outcome"])
        require(presentation.get("lineage_digest") == lineage.get("lineage_digest"))
        require(presentation.get("terminal_receipt_digest") == lineage.get("terminal_receipt_digest"))
        require(learning.get("status") == "learning_recorded")
        require(learning.get("outcome") == case["outcome"])
        require(learning.get("lineage_digest") == lineage.get("lineage_digest"))
        require(learning.get("presentation_digest") == presentation.get("presentation_digest"))
        require(learning.get("historical_truth_preserved") is True)
        require(learning.get("generalized_beyond_evidence") is False)
        require(reliability.get("status") == "recovery_review_ready")
        require(reliability.get("lineage_digest") == lineage.get("lineage_digest"))
        require(reliability.get("presentation_digest") == presentation.get("presentation_digest"))
        require(reliability.get("learning_digest") == learning.get("learning_digest"))
        require(reliability.get("stale_source_detected") is False)
        require(reliability.get("privacy_finding_count") == 0)
        require(reliability.get("error_count") == 0)
        require(reliability.get("historical_truth_preserved") is True)
        for public in (case["lineage_public"], case["outcome_public"], case["reliability_public"]):
            require(public.get("content_free") is True)
            require(public.get("authority_granted") is False)
            require(_forbidden_report_value_count(public) == 0)
        for artifact in (lineage, presentation, learning, reliability):
            for key in (
                "production_source_modified", "sandbox_modified", "execution_invoked",
                "approval_created", "authority_granted", "source_application_authorized",
                "release_authorized",
            ):
                if key in artifact:
                    require(artifact.get(key) is False)

    repaired = next(case for case in cases if case["outcome"] == "repaired")
    lineage = repaired["lineage"]
    presentation = repaired["presentation"]
    learning = repaired["learning"]

    interruption_states = ("not_interrupted", "paused", "resumed", "abandoned")
    interruption_rows = []
    for state in interruption_states:
        row = create_project_reliability_receipt(
            lineage=lineage,
            presentation=presentation,
            learning=learning,
            expected_source_digest=_h("recovery-source"),
            observed_source_digest=_h("recovery-source"),
            expected_terminal_digest=lineage["terminal_receipt_digest"],
            interruption_state=state,
            interruption_receipt_digest=_h(f"interruption:{state}"),
            rollback_expected_digest=_h("rollback"),
            rollback_observed_digest=_h("rollback"),
        )
        interruption_rows.append(row)
        require(row.get("status") == "recovery_review_ready")
        require(row.get("interruption_state") == state)
        require(row.get("rollback_verified") is True)
        require(row.get("rollback_executed") is False)
        require(row.get("operator_review_required_for_next_action") is True)

    negative_rows: list[dict[str, Any]] = []
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("drift"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("different-rollback"),
    ))
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="unsupported",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="paused",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"), privacy_findings=("content_finding",),
    ))
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=_h("wrong-terminal"), interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    tampered_lineage = dict(lineage)
    tampered_lineage["stage_count"] = 8
    negative_rows.append(create_project_reliability_receipt(
        lineage=tampered_lineage, presentation=presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    tampered_presentation = dict(presentation)
    tampered_presentation["outcome"] = "failed"
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=tampered_presentation, learning=learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    tampered_learning = dict(learning)
    tampered_learning["lesson_codes"] = ["no_generalization"]
    negative_rows.append(create_project_reliability_receipt(
        lineage=lineage, presentation=presentation, learning=tampered_learning,
        expected_source_digest=_h("source"), observed_source_digest=_h("source"),
        expected_terminal_digest=lineage["terminal_receipt_digest"], interruption_state="resumed",
        interruption_receipt_digest=_h("interrupt"), rollback_expected_digest=_h("rollback"),
        rollback_observed_digest=_h("rollback"),
    ))
    for row in negative_rows:
        require(row.get("status") == "blocked")
        require(int(row.get("error_count") or 0) >= 1)
        require(row.get("authority_granted") is False)
        require(row.get("rollback_executed") is False)

    partial_rows: list[dict[str, Any]] = []
    previous = ""
    for stage in STAGES[:-1]:
        row = create_project_stage_receipt(
            stage=stage,
            status="completed",
            artifact_digest=_h(f"partial:{stage}"),
            previous_receipt_digest=previous,
            operator_review_digest=_h(f"partial:{stage}:review"),
        )
        partial_rows.append(row)
        previous = row["receipt_digest"]
    partial_lineage = integrate_supervised_project_development(partial_rows)
    require(partial_lineage.get("status") == "in_progress_review_required")
    require(partial_lineage.get("next_stage") == "retest")
    require(create_project_result_presentation(
        lineage=partial_lineage, outcome="accepted", operator_decision_digest=_h("decision"),
        result_evidence_digest=_h("evidence"),
    ).get("status") == "blocked")

    first = create_project_stage_receipt(stage="inspection", status="completed", artifact_digest=_h("first"))
    rejected = create_project_stage_receipt(
        stage="deficiency_review", status="rejected", artifact_digest=_h("reject"),
        previous_receipt_digest=first["receipt_digest"], operator_review_digest=_h("reject-review"),
    )
    continued = create_project_stage_receipt(
        stage="specification", status="completed", artifact_digest=_h("continued"),
        previous_receipt_digest=rejected["receipt_digest"], operator_review_digest=_h("continued-review"),
    )
    require("continued_after_terminal_stage" in integrate_supervised_project_development([first, rejected, continued]).get("errors", []))

    oversized = [{"stage": "inspection", "blob": "x" * (MAX_CONTRACT_BYTES + 1)}]
    require("oversized_contract" in integrate_supervised_project_development(oversized).get("errors", []))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(privacy.get("source_only") is True)
    require(privacy.get("forbidden_count") == 0)
    require(privacy.get("private_content_finding_count") == 0)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "supervised-project-development-alpha-checkpoint"),
        {},
    )
    require(descriptor.get("builder") == "build_supervised_project_development_alpha_checkpoint")
    require(descriptor.get("contract_version") == CONTRACT_VERSION)
    require(descriptor.get("read_only") is True)
    require(descriptor.get("post_available") is False)
    require(registry.get("duplicate_checkpoint_ids") == [])
    require(registry.get("duplicate_builder_targets") == [])

    source_after, source_file_count_after = _tree_signature(source)
    runtime_after, runtime_file_count_after = _tree_signature(runtime)
    require(source_before == source_after)
    require(source_file_count_before == source_file_count_after)
    require(runtime_before == runtime_after)
    require(runtime_file_count_before == runtime_file_count_after)
    require(runtime.exists() is runtime_existed_before)

    summaries = {
        "lineage": repaired["lineage_public"],
        "outcomes": [case["outcome_public"] for case in cases],
        "reliability": [supervised_project_reliability_public_summary(row) for row in interruption_rows],
    }
    summary = {
        "retained_checkpoint_count": len(retained),
        "governed_stage_count": len(STAGES),
        "complete_lineage_case_count": len(cases),
        "outcome_case_count": len(cases),
        "learning_case_count": len(cases),
        "reliability_ready_case_count": len(cases) + len(interruption_rows),
        "interruption_state_case_count": len(interruption_rows),
        "negative_boundary_case_count": len(negative_rows) + 4,
        "rollback_evidence_case_count": sum(1 for case in cases if case["presentation"].get("rollback_available")) + len(interruption_rows),
        "public_summary_case_count": 1 + len(cases) + len(interruption_rows),
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_count") or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count") or 0),
        "source_file_count": source_file_count_after,
        "runtime_file_count": runtime_file_count_after,
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
        "supervised_project_development_alpha_checkpoint_completed": True,
        "retained_project_development_foundations_checkpoint_completed": retained[0].get("ok") is True,
        "retained_project_outcome_learning_checkpoint_completed": retained[1].get("ok") is True,
        "retained_project_reliability_recovery_checkpoint_completed": retained[2].get("ok") is True,
        "inspection_through_retest_lineage_exercised": True,
        "operator_result_presentation_exercised": True,
        "accepted_rejected_failed_repaired_outcomes_exercised": True,
        "accountable_outcome_learning_exercised": True,
        "historical_truth_preservation_exercised": True,
        "stale_source_and_drift_rejection_exercised": True,
        "interruption_recovery_states_exercised": True,
        "rollback_evidence_verification_exercised": True,
        "privacy_hardening_exercised": True,
        "tamper_and_lineage_boundary_rejection_exercised": True,
        "source_runtime_immutability_exercised": True,
        "summary": summary,
        "summaries": summaries,
        "limitations": list(_LIMITATIONS),
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "sandbox_modified": False,
        "runtime_mutated": False,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "raw_test_output_exposed": False,
        "private_evidence_exposed": False,
        "private_reasoning_exposed": False,
        "inspection_executed": False,
        "planning_executed": False,
        "implementation_executed": False,
        "tests_executed": False,
        "repair_executed": False,
        "retest_executed": False,
        "rollback_executed": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "autonomous_action_authorized": False,
        "desktop_verification_deferred_until_v1200": True,
        "source_tree_digest_before": source_before,
        "source_tree_digest_after": source_after,
        "runtime_tree_digest_before": runtime_before,
        "runtime_tree_digest_after": runtime_after,
    }
    report["forbidden_report_value_count"] = _forbidden_report_value_count(report)
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    report["ok"] = report["ok"] and report["forbidden_report_value_count"] == 0
    return report
