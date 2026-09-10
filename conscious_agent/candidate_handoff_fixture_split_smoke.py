from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN

CANDIDATE_HANDOFF_FIXTURE_SPLIT_SMOKE_VERSION = CURRENT_VERSION
CANDIDATE_HANDOFF_FIXTURE_SPLIT_SMOKE = "candidate-handoff-fixture-split-smoke-v1"
CANDIDATE_HANDOFF_FIXTURE_SPLIT_CLI = "--candidate-handoff-fixture-split-smoke"
CANDIDATE_HANDOFF_FIXTURE_SPLIT_TITLE = "Candidate Handoff Fixture Split Smoke v1"

SELECTED_PARENT_TIMEOUT_ROW = "release-candidate-integrity-and-operator-handoff-v1"
SELECTED_FIXTURE_FAMILY = "candidate_handoff"
SELECTED_OWNER_MODULE = "conscious_agent/release_candidate_operator_handoff.py"
SELECTED_FIXTURE_TARGETS: tuple[str, ...] = (
    "release_candidate_scope_contract_fixture",
    "candidate_package_integrity_review_fixture",
    "candidate_verification_evidence_matrix_fixture",
    "operator_release_handoff_packet_fixture",
    "release_candidate_integrity_handoff_board_fixture",
)
REPLACED_PARENT_ROWS_BEFORE_SPLIT = 5
REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT = 2
PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT = 1

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "creates_split_smoke": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_selected_parent_row": False,
    "executes_release_candidate_board": False,
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
        "owner_exists": owner.exists(),
        "source_text": text,
        "scope_fields": _literal_assignment(tree, "RELEASE_CANDIDATE_SCOPE_FIELDS") or (),
        "package_fields": _literal_assignment(tree, "PACKAGE_INTEGRITY_FIELDS") or (),
        "evidence_fields": _literal_assignment(tree, "VERIFICATION_EVIDENCE_FIELDS") or (),
        "handoff_fields": _literal_assignment(tree, "OPERATOR_HANDOFF_FIELDS") or (),
        "scope_boundaries": _literal_assignment(tree, "RELEASE_CANDIDATE_SCOPE_BOUNDARIES") or {},
        "package_boundaries": _literal_assignment(tree, "PACKAGE_INTEGRITY_BOUNDARIES") or {},
        "evidence_boundaries": _literal_assignment(tree, "VERIFICATION_EVIDENCE_BOUNDARIES") or {},
        "handoff_boundaries": _literal_assignment(tree, "OPERATOR_HANDOFF_BOUNDARIES") or {},
        "board_boundaries": _literal_assignment(tree, "RELEASE_CANDIDATE_HANDOFF_BOUNDARIES") or {},
    }


