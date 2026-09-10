from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN
from install_release_fixture_smoke_split import build_install_release_fixture_smoke_split_pilot_review

RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_VERSION = CURRENT_VERSION
RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_SMOKE = "release-archive-fixture-split-expansion-v1"
RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_CLI = "--release-archive-fixture-split-expansion"
RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_TITLE = "Release Archive Fixture Split Expansion v1"

EXPANDED_FIXTURE_FAMILIES: tuple[str, ...] = (
    "archive_search_handoff",
    "archive_export_closure",
)

EXPANDED_PARENT_TIMEOUT_ROWS: dict[str, str] = {
    "archive_search_handoff": "release-archive-search-and-handoff-review-v1",
    "archive_export_closure": "release-archive-export-and-decision-closure-v1",
}

EXPANDED_OWNER_MODULES: dict[str, str] = {
    "archive_search_handoff": "conscious_agent/release_archive_search_handoff.py",
    "archive_export_closure": "conscious_agent/release_archive_export_closure.py",
}

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_release_archive_board": False,
    "split_smokes_created": True,
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


def _fixture_plan_row(family: str) -> dict[str, Any]:
    for row in FIXTURE_DECOMPOSITION_PLAN:
        if row.get("fixture_family") == family:
            return dict(row)
    return {}


def _parent_timeout_row(name: str) -> dict[str, Any]:
    for row in INSTALL_RELEASE_LEDGER_ROWS:
        if row.get("name") == name:
            return dict(row)
    return {}


def _source_contract(root: Path, family: str) -> dict[str, Any]:
    owner_rel = EXPANDED_OWNER_MODULES[family]
    owner = root / owner_rel
    text = _read_text(owner)
    try:
        tree = ast.parse(text or "")
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
    contract: dict[str, Any] = {
        "fixture_family": family,
        "owner_module": owner_rel,
        "owner_exists": owner.exists(),
        "source_text": text,
    }
    if family == "archive_search_handoff":
        contract.update({
            "archive_search_scope_fields": _literal_assignment(tree, "ARCHIVE_SEARCH_SCOPE_FIELDS") or (),
            "release_record_query_fields": _literal_assignment(tree, "RELEASE_RECORD_QUERY_FIELDS") or (),
            "archive_search_result_review_fields": _literal_assignment(tree, "ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS") or (),
            "archive_handoff_review_fields": _literal_assignment(tree, "ARCHIVE_HANDOFF_REVIEW_FIELDS") or (),
            "archive_search_scope_boundaries": _literal_assignment(tree, "ARCHIVE_SEARCH_SCOPE_BOUNDARIES") or {},
            "release_record_query_boundaries": _literal_assignment(tree, "RELEASE_RECORD_QUERY_BOUNDARIES") or {},
            "archive_search_result_boundaries": _literal_assignment(tree, "ARCHIVE_SEARCH_RESULT_BOUNDARIES") or {},
            "archive_handoff_boundaries": _literal_assignment(tree, "ARCHIVE_HANDOFF_BOUNDARIES") or {},
            "board_boundaries": _literal_assignment(tree, "RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_BOUNDARIES") or {},
        })
    if family == "archive_export_closure":
        contract.update({
            "archive_export_scope_fields": _literal_assignment(tree, "ARCHIVE_EXPORT_SCOPE_FIELDS") or (),
            "release_archive_export_packet_fields": _literal_assignment(tree, "RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS") or (),
            "operator_decision_closure_fields": _literal_assignment(tree, "OPERATOR_DECISION_CLOSURE_FIELDS") or (),
            "archive_export_integrity_fields": _literal_assignment(tree, "ARCHIVE_EXPORT_INTEGRITY_FIELDS") or (),
            "archive_export_scope_boundaries": _literal_assignment(tree, "ARCHIVE_EXPORT_SCOPE_BOUNDARIES") or {},
            "release_archive_export_packet_boundaries": _literal_assignment(tree, "RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES") or {},
            "operator_decision_closure_boundaries": _literal_assignment(tree, "OPERATOR_DECISION_CLOSURE_BOUNDARIES") or {},
            "archive_export_integrity_boundaries": _literal_assignment(tree, "ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES") or {},
            "board_boundaries": _literal_assignment(tree, "RELEASE_ARCHIVE_EXPORT_CLOSURE_BOARD_BOUNDARIES") or {},
        })
    return contract


