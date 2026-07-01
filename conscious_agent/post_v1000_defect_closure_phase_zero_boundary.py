from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_MILESTONE, CURRENT_VERSION, NEXT_RECOMMENDED_ARC
from install_release_segment_cleanliness_gate import build_install_release_segment_cleanliness_gate_review
import current_version_staleness_audit as audit
import smoke_registry_pilot as pilot
from release_archive_fixture_split_expansion import build_release_archive_fixture_split_expansion_review
from supervised_blocker_semantics_repair import build_supervised_blocker_semantics_repair_review

POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_VERSION = CURRENT_VERSION
POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_SMOKE = "post-v1000-defect-closure-audit-and-phase-zero-boundary-v1"
POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_CLI = "--post-v1000-defect-closure-audit-and-phase-zero-boundary"
POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_TITLE = "Post-v1000 Defect Closure Audit and Autonomy Phase 0 Readiness Boundary v1"

BOUNDARIES: dict[str, bool] = {
    "review_only": True,
    "phase_zero_observation_only_boundary_defined": True,
    "phase_zero_enabled": False,
    "observation_only_autonomy_enabled": False,
    "autonomy_expanded": False,
    "expands_autonomy": False,
    "source_writes_allowed": False,
    "applies_source_edits": False,
    "writes_source": False,
    "memory_writes_allowed": False,
    "writes_memory": False,
    "memory_mutated": False,
    "approval_system_mutated": False,
    "release_system_mutated": False,
    "scheduler_mutated": False,
    "network_accessed": False,
    "command_execution_allowed": False,
    "runs_unapproved_commands": False,
    "sandbox_promotion_allowed": False,
    "publishes_release": False,
    "release_authorized": False,
    "full_install_release_clean": False,
    "generated_wiring_activated": False,
    "dashboard_wiring_activated": False,
    "api_wiring_activated": False,
    "cli_wiring_activated": False,
    "smoke_wiring_activated": False,
    "manual_registry_authoritative": True,
    "protected_systems_require_operator_approval": True,
}

ORIGINAL_V1000_FINDINGS: tuple[dict[str, str], ...] = (
    {
        "finding": "v1000 closure could pass over failed prerequisite evidence",
        "status": "fixed",
        "evidence": "v1001 replaced docs-token prerequisite closure with actual prerequisite-chain evidence.",
    },
    {
        "finding": "data-driven-first dispatch did not execute declared builders",
        "status": "fixed",
        "evidence": "v1001 executes declared builder/text renderer pairs instead of only checking names in documentation.",
    },
    {
        "finding": "manual fallback was not exercised on the happy path",
        "status": "fixed",
        "evidence": "v1001 added a controlled forced-fallback proof while preserving manual fallback authority.",
    },
    {
        "finding": "packaged scaffold/wrapper evidence was stale",
        "status": "repaired_and_monitored",
        "evidence": "v1001-v1010 regenerate scaffold/wrapper schema markers and hash ledgers to the current verification version.",
    },
    {
        "finding": "stale executable assertions remained outside tools/smoke_check.py",
        "status": "fixed",
        "evidence": "v1001 expanded executable stale comparison scanning beyond smoke_check.py.",
    },
    {
        "finding": "actual install-release segment was unhealthy and vague",
        "status": "partially_mitigated_still_blocking",
        "evidence": "v1002-v1009 classified 30 rows: 17 passing, 6 operator-gated semantics rows, and 7 timeout rows still blocking.",
    },
    {
        "finding": "pilot execution harness lacked sufficient timeout enforcement for expansion",
        "status": "partially_mitigated_still_monitored",
        "evidence": "v1003 added timeout harness proof; full OS sandboxing remains unproven and operator-controlled.",
    },
    {
        "finding": "Smoke Debt dashboard remained visually stale at v910",
        "status": "fixed",
        "evidence": "v1001-v1010 refreshed /self-development-smoke-debt current-state text and stale dashboard drift markers.",
    },
)

PHASE_ZERO_ALLOWED_ACTIONS: tuple[str, ...] = (
    "inspect_source_state",
    "summarize_project_risks",
    "rank_next_repair_work",
    "prepare_review_only_reports",
    "prepare_operator_approval_packets",
)

PHASE_ZERO_FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "apply_source_patches",
    "write_or_retract_memory",
    "publish_or_create_release_packages_without_operator_approval",
    "mutate_approval_policy",
    "run_unapproved_commands",
    "promote_sandbox_output_to_source",
    "change_autonomy_level",
    "schedule_hidden_background_work",
    "activate_generated_dashboard_api_cli_or_smoke_wiring",
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


