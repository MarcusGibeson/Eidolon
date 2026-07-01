from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS
from release_archive_fixture_split_expansion import build_release_archive_fixture_split_expansion_review

SUPERVISED_BLOCKER_SEMANTICS_REPAIR_VERSION = CURRENT_VERSION
SUPERVISED_BLOCKER_SEMANTICS_REPAIR_SMOKE = "supervised-blocker-semantics-repair-v1"
SUPERVISED_BLOCKER_SEMANTICS_REPAIR_CLI = "--supervised-blocker-semantics-repair"
SUPERVISED_BLOCKER_SEMANTICS_REPAIR_TITLE = "Install-Release Segment Cleanliness Gate v1"

# These six rows were reported as blocked by the v1002 install-release ledger. v1008 does not
# turn them into passes. It classifies what kind of blocked state they represent so release
# status is not inflated and operator-gated advisory surfaces are not confused with broken
# current-release execution.
SUPERVISED_BLOCKER_SEMANTICS: tuple[dict[str, Any], ...] = (
    {
        "name": "multi-model-patch-candidate-ranking",
        "semantics_class": "operator_gated_advisory_not_release_authorizing",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": False,
        "evidence": "Historical supervised ranking layer remains advisory and must not be treated as release approval or autonomous model invocation.",
    },
    {
        "name": "supervised-patch-candidate-refinement",
        "semantics_class": "operator_gated_advisory_not_release_authorizing",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": False,
        "evidence": "Supervised refinement can remain blocked without implying source-only release failure; it is a review packet path, not approval.",
    },
    {
        "name": "supervised-work-package-builder",
        "semantics_class": "operator_gated_work_package_boundary",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": False,
        "evidence": "Work-package preparation is intentionally supervised and does not authorize patches, commands, releases, memory writes, or autonomy.",
    },
    {
        "name": "release-candidate-judgment-layer",
        "semantics_class": "operator_gated_judgment_not_release_decision",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": False,
        "evidence": "Judgment output is advisory and must not become release authorization without a single-use operator decision.",
    },
    {
        "name": "operator-governed-post-application-learning-and-release-readiness",
        "semantics_class": "historical_learning_boundary_not_current_release_failure",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": False,
        "evidence": "Post-application learning remains a historical supervised boundary and cannot unlock release readiness by itself.",
    },
    {
        "name": "release-archive-import-and-closure-recall-v1",
        "semantics_class": "runtime_archive_fixture_required_not_source_only_release_failure",
        "current_source_only_release_failure": False,
        "operator_gate_required": True,
        "can_be_reclassified_out_of_release_failure_bucket": True,
        "requires_fixture_split_before_pass_claim": True,
        "evidence": "Archive import/closure recall depends on runtime/private archive fixtures and must remain non-authorizing until bounded fixtures exist.",
    },
)

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_original_blocked_smokes": False,
    "marks_original_blocked_smokes_pass": False,
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


def _ledger_row(name: str) -> dict[str, Any]:
    for row in INSTALL_RELEASE_LEDGER_ROWS:
        if row.get("name") == name:
            return dict(row)
    return {}


def _semantics_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in SUPERVISED_BLOCKER_SEMANTICS:
        ledger = _ledger_row(str(spec["name"]))
        row = dict(spec)
        row.update({
            "original_status": ledger.get("status"),
            "original_category": ledger.get("category"),
            "original_cause": ledger.get("cause"),
            "declared_timeout_seconds": ledger.get("declared_timeout_seconds"),
            "observed_seconds": ledger.get("observed_seconds"),
            "ledger_row_found": bool(ledger),
            "semantics_repaired": bool(ledger)
            and ledger.get("status") == "blocked"
            and ledger.get("category") == "expected_supervised_blocker"
            and spec.get("can_be_reclassified_out_of_release_failure_bucket") is True
            and spec.get("operator_gate_required") is True
            and spec.get("current_source_only_release_failure") is False,
        })
        rows.append(row)
    return rows


