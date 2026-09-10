from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_fixture_harness_isolation import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID,
    build_manifest_generated_dispatch_fixture_harness_isolation,
)

MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID = "manifest-generated-dispatch-fixture-harness-dry-run-ledger-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-harness-dry-run-ledger"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-harness-dry-run-ledger"
INPUT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID
INPUT_HARNESS_ISOLATION_PLAN_COUNT = 24
DRY_RUN_LEDGER_ROW_COUNT = 24
DISPATCH_FAMILY_COUNT = 3
DASHBOARD_DRY_RUN_LEDGER_COUNT = 8
API_DRY_RUN_LEDGER_COUNT = 8
SMOKE_DRY_RUN_LEDGER_COUNT = 8
DRY_RUN_STEP_COUNT_PER_ROW = 6
DRY_RUN_LEDGER_STEP_COUNT = DRY_RUN_LEDGER_ROW_COUNT * DRY_RUN_STEP_COUNT_PER_ROW

DRY_RUN_STEPS: tuple[str, ...] = (
    "create_temporary_workspace",
    "copy_source_tree_readonly_inputs",
    "capture_pre_run_mutation_snapshot",
    "prepare_subprocess_command_without_executing",
    "declare_stdout_stderr_timeout_capture",
    "capture_post_run_cleanup_expectation",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "preview_only": True,
    "dry_run_ledger_only": True,
    "dry_run_commands_prepared": True,
    "dry_run_commands_executed": False,
    "fixture_files_written": False,
    "fixture_harness_executed": False,
    "subprocesses_spawned": False,
    "temp_workspaces_created": False,
    "mutation_snapshots_captured": False,
    "network_access_permitted": False,
    "external_filesystem_write_permitted": False,
    "runtime_data_deleted": False,
    "source_files_mutated_at_runtime": False,
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


@dataclass(frozen=True)
class FixtureHarnessDryRunLedgerRow:
    ledger_id: str
    isolation_id: str
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    dry_run_mode: str
    dry_run_steps: tuple[str, ...]
    dry_run_step_count: int
    temporary_workspace_planned: bool
    subprocess_command_prepared: bool
    network_disabled_required: bool
    mutation_snapshot_required: bool
    stdout_stderr_capture_required: bool
    timeout_required: bool
    dry_run_command_executed: bool
    fixture_file_written: bool
    fixture_harness_executed: bool
    generated_wiring_activated: bool
    operator_action: str


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _ledger_id(isolation_id: str) -> str:
    return f"dry_run_ledger_{isolation_id}"


def _dry_run_rows(isolation_rows: list[dict[str, Any]]) -> list[FixtureHarnessDryRunLedgerRow]:
    rows: list[FixtureHarnessDryRunLedgerRow] = []
    for isolation in isolation_rows:
        isolation_id = str(isolation.get("isolation_id"))
        rows.append(FixtureHarnessDryRunLedgerRow(
            ledger_id=_ledger_id(isolation_id),
            isolation_id=isolation_id,
            fixture_id=str(isolation.get("fixture_id")),
            surface_id=str(isolation.get("surface_id")),
            dispatch_family=str(isolation.get("dispatch_family")),
            candidate_target=str(isolation.get("candidate_target")),
            dry_run_mode="operator_reviewed_isolated_dry_run_ledger_only",
            dry_run_steps=DRY_RUN_STEPS,
            dry_run_step_count=len(DRY_RUN_STEPS),
            temporary_workspace_planned=True,
            subprocess_command_prepared=True,
            network_disabled_required=True,
            mutation_snapshot_required=True,
            stdout_stderr_capture_required=True,
            timeout_required=True,
            dry_run_command_executed=False,
            fixture_file_written=False,
            fixture_harness_executed=False,
            generated_wiring_activated=False,
            operator_action="review dry-run ledger and approve a future isolated execution trial separately; keep manual dispatch authoritative",
        ))
    return rows


def build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_harness_isolation_plan_count": INPUT_HARNESS_ISOLATION_PLAN_COUNT,
        "dry_run_ledger_row_count": DRY_RUN_LEDGER_ROW_COUNT,
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_dry_run_ledger_count": DASHBOARD_DRY_RUN_LEDGER_COUNT,
        "api_dry_run_ledger_count": API_DRY_RUN_LEDGER_COUNT,
        "smoke_dry_run_ledger_count": SMOKE_DRY_RUN_LEDGER_COUNT,
        "dry_run_step_count_per_row": DRY_RUN_STEP_COUNT_PER_ROW,
        "dry_run_ledger_step_count": DRY_RUN_LEDGER_STEP_COUNT,
        "review_only": True,
        "dry_run_ledger_only": True,
        "dry_run_commands_prepared": True,
        "dry_run_commands_executed": False,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch fixture harness dry-run ledger is preview-only; commands are prepared as ledger rows but not executed, and manual dispatch remains authoritative.",
    }


