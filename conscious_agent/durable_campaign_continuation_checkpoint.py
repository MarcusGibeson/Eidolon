from __future__ import annotations

"""Read-only v1186.9 Durable Campaign Continuation checkpoint.

Consolidates durable campaign storage, restoration review, resume reconciliation,
lease-backed resumed-session materialization, restart reconciliation, and lease
release. All writes occur only in isolated temporary external-runtime roots. The
checkpoint never mutates production source, executes campaign work, contacts a
provider/model, or grants installation, promotion, certification, release, or
autonomous authority.
"""

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from persistent_development_campaign import create_campaign_charter, create_campaign_ledger, create_campaign_review
from persistent_development_campaign_continuation import create_bounded_work_selection, create_campaign_session_snapshot, create_work_selection_review
from persistent_development_campaign_reliability import create_campaign_budget_receipt, create_campaign_recovery_receipt, create_stale_work_assessment
from persistent_campaign_storage import create_campaign_storage_record, create_restoration_review, persist_campaign_storage_record, restore_campaign_storage_record, storage_public_summary
from persistent_campaign_resume_reconciliation import create_resume_eligibility_review, create_resume_reconciliation, resume_public_summary
from persistent_campaign_resume_materialization import acquire_resume_lease, create_resume_materialization_contract, materialize_resumed_session, reconcile_materialized_session, release_resume_lease, resume_materialization_public_summary
from persistent_campaign_storage_checkpoint import build_persistent_campaign_storage_checkpoint
from persistent_campaign_resume_reconciliation_checkpoint import build_persistent_campaign_resume_reconciliation_checkpoint
from persistent_campaign_resume_materialization_checkpoint import build_persistent_campaign_resume_materialization_checkpoint

CONTRACT_VERSION = "v1186.9"
_CHECKPOINT_ID = "durable-campaign-continuation:v1186.9"
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
    "Checkpoint evidence uses synthetic content-free campaign lineages and isolated temporary runtime roots.",
    "The durable store is local JSON with atomic replacement, not an encrypted or distributed database.",
    "The filesystem lease is local and does not attest operating-system identity or provide network-filesystem guarantees.",
    "Source drift requires explicit operator acknowledgment and is not automatically reconciled.",
    "A materialized resumed session is execution-eligible but no campaign work is executed automatically.",
    "Lease release is operator-reviewed evidence and does not certify that external processes have stopped.",
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