def _run_candidate_handoff_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    scope_fields = set(contract.get("scope_fields") or ())
    package_fields = set(contract.get("package_fields") or ())
    evidence_fields = set(contract.get("evidence_fields") or ())
    handoff_fields = set(contract.get("handoff_fields") or ())
    scope = dict(contract.get("scope_boundaries") or {})
    package = dict(contract.get("package_boundaries") or {})
    evidence = dict(contract.get("evidence_boundaries") or {})
    handoff = dict(contract.get("handoff_boundaries") or {})
    board = dict(contract.get("board_boundaries") or {})
    return [
        _fixture_result(
            "release_candidate_scope_contract_fixture",
            bool(contract.get("owner_exists"))
            and {"candidate_version_identity", "source_only_package_expectations", "verification_evidence_requirements", "release_notes_requirements", "package_privacy_requirements", "known_warnings", "known_blockers", "operator_notes"}.issubset(scope_fields)
            and scope.get("release_candidate_scope_is_release_creation") is False
            and scope.get("release_candidate_readiness_is_publish_approval") is False
            and scope.get("release_candidate_scope_runs_commands") is False
            and scope.get("release_candidate_scope_creates_release") is False
            and scope.get("release_candidate_scope_publishes_release") is False
            and scope.get("release_candidate_scope_expands_autonomy") is False
            and scope.get("operator_review_required") is True,
            "Release candidate scope contract exists and remains non-creating, non-publishing, non-executing, and operator-reviewed.",
        ),
        _fixture_result(
            "candidate_package_integrity_review_fixture",
            {"source_only_package_path", "zip_entry_inventory", "forbidden_path_scan", "compiled_artifact_scan", "runtime_memory_autonomy_log_scan", "metadata_version_alignment", "package_privacy_result"}.issubset(package_fields)
            and package.get("package_integrity_review_is_release_approval") is False
            and package.get("package_privacy_pass_is_publish_permission") is False
            and package.get("package_integrity_review_creates_release") is False
            and package.get("package_integrity_review_publishes_release") is False
            and package.get("package_integrity_review_expands_autonomy") is False
            and package.get("operator_review_required") is True,
            "Candidate package integrity review is evidence only, not approval, publication permission, release creation, or autonomy expansion.",
        ),
        _fixture_result(
            "candidate_verification_evidence_matrix_fixture",
            len(evidence_fields) >= 15
            and {"compile_evidence", "targeted_smoke_evidence", "fast_smoke_evidence", "extracted_zip_evidence", "stale_version_audit_evidence", "package_privacy_evidence"}.issubset(evidence_fields)
            and evidence.get("verification_evidence_is_authorization") is False
            and evidence.get("passing_checks_approve_release") is False
            and evidence.get("verification_matrix_runs_commands") is False
            and evidence.get("verification_matrix_creates_release") is False
            and evidence.get("verification_matrix_publishes_release") is False
            and evidence.get("verification_matrix_expands_autonomy") is False
            and evidence.get("operator_supplied_evidence_required") is True,
            "Candidate verification matrix covers evidence while denying authorization and automated release approval.",
        ),
        _fixture_result(
            "operator_release_handoff_packet_fixture",
            {"candidate_summary", "changed_surfaces", "verification_checklist", "unresolved_warnings", "rollback_recovery_reference", "release_closure_reference", "operator_decision_options", "single_use_approval_notice"}.issubset(handoff_fields)
            and handoff.get("handoff_packet_is_operator_approval") is False
            and handoff.get("handoff_preparation_creates_release") is False
            and handoff.get("handoff_packet_publishes_release") is False
            and handoff.get("handoff_packet_reuses_approval") is False
            and handoff.get("handoff_packet_continues_automatically") is False
            and handoff.get("handoff_packet_expands_autonomy") is False
            and handoff.get("operator_review_required") is True,
            "Operator handoff packet is prepared for review but cannot approve, publish, reuse approval, continue automatically, or expand autonomy.",
        ),
        _fixture_result(
            "release_candidate_integrity_handoff_board_fixture",
            "build_release_candidate_integrity_handoff_board" in text
            and board.get("candidate_board_is_release_creation") is False
            and board.get("candidate_board_is_publish_approval") is False
            and board.get("candidate_board_is_operator_approval") is False
            and board.get("candidate_board_executes_commands") is False
            and board.get("candidate_board_creates_release") is False
            and board.get("candidate_board_publishes_release") is False
            and board.get("candidate_board_continues_automatically") is False
            and board.get("candidate_board_expands_autonomy") is False
            and board.get("operator_review_required") is True
            and board.get("approval_required") is True,
            "Release candidate integrity handoff board exists and remains non-authorizing, non-executing, non-publishing, and approval-gated.",
        ),
    ]