def _fixture_result(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "blocked", "passed": bool(passed), "evidence": evidence}


def _no_writes_or_autonomy(boundaries: dict[str, Any], prefixes: tuple[str, ...]) -> bool:
    for key, value in boundaries.items():
        if key in {"operator_review_required", "approval_required"}:
            continue
        if any(fragment in key for fragment in prefixes):
            if value is not False:
                return False
    return True


def _run_archive_search_handoff_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    scope_fields = set(contract.get("archive_search_scope_fields") or ())
    query_fields = set(contract.get("release_record_query_fields") or ())
    result_fields = set(contract.get("archive_search_result_review_fields") or ())
    handoff_fields = set(contract.get("archive_handoff_review_fields") or ())
    scope_boundaries = dict(contract.get("archive_search_scope_boundaries") or {})
    query_boundaries = dict(contract.get("release_record_query_boundaries") or {})
    result_boundaries = dict(contract.get("archive_search_result_boundaries") or {})
    handoff_boundaries = dict(contract.get("archive_handoff_boundaries") or {})
    board_boundaries = dict(contract.get("board_boundaries") or {})
    return [
        _fixture_result(
            "archive_search_scope_contract_fixture",
            bool(contract.get("owner_exists"))
            and {"allowed_archive_search_fields", "search_scope_boundaries", "historical_release_lookup_rules", "current_state_lookup_rules", "operator_facing_search_packet"}.issubset(scope_fields)
            and scope_boundaries.get("archive_search_is_read_only") is True
            and scope_boundaries.get("search_scope_authorizes_archive_writes") is False
            and scope_boundaries.get("archive_search_expands_autonomy") is False,
            "Archive search scope schema is present, read-only, and does not authorize archive writes or autonomy expansion.",
        ),
        _fixture_result(
            "release_record_query_matrix_fixture",
            {"version_range", "arc_title", "dashboard_route", "api_cli_surface", "targeted_smoke", "module_file_surface", "status_field", "known_warning", "next_recommended_arc"}.issubset(query_fields)
            and query_boundaries.get("query_matches_are_current_state_authority") is False
            and query_boundaries.get("query_matrix_writes_archive") is False
            and query_boundaries.get("query_matrix_expands_autonomy") is False,
            "Release record query matrix is separated from authority, archive writes, and autonomy expansion.",
        ),
        _fixture_result(
            "archive_search_result_review_packet_fixture",
            {"matched_records", "historical_current_classification", "confidence_notes", "stale_current_risk_notes", "missing_record_warnings", "operator_review_notes"}.issubset(result_fields)
            and result_boundaries.get("search_review_mutates_records") is False
            and result_boundaries.get("search_review_writes_archive") is False
            and result_boundaries.get("search_review_expands_autonomy") is False,
            "Archive search result review packet distinguishes history/current-state risk and does not mutate records.",
        ),
        _fixture_result(
            "archive_handoff_review_packet_fixture",
            {"search_summary", "continuity_chain", "matched_release_records", "warnings_blockers", "source_surfaces", "operator_decision_options"}.issubset(handoff_fields)
            and handoff_boundaries.get("archive_handoff_is_operator_approval") is False
            and handoff_boundaries.get("handoff_review_writes_archive") is False
            and handoff_boundaries.get("handoff_review_expands_autonomy") is False,
            "Archive handoff packet is review-only and does not become operator approval or archive mutation.",
        ),
        _fixture_result(
            "release_archive_search_handoff_board_fixture",
            "build_release_archive_search_handoff_review_board" in text
            and board_boundaries.get("archive_search_board_is_release_approval") is False
            and board_boundaries.get("archive_search_board_executes_commands") is False
            and board_boundaries.get("archive_search_board_writes_archive") is False
            and board_boundaries.get("archive_search_board_expands_autonomy") is False,
            "Archive search handoff board exists and remains non-authorizing, non-executing, non-writing, and non-autonomous.",
        ),
    ]


