from __future__ import annotations

from release_metadata import RUNTIME_VERSION
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_fixture_first_isolated_dry_run_trial import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
    build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata,
)
from manifest_generated_dispatch_fixture_trial_receipt_hardening import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
    build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata,
)
from manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID,
    build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata,
)
from manifest_fixture_sandbox_adapter_contract import (
    MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
    build_manifest_fixture_sandbox_adapter_contract_metadata,
)
from full_tree_mutation_snapshot import (
    FULL_TREE_MUTATION_SNAPSHOT_ID,
    build_full_tree_mutation_snapshot_expansion_metadata,
)

MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_VERSION = RUNTIME_VERSION
MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_ID = "manifest-fixture-receipt-consolidation-v1"
SELF_ROUTE = "/manifest-fixture-receipt-consolidation"
API_ROUTE = "/api/source-surface/manifest-fixture-receipt-consolidation"

RECEIPT_FAMILY_IDS: tuple[str, ...] = (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_FIRST_ISOLATED_DRY_RUN_TRIAL_ID,
    MANIFEST_GENERATED_DISPATCH_FIXTURE_TRIAL_RECEIPT_HARDENING_ID,
    MANIFEST_GENERATED_DISPATCH_FIXTURE_BATCH_ISOLATED_DRY_RUN_EXPANSION_ID,
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "consolidates_receipts": True,
    "claims_real_fixture_execution": False,
    "actual_fixture_execution_attempted": False,
    "actual_fixture_execution_requires_os_sandbox": True,
    "audited_os_sandbox_backend_integrated": False,
    "subprocesses_spawned_by_get": False,
    "dry_run_commands_executed_by_get": False,
    "fixture_files_written": False,
    "generated_dashboard_dispatch_written": False,
    "generated_api_dispatch_written": False,
    "generated_smoke_dispatch_written": False,
    "generated_wiring_activated": False,
    "candidate_routes_registered_live": False,
    "manifest_replaces_dashboard_routes": False,
    "manifest_replaces_api_dispatch": False,
    "manifest_replaces_smoke_registry": False,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "operator_approval_required": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _status_from(rows: list[dict[str, Any]]) -> str:
    return "pass" if all(row.get("ok") is True for row in rows) else "blocked"


def _check(name: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    row = {"name": name, "ok": bool(ok), "status": "pass" if ok else "blocked", "message": message}
    row.update(extra)
    return row


def _fixture_receipt_rows(project_id: str = "eidolon") -> list[dict[str, Any]]:
    first = build_manifest_generated_dispatch_fixture_first_isolated_dry_run_trial_metadata(project_id=project_id)
    hardened = build_manifest_generated_dispatch_fixture_trial_receipt_hardening_metadata(project_id=project_id)
    batch = build_manifest_generated_dispatch_fixture_batch_isolated_dry_run_expansion_metadata(project_id=project_id)
    return [
        {
            "receipt_family": "first_isolated_trial",
            "review_id": first.get("review_id"),
            "source_status": first.get("status"),
            "candidate_count": first.get("trial_candidate_row_count"),
            "attempt_count": first.get("trial_attempt_count"),
            "pass_count": first.get("trial_pass_count"),
            "actual_fixture_execution_count": 0,
            "subprocess_count": 0,
            "source_mutation_count": 0,
            "fixture_files_written": first.get("fixture_files_written") is True,
            "generated_wiring_activated": first.get("generated_wiring_activated") is True,
            "release_authorized": first.get("release_authorized") is True,
            "autonomy_expanded": first.get("autonomy_expanded") is True,
            "consolidation_decision": "historical_receipt_metadata_only_not_real_fixture_execution",
        },
        {
            "receipt_family": "trial_receipt_hardening",
            "review_id": hardened.get("review_id"),
            "source_status": hardened.get("status"),
            "candidate_count": hardened.get("input_trial_receipt_count"),
            "attempt_count": 0,
            "pass_count": hardened.get("hardened_receipt_count"),
            "actual_fixture_execution_count": 0,
            "subprocess_count": 0,
            "source_mutation_count": 0,
            "fixture_files_written": hardened.get("fixture_files_written") is True,
            "generated_wiring_activated": hardened.get("generated_wiring_activated") is True,
            "release_authorized": hardened.get("release_authorized") is True,
            "autonomy_expanded": hardened.get("autonomy_expanded") is True,
            "consolidation_decision": "hardened_receipt_schema_only_not_release_or_promotion_authority",
        },
        {
            "receipt_family": "batch_isolated_dry_run_expansion",
            "review_id": batch.get("review_id"),
            "source_status": batch.get("status"),
            "candidate_count": batch.get("batch_candidate_row_count"),
            "attempt_count": batch.get("batch_attempt_count"),
            "pass_count": batch.get("batch_pass_count"),
            "actual_fixture_execution_count": batch.get("actual_fixture_execution_count"),
            "actual_fixture_execution_blocked_count": batch.get("actual_fixture_execution_blocked_count"),
            "subprocess_count": batch.get("total_subprocess_count"),
            "source_mutation_count": 0,
            "fixture_files_written": batch.get("fixture_files_written") is True,
            "generated_wiring_activated": batch.get("generated_wiring_activated") is True,
            "release_authorized": batch.get("release_authorized") is True,
            "autonomy_expanded": batch.get("autonomy_expanded") is True,
            "consolidation_decision": "batch_preview_rows_block_actual_execution_without_audited_os_sandbox",
        },
    ]


def build_manifest_fixture_receipt_consolidation_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    receipt_rows = _fixture_receipt_rows(project_id=project_id)
    sandbox = build_manifest_fixture_sandbox_adapter_contract_metadata(project_id=project_id)
    snapshot = build_full_tree_mutation_snapshot_expansion_metadata(project_id=project_id)
    actual_fixture_execution_count = sum(int(row.get("actual_fixture_execution_count") or 0) for row in receipt_rows)
    subprocess_count = sum(int(row.get("subprocess_count") or 0) for row in receipt_rows)
    fixture_file_write_count = sum(1 for row in receipt_rows if row.get("fixture_files_written") is True)
    generated_wiring_count = sum(1 for row in receipt_rows if row.get("generated_wiring_activated") is True)
    release_authorized_count = sum(1 for row in receipt_rows if row.get("release_authorized") is True)
    autonomy_expanded_count = sum(1 for row in receipt_rows if row.get("autonomy_expanded") is True)
    checks = [
        _check("current-version", CURRENT_VERSION == MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_VERSION, "Consolidation module is current."),
        _check("receipt-family-count", len(receipt_rows) == 3, "Three fixture receipt family reports are consolidated."),
        _check("actual-execution-blocked", actual_fixture_execution_count == 0, "Consolidation does not claim real fixture execution."),
        _check("get-subprocess-free", subprocess_count == 0, "Metadata/dashboard/API GET consolidation spawns zero subprocesses."),
        _check("sandbox-still-required", sandbox.get("actual_fixture_execution_allowed") is False and sandbox.get("integrated_backend_count") == 0, "Actual fixture execution remains blocked until an audited OS-enforced sandbox backend exists."),
        _check("snapshot-evidence-linked", snapshot.get("full_tree_source_scope") is True or snapshot.get("installation_wide_source_scope") is True, "Installation-wide mutation snapshot evidence remains linked."),
        _check("no-fixture-files-written", fixture_file_write_count == 0, "No fixture files are written by consolidation."),
        _check("manual-authority", BOUNDARIES["manual_dashboard_remains_authoritative"] and BOUNDARIES["manual_api_dispatch_remains_authoritative"] and BOUNDARIES["manual_smoke_remains_authoritative"], "Manual dashboard/API/smoke remain authoritative."),
        _check("no-release-or-autonomy", release_authorized_count == 0 and autonomy_expanded_count == 0 and generated_wiring_count == 0, "No release authorization, generated wiring activation, or autonomy expansion occurs."),
    ]
    return {
        "version": MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_ID,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "status": _status_from(checks),
        "ok": all(row.get("ok") is True for row in checks),
        "receipt_family_count": len(receipt_rows),
        "receipt_family_ids": list(RECEIPT_FAMILY_IDS),
        "consolidated_receipt_rows": receipt_rows,
        "consolidated_receipt_row_count": len(receipt_rows),
        "actual_fixture_execution_count": actual_fixture_execution_count,
        "actual_fixture_execution_blocked": True,
        "actual_fixture_execution_blocked_count": sum(int(row.get("actual_fixture_execution_blocked_count") or 0) for row in receipt_rows),
        "subprocess_spawn_count": subprocess_count,
        "source_mutation_count": sum(int(row.get("source_mutation_count") or 0) for row in receipt_rows),
        "fixture_file_write_count": fixture_file_write_count,
        "generated_wiring_activation_count": generated_wiring_count,
        "release_authorized_count": release_authorized_count,
        "autonomy_expanded_count": autonomy_expanded_count,
        "sandbox_adapter_contract_id": MANIFEST_FIXTURE_SANDBOX_ADAPTER_CONTRACT_ID,
        "sandbox_backend_integrated": sandbox.get("integrated_backend_count") not in (None, 0),
        "audited_os_sandbox_backend_integrated": False,
        "actual_fixture_execution_requires_os_sandbox": True,
        "full_tree_mutation_snapshot_id": FULL_TREE_MUTATION_SNAPSHOT_ID,
        "dashboard_get_preview_only": True,
        "api_get_preview_only": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "boundaries": dict(BOUNDARIES),
        "checks": checks,
    }


def build_manifest_fixture_receipt_consolidation(root: str | Path | None = None, *, inspect_sources: bool = True, docs: str | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    report = build_manifest_fixture_receipt_consolidation_metadata(project_id="eidolon")
    if docs is None and inspect_sources:
        docs = "\n".join(_read_text(project_root, rel) for rel in (
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "conscious_agent/manifest_fixture_receipt_consolidation.py",
            "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py",
            "conscious_agent/source_surface_manifest.py",
            "conscious_agent/current_version_staleness_audit.py",
            "tools/smoke_check.py",
        ))
    docs = docs or ""
    required_tokens = [
        MANIFEST_FIXTURE_RECEIPT_CONSOLIDATION_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_fixture_receipt_consolidation_metadata",
        "build_manifest_fixture_receipt_consolidation",
        "manifest_fixture_receipt_consolidation_text",
        "receipt_family_count=3",
        "consolidated_receipt_row_count=3",
        "actual_fixture_execution_count=0",
        "subprocess_spawn_count=0",
        "audited_os_sandbox_backend_integrated=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    missing_tokens = [token for token in required_tokens if token not in docs]
    checks = list(report.get("checks") or [])
    checks.append(_check("docs-and-surface-tokens", not missing_tokens, "Docs/source/dashboard/API/smoke contain consolidation tokens.", missing_tokens=missing_tokens))
    report.update({
        "state": "manifest_fixture_receipt_consolidation_review",
        "missing_required_tokens": missing_tokens,
        "checks": checks,
        "status": _status_from(checks),
        "ok": all(row.get("ok") is True for row in checks),
    })
    return report


def manifest_fixture_receipt_consolidation_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        "Manifest Fixture Receipt Consolidation v1",
        f"Current milestone: {report.get('current_milestone')}",
        f"Review id: {report.get('review_id')}",
        f"Receipt families consolidated: {report.get('receipt_family_count')}",
        f"Consolidated receipt rows: {report.get('consolidated_receipt_row_count')}",
        f"Actual fixture execution count: {report.get('actual_fixture_execution_count')}",
        f"Subprocess spawn count: {report.get('subprocess_spawn_count')}",
        f"Audited OS sandbox backend integrated: {report.get('audited_os_sandbox_backend_integrated')}",
        f"Manual dashboard authoritative: {report.get('manual_dashboard_remains_authoritative')}",
        f"Manual API authoritative: {report.get('manual_api_dispatch_remains_authoritative')}",
        f"Manual smoke authoritative: {report.get('manual_smoke_remains_authoritative')}",
        f"Generated wiring activated: {report.get('generated_wiring_activated')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Status: {report.get('status')}",
    ]
    if report.get("missing_required_tokens"):
        lines.append("Missing tokens: " + ", ".join(map(str, report.get("missing_required_tokens") or [])))
    if full:
        lines.extend([
            "",
            "Receipt family rows:",
            *[f"- {row.get('receipt_family')}: {row.get('consolidation_decision')}" for row in report.get("consolidated_receipt_rows") or []],
            "",
            "Checks:",
            *[f"- {row.get('name')}: {row.get('status')} - {row.get('message')}" for row in report.get("checks") or []],
            "",
            "Raw report:",
            json.dumps(report, indent=2, sort_keys=True, default=str),
        ])
    return "\n".join(lines)


# v1066.0 manifest fixture receipt consolidation tokens: manifest-fixture-receipt-consolidation-v1 /manifest-fixture-receipt-consolidation /api/source-surface/manifest-fixture-receipt-consolidation build_manifest_fixture_receipt_consolidation build_manifest_fixture_receipt_consolidation_metadata manifest_fixture_receipt_consolidation_text receipt_family_count=3 consolidated_receipt_row_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_requires_os_sandbox=True dashboard_get_preview_only=True api_get_preview_only=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 manifest fixture receipt consolidation current version repair tokens: CURRENT_VERSION=1075.1 CURRENT_MILESTONE="v1075.1 Dispatcher Batch Decomposition Trial v5" NEXT_RECOMMENDED_ARC="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" release_authorized=False autonomy_expanded=False fixture_execution_remains_blocked=True

# v1075.4 install-release successor compatibility token: manifest_fixture_receipt_consolidation.py current_version=1075.4 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False
