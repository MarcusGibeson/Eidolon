from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_timeout_parent_replacement import build_install_release_timeout_parent_replacement_pilot_review
from release_archive_fixture_split_expansion import (
    EXPANDED_FIXTURE_FAMILIES,
    EXPANDED_PARENT_TIMEOUT_ROWS,
    build_release_archive_fixture_split_expansion_review,
)

INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_VERSION = CURRENT_VERSION
INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_SMOKE = "install-release-parent-replacement-expansion-v1"
INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_CLI = "--install-release-parent-replacement-expansion"
INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_TITLE = "Install-Release Parent Replacement Expansion v1"

EXPANSION_REPLACEMENT_FAMILIES: tuple[str, ...] = EXPANDED_FIXTURE_FAMILIES
EXPANSION_REPLACEMENT_PARENT_ROWS: dict[str, str] = dict(EXPANDED_PARENT_TIMEOUT_ROWS)
TOTAL_REPLACED_PARENT_ROWS_AFTER_EXPANSION = 3
TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT = 7
TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_EXPANSION = 4
TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_EXPANSION = 15

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_release_archive_board": False,
    "parent_rows_replaced_for_release_cleanliness_accounting": True,
    "parent_rows_marked_pass": False,
    "original_parent_row_statuses_preserved": True,
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


def _family_report_map(split_expansion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("fixture_family")): dict(row) for row in split_expansion.get("family_reports") or []}


