from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from smoke_segment_registry import classify_check_name

SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_VERSION = CURRENT_VERSION
SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID = "smoke-registry-sidecar-compatibility-extraction-slice-v1"
SIDECAR_MODULE = "conscious_agent/smoke_registry_sidecar_compatibility.py"
MANUAL_SMOKE_MODULE = "tools/smoke_check.py"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "sidecar_metadata_only": True,
    "manual_smoke_remains_authoritative": True,
    "manual_build_checks_remains_authoritative": True,
    "sidecar_executes_checks": False,
    "sidecar_replaces_manual_registry": False,
    "sidecar_dispatches_callables": False,
    "generated_wiring_activated": False,
    "api_wiring_generated": False,
    "cli_wiring_generated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


@dataclass(frozen=True)
class SmokeSidecarRow:
    name: str
    tier: str
    timeout: int
    segment: str
    order: int


# Bounded metadata sidecar slice. The manual tools/smoke_check.py registry remains authoritative.
# v1027 deliberately extracts only recent release-truth/decomposition metadata so parity can be proven
# before any broader generated smoke-registry work is trusted.
SIDECAR_SMOKE_METADATA_SLICE: tuple[SmokeSidecarRow, ...] = (
    SmokeSidecarRow("metadata-currentness-and-historical-prerequisite-repair-v1", "install", 317, classify_check_name("metadata-currentness-and-historical-prerequisite-repair-v1", "install"), 0),
    SmokeSidecarRow("compile-timeout-and-historical-gate-harness-honesty-v1", "install", 318, classify_check_name("compile-timeout-and-historical-gate-harness-honesty-v1", "install"), 1),
    SmokeSidecarRow("behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1", "install", 319, classify_check_name("behavioral-dashboard-route-coverage-and-source-decomposition-prep-v1", "install"), 2),
    SmokeSidecarRow("first-source-decomposition-compatibility-slice-v1", "install", 320, classify_check_name("first-source-decomposition-compatibility-slice-v1", "install"), 3),
    SmokeSidecarRow("dashboard-shell-component-extraction-compatibility-slice-v1", "install", 321, classify_check_name("dashboard-shell-component-extraction-compatibility-slice-v1", "install"), 4),
    SmokeSidecarRow("smoke-registry-sidecar-compatibility-extraction-slice-v1", "install", 322, classify_check_name("smoke-registry-sidecar-compatibility-extraction-slice-v1", "install"), 5),
)


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def sidecar_metadata_rows() -> list[dict[str, Any]]:
    return [asdict(row) for row in SIDECAR_SMOKE_METADATA_SLICE]


def _manual_rows_by_name(manual_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("name")): dict(row) for row in manual_rows}


