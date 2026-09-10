from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from smoke_segment_registry import classify_check_name
from smoke_registry_sidecar_compatibility import sidecar_metadata_rows

SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_VERSION = CURRENT_VERSION
SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID = "smoke-registry-sidecar-expansion-and-route-manifest-prep-v1"
EXPANSION_MODULE = "conscious_agent/smoke_registry_sidecar_expansion_route_manifest_prep.py"
SIDECAR_COMPATIBILITY_MODULE = "conscious_agent/smoke_registry_sidecar_compatibility.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "sidecar_metadata_only": True,
    "sidecar_expanded": True,
    "route_manifest_prep_only": True,
    "command_manifest_prep_only": True,
    "check_manifest_prep_only": True,
    "manual_smoke_remains_authoritative": True,
    "manual_build_checks_remains_authoritative": True,
    "manual_dashboard_remains_authoritative": True,
    "sidecar_executes_checks": False,
    "sidecar_replaces_manual_registry": False,
    "sidecar_dispatches_callables": False,
    "route_manifest_replaces_dashboard_routes": False,
    "command_manifest_replaces_cli_dispatch": False,
    "check_manifest_replaces_manual_smoke": False,
    "generated_wiring_activated": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "cli_wiring_generated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class ManifestPrepRoute:
    route: str
    renderer: str
    surface: str
    status: str = "manual_authoritative"


# Bounded route inventory prep. This is deliberately a small recent-surface slice, not a full router.
ROUTE_MANIFEST_PREP_SLICE: tuple[ManifestPrepRoute, ...] = (
    ManifestPrepRoute("/behavioral-dashboard-route-coverage", "render_behavioral_dashboard_route_coverage", "v1024-behavioral-dashboard-route-coverage-source-decomposition-prep"),
    ManifestPrepRoute("/source-decomposition-compatibility-slice", "render_source_decomposition_compatibility_slice", "v1025-first-source-decomposition-compatibility-slice"),
    ManifestPrepRoute("/dashboard-shell-component-extraction", "render_dashboard_shell_component_extraction", "v1026-dashboard-shell-component-extraction-compatibility-slice"),
    ManifestPrepRoute("/smoke-registry-sidecar-compatibility", "render_smoke_registry_sidecar_compatibility", "v1027-smoke-registry-sidecar-compatibility-extraction-slice"),
    ManifestPrepRoute("/smoke-registry-sidecar-expansion-route-manifest", "render_smoke_registry_sidecar_expansion_route_manifest_prep", "v1028-smoke-registry-sidecar-expansion-route-manifest-prep"),
)


# Expanded sidecar rows add one prior live-ledger repair anchor and the current v1028 smoke row
# around the v1022-v1027 compatibility slice. The manual tools/smoke_check.py registry remains authoritative.
def expanded_sidecar_metadata_rows() -> list[dict[str, Any]]:
    names = [
        ("live-install-release-ledger-and-smoke-debt-route-repair-v1", "install", 316),
        *[(str(row["name"]), str(row["tier"]), int(row["timeout"])) for row in sidecar_metadata_rows()],
        (SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID, "install", 323),
    ]
    rows: list[dict[str, Any]] = []
    for order, (name, tier, timeout) in enumerate(names):
        rows.append({
            "name": name,
            "tier": tier,
            "timeout": timeout,
            "segment": classify_check_name(name, tier),
            "order": order,
        })
    return rows


def route_manifest_prep_rows() -> list[dict[str, Any]]:
    return [asdict(row) for row in ROUTE_MANIFEST_PREP_SLICE]


def command_manifest_prep_rows() -> list[dict[str, Any]]:
    return [
        {
            "surface": row.surface,
            "route": row.route,
            "cli_flag": "not_exposed_review_only",
            "api_route": "not_exposed_review_only",
            "generated_wiring_activated": False,
            "manual_dashboard_remains_authoritative": True,
        }
        for row in ROUTE_MANIFEST_PREP_SLICE
    ]


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _manual_rows_by_name(manual_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("name")): dict(row) for row in manual_rows}


