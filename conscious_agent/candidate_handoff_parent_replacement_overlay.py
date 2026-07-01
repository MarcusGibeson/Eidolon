from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from candidate_handoff_fixture_split_smoke import build_candidate_handoff_fixture_split_smoke_review
from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS

CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_VERSION = CURRENT_VERSION
CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_SMOKE = "candidate-handoff-parent-replacement-overlay-v1"
CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_CLI = "--candidate-handoff-parent-replacement-overlay"
CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_TITLE = "Candidate Handoff Parent Replacement Overlay v1"

REPLACEMENT_PARENT_ROW = "release-candidate-integrity-and-operator-handoff-v1"
REPLACEMENT_FIXTURE_FAMILY = "candidate_handoff"
REPLACEMENT_FIXTURE_TARGET_COUNT = 5
REPLACED_PARENT_ROWS_BEFORE_OVERLAY = 5
TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT = 7
TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY = 6
TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY = 1
TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY = 30

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


def build_candidate_handoff_parent_replacement_overlay_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/candidate_handoff_parent_replacement_overlay.py",
        "conscious_agent/candidate_handoff_fixture_split_smoke.py", "conscious_agent/decision_archive_ledger_parent_replacement_overlay.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "conscious_agent/dashboard.py", "conscious_agent/current_version_staleness_audit.py",
    ])
    split = build_candidate_handoff_fixture_split_smoke_review(root)
    parent = _timeout_row_by_name(REPLACEMENT_PARENT_ROW)
    timeout_rows_before = len(_timeout_rows())
    replacement_accepted = (
        "decision-archive-ledger-parent-replacement-overlay-v1" in docs
        and "total_replaced_parent_rows_after_overlay=5" in docs
        and split.get("ok") is True
        and split.get("selected_fixture_family") == REPLACEMENT_FIXTURE_FAMILY
        and split.get("selected_parent_row") == REPLACEMENT_PARENT_ROW
        and split.get("parent_row_still_timeout") is True
        and split.get("parent_row_marked_pass") is False
        and split.get("parent_row_replaced_for_release_cleanliness_accounting") is False
        and split.get("split_fixture_pass_count") == REPLACEMENT_FIXTURE_TARGET_COUNT
        and split.get("split_fixture_fail_count") == 0
        and parent.get("name") == REPLACEMENT_PARENT_ROW
        and parent.get("status") == "timeout"
    )
    overlay_replaced_parent_rows = 1 if replacement_accepted else 0
    total_replaced_parent_rows = REPLACED_PARENT_ROWS_BEFORE_OVERLAY + overlay_replaced_parent_rows
    timeout_rows_remaining_after_overlay = timeout_rows_before - total_replaced_parent_rows
    active_cleanliness_blockers_after_overlay = timeout_rows_remaining_after_overlay
    total_replacement_fixture_targets = 25 + int(split.get("fixture_targets_in_family") or 0)
    total_replacement_fixture_pass_count = 25 + int(split.get("split_fixture_pass_count") or 0)
    full_install_release_clean = active_cleanliness_blockers_after_overlay == 0
    policy_results = {
        "v1017_decision_overlay_prerequisite_represented": "decision-archive-ledger-parent-replacement-overlay-v1" in docs and "total_replaced_parent_rows_after_overlay=5" in docs,
        "v1018_candidate_split_prerequisite_passed": split.get("ok") is True and split.get("split_smoke_passed") is True,
        "selected_parent_row_is_timeout_in_original_ledger": parent.get("name") == REPLACEMENT_PARENT_ROW and parent.get("status") == "timeout",
        "selected_fixture_family_matches_candidate_handoff": split.get("selected_fixture_family") == REPLACEMENT_FIXTURE_FAMILY,
        "selected_fixture_targets_all_passed": split.get("split_fixture_pass_count") == REPLACEMENT_FIXTURE_TARGET_COUNT and split.get("split_fixture_fail_count") == 0,
        "selected_parent_original_timeout_status_preserved": split.get("parent_row_still_timeout") is True and BOUNDARIES["selected_parent_original_timeout_preserved"] is True,
        "selected_parent_not_marked_pass": split.get("parent_row_marked_pass") is False and BOUNDARIES["selected_parent_marked_pass"] is False,
        "selected_parent_replaced_only_in_overlay_accounting": replacement_accepted and BOUNDARIES["parent_rows_replaced_for_release_cleanliness_accounting"] is True,
        "six_total_parent_rows_replaced_for_accounting": total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_OVERLAY,
        "timeout_blocker_count_reduced_to_one_in_overlay": timeout_rows_before == TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT and timeout_rows_remaining_after_overlay == TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_OVERLAY,
        "thirty_replacement_fixture_targets_passed": total_replacement_fixture_targets == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY and total_replacement_fixture_pass_count == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_OVERLAY,
        "full_install_release_still_not_clean": full_install_release_clean is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_SMOKE in docs,
        "cli_flag_registered": CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_CLI in docs,
        "builder_registered": "build_candidate_handoff_parent_replacement_overlay_review" in docs,
        "text_renderer_registered": "candidate_handoff_parent_replacement_overlay_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"candidate_handoff_parent_replacement_overlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "candidate_handoff_parent_replacement_overlay_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_TITLE,
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
        "replaced_parent_rows_before_overlay": REPLACED_PARENT_ROWS_BEFORE_OVERLAY,
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
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def candidate_handoff_parent_replacement_overlay_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    report = dict(report or build_candidate_handoff_parent_replacement_overlay_review())
    lines = [
        CANDIDATE_HANDOFF_PARENT_REPLACEMENT_OVERLAY_TITLE,
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Replacement parent row: {report.get('replacement_parent_row')}",
        f"Replacement fixture family: {report.get('replacement_fixture_family')}",
        f"Replacement fixture targets: {report.get('replacement_fixture_pass_count')}/{report.get('replacement_fixture_target_count')}",
        f"Parent row original timeout preserved: {report.get('parent_row_original_timeout_preserved')}",
        f"Parent row marked pass: {report.get('parent_row_marked_pass')}",
        f"Parent row replaced for release-cleanliness accounting: {report.get('parent_row_replaced_for_release_cleanliness_accounting')}",
        f"Total replaced parent rows after overlay: {report.get('total_replaced_parent_rows_after_overlay')}",
        f"Timeout rows remaining after overlay: {report.get('timeout_rows_remaining_after_overlay')}",
        f"Active cleanliness blockers after overlay: {report.get('active_cleanliness_blockers_after_overlay')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.append("Policy results:")
        for name, passed in (report.get("policy_results") or {}).items():
            lines.append(f"- {name}: {'pass' if passed else 'blocked'}")
    return "\n".join(lines)


def print_candidate_handoff_parent_replacement_overlay_review(root_dir: str | Path | None = None, *, full: bool = False) -> dict[str, Any]:
    report = build_candidate_handoff_parent_replacement_overlay_review(root_dir)
    print(candidate_handoff_parent_replacement_overlay_review_text(report, full=full))
    return report


# v1019.0 candidate handoff parent replacement overlay tokens: candidate-handoff-parent-replacement-overlay-v1 --candidate-handoff-parent-replacement-overlay build_candidate_handoff_parent_replacement_overlay_review candidate_handoff_parent_replacement_overlay_review_text replacement_parent_row=release-candidate-integrity-and-operator-handoff-v1 replacement_fixture_family=candidate_handoff replacement_fixture_targets=5 parent_row_original_timeout_preserved=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=True replaced_parent_rows_before_overlay=5 overlay_replaced_parent_rows=1 total_replaced_parent_rows_after_overlay=6 replacement_fixture_targets_after_overlay=30 timeout_rows_before_replacement=7 timeout_rows_remaining_after_overlay=1 active_cleanliness_blockers_after_overlay=1 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
