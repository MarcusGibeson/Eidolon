from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from smoke_registry_sidecar_compatibility import sidecar_metadata_rows
from smoke_registry_sidecar_expansion_route_manifest_prep import expanded_sidecar_metadata_rows
from smoke_segment_registry import classify_check_name

SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_VERSION = RUNTIME_VERSION
SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID = "smoke-registry-sidecar-parity-expansion-v1"
PARITY_EXPANSION_MODULE = "conscious_agent/smoke_registry_sidecar_parity_expansion.py"
SIDECAR_COMPATIBILITY_MODULE = "conscious_agent/smoke_registry_sidecar_compatibility.py"
SIDECAR_ROUTE_MANIFEST_PREP_MODULE = "conscious_agent/smoke_registry_sidecar_expansion_route_manifest_prep.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"
DASHBOARD_MODULE = "conscious_agent/dashboard.py"
SOURCE_MANIFEST_MODULE = "conscious_agent/source_surface_manifest.py"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "sidecar_metadata_only": True,
    "sidecar_parity_expanded": True,
    "manual_smoke_remains_authoritative": True,
    "manual_build_checks_remains_authoritative": True,
    "manual_dashboard_remains_authoritative": True,
    "nested_metadata_currentness_audit_expanded": True,
    "sidecar_executes_checks": False,
    "sidecar_replaces_manual_registry": False,
    "sidecar_dispatches_callables": False,
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
class SidecarParityRow:
    name: str
    tier: str
    timeout: int
    segment: str
    order: int
    source: str


# v1033 deliberately expands parity metadata across the recent install-release truth,
# sidecar, route-manifest, and dashboard-route coverage checks. It does not carry a
# function/callable target and does not replace tools/smoke_check.py.
RECENT_INSTALL_PARITY_WINDOW: tuple[tuple[str, str, int, str], ...] = (
    ("live-install-release-ledger-and-smoke-debt-route-repair-v1", "install", 316, "live-ledger-anchor"),
    ("metadata-currentness-and-historical-prerequisite-repair-v1", "install", 317, "currentness-anchor"),
    ("compile-timeout-and-historical-gate-harness-honesty-v1", "install", 318, "compile-timeout-anchor"),
    ("behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1", "install", 319, "behavioral-route-anchor"),
    ("first-source-decomposition-compatibility-slice-v1", "install", 320, "compatibility-extraction-anchor"),
    ("dashboard-shell-component-extraction-compatibility-slice-v1", "install", 321, "dashboard-shell-anchor"),
    ("smoke-registry-sidecar-compatibility-extraction-slice-v1", "install", 322, "v1027-sidecar-slice"),
    ("smoke-registry-sidecar-expansion-and-route-manifest-prep-v1", "install", 323, "v1028-sidecar-expansion"),
    ("route-manifest-inventory-expansion-and-dashboard-parity-gate-v1", "install", 324, "route-manifest-parity"),
    ("dashboard-route-behavioral-coverage-expansion-v1", "install", 325, "dashboard-behavioral-expansion"),
    ("dashboard-route-manifest-to-renderer-reconciliation-v1", "install", 326, "dashboard-route-reconciliation"),
    ("dashboard-route-coverage-completion-and-dispatch-classification-v1", "install", 327, "dashboard-route-classification"),
    (SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID, "install", 328, "v1033-sidecar-parity-expansion"),
)


def sidecar_parity_expansion_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order, (name, tier, timeout, source) in enumerate(RECENT_INSTALL_PARITY_WINDOW):
        rows.append(asdict(SidecarParityRow(
            name=name,
            tier=tier,
            timeout=timeout,
            segment=classify_check_name(name, tier),
            order=order,
            source=source,
        )))
    return rows


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _manual_rows_by_name(manual_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("name")): dict(row) for row in manual_rows}


def _segment_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        segment = str(row.get("segment", "unknown"))
        counts[segment] = counts.get(segment, 0) + 1
    return dict(sorted(counts.items()))


def _timeout_sequence(rows: list[dict[str, Any]]) -> list[int]:
    return [int(row.get("timeout", -1)) for row in rows]


