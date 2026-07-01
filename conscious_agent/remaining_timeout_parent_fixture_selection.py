from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN, build_install_release_fixture_decomposition_plan_review
from install_release_parent_replacement_expansion import build_install_release_parent_replacement_expansion_review

REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_VERSION = CURRENT_VERSION
REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_SMOKE = "remaining-timeout-parent-fixture-selection-v1"
REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_CLI = "--remaining-timeout-parent-fixture-selection"
REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_TITLE = "Remaining Timeout Parent Fixture Split Selection v1"

SELECTED_PARENT_ROW = "recovery-drill-and-release-closure-v1"
SELECTED_FIXTURE_FAMILY = "recovery_closure"
SELECTED_OWNER_MODULE = "conscious_agent/recovery_drill_release_closure.py"
REPLACED_PARENT_ROWS_BEFORE_SELECTION = 3
ACTIVE_TIMEOUT_BLOCKERS_BEFORE_SELECTION = 4
PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT = 3
EXPECTED_SELECTED_FIXTURE_TARGETS = 5

ALREADY_REPLACED_PARENT_ROWS: tuple[str, ...] = (
    "release-archive-retrieval-and-continuity-index-v1",
    "release-archive-search-and-handoff-review-v1",
    "release-archive-export-and-decision-closure-v1",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "executes_release_archive_board": False,
    "selects_next_fixture_family": True,
    "creates_split_smoke": False,
    "parent_rows_replaced_for_release_cleanliness_accounting": False,
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


def _decomposition_row_by_parent(parent_name: str) -> dict[str, Any]:
    for row in FIXTURE_DECOMPOSITION_PLAN:
        if row.get("name") == parent_name:
            return dict(row)
    return {}


def _remaining_timeout_rows_after_v1012() -> list[dict[str, Any]]:
    replaced = set(ALREADY_REPLACED_PARENT_ROWS)
    return [row for row in _timeout_rows() if row.get("name") not in replaced]


def build_remaining_timeout_parent_fixture_selection_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/remaining_timeout_parent_fixture_selection.py",
        "conscious_agent/install_release_parent_replacement_expansion.py",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    replacement_expansion = build_install_release_parent_replacement_expansion_review(root)
    decomposition = build_install_release_fixture_decomposition_plan_review(root)
    timeout_rows = _timeout_rows()
    remaining_rows = _remaining_timeout_rows_after_v1012()
    remaining_names = [str(row.get("name")) for row in remaining_rows]
    selected_parent = next((row for row in remaining_rows if row.get("name") == SELECTED_PARENT_ROW), {})
    selected_plan = _decomposition_row_by_parent(SELECTED_PARENT_ROW)
    selected_targets = list(selected_plan.get("bounded_fixture_targets") or [])
    ready_for_split = (
        selected_parent.get("status") == "timeout"
        and selected_plan.get("fixture_family") == SELECTED_FIXTURE_FAMILY
        and selected_plan.get("owner_module") == SELECTED_OWNER_MODULE
        and len(selected_targets) == EXPECTED_SELECTED_FIXTURE_TARGETS
        and all(str(target).endswith("_fixture") for target in selected_targets)
    )
    projected_remaining_after_future_replacement = len(remaining_rows) - 1 if ready_for_split else len(remaining_rows)
    selection_record = {
        "selected_parent_row": SELECTED_PARENT_ROW,
        "selected_parent_original_status": selected_parent.get("status"),
        "selected_parent_timeout_preserved": selected_parent.get("status") == "timeout",
        "selected_parent_marked_pass": False,
        "selected_fixture_family": SELECTED_FIXTURE_FAMILY,
        "selected_owner_module": SELECTED_OWNER_MODULE,
        "selected_fixture_targets": selected_targets,
        "selected_fixture_target_count": len(selected_targets),
        "selected_family_ready_for_split_smoke": ready_for_split,
        "first_repair_action": selected_plan.get("first_repair_action"),
        "future_expected_action": "create_bounded_split_smoke_before_any_parent_replacement_claim",
    }
    policy_results = {
        "v1012_parent_replacement_expansion_prerequisite_passed": replacement_expansion.get("ok") is True and replacement_expansion.get("total_replaced_parent_rows_after_expansion") == REPLACED_PARENT_ROWS_BEFORE_SELECTION,
        "v1005_decomposition_prerequisite_passed": decomposition.get("ok") is True and decomposition.get("fixture_targets_total") == 35,
        "remaining_timeout_parent_count_is_four": len(remaining_rows) == ACTIVE_TIMEOUT_BLOCKERS_BEFORE_SELECTION,
        "remaining_timeout_parent_names_recorded": set(remaining_names) == {
            "recovery-drill-and-release-closure-v1",
            "release-candidate-integrity-and-operator-handoff-v1",
            "release-decision-and-archive-ledger-v1",
            "fast-install-release-isolation-gate-v1",
        },
        "selected_parent_is_remaining_timeout": selected_parent.get("name") == SELECTED_PARENT_ROW and selected_parent.get("status") == "timeout",
        "selected_fixture_family_matches_plan": selected_plan.get("fixture_family") == SELECTED_FIXTURE_FAMILY,
        "selected_owner_module_matches_plan": selected_plan.get("owner_module") == SELECTED_OWNER_MODULE,
        "selected_fixture_targets_count_is_five": len(selected_targets) == EXPECTED_SELECTED_FIXTURE_TARGETS,
        "selected_fixture_targets_are_named": bool(selected_targets) and all(str(target).endswith("_fixture") for target in selected_targets),
        "selected_family_ready_for_future_split_smoke": ready_for_split is True,
        "projected_blocker_count_after_future_replacement_is_three": projected_remaining_after_future_replacement == PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_selected_parent_row"] is False,
        "does_not_create_split_smoke_yet": BOUNDARIES["creates_split_smoke"] is False,
        "does_not_mark_parent_pass": BOUNDARIES["parent_rows_marked_pass"] is False and selection_record["selected_parent_marked_pass"] is False,
        "full_install_release_still_not_clean": False is False and BOUNDARIES["marks_install_release_clean"] is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_SMOKE in docs,
        "cli_flag_registered": REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_CLI in docs,
        "builder_registered": "build_remaining_timeout_parent_fixture_selection_review" in docs,
        "text_renderer_registered": "remaining_timeout_parent_fixture_selection_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"remaining_timeout_parent_fixture_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "remaining_timeout_parent_fixture_selection_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": REMAINING_TIMEOUT_PARENT_FIXTURE_SELECTION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "selection_mode": "review_only_remaining_timeout_parent_fixture_split_selection",
        "already_replaced_parent_rows": list(ALREADY_REPLACED_PARENT_ROWS),
        "replaced_parent_rows_before_selection": REPLACED_PARENT_ROWS_BEFORE_SELECTION,
        "timeout_rows_before_replacement": len(timeout_rows),
        "remaining_timeout_parent_rows_before_selection": len(remaining_rows),
        "remaining_timeout_parent_names": remaining_names,
        "selected_parent_row": SELECTED_PARENT_ROW,
        "selected_fixture_family": SELECTED_FIXTURE_FAMILY,
        "selected_owner_module": SELECTED_OWNER_MODULE,
        "selected_fixture_target_count": len(selected_targets),
        "selected_fixture_targets": selected_targets,
        "selected_family_ready_for_split_smoke": ready_for_split,
        "selected_parent_original_timeout_preserved": selected_parent.get("status") == "timeout",
        "selected_parent_marked_pass": False,
        "projected_timeout_blockers_after_future_replacement": projected_remaining_after_future_replacement,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_remaining_timeout_parents_have_bounded_split_smokes_and_replacement_evidence",
        "selection_record": selection_record,
        "prerequisite_reports": {
            "parent_replacement_expansion_status": replacement_expansion.get("status"),
            "parent_replacement_expansion_ok": replacement_expansion.get("ok"),
            "decomposition_status": decomposition.get("status"),
            "decomposition_ok": decomposition.get("ok"),
        },
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def remaining_timeout_parent_fixture_selection_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Remaining Timeout Parent Fixture Split Selection report not found."
    lines = [
        "# Remaining Timeout Parent Fixture Split Selection",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Already replaced parent rows: {report.get('replaced_parent_rows_before_selection')}",
        f"Remaining timeout parent rows before selection: {report.get('remaining_timeout_parent_rows_before_selection')}",
        f"Selected parent row: {report.get('selected_parent_row')}",
        f"Selected fixture family: {report.get('selected_fixture_family')}",
        f"Selected owner module: {report.get('selected_owner_module')}",
        f"Selected fixture targets: {report.get('selected_fixture_target_count')}",
        f"Selected family ready for split smoke: {report.get('selected_family_ready_for_split_smoke')}",
        f"Selected parent original timeout preserved: {report.get('selected_parent_original_timeout_preserved')}",
        f"Selected parent marked pass: {report.get('selected_parent_marked_pass')}",
        f"Projected timeout blockers after future replacement: {report.get('projected_timeout_blockers_after_future_replacement')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Remaining timeout parent rows"])
        for name in report.get("remaining_timeout_parent_names") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Selected fixture targets"])
        for target in report.get("selected_fixture_targets") or []:
            lines.append(f"- {target}")
        record = report.get("selection_record") or {}
        if record:
            lines.extend(["", "## Selection record"])
            for key in ["first_repair_action", "future_expected_action"]:
                lines.append(f"- {key}: {record.get(key)}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_remaining_timeout_parent_fixture_selection_review(full: bool = False) -> None:
    print(remaining_timeout_parent_fixture_selection_review_text(build_remaining_timeout_parent_fixture_selection_review(), full=full))


# v1013.0 remaining timeout parent fixture selection tokens: remaining-timeout-parent-fixture-selection-v1 --remaining-timeout-parent-fixture-selection build_remaining_timeout_parent_fixture_selection_review remaining_timeout_parent_fixture_selection_review_text selected_parent_row=recovery-drill-and-release-closure-v1 selected_fixture_family=recovery_closure selected_fixture_targets=5 remaining_timeout_parent_rows_before_selection=4 selected_parent_original_timeout_preserved=True selected_parent_marked_pass=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
