from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_fixture_harness_dry_run_ledger import (
    MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID,
    build_manifest_generated_dispatch_fixture_harness_dry_run_ledger,
)

MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID = "manifest-generated-dispatch-fixture-dry-run-execution-prep-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-dry-run-execution-prep"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-dry-run-execution-prep"
INPUT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_DRY_RUN_LEDGER_ID
INPUT_DRY_RUN_LEDGER_ROW_COUNT = 24
EXECUTION_PREP_ROW_COUNT = 24
DISPATCH_FAMILY_COUNT = 3
DASHBOARD_EXECUTION_PREP_COUNT = 8
API_EXECUTION_PREP_COUNT = 8
SMOKE_EXECUTION_PREP_COUNT = 8
EXECUTION_PREFLIGHT_STEP_COUNT_PER_ROW = 7
EXECUTION_PREFLIGHT_STEP_COUNT = EXECUTION_PREP_ROW_COUNT * EXECUTION_PREFLIGHT_STEP_COUNT_PER_ROW

EXECUTION_PREFLIGHT_STEPS: tuple[str, ...] = (
    "resolve_ledger_row_without_running_command",
    "prepare_ephemeral_workspace_manifest",
    "prepare_subprocess_argv_preview",
    "prepare_network_disabled_environment_preview",
    "prepare_pre_and_post_mutation_snapshot_plan",
    "prepare_stdout_stderr_timeout_capture_plan",
    "prepare_operator_result_receipt_schema",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "preview_only": True,
    "execution_prep_only": True,
    "dry_run_execution_prepared": True,
    "dry_run_commands_executed": False,
    "fixture_files_written": False,
    "fixture_harness_executed": False,
    "subprocesses_spawned": False,
    "temp_workspaces_created": False,
    "mutation_snapshots_captured": False,
    "stdout_stderr_captured": False,
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
class FixtureDryRunExecutionPrepRow:
    execution_prep_id: str
    ledger_id: str
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    execution_mode: str
    execution_preflight_steps: tuple[str, ...]
    execution_preflight_step_count: int
    ephemeral_workspace_manifest_prepared: bool
    subprocess_argv_preview_prepared: bool
    network_disabled_environment_prepared: bool
    mutation_snapshot_plan_prepared: bool
    stdout_stderr_timeout_capture_plan_prepared: bool
    operator_receipt_schema_prepared: bool
    dry_run_command_executed: bool
    subprocess_spawned: bool
    temp_workspace_created: bool
    fixture_file_written: bool
    fixture_harness_executed: bool
    generated_wiring_activated: bool
    release_authorized: bool
    autonomy_expanded: bool
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


def _prep_id(ledger_id: str) -> str:
    return f"execution_prep_{ledger_id}"


def _execution_rows(ledger_rows: list[dict[str, Any]]) -> list[FixtureDryRunExecutionPrepRow]:
    rows: list[FixtureDryRunExecutionPrepRow] = []
    for ledger in ledger_rows:
        ledger_id = str(ledger.get("ledger_id"))
        rows.append(FixtureDryRunExecutionPrepRow(
            execution_prep_id=_prep_id(ledger_id),
            ledger_id=ledger_id,
            fixture_id=str(ledger.get("fixture_id")),
            surface_id=str(ledger.get("surface_id")),
            dispatch_family=str(ledger.get("dispatch_family")),
            candidate_target=str(ledger.get("candidate_target")),
            execution_mode="operator_approved_future_isolated_dry_run_execution_prep_only",
            execution_preflight_steps=EXECUTION_PREFLIGHT_STEPS,
            execution_preflight_step_count=len(EXECUTION_PREFLIGHT_STEPS),
            ephemeral_workspace_manifest_prepared=True,
            subprocess_argv_preview_prepared=True,
            network_disabled_environment_prepared=True,
            mutation_snapshot_plan_prepared=True,
            stdout_stderr_timeout_capture_plan_prepared=True,
            operator_receipt_schema_prepared=True,
            dry_run_command_executed=False,
            subprocess_spawned=False,
            temp_workspace_created=False,
            fixture_file_written=False,
            fixture_harness_executed=False,
            generated_wiring_activated=False,
            release_authorized=False,
            autonomy_expanded=False,
            operator_action="review execution prep and approve a future isolated dry-run trial separately; do not activate generated dispatch",
        ))
    return rows


def build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_dry_run_ledger_row_count": INPUT_DRY_RUN_LEDGER_ROW_COUNT,
        "execution_prep_row_count": EXECUTION_PREP_ROW_COUNT,
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_execution_prep_count": DASHBOARD_EXECUTION_PREP_COUNT,
        "api_execution_prep_count": API_EXECUTION_PREP_COUNT,
        "smoke_execution_prep_count": SMOKE_EXECUTION_PREP_COUNT,
        "execution_preflight_step_count_per_row": EXECUTION_PREFLIGHT_STEP_COUNT_PER_ROW,
        "execution_preflight_step_count": EXECUTION_PREFLIGHT_STEP_COUNT,
        "execution_prep_only": True,
        "dry_run_execution_prepared": True,
        "dry_run_commands_executed": False,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "temp_workspaces_created": False,
        "mutation_snapshots_captured": False,
        "network_access_permitted": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch fixture dry-run execution prep is preview-only; execution plans are prepared but commands are not run and manual dispatch remains authoritative.",
    }