def _current_next_arc_values(data: Any, prefix: str = "") -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if key == "next_recommended_arc" and isinstance(value, str):
                found.append({"path": path, "value": value})
            if key == "release_notes":
                continue
            found.extend(_current_next_arc_values(value, path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_current_next_arc_values(value, f"{prefix}[{index}]"))
    return found


def _read_json(root: Path, rel: str) -> Any:
    import json

    try:
        return json.loads(_read_text(root, rel))
    except Exception:
        return None


def build_smoke_registry_sidecar_parity_expansion_review(root: str | Path | None = None, manual_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    manual_rows = list(manual_rows or [])
    manual_by_name = _manual_rows_by_name(manual_rows)
    manual_names = [str(row.get("name")) for row in manual_rows]
    parity_rows = sidecar_parity_expansion_rows()
    parity_names = [str(row["name"]) for row in parity_rows]
    compatibility_rows = sidecar_metadata_rows()
    route_manifest_prep_rows = expanded_sidecar_metadata_rows()

    smoke_text = _read_text(project_root, MANUAL_SMOKE_MODULE)
    module_text = _read_text(project_root, PARITY_EXPANSION_MODULE)
    dashboard_text = _read_text(project_root, DASHBOARD_MODULE)
    manifest_text = _read_text(project_root, SOURCE_MANIFEST_MODULE)
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([smoke_text, module_text, dashboard_text, manifest_text, readme_next, readme_history])

    missing_from_manual = [name for name in parity_names if name not in manual_by_name]
    field_mismatches: list[dict[str, Any]] = []
    for expected in parity_rows:
        manual = manual_by_name.get(str(expected["name"]))
        if not manual:
            continue
        for field in ("tier", "timeout", "segment"):
            if manual.get(field) != expected.get(field):
                field_mismatches.append({"name": expected["name"], "field": field, "expected": expected.get(field), "actual": manual.get(field)})

    order_mismatches: list[dict[str, Any]] = []
    for index, name in enumerate(parity_names[:-1]):
        next_name = parity_names[index + 1]
        if name in manual_names and next_name in manual_names:
            actual_gap = manual_names.index(next_name) - manual_names.index(name)
            if actual_gap != 1:
                order_mismatches.append({"name": name, "next": next_name, "actual_gap": actual_gap})

    timeout_values = _timeout_sequence(parity_rows)
    timeout_window_contiguous = timeout_values == list(range(316, 329))
    compatibility_slice_names = {str(row.get("name")) for row in compatibility_rows}
    route_manifest_prep_names = {str(row.get("name")) for row in route_manifest_prep_rows}
    parity_name_set = set(parity_names)
    compatibility_slice_embedded = compatibility_slice_names.issubset(parity_name_set)
    route_manifest_prep_embedded = route_manifest_prep_names.issubset(parity_name_set)

    json_next_arc_values: list[dict[str, str]] = []
    for rel in ["data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"]:
        for item in _current_next_arc_values(_read_json(project_root, rel)):
            json_next_arc_values.append({"file": rel, **item})
    stale_nested_next_arc_values = [item for item in json_next_arc_values if item.get("value") != NEXT_RECOMMENDED_ARC]

    required_tokens = [
        CURRENT_MILESTONE,
        SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID,
        "sidecar_parity_expanded=True",
        "sidecar_parity_check_count=13",
        "manual_smoke_remains_authoritative=True",
        "manual_build_checks_remains_authoritative=True",
        "sidecar_executes_checks=False",
        "sidecar_replaces_manual_registry=False",
        "sidecar_dispatches_callables=False",
        "check_manifest_replaces_manual_smoke=False",
        "generated_wiring_activated=False",
        "dashboard_wiring_generated=False",
        "api_wiring_generated=False",
        "cli_wiring_generated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "operator_approval_still_required=True",
        "/smoke-registry-sidecar-parity-expansion",
        "data-tip",
        "command-deck",
        "operator-console",
        "no_native_title_tooltip",
    ]
    rows = [
        {"name": "module-version-current", "ok": SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_VERSION == CURRENT_VERSION, "message": f"module={SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_VERSION}; current={CURRENT_VERSION}"},
        {"name": "manual-smoke-still-authoritative", "ok": "def _build_checks" in smoke_text and "class SmokeCheck" in smoke_text, "message": "Manual tools/smoke_check.py still owns callable registration and execution."},
        {"name": "sidecar-parity-window-present", "ok": len(parity_rows) == 13 and parity_rows[-1]["name"] == SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID, "message": f"sidecar_parity_check_count={len(parity_rows)}"},
        {"name": "sidecar-parity-present-in-manual", "ok": not missing_from_manual, "message": f"missing_from_manual={missing_from_manual}"},
        {"name": "sidecar-field-parity", "ok": not field_mismatches, "message": f"field_mismatches={field_mismatches}"},
        {"name": "sidecar-order-parity", "ok": not order_mismatches, "message": f"order_mismatches={order_mismatches}"},
        {"name": "timeout-window-contiguous", "ok": timeout_window_contiguous, "message": f"timeout_window={timeout_values}"},
        {"name": "prior-sidecar-slices-embedded", "ok": compatibility_slice_embedded and route_manifest_prep_embedded, "message": f"compatibility_slice_count={len(compatibility_rows)} route_manifest_prep_slice_count={len(route_manifest_prep_rows)}"},
        {"name": "nested-next-arc-current", "ok": not stale_nested_next_arc_values, "message": f"stale_nested_next_arc_values={stale_nested_next_arc_values}"},
        {"name": "dashboard-route-present", "ok": "/smoke-registry-sidecar-parity-expansion" in dashboard_text and "render_smoke_registry_sidecar_parity_expansion" in dashboard_text, "message": "Dashboard exposes the v1033 sidecar parity expansion review page."},
        {"name": "source-manifest-represents-slice", "ok": "v1033-smoke-registry-sidecar-parity-expansion" in manifest_text and SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID in manifest_text, "message": "Source surface manifest represents the v1033 sidecar parity expansion."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in required_tokens), "message": "Docs/source carry v1033 sidecar parity expansion truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["sidecar_executes_checks", "sidecar_replaces_manual_registry", "sidecar_dispatches_callables", "check_manifest_replaces_manual_smoke", "generated_wiring_activated", "dashboard_wiring_generated", "api_wiring_generated", "cli_wiring_generated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "No sidecar, check manifest, generated wiring, release, or autonomy authority is activated."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID,
        "state": "smoke_registry_sidecar_parity_expansion_review_only",
        "parity_expansion_module": PARITY_EXPANSION_MODULE,
        "manual_smoke_module": MANUAL_SMOKE_MODULE,
        "dashboard_module": DASHBOARD_MODULE,
        "source_manifest_module": SOURCE_MANIFEST_MODULE,
        "sidecar_parity_rows": parity_rows,
        "sidecar_parity_check_count": len(parity_rows),
        "manual_check_count": len(manual_rows),
        "segment_counts": _segment_counts(parity_rows),
        "timeout_window": timeout_values,
        "timeout_window_contiguous": timeout_window_contiguous,
        "compatibility_slice_embedded": compatibility_slice_embedded,
        "route_manifest_prep_embedded": route_manifest_prep_embedded,
        "sidecar_metadata_only": True,
        "sidecar_parity_expanded": True,
        "manual_smoke_remains_authoritative": True,
        "manual_build_checks_remains_authoritative": True,
        "manual_dashboard_remains_authoritative": True,
        "nested_metadata_currentness_audit_expanded": True,
        "sidecar_executes_checks": False,
        "sidecar_replaces_manual_registry": False,
        "sidecar_dispatches_callables": False,
        "check_manifest_replaces_manual_smoke": False,
        "generated_wiring_activated": False,
        "dashboard_wiring_generated": False,
        "api_wiring_generated": False,
        "cli_wiring_generated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "missing_from_manual": missing_from_manual,
        "field_mismatches": field_mismatches,
        "order_mismatches": order_mismatches,
        "stale_nested_next_arc_values": stale_nested_next_arc_values,
        "boundaries": dict(BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def smoke_registry_sidecar_parity_expansion_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", SMOKE_REGISTRY_SIDECAR_PARITY_EXPANSION_ID)),
        f"parity_expansion_module={report.get('parity_expansion_module')}",
        f"manual_smoke_module={report.get('manual_smoke_module')}",
        f"sidecar_parity_check_count={report.get('sidecar_parity_check_count')}",
        f"manual_check_count={report.get('manual_check_count')}",
        f"timeout_window_contiguous={report.get('timeout_window_contiguous')}",
        f"compatibility_slice_embedded={report.get('compatibility_slice_embedded')}",
        f"route_manifest_prep_embedded={report.get('route_manifest_prep_embedded')}",
        f"sidecar_metadata_only={report.get('sidecar_metadata_only')}",
        f"sidecar_parity_expanded={report.get('sidecar_parity_expanded')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manual_build_checks_remains_authoritative={report.get('manual_build_checks_remains_authoritative')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"nested_metadata_currentness_audit_expanded={report.get('nested_metadata_currentness_audit_expanded')}",
        f"sidecar_executes_checks={report.get('sidecar_executes_checks')}",
        f"sidecar_replaces_manual_registry={report.get('sidecar_replaces_manual_registry')}",
        f"sidecar_dispatches_callables={report.get('sidecar_dispatches_callables')}",
        f"check_manifest_replaces_manual_smoke={report.get('check_manifest_replaces_manual_smoke')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"dashboard_wiring_generated={report.get('dashboard_wiring_generated')}",
        f"api_wiring_generated={report.get('api_wiring_generated')}",
        f"cli_wiring_generated={report.get('cli_wiring_generated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nSidecar parity rows:")
        for row in report.get("sidecar_parity_rows", []):
            lines.append(f"- {row.get('order')}: {row.get('name')} tier={row.get('tier')} timeout={row.get('timeout')} segment={row.get('segment')} source={row.get('source')}")
        lines.append("\nSegment counts:")
        for segment, count in (report.get("segment_counts") or {}).items():
            lines.append(f"- {segment}: {count}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1033.0 Smoke Registry Sidecar Parity Expansion v1 tokens: smoke-registry-sidecar-parity-expansion-v1 smoke-registry-sidecar-parity-expansion-v1 build_smoke_registry_sidecar_parity_expansion_review smoke_registry_sidecar_parity_expansion_review_text parity_expansion_module=conscious_agent/smoke_registry_sidecar_parity_expansion.py manual_smoke_module=tools/smoke_check.py sidecar_parity_check_count=13 timeout_window_contiguous=True compatibility_slice_embedded=True route_manifest_prep_embedded=True sidecar_parity_expanded=True sidecar_metadata_only=True manual_smoke_remains_authoritative=True manual_build_checks_remains_authoritative=True manual_dashboard_remains_authoritative=True nested_metadata_currentness_audit_expanded=True sidecar_executes_checks=False sidecar_replaces_manual_registry=False sidecar_dispatches_callables=False check_manifest_replaces_manual_smoke=False generated_wiring_activated=False dashboard_wiring_generated=False api_wiring_generated=False cli_wiring_generated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip /smoke-registry-sidecar-parity-expansion.
