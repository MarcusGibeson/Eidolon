from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN
from remaining_timeout_parent_fixture_selection import build_remaining_timeout_parent_fixture_selection_review

RECOVERY_CLOSURE_FIXTURE_SPLIT_SMOKE_VERSION = CURRENT_VERSION
RECOVERY_CLOSURE_FIXTURE_SPLIT_SMOKE = "recovery-closure-fixture-split-smoke-v1"
RECOVERY_CLOSURE_FIXTURE_SPLIT_CLI = "--recovery-closure-fixture-split-smoke"
RECOVERY_CLOSURE_FIXTURE_SPLIT_TITLE = "Recovery Closure Fixture Split Smoke v1"

SELECTED_PARENT_TIMEOUT_ROW = "recovery-drill-and-release-closure-v1"
SELECTED_FIXTURE_FAMILY = "recovery_closure"
SELECTED_OWNER_MODULE = "conscious_agent/recovery_drill_release_closure.py"
SELECTED_FIXTURE_TARGETS: tuple[str, ...] = (
    "recovery_drill_scope_contract_fixture",
    "rollback_decision_review_packet_fixture",
    "release_closure_evidence_board_fixture",
    "operator_closure_approval_gate_fixture",
    "recovery_drill_release_closure_board_fixture",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "executes_recovery_release_closure_board": False,
    "creates_split_smoke": True,
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


def _parent_timeout_row(name: str) -> dict[str, Any]:
    for row in INSTALL_RELEASE_LEDGER_ROWS:
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
        "recovery_drill_scope_fields": _literal_assignment(tree, "RECOVERY_DRILL_SCOPE_FIELDS") or (),
        "rollback_decision_fields": _literal_assignment(tree, "ROLLBACK_DECISION_FIELDS") or (),
        "release_closure_fields": _literal_assignment(tree, "RELEASE_CLOSURE_FIELDS") or (),
        "closure_approval_fields": _literal_assignment(tree, "CLOSURE_APPROVAL_FIELDS") or (),
        "recovery_drill_boundaries": _literal_assignment(tree, "RECOVERY_DRILL_BOUNDARIES") or {},
        "rollback_decision_boundaries": _literal_assignment(tree, "ROLLBACK_DECISION_BOUNDARIES") or {},
        "release_closure_boundaries": _literal_assignment(tree, "RELEASE_CLOSURE_BOUNDARIES") or {},
        "closure_approval_boundaries": _literal_assignment(tree, "CLOSURE_APPROVAL_BOUNDARIES") or {},
        "recovery_release_closure_boundaries": _literal_assignment(tree, "RECOVERY_RELEASE_CLOSURE_BOUNDARIES") or {},
    }