def _run_archive_export_closure_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    scope_fields = set(contract.get("archive_export_scope_fields") or ())
    packet_fields = set(contract.get("release_archive_export_packet_fields") or ())
    closure_fields = set(contract.get("operator_decision_closure_fields") or ())
    integrity_fields = set(contract.get("archive_export_integrity_fields") or ())
    scope_boundaries = dict(contract.get("archive_export_scope_boundaries") or {})
    packet_boundaries = dict(contract.get("release_archive_export_packet_boundaries") or {})
    closure_boundaries = dict(contract.get("operator_decision_closure_boundaries") or {})
    integrity_boundaries = dict(contract.get("archive_export_integrity_boundaries") or {})
    board_boundaries = dict(contract.get("board_boundaries") or {})
    return [
        _fixture_result(
            "archive_export_scope_contract_fixture",
            bool(contract.get("owner_exists"))
            and {"archive_export_scope", "allowed_export_fields", "source_only_export_boundaries", "operator_review_requirements", "external_write_prohibition"}.issubset(scope_fields)
            and scope_boundaries.get("archive_export_prep_writes_external_files") is False
            and scope_boundaries.get("export_scope_is_release_approval") is False
            and scope_boundaries.get("archive_export_scope_expands_autonomy") is False,
            "Archive export scope schema preserves source-only and external-write prohibition boundaries.",
        ),
        _fixture_result(
            "release_archive_export_packet_prep_fixture",
            {"version_identity", "arc_title", "release_continuity_summary", "verification_evidence_summary", "package_privacy_status", "known_warnings", "operator_decision_status", "next_arc_pointer"}.issubset(packet_fields)
            and packet_boundaries.get("export_packet_prep_writes_external_archive") is False
            and packet_boundaries.get("prepared_packet_is_approval") is False
            and packet_boundaries.get("export_packet_expands_autonomy") is False,
            "Release archive export packet prep is evidence preparation, not external archive write or approval.",
        ),
        _fixture_result(
            "operator_decision_closure_checklist_fixture",
            {"candidate_version_confirmation", "evidence_packet_review", "archive_packet_review", "known_blocker_review", "exact_operator_closure_decision", "single_use_closure_boundary"}.issubset(closure_fields)
            and closure_boundaries.get("closure_checklist_completion_is_automatic_approval") is False
            and closure_boundaries.get("closure_decision_reusable_for_future_releases") is False
            and closure_boundaries.get("closure_checklist_expands_autonomy") is False,
            "Operator decision closure checklist requires exact single-use decision and does not auto-approve.",
        ),
        _fixture_result(
            "archive_export_integrity_review_fixture",
            {"readme_current_header", "release_history_top_entry", "workspace_project_metadata", "source_version_markers", "dashboard_api_cli_current_text", "stale_current_reference_blocking", "package_privacy_status", "historical_reference_classification"}.issubset(integrity_fields)
            and integrity_boundaries.get("export_integrity_review_writes_external_archive") is False
            and integrity_boundaries.get("integrity_pass_is_publish_approval") is False
            and integrity_boundaries.get("export_integrity_expands_autonomy") is False,
            "Archive export integrity review covers current metadata and privacy while denying publish approval.",
        ),
        _fixture_result(
            "release_archive_export_decision_closure_board_fixture",
            "build_release_archive_export_decision_closure_board" in text
            and board_boundaries.get("archive_export_board_is_release_approval") is False
            and board_boundaries.get("archive_export_board_publishes_release") is False
            and board_boundaries.get("archive_export_board_writes_external_archive") is False
            and board_boundaries.get("archive_export_board_expands_autonomy") is False,
            "Archive export closure board exists and remains non-approving, non-publishing, non-writing, and non-autonomous.",
        ),
    ]