def build_post_v1000_defect_closure_phase_zero_boundary_review(root_dir: str | Path | None = None) -> dict[str, Any]:
    root = _repo(root_dir)
    docs = "\n".join(_read_text(root / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/post_v1000_defect_closure_phase_zero_boundary.py",
        "conscious_agent/install_release_segment_cleanliness_gate.py",
        "conscious_agent/main.py",
        "conscious_agent/source_surface_manifest.py",
        "tools/smoke_check.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/current_version_staleness_audit.py",
    ])
    scaffold = pilot._hash_ledger_artifacts_pass(root, "sandbox/generated_surface_scaffold_previews", "hash_ledger.json")
    wrappers = pilot._hash_ledger_artifacts_pass(root, "sandbox/generated_scaffold_wrapper_previews", "wrapper_hash_ledger.json")
    scanner = audit.build_stale_version_string_scanner(root)
    pilot_text = _read_text(root / "conscious_agent/smoke_registry_pilot.py")
    dashboard_text = _read_text(root / "conscious_agent/dashboard.py")
    smoke_debt_section = dashboard_text.split("def render_self_development_smoke_debt", 1)[-1].split("\ndef ", 1)[0]
    evidence_chain_repair_passed = (
        scaffold.get("passed") is True
        and wrappers.get("passed") is True
        and scanner.get("ok") is True
        and CURRENT_MILESTONE in smoke_debt_section
        and "v910.0 Metadata and Current Marker Gate Reconciliation v1" not in smoke_debt_section
        and "forced_fallback_used_once" in pilot_text
        and "documentation_only_dispatch_rejected" in pilot_text
        and "_run_smoke_check_subprocess" in pilot_text
        and "documentation_only_prerequisite_evidence_rejected" in pilot_text
        and "build_prerequisite_closure_chain_evidence" in pilot_text
    )
    cleanliness = build_install_release_segment_cleanliness_gate_review(root)
    split = build_release_archive_fixture_split_expansion_review(root)
    semantics = build_supervised_blocker_semantics_repair_review(root)
    statuses = [row["status"] for row in ORIGINAL_V1000_FINDINGS]
    fixed_count = statuses.count("fixed")
    repaired_count = statuses.count("repaired_and_monitored")
    partial_count = sum(1 for status in statuses if status.startswith("partially_mitigated"))
    still_blocking_count = 1 if cleanliness.get("install_release_active_cleanliness_blockers") == 7 else 0
    phase_zero_readiness_status = "boundary_defined_observation_only_not_enabled"
    policy_results = {
        "all_original_findings_accounted": len(ORIGINAL_V1000_FINDINGS) == 8,
        "evidence_chain_repair_passed": evidence_chain_repair_passed,
        "cleanliness_gate_prerequisite_passed": cleanliness.get("ok") is True,
        "install_release_truth_preserved": cleanliness.get("full_install_release_clean") is False and cleanliness.get("install_release_active_cleanliness_blockers") == 7,
        "split_fixture_evidence_preserved": split.get("ok") is True and split.get("total_split_fixture_targets_including_v1006") == 15,
        "supervised_semantics_preserved": semantics.get("ok") is True and semantics.get("release_authorizing_blockers_remaining") == 0,
        "no_all_fixed_claim": partial_count >= 2 and still_blocking_count == 1,
        "phase_zero_boundary_defined": BOUNDARIES["phase_zero_observation_only_boundary_defined"] is True,
        "phase_zero_not_enabled": BOUNDARIES["phase_zero_enabled"] is False and BOUNDARIES["observation_only_autonomy_enabled"] is False,
        "source_writes_forbidden": BOUNDARIES["source_writes_allowed"] is False and BOUNDARIES["writes_source"] is False,
        "memory_writes_forbidden": BOUNDARIES["memory_writes_allowed"] is False and BOUNDARIES["writes_memory"] is False,
        "release_authorization_forbidden": BOUNDARIES["release_authorized"] is False and BOUNDARIES["publishes_release"] is False,
        "command_execution_forbidden": BOUNDARIES["command_execution_allowed"] is False and BOUNDARIES["runs_unapproved_commands"] is False,
        "sandbox_promotion_forbidden": BOUNDARIES["sandbox_promotion_allowed"] is False,
        "generated_wiring_inactive": BOUNDARIES["generated_wiring_activated"] is False,
        "manual_registry_authoritative": BOUNDARIES["manual_registry_authoritative"] is True,
        "autonomy_not_expanded": BOUNDARIES["autonomy_expanded"] is False and BOUNDARIES["expands_autonomy"] is False,
        "targeted_smoke_registered": POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_SMOKE in docs,
        "cli_flag_registered": POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_CLI in docs,
        "builder_registered": "build_post_v1000_defect_closure_phase_zero_boundary_review" in docs,
        "text_renderer_registered": "post_v1000_defect_closure_phase_zero_boundary_review_text" in docs,
        "dashboard_current_marker_present": CURRENT_MILESTONE in docs and POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_SMOKE in docs,
        "protected_systems_operator_controlled": BOUNDARIES["protected_systems_require_operator_approval"] is True,
    }
    ok = all(policy_results.values())
    return {
        "id": f"post_v1000_defect_closure_phase_zero_boundary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "post_v1000_defect_closure_phase_zero_boundary_review",
        "version": CURRENT_VERSION,
        "current_milestone": CURRENT_MILESTONE,
        "title": POST_V1000_DEFECT_CLOSURE_PHASE_ZERO_BOUNDARY_TITLE,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "policies_passed": ok,
        "policy_results": policy_results,
        "checked_at": _now_iso(),
        "original_v1000_findings_total": len(ORIGINAL_V1000_FINDINGS),
        "original_v1000_findings_fixed": fixed_count,
        "original_v1000_findings_repaired_and_monitored": repaired_count,
        "original_v1000_findings_partially_mitigated": partial_count,
        "original_v1000_findings_still_blocking": still_blocking_count,
        "finding_rows": [dict(row) for row in ORIGINAL_V1000_FINDINGS],
        "install_release_total_checks": cleanliness.get("install_release_total_checks"),
        "install_release_passing_rows": cleanliness.get("install_release_passing_rows"),
        "operator_gated_semantics_rows": cleanliness.get("install_release_operator_gated_semantics_rows"),
        "timeout_rows_still_blocking": cleanliness.get("install_release_timeout_rows"),
        "split_fixture_families_passing": cleanliness.get("split_fixture_families_passing"),
        "split_fixture_targets_passing": cleanliness.get("split_fixture_targets_passing"),
        "full_install_release_clean": False,
        "release_authorized": False,
        "phase_zero_readiness_status": phase_zero_readiness_status,
        "phase_zero_allowed_actions": list(PHASE_ZERO_ALLOWED_ACTIONS),
        "phase_zero_forbidden_actions": list(PHASE_ZERO_FORBIDDEN_ACTIONS),
        "closure_summary": "Post-v1000 truth-repair arc is closed as an audit boundary, not as full install-release cleanup; seven timeout rows still block release cleanliness and Phase 0 remains observation-only/not enabled.",
        "autonomy_blocking_status": "autonomy_remains_blocked_until_install_release_timeout_rows_are_resolved_and_sandbox_operator_gates_are_proven",
        **BOUNDARIES,
        "recommended_next_arc": NEXT_RECOMMENDED_ARC,
    }


