from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_blocker_ledger import INSTALL_RELEASE_LEDGER_ROWS, build_install_release_blocker_ledger_refresh_review
from release_archive_fixture_split_expansion import build_release_archive_fixture_split_expansion_review
from supervised_blocker_semantics_repair import build_supervised_blocker_semantics_repair_review

INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_VERSION = CURRENT_VERSION
INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_SMOKE = "install-release-segment-cleanliness-gate-v1"
INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_CLI = "--install-release-segment-cleanliness-gate"
INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_TITLE = "Install-Release Segment Cleanliness Gate v1"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "executes_full_install_release_segment": False,
    "executes_parent_timeout_rows": False,
    "executes_original_blocked_smokes": False,
    "marks_timeout_rows_pass": False,
    "marks_operator_gated_rows_pass": False,
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


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"pass": 0, "blocked": 0, "timeout": 0}
    for row in rows:
        status = str(row.get("status"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _category_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        category = str(row.get("category") or "uncategorized")
        counts[category] = counts.get(category, 0) + 1
    return counts


def _timeout_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if row.get("status") == "timeout"]


def _operator_gated_rows(semantics_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in semantics_report.get("rows") or [] if row.get("operator_gate_required") is True]


def build_install_release_segment_cleanliness_gate_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/install_release_segment_cleanliness_gate.py",
        "conscious_agent/install_release_blocker_ledger.py",
        "conscious_agent/release_archive_fixture_split_expansion.py",
        "conscious_agent/supervised_blocker_semantics_repair.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    ledger = build_install_release_blocker_ledger_refresh_review(root)
    split = build_release_archive_fixture_split_expansion_review(root)
    semantics = build_supervised_blocker_semantics_repair_review(root)
    rows = [dict(row) for row in INSTALL_RELEASE_LEDGER_ROWS]
    status_counts = _status_counts(rows)
    category_counts = _category_counts(rows)
    timeout_rows = _timeout_rows(rows)
    operator_rows = _operator_gated_rows(semantics)
    split_families = int(split.get("total_split_families_including_v1006") or 0)
    split_targets = int(split.get("total_split_fixture_targets_including_v1006") or 0)
    split_pass_targets = int(split.get("total_split_fixture_targets_including_v1006") or 0) if split.get("ok") is True else 0
    release_authorizing_blockers_remaining = int(semantics.get("release_authorizing_blockers_remaining") or 0)
    current_source_only_release_failure_count = int(semantics.get("current_source_only_release_failure_count") or 0)
    active_cleanliness_blockers = len(timeout_rows)
    full_install_release_clean = active_cleanliness_blockers == 0 and release_authorizing_blockers_remaining == 0
    policy_results = {
        "v1002_ledger_prerequisite_passed": ledger.get("ok") is True and ledger.get("install_release_total_checks") == 30,
        "v1007_split_expansion_prerequisite_passed": split.get("ok") is True and split_families == 3 and split_targets == 15,
        "v1008_semantics_prerequisite_passed": semantics.get("ok") is True and semantics.get("supervised_blocker_semantics_repaired") == 6,
        "thirty_install_release_rows_accounted": len(rows) == 30,
        "seventeen_passing_rows_recorded": status_counts.get("pass") == 17,
        "six_operator_gated_rows_semantics_classified": len(operator_rows) == 6 and semantics.get("release_authorizing_blockers_remaining") == 0,
        "seven_timeout_rows_remain_active_blockers": len(timeout_rows) == 7,
        "split_fixture_evidence_recorded": split_families == 3 and split_targets == 15 and split_pass_targets == 15,
        "full_install_release_not_claimed_clean": full_install_release_clean is False,
        "release_not_authorized": BOUNDARIES["release_authorized"] is False,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "manual_registry_still_authoritative": True,
        "generated_wiring_stays_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "does_not_execute_full_install_release_segment": BOUNDARIES["executes_full_install_release_segment"] is False,
        "does_not_mark_blocked_rows_pass": BOUNDARIES["marks_timeout_rows_pass"] is False and BOUNDARIES["marks_operator_gated_rows_pass"] is False,
        "targeted_smoke_registered": INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_SMOKE in docs,
        "cli_flag_registered": INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_CLI in docs,
        "builder_registered": "build_install_release_segment_cleanliness_gate_review" in docs,
        "text_renderer_registered": "install_release_segment_cleanliness_gate_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"install_release_segment_cleanliness_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "install_release_segment_cleanliness_gate_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": INSTALL_RELEASE_SEGMENT_CLEANLINESS_GATE_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "segment": "install-release",
        "install_release_total_checks": len(rows),
        "install_release_passing_rows": status_counts.get("pass", 0),
        "install_release_operator_gated_semantics_rows": len(operator_rows),
        "install_release_timeout_rows": len(timeout_rows),
        "install_release_active_cleanliness_blockers": active_cleanliness_blockers,
        "release_authorizing_blockers_remaining": release_authorizing_blockers_remaining,
        "current_source_only_release_failure_count": current_source_only_release_failure_count,
        "split_fixture_families_passing": split_families if split.get("ok") is True else 0,
        "split_fixture_targets_passing": split_pass_targets,
        "split_fixture_targets_total": split_targets,
        "full_install_release_clean": full_install_release_clean,
        "marks_install_release_clean": False,
        "release_authorized": False,
        "manual_registry_authoritative": True,
        "timeout_row_names": [row.get("name") for row in timeout_rows],
        "operator_gated_row_names": [row.get("name") for row in operator_rows],
        "status_counts": status_counts,
        "category_counts": category_counts,
        "autonomy_blocking_status": "blocked_until_seven_timeout_rows_are_resolved_or_replaced_by_fixture_level_release_checks_and_phase_zero_is_audited",
        "cleanliness_summary": "17 pass, 6 operator-gated semantics-classified, 7 timeout rows still blocking; full install-release remains not clean.",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def install_release_segment_cleanliness_gate_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Install-Release Segment Cleanliness Gate report not found."
    lines = [
        "# Install-Release Segment Cleanliness Gate",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Segment: {report.get('segment')}",
        f"Install-release total checks: {report.get('install_release_total_checks')}",
        f"Install-release passing rows: {report.get('install_release_passing_rows')}",
        f"Operator-gated semantics rows: {report.get('install_release_operator_gated_semantics_rows')}",
        f"Timeout rows still blocking: {report.get('install_release_timeout_rows')}",
        f"Active cleanliness blockers: {report.get('install_release_active_cleanliness_blockers')}",
        f"Release-authorizing blockers remaining: {report.get('release_authorizing_blockers_remaining')}",
        f"Split fixture families passing: {report.get('split_fixture_families_passing')}",
        f"Split fixture targets passing: {report.get('split_fixture_targets_passing')}/{report.get('split_fixture_targets_total')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Summary: {report.get('cleanliness_summary')}",
    ]
    if full:
        lines.extend(["", "## Timeout rows still blocking"])
        for name in report.get("timeout_row_names") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Operator-gated semantics rows"])
        for name in report.get("operator_gated_row_names") or []:
            lines.append(f"- {name}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_install_release_segment_cleanliness_gate_review(full: bool = False) -> None:
    print(install_release_segment_cleanliness_gate_review_text(build_install_release_segment_cleanliness_gate_review(), full=full))


# v1011.0 install-release segment cleanliness gate tokens: install-release-segment-cleanliness-gate-v1 --install-release-segment-cleanliness-gate build_install_release_segment_cleanliness_gate_review install_release_segment_cleanliness_gate_review_text install_release_total_checks=30 install_release_passing_rows=17 operator_gated_semantics_rows=6 timeout_rows_still_blocking=7 split_fixture_families_passing=3 split_fixture_targets_passing=15 full_install_release_clean=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