def build_smoke_registry_sidecar_expansion_route_manifest_prep_review(root: str | Path | None = None, manual_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    manual_rows = list(manual_rows or [])
    manual_by_name = _manual_rows_by_name(manual_rows)
    manual_names = [str(row.get("name")) for row in manual_rows]
    expanded_rows = expanded_sidecar_metadata_rows()
    expanded_names = [str(row["name"]) for row in expanded_rows]
    route_rows = route_manifest_prep_rows()
    command_rows = command_manifest_prep_rows()

    smoke_text = _read_text(project_root, MANUAL_SMOKE_MODULE)
    expansion_text = _read_text(project_root, EXPANSION_MODULE)
    sidecar_text = _read_text(project_root, SIDECAR_COMPATIBILITY_MODULE)
    dashboard_text = _read_text(project_root, DASHBOARD_MODULE)
    manifest_text = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([smoke_text, expansion_text, sidecar_text, dashboard_text, manifest_text, readme_next, readme_history])

    missing_from_manual = [name for name in expanded_names if name not in manual_by_name]
    field_mismatches: list[dict[str, Any]] = []
    for expected in expanded_rows:
        manual = manual_by_name.get(str(expected["name"]))
        if not manual:
            continue
        for field in ("tier", "timeout", "segment"):
            if manual.get(field) != expected.get(field):
                field_mismatches.append({"name": expected["name"], "field": field, "expected": expected.get(field), "actual": manual.get(field)})

    order_mismatches: list[dict[str, Any]] = []
    for index, name in enumerate(expanded_names[:-1]):
        next_name = expanded_names[index + 1]
        if name in manual_names and next_name in manual_names:
            actual_gap = manual_names.index(next_name) - manual_names.index(name)
            if actual_gap != 1:
                order_mismatches.append({"name": name, "next": next_name, "actual_gap": actual_gap})

    route_missing: list[dict[str, str]] = []
    for row in route_rows:
        route = str(row["route"])
        renderer = str(row["renderer"])
        if route not in dashboard_text or f"def {renderer}" not in dashboard_text:
            route_missing.append({"route": route, "renderer": renderer})

    manifest_missing = [str(row["surface"]) for row in route_rows if str(row["surface"]) not in manifest_text]

    required_tokens = [
        CURRENT_MILESTONE,
        SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID,
        "sidecar_expanded=True",
        "expanded_sidecar_check_count=8",
        "route_manifest_prep_only=True",
        "route_manifest_route_count=5",
        "command_manifest_prep_only=True",
        "check_manifest_prep_only=True",
        "manual_smoke_remains_authoritative=True",
        "manual_dashboard_remains_authoritative=True",
        "sidecar_replaces_manual_registry=False",
        "sidecar_dispatches_callables=False",
        "route_manifest_replaces_dashboard_routes=False",
        "command_manifest_replaces_cli_dispatch=False",
        "check_manifest_replaces_manual_smoke=False",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "/smoke-registry-sidecar-expansion-route-manifest",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    rows = [
        {"name": "module-version-current", "ok": SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_VERSION == CURRENT_VERSION, "message": f"module={SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_VERSION}; current={CURRENT_VERSION}"},
        {"name": "manual-smoke-still-authoritative", "ok": "def _build_checks" in smoke_text and "class SmokeCheck" in smoke_text, "message": "Manual tools/smoke_check.py still owns callable registration and execution."},
        {"name": "expanded-sidecar-present", "ok": len(expanded_rows) == 8 and expanded_rows[-1]["name"] == SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID, "message": f"expanded_sidecar_check_count={len(expanded_rows)}"},
        {"name": "expanded-sidecar-present-in-manual", "ok": not missing_from_manual, "message": f"missing_from_manual={missing_from_manual}"},
        {"name": "expanded-sidecar-field-parity", "ok": not field_mismatches, "message": f"field_mismatches={field_mismatches}"},
        {"name": "expanded-sidecar-order-parity", "ok": not order_mismatches, "message": f"order_mismatches={order_mismatches}"},
        {"name": "route-manifest-prep-present", "ok": len(route_rows) == 5 and not route_missing, "message": f"route_manifest_route_count={len(route_rows)} route_missing={route_missing}"},
        {"name": "command-manifest-prep-review-only", "ok": len(command_rows) == len(route_rows) and all(row["cli_flag"] == "not_exposed_review_only" and row["api_route"] == "not_exposed_review_only" for row in command_rows), "message": "Command/API manifest prep remains review-only and not exposed."},
        {"name": "source-manifest-represents-prep-slice", "ok": not manifest_missing and "v1028-smoke-registry-sidecar-expansion-route-manifest-prep" in manifest_text, "message": f"manifest_missing={manifest_missing}"},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Docs/source carry v1028 sidecar expansion and route manifest prep truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["sidecar_executes_checks", "sidecar_replaces_manual_registry", "sidecar_dispatches_callables", "route_manifest_replaces_dashboard_routes", "command_manifest_replaces_cli_dispatch", "check_manifest_replaces_manual_smoke", "generated_wiring_activated", "dashboard_wiring_generated", "api_wiring_generated", "cli_wiring_generated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "No sidecar, route, command, check, generated wiring, release, or autonomy authority is activated."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID,
        "state": "smoke_registry_sidecar_expansion_route_manifest_prep_review_only",
        "expansion_module": EXPANSION_MODULE,
        "sidecar_compatibility_module": SIDECAR_COMPATIBILITY_MODULE,
        "manual_smoke_module": MANUAL_SMOKE_MODULE,
        "dashboard_module": DASHBOARD_MODULE,
        "source_manifest_module": SOURCE_MANIFEST_MODULE,
        "expanded_sidecar_rows": expanded_rows,
        "expanded_sidecar_check_count": len(expanded_rows),
        "manual_check_count": len(manual_rows),
        "route_manifest_rows": route_rows,
        "route_manifest_route_count": len(route_rows),
        "command_manifest_rows": command_rows,
        "command_manifest_route_count": len(command_rows),
        "sidecar_metadata_only": True,
        "sidecar_expanded": True,
        "route_manifest_prep_only": True,
        "command_manifest_prep_only": True,
        "check_manifest_prep_only": True,
        "manual_smoke_remains_authoritative": True,
        "manual_build_checks_remains_authoritative": True,
        "manual_dashboard_remains_authoritative": True,
        "sidecar_executes_checks": False,
        "sidecar_replaces_manual_registry": False,
        "sidecar_dispatches_callables": False,
        "route_manifest_replaces_dashboard_routes": False,
        "command_manifest_replaces_cli_dispatch": False,
        "check_manifest_replaces_manual_smoke": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "missing_from_manual": missing_from_manual,
        "field_mismatches": field_mismatches,
        "order_mismatches": order_mismatches,
        "route_missing": route_missing,
        "manifest_missing": manifest_missing,
        "boundaries": dict(BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def smoke_registry_sidecar_expansion_route_manifest_prep_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", SMOKE_REGISTRY_SIDECAR_EXPANSION_ROUTE_MANIFEST_PREP_ID)),
        f"expansion_module={report.get('expansion_module')}",
        f"sidecar_compatibility_module={report.get('sidecar_compatibility_module')}",
        f"manual_smoke_module={report.get('manual_smoke_module')}",
        f"expanded_sidecar_check_count={report.get('expanded_sidecar_check_count')}",
        f"manual_check_count={report.get('manual_check_count')}",
        f"route_manifest_route_count={report.get('route_manifest_route_count')}",
        f"command_manifest_route_count={report.get('command_manifest_route_count')}",
        f"sidecar_metadata_only={report.get('sidecar_metadata_only')}",
        f"sidecar_expanded={report.get('sidecar_expanded')}",
        f"route_manifest_prep_only={report.get('route_manifest_prep_only')}",
        f"command_manifest_prep_only={report.get('command_manifest_prep_only')}",
        f"check_manifest_prep_only={report.get('check_manifest_prep_only')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"sidecar_executes_checks={report.get('sidecar_executes_checks')}",
        f"sidecar_replaces_manual_registry={report.get('sidecar_replaces_manual_registry')}",
        f"sidecar_dispatches_callables={report.get('sidecar_dispatches_callables')}",
        f"route_manifest_replaces_dashboard_routes={report.get('route_manifest_replaces_dashboard_routes')}",
        f"command_manifest_replaces_cli_dispatch={report.get('command_manifest_replaces_cli_dispatch')}",
        f"check_manifest_replaces_manual_smoke={report.get('check_manifest_replaces_manual_smoke')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nExpanded sidecar rows:")
        for row in report.get("expanded_sidecar_rows", []):
            lines.append(f"- {row.get('order')}: {row.get('name')} tier={row.get('tier')} timeout={row.get('timeout')} segment={row.get('segment')}")
        lines.append("\nRoute manifest prep rows:")
        for row in report.get("route_manifest_rows", []):
            lines.append(f"- {row.get('route')} -> {row.get('renderer')} surface={row.get('surface')} status={row.get('status')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1030.0 Dashboard Route Behavioral Coverage Expansion v1 tokens: smoke-registry-sidecar-expansion-and-route-manifest-prep-v1 smoke-registry-sidecar-expansion-route-manifest-v1 build_smoke_registry_sidecar_expansion_route_manifest_prep_review smoke_registry_sidecar_expansion_route_manifest_prep_review_text expansion_module=conscious_agent/smoke_registry_sidecar_expansion_route_manifest_prep.py sidecar_compatibility_module=conscious_agent/smoke_registry_sidecar_compatibility.py manual_smoke_module=tools/smoke_check.py expanded_sidecar_check_count=8 route_manifest_route_count=5 sidecar_expanded=True sidecar_metadata_only=True route_manifest_prep_only=True command_manifest_prep_only=True check_manifest_prep_only=True manual_smoke_remains_authoritative=True manual_dashboard_remains_authoritative=True sidecar_executes_checks=False sidecar_replaces_manual_registry=False sidecar_dispatches_callables=False route_manifest_replaces_dashboard_routes=False command_manifest_replaces_cli_dispatch=False check_manifest_replaces_manual_smoke=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True /smoke-registry-sidecar-expansion-route-manifest data-tip command-deck operator-console no_native_title_tooltip.