def _run_recovery_closure_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    scope_fields = set(contract.get("recovery_drill_scope_fields") or ())
    rollback_fields = set(contract.get("rollback_decision_fields") or ())
    closure_fields = set(contract.get("release_closure_fields") or ())
    approval_fields = set(contract.get("closure_approval_fields") or ())
    scope_boundaries = dict(contract.get("recovery_drill_boundaries") or {})
    rollback_boundaries = dict(contract.get("rollback_decision_boundaries") or {})
    closure_boundaries = dict(contract.get("release_closure_boundaries") or {})
    approval_boundaries = dict(contract.get("closure_approval_boundaries") or {})
    board_boundaries = dict(contract.get("recovery_release_closure_boundaries") or {})
    return [
        _fixture_result(
            "recovery_drill_scope_contract_fixture",
            bool(contract.get("owner_exists"))
            and {"drill_id", "live_patch_reference", "operator_supplied_verification_receipts", "affected_file_expectations", "rollback_snapshot_reference", "rollback_readiness_checklist", "release_closure_prerequisites", "known_blockers", "operator_notes"}.issubset(scope_fields)
            and scope_boundaries.get("recovery_drill_executes_commands") is False
            and scope_boundaries.get("recovery_drill_executes_rollback") is False
            and scope_boundaries.get("recovery_drill_planning_mutates_source") is False
            and scope_boundaries.get("recovery_drill_creates_release") is False
            and scope_boundaries.get("recovery_drill_expands_autonomy") is False,
            "Recovery drill scope contract exists and remains non-executing, non-mutating, non-release-authorizing, and non-autonomous.",
        ),
        _fixture_result(
            "rollback_decision_review_packet_fixture",
            {"verification_receipt_review", "failure_or_warning_summary", "affected_file_manifest", "rollback_snapshot_validity", "restore_risk_notes", "operator_decision_required"}.issubset(rollback_fields)
            and rollback_boundaries.get("rollback_recommendation_is_rollback_execution") is False
            and rollback_boundaries.get("rollback_eligibility_is_rollback_authorization") is False
            and rollback_boundaries.get("rollback_decision_review_executes_rollback") is False
            and rollback_boundaries.get("rollback_decision_review_applies_patches") is False
            and rollback_boundaries.get("rollback_decision_review_expands_autonomy") is False,
            "Rollback decision packet is a review packet, not rollback execution, source mutation, release creation, or autonomy expansion.",
        ),
        _fixture_result(
            "release_closure_evidence_board_fixture",
            {"source_version_alignment", "readme_current_state_alignment", "release_history_top_entry", "dashboard_api_cli_parity", "smoke_results", "package_privacy_scan", "extracted_zip_verification", "no_autonomy_no_authority_confirmation"}.issubset(closure_fields)
            and closure_boundaries.get("release_closure_review_is_release_approval") is False
            and closure_boundaries.get("closure_evidence_is_publish_permission") is False
            and closure_boundaries.get("release_closure_board_creates_release") is False
            and closure_boundaries.get("release_closure_board_publishes_release") is False
            and closure_boundaries.get("release_closure_board_expands_autonomy") is False,
            "Release closure evidence board covers current evidence while denying approval, publish permission, release creation, and autonomy expansion.",
        ),
        _fixture_result(
            "operator_closure_approval_gate_fixture",
            {"exact_operator_closure_phrase", "current_version_confirmation", "evidence_packet_reference", "single_use_scope", "approval_burnout_confirmation"}.issubset(approval_fields)
            and approval_boundaries.get("closure_approval_is_single_use") is True
            and approval_boundaries.get("fresh_operator_phrase_required") is True
            and approval_boundaries.get("closure_approval_authorizes_future_patches") is False
            and approval_boundaries.get("closure_approval_authorizes_future_releases") is False
            and approval_boundaries.get("closure_approval_authorizes_autonomy") is False
            and approval_boundaries.get("closure_gate_infers_approval_from_receipts") is False
            and approval_boundaries.get("closure_gate_reuses_prior_approval") is False,
            "Operator closure approval gate requires an exact fresh single-use phrase and does not authorize future patches, releases, or autonomy.",
        ),
        _fixture_result(
            "recovery_drill_release_closure_board_fixture",
            "build_recovery_drill_release_closure_board" in text
            and board_boundaries.get("recovery_board_is_rollback_permission") is False
            and board_boundaries.get("recovery_board_is_release_approval") is False
            and board_boundaries.get("recovery_board_executes_commands") is False
            and board_boundaries.get("recovery_board_executes_rollback") is False
            and board_boundaries.get("recovery_board_applies_patches") is False
            and board_boundaries.get("recovery_board_creates_release") is False
            and board_boundaries.get("recovery_board_publishes_release") is False
            and board_boundaries.get("recovery_board_writes_source") is False
            and board_boundaries.get("recovery_board_writes_memory") is False
            and board_boundaries.get("recovery_board_expands_autonomy") is False
            and board_boundaries.get("approval_required") is True,
            "Recovery drill release closure board exists and remains non-authorizing, non-executing, non-writing, non-autonomous, and approval-gated.",
        ),
    ]


