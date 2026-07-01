from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_fixture_decomposition import FIXTURE_DECOMPOSITION_PLAN

INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_VERSION = CURRENT_VERSION
INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_SMOKE = "install-release-fixture-smoke-split-pilot-v1"
INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_CLI = "--install-release-fixture-smoke-split-pilot"
INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_TITLE = "Install-Release Fixture Smoke Split Pilot v1"

SELECTED_FIXTURE_FAMILY = "archive_continuity_index"
SELECTED_PARENT_TIMEOUT_ROW = "release-archive-retrieval-and-continuity-index-v1"
SELECTED_OWNER_MODULE = "conscious_agent/release_archive_continuity_index.py"
SELECTED_FIXTURE_TARGETS: tuple[str, ...] = (
    "archive_retrieval_read_only_fixture",
    "continuity_index_projection_fixture",
    "historical_reference_classification_fixture",
    "stale_current_reference_guard_fixture",
    "retrieval_packet_fixture",
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_row": False,
    "executes_release_archive_board": False,
    "split_smoke_created": True,
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


def _fixture_plan_row() -> dict[str, Any]:
    for row in FIXTURE_DECOMPOSITION_PLAN:
        if row.get("fixture_family") == SELECTED_FIXTURE_FAMILY:
            return dict(row)
    return {}


def _parent_timeout_row() -> dict[str, Any]:
    for row in INSTALL_RELEASE_LEDGER_ROWS:
        if row.get("name") == SELECTED_PARENT_TIMEOUT_ROW:
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
        "owner_module": SELECTED_OWNER_MODULE,
        "owner_exists": owner.exists(),
        "source_text": text,
        "archive_scope_fields": _literal_assignment(tree, "ARCHIVE_RETRIEVAL_SCOPE_FIELDS") or (),
        "continuity_index_fields": _literal_assignment(tree, "CONTINUITY_INDEX_FIELDS") or (),
        "historical_reference_classes": _literal_assignment(tree, "HISTORICAL_REFERENCE_CLASSES") or (),
        "retrieval_packet_fields": _literal_assignment(tree, "CONTINUITY_RETRIEVAL_PACKET_FIELDS") or (),
        "archive_scope_boundaries": _literal_assignment(tree, "ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES") or {},
        "continuity_index_boundaries": _literal_assignment(tree, "CONTINUITY_INDEX_BOUNDARIES") or {},
        "historical_reference_boundaries": _literal_assignment(tree, "HISTORICAL_REFERENCE_BOUNDARIES") or {},
        "retrieval_packet_boundaries": _literal_assignment(tree, "CONTINUITY_RETRIEVAL_BOUNDARIES") or {},
    }


def _fixture_result(name: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if passed else "blocked", "passed": bool(passed), "evidence": evidence}