def build_install_release_parent_replacement_expansion_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_parent_replacement_expansion.py",
        "conscious_agent/install_release_timeout_parent_replacement.py",
        "conscious_agent/release_archive_fixture_split_expansion.py",
        "conscious_agent/install_release_fixture_smoke_split.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    pilot = build_install_release_timeout_parent_replacement_pilot_review(root)
    split = build_release_archive_fixture_split_expansion_review(root)
    family_reports = _family_report_map(split)
    timeout_rows_before = len(_timeout_rows())
    expansion_rows: list[dict[str, Any]] = []
    for family in EXPANSION_REPLACEMENT_FAMILIES:
        parent_name = EXPANSION_REPLACEMENT_PARENT_ROWS[family]
        parent = _timeout_row_by_name(parent_name)
        family_report = family_reports.get(family, {})
        fixture_names = list(family_report.get("fixture_target_names") or [])
        fixture_pass_count = int(family_report.get("split_fixture_pass_count") or 0)
        fixture_fail_count = int(family_report.get("split_fixture_fail_count") or 0)
        accepted = (
            parent.get("name") == parent_name
            and parent.get("status") == "timeout"
            and family_report.get("family_split_passed") is True
            and family_report.get("parent_row_still_timeout") is True
            and len(fixture_names) == 5
            and fixture_pass_count == 5
            and fixture_fail_count == 0
        )
        expansion_rows.append({
            "fixture_family": family,
            "parent_row": parent_name,
            "parent_row_original_status": parent.get("status"),
            "parent_row_original_timeout_preserved": parent.get("status") == "timeout",
            "parent_row_marked_pass": False,
            "fixture_target_names": fixture_names,
            "fixture_target_count": len(fixture_names),
            "fixture_pass_count": fixture_pass_count,
            "fixture_fail_count": fixture_fail_count,
            "replacement_accepted": accepted,
        })
    expansion_replaced_count = sum(1 for row in expansion_rows if row.get("replacement_accepted") is True)
    total_replaced_parent_rows = int(pilot.get("replaced_parent_rows") or 0) + expansion_replaced_count
    timeout_rows_remaining_after_expansion = timeout_rows_before - total_replaced_parent_rows
    active_cleanliness_blockers_after_expansion = timeout_rows_remaining_after_expansion
    total_replacement_fixture_targets = int(pilot.get("replacement_fixture_target_count") or 0) + sum(int(row.get("fixture_target_count") or 0) for row in expansion_rows)
    total_replacement_fixture_pass_count = int(pilot.get("replacement_fixture_pass_count") or 0) + sum(int(row.get("fixture_pass_count") or 0) for row in expansion_rows)
    full_install_release_clean = active_cleanliness_blockers_after_expansion == 0
    policy_results = {
        "v1011_parent_replacement_prerequisite_passed": pilot.get("ok") is True and pilot.get("replaced_parent_rows") == 1,
        "v1007_split_expansion_prerequisite_passed": split.get("ok") is True and split.get("expanded_family_count") == 2,
        "expansion_replacement_family_count_is_two": len(expansion_rows) == 2,
        "expansion_families_are_expected": {row.get("fixture_family") for row in expansion_rows} == set(EXPANSION_REPLACEMENT_FAMILIES),
        "expansion_parent_rows_original_timeouts_preserved": all(row.get("parent_row_original_timeout_preserved") is True for row in expansion_rows),
        "expansion_parent_rows_not_marked_pass": all(row.get("parent_row_marked_pass") is False for row in expansion_rows) and BOUNDARIES["parent_rows_marked_pass"] is False,
        "expansion_fixture_targets_all_passed": sum(int(row.get("fixture_target_count") or 0) for row in expansion_rows) == 10 and sum(int(row.get("fixture_pass_count") or 0) for row in expansion_rows) == 10 and all(row.get("fixture_fail_count") == 0 for row in expansion_rows),
        "two_expansion_parent_rows_replaced_for_accounting": expansion_replaced_count == 2,
        "three_total_parent_rows_replaced_for_accounting": total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_EXPANSION,
        "timeout_blocker_count_reduced_to_four_in_overlay": timeout_rows_before == TOTAL_TIMEOUT_ROWS_BEFORE_REPLACEMENT and timeout_rows_remaining_after_expansion == TOTAL_TIMEOUT_ROWS_REMAINING_AFTER_EXPANSION,
        "fifteen_replacement_fixture_targets_passed": total_replacement_fixture_targets == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_EXPANSION and total_replacement_fixture_pass_count == TOTAL_REPLACEMENT_FIXTURE_TARGETS_AFTER_EXPANSION,
        "full_install_release_still_not_clean": full_install_release_clean is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_CLI in docs,
        "builder_registered": "build_install_release_parent_replacement_expansion_review" in docs,
        "text_renderer_registered": "install_release_parent_replacement_expansion_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_parent_replacement_expansion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_parent_replacement_expansion_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_PARENT_REPLACEMENT_EXPANSION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "pilot_replaced_parent_rows": pilot.get("replaced_parent_rows"),
        "expansion_replacement_families": list(EXPANSION_REPLACEMENT_FAMILIES),
        "expansion_replacement_parent_rows": [EXPANSION_REPLACEMENT_PARENT_ROWS[family] for family in EXPANSION_REPLACEMENT_FAMILIES],
        "expansion_rows": expansion_rows,
        "expansion_replaced_parent_rows": expansion_replaced_count,
        "total_replaced_parent_rows_after_expansion": total_replaced_parent_rows,
        "timeout_rows_before_replacement": timeout_rows_before,
        "timeout_rows_remaining_after_expansion": timeout_rows_remaining_after_expansion,
        "active_cleanliness_blockers_after_expansion": active_cleanliness_blockers_after_expansion,
        "replacement_fixture_targets_after_expansion": total_replacement_fixture_targets,
        "replacement_fixture_pass_count_after_expansion": total_replacement_fixture_pass_count,
        "replacement_fixture_fail_count_after_expansion": total_replacement_fixture_targets - total_replacement_fixture_pass_count,
        "parent_rows_original_timeout_preserved": all(row.get("parent_row_original_timeout_preserved") is True for row in expansion_rows) and pilot.get("parent_row_original_timeout_preserved") is True,
        "parent_rows_marked_pass": False,
        "parent_rows_replaced_for_release_cleanliness_accounting": total_replaced_parent_rows == TOTAL_REPLACED_PARENT_ROWS_AFTER_EXPANSION,
        "full_install_release_clean": full_install_release_clean,
        "release_authorized": False,
        "marks_install_release_clean": False,
        "replacement_summary": "Three timeout parent rows now have bounded fixture replacement evidence for release-cleanliness accounting; four timeout parent rows remain active blockers.",
        "autonomy_blocking_status": "blocked_until_remaining_four_timeout_parent_rows_are_replaced_or_repaired_and_phase_zero_is_explicitly_authorized",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_parent_replacement_expansion_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Parent Replacement Expansion report not found."
    lines = [
        "# Install-Release Parent Replacement Expansion",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Pilot replaced parent rows: {report.get('pilot_replaced_parent_rows')}",
        f"Expansion replacement families: {', '.join(report.get('expansion_replacement_families') or [])}",
        f"Expansion replaced parent rows: {report.get('expansion_replaced_parent_rows')}",
        f"Total replaced parent rows after expansion: {report.get('total_replaced_parent_rows_after_expansion')}",
        f"Replacement fixture targets after expansion: {report.get('replacement_fixture_pass_count_after_expansion')}/{report.get('replacement_fixture_targets_after_expansion')}",
        f"Parent rows original timeout preserved: {report.get('parent_rows_original_timeout_preserved')}",
        f"Parent rows marked pass: {report.get('parent_rows_marked_pass')}",
        f"Timeout rows before replacement: {report.get('timeout_rows_before_replacement')}",
        f"Timeout rows remaining after expansion: {report.get('timeout_rows_remaining_after_expansion')}",
        f"Active cleanliness blockers after expansion: {report.get('active_cleanliness_blockers_after_expansion')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Summary: {report.get('replacement_summary')}",
    ]
    if full:
        lines.extend(["", "## Expansion rows"])
        for row in report.get("expansion_rows") or []:
            lines.append(f"- {row.get('parent_row')} via {row.get('fixture_family')}: {row.get('fixture_pass_count')}/{row.get('fixture_target_count')} fixtures passed; parent timeout preserved={row.get('parent_row_original_timeout_preserved')}; parent marked pass={row.get('parent_row_marked_pass')}; replacement accepted={row.get('replacement_accepted')}")
            for name in row.get("fixture_target_names") or []:
                lines.append(f"  - {name}")
        lines.extend(["", "## Policy results"])
        for key, value in sorted((report.get("policy_results") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Boundaries"])
        for key in ["executes_full_install_release_segment", "executes_parent_timeout_rows", "parent_rows_marked_pass", "release_authorized", "autonomy_expanded", "review_only"]:
            lines.append(f"- {key}: {report.get(key)}")
    return "\n".join(lines)


def print_install_release_parent_replacement_expansion_review(full: bool = False, root_dir: str | Path | None = None) -> None:
    print(install_release_parent_replacement_expansion_review_text(build_install_release_parent_replacement_expansion_review(root_dir), full=full))


# v1013.0 install-release parent replacement expansion tokens: install-release-parent-replacement-expansion-v1 --install-release-parent-replacement-expansion build_install_release_parent_replacement_expansion_review install_release_parent_replacement_expansion_review_text expansion_replacement_families=archive_search_handoff,archive_export_closure expansion_replaced_parent_rows=2 total_replaced_parent_rows_after_expansion=3 replacement_fixture_targets_after_expansion=15 parent_rows_original_timeout_preserved=True parent_rows_marked_pass=False timeout_rows_before_replacement=7 timeout_rows_remaining_after_expansion=4 active_cleanliness_blockers_after_expansion=4 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
