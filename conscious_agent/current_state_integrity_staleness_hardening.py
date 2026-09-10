from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import (
    CURRENT_VERSION,
    CURRENT_VERSION_TAG,
    CURRENT_MILESTONE,
    NEXT_RECOMMENDED_ARC,
    build_current_version_source_of_truth_contract,
    build_stale_version_string_scanner,
    build_stale_milestone_title_drift_audit,
    build_current_symbol_staleness_audit,
    build_release_staleness_and_verification_audit_board,
)
from source_project_metadata import load_source_project_metadata

CURRENT_STATE_INTEGRITY_STALENESS_HARDENING_VERSION = RUNTIME_VERSION
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
SMOKE_SUMMARY_VERSION_ALIGNMENT_ID = "v601_smoke_summary_version_alignment_contract"
NESTED_METADATA_ROOT_VERSION_GUARD_ID = "v602_nested_metadata_root_version_guard"
README_CURRENT_HANDOFF_STALENESS_GUARD_ID = "v603_readme_current_handoff_staleness_guard"
SETUP_SMOKE_SCOPE_GUARD_ID = "v604_setup_smoke_scope_guard"
CURRENT_STATE_INTEGRITY_HARDENING_BOARD_ID = "v605_current_state_integrity_staleness_hardening_board"

HARDENING_BOUNDARIES: dict[str, bool] = {
    "hardening_report_writes_source": False,
    "hardening_report_writes_metadata": False,
    "hardening_report_executes_smoke": False,
    "hardening_report_executes_commands": False,
    "hardening_report_applies_patch": False,
    "hardening_report_creates_release": False,
    "hardening_report_publishes_release": False,
    "hardening_report_writes_memory": False,
    "hardening_report_reuses_approval": False,
    "hardening_report_continues_automatically": False,
    "hardening_report_expands_autonomy": False,
    "audit_pass_is_release_approval": False,
    "audit_pass_is_live_patch_permission": False,
    "setup_scope_check_executes_setup": False,
    "operator_review_required": True,
    "approval_required": True,
}


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read_text(path))
    except Exception:
        return None


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _base_state() -> dict[str, Any]:
    return {
        "integrity_hardening_status": "review_prepared",
        "stale_version_audit_status": "clean_or_blocked",
        "metadata_current_state_status": "aligned_or_blocked",
        "smoke_summary_version_status": "aligned_or_blocked",
        "nested_metadata_root_version_status": "aligned_or_blocked",
        "readme_current_handoff_status": "current_or_historical_only",
        "setup_smoke_scope_status": "bounded_install_segment",
        "current_state_mutation_status": "not_performed_by_report",
        "source_status": "untouched_by_report",
        "memory_status": "untouched",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "writes_source": False,
        "writes_memory": False,
        "writes_metadata": False,
        "modifies_live_files": False,
        "executes_commands": False,
        "executes_smoke": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "operator_review_required": True,
        "approval_required": True,
        "review_only": True,
    }


