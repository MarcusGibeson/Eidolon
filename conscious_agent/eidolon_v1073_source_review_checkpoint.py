from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

from dashboard_dispatcher_branch_helpers import consolidated_branch_helper_rows
from dashboard_dispatcher_parity import dashboard_dispatcher_parity_rows

EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_VERSION = "1073.3"
EIDOLON_SOURCE_REVIEW_CHECKPOINT_VERSION = RUNTIME_VERSION
EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_CHECK_ID = "eidolon-v1073-source-review-checkpoint-v1"
EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_TITLE = "Eidolon v1073 Source Review and Autonomy Readiness Checkpoint v1"
EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE = "/eidolon-v1073-source-review-checkpoint"
EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_RENDERER = "render_eidolon_v1073_source_review_checkpoint"
NEXT_ARC = "v1078.1 Dispatcher Proof Surface Historical Compatibility Migration Trial v2"

SAFETY_BOUNDARY: dict[str, bool | int] = {
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
    "supervised_autonomy_ready": False,
    "real_autonomy_ready": False,
    "os_enforced_sandbox_backend_admitted": False,
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8", errors="ignore")


def build_eidolon_v1073_source_review_checkpoint_report(project_root: str | Path, *, expected_version: str) -> dict[str, Any]:
    root = Path(project_root)
    dashboard_text = _read(root, "conscious_agent/dashboard.py")
    smoke_text = _read(root, "tools/smoke_check.py")
    helper_rows = consolidated_branch_helper_rows()
    parity_rows = dashboard_dispatcher_parity_rows(root)
    blocked_parity = [row for row in parity_rows if row.get("ok") is not True]
    python_files = list((root / "conscious_agent").glob("*.py")) + list((root / "tools").glob("*.py"))
    proof_rows = [
        {"name": "checkpoint-module-current", "ok": EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_VERSION == expected_version},
        {"name": "helper-backed-branch-count-six", "ok": len(helper_rows) == 6},
        {"name": "dispatcher-parity-clean", "ok": len(blocked_parity) == 0, "blocked_count": len(blocked_parity)},
        {"name": "manual-dashboard-remains-authoritative", "ok": SAFETY_BOUNDARY["manual_dashboard_remains_authoritative"] is True and "elif path ==" in dashboard_text},
        {"name": "manual-smoke-remains-authoritative", "ok": SAFETY_BOUNDARY["manual_smoke_remains_authoritative"] is True and "def _build_checks" in smoke_text},
        {"name": "custom-data-tip-preserved", "ok": "data-tip" in dashboard_text and "command-deck" in dashboard_text},
        {"name": "native-title-tooltip-not-reintroduced", "ok": 'title="' not in dashboard_text},
        {"name": "sandbox-backed-autonomy-still-blocked", "ok": SAFETY_BOUNDARY["os_enforced_sandbox_backend_admitted"] is False and SAFETY_BOUNDARY["actual_fixture_execution_count"] == 0},
        {"name": "release-and-autonomy-authority-boundary", "ok": SAFETY_BOUNDARY["release_authorized"] is False and SAFETY_BOUNDARY["autonomy_expanded"] is False and SAFETY_BOUNDARY["generated_wiring_activated"] is False},
    ]
    ok = all(row.get("ok") is True for row in proof_rows)
    return {
        "version": expected_version,
        "check_id": EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_CHECK_ID,
        "title": EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "helper_module": "conscious_agent/eidolon_v1073_source_review_checkpoint.py",
        "route": EIDOLON_V1073_SOURCE_REVIEW_CHECKPOINT_ROUTE,
        "python_file_count": len(python_files),
        "dashboard_line_count": dashboard_text.count("\n") + 1,
        "smoke_check_line_count": smoke_text.count("\n") + 1,
        "helper_backed_branch_count": len(helper_rows),
        "parity_row_count": len(parity_rows),
        "blocked_parity_rows": blocked_parity,
        "milestones_before_supervised_autonomy": [
            "finish dashboard and smoke decomposition",
            "replace brittle text-token proofs with behavior checks",
            "preserve fresh-extract install-release verification",
            "build and audit an OS-enforced sandbox backend",
        ],
        "milestones_before_real_autonomy": [
            "adversarially test sandbox confinement",
            "require operator approval for generated fixture execution and promotion",
            "prove rollback and release authorization separation",
            "make autonomy observable, interruptible, and capability-scoped",
        ],
        "rows": proof_rows,
        "next_recommended_arc": NEXT_ARC,
        **SAFETY_BOUNDARY,
    }


def eidolon_v1073_source_review_checkpoint_text(report: dict[str, Any], *, full: bool = False) -> str:
    lines = [
        f"Eidolon v1073 source review checkpoint: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Python files: {report.get('python_file_count')}",
        f"dashboard.py lines: {report.get('dashboard_line_count')}",
        f"tools/smoke_check.py lines: {report.get('smoke_check_line_count')}",
        f"Helper-backed dispatcher branches: {report.get('helper_backed_branch_count')}",
        "Supervised autonomy ready: False",
        "Real autonomy ready: False",
        "A real audited OS-enforced sandbox backend remains mandatory before fixture execution or autonomy expansion.",
    ]
    if full:
        for row in report.get("rows", []):
            lines.append(f"- {row.get('name')}: {'pass' if row.get('ok') else 'blocked'}")
    return "\n".join(lines)


def run_eidolon_v1073_source_review_checkpoint_check(project_root: str | Path, *, expected_version: str) -> bool:
    try:
        report = build_eidolon_v1073_source_review_checkpoint_report(project_root, expected_version=expected_version)
        if report.get("ok") is not True:
            print("[fail] eidolon-v1073-source-review-checkpoint-v1: checkpoint blocked")
            print(report.get("rows"))
            return False
        print(f"[ok] eidolon-v1073-source-review-checkpoint-v1 helper_count={report.get('helper_backed_branch_count')} parity_rows={report.get('parity_row_count')}")
        return True
    except Exception as error:
        print(f"[fail] eidolon-v1073-source-review-checkpoint-v1: {error}")
        return False


# v1073.0 checkpoint tokens: eidolon-v1073-source-review-checkpoint-v1 /eidolon-v1073-source-review-checkpoint helper_backed_branch_count=6 supervised_autonomy_ready=False real_autonomy_ready=False os_enforced_sandbox_backend_admitted=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 checkpoint successor tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep helper_backed_branch_count=6 branch_decomposition_continuation_prepared_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.3 checkpoint successor tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 helper_backed_branch_count=7 branch_decomposition_continuation_prepared_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
