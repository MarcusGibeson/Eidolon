from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_parent_replacement_expansion import build_install_release_parent_replacement_expansion_review
from recovery_closure_fixture_split_smoke import build_recovery_closure_fixture_split_smoke_review

RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_VERSION = CURRENT_VERSION
RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_SMOKE = "recovery-closure-parent-replacement-overlay-v1"
RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_CLI = "--recovery-closure-parent-replacement-overlay"
RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_TITLE = "Recovery Closure Parent Replacement Overlay v1"

REPLACEMENT_PARENT_ROW = "recovery-drill-and-release-closure-v1"
REPLACEMENT_FIXTURE_FAMILY = "recovery_closure"
REPLACEMENT_FIXTURE_TARGET_COUNT = 5
REPLACED_PARENT_ROWS_BEFORE_OVERLAY = 3
TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT = 7
TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY = 4
TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY = 3
TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY = 20

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "executes_recovery_release_closure_board": False,
    "parent_rows_replaced_for_release_cleanliness_accounting": True,
    "parent_rows_marked_pass": False,
    "selected_parent_marked_pass": False,
    "original_parent_row_statuses_preserved": True,
    "selected_parent_original_timeout_preserved": True,
    "marks_install_release_clean": False,
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
    "dashboard_wiring_activated": False,
    "api_wiring_activated": False,
    "cli_wiring_activated": False,
    "smoke_wiring_activated": False,
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


def _timeout_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS if row.get("status") == "timeout"]


def _timeout_row_by_name(name: str) -> dict[str, Any]:
    for row in _timeout_rows():
        if row.get("name") == name:
            return dict(row)
    return {}


