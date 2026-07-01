from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from install_release_timeout_harness import build_install_release_timeout_harness_repair_review
from install_release_timeout_retest import build_install_release_timeout_row_bounded_retest_review

INSTALL_RELEASE_FIXTURE_DECOMPOSITION_VERSION = CURRENT_VERSION
INSTALL_RELEASE_FIXTURE_DECOMPOSITION_SMOKE = "install-release-fixture-decomposition-plan-v1"
INSTALL_RELEASE_FIXTURE_DECOMPOSITION_CLI = "--install-release-fixture-decomposition-plan"
INSTALL_RELEASE_FIXTURE_DECOMPOSITION_TITLE = "Install-Release Fixture Decomposition Plan v1"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_timeout_rows": False,
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

# Each timeout row gets decomposed into smaller evidence fixtures. These are plans for v1006+;
# v1005 intentionally does not claim the seven timeout checks are fixed.
FIXTURE_DECOMPOSITION_PLAN: tuple[dict[str, Any], ...] = (
    {
        "name": "recovery-drill-and-release-closure-v1",
        "owner_module": "conscious_agent/recovery_drill_release_closure.py",
        "fixture_family": "recovery_closure",
        "problem_class": "release_archive_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "recovery_drill_scope_contract_fixture",
            "rollback_decision_review_packet_fixture",
            "release_closure_evidence_board_fixture",
            "operator_closure_approval_gate_fixture",
            "recovery_drill_release_closure_board_fixture",
        ),
        "first_repair_action": "split recovery closure board checks from archive/release closure evidence checks",
    },
    {
        "name": "release-candidate-integrity-and-operator-handoff-v1",
        "owner_module": "conscious_agent/release_candidate_operator_handoff.py",
        "fixture_family": "candidate_handoff",
        "problem_class": "release_candidate_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "release_candidate_scope_contract_fixture",
            "candidate_package_integrity_review_fixture",
            "candidate_verification_evidence_matrix_fixture",
            "operator_release_handoff_packet_fixture",
            "release_candidate_integrity_handoff_board_fixture",
        ),
        "first_repair_action": "split package integrity and operator handoff evidence into separately timed fixtures",
    },
    {
        "name": "release-decision-and-archive-ledger-v1",
        "owner_module": "conscious_agent/release_decision_archive_ledger.py",
        "fixture_family": "decision_archive_ledger",
        "problem_class": "archive_decision_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "release_decision_scope_contract_fixture",
            "operator_decision_option_matrix_fixture",
            "release_archive_ledger_prep_fixture",
            "archive_integrity_continuity_review_fixture",
            "release_decision_archive_ledger_board_fixture",
        ),
        "first_repair_action": "split decision option matrix from archive ledger continuity checks",
    },
    {
        "name": "release-archive-retrieval-and-continuity-index-v1",
        "owner_module": "conscious_agent/release_archive_continuity_index.py",
        "fixture_family": "archive_continuity_index",
        "problem_class": "archive_retrieval_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "archive_retrieval_read_only_fixture",
            "continuity_index_projection_fixture",
            "historical_reference_classification_fixture",
            "stale_current_reference_guard_fixture",
            "retrieval_packet_fixture",
        ),
        "first_repair_action": "split read-only archive retrieval from continuity index projection",
    },
    {
        "name": "release-archive-search-and-handoff-review-v1",
        "owner_module": "conscious_agent/release_archive_search_handoff.py",
        "fixture_family": "archive_search_handoff",
        "problem_class": "archive_search_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "archive_search_scope_contract_fixture",
            "release_record_query_matrix_fixture",
            "archive_search_result_review_packet_fixture",
            "archive_handoff_review_packet_fixture",
            "release_archive_search_handoff_board_fixture",
        ),
        "first_repair_action": "split search result review from handoff packet review",
    },
    {
        "name": "release-archive-export-and-decision-closure-v1",
        "owner_module": "conscious_agent/release_archive_export_closure.py",
        "fixture_family": "archive_export_closure",
        "problem_class": "archive_export_fixture_too_large_or_composite",
        "bounded_fixture_targets": (
            "archive_export_scope_contract_fixture",
            "release_archive_export_packet_prep_fixture",
            "operator_decision_closure_checklist_fixture",
            "archive_export_integrity_review_fixture",
            "release_archive_export_decision_closure_board_fixture",
        ),
        "first_repair_action": "split export packet preparation from operator closure checklist evidence",
    },
    {
        "name": "fast-install-release-isolation-gate-v1",
        "owner_module": "conscious_agent/smoke_registry_pilot.py",
        "fixture_family": "fast_install_release_isolation",
        "problem_class": "segment_isolation_composite_or_cap_mismatch",
        "bounded_fixture_targets": (
            "fast_smoke_isolation_fixture",
            "install_segment_isolation_fixture",
            "release_segment_isolation_fixture",
            "registry_scope_boundary_fixture",
            "json_output_stability_fixture",
        ),
        "first_repair_action": "split fast/install/release segment isolation assertions before raising any timeout cap",
    },
)


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


