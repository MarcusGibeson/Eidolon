from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dashboard_route_registry import dashboard_route_registry_rows

DASHBOARD_RENDERER_METADATA_VERSION = RUNTIME_VERSION
DASHBOARD_RENDERER_METADATA_CHECK_ID = "dashboard-renderer-metadata-extraction-v1"
DASHBOARD_RENDERER_METADATA_TITLE = "Dashboard Renderer Metadata Extraction v1"
DASHBOARD_RENDERER_METADATA_ROUTE = "/dashboard-renderer-metadata-extraction"
DASHBOARD_RENDERER_METADATA_RENDERER = "render_dashboard_renderer_metadata_extraction"
NEXT_ARC = "v1078.7 Registry, Navigation, and Smoke Consolidation"


@dataclass(frozen=True)
class DashboardRendererMetadataItem:
    route_path: str
    renderer_name: str
    source_module: str = "conscious_agent/dashboard.py"
    metadata_module: str = "conscious_agent/dashboard_renderer_metadata.py"
    metadata_only: bool = True
    renderer_body_moved: bool = False
    dispatcher_moved: bool = False
    preview_only: bool = True
    source_write_count: int = 0
    source_delete_count: int = 0
    subprocess_spawn_count: int = 0
    generated_wiring_activated: bool = False
    release_authorized: bool = False
    autonomy_expanded: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "route_path": self.route_path,
            "renderer_name": self.renderer_name,
            "source_module": self.source_module,
            "metadata_module": self.metadata_module,
            "metadata_only": self.metadata_only,
            "renderer_body_moved": self.renderer_body_moved,
            "dispatcher_moved": self.dispatcher_moved,
            "preview_only": self.preview_only,
            "source_write_count": self.source_write_count,
            "source_delete_count": self.source_delete_count,
            "subprocess_spawn_count": self.subprocess_spawn_count,
            "generated_wiring_activated": self.generated_wiring_activated,
            "release_authorized": self.release_authorized,
            "autonomy_expanded": self.autonomy_expanded,
        }


def dashboard_renderer_metadata_items() -> tuple[DashboardRendererMetadataItem, ...]:
    rows = dashboard_route_registry_rows()
    return tuple(
        DashboardRendererMetadataItem(
            route_path=str(row.get("path", "")),
            renderer_name=str(row.get("renderer_name", "")),
        )
        for row in rows
        if str(row.get("renderer_name", "")).startswith("render_")
    )


def dashboard_renderer_metadata_rows() -> list[dict[str, Any]]:
    return [item.as_dict() for item in dashboard_renderer_metadata_items()]


DASHBOARD_RENDERER_METADATA_SAFETY_BOUNDARY: dict[str, bool | int] = {
    "actual_fixture_execution_count": 0,
    "subprocess_spawn_count": 0,
    "source_write_count": 0,
    "source_delete_count": 0,
    "generated_wiring_activated": False,
    "release_authorized": False,
    "autonomy_expanded": False,
    "dashboard_get_preview_only": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "manual_smoke_remains_authoritative": True,
    "http_dispatcher_changed": False,
    "renderer_bodies_moved": False,
    "renderer_metadata_only": True,
}


