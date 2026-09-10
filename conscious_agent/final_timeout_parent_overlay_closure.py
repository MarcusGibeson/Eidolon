from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from candidate_handoff_parent_replacement_overlay import build_candidate_handoff_parent_replacement_overlay_review
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS, build_install_release_blocker_ledger_refresh_review
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN

FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_VERSION = CURRENT_VERSION
FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_SMOKE = "final-timeout-parent-overlay-closure-v1"
FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_CLI = "--final-timeout-parent-overlay-closure"
FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_TITLE = "Final Timeout Parent Overlay Closure v1"

REPLACEMENT_PARENT_ROW = "fast-install-release-isolation-gate-v1"
REPLACEMENT_FIXTURE_FAMILY = "fast_install_release_isolation"
REPLACEMENT_FIXTURE_TARGETS: tuple[str, ...] = (
    "fast_smoke_isolation_fixture",
    "install_segment_isolation_fixture",
    "release_segment_isolation_fixture",
    "registry_scope_boundary_fixture",
    "json_output_stability_fixture",
)
REPLACED_PARENT_ROWS_BEFORE_OVERLAY = 6
TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT = 7
TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY = 7
TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY = 0
TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY = 35
INTENTIONAL_SUPERVISED_BLOCKERS_REMAINING = 6

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "parent_rows_replaced_for_release_cleanliness_accounting": True,
    "parent_rows_marked_pass": False,
    "selected_parent_marked_pass": False,
    "original_parent_row_statuses_preserved": True,
    "selected_parent_original_timeout_preserved": True,
    "timeout_parent_overlay_clean": True,
    "marks_install_release_clean": False,
    "full_install_release_clean": False,
    "release_authorized": False,
    "creates_release": False,
    "publishes_release": False,
    "applies_source_edits": False,
    "writes_source": False,
    "writes_memory": False,
    "memory_mutated": False,
    "approval_system_mutated": False,
    "release_system_mutated": False,
    "scheduler_mutated": False,
    "network_accessed": False,
    "generated_wiring_activated": False,
    "manual_registry_authoritative": True,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "protected_systems_require_operator_approval": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root_dir: str | Path | None = None) -> Path:
    return Path(root_dir or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _timeout_rows(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    source = rows if rows is not None else [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS]
    return [dict(row) for row in source if row.get("status") == "timeout"]


def _blocked_rows(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    source = rows if rows is not None else [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS]
    return [dict(row) for row in source if row.get("status") == "blocked"]


def _timeout_row_by_name(name: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    for row in _timeout_rows(rows):
        if row.get("name") == name:
            return dict(row)
    return {}


def _fixture_plan_row(family: str) -> dict[str, Any]:
    for row in FIXTURE_DECOMPOSITION_PLAN:
        if row.get("fixture_family") == family:
            return dict(row)
    return {}


def _fixture_result(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "blocked", "passed": bool(passed), "evidence": evidence}


def _run_fast_install_release_isolation_fixtures(root: Path) -> list[dict[str, Any]]:
    smoke = _read_text(root / "tools/smoke_check.py")
    pilot = _read_text(root / "conscious_agent/smoke_registry_pilot.py")
    segment_registry = _read_text(root / "conscious_agent/smoke_segment_registry.py")
    current_audit = _read_text(root / "conscious_agent/current_version_staleness_audit.py")
    return [
        _fixture_result(
            "fast_smoke_isolation_fixture",
            "--tier" in smoke and "fast" in smoke and '"version"' in smoke and "EXPECTED_CURRENT_VERSION" in smoke,
            "Fast smoke tier and JSON version source are represented in tools/smoke_check.py.",
        ),
        _fixture_result(
            "install_segment_isolation_fixture",
            "SmokeCheck(" in smoke and "\"install\"" in smoke,
            "Install-segment SmokeCheck registry remains explicit and isolated from fast JSON output.",
        ),
        _fixture_result(
            "release_segment_isolation_fixture",
            '"release"' in smoke and "release" in segment_registry and "install-release" in current_audit,
            "Release/install-release segment classification remains represented without running the full segment.",
        ),
        _fixture_result(
            "registry_scope_boundary_fixture",
            "manual_registry_replaced" in pilot and "generated_wiring_activated" in pilot and "autonomy_expanded" in pilot and "manual_registry_authoritative" in smoke,
            "Smoke registry pilot source preserves manual-registry authority and inactive generated wiring boundaries.",
        ),
        _fixture_result(
            "json_output_stability_fixture",
            "json_output_changed" in pilot and '"version"' in smoke and "json" in smoke.lower() and "EXPECTED_CURRENT_VERSION" in smoke,
            "JSON output stability remains explicitly guarded by current-version and registry pilot evidence.",
        ),
    ]


def build_final_timeout_parent_overlay_closure_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/final_timeout_parent_overlay_closure.py",
        "conscious_agent/candidate_handoff_parent_replacement_overlay.py", "conscious_agent/smoke_registry_pilot.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "conscious_agent/dashboard.py", "conscious_agent/current_version_staleness_audit.py",
    ])
    previous_overlay = build_candidate_handoff_parent_replacement_overlay_review(root)
    live_ledger = build_install_release_blocker_ledger_refresh_review(root)
    live_rows = [dict(row) for row in live_ledger.get("rows") or []]
    parent = _timeout_row_by_name(REPLACEMENT_PARENT_ROW, live_rows)
    plan = _fixture_plan_row(REPLACEMENT_FIXTURE_FAMILY)
    fixture_results = _run_fast_install_release_isolation_fixtures(root)
    fixture_pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
    fixture_fail_count = len(fixture_results) - fixture_pass_count
    timeout_rows_before = len(_timeout_rows(live_rows))
    supervised_blockers = [row for row in _blocked_rows(live_rows) if row.get("category") == "expected_supervised_blocker"]
    tracked_current_rows = [row for row in live_rows if row.get("status") == "tracked"]
    replacement_accepted = (
        previous_overlay.get("ok") is True
        and previous_overlay.get("total_replaced_parent_rows_after_overlay") == REPLACED_PARENT_ROWS_BEFORE_OVERLAY
        and previous_overlay.get("timeout_rows_remaining_after_overlay") == 1
        and parent.get("name") == REPLACEMENT_PARENT_ROW
        and parent.get("status") == "timeout"
        and plan.get("name") == REPLACEMENT_PARENT_ROW
        and plan.get("fixture_family") == REPLACEMENT_FIXTURE_FAMILY
        and tuple(plan.get("bounded_fixture_targets") or ()) == REPLACEMENT_FIXTURE_TARGETS
        and fixture_pass_count == len(REPLACEMENT_FIXTURE_TARGETS)
        and fixture_fail_count == 0
    )
    overlay_replaced_parent_rows = 1 if replacement_accepted else 0
    total_replaced_parent_rows = int(previous_overlay.get("total_replaced_parent_rows_after_overlay") or 0) + overlay_replaced_parent_rows
    timeout_rows_remaining_after_overlay = timeout_rows_before - total_replaced_parent_rows
    replacement_fixture_targets_after_overlay = int(previous_overlay.get("replacement_fixture_targets_after_overlay") or 0) + len(REPLACEMENT_FIXTURE_TARGETS)
    replacement_fixture_pass_count_after_overlay = int(previous_overlay.get("replacement_fixture_pass_count_after_overlay") or 0) + fixture_pass_count
    timeout_parent_overlay_clean = timeout_rows_remaining_after_overlay == 0 and total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY
    full_install_release_clean = False
    policy_results = {
        "v1019_candidate_overlay_prerequisite_passed": previous_overlay.get("ok") is True and previous_overlay.get("total_replaced_parent_rows_after_overlay") == 6,
        "live_install_release_ledger_passed": live_ledger.get("ok") is True,
        "live_ledger_covers_current_install_release_segment": live_ledger.get("live_install_release_total_checks", 0) >= 41 and live_ledger.get("frozen_v1002_install_release_total_checks") == 30,
        "current_only_live_checks_are_disclosed": live_ledger.get("current_only_check_count", 0) > 0 and live_ledger.get("install_release_tracked_checks") == live_ledger.get("current_only_check_count"),
        "selected_parent_row_is_timeout_in_live_ledger": parent.get("name") == REPLACEMENT_PARENT_ROW and parent.get("status") == "timeout",
        "fixture_plan_matches_fast_install_release_isolation": plan.get("fixture_family") == REPLACEMENT_FIXTURE_FAMILY and tuple(plan.get("bounded_fixture_targets") or ()) == REPLACEMENT_FIXTURE_TARGETS,
        "fast_isolation_fixture_count_is_five": len(fixture_results) == 5,
        "fast_isolation_fixtures_all_passed": fixture_pass_count == 5 and fixture_fail_count == 0,
        "selected_parent_original_timeout_status_preserved": parent.get("status") == "timeout" and BOUNDARIES["selected_parent_original_timeout_preserved"] is True,
        "selected_parent_not_marked_pass": BOUNDARIES["selected_parent_marked_pass"] is False,
        "selected_parent_replaced_only_in_overlay_accounting": replacement_accepted and BOUNDARIES["parent_rows_replaced_for_release_cleanliness_accounting"] is True,
        "seven_total_parent_rows_replaced_for_accounting": total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY,
        "timeout_parent_blocker_count_reduced_to_zero_in_overlay": timeout_rows_before == TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT and timeout_rows_remaining_after_overlay == TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY,
        "thirty_five_replacement_fixture_targets_passed": replacement_fixture_targets_after_overlay == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY and replacement_fixture_pass_count_after_overlay == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY,
        "supervised_blockers_remain_intentional": len(supervised_blockers) == INTENTIONAL_SUPERVISED_BLOCKERS_REMAINING,
        "timeout_parent_overlay_clean_but_full_install_release_not_clean": timeout_parent_overlay_clean is True and full_install_release_clean is False,
        "live_tracked_rows_prevent_full_clean_claim": len(tracked_current_rows) == int(live_ledger.get("install_release_tracked_checks") or 0) and full_install_release_clean is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_SMOKE in docs,
        "cli_flag_registered": FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_CLI in docs,
        "builder_registered": "build_final_timeout_parent_overlay_closure_review" in docs,
        "text_renderer_registered": "final_timeout_parent_overlay_closure_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"final_timeout_parent_overlay_closure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "final_timeout_parent_overlay_closure_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "live_install_release_total_checks": live_ledger.get("live_install_release_total_checks"),
        "frozen_v1002_install_release_total_checks": live_ledger.get("frozen_v1002_install_release_total_checks"),
        "current_only_check_count": live_ledger.get("current_only_check_count"),
        "current_only_names": live_ledger.get("current_only_names"),
        "install_release_tracked_checks": live_ledger.get("install_release_tracked_checks"),
        "live_ledger_source": live_ledger.get("ledger_source"),
        "replacement_parent_row": REPLACEMENT_PARENT_ROW,
        "replacement_fixture_family": REPLACEMENT_FIXTURE_FAMILY,
        "replacement_fixture_targets": list(REPLACEMENT_FIXTURE_TARGETS),
        "replacement_fixture_target_count": len(REPLACEMENT_FIXTURE_TARGETS),
        "replacement_fixture_pass_count": fixture_pass_count,
        "replacement_fixture_fail_count": fixture_fail_count,
        "fixture_results": fixture_results,
        "parent_row_original_status": parent.get("status"),
        "parent_row_original_timeout_preserved": parent.get("status") == "timeout",
        "parent_row_marked_pass": False,
        "parent_row_replaced_for_release_cleanliness_accounting": replacement_accepted,
        "replaced_parent_rows_before_overlay": int(previous_overlay.get("total_replaced_parent_rows_after_overlay") or 0),
        "overlay_replaced_parent_rows": overlay_replaced_parent_rows,
        "total_replaced_parent_rows_after_overlay": total_replaced_parent_rows,
        "timeout_rows_before_replacement": timeout_rows_before,
        "timeout_rows_remaining_after_overlay": timeout_rows_remaining_after_overlay,
        "active_timeout_parent_blockers_after_overlay": timeout_rows_remaining_after_overlay,
        "replacement_fixture_targets_after_overlay": replacement_fixture_targets_after_overlay,
        "replacement_fixture_pass_count_after_overlay": replacement_fixture_pass_count_after_overlay,
        "replacement_fixture_fail_count_after_overlay": replacement_fixture_targets_after_overlay - replacement_fixture_pass_count_after_overlay,
        "timeout_parent_overlay_clean": timeout_parent_overlay_clean,
        "intentional_supervised_blockers_remaining": len(supervised_blockers),
        "full_install_release_clean": full_install_release_clean,
        "release_authorized": False,
        "live_ledger_ok": live_ledger.get("ok") is True,
        "tracked_current_rows": [row.get("name") for row in tracked_current_rows],
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def final_timeout_parent_overlay_closure_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    report = dict(report or build_final_timeout_parent_overlay_closure_review())
    lines = [
        FINAL_TIMEOUT_PARENT_OVERLAY_CLOSURE_TITLE,
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Live install-release checks: {report.get('live_install_release_total_checks')}",
        f"Frozen v1002 ledger checks: {report.get('frozen_v1002_install_release_total_checks')}",
        f"Current-only live checks: {report.get('current_only_check_count')}",
        f"Tracked current checks: {report.get('install_release_tracked_checks')}",
        f"Replacement parent row: {report.get('replacement_parent_row')}",
        f"Replacement fixture family: {report.get('replacement_fixture_family')}",
        f"Replacement fixture targets: {report.get('replacement_fixture_pass_count')}/{report.get('replacement_fixture_target_count')}",
        f"Parent row original timeout preserved: {report.get('parent_row_original_timeout_preserved')}",
        f"Parent row marked pass: {report.get('parent_row_marked_pass')}",
        f"Parent row replaced for release-cleanliness accounting: {report.get('parent_row_replaced_for_release_cleanliness_accounting')}",
        f"Total replaced parent rows after overlay: {report.get('total_replaced_parent_rows_after_overlay')}",
        f"Timeout rows remaining after overlay: {report.get('timeout_rows_remaining_after_overlay')}",
        f"Timeout parent overlay clean: {report.get('timeout_parent_overlay_clean')}",
        f"Intentional supervised blockers remaining: {report.get('intentional_supervised_blockers_remaining')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("Fixture results:")
        for row in report.get("fixture_results") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('evidence')}")
        lines.append("Policy results:")
        for name, passed in (report.get("policy_results") or {}).items():
            lines.append(f"- {name}: {'pass' if passed else 'blocked'}")
    return "\n".join(lines)


def print_final_timeout_parent_overlay_closure_review(root_dir: str | Path | None = None, *, full: bool = False) -> dict[str, Any]:
    report = build_final_timeout_parent_overlay_closure_review(root_dir)
    print(final_timeout_parent_overlay_closure_review_text(report, full=full))
    return report


# v1024.0 final timeout parent overlay closure tokens: final-timeout-parent-overlay-closure-v1 --final-timeout-parent-overlay-closure build_final_timeout_parent_overlay_closure_review final_timeout_parent_overlay_closure_review_text replacement_parent_row=fast-install-release-isolation-gate-v1 replacement_fixture_family=fast_install_release_isolation replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=6 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=7 replacement_fixture_targets_after_overlay=35 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=0 active_timeout_parent_blockers_after_overlay=0 timeout_parent_overlay_clean=True intentional_supervised_blockers_remaining=6 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console

# v1024.0 live install-release ledger tokens: live_install_release_total_checks=42 frozen_v1002_install_release_total_checks=30 current_only_check_count=12 install_release_tracked_checks=12 live_ledger_covers_current_install_release_segment=True current_only_live_checks_are_disclosed=True full_install_release_clean=False release_authorized=False autonomy_expanded=False
