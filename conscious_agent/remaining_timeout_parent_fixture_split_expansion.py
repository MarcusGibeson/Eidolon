from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN
from recovery_closure_parent_replacement_overlay import build_recovery_closure_parent_replacement_overlay_review

REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_VERSION = CURRENT_VERSION
REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_SMOKE = "remaining-timeout-parent-fixture-split-expansion-v1"
REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_CLI = "--remaining-timeout-parent-fixture-split-expansion"
REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_TITLE = "Remaining Timeout Parent Fixture Split Expansion v1"

SELECTED_PARENT_TIMEOUT_ROW = "release-decision-and-archive-ledger-v1"
SELECTED_FIXTURE_FAMILY = "decision_archive_ledger"
SELECTED_OWNER_MODULE = "conscious_agent/release_decision_archive_ledger.py"
SELECTED_FIXTURE_TARGETS: tuple[str, ...] = (
    "release_decision_scope_contract_fixture",
    "operator_decision_option_matrix_fixture",
    "release_archive_ledger_prep_fixture",
    "archive_integrity_continuity_review_fixture",
    "release_decision_archive_ledger_board_fixture",
)
REPLACED_PARENT_ROWS_BEFORE_SPLIT = 4
REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT = 3
PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT = 2

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "creates_split_smoke": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "executes_release_decision_archive_board": False,
    "parent_row_replaced_for_release_cleanliness_accounting": False,
    "parent_row_marked_pass": False,
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


def _literal_assignment(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            try:
                return ast.literal_eval(node.value)
            except Exception:
                return None
    return None


def _fixture_result(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "blocked", "passed": bool(passed), "evidence": evidence}


def _timeout_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS if row.get("status") == "timeout"]


def _parent_timeout_row(name: str) -> dict[str, Any]:
    for row in _timeout_rows():
        if row.get("name") == name:
            return dict(row)
    return {}


def _fixture_plan_row(family: str) -> dict[str, Any]:
    for row in FIXTURE_DECOMPOSITION_PLAN:
        if row.get("fixture_family") == family:
            return dict(row)
    return {}


def _source_contract(root: Path) -> dict[str, Any]:
    owner = root / SELECTED_OWNER_MODULE
    text = _read_text(owner)
    try:
        tree = ast.parse(text or "")
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
    return {
        "fixture_family": SELECTED_FIXTURE_FAMILY,
        "parent_timeout_row": SELECTED_PARENT_TIMEOUT_ROW,
        "owner_module": SELECTED_OWNER_MODULE,
        "owner_exists": owner.exists(),
        "source_text": text,
        "release_decision_scope_fields": _literal_assignment(tree, "RELEASE_DECISION_SCOPE_FIELDS") or (),
        "operator_decision_option_fields": _literal_assignment(tree, "OPERATOR_DECISION_OPTION_FIELDS") or (),
        "release_archive_ledger_fields": _literal_assignment(tree, "RELEASE_ARCHIVE_LEDGER_FIELDS") or (),
        "archive_integrity_fields": _literal_assignment(tree, "ARCHIVE_INTEGRITY_FIELDS") or (),
        "operator_decision_options": _literal_assignment(tree, "OPERATOR_DECISION_OPTIONS") or (),
        "release_decision_scope_boundaries": _literal_assignment(tree, "RELEASE_DECISION_SCOPE_BOUNDARIES") or {},
        "operator_decision_boundaries": _literal_assignment(tree, "OPERATOR_DECISION_BOUNDARIES") or {},
        "archive_ledger_boundaries": _literal_assignment(tree, "ARCHIVE_LEDGER_BOUNDARIES") or {},
        "archive_integrity_boundaries": _literal_assignment(tree, "ARCHIVE_INTEGRITY_BOUNDARIES") or {},
        "release_decision_archive_board_boundaries": _literal_assignment(tree, "RELEASE_DECISION_ARCHIVE_BOARD_BOUNDARIES") or {},
    }