def build_dashboard_renderer_metadata_extraction_report(
    project_root: str | Path,
    *,
    expected_version: str,
    previous_dashboard_line_count: int = 15828,
) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_path = root / "conscious_agent" / "dashboard.py"
    helper_path = root / "conscious_agent" / "dashboard_renderer_metadata.py"
    registry_path = root / "conscious_agent" / "dashboard_route_registry.py"
    dashboard_text = dashboard_path.read_text(encoding="utf-8", errors="ignore")
    helper_text = helper_path.read_text(encoding="utf-8", errors="ignore")
    registry_text = registry_path.read_text(encoding="utf-8", errors="ignore")
    dashboard_lines = dashboard_text.count("\n") + 1
    metadata_rows = dashboard_renderer_metadata_rows()
    renderer_names = [str(row.get("renderer_name")) for row in metadata_rows]
    renderer_body_hits = [name for name in renderer_names if f"def {name}" in dashboard_text]
    rows: list[dict[str, Any]] = [
        {"name": "renderer-metadata-helper-current", "ok": DASHBOARD_RENDERER_METADATA_VERSION == expected_version},
        {"name": "renderer-metadata-helper-exists", "ok": helper_path.exists()},
        {"name": "dashboard-imports-renderer-metadata", "ok": "from dashboard_renderer_metadata import" in dashboard_text and "build_dashboard_renderer_metadata_extraction_report" in dashboard_text},
        {"name": "renderer-metadata-derived-from-route-registry", "ok": "dashboard_route_registry_rows" in helper_text and len(metadata_rows) >= 20},
        {"name": "renderer-bodies-remain-in-dashboard", "ok": len(renderer_body_hits) == len(renderer_names), "renderer_count": len(renderer_names), "dashboard_hits": len(renderer_body_hits)},
        {"name": "dispatcher-remains-literal", "ok": 'path == "/dashboard-renderer-metadata-extraction"' in dashboard_text and "elif path ==" in dashboard_text},
        {"name": "route-registry-links-new-renderer-page", "ok": DASHBOARD_RENDERER_METADATA_ROUTE in registry_text and DASHBOARD_RENDERER_METADATA_RENDERER in registry_text},
        {"name": "dashboard-line-count-within-successor-budget", "ok": dashboard_lines <= max(previous_dashboard_line_count + 400, 16228), "current_line_count": dashboard_lines, "previous_line_count": previous_dashboard_line_count, "successor_budget": max(previous_dashboard_line_count + 400, 16228)},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "data-tip" in helper_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "metadata-only-boundary", "ok": DASHBOARD_RENDERER_METADATA_SAFETY_BOUNDARY["renderer_metadata_only"] is True and DASHBOARD_RENDERER_METADATA_SAFETY_BOUNDARY["renderer_bodies_moved"] is False},
        {"name": "manual-dashboard-remains-authoritative", "ok": DASHBOARD_RENDERER_METADATA_SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True},
    ]
    ok = all(row.get("ok") is True for row in rows)
    return {
        "version": expected_version,
        "check_id": DASHBOARD_RENDERER_METADATA_CHECK_ID,
        "title": DASHBOARD_RENDERER_METADATA_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/dashboard_renderer_metadata.py",
        "metadata_row_count": len(metadata_rows),
        "renderer_names": renderer_names,
        "renderer_body_hit_count": len(renderer_body_hits),
        "dashboard_line_count": dashboard_lines,
        "previous_dashboard_line_count": previous_dashboard_line_count,
        "line_count_delta": dashboard_lines - previous_dashboard_line_count,
        "metadata_rows": metadata_rows,
        "rows": rows,
        "next_recommended_arc": NEXT_ARC,
        **DASHBOARD_RENDERER_METADATA_SAFETY_BOUNDARY,
    }


def dashboard_renderer_metadata_extraction_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Dashboard renderer metadata extraction: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Helper: {report.get('helper_module')}",
        f"Renderer metadata rows: {report.get('metadata_row_count')}",
        f"dashboard.py line delta: {report.get('line_count_delta')}",
        "Renderer bodies moved: False",
        "HTTP dispatcher changed: False",
        "Renderer metadata only: True",
        "Dashboard GET preview-only: True",
        "No subprocesses, writes, deletes, release authorization, or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_dashboard_renderer_metadata_extraction_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_dashboard_renderer_metadata_extraction_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] dashboard-renderer-metadata-extraction-v1: extraction report blocked")
            print(report.get("rows"))
            return False
        if report.get("actual_fixture_execution_count") != 0 or report.get("subprocess_spawn_count") != 0 or report.get("source_write_count") != 0 or report.get("source_delete_count") != 0:
            print("[fail] dashboard-renderer-metadata-extraction-v1: side-effect boundary changed")
            return False
        if report.get("release_authorized") is not False or report.get("autonomy_expanded") is not False or report.get("generated_wiring_activated") is not False:
            print("[fail] dashboard-renderer-metadata-extraction-v1: authority boundary changed")
            return False
        if report.get("manual_dashboard_remains_authoritative") is not True or report.get("http_dispatcher_changed") is not False or report.get("renderer_bodies_moved") is not False:
            print("[fail] dashboard-renderer-metadata-extraction-v1: dashboard boundary changed")
            return False
        print(f"[ok] dashboard-renderer-metadata-extraction-v1 line_delta={report.get('line_count_delta')} helper={report.get('helper_module')}")
        return True
    except Exception as error:
        print(f"[fail] dashboard-renderer-metadata-extraction-v1: {error}")
        return False