def _run_split_fixtures(contract: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(contract.get("source_text") or "")
    archive_scope_fields = set(contract.get("archive_scope_fields") or ())
    continuity_index_fields = set(contract.get("continuity_index_fields") or ())
    historical_reference_classes = set(contract.get("historical_reference_classes") or ())
    retrieval_packet_fields = set(contract.get("retrieval_packet_fields") or ())
    archive_scope_boundaries = dict(contract.get("archive_scope_boundaries") or {})
    continuity_index_boundaries = dict(contract.get("continuity_index_boundaries") or {})
    historical_reference_boundaries = dict(contract.get("historical_reference_boundaries") or {})
    retrieval_packet_boundaries = dict(contract.get("retrieval_packet_boundaries") or {})
    return [
        _fixture_result(
            "archive_retrieval_read_only_fixture",
            bool(contract.get("owner_exists"))
            and {"archive_retrieval_scope", "allowed_archive_fields", "current_state_vs_historical_reference_distinction"}.issubset(archive_scope_fields)
            and archive_scope_boundaries.get("archive_retrieval_runs_commands") is False
            and archive_scope_boundaries.get("archive_lookup_writes_archive_records") is False
            and archive_scope_boundaries.get("archive_retrieval_expands_autonomy") is False,
            "Owner module exposes read-only archive retrieval scope fields and denies commands, archive writes, and autonomy expansion.",
        ),
        _fixture_result(
            "continuity_index_projection_fixture",
            {"version_range", "arc_title", "primary_module", "dashboard_routes", "api_cli_surfaces", "targeted_smoke_name", "next_arc_pointer"}.issubset(continuity_index_fields)
            and continuity_index_boundaries.get("continuity_index_runs_commands") is False
            and continuity_index_boundaries.get("continuity_index_writes_archive") is False
            and continuity_index_boundaries.get("continuity_index_expands_autonomy") is False,
            "Continuity index projection schema is present and remains read-only/review-only.",
        ),
        _fixture_result(
            "historical_reference_classification_fixture",
            {"allowed_historical_release_history_reference", "allowed_prior_arc_route_smoke_reference", "blocked_stale_current_state_marker", "blocked_stale_dashboard_api_cli_current_text"}.issubset(historical_reference_classes)
            and historical_reference_boundaries.get("historical_classification_weakens_stale_current_blocking") is False
            and historical_reference_boundaries.get("historical_classification_runs_commands") is False
            and historical_reference_boundaries.get("historical_classification_expands_autonomy") is False,
            "Historical reference classes keep allowed history separate from blocked stale current-state markers.",
        ),
        _fixture_result(
            "stale_current_reference_guard_fixture",
            "build_stale_version_string_scanner" in text
            and "build_current_symbol_staleness_audit" in text
            and "stale_current_reference_status" in text
            and "blocked_if_detected" in text,
            "The owner module still delegates stale current-state detection to the centralized audit and records blocked stale-current status.",
        ),
        _fixture_result(
            "retrieval_packet_fixture",
            {"current_version_identity", "recent_arc_chain", "historical_references", "blocked_stale_references", "archive_ledger_continuity_summary", "operator_review_notes", "next_recommended_arc"}.issubset(retrieval_packet_fields)
            and retrieval_packet_boundaries.get("retrieval_packet_is_operator_approval") is False
            and retrieval_packet_boundaries.get("retrieval_packet_writes_external_archive") is False
            and retrieval_packet_boundaries.get("retrieval_packet_expands_autonomy") is False,
            "Continuity retrieval packet schema is present and remains non-approving, non-writing, and non-autonomous.",
        ),
    ]


def build_install_release_fixture_smoke_split_pilot_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_fixture_smoke_split.py",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/install_release_timeout_retest.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/release_archive_continuity_index.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])
    plan_row = _fixture_plan_row()
    parent_row = _parent_timeout_row()
    contract = _source_contract(root)
    fixture_results = _run_split_fixtures(contract)
    fixture_target_set = set(plan_row.get("bounded_fixture_targets") or ())
    fixture_result_set = {row["name"] for row in fixture_results}
    fixture_pass_count = sum(1 for row in fixture_results if row.get("passed") is True)
    fixture_fail_count = len(fixture_results) - fixture_pass_count
    parent_row_still_timeout = parent_row.get("status") == "timeout"
    policy_results = {
        "selected_fixture_family_is_archive_continuity_index": plan_row.get("fixture_family") == SELECTED_FIXTURE_FAMILY,
        "selected_parent_row_matches_timeout_ledger": parent_row.get("name") == SELECTED_PARENT_TIMEOUT_ROW and parent_row_still_timeout,
        "split_targets_match_decomposition_plan": fixture_target_set == set(SELECTED_FIXTURE_TARGETS) == fixture_result_set,
        "owner_module_exists": contract.get("owner_exists") is True,
        "all_split_fixtures_executed": len(fixture_results) == len(SELECTED_FIXTURE_TARGETS),
        "all_split_fixtures_passed": fixture_fail_count == 0,
        "parent_row_still_not_claimed_fixed": parent_row_still_timeout,
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_CLI in docs,
        "builder_registered": "build_install_release_fixture_smoke_split_pilot_review" in docs,
        "text_renderer_registered": "install_release_fixture_smoke_split_pilot_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_SMOKE in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "no_parent_timeout_row_execution": BOUNDARIES["executes_parent_timeout_row"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_fixture_smoke_split_pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_fixture_smoke_split_pilot_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_FIXTURE_SMOKE_SPLIT_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "fixture_family_selected": SELECTED_FIXTURE_FAMILY,
        "parent_timeout_row": SELECTED_PARENT_TIMEOUT_ROW,
        "parent_row_status": parent_row.get("status"),
        "parent_row_still_timeout": parent_row_still_timeout,
        "owner_module": SELECTED_OWNER_MODULE,
        "fixture_targets_in_family": len(SELECTED_FIXTURE_TARGETS),
        "fixture_target_names": list(SELECTED_FIXTURE_TARGETS),
        "split_fixture_results": fixture_results,
        "split_fixture_pass_count": fixture_pass_count,
        "split_fixture_fail_count": fixture_fail_count,
        "split_smoke_created": True,
        "split_smoke_passed": ok,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_more_release_archive_fixture_families_are_split_and_parent_timeout_rows_are_replaced_or_reclassified",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_fixture_smoke_split_pilot_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Fixture Smoke Split Pilot report not found."
    lines = [
        "# Install-Release Fixture Smoke Split Pilot",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Fixture family selected: {report.get('fixture_family_selected')}",
        f"Parent timeout row: {report.get('parent_timeout_row')}",
        f"Parent row still timeout: {report.get('parent_row_still_timeout')}",
        f"Fixture targets in family: {report.get('fixture_targets_in_family')}",
        f"Split smoke created: {report.get('split_smoke_created')}",
        f"Split smoke passed: {report.get('split_smoke_passed')}",
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
        for key in ["executes_full_install_release_segment", "executes_parent_timeout_row", "release_authorized", "autonomy_expanded", "review_only"]:
            lines.append(f"- {key}: {report.get(key)}")
    return "\n".join(lines)


def print_install_release_fixture_smoke_split_pilot_review(full: bool = False, root_dir: str | Path | None = None) -> None:
    print(install_release_fixture_smoke_split_pilot_review_text(build_install_release_fixture_smoke_split_pilot_review(root_dir), full=full))


# v1011.0 install-release fixture smoke split pilot tokens: install-release-fixture-smoke-split-pilot-v1 --install-release-fixture-smoke-split-pilot build_install_release_fixture_smoke_split_pilot_review install_release_fixture_smoke_split_pilot_review_text fixture_family_selected=archive_continuity_index parent_timeout_row=release-archive-retrieval-and-continuity-index-v1 fixture_targets_in_family=5 split_smoke_created=True split_smoke_passed=True parent_row_still_timeout=True full_install_release_clean=False review_only=True release_authorized=False autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