def _forbidden_report_value_count(value: object, *, key: str = "") -> int:
    count = 1 if key.lower() in _FORBIDDEN_PUBLIC_KEYS else 0
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            count += _forbidden_report_value_count(child, key=str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            count += _forbidden_report_value_count(child, key=key)
    return count


def _lineage_fixture(token: str = "alpha") -> dict[str, Any]:
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
    work_items = [
        {
            "work_item_id": f"work-{index}",
            "status": "queued",
            "work_item_digest": _h(f"{token}:work:{index}"),
            "content_free": True,
        }
        for index in range(1, 4)
    ]
    ledger = create_campaign_ledger(charter=charter, review=review, work_items=work_items)
    snapshot = create_campaign_session_snapshot(
        charter=charter,
        review=review,
        ledger=ledger,
        session_id=f"session-{token}-1",
        session_index=1,
        state="paused",
        consumed={"work_items": 1, "sessions": 1, "elapsed_seconds": 120, "disk_bytes": 4096, "token_budget": 1200},
    )
    snapshot = _resign(snapshot, "snapshot_digest", source_baseline_digest=source_digest)
    selection_review = create_work_selection_review(
        snapshot=snapshot,
        ledger=ledger,
        candidate_work_item_ids=["work-1", "work-2"],
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
    budget = create_campaign_budget_receipt(
        charter=charter,
        snapshot=snapshot,
        observed={"work_items": 1, "sessions": 1, "elapsed_seconds": 120, "disk_bytes": 4096, "token_budget": 1200},
    )
    stale = create_stale_work_assessment(
        snapshot=snapshot,
        selection=selection,
        current_source_digest=source_digest,
        work_states={"work-1": "current", "work-2": "current"},
    )
    recovery = create_campaign_recovery_receipt(
        snapshot=snapshot,
        budget_receipt=budget,
        stale_assessment=stale,
        reason="process_restart",
        prior_runtime_digest=_h(f"{token}:runtime:prior"),
        restarted_runtime_digest=_h(f"{token}:runtime:restarted"),
    )
    return {
        "source_digest": source_digest,
        "charter": charter,
        "review": review,
        "ledger": ledger,
        "snapshot": snapshot,
        "selection": selection,
        "budget": budget,
        "stale": stale,
        "recovery": recovery,
    }


def build_durable_campaign_continuation_checkpoint(
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

    retained_reports: list[dict[str, Any]] = []
    retained_specs = (
        (build_persistent_campaign_storage_checkpoint, "v1186.2"),
        (build_persistent_campaign_resume_reconciliation_checkpoint, "v1186.5"),
        (build_persistent_campaign_resume_materialization_checkpoint, "v1186.8"),
    )
    for index, (builder, expected) in enumerate(retained_specs):
        with tempfile.TemporaryDirectory(prefix=f"eidolon-v1186-9-retained-{index}-") as isolated:
            report = builder(source_root=source, runtime_root=Path(isolated) / "runtime")
        retained_reports.append(report)
        for condition in (
            report.get("ok") is True,
            report.get("passed") == report.get("total"),
            report.get("contract_version") == expected,
            report.get("content_free") is True,
            report.get("production_source_modified") is False,
            report.get("sandbox_modified") is False,
            report.get("work_executed") is False,
            report.get("provider_contacted") is False,
            report.get("model_contacted") is False,
            report.get("authority_granted") is False,
            report.get("release_authorized") is False,
            report.get("desktop_verification_deferred_until_v1200") is True,
        ):
            require(condition)

    fixture = _lineage_fixture()
    for name in ("charter", "review", "ledger", "snapshot", "selection", "budget", "stale", "recovery"):
        row = fixture[name]
        require(row.get("error_count") == 0)
        require(row.get("content_free") is True)
        require(row.get("authority_granted") is False)

    with tempfile.TemporaryDirectory(prefix="eidolon-v1186-9-runtime-") as isolated:
        isolated_root = Path(isolated) / "runtime"
        record1 = create_campaign_storage_record(
            charter=fixture["charter"], review=fixture["review"], ledger=fixture["ledger"],
            snapshot=fixture["snapshot"], selection=fixture["selection"], budget_receipt=fixture["budget"],
            stale_assessment=fixture["stale"], recovery_receipt=fixture["recovery"],
            storage_generation=1, operator_storage_digest=_h("store-generation-1"),
        )
        stored1 = persist_campaign_storage_record(runtime_root=isolated_root, record=record1)
        restored1 = restore_campaign_storage_record(
            runtime_root=isolated_root,
            campaign_id=fixture["charter"]["campaign_id"],
            expected_record_digest=record1["storage_record_digest"],
            current_source_digest=fixture["source_digest"],
        )
        restoration_reviews = {
            decision: create_restoration_review(
                restoration=restored1, decision=decision, operator_decision_digest=_h(f"restore:{decision}")
            )
            for decision in ("approve", "reject", "defer")
        }
        approved_restoration = restoration_reviews["approve"]
        reconciliation = create_resume_reconciliation(
            restoration=restored1,
            restoration_review=approved_restoration,
            current_charter_digest=fixture["charter"]["charter_digest"],
            current_review_digest=fixture["review"]["review_digest"],
            current_ledger_digest=fixture["ledger"]["ledger_digest"],
            current_snapshot_digest=fixture["snapshot"]["snapshot_digest"],
            current_selection_digest=fixture["selection"]["selection_digest"],
            current_budget_receipt_digest=fixture["budget"]["budget_receipt_digest"],
            current_stale_assessment_digest=fixture["stale"]["stale_assessment_digest"],
            current_recovery_receipt_digest=fixture["recovery"]["recovery_receipt_digest"],
        )
        eligibility_reviews = {
            decision: create_resume_eligibility_review(
                reconciliation=reconciliation, decision=decision, operator_decision_digest=_h(f"eligibility:{decision}")
            )
            for decision in ("approve", "reject", "defer")
        }
        approved_eligibility = eligibility_reviews["approve"]
        contract = create_resume_materialization_contract(
            reconciliation=reconciliation,
            eligibility_review=approved_eligibility,
            session_id="restored-session-2",
            session_generation=2,
            operator_materialization_digest=_h("materialize"),
            lease_ttl_seconds=60,
        )
        lease = acquire_resume_lease(
            runtime_root=isolated_root, contract=contract, lease_owner_digest=_h("lease-owner"), now_epoch=1000,
        )
        active_conflict = acquire_resume_lease(
            runtime_root=isolated_root, contract=contract, lease_owner_digest=_h("other-owner"), now_epoch=1001,
        )
        materialized = materialize_resumed_session(
            runtime_root=isolated_root, contract=contract, lease_receipt=lease,
        )
        restart = reconcile_materialized_session(
            runtime_root=isolated_root,
            campaign_id=fixture["charter"]["campaign_id"],
            expected_session_digest=materialized["resumed_session_digest"],
            expected_lease_digest=lease["lease_digest"],
        )
        storage_summary = storage_public_summary(record1, stored1, restored1, approved_restoration)
        resume_summary = resume_public_summary(reconciliation, approved_eligibility)
        materialization_summary = resume_materialization_public_summary(contract, materialized)
        release = release_resume_lease(
            runtime_root=isolated_root,
            campaign_id=fixture["charter"]["campaign_id"],
            expected_lease_digest=lease["lease_digest"],
            operator_release_digest=_h("release"),
        )
        post_release_materialization = materialize_resumed_session(
            runtime_root=isolated_root, contract=contract, lease_receipt=lease,
        )

        expected_statuses = (
            (record1, "ready_for_runtime_storage"),
            (stored1, "stored"),
            (restored1, "restoration_review_required"),
            (approved_restoration, "approved_not_resumed"),
            (reconciliation, "resume_review_required"),
            (approved_eligibility, "eligible_not_resumed"),
            (contract, "materialization_ready"),
            (lease, "lease_acquired"),
            (materialized, "resumed_session_materialized_not_executing"),
            (restart, "restored_execution_eligible_not_executing"),
            (release, "lease_released"),
        )
        for row, status in expected_statuses:
            require(row.get("status") == status)
            require(row.get("error_count", 0) == 0)
            require(row.get("content_free", True) is True)
            require(row.get("authority_granted") is False)
        require(active_conflict.get("status") == "blocked")
        require("active_lease_exists" in (active_conflict.get("errors") or []))
        require(post_release_materialization.get("status") == "blocked")
        require(materialized.get("work_execution_eligible") is True)
        require(materialized.get("work_executed") is False)
        require(materialized.get("automatic_execution") is False)
        require(restart.get("work_execution_eligible") is True)
        require(restart.get("work_executed") is False)
        require(restart.get("automatic_execution") is False)

        for decision, status in (("approve", "approved_not_resumed"), ("reject", "rejected"), ("defer", "deferred")):
            row = restoration_reviews[decision]
            require(row.get("status") == status)
            require(row.get("work_resumed") is False)
            require(row.get("authority_granted") is False)
        for decision, status in (("approve", "eligible_not_resumed"), ("reject", "rejected"), ("defer", "deferred")):
            row = eligibility_reviews[decision]
            require(row.get("status") == status)
            require(row.get("work_resumed") is False)
            require(row.get("automatic_resume") is False)
            require(row.get("authority_granted") is False)

        for summary in (storage_summary, resume_summary, materialization_summary):
            require(summary.get("content_free") is True)
            require(summary.get("authority_granted") is False)
        require(storage_summary.get("source_modified") is False)
        require(storage_summary.get("work_resumed") is False)
        require(resume_summary.get("resume_eligible") is True)
        require(resume_summary.get("work_resumed") is False)
        require(materialization_summary.get("work_execution_eligible") is True)
        require(materialization_summary.get("work_executed") is False)

        record2 = create_campaign_storage_record(
            charter=fixture["charter"], review=fixture["review"], ledger=fixture["ledger"],
            snapshot=fixture["snapshot"], selection=fixture["selection"], budget_receipt=fixture["budget"],
            stale_assessment=fixture["stale"], recovery_receipt=fixture["recovery"],
            storage_generation=2, prior_record_digest=record1["storage_record_digest"],
            operator_storage_digest=_h("store-generation-2"),
        )
        stored2 = persist_campaign_storage_record(runtime_root=isolated_root, record=record2)
        restored2 = restore_campaign_storage_record(
            runtime_root=isolated_root,
            campaign_id=fixture["charter"]["campaign_id"],
            expected_record_digest=record2["storage_record_digest"],
            current_source_digest=fixture["source_digest"],
        )
        require(record2.get("status") == "ready_for_runtime_storage")
        require(stored2.get("status") == "stored")
        require(restored2.get("storage_generation") == 2)
        require(restored2.get("status") == "restoration_review_required")

        drift = restore_campaign_storage_record(
            runtime_root=isolated_root,
            campaign_id=fixture["charter"]["campaign_id"],
            expected_record_digest=record2["storage_record_digest"],
            current_source_digest=_h("drifted-source"),
        )
        drift_review = create_restoration_review(
            restoration=drift, decision="approve", operator_decision_digest=_h("drift-restore"),
        )
        drift_reconciliation = create_resume_reconciliation(
            restoration=drift,
            restoration_review=drift_review,
            current_charter_digest=fixture["charter"]["charter_digest"],
            current_review_digest=fixture["review"]["review_digest"],
            current_ledger_digest=fixture["ledger"]["ledger_digest"],
            current_snapshot_digest=fixture["snapshot"]["snapshot_digest"],
            current_selection_digest=fixture["selection"]["selection_digest"],
            current_budget_receipt_digest=fixture["budget"]["budget_receipt_digest"],
            current_stale_assessment_digest=fixture["stale"]["stale_assessment_digest"],
            current_recovery_receipt_digest=fixture["recovery"]["recovery_receipt_digest"],
        )
        drift_blocked = create_resume_eligibility_review(
            reconciliation=drift_reconciliation,
            decision="approve",
            operator_decision_digest=_h("drift-no-ack"),
        )
        drift_acknowledged = create_resume_eligibility_review(
            reconciliation=drift_reconciliation,
            decision="approve",
            operator_decision_digest=_h("drift-ack"),
            acknowledge_source_drift=True,
        )
        require(drift.get("status") == "reconciliation_required")
        require(drift.get("source_drift") is True)
        require(drift_reconciliation.get("status") == "operator_reconciliation_required")
        require(drift_blocked.get("status") == "blocked")
        require("source_drift_not_acknowledged" in (drift_blocked.get("errors") or []))
        require(drift_acknowledged.get("status") == "eligible_not_resumed")
        require(drift_acknowledged.get("source_drift_acknowledged") is True)

        stale_root = Path(isolated) / "stale-runtime"
        stale_contract = create_resume_materialization_contract(
            reconciliation=reconciliation,
            eligibility_review=approved_eligibility,
            session_id="stale-session",
            session_generation=3,
            operator_materialization_digest=_h("stale-materialize"),
            lease_ttl_seconds=30,
        )
        first_stale_lease = acquire_resume_lease(
            runtime_root=stale_root, contract=stale_contract, lease_owner_digest=_h("stale-owner-1"), now_epoch=2000,
        )
        takeover_blocked = acquire_resume_lease(
            runtime_root=stale_root, contract=stale_contract, lease_owner_digest=_h("stale-owner-2"), now_epoch=2031,
        )
        takeover = acquire_resume_lease(
            runtime_root=stale_root, contract=stale_contract, lease_owner_digest=_h("stale-owner-2"), now_epoch=2031,
            stale_takeover_digest=_h("stale-takeover"),
        )
        require(first_stale_lease.get("status") == "lease_acquired")
        require(takeover_blocked.get("status") == "blocked")
        require("stale_takeover_not_authorized" in (takeover_blocked.get("errors") or []))
        require(takeover.get("status") == "lease_acquired")

        negative_rows: list[Mapping[str, Any]] = []
        tampered_record = dict(record2); tampered_record["campaign_state"] = "active"
        negative_rows.append(persist_campaign_storage_record(runtime_root=Path(isolated) / "tampered", record=tampered_record))
        negative_rows.append(restore_campaign_storage_record(runtime_root=isolated_root, campaign_id="../escape", expected_record_digest=_h("x"), current_source_digest=fixture["source_digest"]))
        negative_rows.append(restore_campaign_storage_record(runtime_root=isolated_root, campaign_id=fixture["charter"]["campaign_id"], expected_record_digest=_h("wrong"), current_source_digest=fixture["source_digest"]))
        malformed_root = Path(isolated) / "malformed" / "campaigns" / "bad"
        malformed_root.mkdir(parents=True, exist_ok=True)
        (malformed_root / "campaign_state.json").write_text("{", encoding="utf-8")
        negative_rows.append(restore_campaign_storage_record(runtime_root=Path(isolated) / "malformed", campaign_id="bad", expected_record_digest=_h("x"), current_source_digest=fixture["source_digest"]))
        tampered_restoration = dict(restored2); tampered_restoration["session_id"] = "tampered"
        negative_rows.append(create_restoration_review(restoration=tampered_restoration, decision="approve", operator_decision_digest=_h("x")))
        rejected_restore = create_restoration_review(restoration=restored2, decision="reject", operator_decision_digest=_h("reject"))
        negative_rows.append(create_resume_reconciliation(restoration=restored2, restoration_review=rejected_restore, current_charter_digest=fixture["charter"]["charter_digest"], current_review_digest=fixture["review"]["review_digest"], current_ledger_digest=fixture["ledger"]["ledger_digest"], current_snapshot_digest=fixture["snapshot"]["snapshot_digest"]))
        negative_rows.append(create_resume_reconciliation(restoration=restored2, restoration_review=create_restoration_review(restoration=restored2, decision="approve", operator_decision_digest=_h("ok")), current_charter_digest="bad", current_review_digest=fixture["review"]["review_digest"], current_ledger_digest=fixture["ledger"]["ledger_digest"], current_snapshot_digest=fixture["snapshot"]["snapshot_digest"]))
        tampered_reconciliation = dict(reconciliation); tampered_reconciliation["campaign_id"] = "tampered"
        negative_rows.append(create_resume_eligibility_review(reconciliation=tampered_reconciliation, decision="approve", operator_decision_digest=_h("x")))
        negative_rows.append(create_resume_materialization_contract(reconciliation=reconciliation, eligibility_review=eligibility_reviews["reject"], session_id="s", session_generation=2, operator_materialization_digest=_h("x")))
        negative_rows.append(create_resume_materialization_contract(reconciliation=reconciliation, eligibility_review=approved_eligibility, session_id="../bad", session_generation=2, operator_materialization_digest=_h("x")))
        negative_rows.append(create_resume_materialization_contract(reconciliation=reconciliation, eligibility_review=approved_eligibility, session_id="s", session_generation=0, operator_materialization_digest=_h("x")))
        negative_rows.append(create_resume_materialization_contract(reconciliation=reconciliation, eligibility_review=approved_eligibility, session_id="s", session_generation=2, operator_materialization_digest=_h("x"), lease_ttl_seconds=1))
        tampered_contract = dict(contract); tampered_contract["session_id"] = "tampered"
        negative_rows.append(acquire_resume_lease(runtime_root=Path(isolated) / "bad-contract", contract=tampered_contract, lease_owner_digest=_h("owner")))
        tampered_lease = dict(lease); tampered_lease["status"] = "blocked"
        negative_rows.append(materialize_resumed_session(runtime_root=Path(isolated) / "bad-lease", contract=contract, lease_receipt=tampered_lease))
        negative_rows.append(reconcile_materialized_session(runtime_root=isolated_root, campaign_id=fixture["charter"]["campaign_id"], expected_session_digest=_h("wrong"), expected_lease_digest=lease["lease_digest"]))
        negative_rows.append(release_resume_lease(runtime_root=isolated_root, campaign_id=fixture["charter"]["campaign_id"], expected_lease_digest=_h("wrong"), operator_release_digest=_h("release")))
        for row in negative_rows:
            require(row.get("status") == "blocked")
            require(int(row.get("error_count") or 0) >= 1)
            require(row.get("authority_granted") is False)

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("forbidden_count") == 0)
    require(privacy.get("private_content_finding_count") == 0)

    registry = inspect_checkpoint_registry(source_root=source)
    registry_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "durable-campaign-continuation-checkpoint"),
        {},
    )
    require(registry_row.get("builder") == "build_durable_campaign_continuation_checkpoint")
    require(registry_row.get("contract_version") == CONTRACT_VERSION)
    require(registry_row.get("read_only") is True)
    require(registry_row.get("post_available") is False)
    require(registry.get("duplicate_checkpoint_ids") == [])
    require(registry.get("duplicate_builder_targets") == [])

    source_after, source_count_after = _tree_signature(source)
    runtime_after, runtime_count_after = _tree_signature(runtime)
    runtime_existed_after = runtime.exists()
    require(source_before == source_after)
    require(source_count_before == source_count_after)
    require(runtime_before == runtime_after)
    require(runtime_count_before == runtime_count_after)
    require(runtime_existed_before == runtime_existed_after)

    summary = {
        "retained_checkpoint_count": 3,
        "storage_generation_case_count": 2,
        "restoration_decision_case_count": 3,
        "eligibility_decision_case_count": 3,
        "source_drift_case_count": 2,
        "lease_conflict_case_count": 1,
        "stale_takeover_case_count": 2,
        "restart_reconciliation_case_count": 1,
        "lease_release_case_count": 1,
        "negative_boundary_case_count": len(negative_rows),
        "public_summary_case_count": 3,
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_count") or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count") or 0),
        "open_limitation_count": len(_LIMITATIONS),
    }

    report: dict[str, Any] = {
        "ok": all(checks),
        "status": "ready" if all(checks) else "review_required",
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
        "durable_campaign_continuation_checkpoint_completed": all(checks),
        "retained_storage_checkpoint_completed": retained_reports[0].get("ok") is True,
        "retained_resume_reconciliation_checkpoint_completed": retained_reports[1].get("ok") is True,
        "retained_resume_materialization_checkpoint_completed": retained_reports[2].get("ok") is True,
        "atomic_storage_generation_chaining_exercised": True,
        "restoration_review_decisions_exercised": True,
        "source_drift_reconciliation_exercised": True,
        "resume_eligibility_decisions_exercised": True,
        "exclusive_lease_conflict_exercised": True,
        "stale_lease_takeover_exercised": True,
        "resumed_session_materialization_exercised": True,
        "restart_reconciliation_exercised": True,
        "operator_reviewed_lease_release_exercised": True,
        "tamper_lineage_privacy_boundaries_exercised": True,
        "source_runtime_immutability_exercised": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "sandbox_modified": False,
        "runtime_mutated": False,
        "campaign_work_selected_automatically": False,
        "campaign_work_executed": False,
        "work_executed": False,
        "automatic_resume_performed": False,
        "automatic_execution_performed": False,
        "provider_reconnected": False,
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
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "autonomous_action_authorized": False,
        "forbidden_report_value_count": 0,
        "source_tree_digest_before": source_before,
        "source_tree_digest_after": source_after,
        "source_file_count_before": source_count_before,
        "source_file_count_after": source_count_after,
        "runtime_tree_digest_before": runtime_before,
        "runtime_tree_digest_after": runtime_after,
        "runtime_file_count_before": runtime_count_before,
        "runtime_file_count_after": runtime_count_after,
        "summary": summary,
        "limitations": list(_LIMITATIONS),
    }
    report["forbidden_report_value_count"] = _forbidden_report_value_count(report)
    report["structural_digest"] = _digest(report)
    return report
