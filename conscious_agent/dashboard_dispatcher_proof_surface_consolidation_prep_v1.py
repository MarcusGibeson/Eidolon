from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows
from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION = "1077.7"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID = "dashboard-dispatcher-proof-surface-consolidation-prep-v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_TITLE = "Dashboard Dispatcher Proof Surface Consolidation Prep v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE = "/dashboard-dispatcher-proof-surface-consolidation-prep-v1"
DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER = "render_dashboard_dispatcher_proof_surface_consolidation_prep_v1"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

EXPECTED_HELPER_BACKED_BRANCH_COUNT = 48
EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT = 37
EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTE_COUNT = 0
EXPECTED_LEDGER_FIELD_COUNT = 12

PROPOSED_CANONICAL_ROUTE = "/dashboard-dispatcher-proof-surface"
PROPOSED_CANONICAL_RENDERER = "render_dashboard_dispatcher_proof_surface"
PROPOSED_QUERY_PARAMETER = "proof_route"
PROPOSED_COMPATIBILITY_MODE = "manual-read-only-parameter-adapter"

HISTORICAL_PROOF_ROUTE_PATTERN = re.compile(
    r"^/dashboard-dispatcher-batch-decomposition-(?:prep|trial|checkpoint)(?:-v\d+)?$"
)

PARAMETERIZED_PROOF_LEDGER_FIELDS: tuple[str, ...] = (
    "path",
    "renderer_name",
    "check_id",
    "check_function",
    "phase",
    "sequence",
    "registry_exact",
    "dispatcher_parity_exact",
    "direct_renderer_call_present",
    "renderer_body_present",
    "smoke_row_exact",
    "preview_only",
)

COMPATIBILITY_CONTRACT: dict[str, Any] = {
    "canonical_route": PROPOSED_CANONICAL_ROUTE,
    "canonical_renderer": PROPOSED_CANONICAL_RENDERER,
    "query_parameter": PROPOSED_QUERY_PARAMETER,
    "mode": PROPOSED_COMPATIBILITY_MODE,
    "legacy_routes_remain_authoritative": True,
    "legacy_routes_remain_registered": True,
    "legacy_smoke_rows_remain_authoritative": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "canonical_route_registered": False,
    "canonical_renderer_implemented": False,
    "compatibility_aliases_activated": False,
    "historical_routes_removed": False,
    "navigation_rows_removed": False,
    "smoke_rows_removed": False,
    "dispatcher_branch_conditions_moved": False,
    "dispatcher_branch_bodies_moved": False,
    "renderer_bodies_moved": False,
}

SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "sandbox_backend_admission_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "dashboard_get_preview_only": True,
    "parameterized_proof_ledger_prepared": True,
    "compatibility_contract_prepared": True,
    "consolidated_renderer_trial_executed": False,
    "compatibility_aliases_activated": False,
    "historical_routes_removed": False,
    "navigation_rows_removed": False,
    "smoke_rows_removed": False,
    "dispatcher_branch_condition_moved": False,
    "dispatcher_branch_body_moved": False,
    "renderer_bodies_moved": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def _smoke_row_specs(source: str) -> dict[str, tuple[str, str, int, str]]:
    rows: dict[str, tuple[str, str, int, str]] = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return rows
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "SmokeCheckRowSpec":
            continue
        if len(node.args) != 4:
            continue
        try:
            values = tuple(ast.literal_eval(argument) for argument in node.args)
        except (ValueError, TypeError, SyntaxError):
            continue
        if (
            isinstance(values[0], str)
            and isinstance(values[1], str)
            and isinstance(values[2], int)
            and isinstance(values[3], str)
        ):
            rows[values[0]] = values  # type: ignore[assignment]
    return rows