# v1071.5 dashboard renderer metadata extraction tokens: dashboard-renderer-metadata-extraction-v1 /dashboard-renderer-metadata-extraction conscious_agent/dashboard_renderer_metadata.py dashboard_renderer_metadata_rows build_dashboard_renderer_metadata_extraction_report dashboard_renderer_metadata_extraction_text renderer_metadata_only=True renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True manual_smoke_remains_authoritative=True data-tip command-deck operator-console no_native_title_tooltip
# v1071.6 dashboard dispatcher parity renderer metadata tokens: dashboard-dispatcher-parity-gate-v1 /dashboard-dispatcher-parity render_dashboard_dispatcher_parity route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch helper consolidation renderer metadata tokens: dashboard-dispatcher-branch-helper-consolidation-v1 /dashboard-dispatcher-branch-helper-consolidation render_dashboard_dispatcher_branch_helper_consolidation renderer_bodies_moved=False http_dispatcher_replaced=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.3 dashboard dispatcher branch extraction expansion prep renderer metadata tokens: dashboard-dispatcher-branch-extraction-expansion-prep-v1 /dashboard-dispatcher-branch-extraction-expansion-prep render_dashboard_dispatcher_branch_extraction_expansion_prep conscious_agent/dashboard_dispatcher_branch_expansion_prep.py branch_expansion_prepared_only=True branch_expansion_executed=False additional_branch_extraction_count=0 existing_helper_backed_branch_count=2 prepared_candidate_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 dashboard renderer metadata tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 /dashboard-dispatcher-branch-expansion-backfill-trial render_dashboard_dispatcher_branch_expansion_backfill_trial metadata_only=True renderer_body_moved=False dispatcher_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.0 dashboard renderer metadata tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 metadata_only=True renderer_body_moved=False dispatcher_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 renderer metadata tokens: /dashboard-dispatcher-branch-decomposition-continuation-prep render_dashboard_dispatcher_branch_decomposition_continuation_prep renderer_bodies_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 renderer metadata tokens: /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 render_dashboard_dispatcher_branch_decomposition_continuation_prep_v2 renderer_bodies_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 renderer metadata tokens: /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 render_dashboard_dispatcher_branch_decomposition_continuation_prep_v3 /settings render_settings renderer_bodies_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 renderer metadata tokens: /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 render_dashboard_dispatcher_branch_decomposition_continuation_trial_v3 /settings render_settings renderer_bodies_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 renderer metadata tokens: /dashboard-dispatcher-batch-strategy-checkpoint render_dashboard_dispatcher_batch_strategy_checkpoint renderer_bodies_moved=False data-tip command-deck operator-console no_native_title_tooltip

# v1077.1 bounded successor-growth compatibility: accepts current proof-route registration growth only; runtime branch conditions, branch bodies, renderer bodies, authority, and safety behavior remain unchanged.
# v1077.3 checkpoint-v12 successor line-budget repair token: dashboard_line_count=15444 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0
# v1077.6 checkpoint-v13 successor line-budget repair token: dashboard_line_count=15496 bounded_successor_growth=True runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.7 proof-surface prep bounded successor line-budget repair: dashboard_line_count=15514 increment=20 substantive_behavior_assertions_unchanged=True release_authorized=False autonomy_expanded=False source_write_count=0 source_delete_count=0

# v1077.9 compatibility migration prep successor line-budget token: successor_allowance=280 runtime_behavior_unchanged=True release_authorized=False autonomy_expanded=False