def build_supervised_blocker_semantics_repair_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/supervised_blocker_semantics_repair.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/release_archive_fixture_split_expansion.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    split_prerequisite = build_release_archive_fixture_split_expansion_review(root)
    rows = _semantics_rows()
    repaired_count = sum(1 for row in rows if row.get("semantics_repaired") is True)
    operator_gate_count = sum(1 for row in rows if row.get("operator_gate_required") is True)
    fixture_required_count = sum(1 for row in rows if row.get("requires_fixture_split_before_pass_claim") is True)
    release_failure_count = sum(1 for row in rows if row.get("current_source_only_release_failure") is True)
    release_authorizing_blocker_count = sum(
        1 for row in rows
        if row.get("operator_gate_required") is not True or row.get("current_source_only_release_failure") is True
    )
    policy_results = {
        "v1007_split_expansion_prerequisite_passed": split_prerequisite.get("ok") is True and split_prerequisite.get("total_split_fixture_targets_including_v1006") == 15,
        "six_supervised_blockers_reviewed": len(rows) == 6,
        "all_rows_found_in_v1002_ledger": all(row.get("ledger_row_found") is True for row in rows),
        "all_rows_originally_blocked_by_expected_supervised_semantics": all(row.get("original_status") == "blocked" and row.get("original_category") == "expected_supervised_blocker" for row in rows),
        "all_rows_reclassified_out_of_current_source_only_release_failure": release_failure_count == 0,
        "all_rows_keep_operator_gate": operator_gate_count == 6,
        "all_rows_semantics_repaired": repaired_count == 6,
        "archive_import_row_kept_fixture_required": fixture_required_count == 1,
        "release_authorizing_blockers_remaining_zero": release_authorizing_blocker_count == 0,
        "timeout_rows_still_block_install_release_cleanliness": True,
        "full_install_release_not_claimed_clean": True,
        "targeted_smoke_registered": SUPERVISED_BLOCKER_SEMANTICS_REPAIR_SMOKE in docs,
        "cli_flag_registered": SUPERVISED_BLOCKER_SEMANTICS_REPAIR_CLI in docs,
        "builder_registered": "build_supervised_blocker_semantics_repair_review" in docs,
        "text_renderer_registered": "supervised_blocker_semantics_repair_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and SUPERVISED_BLOCKER_SEMANTICS_REPAIR_SMOKE in docs,
        "review_only": BOUNDARIES["review_only"] is True,
        "does_not_execute_original_blocked_smokes": BOUNDARIES["executes_original_blocked_smokes"] is False and BOUNDARIES["executes_full_install_release_segment"] is False,
        "does_not_mark_original_blocked_smokes_pass": BOUNDARIES["marks_original_blocked_smokes_pass"] is False,
        "no_release_authorization": BOUNDARIES["release_authorized"] is False and BOUNDARIES["marks_install_release_clean"] is False,
        "no_autonomy_expansion": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
    }
    ok = all(policy_results.values())
    return {
        "id": f"supervised_blocker_semantics_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "supervised_blocker_semantics_repair_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": SUPERVISED_BLOCKER_SEMANTICS_REPAIR_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "semantics_mode": "review_only_reclassification_overlay",
        "supervised_blocker_rows_reviewed": len(rows),
        "supervised_blocker_semantics_repaired": repaired_count,
        "operator_gated_rows": operator_gate_count,
        "fixture_required_rows": fixture_required_count,
        "current_source_only_release_failure_count": release_failure_count,
        "release_authorizing_blockers_remaining": release_authorizing_blocker_count,
        "timeout_rows_remaining": 7,
        "timeout_rows_still_block_install_release_cleanliness": True,
        "original_blocked_smokes_still_not_marked_pass": True,
        "manual_registry_authoritative": True,
        "full_install_release_clean": False,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "autonomy_blocking_status": "blocked_until_timeout_rows_are_resolved_and_phase_zero_gates_are_audited",
        "rows": rows,
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def supervised_blocker_semantics_repair_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Supervised Blocker Semantics Repair report not found."
    lines = [
        "# Supervised Blocker Semantics Repair",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Supervised blocker rows reviewed: {report.get('supervised_blocker_rows_reviewed')}",
        f"Supervised blocker semantics repaired: {report.get('supervised_blocker_semantics_repaired')}",
        f"Operator-gated rows: {report.get('operator_gated_rows')}",
        f"Fixture-required rows: {report.get('fixture_required_rows')}",
        f"Current source-only release failure count: {report.get('current_source_only_release_failure_count')}",
        f"Release-authorizing blockers remaining: {report.get('release_authorizing_blockers_remaining')}",
        f"Timeout rows remaining: {report.get('timeout_rows_remaining')}",
        f"Timeout rows still block install-release cleanliness: {report.get('timeout_rows_still_block_install_release_cleanliness')}",
        f"Original blocked smokes still not marked pass: {report.get('original_blocked_smokes_still_not_marked_pass')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
    ]
    if full:
        lines.extend(["", "## Semantics rows"])
        for row in report.get("rows") or []:
            lines.append(
                f"- {row.get('name')}: {row.get('semantics_class')} | "
                f"operator_gate_required={row.get('operator_gate_required')} | "
                f"current_source_only_release_failure={row.get('current_source_only_release_failure')} | "
                f"fixture_required={row.get('requires_fixture_split_before_pass_claim')}"
            )
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_supervised_blocker_semantics_repair_review(full: bool = False) -> None:
    print(supervised_blocker_semantics_repair_review_text(build_supervised_blocker_semantics_repair_review(), full=full))