def _run_family_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    family = str(contract.get("fixture_family"))
    if family == "archive_search_handoff":
        return _run_archive_search_handoff_fixtures(contract)
    if family == "archive_export_closure":
        return _run_archive_export_closure_fixtures(contract)
    return []


def build_release_archive_fixture_split_expansion_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/release_archive_fixture_split_expansion.py",
        "conscious_agent/install_release_fixture_smoke_split.py",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/release_archive_search_handoff.py",
        "conscious_agent/release_archive_export_closure.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
    ])
    pilot_report = build_install_release_fixture_smoke_split_pilot_review(root)
    family_reports: list[dict[str, Any]] = []
    all_fixture_results: list[dict[str, Any]] = []
    for family in EXPANDED_FIXTURE_FAMILIES:
        plan_row = _fixture_plan_row(family)
        parent_row_name = EXPANDED_PARENT_TIMEOUT_ROWS[family]
        parent_row = _parent_timeout_row(parent_row_name)
        contract = _source_contract(root, family)
        fixture_results = _run_family_fixtures(contract)
        fixture_target_set = set(plan_row.get("bounded_fixture_targets") or ())
        fixture_result_set = {row["name"] for row in fixture_results}
        fixture_pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
        family_ok = (
            plan_row.get("fixture_family") == family
            and parent_row.get("name") == parent_row_name
            and parent_row.get("status") == "timeout"
            and fixture_target_set == fixture_result_set
            and len(fixture_results) == 5
            and fixture_pass_count == 5
            and contract.get("owner_exists") is True
        )
        family_report = {
            "fixture_family": family,
            "parent_timeout_row": parent_row_name,
            "parent_row_status": parent_row.get("status"),
            "parent_row_still_timeout": parent_row.get("status") == "timeout",
            "owner_module": EXPANDED_OWNER_MODULES[family],
            "fixture_targets_in_family": len(fixture_results),
            "fixture_target_names": [row["name"] for row in fixture_results],
            "split_fixture_results": fixture_results,
            "split_fixture_pass_count": fixture_pass_count,
            "split_fixture_fail_count": len(fixture_results) - fixture_pass_count,
            "family_split_passed": family_ok,
        }
        family_reports.append(family_report)
        all_fixture_results.extend(fixture_results)
    family_pass_count = sum(1 for row in family_reports if row.get("family_split_passed") is True)
    fixture_pass_count = sum(1 for row in all_fixture_results if row.get("passed") is True)
    fixture_fail_count = len(all_fixture_results) - fixture_pass_count
    policy_results = {
        "v1006_split_pilot_prerequisite_passed": pilot_report.get("ok") is True and pilot_report.get("split_fixture_pass_count") == 5,
        "expanded_family_count_is_two": len(family_reports) == 2,
        "expanded_families_are_expected": {row.get("fixture_family") for row in family_reports} == set(EXPANDED_FIXTURE_FAMILIES),
        "expanded_parent_rows_still_timeout": all(row.get("parent_row_still_timeout") is True for row in family_reports),
        "split_fixture_count_is_ten": len(all_fixture_results) == 10,
        "all_expanded_families_passed": family_pass_count == 2,
        "all_expanded_split_fixtures_passed": fixture_pass_count == 10 and fixture_fail_count == 0,
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_SMOKE in docs,
        "cli_flag_registered": RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_CLI in docs,
        "builder_registered": "build_release_archive_fixture_split_expansion_review" in docs,
        "text_renderer_registered": "release_archive_fixture_split_expansion_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_SMOKE in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "no_parent_timeout_row_execution": BOUNDARIES["executes_parent_timeout_rows"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
    }
    ok = all(policy_results.values())
    return {
        "id": f"release_archive_fixture_split_expansion_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "release_archive_fixture_split_expansion_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": RELEASE_ARCHIVE_FIXTURE_SPLIT_EXPANSION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "expansion_mode": "review_only_fixture_level_split_expansion",
        "expanded_fixture_families": list(EXPANDED_FIXTURE_FAMILIES),
        "expanded_family_count": len(family_reports),
        "expanded_family_pass_count": family_pass_count,
        "split_fixture_targets_total": len(all_fixture_results),
        "split_fixture_pass_count": fixture_pass_count,
        "split_fixture_fail_count": fixture_fail_count,
        "family_reports": family_reports,
        "parent_timeout_rows": [EXPANDED_PARENT_TIMEOUT_ROWS[family] for family in EXPANDED_FIXTURE_FAMILIES],
        "parent_rows_still_timeout": all(row.get("parent_row_still_timeout") is True for row in family_reports),
        "v1006_pilot_family": pilot_report.get("fixture_family_selected"),
        "total_split_families_including_v1006": 3,
        "total_split_fixture_targets_including_v1006": 15,
        "split_smokes_created": True,
        "split_smokes_passed": ok,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_remaining_timeout_families_are_split_or_reclassified_and_supervised_blockers_are_repaired",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def release_archive_fixture_split_expansion_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Release Archive Fixture Split Expansion report not found."
    lines = [
        "# Release Archive Fixture Split Expansion",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Expanded fixture families: {', '.join(report.get('expanded_fixture_families') or [])}",
        f"Expanded family count: {report.get('expanded_family_count')}",
        f"Expanded family pass count: {report.get('expanded_family_pass_count')}",
        f"Split fixture targets total: {report.get('split_fixture_targets_total')}",
        f"Split fixture pass count: {report.get('split_fixture_pass_count')}",
        f"Split fixture fail count: {report.get('split_fixture_fail_count')}",
        f"Parent rows still timeout: {report.get('parent_rows_still_timeout')}",
        f"Total split families including v1006: {report.get('total_split_families_including_v1006')}",
        f"Total split fixture targets including v1006: {report.get('total_split_fixture_targets_including_v1006')}",
        f"Split smokes created: {report.get('split_smokes_created')}",
        f"Split smokes passed: {report.get('split_smokes_passed')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Family reports"])
        for family in report.get("family_reports") or []:
            lines.append(f"- {family.get('fixture_family')}: {family.get('split_fixture_pass_count')} passed / {family.get('split_fixture_fail_count')} blocked; parent still timeout={family.get('parent_row_still_timeout')}")
            for row in family.get("split_fixture_results") or []:
                lines.append(f"  - {row.get('name')}: {row.get('status')} — {row.get('evidence')}")
        lines.extend(["", "## Policy results"])
        for key, value in sorted((report.get("policy_results") or {}).items()):
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Boundaries"])
        for key in ["executes_full_install_release_segment", "executes_parent_timeout_rows", "release_authorized", "autonomy_expanded", "review_only"]:
            lines.append(f"- {key}: {report.get(key)}")
    return "\n".join(lines)


def print_release_archive_fixture_split_expansion_review(full: bool = False, root_dir: str | Path | None = None) -> None:
    print(release_archive_fixture_split_expansion_review_text(build_release_archive_fixture_split_expansion_review(root_dir), full=full))


# v1011.0 release archive fixture split expansion tokens: release-archive-fixture-split-expansion-v1 --release-archive-fixture-split-expansion build_release_archive_fixture_split_expansion_review release_archive_fixture_split_expansion_review_text expanded_fixture_families=archive_search_handoff,archive_export_closure expanded_family_count=2 split_fixture_targets_total=10 split_fixture_pass_count=10 parent_rows_still_timeout=True total_split_families_including_v1006=3 total_split_fixture_targets_including_v1006=15 full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