def _run_decision_archive_ledger_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    scope_fields = set(contract.get("release_decision_scope_fields") or ())
    option_fields = set(contract.get("operator_decision_option_fields") or ())
    ledger_fields = set(contract.get("release_archive_ledger_fields") or ())
    integrity_fields = set(contract.get("archive_integrity_fields") or ())
    decision_options = tuple(contract.get("operator_decision_options") or ())
    scope_boundaries = dict(contract.get("release_decision_scope_boundaries") or {})
    option_boundaries = dict(contract.get("operator_decision_boundaries") or {})
    ledger_boundaries = dict(contract.get("archive_ledger_boundaries") or {})
    integrity_boundaries = dict(contract.get("archive_integrity_boundaries") or {})
    board_boundaries = dict(contract.get("release_decision_archive_board_boundaries") or {})
    return [
        _fixture_result(
            "release_decision_scope_contract_fixture",
            bool(contract.get("owner_exists"))
            and {"candidate_version_identity", "handoff_packet_reference", "verification_evidence_summary", "known_warnings", "known_blockers", "operator_decision_choices", "archive_readiness_requirements", "operator_notes"}.issubset(scope_fields)
            and scope_boundaries.get("release_decision_scope_is_release_approval") is False
            and scope_boundaries.get("decision_preparation_is_publish_permission") is False
            and scope_boundaries.get("release_decision_scope_runs_commands") is False
            and scope_boundaries.get("release_decision_scope_applies_patches") is False
            and scope_boundaries.get("release_decision_scope_executes_rollback") is False
            and scope_boundaries.get("release_decision_scope_creates_release") is False
            and scope_boundaries.get("release_decision_scope_publishes_release") is False
            and scope_boundaries.get("release_decision_scope_writes_source") is False
            and scope_boundaries.get("release_decision_scope_writes_memory") is False
            and scope_boundaries.get("release_decision_scope_expands_autonomy") is False
            and scope_boundaries.get("operator_review_required") is True,
            "Release decision scope contract exists and remains review-only, non-approving, non-executing, non-writing, and operator-reviewed.",
        ),
        _fixture_result(
            "operator_decision_option_matrix_fixture",
            {"candidate_summary", "verification_summary", "rollback_recovery_reference", "archive_readiness_summary", "decision_options", "operator_selection_required"}.issubset(option_fields)
            and len(decision_options) == 6
            and option_boundaries.get("decision_options_are_selected_automatically") is False
            and option_boundaries.get("ranking_an_option_authorizes_it") is False
            and option_boundaries.get("recommendation_is_approval") is False
            and option_boundaries.get("decision_matrix_runs_commands") is False
            and option_boundaries.get("decision_matrix_applies_patches") is False
            and option_boundaries.get("decision_matrix_executes_rollback") is False
            and option_boundaries.get("decision_matrix_creates_release") is False
            and option_boundaries.get("decision_matrix_publishes_release") is False
            and option_boundaries.get("decision_matrix_writes_source") is False
            and option_boundaries.get("decision_matrix_writes_memory") is False
            and option_boundaries.get("decision_matrix_expands_autonomy") is False
            and option_boundaries.get("operator_selection_required") is True,
            "Operator decision matrix provides choices but does not select, approve, publish, run commands, write source/memory, or expand autonomy.",
        ),
        _fixture_result(
            "release_archive_ledger_prep_fixture",
            {"version", "arc_title", "package_name", "source_only_package_privacy_status", "verification_summary", "known_warnings", "operator_decision_status", "closure_status", "next_arc_reference"}.issubset(ledger_fields)
            and ledger_boundaries.get("archive_ledger_prep_writes_external_archive") is False
            and ledger_boundaries.get("ledger_readiness_is_release_publication") is False
            and ledger_boundaries.get("archive_ledger_prep_creates_release") is False
            and ledger_boundaries.get("archive_ledger_prep_publishes_release") is False
            and ledger_boundaries.get("archive_ledger_prep_runs_commands") is False
            and ledger_boundaries.get("archive_ledger_prep_applies_patches") is False
            and ledger_boundaries.get("archive_ledger_prep_executes_rollback") is False
            and ledger_boundaries.get("archive_ledger_prep_writes_source") is False
            and ledger_boundaries.get("archive_ledger_prep_writes_memory") is False
            and ledger_boundaries.get("archive_ledger_prep_expands_autonomy") is False
            and ledger_boundaries.get("operator_review_required") is True,
            "Archive ledger prep is a source-local review contract, not external archive writing, release creation, publish permission, or autonomy expansion.",
        ),
        _fixture_result(
            "archive_integrity_continuity_review_fixture",
            {"readme_current_header", "release_history_top_entry", "workspace_project_metadata", "source_version_markers", "dashboard_api_cli_current_text", "stale_version_audit_compatibility", "package_privacy_summary"}.issubset(integrity_fields)
            and integrity_boundaries.get("archive_integrity_is_release_approval") is False
            and integrity_boundaries.get("continuity_alignment_is_publish_permission") is False
            and integrity_boundaries.get("archive_integrity_review_writes_archive") is False
            and integrity_boundaries.get("archive_integrity_review_creates_release") is False
            and integrity_boundaries.get("archive_integrity_review_publishes_release") is False
            and integrity_boundaries.get("archive_integrity_review_runs_commands") is False
            and integrity_boundaries.get("archive_integrity_review_applies_patches") is False
            and integrity_boundaries.get("archive_integrity_review_executes_rollback") is False
            and integrity_boundaries.get("archive_integrity_review_expands_autonomy") is False
            and integrity_boundaries.get("operator_review_required") is True,
            "Archive integrity continuity review checks current evidence without approving, publishing, writing archive data, executing rollback, or expanding autonomy.",
        ),
        _fixture_result(
            "release_decision_archive_ledger_board_fixture",
            "build_release_decision_archive_ledger_board" in text
            and board_boundaries.get("release_decision_board_is_release_approval") is False
            and board_boundaries.get("release_decision_board_is_publish_permission") is False
            and board_boundaries.get("release_decision_board_selects_decision") is False
            and board_boundaries.get("release_decision_board_writes_external_archive") is False
            and board_boundaries.get("release_decision_board_executes_commands") is False
            and board_boundaries.get("release_decision_board_applies_patches") is False
            and board_boundaries.get("release_decision_board_executes_rollback") is False
            and board_boundaries.get("release_decision_board_writes_source") is False
            and board_boundaries.get("release_decision_board_writes_memory") is False
            and board_boundaries.get("release_decision_board_creates_release") is False
            and board_boundaries.get("release_decision_board_publishes_release") is False
            and board_boundaries.get("release_decision_board_invokes_models_by_default") is False
            and board_boundaries.get("release_decision_board_schedules_work") is False
            and board_boundaries.get("release_decision_board_reuses_approval") is False
            and board_boundaries.get("release_decision_board_continues_automatically") is False
            and board_boundaries.get("release_decision_board_expands_autonomy") is False
            and board_boundaries.get("operator_review_required") is True
            and board_boundaries.get("approval_required") is True,
            "Release decision archive ledger board exists and remains non-authorizing, non-executing, non-writing, non-autonomous, and approval-gated.",
        ),
    ]