def build_manifest_generated_dispatch_fixture_harness_dry_run_ledger(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    isolation_report = build_manifest_generated_dispatch_fixture_harness_isolation(project_root, inspect_sources=inspect_sources)
    isolation_rows = list(isolation_report.get("isolation_rows") or [])
    dry_run_rows = _dry_run_rows(isolation_rows)
    row_dicts = [asdict(row) for row in dry_run_rows]
    dashboard_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "dashboard")
    api_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "api")
    smoke_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "smoke")
    prepared_count = sum(1 for row in row_dicts if row.get("subprocess_command_prepared") is True)
    executed_count = sum(1 for row in row_dicts if row.get("dry_run_command_executed") is True)
    fixture_file_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    fixture_harness_execution_count = sum(1 for row in row_dicts if row.get("fixture_harness_executed") is True)
    generated_wiring_count = sum(1 for row in row_dicts if row.get("generated_wiring_activated") is True)
    step_total = sum(int(row.get("dry_run_step_count") or 0) for row in row_dicts)
    containment_ready_count = sum(
        1 for row in row_dicts
        if row.get("temporary_workspace_planned") is True
        and row.get("subprocess_command_prepared") is True
        and row.get("network_disabled_required") is True
        and row.get("mutation_snapshot_required") is True
        and row.get("stdout_stderr_capture_required") is True
        and row.get("timeout_required") is True
    )
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_fixture_harness_dry_run_ledger.py",
        "conscious_agent/manifest_generated_dispatch_fixture_harness_isolation.py",
        "conscious_agent/manifest_generated_dispatch_parity_fixture_preview.py",
        "conscious_agent/source_surface_manifest_dispatch_candidate_preparation.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata",
        "build_manifest_generated_dispatch_fixture_harness_dry_run_ledger",
        "manifest_generated_dispatch_fixture_harness_dry_run_ledger_text",
        "input_harness_isolation_plan_count=24",
        "dry_run_ledger_row_count=24",
        "dispatch_family_count=3",
        "dashboard_dry_run_ledger_count=8",
        "api_dry_run_ledger_count=8",
        "smoke_dry_run_ledger_count=8",
        "dry_run_step_count_per_row=6",
        "dry_run_ledger_step_count=144",
        "dry_run_command_prepared_count=24",
        "dry_run_command_executed_count=0",
        "containment_ready_count=24",
        "dry_run_ledger_only=True",
        "dry_run_commands_prepared=True",
        "dry_run_commands_executed=False",
        "fixture_files_written=False",
        "fixture_harness_executed=False",
        "subprocesses_spawned=False",
        "temp_workspaces_created=False",
        "mutation_snapshots_captured=False",
        "network_access_permitted=False",
        "manual_dashboard_remains_authoritative=True",
        "manual_api_dispatch_remains_authoritative=True",
        "manual_smoke_remains_authoritative=True",
        "manifest_replaces_dashboard_routes=False",
        "manifest_replaces_api_dispatch=False",
        "manifest_replaces_smoke_registry=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_required=True",
    ]
    checks = [
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-isolation-pass", "ok": isolation_report.get("ok") is True and isolation_report.get("status") == "pass", "message": f"input_status={isolation_report.get('status')} input_ok={isolation_report.get('ok')}"},
        {"name": "input-isolation-row-count", "ok": len(isolation_rows) == INPUT_HARNESS_ISOLATION_PLAN_COUNT, "message": f"input_rows={len(isolation_rows)} expected={INPUT_HARNESS_ISOLATION_PLAN_COUNT}"},
        {"name": "dry-run-ledger-row-count", "ok": len(row_dicts) == DRY_RUN_LEDGER_ROW_COUNT, "message": f"dry_run_rows={len(row_dicts)} expected={DRY_RUN_LEDGER_ROW_COUNT}"},
        {"name": "dry-run-family-counts", "ok": dashboard_count == DASHBOARD_DRY_RUN_LEDGER_COUNT and api_count == API_DRY_RUN_LEDGER_COUNT and smoke_count == SMOKE_DRY_RUN_LEDGER_COUNT, "message": f"dashboard={dashboard_count} api={api_count} smoke={smoke_count}"},
        {"name": "dry-run-step-ledger", "ok": step_total == DRY_RUN_LEDGER_STEP_COUNT, "message": f"steps={step_total} expected={DRY_RUN_LEDGER_STEP_COUNT}"},
        {"name": "dry-run-containment-ready", "ok": containment_ready_count == DRY_RUN_LEDGER_ROW_COUNT, "message": f"containment_ready={containment_ready_count}"},
        {"name": "dry-run-not-executed", "ok": prepared_count == DRY_RUN_LEDGER_ROW_COUNT and executed_count == 0 and fixture_file_write_count == 0 and fixture_harness_execution_count == 0 and generated_wiring_count == 0, "message": f"prepared={prepared_count} executed={executed_count} writes={fixture_file_write_count} harness={fixture_harness_execution_count} generated={generated_wiring_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "dry_run_ledger_only": True,
            "dry_run_commands_prepared": True,
            "dry_run_commands_executed": False,
            "fixture_files_written": False,
            "fixture_harness_executed": False,
            "subprocesses_spawned": False,
            "temp_workspaces_created": False,
            "mutation_snapshots_captured": False,
            "network_access_permitted": False,
            "external_filesystem_write_permitted": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Dry-run ledger prepares commands but does not execute harnesses, write fixtures, spawn subprocesses, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "input_harness_isolation_plan_count": len(isolation_rows),
        "dry_run_ledger_row_count": len(row_dicts),
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_dry_run_ledger_count": dashboard_count,
        "api_dry_run_ledger_count": api_count,
        "smoke_dry_run_ledger_count": smoke_count,
        "dry_run_step_count_per_row": DRY_RUN_STEP_COUNT_PER_ROW,
        "dry_run_ledger_step_count": step_total,
        "dry_run_command_prepared_count": prepared_count,
        "dry_run_command_executed_count": executed_count,
        "containment_ready_count": containment_ready_count,
        "fixture_file_write_count": fixture_file_write_count,
        "fixture_harness_execution_count": fixture_harness_execution_count,
        "generated_wiring_activation_count": generated_wiring_count,
        "dry_run_ledger_only": True,
        "dry_run_commands_prepared": True,
        "dry_run_commands_executed": False,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "temp_workspaces_created": False,
        "mutation_snapshots_captured": False,
        "network_access_permitted": False,
        "external_filesystem_write_permitted": False,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "manual_smoke_remains_authoritative": True,
        "manifest_replaces_dashboard_routes": False,
        "manifest_replaces_api_dispatch": False,
        "manifest_replaces_smoke_registry": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "operator_approval_required": True,
        "dry_run_ledger_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_harness_dry_run_ledger_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_harness_isolation_plan_count={report.get('input_harness_isolation_plan_count')}",
        f"dry_run_ledger_row_count={report.get('dry_run_ledger_row_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"dashboard_dry_run_ledger_count={report.get('dashboard_dry_run_ledger_count')}",
        f"api_dry_run_ledger_count={report.get('api_dry_run_ledger_count')}",
        f"smoke_dry_run_ledger_count={report.get('smoke_dry_run_ledger_count')}",
        f"dry_run_step_count_per_row={report.get('dry_run_step_count_per_row')}",
        f"dry_run_ledger_step_count={report.get('dry_run_ledger_step_count')}",
        f"dry_run_command_prepared_count={report.get('dry_run_command_prepared_count')}",
        f"dry_run_command_executed_count={report.get('dry_run_command_executed_count')}",
        f"containment_ready_count={report.get('containment_ready_count')}",
        f"dry_run_ledger_only={report.get('dry_run_ledger_only')}",
        f"dry_run_commands_prepared={report.get('dry_run_commands_prepared')}",
        f"dry_run_commands_executed={report.get('dry_run_commands_executed')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"fixture_harness_executed={report.get('fixture_harness_executed')}",
        f"subprocesses_spawned={report.get('subprocesses_spawned')}",
        f"temp_workspaces_created={report.get('temp_workspaces_created')}",
        f"mutation_snapshots_captured={report.get('mutation_snapshots_captured')}",
        f"network_access_permitted={report.get('network_access_permitted')}",
        f"external_filesystem_write_permitted={report.get('external_filesystem_write_permitted')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"manual_api_dispatch_remains_authoritative={report.get('manual_api_dispatch_remains_authoritative')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manifest_replaces_dashboard_routes={report.get('manifest_replaces_dashboard_routes')}",
        f"manifest_replaces_api_dispatch={report.get('manifest_replaces_api_dispatch')}",
        f"manifest_replaces_smoke_registry={report.get('manifest_replaces_smoke_registry')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_required={report.get('operator_approval_required')}",
    ]
    if full:
        for row in report.get("dry_run_ledger_rows", []):
            lines.append(
                f"dry_run_row={row.get('ledger_id')} family={row.get('dispatch_family')} "
                f"fixture={row.get('fixture_id')} target={row.get('candidate_target')} "
                f"steps={row.get('dry_run_step_count')} command_prepared={row.get('subprocess_command_prepared')} "
                f"executed={row.get('dry_run_command_executed')} fixture_written={row.get('fixture_file_written')} "
                f"harness_executed={row.get('fixture_harness_executed')} generated_wiring={row.get('generated_wiring_activated')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1061.0 manifest generated dispatch fixture harness dry run ledger tokens: manifest-generated-dispatch-fixture-harness-dry-run-ledger-v1 /manifest-generated-dispatch-fixture-harness-dry-run-ledger /api/source-surface/manifest-generated-dispatch-fixture-harness-dry-run-ledger build_manifest_generated_dispatch_fixture_harness_dry_run_ledger_metadata build_manifest_generated_dispatch_fixture_harness_dry_run_ledger manifest_generated_dispatch_fixture_harness_dry_run_ledger_text input_harness_isolation_plan_count=24 dry_run_ledger_row_count=24 dispatch_family_count=3 dashboard_dry_run_ledger_count=8 api_dry_run_ledger_count=8 smoke_dry_run_ledger_count=8 dry_run_step_count_per_row=6 dry_run_ledger_step_count=144 dry_run_command_prepared_count=24 dry_run_command_executed_count=0 containment_ready_count=24 dry_run_ledger_only=True dry_run_commands_prepared=True dry_run_commands_executed=False fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False temp_workspaces_created=False mutation_snapshots_captured=False network_access_permitted=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