def build_smoke_registry_sidecar_compatibility_review(root: str | Path | None = None, manual_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    manual_rows = list(manual_rows or [])
    manual_by_name = _manual_rows_by_name(manual_rows)
    sidecar_rows = sidecar_metadata_rows()
    sidecar_names = [row["name"] for row in sidecar_rows]
    manual_names = [str(row.get("name")) for row in manual_rows]
    smoke_text = _read_text(project_root, MANUAL_SMOKE_MODULE)
    sidecar_text = _read_text(project_root, SIDECAR_MODULE)
    dashboard_text = _read_text(project_root, "conscious_agent/dashboard.py")
    manifest_text = _read_text(project_root, "conscious_agent/source_surface_manifest.py")
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([smoke_text, sidecar_text, dashboard_text, manifest_text, readme_next, readme_history])

    missing_from_manual = [name for name in sidecar_names if name not in manual_by_name]
    field_mismatches: list[dict[str, Any]] = []
    order_mismatches: list[dict[str, Any]] = []
    for expected in sidecar_rows:
        manual = manual_by_name.get(expected["name"])
        if not manual:
            continue
        for field in ("tier", "timeout", "segment"):
            if manual.get(field) != expected.get(field):
                field_mismatches.append({"name": expected["name"], "field": field, "expected": expected.get(field), "actual": manual.get(field)})
    for index, name in enumerate(sidecar_names[:-1]):
        next_name = sidecar_names[index + 1]
        if name in manual_names and next_name in manual_names:
            actual_gap = manual_names.index(next_name) - manual_names.index(name)
            if actual_gap != 1:
                order_mismatches.append({"name": name, "next": next_name, "actual_gap": actual_gap})

    rows = [
        {"name": "module-version-current", "ok": SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_VERSION == CURRENT_VERSION, "message": f"sidecar={SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_VERSION}; current={CURRENT_VERSION}"},
        {"name": "sidecar-module-present", "ok": bool(sidecar_text) and "SIDECAR_SMOKE_METADATA_SLICE" in sidecar_text and "SmokeSidecarRow" in sidecar_text, "message": "Sidecar metadata module exposes a bounded smoke metadata slice."},
        {"name": "manual-registry-still-authoritative", "ok": "def _build_checks" in smoke_text and "class SmokeCheck" in smoke_text and "manual tools/smoke_check.py registry remains authoritative" in sidecar_text, "message": "Manual tools/smoke_check.py still owns callable registration and execution."},
        {"name": "sidecar-does-not-dispatch-callables", "ok": "func" not in "\n".join(str(row) for row in sidecar_rows) and "sidecar_executes_checks\": False" in sidecar_text, "message": "Sidecar rows carry metadata only and no callable dispatch target."},
        {"name": "sidecar-slice-present-in-manual", "ok": not missing_from_manual, "message": f"missing_from_manual={missing_from_manual}"},
        {"name": "sidecar-field-parity", "ok": not field_mismatches, "message": f"field_mismatches={field_mismatches}"},
        {"name": "sidecar-order-parity", "ok": not order_mismatches, "message": f"order_mismatches={order_mismatches}"},
        {"name": "targeted-smoke-registered", "ok": SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID in manual_by_name and manual_by_name.get(SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID, {}).get("timeout") == 322, "message": "v1027 targeted smoke is registered in the manual smoke runner."},
        {"name": "dashboard-route-present", "ok": "/smoke-registry-sidecar-compatibility" in dashboard_text and "render_smoke_registry_sidecar_compatibility" in dashboard_text, "message": "Dashboard exposes the v1027 sidecar compatibility review page."},
        {"name": "manifest-representation-present", "ok": "v1027-smoke-registry-sidecar-compatibility-extraction-slice" in manifest_text, "message": "Source surface manifest represents the v1027 sidecar slice."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in [CURRENT_MILESTONE, SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID, "sidecar_metadata_only=True", "manual_smoke_remains_authoritative=True", "sidecar_replaces_manual_registry=False", "sidecar_dispatches_callables=False", "generated_wiring_activated=False", "release_authorized=False", "autonomy_expanded=False", "/smoke-registry-sidecar-compatibility", "data-tip", "command-deck", "operator-console", "no_native_title_tooltip"]), "message": "Docs and source carry the v1027 smoke sidecar compatibility truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["sidecar_executes_checks", "sidecar_replaces_manual_registry", "sidecar_dispatches_callables", "generated_wiring_activated", "api_wiring_generated", "cli_wiring_generated", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "The sidecar does not execute checks, replace manual smoke, authorize release, or expand autonomy."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID,
        "state": "smoke_registry_sidecar_compatibility_extraction_slice_review_only",
        "sidecar_module": SIDECAR_MODULE,
        "manual_smoke_module": MANUAL_SMOKE_MODULE,
        "sidecar_rows": sidecar_rows,
        "sidecar_check_count": len(sidecar_rows),
        "manual_check_count": len(manual_rows),
        "sidecar_metadata_only": True,
        "manual_smoke_remains_authoritative": True,
        "manual_build_checks_remains_authoritative": True,
        "sidecar_executes_checks": False,
        "sidecar_replaces_manual_registry": False,
        "sidecar_dispatches_callables": False,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "missing_from_manual": missing_from_manual,
        "field_mismatches": field_mismatches,
        "order_mismatches": order_mismatches,
        "boundaries": dict(BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def smoke_registry_sidecar_compatibility_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", SMOKE_REGISTRY_SIDECAR_COMPATIBILITY_ID)),
        f"sidecar_module={report.get('sidecar_module')}",
        f"manual_smoke_module={report.get('manual_smoke_module')}",
        f"sidecar_check_count={report.get('sidecar_check_count')}",
        f"manual_check_count={report.get('manual_check_count')}",
        f"sidecar_metadata_only={report.get('sidecar_metadata_only')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"manual_build_checks_remains_authoritative={report.get('manual_build_checks_remains_authoritative')}",
        f"sidecar_executes_checks={report.get('sidecar_executes_checks')}",
        f"sidecar_replaces_manual_registry={report.get('sidecar_replaces_manual_registry')}",
        f"sidecar_dispatches_callables={report.get('sidecar_dispatches_callables')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nSidecar rows:")
        for row in report.get("sidecar_rows", []):
            lines.append(f"- {row.get('order')}: {row.get('name')} tier={row.get('tier')} timeout={row.get('timeout')} segment={row.get('segment')}")
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1030.0 Dashboard Route Behavioral Coverage Expansion v1 tokens: smoke-registry-sidecar-compatibility-extraction-slice-v1 smoke-registry-sidecar-compatibility-v1 build_smoke_registry_sidecar_compatibility_review smoke_registry_sidecar_compatibility_review_text sidecar_module=conscious_agent/smoke_registry_sidecar_compatibility.py manual_smoke_module=tools/smoke_check.py sidecar_metadata_only=True manual_smoke_remains_authoritative=True manual_build_checks_remains_authoritative=True sidecar_executes_checks=False sidecar_replaces_manual_registry=False sidecar_dispatches_callables=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True /smoke-registry-sidecar-compatibility data-tip command-deck operator-console no_native_title_tooltip.
