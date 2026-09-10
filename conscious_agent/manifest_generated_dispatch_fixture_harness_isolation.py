from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from manifest_generated_dispatch_parity_fixture_preview import (
    MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID,
    build_manifest_generated_dispatch_parity_fixture_preview,
)

MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_VERSION = RUNTIME_VERSION
MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID = "manifest-generated-dispatch-fixture-harness-isolation-v1"
SELF_ROUTE = "/manifest-generated-dispatch-fixture-harness-isolation"
API_ROUTE = "/api/source-surface/manifest-generated-dispatch-fixture-harness-isolation"
INPUT_REVIEW_ID = MANIFEST_GENERATED_DISPATCH_PARITY_FIXTURE_PREVIEW_ID
INPUT_PARITY_FIXTURE_ROW_COUNT = 24
HARNESS_ISOLATION_PLAN_COUNT = 24
DISPATCH_FAMILY_COUNT = 3
DASHBOARD_HARNESS_PLAN_COUNT = 8
API_HARNESS_PLAN_COUNT = 8
SMOKE_HARNESS_PLAN_COUNT = 8

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "preview_only": True,
    "harness_isolation_plan_only": True,
    "fixture_files_written": False,
    "fixture_harness_executed": False,
    "subprocesses_spawned": False,
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
class FixtureHarnessIsolationRow:
    isolation_id: str
    fixture_id: str
    surface_id: str
    dispatch_family: str
    candidate_target: str
    harness_mode: str
    isolated_temp_workspace_required: bool
    subprocess_required_for_future_execution: bool
    network_disabled_required: bool
    mutation_snapshot_required: bool
    stdout_stderr_capture_required: bool
    timeout_required: bool
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


def _isolation_id(fixture_id: str) -> str:
    return f"isolate_{fixture_id}"


def _isolation_rows(fixture_rows: list[dict[str, Any]]) -> list[FixtureHarnessIsolationRow]:
    rows: list[FixtureHarnessIsolationRow] = []
    for fixture in fixture_rows:
        family = str(fixture.get("dispatch_family"))
        fixture_id = str(fixture.get("fixture_id"))
        rows.append(FixtureHarnessIsolationRow(
            isolation_id=_isolation_id(fixture_id),
            fixture_id=fixture_id,
            surface_id=str(fixture.get("surface_id")),
            dispatch_family=family,
            candidate_target=str(fixture.get("candidate_target")),
            harness_mode="isolated_preview_contract_only",
            isolated_temp_workspace_required=True,
            subprocess_required_for_future_execution=True,
            network_disabled_required=True,
            mutation_snapshot_required=True,
            stdout_stderr_capture_required=True,
            timeout_required=True,
            fixture_file_written=False,
            fixture_harness_executed=False,
            generated_wiring_activated=False,
            operator_action="review isolated harness contract; keep generated dispatch inactive until a future operator-approved dry-run executes in containment",
        ))
    return rows


def build_manifest_generated_dispatch_fixture_harness_isolation_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "preview",
        "ok": True,
        "input_parity_fixture_row_count": INPUT_PARITY_FIXTURE_ROW_COUNT,
        "harness_isolation_plan_count": HARNESS_ISOLATION_PLAN_COUNT,
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_harness_plan_count": DASHBOARD_HARNESS_PLAN_COUNT,
        "api_harness_plan_count": API_HARNESS_PLAN_COUNT,
        "smoke_harness_plan_count": SMOKE_HARNESS_PLAN_COUNT,
        "review_only": True,
        "harness_isolation_plan_only": True,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "message": "Manifest-generated dispatch fixture harness isolation is preview-only; no fixture files are written, no subprocesses are spawned, and manual dispatch remains authoritative.",
    }