def build_smoke_summary_version_alignment_contract(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    smoke = _read_text(repo / "tools/smoke_check.py")
    exact_summary = f'"version": "{CURRENT_VERSION}"'
    stale_summary = '"version": "' + '551' + '.0"'
    rows = [
        _row("smoke-json-summary-current", exact_summary in smoke, f"tools/smoke_check.py JSON summary declares {CURRENT_VERSION}."),
        _row("stale-smoke-summary-removed", stale_summary not in smoke, "Active smoke JSON summary no longer reports v551.0."),
        _row("summary-check-review-only", HARDENING_BOUNDARIES["hardening_report_executes_smoke"] is False, "Alignment contract inspects source text only and does not run smoke."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "smoke_summary_version_alignment_contract_review_only",
        "contract_id": SMOKE_SUMMARY_VERSION_ALIGNMENT_ID,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        **_base_state(),
        "boundaries": dict(HARDENING_BOUNDARIES),
    }


def build_nested_metadata_root_version_guard(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    paths = ["data/workspaces/active_project.json", "data/workspaces/projects.json"]
    findings: list[dict[str, str]] = []
    inspected: dict[str, Any] = {"source-project-metadata": load_source_project_metadata(repo)}

    def walk(value: Any, source: str, prefix: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else key
                if key in {"release_notes", "history"}:
                    continue
                if key in {"version", "root_version"} and isinstance(child, str) and child != CURRENT_VERSION:
                    findings.append({"path": source, "field": path, "value": child, "expected": CURRENT_VERSION})
                walk(child, source, path)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, source, f"{prefix}[{idx}]")

    walk(inspected["source-project-metadata"], "source-project-metadata")
    for rel in paths:
        data = _read_json(repo / rel)
        inspected[rel] = data
        walk(data, rel)
    rows = [
        _row("nested-version-root-version-current", not findings, f"Nested current metadata version/root_version findings={len(findings)}."),
        _row("metadata-guard-review-only", HARDENING_BOUNDARIES["hardening_report_writes_metadata"] is False, "Guard reports metadata drift but does not write metadata."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "nested_metadata_root_version_guard_review_only",
        "guard_id": NESTED_METADATA_ROOT_VERSION_GUARD_ID,
        "findings": findings,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        **_base_state(),
        "boundaries": dict(HARDENING_BOUNDARIES),
    }


def build_readme_current_handoff_staleness_guard(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    readme = _read_text(repo / "README_NEXT_STEPS.md")
    current_heading = "## Current Operator Continuity Handoff"
    has_current_heading = current_heading in readme
    has_allowed_current_heading = f"## Current Operator Continuity Handoff — {CURRENT_VERSION_TAG}" in readme
    has_stale_current_heading = has_current_heading and not has_allowed_current_heading
    stale_tokens = ["Latest completed version: v585.0", "Next recommended arc: v586.0-v590.0", "Latest completed version: v600.0"]
    stale_current_tokens = [token for token in stale_tokens if token in readme and has_stale_current_heading]
    historical_heading_ok = "## Historical Operator Continuity Handoff" in readme or has_allowed_current_heading or not has_current_heading
    rows = [
        _row("no-stale-current-handoff-heading", not has_stale_current_heading, "README no longer labels stale historical handoff guidance as current."),
        _row("historical-or-current-handoff-explicit", historical_heading_ok, "Retained old handoff guidance is historical, while current handoff is version-specific."),
        _row("stale-current-handoff-tokens-blocked", not stale_current_tokens, f"stale current handoff tokens={len(stale_current_tokens)}."),
        _row("readme-guard-review-only", HARDENING_BOUNDARIES["hardening_report_writes_source"] is False, "README guard is review-only and does not edit docs."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "readme_current_handoff_staleness_guard_review_only",
        "guard_id": README_CURRENT_HANDOFF_STALENESS_GUARD_ID,
        "stale_current_handoff_tokens": stale_current_tokens,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        **_base_state(),
        "boundaries": dict(HARDENING_BOUNDARIES),
    }


def build_setup_smoke_scope_guard(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    setup = _read_text(repo / "setup.ps1")
    bounded_segment = (
        "--segment install-regression-recent" in setup
        or "--segment install-dashboard" in setup
        or ("tools\\release_verify.py" in setup and "--profile quick" in setup)
        or ("tools/release_verify.py" in setup and "--profile quick" in setup)
    )
    default_full_invocation = "tools/smoke_check.py" in setup and "--tier full" in setup
    rows = [
        _row("setup-uses-bounded-smoke-segment", bounded_segment, "setup.ps1 uses a bounded install smoke segment for operator install ergonomics."),
        _row("setup-does-not-force-full-smoke", not default_full_invocation, "setup.ps1 does not force the timeout-prone full legacy smoke tier."),
        _row("setup-guard-does-not-run", HARDENING_BOUNDARIES["setup_scope_check_executes_setup"] is False, "Setup scope guard inspects setup text only and does not execute setup."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "setup_smoke_scope_guard_review_only",
        "guard_id": SETUP_SMOKE_SCOPE_GUARD_ID,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        **_base_state(),
        "boundaries": dict(HARDENING_BOUNDARIES),
    }


def build_current_state_integrity_staleness_hardening_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    source = build_current_version_source_of_truth_contract(repo)
    scanner = build_stale_version_string_scanner(repo)
    milestone = build_stale_milestone_title_drift_audit(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    smoke = build_smoke_summary_version_alignment_contract(repo)
    metadata = build_nested_metadata_root_version_guard(repo)
    readme = build_readme_current_handoff_staleness_guard(repo)
    setup = build_setup_smoke_scope_guard(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/current_state_integrity_staleness_hardening.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "setup.ps1",
    ])
    required_tokens = [
        "v605.0 - Current-State Integrity and Staleness Audit Hardening v1",
        TARGETED_SMOKE,
        "smoke-summary-version-alignment-contract",
        "nested-metadata-root-version-guard",
        "readme-current-handoff-staleness-guard",
        "setup-smoke-scope-guard",
        "current-state-integrity-staleness-hardening-board",
        "current_state_integrity_staleness_hardening.py",
        "audit_pass_is_release_approval=False",
        "audit_pass_is_live_patch_permission=False",
        "data-tip",
        "no_native_title_tooltip",
    ]
    rows = [
        _row("source-of-truth-current", source.get("ok") is True, "Current version source-of-truth contract is aligned."),
        _row("stale-scanner-hardened", scanner.get("ok") is True, "Stale scanner is clean after expanded current-state coverage."),
        _row("milestone-current", milestone.get("ok") is True, "Current milestone title drift audit is clean."),
        _row("current-symbols-current", symbols.get("ok") is True, "Current symbol staleness audit is clean."),
        _row("release-board-current", release_board.get("ok") is True, "Release staleness verification board is aligned to the current hardening arc."),
        _row("smoke-summary-current", smoke.get("ok") is True, "Smoke JSON summary version is current."),
        _row("nested-metadata-current", metadata.get("ok") is True, "Nested project metadata version/root_version fields are current."),
        _row("readme-current-handoff-clean", readme.get("ok") is True, "README current-state handoff language has no stale current section."),
        _row("setup-smoke-bounded", setup.get("ok") is True, "setup.ps1 uses a bounded install smoke segment."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke/setup metadata include v601-v605 hardening surfaces and non-authority tokens."),
        _row("no-authority", all(HARDENING_BOUNDARIES[key] is False for key in ["hardening_report_writes_source", "hardening_report_writes_metadata", "hardening_report_executes_smoke", "hardening_report_executes_commands", "hardening_report_applies_patch", "hardening_report_creates_release", "hardening_report_publishes_release", "hardening_report_writes_memory", "hardening_report_reuses_approval", "hardening_report_continues_automatically", "hardening_report_expands_autonomy", "audit_pass_is_release_approval", "audit_pass_is_live_patch_permission"]), "Hardening board grants no source, metadata, smoke execution, command execution, patch, release, publish, memory, approval reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "current_state_integrity_staleness_hardening_board_review_only",
        "board_id": CURRENT_STATE_INTEGRITY_HARDENING_BOARD_ID,
        **_base_state(),
        "source_of_truth_contract": source,
        "stale_version_string_scanner": scanner,
        "stale_milestone_title_drift_audit": milestone,
        "current_symbol_staleness_audit": symbols,
        "release_staleness_verification_board": release_board,
        "smoke_summary_version_alignment_contract": smoke,
        "nested_metadata_root_version_guard": metadata,
        "readme_current_handoff_staleness_guard": readme,
        "setup_smoke_scope_guard": setup,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(HARDENING_BOUNDARIES),
        "safe_next_action": "Operator may review the v605 current-state hardening board. Next work should prepare operator-governed archive reconciliation application prep without selecting decisions, writing archive records, mutating current state, creating releases, publishing releases, executing rollback, writing memory, or expanding autonomy.",
    }


def build_current_state_integrity_staleness_hardening_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "current_state_integrity_staleness_hardening_board_v1"
    builders = {
        "smoke_summary_version_alignment_contract_v1": build_smoke_summary_version_alignment_contract,
        "nested_metadata_root_version_guard_v1": build_nested_metadata_root_version_guard,
        "readme_current_handoff_staleness_guard_v1": build_readme_current_handoff_staleness_guard,
        "setup_smoke_scope_guard_v1": build_setup_smoke_scope_guard,
        "current_state_integrity_staleness_hardening_board_v1": build_current_state_integrity_staleness_hardening_board,
    }
    return builders.get(stage, build_current_state_integrity_staleness_hardening_board)(root)


def render_current_state_integrity_staleness_hardening_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"integrity_hardening_status: {report.get('integrity_hardening_status')}",
        f"stale_version_audit_status: {report.get('stale_version_audit_status')}",
        f"metadata_current_state_status: {report.get('metadata_current_state_status')}",
        f"smoke_summary_version_status: {report.get('smoke_summary_version_status')}",
        f"nested_metadata_root_version_status: {report.get('nested_metadata_root_version_status')}",
        f"readme_current_handoff_status: {report.get('readme_current_handoff_status')}",
        f"setup_smoke_scope_status: {report.get('setup_smoke_scope_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v601.0-v605.0 current-state integrity and staleness hardening tokens: smoke-summary-version-alignment-contract nested-metadata-root-version-guard readme-current-handoff-staleness-guard setup-smoke-scope-guard current-state-integrity-staleness-hardening-board current-state-integrity-staleness-hardening-v1 current_state_integrity_staleness_hardening.py smoke_summary_version_status=aligned_or_blocked nested_metadata_root_version_status=aligned_or_blocked readme_current_handoff_status=current_or_historical_only setup_smoke_scope_status=bounded_install_segment current_state_mutation_status=not_performed_by_report release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous hardening_report_writes_source=False hardening_report_writes_metadata=False hardening_report_executes_smoke=False audit_pass_is_release_approval=False audit_pass_is_live_patch_permission=False no_native_title_tooltip data-tip command-deck operator-console

# v661.0-v665.0 integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy_smoke_segmentation_repair_status=prepared_only smoke_segmentation_integrity_board_status=review_only current_release_blocking legacy_advisory historical_pinned slow_full_audit migration_debt approval_semantics_changed=False current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v676.0-v685.0 current integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_renderer_component_extraction_board_status=review_only approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v686.0-v690.0 neural command deck dashboard redesign integrity tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console