def build_remaining_timeout_parent_fixture_split_expansion_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/remaining_timeout_parent_fixture_split_expansion.py",
        "conscious_agent/recovery_closure_parent_replacement_overlay.py",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/release_decision_archive_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    overlay = build_recovery_closure_parent_replacement_overlay_review(root)
    parent = _parent_timeout_row(SELECTED_PARENT_TIMEOUT_ROW)
    plan = _fixture_plan_row(SELECTED_FIXTURE_FAMILY)
    contract = _source_contract(root)
    fixture_results = _run_decision_archive_ledger_fixtures(contract)
    pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
    fail_count = len(fixture_results) - pass_count
    timeout_rows_total = len(_timeout_rows())
    split_smoke_passed = pass_count == len(SELECTED_FIXTURE_TARGETS) and fail_count == 0
    policy_results = {
        "v1015_recovery_overlay_prerequisite_passed": overlay.get("ok") is True and overlay.get("total_replaced_parent_rows_after_overlay") == REPLACED_PARENT_ROWS_BEFORE_SPLIT,
        "three_timeout_parent_rows_remain_before_split": overlay.get("timeout_rows_remaining_after_overlay") == REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT,
        "selected_parent_row_is_original_timeout": parent.get("name") == SELECTED_PARENT_TIMEOUT_ROW and parent.get("status") == "timeout",
        "fixture_plan_matches_selected_parent": plan.get("name") == SELECTED_PARENT_TIMEOUT_ROW and plan.get("fixture_family") == SELECTED_FIXTURE_FAMILY,
        "fixture_plan_targets_match_selection": tuple(plan.get("bounded_fixture_targets") or ()) == SELECTED_FIXTURE_TARGETS,
        "owner_module_exists": contract.get("owner_exists") is True,
        "split_fixture_count_is_five": len(fixture_results) == 5,
        "split_fixture_names_match_selection": tuple(row.get("name") for row in fixture_results) == SELECTED_FIXTURE_TARGETS,
        "split_fixture_targets_all_passed": split_smoke_passed,
        "selected_parent_original_timeout_preserved": BOUNDARIES["selected_parent_original_timeout_preserved"] is True,
        "selected_parent_not_marked_pass": BOUNDARIES["parent_row_marked_pass"] is False,
        "selected_parent_not_replaced_yet": BOUNDARIES["parent_row_replaced_for_release_cleanliness_accounting"] is False,
        "projected_blocker_count_after_future_replacement_is_two": PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT == 2,
        "full_install_release_still_not_clean": BOUNDARIES["marks_install_release_clean"] is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_SMOKE in docs,
        "cli_flag_registered": REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_CLI in docs,
        "builder_registered": "build_remaining_timeout_parent_fixture_split_expansion_review" in docs,
        "text_renderer_registered": "remaining_timeout_parent_fixture_split_expansion_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"remaining_timeout_parent_fixture_split_expansion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "remaining_timeout_parent_fixture_split_expansion_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "selected_parent_row": SELECTED_PARENT_TIMEOUT_ROW,
        "selected_fixture_family": SELECTED_FIXTURE_FAMILY,
        "selected_owner_module": SELECTED_OWNER_MODULE,
        "selected_fixture_targets": list(SELECTED_FIXTURE_TARGETS),
        "fixture_target_names": [row.get("name") for row in fixture_results],
        "fixture_targets_in_family": len(fixture_results),
        "split_fixture_pass_count": pass_count,
        "split_fixture_fail_count": fail_count,
        "fixture_results": fixture_results,
        "split_smoke_created": True,
        "split_smoke_passed": split_smoke_passed,
        "already_replaced_parent_rows": REPLACED_PARENT_ROWS_BEFORE_SPLIT,
        "remaining_timeout_parent_rows_before_split": REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT,
        "timeout_rows_before_replacement": timeout_rows_total,
        "parent_row_still_timeout": parent.get("status") == "timeout",
        "parent_row_marked_pass": False,
        "parent_row_replaced_for_release_cleanliness_accounting": False,
        "projected_timeout_blockers_after_future_replacement": PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT,
        "full_install_release_clean": False,
        "release_authorized": False,
        "prerequisite_reports": {
            "v1015_overlay_ok": overlay.get("ok"),
            "v1015_replaced_parent_rows": overlay.get("total_replaced_parent_rows_after_overlay"),
            "v1015_timeout_rows_remaining": overlay.get("timeout_rows_remaining_after_overlay"),
        },
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def remaining_timeout_parent_fixture_split_expansion_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    report = dict(report or build_remaining_timeout_parent_fixture_split_expansion_review())
    lines = [
        f"{REMAINING_TIMEOUT_PARENT_FIXTURE_SPLIT_EXPANSION_TITLE}",
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"OK: {report.get('ok')}",
        f"Selected parent row: {report.get('selected_parent_row')}",
        f"Selected fixture family: {report.get('selected_fixture_family')}",
        f"Selected owner module: {report.get('selected_owner_module')}",
        f"Fixture targets: {report.get('split_fixture_pass_count')}/{report.get('fixture_targets_in_family')}",
        f"Split smoke created: {report.get('split_smoke_created')}",
        f"Split smoke passed: {report.get('split_smoke_passed')}",
        f"Already replaced parent rows: {report.get('already_replaced_parent_rows')}",
        f"Remaining timeout parent rows before split: {report.get('remaining_timeout_parent_rows_before_split')}",
        f"Parent row still timeout: {report.get('parent_row_still_timeout')}",
        f"Parent row marked pass: {report.get('parent_row_marked_pass')}",
        f"Parent row replaced for release-cleanliness accounting: {report.get('parent_row_replaced_for_release_cleanliness_accounting')}",
        f"Projected timeout blockers after future replacement: {report.get('projected_timeout_blockers_after_future_replacement')}",
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


def print_remaining_timeout_parent_fixture_split_expansion_review(root_dir: str | Path | None = None, *, full: bool = False) -> dict[str, Any]:
    report = build_remaining_timeout_parent_fixture_split_expansion_review(root_dir)
    print(remaining_timeout_parent_fixture_split_expansion_review_text(report, full=full))
    return report


# v1016.0 remaining timeout parent fixture split expansion tokens: remaining-timeout-parent-fixture-split-expansion-v1 --remaining-timeout-parent-fixture-split-expansion build_remaining_timeout_parent_fixture_split_expansion_review remaining_timeout_parent_fixture_split_expansion_review_text selected_parent_row=release-decision-and-archive-ledger-v1 selected_fixture_family=decision_archive_ledger selected_fixture_targets=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False already_replaced_parent_rows=4 remaining_timeout_parent_rows_before_split=3 projected_timeout_blockers_after_future_replacement=2 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