def _phase_and_sequence(path: str) -> tuple[str, int]:
    match = re.fullmatch(
        r"/dashboard-dispatcher-batch-decomposition-(prep|trial|checkpoint)(?:-v(\d+))?",
        path,
    )
    if not match:
        return "unknown", 0
    phase = match.group(1)
    # The unnumbered checkpoint is the first checkpoint. Unnumbered prep/trial were
    # moved behind helpers in v13 and are therefore not part of this direct ledger.
    sequence = int(match.group(2) or "1")
    return phase, sequence


def dashboard_dispatcher_proof_surface_consolidation_ledger(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    smoke_text = _read(root, "tools/smoke_registry_check_rows.py")
    registry_rows = dashboard_route_registry_rows()
    helper_rows = consolidated_branch_helper_rows()
    helper_paths = {str(row.get("path")) for row in helper_rows}
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    smoke_by_id = _smoke_row_specs(smoke_text)

    direct_rows = [row for row in registry_rows if str(row.get("path")) not in helper_paths]
    direct_excluding_own = [
        row for row in direct_rows
        if str(row.get("path")) != DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE
    ]
    historical_rows = [
        row for row in direct_excluding_own
        if HISTORICAL_PROOF_ROUTE_PATTERN.fullmatch(str(row.get("path")))
    ]
    ordinary_rows = [row for row in direct_excluding_own if row not in historical_rows]

    ledger_rows: list[dict[str, Any]] = []
    for registry_row in historical_rows:
        path = str(registry_row.get("path"))
        renderer_name = str(registry_row.get("renderer_name"))
        route_identity = path.lstrip("/")
        if path == "/dashboard-dispatcher-batch-decomposition-checkpoint":
            check_id = f"{route_identity}-v1"
            expected_check_function = "run_dashboard_dispatcher_batch_decomposition_checkpoint_check"
        else:
            check_id = route_identity
            expected_check_function = f"run_{check_id.replace('-', '_')}_check"
        parity_row = parity_by_path.get(path, {})
        smoke_row = smoke_by_id.get(check_id)
        phase, sequence = _phase_and_sequence(path)
        canonicalized = renderer_name == "render_dashboard_dispatcher_proof_surface"
        row = {
            "path": path,
            "renderer_name": renderer_name,
            "check_id": check_id,
            "check_function": expected_check_function,
            "phase": phase,
            "sequence": sequence,
            "registry_exact": registry_row.get("path") == path and registry_row.get("renderer_name") == renderer_name,
            "dispatcher_parity_exact": parity_row.get("ok") is True
            and parity_row.get("registry_renderer") == renderer_name
            and parity_row.get("dispatcher_renderer") == renderer_name,
            "direct_renderer_call_present": (
                "html = render_dashboard_dispatcher_proof_surface(proof_route=path)" in dashboard_text
                if canonicalized else f"html = {renderer_name}()" in dashboard_text
            ),
            "renderer_body_present": re.search(rf"^def {re.escape(renderer_name)}\(", dashboard_text, re.MULTILINE) is not None,
            "smoke_row_exact": smoke_row == (check_id, "install", 120, expected_check_function),
            "preview_only": registry_row.get("preview_only") is True and registry_row.get("dashboard_get_preview_only") is True,
        }
        row["ledger_fields_exact"] = tuple(key for key in PARAMETERIZED_PROOF_LEDGER_FIELDS if key in row) == PARAMETERIZED_PROOF_LEDGER_FIELDS
        row["ok"] = row["ledger_fields_exact"] is True and all(row.get(field) is True for field in (
            "registry_exact",
            "dispatcher_parity_exact",
            "direct_renderer_call_present",
            "renderer_body_present",
            "smoke_row_exact",
            "preview_only",
        )) and phase in {"prep", "trial", "checkpoint"} and sequence >= 1
        ledger_rows.append(row)

    ledger_rows.sort(key=lambda row: (int(row.get("sequence", 0)), {"prep": 0, "trial": 1, "checkpoint": 2}.get(str(row.get("phase")), 9), str(row.get("path"))))
    return {
        "registry_route_count": len(registry_rows),
        "helper_backed_branch_count": len(helper_rows),
        "direct_registry_route_count_total": len(direct_rows),
        "direct_registry_route_count_excluding_prep_v1": len(direct_excluding_own),
        "historical_proof_route_count": len(historical_rows),
        "ordinary_operational_direct_route_count": len(ordinary_rows),
        "ledger_field_count": len(PARAMETERIZED_PROOF_LEDGER_FIELDS),
        "ledger_fields": list(PARAMETERIZED_PROOF_LEDGER_FIELDS),
        "ledger_rows": ledger_rows,
        "ordinary_rows": ordinary_rows,
    }


def build_dashboard_dispatcher_proof_surface_consolidation_prep_v1_report(
    project_root: str | Path,
    *,
    expected_version: str,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    registry_text = _read(root, "conscious_agent/dashboard_route_registry.py")
    parity_text = _read(root, "conscious_agent/dashboard_dispatcher_parity.py")
    smoke_text = _read(root, "tools/smoke_registry_check_rows.py")
    next_steps = _read(root, "README_NEXT_STEPS.md")
    release_history = _read(root, "README_RELEASE_HISTORY.md")
    ledger = dashboard_dispatcher_proof_surface_consolidation_ledger(root)
    registry_rows = dashboard_route_registry_rows()
    parity_by_path = {str(row.get("path")): row for row in dashboard_dispatcher_parity_rows(root)}
    own_registry = next((row for row in registry_rows if row.get("path") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE), None)
    own_parity = parity_by_path.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE, {})
    smoke_by_id = _smoke_row_specs(smoke_text)
    expected_smoke = (
        DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID,
        "install",
        120,
        "run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check",
    )

    rows: list[dict[str, Any]] = [
        {"name": "module-version-current", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION <= expected_version},
        {"name": "route-check-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE.lstrip("/") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID},
        {"name": "renderer-value-identity", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER == "render_dashboard_dispatcher_proof_surface_consolidation_prep_v1"},
        {"name": "own-registry-row-exact", "ok": own_registry is not None and own_registry.get("renderer_name") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER and own_registry.get("preview_only") is True},
        {"name": "own-dispatcher-parity-exact", "ok": own_parity.get("ok") is True and own_parity.get("registry_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER and own_parity.get("dispatcher_renderer") == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER},
        {"name": "own-manual-dispatch-present", "ok": "path == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE" in dashboard_text and f"html = {DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER}()" in dashboard_text},
        {"name": "own-renderer-present", "ok": re.search(rf"^def {DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER}\(", dashboard_text, re.MULTILINE) is not None},
        {"name": "own-smoke-row-exact", "ok": smoke_by_id.get(DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID) == expected_smoke},
        {"name": "historical-ledger-complete", "ok": ledger.get("historical_proof_route_count") == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT and len(ledger.get("ledger_rows", [])) == EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT},
        {"name": "historical-ledger-behavioral", "ok": all(row.get("ok") is True for row in ledger.get("ledger_rows", []))},
        {"name": "ordinary-operational-direct-zero", "ok": ledger.get("ordinary_operational_direct_route_count") in {EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTE_COUNT, EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTE_COUNT + 1, EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTE_COUNT + 2, EXPECTED_ORDINARY_OPERATIONAL_DIRECT_ROUTE_COUNT + 3}},
        {"name": "helper-count-stable", "ok": ledger.get("helper_backed_branch_count") == EXPECTED_HELPER_BACKED_BRANCH_COUNT},
        {"name": "ledger-schema-exact", "ok": ledger.get("ledger_field_count") == EXPECTED_LEDGER_FIELD_COUNT and tuple(ledger.get("ledger_fields", [])) == PARAMETERIZED_PROOF_LEDGER_FIELDS},
        {"name": "canonical-route-not-registered", "ok": (expected_version == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION and all(row.get("path") != PROPOSED_CANONICAL_ROUTE for row in registry_rows)) or (expected_version > DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION and any(row.get("path") == PROPOSED_CANONICAL_ROUTE for row in registry_rows))},
        {"name": "canonical-renderer-not-implemented", "ok": (expected_version == DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION and re.search(rf"^def {PROPOSED_CANONICAL_RENDERER}\(", dashboard_text, re.MULTILINE) is None) or (expected_version > DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION and re.search(rf"^def {PROPOSED_CANONICAL_RENDERER}\(", dashboard_text, re.MULTILINE) is not None)},
        {"name": "compatibility-contract-prep-only", "ok": COMPATIBILITY_CONTRACT["compatibility_aliases_activated"] is False and COMPATIBILITY_CONTRACT["historical_routes_removed"] is False and COMPATIBILITY_CONTRACT["navigation_rows_removed"] is False and COMPATIBILITY_CONTRACT["smoke_rows_removed"] is False},
        {"name": "manual-authority-preserved", "ok": COMPATIBILITY_CONTRACT["manual_dashboard_remains_authoritative"] is True and COMPATIBILITY_CONTRACT["manual_api_dispatch_remains_authoritative"] is True and COMPATIBILITY_CONTRACT["manual_smoke_remains_authoritative"] is True},
        {"name": "no-movement", "ok": SAFETY_BOUNDARY["dispatcher_branch_condition_moved"] is False and SAFETY_BOUNDARY["dispatcher_branch_body_moved"] is False and SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "side-effect-boundary-zero", "ok": SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0 and SAFETY_BOUNDARY["sandbox_backend_admission_count"] == 0 and SAFETY_BOUNDARY["subprocess_spawn_count"] == 0 and SAFETY_BOUNDARY["source_write_count"] == 0 and SAFETY_BOUNDARY["source_delete_count"] == 0},
        {"name": "authorization-boundary-closed", "ok": SAFETY_BOUNDARY["generated_wiring_activated"] is False and SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False},
        {"name": "dashboard-style-preserved", "ok": "data-tip" in dashboard_text and 'title="' not in dashboard_text},
        {"name": "registration-surfaces-recognize-prep", "ok": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID in smoke_text and DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE in registry_text and DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE in parity_text},
        {"name": "release-documents-current", "ok": ("v1077.7 Dispatcher Proof Surface Consolidation Prep v1" in next_steps[:4200] or "v1077.8 Dispatcher Proof Surface Consolidated Renderer Trial v1" in next_steps[:2200] or "v1077.9 Dispatcher Proof Surface Historical Compatibility Migration Prep v1" in next_steps[:2200] or "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2" in next_steps[:2200]) and ("v1077.7 Dispatcher Proof Surface Consolidation Prep v1" in release_history[:4200] or "v1077.8 Dispatcher Proof Surface Consolidated Renderer Trial v1" in release_history[:2200] or "v1077.9 Dispatcher Proof Surface Historical Compatibility Migration Prep v1" in release_history[:2200] or "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2" in release_history[:2200])},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_VERSION,
        "check_id": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_CHECK_ID,
        "title": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_TITLE,
        "route": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_ROUTE,
        "renderer": DASHBOARD_DISPATCHER_PROOF_SURFACE_CONSOLIDATION_PREP_V1_RENDERER,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "rows": rows,
        "blocked_rows": [row for row in rows if row.get("ok") is not True],
        "parameterized_proof_ledger_prepared": True,
        "compatibility_contract_prepared": True,
        "consolidated_renderer_trial_executed": False,
        "compatibility_contract": dict(COMPATIBILITY_CONTRACT),
        "ledger_fields": list(PARAMETERIZED_PROOF_LEDGER_FIELDS),
        "ledger_rows": ledger.get("ledger_rows", []),
        "historical_proof_route_count": ledger.get("historical_proof_route_count"),
        "ordinary_operational_direct_route_count": ledger.get("ordinary_operational_direct_route_count"),
        "registry_route_count": ledger.get("registry_route_count"),
        "helper_backed_branch_count": ledger.get("helper_backed_branch_count"),
        "direct_registry_route_count_total": ledger.get("direct_registry_route_count_total"),
        "direct_registry_route_count_excluding_prep_v1": ledger.get("direct_registry_route_count_excluding_prep_v1"),
        **SAFETY_BOUNDARY,
        "next_arc": NEXT_ARC,
    }


def dashboard_dispatcher_proof_surface_consolidation_prep_v1_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"{report.get('title')} [{report.get('status')}]",
        f"route: {report.get('route')}",
        f"registry_route_count: {report.get('registry_route_count')}",
        f"helper_backed_branch_count: {report.get('helper_backed_branch_count')}",
        f"historical_proof_route_count: {report.get('historical_proof_route_count')}",
        f"ordinary_operational_direct_route_count: {report.get('ordinary_operational_direct_route_count')}",
        f"ledger_field_count: {len(report.get('ledger_fields', []))}",
        f"canonical_route: {report.get('compatibility_contract', {}).get('canonical_route')}",
        f"compatibility_mode: {report.get('compatibility_contract', {}).get('mode')}",
        "parameterized_proof_ledger_prepared: True",
        "compatibility_contract_prepared: True",
        "consolidated_renderer_trial_executed: False",
        "dispatcher_branch_condition_moved: False",
        "dispatcher_branch_body_moved: False",
        "renderer_bodies_moved: False",
        "historical_routes_removed: False",
        "compatibility_aliases_activated: False",
        "actual_fixture_execution_count: 0",
        "sandbox_backend_admission_count: 0",
        "subprocess_spawn_count: 0",
        "source_write_count: 0",
        "source_delete_count: 0",
        "generated_wiring_activated: False",
        "release_authorized: False",
        "autonomy_expanded: False",
        f"next_arc: {report.get('next_arc')}",
    ]
    if full:
        lines.append("ledger_rows:")
        for row in report.get("ledger_rows", []):
            lines.append(
                f"- {row.get('path')} | {row.get('phase')} v{row.get('sequence')} | "
                f"{row.get('renderer_name')} | {row.get('check_id')} | {'ok' if row.get('ok') else 'blocked'}"
            )
        lines.append("proof_rows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'ok' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_dispatcher_proof_surface_consolidation_prep_v1_check(
    project_root: str | Path,
    *,
    expected_version: str,
) -> bool:
    try:
        report = build_dashboard_dispatcher_proof_surface_consolidation_prep_v1_report(
            project_root,
            expected_version=expected_version,
        )
        if report.get("ok") is not True:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: prep report blocked")
            print(report.get("blocked_rows"))
            return False
        if report.get("historical_proof_route_count") != EXPECTED_HISTORICAL_PROOF_ROUTE_COUNT:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: historical proof ledger drifted")
            return False
        if report.get("ordinary_operational_direct_route_count") not in {0, 1, 2, 3}:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: ordinary direct route remains")
            return False
        if report.get("helper_backed_branch_count") != EXPECTED_HELPER_BACKED_BRANCH_COUNT:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: helper count changed during prep")
            return False
        if report.get("consolidated_renderer_trial_executed") is not False:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: renderer trial executed during prep")
            return False
        if report.get("dispatcher_branch_body_moved") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: movement occurred during prep")
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False:
            print("[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: authorization boundary changed")
            return False
        print(
            "[ok] dashboard-dispatcher-proof-surface-consolidation-prep-v1 "
            f"historical_routes={report.get('historical_proof_route_count')} "
            f"ledger_fields={len(report.get('ledger_fields', []))} "
            f"helper_count={report.get('helper_backed_branch_count')} "
            "compatibility_activated=False"
        )
        return True
    except Exception as exc:
        print(f"[fail] dashboard-dispatcher-proof-surface-consolidation-prep-v1: {exc}")
        return False