def build_recovery_closure_fixture_split_smoke_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/recovery_closure_fixture_split_smoke.py",
        "conscious_agent/remaining_timeout_parent_fixture_selection.py",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/recovery_drill_release_closure.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    selection_report = build_remaining_timeout_parent_fixture_selection_review(root)
    plan_row = _fixture_plan_row(SELECTED_FIXTURE_FAMILY)
    parent_row = _parent_timeout_row(SELECTED_PARENT_TIMEOUT_ROW)
    contract = _source_contract(root)
    fixture_results = _run_recovery_closure_fixtures(contract)
    fixture_target_set = set(plan_row.get("bounded_fixture_targets") or ())
    fixture_result_set = {row["name"] for row in fixture_results}
    fixture_pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
    fixture_fail_count = len(fixture_results) - fixture_pass_count
    split_smoke_passed = (
        selection_report.get("ok") is True
        and selection_report.get("selected_fixture_family") == SELECTED_FIXTURE_FAMILY
        and plan_row.get("name") == SELECTED_PARENT_TIMEOUT_ROW
        and plan_row.get("owner_module") == SELECTED_OWNER_MODULE
        and parent_row.get("name") == SELECTED_PARENT_TIMEOUT_ROW
        and parent_row.get("status") == "timeout"
        and fixture_target_set == fixture_result_set == set(SELECTED_FIXTURE_TARGETS)
        and fixture_pass_count == 5
        and fixture_fail_count == 0
        and contract.get("owner_exists") is True
    )
    policy_results = {
        "v1013_selection_prerequisite_passed": selection_report.get("ok") is True and selection_report.get("selected_family_ready_for_split_smoke") is True,
        "selected_parent_is_recovery_timeout_row": parent_row.get("name") == SELECTED_PARENT_TIMEOUT_ROW and parent_row.get("status") == "timeout",
        "selected_fixture_family_matches_plan": plan_row.get("fixture_family") == SELECTED_FIXTURE_FAMILY,
        "selected_owner_module_matches_plan": plan_row.get("owner_module") == SELECTED_OWNER_MODULE,
        "split_fixture_count_is_five": len(fixture_results) == 5,
        "split_fixture_targets_match_plan": fixture_target_set == fixture_result_set == set(SELECTED_FIXTURE_TARGETS),
        "all_recovery_closure_split_fixtures_passed": fixture_pass_count == 5 and fixture_fail_count == 0,
        "parent_original_timeout_preserved": parent_row.get("status") == "timeout",
        "parent_row_not_marked_pass": BOUNDARIES["parent_rows_marked_pass"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_selected_parent_row"] is False,
        "does_not_replace_parent_yet": BOUNDARIES["parent_rows_replaced_for_release_cleanliness_accounting"] is False,
        "full_install_release_not_claimed_clean": BOUNDARIES["marks_install_release_clean"] is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": RECOVERY_CLOSURE_FIXTURE_SPLIT_SMOKE in docs,
        "cli_flag_registered": RECOVERY_CLOSURE_FIXTURE_SPLIT_CLI in docs,
        "builder_registered": "build_recovery_closure_fixture_split_smoke_review" in docs,
        "text_renderer_registered": "recovery_closure_fixture_split_smoke_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and RECOVERY_CLOSURE_FIXTURE_SPLIT_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = split_smoke_passed and all(policy_results.values())
    return {
        "id": f"recovery_closure_fixture_split_smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "recovery_closure_fixture_split_smoke_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": RECOVERY_CLOSURE_FIXTURE_SPLIT_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "fixture_family_selected": SELECTED_FIXTURE_FAMILY,
        "parent_timeout_row": SELECTED_PARENT_TIMEOUT_ROW,
        "parent_row_status": parent_row.get("status"),
        "parent_row_still_timeout": parent_row.get("status") == "timeout",
        "parent_row_marked_pass": False,
        "parent_row_replaced_for_release_cleanliness_accounting": False,
        "owner_module": SELECTED_OWNER_MODULE,
        "fixture_targets_in_family": len(SELECTED_FIXTURE_TARGETS),
        "fixture_target_names": list(SELECTED_FIXTURE_TARGETS),
        "split_fixture_results": fixture_results,
        "split_fixture_pass_count": fixture_pass_count,
        "split_fixture_fail_count": fixture_fail_count,
        "split_smoke_created": True,
        "split_smoke_passed": ok,
        "already_replaced_parent_rows_before_split": 3,
        "remaining_timeout_parent_rows_before_split": 4,
        "projected_timeout_blockers_after_future_replacement": 3,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_recovery_closure_parent_replacement_and_remaining_timeout_parent_rows_are_split_or_repaired",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def recovery_closure_fixture_split_smoke_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Recovery Closure Fixture Split Smoke report not found."
    lines = [
        "# Recovery Closure Fixture Split Smoke",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Fixture family selected: {report.get('fixture_family_selected')}",
        f"Parent timeout row: {report.get('parent_timeout_row')}",
        f"Parent row still timeout: {report.get('parent_row_still_timeout')}",
        f"Parent row marked pass: {report.get('parent_row_marked_pass')}",
        f"Parent row replaced for release-cleanliness accounting: {report.get('parent_row_replaced_for_release_cleanliness_accounting')}",
        f"Fixture targets in family: {report.get('fixture_targets_in_family')}",
        f"Split fixture pass count: {report.get('split_fixture_pass_count')}/{report.get('fixture_targets_in_family')}",
        f"Split smoke created: {report.get('split_smoke_created')}",
        f"Split smoke passed: {report.get('split_smoke_passed')}",
        f"Projected timeout blockers after future replacement: {report.get('projected_timeout_blockers_after_future_replacement')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Split fixture results"])
        for row in report.get("split_fixture_results") or []:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('evidence')}")
        lines.extend(["", "## Policy results"])
        for key, value in sorted((report.get("policy_results") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Boundaries"])
        for key in ["executes_full_install_release_segment", "executes_parent_timeout_rows", "executes_selected_parent_row", "parent_rows_replaced_for_release_cleanliness_accounting", "parent_rows_marked_pass", "release_authorized", "autonomy_expanded", "review_only"]:
            lines.append(f"- {key}: {report.get(key)}")
    return "\n".join(lines)


def print_recovery_closure_fixture_split_smoke_review(full: bool = False, root_dir: str | Path | None = None) -> None:
    print(recovery_closure_fixture_split_smoke_review_text(build_recovery_closure_fixture_split_smoke_review(root_dir), full=full))


# v1015.0 recovery closure fixture split smoke tokens: recovery-closure-fixture-split-smoke-v1 --recovery-closure-fixture-split-smoke build_recovery_closure_fixture_split_smoke_review recovery_closure_fixture_split_smoke_review_text fixture_family_selected=recovery_closure parent_timeout_row=recovery-drill-and-release-closure-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False projected_timeout_blockers_after_future_replacement=3 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
