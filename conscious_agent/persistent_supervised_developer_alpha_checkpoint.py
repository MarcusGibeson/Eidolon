from __future__ import annotations

"""Read-only v1185.9 Persistent Supervised Developer Alpha checkpoint.

Consolidates the v1185 campaign charter, operator review, bounded work ledger,
multi-session continuation, pause/resume transitions, bounded work selection,
resource-limit evidence, stale-work assessment, and interruption/outage/restart
recovery receipts. The checkpoint uses synthetic digest-only contracts, performs
no campaign work, persists no runtime state, contacts no provider or model, and
grants no implementation, installation, promotion, certification, release, or
autonomous authority.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from persistent_development_campaign import create_campaign_charter, create_campaign_ledger, create_campaign_review, campaign_public_summary
from persistent_development_campaign_continuation import create_bounded_work_selection, create_campaign_session_snapshot, create_session_transition, create_work_selection_review, continuation_public_summary
from persistent_development_campaign_reliability import create_campaign_budget_receipt, create_campaign_recovery_receipt, create_stale_work_assessment, reliability_public_summary
from persistent_development_campaign_foundations_checkpoint import build_persistent_development_campaign_foundations_checkpoint
from persistent_development_campaign_continuation_checkpoint import build_persistent_development_campaign_continuation_checkpoint
from persistent_development_campaign_reliability_checkpoint import build_persistent_development_campaign_reliability_checkpoint

CONTRACT_VERSION = "v1185.9"
_CHECKPOINT_ID = "persistent-supervised-developer-alpha:v1185.9"
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
    "Checkpoint evidence is synthetic, digest-only, content-free, and read-only; it does not execute campaign work.",
    "Campaign persistence remains represented by caller-supplied snapshots and receipts rather than owned durable storage.",
    "Budget observations are caller-supplied evidence and are not direct operating-system resource measurements.",
    "Recovery receipts require later operator review and do not automatically resume, reconnect, or reselect work.",
    "Stale-work reconciliation is detected but no replacement work is automatically selected.",
    "The checkpoint verifies one bounded campaign lineage at a time and does not coordinate multiple campaigns.",
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


def _resign(value: Mapping[str, Any], digest_field: str, **changes: object) -> dict[str, Any]:
    row = dict(value)
    row.update(changes)
    row.pop(digest_field, None)
    row[digest_field] = _digest(row)
    return row


def _campaign_fixture(*, state: str = "active", token: str = "alpha", work_count: int = 3) -> dict[str, Any]:
    source_digest = _h(f"{token}:source")
    charter = create_campaign_charter(
        campaign_id=f"campaign-{token}",
        source_baseline_digest=source_digest,
        scope_digest=_h(f"{token}:scope"),
        goal_digests=[_h(f"{token}:goal:1"), _h(f"{token}:goal:2")],
        limits={
            "max_work_items": 8,
            "max_sessions": 6,
            "max_elapsed_seconds": 3600,
            "max_disk_bytes": 1_000_000,
            "max_token_budget": 50_000,
        },
    )
    review = create_campaign_review(
        charter=charter,
        decision="approve",
        operator_decision_digest=_h(f"{token}:campaign-review"),
    )
    items = [
        {
            "work_item_id": f"work-{index}",
            "status": "queued",
            "work_item_digest": _h(f"{token}:work:{index}"),
            "content_free": True,
        }
        for index in range(1, work_count + 1)
    ]
    ledger = create_campaign_ledger(charter=charter, review=review, work_items=items)
    snapshot = create_campaign_session_snapshot(
        charter=charter,
        review=review,
        ledger=ledger,
        session_id=f"session-{token}",
        session_index=1,
        state=state,
        consumed={"work_items": 0, "sessions": 1, "elapsed_seconds": 10, "disk_bytes": 0, "token_budget": 0},
    )
    snapshot = _resign(snapshot, "snapshot_digest", source_baseline_digest=source_digest)
    selection_review = create_work_selection_review(
        snapshot=snapshot,
        ledger=ledger,
        candidate_work_item_ids=[item["work_item_id"] for item in items[:2]],
        decision="approve",
        operator_decision_digest=_h(f"{token}:selection-review"),
    )
    selection = create_bounded_work_selection(
        charter=charter,
        snapshot=snapshot,
        ledger=ledger,
        selection_review=selection_review,
        max_items=2,
    )
    return {
        "source_digest": source_digest,
        "charter": charter,
        "review": review,
        "ledger": ledger,
        "snapshot": snapshot,
        "selection_review": selection_review,
        "selection": selection,
    }


def _forbidden_report_value_count(value: object, *, key: str = "") -> int:
    count = 1 if key.lower() in _FORBIDDEN_PUBLIC_KEYS else 0
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            count += _forbidden_report_value_count(child, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += _forbidden_report_value_count(child, key=key)
    return count


def build_persistent_supervised_developer_alpha_checkpoint(
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or os.environ.get("EIDOLON_DATA_DIR") or source / "data").resolve()
    source_before, source_count_before = _tree_signature(source)
    runtime_before, runtime_count_before = _tree_signature(runtime)
    runtime_existed_before = runtime.exists()
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = (
        build_persistent_development_campaign_foundations_checkpoint(source_root=source, runtime_root=runtime),
        build_persistent_development_campaign_continuation_checkpoint(source_root=source, runtime_root=runtime),
        build_persistent_development_campaign_reliability_checkpoint(source_root=source, runtime_root=runtime),
    )
    for report, expected in zip(retained, ("v1185.2", "v1185.5", "v1185.8")):
        require(report.get("ok") is True)
        require(report.get("passed") == report.get("total"))
        require(report.get("contract_version") == expected)
        require(report.get("read_only") is True)
        require(report.get("content_free") is True)
        for key in (
            "production_source_modified", "sandbox_modified", "execution_invoked",
            "provider_contacted", "model_contacted", "authority_granted", "release_authorized",
        ):
            require(report.get(key) is False)
        require(report.get("desktop_verification_deferred_until_v1200") is True)

    fixture = _campaign_fixture()
    charter = fixture["charter"]
    review = fixture["review"]
    ledger = fixture["ledger"]
    snapshot = fixture["snapshot"]
    selection_review = fixture["selection_review"]
    selection = fixture["selection"]

    foundation_summary = campaign_public_summary(charter, review, ledger)
    continuation_summary = continuation_public_summary(snapshot, selection)
    for row, status in (
        (charter, "ready_for_review"),
        (review, "approved_not_started"),
        (ledger, "approved_bounded_ledger"),
        (snapshot, "session_snapshot_ready"),
        (selection_review, "selection_approved"),
        (selection, "bounded_selection_ready"),
    ):
        require(row.get("status") == status)
        require(row.get("error_count") == 0)
        require(row.get("content_free") is True)
        require(row.get("authority_granted") is False)
    require(foundation_summary.get("work_started") is False)
    require(foundation_summary.get("authority_granted") is False)
    require(continuation_summary.get("work_executed") is False)
    require(continuation_summary.get("automatic_resume") is False)
    require(continuation_summary.get("authority_granted") is False)

    campaign_decision_cases = []
    for decision, status in (("approve", "approved_not_started"), ("reject", "rejected"), ("defer", "deferred")):
        row = create_campaign_review(
            charter=charter,
            decision=decision,
            operator_decision_digest=_h(f"campaign:{decision}"),
        )
        campaign_decision_cases.append(row)
        require(row.get("status") == status)
        require(row.get("work_started") is False)
        require(row.get("authority_granted") is False)
        require(row.get("release_authorized") is False)

    empty_ledger = create_campaign_ledger(charter=charter, review=review)
    require(empty_ledger.get("status") == "approved_empty_ledger")
    require(empty_ledger.get("work_item_count") == 0)
    require(empty_ledger.get("work_started") is False)

    selection_decision_cases = []
    for decision, status in (("approve", "selection_approved"), ("reject", "selection_rejected"), ("defer", "selection_deferred")):
        row = create_work_selection_review(
            snapshot=snapshot,
            ledger=ledger,
            candidate_work_item_ids=["work-1"],
            decision=decision,
            operator_decision_digest=_h(f"selection:{decision}"),
        )
        selection_decision_cases.append(row)
        require(row.get("status") == status)
        require(row.get("work_executed") is False)
        require(row.get("authority_granted") is False)
        require(row.get("implementation_authorized") is False)

    transition_specs = (
        ("ready", "active"), ("ready", "abandoned"),
        ("active", "paused"), ("active", "completed"), ("active", "abandoned"),
        ("paused", "active"), ("paused", "abandoned"),
    )
    transition_rows = []
    for index, (current, requested) in enumerate(transition_specs):
        row_fixture = _campaign_fixture(state=current, token=f"transition-{index}", work_count=1)
        row = create_session_transition(
            snapshot=row_fixture["snapshot"],
            requested_state=requested,
            operator_transition_digest=_h(f"transition:{current}:{requested}"),
        )
        transition_rows.append(row)
        require(row.get("status") == "transition_recorded")
        require(row.get("from_state") == current)
        require(row.get("to_state") == requested)
        require(row.get("durable_write_performed") is False)
        require(row.get("work_executed") is False)
        require(row.get("automatic_resume") is False)
        require(row.get("authority_granted") is False)

    observed_within = {
        "work_items": 2,
        "sessions": 1,
        "elapsed_seconds": 100,
        "disk_bytes": 10_000,
        "token_budget": 2_000,
    }
    budget_within = create_campaign_budget_receipt(charter=charter, snapshot=snapshot, observed=observed_within)
    require(budget_within.get("status") == "budget_within_limits")
    require(budget_within.get("exceeded_limits") == [])
    require(budget_within.get("budget_enforced") is True)
    require(budget_within.get("work_executed") is False)
    require(budget_within.get("authority_granted") is False)

    budget_exhaustion_cases = []
    budget_limits = {
        "work_items": 9,
        "sessions": 7,
        "elapsed_seconds": 3601,
        "disk_bytes": 1_000_001,
        "token_budget": 50_001,
    }
    for key, value in budget_limits.items():
        row = create_campaign_budget_receipt(charter=charter, snapshot=snapshot, observed={key: value})
        budget_exhaustion_cases.append(row)
        require(row.get("status") == "budget_exhausted")
        require(row.get("exceeded_limits") == [key])
        require(row.get("budget_enforced") is True)
        require(row.get("work_executed") is False)
        require(row.get("authority_granted") is False)

    stale_cases = []
    stale_specs = (
        (fixture["source_digest"], {"work-1": "current", "work-2": "current"}, "work_current", False, 0),
        (fixture["source_digest"], {"work-1": "stale", "work-2": "current"}, "reconciliation_required", False, 1),
        (_h("drifted-source"), {"work-1": "current", "work-2": "current"}, "reconciliation_required", True, 0),
        (fixture["source_digest"], {"work-1": "completed", "work-2": "cancelled"}, "work_current", False, 0),
        (fixture["source_digest"], {"work-1": "blocked", "work-2": "current"}, "work_current", False, 0),
    )
    for current_source, states, status, source_drift, stale_count in stale_specs:
        row = create_stale_work_assessment(
            snapshot=snapshot,
            selection=selection,
            current_source_digest=current_source,
            work_states=states,
        )
        stale_cases.append(row)
        require(row.get("status") == status)
        require(row.get("source_drift") is source_drift)
        require(len(row.get("stale_work_item_ids") or []) == stale_count)
        require(row.get("automatic_reselection") is False)
        require(row.get("operator_review_required") is True)
        require(row.get("work_executed") is False)
        require(row.get("authority_granted") is False)

    current_assessment = stale_cases[0]
    recovery_rows = []
    for reason in ("interruption", "provider_outage", "process_restart", "operator_pause"):
        row = create_campaign_recovery_receipt(
            snapshot=snapshot,
            budget_receipt=budget_within,
            stale_assessment=current_assessment,
            reason=reason,
            prior_runtime_digest=_h(f"{reason}:prior"),
            restarted_runtime_digest=_h(f"{reason}:restarted"),
        )
        recovery_rows.append(row)
        require(row.get("status") == "recovery_review_required")
        require(row.get("reason") == reason)
        require(row.get("durable_resume_performed") is False)
        require(row.get("work_executed") is False)
        require(row.get("provider_contacted") is False)
        require(row.get("model_contacted") is False)
        require(row.get("operator_review_required") is True)
        require(row.get("authority_granted") is False)

    reliability_summaries = [reliability_public_summary(budget_within, current_assessment, row) for row in recovery_rows]
    for summary in reliability_summaries:
        require(summary.get("content_free") is True)
        require(summary.get("work_executed") is False)
        require(summary.get("durable_resume_performed") is False)
        require(summary.get("operator_review_required") is True)
        require(summary.get("authority_granted") is False)

    negative_rows: list[Mapping[str, Any]] = []
    tampered_charter = dict(charter); tampered_charter["scope_digest"] = _h("tampered")
    negative_rows.append(create_campaign_review(charter=tampered_charter, decision="approve", operator_decision_digest=_h("x")))
    tampered_review = dict(review); tampered_review["decision"] = "reject"
    negative_rows.append(create_campaign_ledger(charter=charter, review=tampered_review))
    tampered_ledger = dict(ledger); tampered_ledger["work_item_count"] = 99
    negative_rows.append(create_campaign_session_snapshot(charter=charter, review=review, ledger=tampered_ledger, session_id="s", session_index=1))
    tampered_snapshot = dict(snapshot); tampered_snapshot["state"] = "paused"
    negative_rows.append(create_work_selection_review(snapshot=tampered_snapshot, ledger=ledger, candidate_work_item_ids=["work-1"], decision="approve", operator_decision_digest=_h("x")))
    negative_rows.append(create_work_selection_review(snapshot=snapshot, ledger=ledger, candidate_work_item_ids=["unknown"], decision="approve", operator_decision_digest=_h("x")))
    negative_rows.append(create_work_selection_review(snapshot=snapshot, ledger=ledger, candidate_work_item_ids=["work-1", "work-1"], decision="approve", operator_decision_digest=_h("x")))
    rejected_selection_review = selection_decision_cases[1]
    negative_rows.append(create_bounded_work_selection(charter=charter, snapshot=snapshot, ledger=ledger, selection_review=rejected_selection_review, max_items=1))
    negative_rows.append(create_bounded_work_selection(charter=charter, snapshot=snapshot, ledger=ledger, selection_review=selection_review, max_items=9))
    negative_rows.append(create_session_transition(snapshot=snapshot, requested_state="ready", operator_transition_digest=_h("bad")))
    negative_rows.append(create_campaign_budget_receipt(charter=charter, snapshot=snapshot, observed={"unknown": 1}))
    tampered_selection = dict(selection); tampered_selection["selected_count"] = 99
    negative_rows.append(create_stale_work_assessment(snapshot=snapshot, selection=tampered_selection, current_source_digest=fixture["source_digest"], work_states={"work-1": "current", "work-2": "current"}))
    negative_rows.append(create_stale_work_assessment(snapshot=snapshot, selection=selection, current_source_digest="bad", work_states={"work-1": "current", "work-2": "current"}))
    negative_rows.append(create_stale_work_assessment(snapshot=snapshot, selection=selection, current_source_digest=fixture["source_digest"], work_states={"work-1": "nonsense", "work-2": "current"}))
    negative_rows.append(create_campaign_recovery_receipt(snapshot=snapshot, budget_receipt=budget_exhaustion_cases[0], stale_assessment=current_assessment, reason="process_restart", prior_runtime_digest=_h("a"), restarted_runtime_digest=_h("b")))
    negative_rows.append(create_campaign_recovery_receipt(snapshot=snapshot, budget_receipt=budget_within, stale_assessment=current_assessment, reason="unsupported", prior_runtime_digest=_h("a"), restarted_runtime_digest=_h("b")))
    tampered_budget = dict(budget_within); tampered_budget["status"] = "budget_exhausted"
    negative_rows.append(create_campaign_recovery_receipt(snapshot=snapshot, budget_receipt=tampered_budget, stale_assessment=current_assessment, reason="interruption", prior_runtime_digest=_h("a"), restarted_runtime_digest=_h("b")))
    mismatched_fixture = _campaign_fixture(token="mismatch", work_count=2)
    mismatched_fixture_budget = create_campaign_budget_receipt(
        charter=mismatched_fixture["charter"],
        snapshot=mismatched_fixture["snapshot"],
        observed={"sessions": 1},
    )
    negative_rows.append(create_campaign_recovery_receipt(
        snapshot=snapshot,
        budget_receipt=mismatched_fixture_budget,
        stale_assessment=current_assessment,
        reason="interruption",
        prior_runtime_digest=_h("a"),
        restarted_runtime_digest=_h("b"),
    ))

    for row in negative_rows:
        require(row.get("status") == "blocked")
        require(int(row.get("error_count") or 0) >= 1)
        require(row.get("authority_granted") is False)
        require(row.get("work_executed", False) is False)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok") is True)
    require(privacy.get("source_only") is True)
    require(privacy.get("forbidden_count") == 0)
    require(privacy.get("private_content_finding_count") == 0)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "persistent-supervised-developer-alpha-checkpoint"),
        {},
    )
    require(descriptor.get("builder") == "build_persistent_supervised_developer_alpha_checkpoint")
    require(descriptor.get("contract_version") == CONTRACT_VERSION)
    require(descriptor.get("read_only") is True)
    require(descriptor.get("post_available") is False)
    require(registry.get("duplicate_checkpoint_ids") == [])
    require(registry.get("duplicate_builder_targets") == [])

    source_after, source_count_after = _tree_signature(source)
    runtime_after, runtime_count_after = _tree_signature(runtime)
    require(source_before == source_after)
    require(source_count_before == source_count_after)
    require(runtime_before == runtime_after)
    require(runtime_count_before == runtime_count_after)
    require(runtime.exists() is runtime_existed_before)

    summary = {
        "retained_checkpoint_count": len(retained),
        "campaign_decision_case_count": len(campaign_decision_cases),
        "ledger_state_case_count": 2,
        "selection_decision_case_count": len(selection_decision_cases),
        "valid_transition_case_count": len(transition_rows),
        "budget_within_limit_case_count": 1,
        "budget_exhaustion_case_count": len(budget_exhaustion_cases),
        "stale_work_case_count": len(stale_cases),
        "recovery_reason_case_count": len(recovery_rows),
        "negative_boundary_case_count": len(negative_rows),
        "public_summary_case_count": 2 + len(reliability_summaries),
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_count") or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count") or 0),
        "source_file_count": source_count_after,
        "runtime_file_count": runtime_count_after,
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
        "persistent_supervised_developer_alpha_checkpoint_completed": True,
        "retained_campaign_foundations_checkpoint_completed": retained[0].get("ok") is True,
        "retained_campaign_continuation_checkpoint_completed": retained[1].get("ok") is True,
        "retained_campaign_reliability_checkpoint_completed": retained[2].get("ok") is True,
        "campaign_scope_goals_limits_and_approval_exercised": True,
        "bounded_work_ledger_exercised": True,
        "multi_session_pause_resume_exercised": True,
        "bounded_operator_work_selection_exercised": True,
        "all_resource_budget_classes_exercised": True,
        "stale_work_and_source_drift_exercised": True,
        "interruption_outage_restart_recovery_exercised": True,
        "tamper_lineage_privacy_boundaries_exercised": True,
        "source_runtime_immutability_exercised": True,
        "summary": summary,
        "summaries": {
            "campaign": foundation_summary,
            "continuation": continuation_summary,
            "recovery": reliability_summaries,
        },
        "limitations": list(_LIMITATIONS),
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "sandbox_modified": False,
        "runtime_mutated": False,
        "campaign_state_persisted": False,
        "campaign_work_selected_automatically": False,
        "campaign_work_executed": False,
        "durable_resume_performed": False,
        "automatic_reselection_performed": False,
        "provider_reconnected": False,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "raw_test_output_exposed": False,
        "private_evidence_exposed": False,
        "private_reasoning_exposed": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "implementation_authorized": False,
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
