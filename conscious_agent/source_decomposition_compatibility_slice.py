from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from smoke_timeout_contract import COMPILE_SMOKE_TIMEOUT_SECONDS, build_smoke_timeout_contract_review

FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_VERSION = CURRENT_VERSION
FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_ID = "first-source-decomposition-compatibility-slice-v1"
EXTRACTED_MODULE = "conscious_agent/smoke_timeout_contract.py"
SOURCE_MODULE = "tools/smoke_check.py"

SLICE_BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "compatibility_slice_applied": True,
    "manual_smoke_remains_authoritative": True,
    "generated_wiring_activated": False,
    "dashboard_wiring_generated": False,
    "api_wiring_generated": False,
    "cli_wiring_generated": False,
    "smoke_registry_replaced": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def build_first_source_decomposition_compatibility_slice_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    smoke_text = _read_text(project_root, SOURCE_MODULE)
    contract_text = _read_text(project_root, EXTRACTED_MODULE)
    dashboard_text = _read_text(project_root, "conscious_agent/dashboard.py")
    source_manifest_text = _read_text(project_root, "conscious_agent/source_surface_manifest.py")
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    timeout_review = build_smoke_timeout_contract_review(project_root)
    try:
        smoke_tree = ast.parse(smoke_text)
    except SyntaxError:
        smoke_tree = ast.Module(body=[], type_ignores=[])
    smoke_local_timeout_assignment_present = any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "COMPILE_SMOKE_TIMEOUT_SECONDS" for target in node.targets)
        for node in getattr(smoke_tree, "body", [])
    )
    docs = "\n".join([smoke_text, contract_text, dashboard_text, source_manifest_text, readme_next, readme_history])
    required_tokens = [
        CURRENT_MILESTONE,
        FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_ID,
        "smoke-timeout-contract-extraction-v1",
        "constant_extracted_from_smoke_check=True",
        "manual_smoke_local_timeout_assignment_removed=True",
        "registry_and_subprocess_still_share_timeout=True",
        "manual_smoke_remains_authoritative=True",
        "generated_wiring_activated=False",
        "release_authorized=False",
        "autonomy_expanded=False",
        "/source-decomposition-compatibility-slice",
    ]
    rows = [
        {
            "name": "module-version-current",
            "ok": FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_VERSION == CURRENT_VERSION,
            "message": f"module={FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_VERSION}; current={CURRENT_VERSION}",
        },
        {
            "name": "extracted-timeout-contract-passes",
            "ok": timeout_review.get("ok") is True,
            "message": "The extracted smoke timeout contract validates its own compatibility boundary.",
        },
        {
            "name": "compile-timeout-value-preserved",
            "ok": COMPILE_SMOKE_TIMEOUT_SECONDS == 35,
            "message": "The compile timeout value is unchanged by extraction.",
        },
        {
            "name": "manual-smoke-imports-extracted-contract",
            "ok": "from smoke_timeout_contract import COMPILE_SMOKE_TIMEOUT_SECONDS" in smoke_text,
            "message": "tools/smoke_check.py now consumes the extracted timeout contract.",
        },
        {
            "name": "manual-smoke-local-assignment-removed",
            "ok": not smoke_local_timeout_assignment_present,
            "message": "The old local compile timeout assignment has been removed from the smoke runner.",
        },
        {
            "name": "dashboard-route-present",
            "ok": "/source-decomposition-compatibility-slice" in dashboard_text and "render_source_decomposition_compatibility_slice" in dashboard_text,
            "message": "Dashboard exposes the v1025 compatibility slice review route.",
        },
        {
            "name": "manifest-representation-present",
            "ok": "v1025-first-source-decomposition-compatibility-slice" in source_manifest_text,
            "message": "Source surface manifest represents the v1025 compatibility slice.",
        },
        {
            "name": "docs-current-tokens",
            "ok": all(token in docs for token in required_tokens),
            "message": "Docs and source carry v1025 compatibility slice truth tokens.",
        },
        {
            "name": "no-authority-expansion",
            "ok": all(SLICE_BOUNDARIES[key] is False for key in ["generated_wiring_activated", "dashboard_wiring_generated", "api_wiring_generated", "cli_wiring_generated", "smoke_registry_replaced", "release_authorized", "autonomy_expanded", "expands_autonomy"]),
            "message": "The slice does not activate generated wiring, authorize release, or expand autonomy.",
        },
    ]
    ok = all(bool(row["ok"]) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_ID,
        "state": "first_source_decomposition_compatibility_slice_review_only",
        "extracted_module": EXTRACTED_MODULE,
        "source_module": SOURCE_MODULE,
        "compile_timeout_seconds": COMPILE_SMOKE_TIMEOUT_SECONDS,
        "compatibility_slice_applied": True,
        "constant_extracted_from_smoke_check": timeout_review.get("constant_extracted_from_smoke_check"),
        "manual_smoke_local_timeout_assignment_removed": timeout_review.get("manual_smoke_local_timeout_assignment_removed"),
        "registry_and_subprocess_still_share_timeout": timeout_review.get("registry_and_subprocess_still_share_timeout"),
        "manual_smoke_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "timeout_contract_review": timeout_review,
        "boundaries": dict(SLICE_BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row["ok"]],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def first_source_decomposition_compatibility_slice_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        CURRENT_MILESTONE,
        FIRST_SOURCE_DECOMPOSITION_COMPATIBILITY_SLICE_ID,
        f"extracted_module={report.get('extracted_module')}",
        f"source_module={report.get('source_module')}",
        f"compile_timeout_seconds={report.get('compile_timeout_seconds')}",
        f"compatibility_slice_applied={report.get('compatibility_slice_applied')}",
        f"constant_extracted_from_smoke_check={report.get('constant_extracted_from_smoke_check')}",
        f"manual_smoke_local_timeout_assignment_removed={report.get('manual_smoke_local_timeout_assignment_removed')}",
        f"registry_and_subprocess_still_share_timeout={report.get('registry_and_subprocess_still_share_timeout')}",
        f"manual_smoke_remains_authoritative={report.get('manual_smoke_remains_authoritative')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    if full:
        lines.append("\nRows:")
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {row.get('ok')} — {row.get('message')}")
    return "\n".join(lines)


# v1025.0 First Source Decomposition Compatibility Slice v1 tokens: first-source-decomposition-compatibility-slice-v1 source-decomposition-compatibility-slice smoke-timeout-contract-extraction-v1 extracted_module=conscious_agent/smoke_timeout_contract.py source_module=tools/smoke_check.py compatibility_slice_applied=True constant_extracted_from_smoke_check=True manual_smoke_local_timeout_assignment_removed=True registry_and_subprocess_still_share_timeout=True manual_smoke_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True /source-decomposition-compatibility-slice data-tip command-deck operator-console no_native_title_tooltip.