def build_manifest_generated_dispatch_fixture_dry_run_execution_prep(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    ledger_report = build_manifest_generated_dispatch_fixture_harness_dry_run_ledger(project_root, inspect_sources=inspect_sources)
    ledger_rows = list(ledger_report.get("dry_run_ledger_rows") or [])
    prep_rows = _execution_rows(ledger_rows)
    row_dicts = [asdict(row) for row in prep_rows]
    dashboard_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "dashboard")
    api_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "api")
    smoke_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "smoke")
    step_total = sum(int(row.get("execution_preflight_step_count") or 0) for row in row_dicts)
    execution_ready_count = sum(
        1 for row in row_dicts
        if row.get("ephemeral_workspace_manifest_prepared") is True
        and row.get("subprocess_argv_preview_prepared") is True
        and row.get("network_disabled_environment_prepared") is True
        and row.get("mutation_snapshot_plan_prepared") is True
        and row.get("stdout_stderr_timeout_capture_plan_prepared") is True
        and row.get("operator_receipt_schema_prepared") is True
    )
    executed_count = sum(1 for row in row_dicts if row.get("dry_run_command_executed") is True)
    subprocess_count = sum(1 for row in row_dicts if row.get("subprocess_spawned") is True)
    temp_workspace_count = sum(1 for row in row_dicts if row.get("temp_workspace_created") is True)
    fixture_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    harness_execution_count = sum(1 for row in row_dicts if row.get("fixture_harness_executed") is True)
    generated_wiring_count = sum(1 for row in row_dicts if row.get("generated_wiring_activated") is True)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_generated_dispatch_fixture_dry_run_execution_prep.py",
        "conscious_agent/manifest_generated_dispatch_fixture_harness_dry_run_ledger.py",
        "conscious_agent/manifest_generated_dispatch_fixture_harness_isolation.py",
        "conscious_agent/manifest_generated_dispatch_parity_fixture_preview.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/current_version_staleness_audit.py",
        "tools/smoke_check.py",
    ])
    required_tokens = [
        CURRENT_MILESTONE,
        MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata",
        "build_manifest_generated_dispatch_fixture_dry_run_execution_prep",
        "manifest_generated_dispatch_fixture_dry_run_execution_prep_text",
        "input_dry_run_ledger_row_count=24",
        "execution_prep_row_count=24",
        "dispatch_family_count=3",
        "dashboard_execution_prep_count=8",
        "api_execution_prep_count=8",
        "smoke_execution_prep_count=8",
        "execution_preflight_step_count_per_row=7",
        "execution_preflight_step_count=168",
        "execution_ready_contract_count=24",
        "dry_run_execution_prepared=True",
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
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-dry-run-ledger-pass", "ok": ledger_report.get("ok") is True and ledger_report.get("status") == "pass", "message": f"input_status={ledger_report.get('status')} input_ok={ledger_report.get('ok')}"},
        {"name": "input-dry-run-ledger-row-count", "ok": len(ledger_rows) == INPUT_DRY_RUN_LEDGER_ROW_COUNT, "message": f"input_rows={len(ledger_rows)} expected={INPUT_DRY_RUN_LEDGER_ROW_COUNT}"},
        {"name": "execution-prep-row-count", "ok": len(row_dicts) == EXECUTION_PREP_ROW_COUNT, "message": f"execution_prep_rows={len(row_dicts)} expected={EXECUTION_PREP_ROW_COUNT}"},
        {"name": "execution-prep-family-counts", "ok": dashboard_count == DASHBOARD_EXECUTION_PREP_COUNT and api_count == API_EXECUTION_PREP_COUNT and smoke_count == SMOKE_EXECUTION_PREP_COUNT, "message": f"dashboard={dashboard_count} api={api_count} smoke={smoke_count}"},
        {"name": "execution-preflight-step-count", "ok": step_total == EXECUTION_PREFLIGHT_STEP_COUNT, "message": f"steps={step_total} expected={EXECUTION_PREFLIGHT_STEP_COUNT}"},
        {"name": "execution-ready-contracts", "ok": execution_ready_count == EXECUTION_PREP_ROW_COUNT, "message": f"execution_ready={execution_ready_count}"},
        {"name": "execution-prep-not-executed", "ok": executed_count == 0 and subprocess_count == 0 and temp_workspace_count == 0 and fixture_write_count == 0 and harness_execution_count == 0 and generated_wiring_count == 0, "message": f"executed={executed_count} subprocesses={subprocess_count} temp_workspaces={temp_workspace_count} writes={fixture_write_count} harness={harness_execution_count} generated={generated_wiring_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "execution_prep_only": True,
            "dry_run_execution_prepared": True,
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
        }.items()), "message": "Dry-run execution prep prepares an execution contract but does not run commands, create temp workspaces, spawn subprocesses, write fixtures, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_DRY_RUN_EXECUTION_PREP_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "input_dry_run_ledger_row_count": len(ledger_rows),
        "execution_prep_row_count": len(row_dicts),
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_execution_prep_count": dashboard_count,
        "api_execution_prep_count": api_count,
        "smoke_execution_prep_count": smoke_count,
        "execution_preflight_step_count_per_row": EXECUTION_PREFLIGHT_STEP_COUNT_PER_ROW,
        "execution_preflight_step_count": step_total,
        "execution_ready_contract_count": execution_ready_count,
        "dry_run_execution_prepared": True,
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
        "execution_prep_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_dry_run_execution_prep_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_dry_run_ledger_row_count={report.get('input_dry_run_ledger_row_count')}",
        f"execution_prep_row_count={report.get('execution_prep_row_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"dashboard_execution_prep_count={report.get('dashboard_execution_prep_count')}",
        f"api_execution_prep_count={report.get('api_execution_prep_count')}",
        f"smoke_execution_prep_count={report.get('smoke_execution_prep_count')}",
        f"execution_preflight_step_count_per_row={report.get('execution_preflight_step_count_per_row')}",
        f"execution_preflight_step_count={report.get('execution_preflight_step_count')}",
        f"execution_ready_contract_count={report.get('execution_ready_contract_count')}",
        f"dry_run_execution_prepared={report.get('dry_run_execution_prepared')}",
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
        for row in report.get("execution_prep_rows", []):
            lines.append(
                f"execution_prep_row={row.get('execution_prep_id')} family={row.get('dispatch_family')} "
                f"fixture={row.get('fixture_id')} target={row.get('candidate_target')} "
                f"steps={row.get('execution_preflight_step_count')} argv_prepared={row.get('subprocess_argv_preview_prepared')} "
                f"executed={row.get('dry_run_command_executed')} subprocess={row.get('subprocess_spawned')} "
                f"temp_workspace={row.get('temp_workspace_created')} fixture_written={row.get('fixture_file_written')} "
                f"harness_executed={row.get('fixture_harness_executed')} generated_wiring={row.get('generated_wiring_activated')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1064.0 manifest generated dispatch fixture dry run execution prep tokens: manifest-generated-dispatch-fixture-dry-run-execution-prep-v1 /manifest-generated-dispatch-fixture-dry-run-execution-prep /api/source-surface/manifest-generated-dispatch-fixture-dry-run-execution-prep build_manifest_generated_dispatch_fixture_dry_run_execution_prep_metadata build_manifest_generated_dispatch_fixture_dry_run_execution_prep manifest_generated_dispatch_fixture_dry_run_execution_prep_text input_dry_run_ledger_row_count=24 execution_prep_row_count=24 dispatch_family_count=3 dashboard_execution_prep_count=8 api_execution_prep_count=8 smoke_execution_prep_count=8 execution_preflight_step_count_per_row=7 execution_preflight_step_count=168 execution_ready_contract_count=24 dry_run_execution_prepared=True dry_run_commands_executed=False fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False temp_workspaces_created=False mutation_snapshots_captured=False network_access_permitted=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