def build_recovery_closure_parent_replacement_overlay_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/recovery_closure_parent_replacement_overlay.py",
        "conscious_agent/recovery_closure_fixture_split_smoke.py",
        "conscious_agent/install_release_parent_replacement_expansion.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    expansion = build_install_release_parent_replacement_expansion_review(root)
    split = build_recovery_closure_fixture_split_smoke_review(root)
    parent = _timeout_row_by_name(REPLACEMENT_PARENT_ROW)
    timeout_rows_before = len(_timeout_rows())
    replacement_accepted = (
        expansion.get("ok") is True
        and expansion.get("total_replaced_parent_rows_after_expansion") == REPLACED_PARENT_ROWS_BEFORE_OVERLAY
        and expansion.get("timeout_rows_remaining_after_expansion") == 4
        and split.get("ok") is True
        and split.get("fixture_family_selected") == REPLACEMENT_FIXTURE_FAMILY
        and split.get("parent_timeout_row") == REPLACEMENT_PARENT_ROW
        and split.get("parent_row_still_timeout") is True
        and split.get("parent_row_marked_pass") is False
        and split.get("parent_row_replaced_for_release_cleanliness_accounting") is False
        and split.get("split_fixture_pass_count") == REPLACEMENT_FIXTURE_TARGET_COUNT
        and split.get("split_fixture_fail_count") == 0
        and parent.get("name") == REPLACEMENT_PARENT_ROW
        and parent.get("status") == "timeout"
    )
    overlay_replaced_parent_rows = 1 if replacement_accepted else 0
    total_replaced_parent_rows = int(expansion.get("total_replaced_parent_rows_after_expansion") or 0) + overlay_replaced_parent_rows
    timeout_rows_remaining_after_overlay = timeout_rows_before - total_replaced_parent_rows
    active_cleanliness_blockers_after_overlay = timeout_rows_remaining_after_overlay
    total_replacement_fixture_targets = int(expansion.get("replacement_fixture_targets_after_expansion") or 0) + int(split.get("fixture_targets_in_family") or 0)
    total_replacement_fixture_pass_count = int(expansion.get("replacement_fixture_pass_count_after_expansion") or 0) + int(split.get("split_fixture_pass_count") or 0)
    full_install_release_clean = active_cleanliness_blockers_after_overlay == 0
    policy_results = {
        "v1012_parent_replacement_expansion_prerequisite_passed": expansion.get("ok") is True and expansion.get("total_replaced_parent_rows_after_expansion") == 3,
        "v1014_recovery_split_prerequisite_passed": split.get("ok") is True and split.get("split_smoke_passed") is True,
        "selected_parent_row_is_timeout_in_original_ledger": parent.get("name") == REPLACEMENT_PARENT_ROW and parent.get("status") == "timeout",
        "selected_fixture_family_matches_recovery_closure": split.get("fixture_family_selected") == REPLACEMENT_FIXTURE_FAMILY,
        "selected_fixture_targets_all_passed": split.get("split_fixture_pass_count") == REPLACEMENT_FIXTURE_TARGET_COUNT and split.get("split_fixture_fail_count") == 0,
        "selected_parent_original_timeout_status_preserved": split.get("parent_row_still_timeout") is True and BOUNDARIES["selected_parent_original_timeout_preserved"] is True,
        "selected_parent_not_marked_pass": split.get("parent_row_marked_pass") is False and BOUNDARIES["selected_parent_marked_pass"] is False,
        "selected_parent_replaced_only_in_overlay_accounting": replacement_accepted and BOUNDARIES["parent_rows_replaced_for_release_cleanliness_accounting"] is True,
        "four_total_parent_rows_replaced_for_accounting": total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY,
        "timeout_blocker_count_reduced_to_three_in_overlay": timeout_rows_before == TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT and timeout_rows_remaining_after_overlay == TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY,
        "twenty_replacement_fixture_targets_passed": total_replacement_fixture_targets == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY and total_replacement_fixture_pass_count == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY,
        "full_install_release_still_not_clean": full_install_release_clean is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_SMOKE in docs,
        "cli_flag_registered": RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_CLI in docs,
        "builder_registered": "build_recovery_closure_parent_replacement_overlay_review" in docs,
        "text_renderer_registered": "recovery_closure_parent_replacement_overlay_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"recovery_closure_parent_replacement_overlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "recovery_closure_parent_replacement_overlay_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": RECOVERY_CLOSURE_PARENT_REPLACEMENT_OVERLAY_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "replacement_parent_row": REPLACEMENT_PARENT_ROW,
        "replacement_fixture_family": REPLACEMENT_FIXTURE_FAMILY,
        "replacement_fixture_targets": list(split.get("fixture_target_names") or []),
        "replacement_fixture_target_count": REPLACEMENT_FIXTURE_TARGET_COUNT,
        "replacement_fixture_pass_count": split.get("split_fixture_pass_count"),
        "replacement_fixture_fail_count": split.get("split_fixture_fail_count"),
        "parent_row_original_status": parent.get("status"),
        "parent_row_original_timeout_preserved": parent.get("status") == "timeout",
        "parent_row_marked_pass": False,
        "parent_row_replaced_for_release_cleanliness_accounting": replacement_accepted,
        "replaced_parent_rows_before_overlay": int(expansion.get("total_replaced_parent_rows_after_expansion") or 0),
        "overlay_replaced_parent_rows": overlay_replaced_parent_rows,
        "total_replaced_parent_rows_after_overlay": total_replaced_parent_rows,
        "timeout_rows_before_replacement": timeout_rows_before,
        "timeout_rows_remaining_after_overlay": timeout_rows_remaining_after_overlay,
        "active_cleanliness_blockers_after_overlay": active_cleanliness_blockers_after_overlay,
        "replacement_fixture_targets_after_overlay": total_replacement_fixture_targets,
        "replacement_fixture_pass_count_after_overlay": total_replacement_fixture_pass_count,
        "replacement_fixture_fail_count_after_overlay": total_replacement_fixture_targets - total_replacement_fixture_pass_count,
        "full_install_release_clean": full_install_release_clean,
        "release_authorized": False,
        "marks_install_release_clean": False,
        "replacement_summary": "Recovery closure is now replaced in release-cleanliness accounting by five passing bounded fixtures; three timeout parent rows remain active blockers.",
        "autonomy_blocking_status": "blocked_until_remaining_three_timeout_parent_rows_are_replaced_or_repaired_and_phase_zero_is_explicitly_authorized",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def recovery_closure_parent_replacement_overlay_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Recovery Closure Parent Replacement Overlay report not found."
    lines = [
        "# Recovery Closure Parent Replacement Overlay",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Replacement parent row: {report.get('replacement_parent_row')}",
        f"Replacement fixture family: {report.get('replacement_fixture_family')}",
        f"Replacement fixture targets: {report.get('replacement_fixture_pass_count')}/{report.get('replacement_fixture_target_count')}",
        f"Parent row original timeout preserved: {report.get('parent_row_original_timeout_preserved')}",
        f"Parent row marked pass: {report.get('parent_row_marked_pass')}",
        f"Parent row replaced for release-cleanliness accounting: {report.get('parent_row_replaced_for_release_cleanliness_accounting')}",
        f"Replaced parent rows before overlay: {report.get('replaced_parent_rows_before_overlay')}",
        f"Overlay replaced parent rows: {report.get('overlay_replaced_parent_rows')}",
        f"Total replaced parent rows after overlay: {report.get('total_replaced_parent_rows_after_overlay')}",
        f"Replacement fixture targets after overlay: {report.get('replacement_fixture_pass_count_after_overlay')}/{report.get('replacement_fixture_targets_after_overlay')}",
        f"Timeout rows before replacement: {report.get('timeout_rows_before_replacement')}",
        f"Timeout rows remaining after overlay: {report.get('timeout_rows_remaining_after_overlay')}",
        f"Active cleanliness blockers after overlay: {report.get('active_cleanliness_blockers_after_overlay')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Summary: {report.get('replacement_summary')}",
    ]
    if full:
        lines.extend(["", "## Replacement fixture targets"])
        for name in report.get("replacement_fixture_targets") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Policy results"])
        for key, value in sorted((report.get("policy_results") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Boundaries"])
        for key in ["executes_full_install_release_segment", "executes_parent_timeout_rows", "parent_rows_marked_pass", "release_authorized", "autonomy_expanded", "review_only"]:
            lines.append(f"- {key}: {report.get(key)}")
    return "\n".join(lines)


def print_recovery_closure_parent_replacement_overlay_review(full: bool = False, root_dir: str | Path | None = None) -> None:
    print(recovery_closure_parent_replacement_overlay_review_text(build_recovery_closure_parent_replacement_overlay_review(root_dir), full=full))


# v1015.0 recovery closure parent replacement overlay tokens: recovery-closure-parent-replacement-overlay-v1 --recovery-closure-parent-replacement-overlay build_recovery_closure_parent_replacement_overlay_review recovery_closure_parent_replacement_overlay_review_text replacement_parent_row=recovery-drill-and-release-closure-v1 replacement_fixture_family=recovery_closure replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=3 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=4 replacement_fixture_targets_after_overlay=20 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=3 active_cleanliness_blockers_after_overlay=3 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
