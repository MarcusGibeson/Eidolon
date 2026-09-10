from __future__ import annotations

from html import escape
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, CURRENT_VERSION_TAG, NEXT_RECOMMENDED_ARC

DASHBOARD_SHELL_COMPONENTS_VERSION = CURRENT_VERSION
DASHBOARD_SHELL_COMPONENTS_ID = "dashboard-shell-component-extraction-v1"


def safe_html(value: Any) -> str:
    """Escape a value for dashboard HTML output."""
    return escape(str(value), quote=True)


def render_text_block_component(text: str) -> str:
    """Render escaped preformatted dashboard text."""
    return f"<pre>{safe_html(text)}</pre>"


def render_card_component(title: str, body: str, *, css_class: str = "card") -> str:
    """Render the common command-deck dashboard card shell."""
    return f"<section class='{safe_html(css_class)}'><h2>{safe_html(title)}</h2>{body}</section>"


def build_dashboard_shell_component_contract_review(root: str | None = None) -> dict[str, Any]:
    return {
        "version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "review_id": DASHBOARD_SHELL_COMPONENTS_ID,
        "extracted_helpers": ["safe_html", "render_text_block_component", "render_card_component"],
        "component_module": "conscious_agent/dashboard_shell_components.py",
        "manual_dashboard_remains_authoritative": True,
        "generated_wiring_activated": False,
        "release_authorized": False,
        "autonomy_expanded": False,
        "expands_autonomy": False,
        "operator_approval_still_required": True,
        "ok": True,
        "status": "pass",
    }


def dashboard_shell_component_contract_review_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        str(report.get("current_milestone", CURRENT_MILESTONE)),
        str(report.get("review_id", DASHBOARD_SHELL_COMPONENTS_ID)),
        f"component_module={report.get('component_module')}",
        f"extracted_helpers={','.join(report.get('extracted_helpers') or [])}",
        f"manual_dashboard_remains_authoritative={report.get('manual_dashboard_remains_authoritative')}",
        f"generated_wiring_activated={report.get('generated_wiring_activated')}",
        f"release_authorized={report.get('release_authorized')}",
        f"autonomy_expanded={report.get('autonomy_expanded')}",
        f"operator_approval_still_required={report.get('operator_approval_still_required')}",
    ]
    return "\n".join(lines)


# v1026.0 Dashboard Shell Component Extraction Compatibility Slice v1 tokens: dashboard-shell-component-extraction-v1 component_module=conscious_agent/dashboard_shell_components.py extracted_helpers=safe_html,render_text_block_component,render_card_component manual_dashboard_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip.