def _fixture_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {row["name"]: len(row.get("bounded_fixture_targets") or ()) for row in rows}


def build_install_release_fixture_decomposition_plan_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_fixture_decomposition.py",
        "conscious_agent/install_release_timeout_retest.py",
        "conscious_agent/install_release_timeout_harness.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
    ])
    timeout_rows = _timeout_rows()
    timeout_names = {row["name"] for row in timeout_rows}
    plan_rows = [dict(row) for row in FIXTURE_DECOMPOSITION_PLAN]
    plan_names = {row["name"] for row in plan_rows}
    fixture_counts = _fixture_counts(plan_rows)
    harness_report = build_install_release_timeout_harness_repair_review(root)
    # The v1004 retest is intentionally re-used as prerequisite evidence, not as a claim that timeouts are repaired.
    retest_report = build_install_release_timeout_row_bounded_retest_review(root)
    decomposition_queue = [
        {
            "name": row["name"],
            "owner_module": row["owner_module"],
            "fixture_family": row["fixture_family"],
            "problem_class": row["problem_class"],
            "bounded_fixture_count": len(row.get("bounded_fixture_targets") or ()),
            "bounded_fixture_targets": list(row.get("bounded_fixture_targets") or ()),
            "first_repair_action": row["first_repair_action"],
            "next_status": "ready_for_fixture_level_smoke_split",
        }
        for row in plan_rows
    ]
    total_fixture_targets = sum(fixture_counts.values())
    policy_results = {
        "seven_timeout_rows_identified": len(timeout_rows) == 7,
        "decomposition_rows_cover_all_timeout_rows": timeout_names == plan_names,
        "each_timeout_row_has_owner_module": all(bool(row.get("owner_module")) for row in plan_rows),
        "each_timeout_row_has_fixture_family": all(bool(row.get("fixture_family")) for row in plan_rows),
        "each_timeout_row_has_at_least_three_fixture_targets": all(fixture_counts.get(row["name"], 0) >= 3 for row in plan_rows),
        "fixture_targets_are_named": all(all(str(target).endswith("_fixture") for target in row.get("bounded_fixture_targets") or ()) for row in plan_rows),
        "total_fixture_targets_recorded": total_fixture_targets >= 21,
        "v1003_timeout_harness_prerequisite_passed": harness_report.get("ok") is True and harness_report.get("timeout_rows_protected") == 7,
        "v1004_bounded_retest_prerequisite_passed": retest_report.get("ok") is True and retest_report.get("timeout_rows_still_timeout") == 7,
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": INSTALL_RELEASE_FIXTURE_DECOMPOSITION_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_FIXTURE_DECOMPOSITION_CLI in docs,
        "builder_registered": "build_install_release_fixture_smoke_split_pilot_review" in docs,
        "text_renderer_registered": "install_release_fixture_smoke_split_pilot_review_text" in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_fixture_decomposition_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_fixture_decomposition_plan_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_FIXTURE_DECOMPOSITION_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "decomposition_mode": "review_only_fixture_split_plan",
        "timeout_rows_total": len(timeout_rows),
        "timeout_rows_planned": len(plan_rows),
        "timeout_rows_still_timeout": retest_report.get("timeout_rows_still_timeout"),
        "fixture_targets_total": total_fixture_targets,
        "fixture_counts_by_row": fixture_counts,
        "decomposition_queue": decomposition_queue,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_timeout_rows_are_split_into_fixture_level_smokes_and_supervised_blockers_are_reclassified",
        "prerequisite_reports": {
            "timeout_harness_status": harness_report.get("status"),
            "timeout_harness_ok": harness_report.get("ok"),
            "bounded_retest_status": retest_report.get("status"),
            "bounded_retest_ok": retest_report.get("ok"),
            "bounded_retest_still_timeout": retest_report.get("timeout_rows_still_timeout"),
        },
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_fixture_decomposition_plan_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Fixture Decomposition Plan report not found."
    lines = [
        "# Install-Release Fixture Decomposition Plan",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Timeout rows total: {report.get('timeout_rows_total')}",
        f"Timeout rows planned: {report.get('timeout_rows_planned')}",
        f"Timeout rows still timeout: {report.get('timeout_rows_still_timeout')}",
        f"Fixture targets total: {report.get('fixture_targets_total')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Decomposition queue"])
        for row in report.get("decomposition_queue") or []:
            lines.append(f"- {row.get('name')}: {row.get('bounded_fixture_count')} fixtures, owner={row.get('owner_module')}, next={row.get('first_repair_action')}")
        lines.extend(["", "## Prerequisite reports"])
        for key, value in (report.get("prerequisite_reports") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_fixture_decomposition_plan_review(full: bool = False) -> None:
    print(install_release_fixture_smoke_split_pilot_review_text(build_install_release_fixture_smoke_split_pilot_review(), full=full))