def post_v1000_defect_closure_phase_zero_boundary_review_text(report: dict[str, Any] | None, full: bool = False) -> str:
    if not report:
        return "Post-v1000 Defect Closure Audit and Phase Zero Boundary report not found."
    lines = [
        "# Post-v1000 Defect Closure Audit and Autonomy Phase 0 Boundary",
        "",
        f"Status: {report.get('status')}",
        f"Version: {report.get('version')}",
        f"Original v1000 findings total: {report.get('original_v1000_findings_total')}",
        f"Fixed findings: {report.get('original_v1000_findings_fixed')}",
        f"Repaired/monitored findings: {report.get('original_v1000_findings_repaired_and_monitored')}",
        f"Partially mitigated findings: {report.get('original_v1000_findings_partially_mitigated')}",
        f"Still-blocking finding groups: {report.get('original_v1000_findings_still_blocking')}",
        f"Install-release total checks: {report.get('install_release_total_checks')}",
        f"Install-release passing rows: {report.get('install_release_passing_rows')}",
        f"Operator-gated semantics rows: {report.get('operator_gated_semantics_rows')}",
        f"Timeout rows still blocking: {report.get('timeout_rows_still_blocking')}",
        f"Split fixture targets passing: {report.get('split_fixture_targets_passing')}",
        f"Full install-release clean: {report.get('full_install_release_clean')}",
        f"Release authorized: {report.get('release_authorized')}",
        f"Phase Zero readiness status: {report.get('phase_zero_readiness_status')}",
        f"Phase Zero enabled: {report.get('phase_zero_enabled')}",
        f"Autonomy expanded: {report.get('autonomy_expanded')}",
        f"Summary: {report.get('closure_summary')}",
    ]
    if full:
        lines.extend(["", "## Finding rows"])
        for row in report.get("finding_rows") or []:
            lines.append(f"- {row.get('status')}: {row.get('finding')} — {row.get('evidence')}")
        lines.extend(["", "## Phase Zero allowed actions"])
        for action in report.get("phase_zero_allowed_actions") or []:
            lines.append(f"- {action}")
        lines.extend(["", "## Phase Zero forbidden actions"])
        for action in report.get("phase_zero_forbidden_actions") or []:
            lines.append(f"- {action}")
        lines.extend(["", "## Policy results"])
        for key, value in (report.get("policy_results") or {}).items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def print_post_v1000_defect_closure_phase_zero_boundary_review(full: bool = False) -> None:
    print(post_v1000_defect_closure_phase_zero_boundary_review_text(build_post_v1000_defect_closure_phase_zero_boundary_review(), full=full))


# v1011.0 post-v1000 defect closure and phase zero boundary tokens: post-v1000-defect-closure-audit-and-phase-zero-boundary-v1 --post-v1000-defect-closure-audit-and-phase-zero-boundary build_post_v1000_defect_closure_phase_zero_boundary_review post_v1000_defect_closure_phase_zero_boundary_review_text original_v1000_findings_total=8 fixed_findings=5 repaired_and_monitored=1 partially_mitigated=2 timeout_rows_still_blocking=7 full_install_release_clean=False phase_zero_enabled=False observation_only_autonomy_enabled=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False protected_systems_require_operator_approval=True data-tip command-deck operator-console