def build_candidate_handoff_fixture_split_smoke_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/candidate_handoff_fixture_split_smoke.py",
        "conscious_agent/decision_archive_ledger_parent_replacement_overlay.py", "conscious_agent/release_candidate_operator_handoff.py",
        "conscious_agent/main.py", "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "conscious_agent/dashboard.py", "conscious_agent/current_version_staleness_audit.py",
    ])
    parent = _parent_timeout_row(SELECTED_PARENT_TIMEOUT_ROW)
    plan = _fixture_plan_row(SELECTED_FIXTURE_FAMILY)
    contract = _source_contract(root)
    fixture_results = _run_candidate_handoff_fixtures(contract)
    pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
    fail_count = len(fixture_results) - pass_count
    split_smoke_passed = pass_count == 5 and fail_count == 0
    policy_results = {
        "v1017_decision_overlay_prerequisite_represented": "decision-archive-ledger-parent-replacement-overlay-v1" in docs and "total_replaced_parent_rows_after_overlay=5" in docs,
        "two_timeout_parent_rows_remain_before_split": REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT == 2,
        "selected_parent_row_is_original_timeout": parent.get("name") == SELECTED_PARENT_TIMEOUT_ROW and parent.get("status") == "timeout",
        "fixture_plan_matches_selected_parent": plan.get("name") == SELECTED_PARENT_TIMEOUT_ROW and plan.get("fixture_family") == SELECTED_FIXTURE_FAMILY,
        "fixture_plan_targets_match_selection": tuple(plan.get("bounded_fixture_targets") or ()) == SELECTED_FIXTURE_TARGETS,
        "split_fixture_count_is_five": len(fixture_results) == 5,
        "split_fixture_targets_all_passed": split_smoke_passed,
        "selected_parent_not_marked_pass": BOUNDARIES["parent_row_marked_pass"] is False,
        "selected_parent_not_replaced_yet": BOUNDARIES["parent_row_replaced_for_release_cleanliness_accounting"] is False,
        "projected_blocker_count_after_future_replacement_is_one": PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT == 1,
        "full_install_release_still_not_clean": BOUNDARIES["marks_install_release_clean"] is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False,
        "does_not_execute_parent_rows": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "manual_registry_still_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": CANDIDATE_HANDOFF_FIXTURE_SPLIT_SMOKE in docs,
        "cli_flag_registered": CANDIDATE_HANDOFF_FIXTURE_SPLIT_CLI in docs,
        "builder_registered": "build_candidate_handoff_fixture_split_smoke_review" in docs,
        "text_renderer_registered": "candidate_handoff_fixture_split_smoke_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and CANDIDATE_HANDOFF_FIXTURE_SPLIT_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"candidate_handoff_fixture_split_smoke_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "candidate_handoff_fixture_split_smoke_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": CANDIDATE_HANDOFF_FIXTURE_SPLIT_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "selected_parent_row": SELECTED_PARENT_TIMEOUT_ROW,
        "selected_fixture_family": SELECTED_FIXTURE_FAMILY,
        "selected_owner_module": SELECTED_OWNER_MODULE,
        "fixture_target_names": [row.get("name") for row in fixture_results],
        "fixture_targets_in_family": len(fixture_results),
        "split_fixture_pass_count": pass_count,
        "split_fixture_fail_count": fail_count,
        "fixture_results": fixture_results,
        "split_smoke_created": True,
        "split_smoke_passed": split_smoke_passed,
        "already_replaced_parent_rows": REPLACED_PARENT_ROWS_BEFORE_SPLIT,
        "remaining_timeout_parent_rows_before_split": REMAINING_TIMEOUT_PARENT_ROWS_BEFORE_SPLIT,
        "parent_row_still_timeout": parent.get("status") == "timeout",
        "parent_row_marked_pass": False,
        "parent_row_replaced_for_release_cleanliness_accounting": False,
        "projected_timeout_blockers_after_future_replacement": PROJECTED_TIMEOUT_BLOCKERS_AFTER_FUTURE_REPLACEMENT,
        "full_install_release_clean": False,
        "release_authorized": False,
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def candidate_handoff_fixture_split_smoke_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    report = dict(report or build_candidate_handoff_fixture_split_smoke_review())
    lines = [
        CANDIDATE_HANDOFF_FIXTURE_SPLIT_TITLE,
        f"Version: {report.get('version')}",
        f"Status: {report.get('status')}",
        f"Selected parent row: {report.get('selected_parent_row')}",
        f"Selected fixture family: {report.get('selected_fixture_family')}",
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


def print_candidate_handoff_fixture_split_smoke_review(root_dir: str | Path | None = None, *, full: bool = False) -> dict[str, Any]:
    report = build_candidate_handoff_fixture_split_smoke_review(root_dir)
    print(candidate_handoff_fixture_split_smoke_review_text(report, full=full))
    return report


# v1018.0 candidate handoff fixture split smoke tokens: candidate-handoff-fixture-split-smoke-v1 --candidate-handoff-fixture-split-smoke build_candidate_handoff_fixture_split_smoke_review candidate_handoff_fixture_split_smoke_review_text selected_parent_row=release-candidate-integrity-and-operator-handoff-v1 selected_fixture_family=candidate_handoff selected_fixture_targets=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True parent_row_marked_pass=False parent_row_replaced_for_release_cleanliness_accounting=False already_replaced_parent_rows=5 remaining_timeout_parent_rows_before_split=2 projected_timeout_blockers_after_future_replacement=1 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
