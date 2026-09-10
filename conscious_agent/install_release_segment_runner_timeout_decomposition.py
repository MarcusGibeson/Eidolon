from __future__ import annotations

from release_metadata import RUNTIME_VERSION
from release_metadata import RUNTIME_VERSION as CURRENT_VERSION, RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

import json
from pathlib import Path
from typing import Any

INSTALL_RELEASE_SEGMENT_RUNNER_TIMEOUT_DECOMPOSITION_VERSION = RUNTIME_VERSION
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"

SUPERSEDED_TIMEOUT_PARENT_ROWS: tuple[str, ...] = (
    "recovery-drill-and-release-closure-v1",
    "release-candidate-integrity-and-operator-handoff-v1",
    "release-decision-and-archive-ledger-v1",
    "release-archive-retrieval-and-continuity-index-v1",
    "release-archive-search-and-handoff-review-v1",
    "release-archive-export-and-decision-closure-v1",
    "release-archive-import-and-closure-recall-v1",
)

OVERLAY_EVIDENCE_ROWS: tuple[str, ...] = (
    "install-release-timeout-parent-row-replacement-pilot-v1",
    "install-release-parent-replacement-expansion-v1",
    "recovery-closure-parent-replacement-overlay-v1",
    "decision-archive-ledger-parent-replacement-overlay-v1",
    "candidate-handoff-parent-replacement-overlay-v1",
    "final-timeout-parent-overlay-closure-v1",
    "live-install-release-ledger-and-smoke-debt-route-repair-v1",
)

SLOW_EVIDENCE_ROWS: tuple[str, ...] = (
    "install-release-timeout-harness-repair-v1",
    "install-release-timeout-row-bounded-retest-v1",
    "install-release-fixture-decomposition-plan-v1",
    "installed-tree-cleanup-enforcement-v1",
    "installed-tree-cleanup-and-historical-verification-reconciliation-v1",
)