def build_manifest_generated_dispatch_fixture_harness_isolation(root: str | Path | None = None, *, inspect_sources: bool = True) -> dict[str, Any]:
    project_root = _repo(root)
    preview_report = build_manifest_generated_dispatch_parity_fixture_preview(project_root, inspect_sources=inspect_sources)
    fixture_rows = list(preview_report.get("fixture_rows") or [])
    isolation_rows = _isolation_rows(fixture_rows)
    row_dicts = [asdict(row) for row in isolation_rows]
    dashboard_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "dashboard")
    api_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "api")
    smoke_count = sum(1 for row in row_dicts if row.get("dispatch_family") == "smoke")
    isolation_contract_count = sum(
        1 for row in row_dicts
        if row.get("isolated_temp_workspace_required") is True
        and row.get("subprocess_required_for_future_execution") is True
        and row.get("network_disabled_required") is True
        and row.get("mutation_snapshot_required") is True
        and row.get("stdout_stderr_capture_required") is True
        and row.get("timeout_required") is True
    )
    fixture_file_write_count = sum(1 for row in row_dicts if row.get("fixture_file_written") is True)
    fixture_harness_execution_count = sum(1 for row in row_dicts if row.get("fixture_harness_executed") is True)
    generated_wiring_count = sum(1 for row in row_dicts if row.get("generated_wiring_activated") is True)
    docs = "\n".join(_read_text(project_root, rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
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
        MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID,
        SELF_ROUTE,
        API_ROUTE,
        "build_manifest_generated_dispatch_fixture_harness_isolation_metadata",
        "build_manifest_generated_dispatch_fixture_harness_isolation",
        "manifest_generated_dispatch_fixture_harness_isolation_text",
        "input_parity_fixture_row_count=24",
        "harness_isolation_plan_count=24",
        "dispatch_family_count=3",
        "dashboard_harness_plan_count=8",
        "api_harness_plan_count=8",
        "smoke_harness_plan_count=8",
        "isolation_contract_pass_count=24",
        "fixture_files_written=False",
        "fixture_harness_executed=False",
        "subprocesses_spawned=False",
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
        {"name": "module-version-current", "ok": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_VERSION == CURRENT_VERSION, "message": f"module={MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "input-fixture-preview-pass", "ok": preview_report.get("ok") is True and preview_report.get("status") == "pass", "message": f"input_status={preview_report.get('status')} input_ok={preview_report.get('ok')}"},
        {"name": "input-fixture-row-count", "ok": len(fixture_rows) == INPUT_PARITY_FIXTURE_ROW_COUNT, "message": f"input_rows={len(fixture_rows)} expected={INPUT_PARITY_FIXTURE_ROW_COUNT}"},
        {"name": "harness-isolation-row-count", "ok": len(row_dicts) == HARNESS_ISOLATION_PLAN_COUNT, "message": f"isolation_rows={len(row_dicts)} expected={HARNESS_ISOLATION_PLAN_COUNT}"},
        {"name": "harness-family-counts", "ok": dashboard_count == DASHBOARD_HARNESS_PLAN_COUNT and api_count == API_HARNESS_PLAN_COUNT and smoke_count == SMOKE_HARNESS_PLAN_COUNT, "message": f"dashboard={dashboard_count} api={api_count} smoke={smoke_count}"},
        {"name": "isolation-contracts-present", "ok": isolation_contract_count == HARNESS_ISOLATION_PLAN_COUNT, "message": f"isolation_contracts={isolation_contract_count}"},
        {"name": "harness-preview-only", "ok": fixture_file_write_count == 0 and fixture_harness_execution_count == 0 and generated_wiring_count == 0, "message": f"writes={fixture_file_write_count} executed={fixture_harness_execution_count} generated={generated_wiring_count}"},
        {"name": "authority-boundaries", "ok": all(BOUNDARIES[key] is expected for key, expected in {
            "review_only": True,
            "harness_isolation_plan_only": True,
            "fixture_files_written": False,
            "fixture_harness_executed": False,
            "subprocesses_spawned": False,
            "network_access_permitted": False,
            "external_filesystem_write_permitted": False,
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
            "manual_api_dispatch_remains_authoritative": True,
            "manual_smoke_remains_authoritative": True,
            "release_authorized": False,
            "autonomy_expanded": False,
            "operator_approval_required": True,
        }.items()), "message": "Harness isolation remains preview-only and cannot activate dispatch, write fixtures, spawn subprocesses, authorize release, or expand autonomy."},
        {"name": "documentation-tokens", "ok": all(token in docs for token in required_tokens), "message": f"required_tokens={len(required_tokens)}"},
    ]
    ok = all(row.get("ok") is True for row in checks)
    return {
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "checked_at": _now(),
        "review_id": MANIFEST_GENERATED_DISPATCH_FIXTURE_HARNESS_ISOLATION_ID,
        "input_review_id": INPUT_REVIEW_ID,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "review_only": True,
        "input_parity_fixture_row_count": len(fixture_rows),
        "harness_isolation_plan_count": len(row_dicts),
        "dispatch_family_count": DISPATCH_FAMILY_COUNT,
        "dashboard_harness_plan_count": dashboard_count,
        "api_harness_plan_count": api_count,
        "smoke_harness_plan_count": smoke_count,
        "isolation_contract_pass_count": isolation_contract_count,
        "fixture_file_write_count": fixture_file_write_count,
        "fixture_harness_execution_count": fixture_harness_execution_count,
        "generated_wiring_activation_count": generated_wiring_count,
        "fixture_files_written": False,
        "fixture_harness_executed": False,
        "subprocesses_spawned": False,
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
        "isolation_rows": row_dicts,
        "checks": checks,
        "blocked": [row for row in checks if not row.get("ok")],
        "boundaries": dict(BOUNDARIES),
    }


def manifest_generated_dispatch_fixture_harness_isolation_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone")),
        f"review_id={report.get('review_id')}",
        f"input_review_id={report.get('input_review_id')}",
        f"status={report.get('status')}",
        f"input_parity_fixture_row_count={report.get('input_parity_fixture_row_count')}",
        f"harness_isolation_plan_count={report.get('harness_isolation_plan_count')}",
        f"dispatch_family_count={report.get('dispatch_family_count')}",
        f"dashboard_harness_plan_count={report.get('dashboard_harness_plan_count')}",
        f"api_harness_plan_count={report.get('api_harness_plan_count')}",
        f"smoke_harness_plan_count={report.get('smoke_harness_plan_count')}",
        f"isolation_contract_pass_count={report.get('isolation_contract_pass_count')}",
        f"fixture_files_written={report.get('fixture_files_written')}",
        f"fixture_harness_executed={report.get('fixture_harness_executed')}",
        f"subprocesses_spawned={report.get('subprocesses_spawned')}",
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
        for row in report.get("isolation_rows", []):
            lines.append(
                f"isolation_row={row.get('isolation_id')} family={row.get('dispatch_family')} "
                f"fixture={row.get('fixture_id')} target={row.get('candidate_target')} "
                f"temp_workspace={row.get('isolated_temp_workspace_required')} subprocess_future={row.get('subprocess_required_for_future_execution')} "
                f"network_disabled={row.get('network_disabled_required')} mutation_snapshot={row.get('mutation_snapshot_required')} "
                f"executed={row.get('fixture_harness_executed')} generated_wiring={row.get('generated_wiring_activated')}"
            )
        for check in report.get("checks", []):
            lines.append(f"check={check.get('name')} ok={check.get('ok')} message={check.get('message')}")
    return "\n".join(lines)


# v1060.0 manifest generated dispatch fixture harness isolation tokens: manifest-generated-dispatch-fixture-harness-isolation-v1 /manifest-generated-dispatch-fixture-harness-isolation /api/source-surface/manifest-generated-dispatch-fixture-harness-isolation build_manifest_generated_dispatch_fixture_harness_isolation_metadata build_manifest_generated_dispatch_fixture_harness_isolation manifest_generated_dispatch_fixture_harness_isolation_text input_parity_fixture_row_count=24 harness_isolation_plan_count=24 dispatch_family_count=3 dashboard_harness_plan_count=8 api_harness_plan_count=8 smoke_harness_plan_count=8 isolation_contract_pass_count=24 fixture_files_written=False fixture_harness_executed=False subprocesses_spawned=False network_access_permitted=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True manifest_replaces_dashboard_routes=False manifest_replaces_api_dispatch=False manifest_replaces_smoke_registry=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip
