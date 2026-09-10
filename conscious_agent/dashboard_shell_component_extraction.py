from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC
from dashboard_shell_components import (
    DASHBOARD_SHELL_COMPONENTS_ID,
    DASHBOARD_SHELL_COMPONENTS_VERSION,
    build_dashboard_shell_component_contract_review,
    render_card_component,
    render_text_block_component,
    safe_html,
)

DASHBOARD_SHELL_COMPONENT_EXTRACTION_VERSION = CURRENT_VERSION
DASHBOARD_SHELL_COMPONENT_EXTRACTION_ID = "dashboard-shell-component-extraction-compatibility-slice-v1"
COMPONENT_MODULE = "conscious_agent/dashboard_shell_components.py"
SOURCE_MODULE = "conscious_agent/dashboard.py"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "compatibility_slice_applied": True,
    "manual_dashboard_remains_authoritative": True,
    "dashboard_routes_preserved": True,
    "generated_wiring_activated": False,
    "api_wiring_generated": False,
    "cli_wiring_generated": False,
    "smoke_registry_replaced": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "operator_approval_still_required": True,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1]).resolve()


def _read_text(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _function_body_source(source: str, name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1: getattr(node, "end_lineno", node.lineno)])
    return ""


def build_dashboard_shell_component_extraction_review(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _repo(root)
    dashboard_text = _read_text(project_root, SOURCE_MODULE)
    component_text = _read_text(project_root, COMPONENT_MODULE)
    smoke_text = _read_text(project_root, "tools/smoke_check.py")
    manifest_text = _read_text(project_root, "conscious_agent/source_surface_manifest.py")
    readme_next = _read_text(project_root, "README_NEXT_STEPS.md")
    readme_history = _read_text(project_root, "README_RELEASE_HISTORY.md")
    docs = "\n".join([dashboard_text, component_text, smoke_text, manifest_text, readme_next, readme_history])
    card_body = _function_body_source(dashboard_text, "_card")
    text_block_body = _function_body_source(dashboard_text, "_text_block")
    component_contract = build_dashboard_shell_component_contract_review(str(project_root))
    sample_card = render_card_component("Sample", "<p>Body</p>")
    sample_text = render_text_block_component("<unsafe>")
    rows = [
        {"name": "module-version-current", "ok": DASHBOARD_SHELL_COMPONENT_EXTRACTION_VERSION == CURRENT_VERSION and DASHBOARD_SHELL_COMPONENTS_VERSION == CURRENT_VERSION, "message": f"module={DASHBOARD_SHELL_COMPONENT_EXTRACTION_VERSION}; components={DASHBOARD_SHELL_COMPONENTS_VERSION}; current={CURRENT_VERSION}"},
        {"name": "component-module-present", "ok": bool(component_text) and "def render_card_component" in component_text and "def render_text_block_component" in component_text, "message": "Dashboard shell component module exposes extracted card/text helpers."},
        {"name": "dashboard-imports-component-module", "ok": "from dashboard_shell_components import" in dashboard_text and "render_card_component" in dashboard_text and "render_text_block_component" in dashboard_text, "message": "dashboard.py imports the extracted shell components."},
        {"name": "legacy-card-wrapper-delegates", "ok": "return render_card_component(title, body)" in card_body, "message": "Legacy _card wrapper delegates to the extracted card component."},
        {"name": "legacy-text-block-wrapper-delegates", "ok": "return render_text_block_component(text)" in text_block_body, "message": "Legacy _text_block wrapper delegates to the extracted text component."},
        {"name": "component-escape-contract", "ok": "&lt;unsafe&gt;" in sample_text and "<unsafe>" not in sample_text and "<section class='card'><h2>Sample</h2><p>Body</p></section>" == sample_card, "message": "Extracted helpers preserve escaping and card shell output."},
        {"name": "dashboard-route-present", "ok": "/dashboard-shell-component-extraction" in dashboard_text and "render_dashboard_shell_component_extraction" in dashboard_text, "message": "Dashboard exposes the v1026 component extraction review page."},
        {"name": "manifest-representation-present", "ok": "v1026-dashboard-shell-component-extraction-compatibility-slice" in manifest_text, "message": "Source surface manifest represents the v1026 compatibility slice."},
        {"name": "component-contract-pass", "ok": component_contract.get("ok") is True, "message": "Extracted component contract review passes."},
        {"name": "docs-current-tokens", "ok": all(token in docs for token in [CURRENT_MILESTONE, DASHBOARD_SHELL_COMPONENT_EXTRACTION_ID, DASHBOARD_SHELL_COMPONENTS_ID, "component_module=conscious_agent/dashboard_shell_components.py", "legacy_card_wrapper_delegates=True", "manual_dashboard_remains_authoritative=True", "generated_wiring_activated=False", "release_authorized=False", "autonomy_expanded=False", "/dashboard-shell-component-extraction", "data-tip", "command-deck", "operator-console", "no_native_title_tooltip"]), "message": "Docs and source carry the v1026 dashboard shell extraction truth tokens."},
        {"name": "no-authority-expansion", "ok": all(BOUNDARIES[key] is False for key in ["generated_wiring_activated", "api_wiring_generated", "cli_wiring_generated", "smoke_registry_replaced", "release_authorized", "autonomy_expanded", "expands_autonomy"]), "message": "The slice does not activate generated wiring, authorize release, replace smoke, or expand autonomy."},
    ]
    ok = all(bool(row.get("ok")) for row in rows)
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SHELL_COMPONENT_EXTRACTION_ID,
        "state": "dashboard_shell_component_extraction_compatibility_slice_review_only",
        "component_module": COMPONENT_MODULE,
        "source_module": SOURCE_MODULE,
        "extracted_helpers": ["safe_html", "render_text_block_component", "render_card_component"],
        "compatibility_slice_applied": True,
        "legacy_card_wrapper_delegates": "return render_card_component(title, body)" in card_body,
        "legacy_text_block_wrapper_delegates": "return render_text_block_component(text)" in text_block_body,
        "manual_dashboard_remains_authoritative": True,
        "dashboard_routes_preserved": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "component_contract_review": component_contract,
        "boundaries": dict(BOUNDARIES),
        "rows": rows,
        "blocked": [row for row in rows if not row.get("ok")],
        "ok": ok,
        "status": "pass" if ok else "blocked",
    }


def dashboard_shell_component_extraction_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", DASHBOARD_SHELL_COMPONENT_EXTRACTION_ID)),
        f"component_module={report.get('component_module')}",
        f"source_module={report.get('source_module')}",
        f"extracted_helpers={','.join(report.get('extracted_helpers') or [])}",
        f"compatibility_slice_applied={report.get('compatibility_slice_applied')}",
        f"legacy_card_wrapper_delegates={report.get('legacy_card_wrapper_delegates')}",
        f"legacy_text_block_wrapper_delegates={report.get('legacy_text_block_wrapper_delegates')}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"dashboard_routes_preserved={report.get('dashboard_routes_preserved')}",
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


# v1026.0 Dashboard Shell Component Extraction Compatibility Slice v1 tokens: dashboard-shell-component-extraction-compatibility-slice-v1 dashboard-shell-component-extraction-v1 build_dashboard_shell_component_extraction_review dashboard_shell_component_extraction_review_text build_dashboard_shell_component_contract_review dashboard_shell_component_contract_review_text component_module=conscious_agent/dashboard_shell_components.py source_module=conscious_agent/dashboard.py extracted_helpers=safe_html,render_text_block_component,render_card_component compatibility_slice_applied=True legacy_card_wrapper_delegates=True legacy_text_block_wrapper_delegates=True manual_dashboard_remains_authoritative=True dashboard_routes_preserved=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True /dashboard-shell-component-extraction data-tip command-deck operator-console no_native_title_tooltip.