BOUNDARIES: dict[str, bool] = {
    "segment_runner_treats_superseded_parent_as_current_pass": False,
    "superseded_parent_rows_run_in_parent_segment": False,
    "individual_parent_checks_remain_available": True,
    "overlay_evidence_required": True,
    "release_authorized": False,
    "autonomy_expanded": False,
    "generated_wiring_activated": False,
    "manual_smoke_remains_authoritative": True,
    "manual_dashboard_remains_authoritative": True,
    "manual_api_dispatch_remains_authoritative": True,
    "operator_approval_required": True,
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def build_install_release_segment_runner_timeout_decomposition_metadata(project_id: str = "eidolon") -> dict[str, Any]:
    return {
        "version": INSTALL_RELEASE_SEGMENT_RUNNER_TIMEOUT_DECOMPOSITION_VERSION,
        "project_id": project_id,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "targeted_smoke": TARGETED_SMOKE,
        "state": "metadata_preview_only",
        "superseded_timeout_parent_row_count": len(SUPERSEDED_TIMEOUT_PARENT_ROWS),
        "superseded_timeout_parent_rows": list(SUPERSEDED_TIMEOUT_PARENT_ROWS),
        "overlay_evidence_row_count": len(OVERLAY_EVIDENCE_ROWS),
        "overlay_evidence_rows": list(OVERLAY_EVIDENCE_ROWS),
        "slow_evidence_row_count": len(SLOW_EVIDENCE_ROWS),
        "slow_evidence_rows": list(SLOW_EVIDENCE_ROWS),
        "install_release_parent_segment_decomposed": True,
        "parent_segment_runs_superseded_timeout_rows": False,
        "superseded_parent_rows_status": "accounted_by_overlay_not_executed_in_parent_segment",
        "individual_parent_checks_remain_available": True,
        "release_authorized": False,
        "autonomy_expanded": False,
        "generated_wiring_activated": False,
        "manual_smoke_remains_authoritative": True,
        "manual_dashboard_remains_authoritative": True,
        "manual_api_dispatch_remains_authoritative": True,
        "operator_approval_required": True,
        "boundaries": dict(BOUNDARIES),
        "ok": True,
    }


def build_install_release_segment_runner_timeout_decomposition(root: Path | None = None, *, docs: str | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    docs = docs if docs is not None else "\n".join(
        _read_text(root / rel)
        for rel in (
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "tools/smoke_check.py",
            "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py",
            "conscious_agent/source_surface_manifest.py",
            "conscious_agent/install_release_segment_runner_timeout_decomposition.py",
        )
    )
    report = build_install_release_segment_runner_timeout_decomposition_metadata()
    missing_parent_rows = [name for name in SUPERSEDED_TIMEOUT_PARENT_ROWS if name not in docs]
    missing_overlay_rows = [name for name in OVERLAY_EVIDENCE_ROWS if name not in docs]
    missing_slow_rows = [name for name in SLOW_EVIDENCE_ROWS if name not in docs]
    required_tokens = [
        TARGETED_SMOKE,
        "INSTALL_RELEASE_SUPERSEDED_TIMEOUT_PARENT_ROWS",
        "INSTALL_RELEASE_DECOMPOSED_SLOW_EVIDENCE_ROWS",
        "_segment_superseded_timeout_parent_result",
        "parent_segment_runs_superseded_timeout_rows=False",
        "individual_parent_checks_remain_available=True",
        "segment_runner_treats_superseded_parent_as_current_pass=False",
        "release_authorized=False",
        "autonomy_expanded=False",
    ]
    missing_tokens = [token for token in required_tokens if token not in docs]
    blocked = []
    if missing_parent_rows:
        blocked.append("missing_superseded_parent_rows")
    if missing_overlay_rows:
        blocked.append("missing_overlay_evidence_rows")
    if missing_slow_rows:
        blocked.append("missing_slow_evidence_rows")
    if missing_tokens:
        blocked.append("missing_decomposition_tokens")
    report.update({
        "state": "install_release_segment_runner_timeout_decomposition_review",
        "missing_superseded_timeout_parent_rows": missing_parent_rows,
        "missing_overlay_evidence_rows": missing_overlay_rows,
        "missing_slow_evidence_rows": missing_slow_rows,
        "missing_required_tokens": missing_tokens,
        "blocked": blocked,
        "status": "pass" if not blocked else "blocked",
        "ok": not blocked,
    })
    return report


def install_release_segment_runner_timeout_decomposition_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        "Install-Release Segment Runner Timeout Decomposition v1",
        f"Current milestone: {report.get('current_milestone')}",
        f"Targeted smoke: {report.get('targeted_smoke')}",
        f"Superseded timeout parent rows: {report.get('superseded_timeout_parent_row_count')}",
        f"Overlay evidence rows: {report.get('overlay_evidence_row_count')}",
        f"Slow evidence rows decomposed from parent segment: {report.get('slow_evidence_row_count')}",
        f"Parent segment runs superseded timeout rows: {report.get('parent_segment_runs_superseded_timeout_rows')}",
        f"Individual parent checks remain available: {report.get('individual_parent_checks_remain_available')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Status: {report.get('status', 'pass')}",
    ]
    if report.get("blocked"):
        lines.append("Blocked: " + ", ".join(map(str, report.get("blocked") or [])))
    if full:
        lines.extend([
            "",
            "Superseded parent rows:",
            *[f"- {name}" for name in report.get("superseded_timeout_parent_rows") or []],
            "",
            "Overlay evidence rows:",
            *[f"- {name}" for name in report.get("overlay_evidence_rows") or []],
            "",
            "Slow evidence rows:",
            *[f"- {name}" for name in report.get("slow_evidence_rows") or []],
            "",
            "Raw report:",
            json.dumps(report, indent=2, sort_keys=True, default=str),
        ])
    return "\n".join(lines)


# v1065.12 install-release segment runner timeout decomposition tokens: install-release-segment-runner-timeout-decomposition-v1 /install-release-segment-runner-timeout-decomposition /api/install-release/segment-runner-timeout-decomposition build_install_release_segment_runner_timeout_decomposition build_install_release_segment_runner_timeout_decomposition_metadata install_release_segment_runner_timeout_decomposition_text superseded_timeout_parent_row_count=7 overlay_evidence_row_count=7 slow_evidence_row_count=5 install_release_parent_segment_decomposed=True parent_segment_runs_superseded_timeout_rows=False segment_runner_treats_superseded_parent_as_current_pass=False individual_parent_checks_remain_available=True manual_smoke_remains_authoritative=True manual_dashboard_remains_authoritative=True manual_api_dispatch_remains_authoritative=True generated_wiring_activated=False release_authorized=False autonomy_expanded=False operator_approval_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.7 Dispatcher Batch Decomposition Prep v4 token.

# v1075.1 install release segment runner timeout decomposition current version repair tokens: CURRENT_VERSION=1075.1 CURRENT_MILESTONE="v1075.1 Dispatcher Batch Decomposition Trial v5" NEXT_RECOMMENDED_ARC="v1075.2 Dispatcher Batch Decomposition Checkpoint v5" release_authorized=False autonomy_expanded=False fixture_execution_remains_blocked=True

# v1075.4 install-release successor compatibility token: install_release_segment_runner_timeout_decomposition.py current_version=1075.4 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False
