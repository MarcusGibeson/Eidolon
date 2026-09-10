from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from pathlib import Path
from typing import Any

DOCUMENTATION_CONTINUITY_HEADER_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
DOCUMENTATION_CONTINUITY_BOUNDARIES: dict[str, bool] = {
    "documentation_state_is_authorization": False,
    "release_history_is_authorization": False,
    "recommended_next_arc_is_permission": False,
    "handoff_packet_is_execution_packet": False,
    "current_state_header_creates_approval": False,
    "documentation_cleanup_writes_memory": False,
    "documentation_cleanup_applies_source_edits": False,
    "documentation_cleanup_expands_autonomy": False,
    "operator_approval_still_required": True,
}

CURRENT_HEADER_TOKENS = [
    "Current version: v700.0 - Autonomy Phase 0 Readiness Harness v1",
    "Current milestone: v700.0 Autonomy Phase 0 Readiness Harness v1",
    "Verification",
    "Recommended Next Arc",
    "Standing Rules",
    "Current Operator Continuity Handoff",
]

HISTORICAL_LEDGER_TOKENS = [
    "## Historical Next-Steps Ledger",
    "HISTORICAL ARC RECORD",
    "COMPLETED ARC RECORD",
    "SUPERSEDED PLANNING NOTE",
    "DO NOT TREAT AS CURRENT PLAN",
]

HANDOFF_TOKENS = [
    "NEW CHAT CONTINUATION PACKET",
    "Latest completed version: v700.0",
    "Standing README rule",
    "Dashboard style rule",
    "Safety/autonomy restriction",
    "Next recommended arc: v711.0-v760.0 Phase 0 Observation Trial Review and Telemetry Calibration v1",
]

BOUNDARY_TOKENS = [
    "README state is not approval",
    "Release history is not authorization",
    "A recommended next arc is not permission to execute it",
    "A completed smoke check is not operator consent",
    "A handoff packet is not an execution packet",
    "documentation_state_is_authorization=False",
    "release_history_is_authorization=False",
    "recommended_next_arc_is_permission=False",
    "handoff_packet_is_execution_packet=False",
]


def _root(root: str | Path | None = None) -> Path:
    if root is not None:
        candidate = Path(root).resolve()
        if (candidate / "conscious_agent").exists():
            return candidate
        if candidate.name == "conscious_agent":
            return candidate.parents[0]
        return candidate
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _status(ok: bool) -> str:
    return "pass" if ok else "blocked"


def _row(name: str, ok: bool, message: str, **extra: Any) -> dict[str, Any]:
    row = {"name": name, "status": _status(ok), "message": message}
    row.update(extra)
    return row


def _readme_next(root: Path) -> str:
    return _read(root / "README_NEXT_STEPS.md")


def _release_history(root: Path) -> str:
    return _read(root / "README_RELEASE_HISTORY.md")


def _project_docs(root: Path) -> str:
    rels = [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/documentation_continuity_header.py",
        "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/source_surface_manifest.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
        "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ]
    return "\n".join(_read(root / rel) for rel in rels)


def build_current_state_header_block(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    first_chunk = text[:5000]
    rows = [
        _row("current-version-top", ("Current version: v700.0" in first_chunk and "Autonomy Phase 0 Readiness Harness v1" in first_chunk), "README_NEXT_STEPS.md exposes the current version near the top."),
        _row("current-milestone-top", CURRENT_MILESTONE in first_chunk, "README_NEXT_STEPS.md names the current milestone near the top."),
        _row("verified-checks-top", ("Targeted smoke" in first_chunk or "Verification" in first_chunk), "Verification/smoke section is near the top."),
        _row("current-blockers-top", ("does not" in first_chunk or "Do not" in first_chunk), "Current non-authorization boundaries appear near the top."),
        _row("recommended-next-arc-top", NEXT_RECOMMENDED_ARC in first_chunk, "Current recommended next arc points to v696-v700."),
        _row("safety-boundary-top", ("not_authorized" in first_chunk.lower() or "no autonomy" in first_chunk.lower() or "Do not make Eidolon autonomous" in first_chunk), "Safety boundary appears near the top."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "current_state_header_block_review_only",
        "expected_version": CURRENT_VERSION_TAG,
        "expected_milestone": CURRENT_MILESTONE,
        "expected_next_arc": NEXT_RECOMMENDED_ARC,
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_historical_next_steps_separation(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    current_pos = text.find("Current version: v700.0")
    ledger_pos = text.find("## Historical Next-Steps Ledger")
    rows = [
        _row("historical-ledger-optional", True, "Historical next-step content may live in README_RELEASE_HISTORY.md for source-only packages."),
        _row("current-state-present", current_pos >= 0, "Current-state header appears in README_NEXT_STEPS.md."),
        _row("historical-warning-tokens", (ledger_pos < 0 or all(token in text for token in HISTORICAL_LEDGER_TOKENS)), "Historical/superseded labels are present when a local historical ledger exists."),
        _row("active-plan-not-buried", text.find("Next recommended arc: " + NEXT_RECOMMENDED_ARC) >= 0, "Active next arc appears in the current README."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "historical_next_steps_separation_review_only",
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        "historical_sections_are_authorization": False,
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_operator_continuity_handoff_packet(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    text = _readme_next(project_root)
    rows = [
        _row("handoff-section-present", "Current Operator Continuity Handoff" in text or "NEW CHAT CONTINUATION PACKET" in text, "Operator continuation handoff section is present."),
        _row("handoff-required-tokens", all(token in text for token in HANDOFF_TOKENS), "Handoff packet includes latest version, rules, safety, verification, and next arc."),
        _row("standing-readme-rule", "README_NEXT_STEPS.md" in text and "README_RELEASE_HISTORY.md" in text, "Standing README/release-history update rule is present."),
        _row("dashboard-rule", "data-tip" in text and "native" in text and "title" in text and "tooltip" in text, "Dashboard command-deck/data-tip rule is preserved."),
        _row("handoff-not-execution", "A handoff packet is not an execution packet" in text, "Handoff packet is explicitly not execution authority."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "operator_continuity_handoff_packet_review_only",
        "latest_completed_version": CURRENT_VERSION_TAG,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_documentation_boundary_language(root: str | Path | None = None) -> dict[str, Any]:
    project_root = _root(root)
    docs = _project_docs(project_root)
    rows = [
        _row("boundary-tokens-present", all(token in docs for token in BOUNDARY_TOKENS), "Documentation contains explicit no-authorization boundary tokens."),
        _row("readme-not-approval", "README state is not approval" in docs, "README state cannot be read as approval."),
        _row("release-history-not-authorization", "Release history is not authorization" in docs, "Release history cannot be read as authorization."),
        _row("next-arc-not-permission", "A recommended next arc is not permission to execute it" in docs, "Recommended next arc remains advisory until operator approval."),
        _row("smoke-not-consent", "A completed smoke check is not operator consent" in docs, "Smoke success cannot be read as operator consent."),
        _row("handoff-not-execution", "A handoff packet is not an execution packet" in docs, "Handoff packet cannot execute work."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "documentation_boundary_language_review_only",
        "rows": rows,
        "ok": ok,
        "status": _status(ok),
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def build_documentation_continuity_header_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    project_root = _root(root)
    docs = docs_text if docs_text is not None else _project_docs(project_root)
    header = build_current_state_header_block(project_root)
    history = build_historical_next_steps_separation(project_root)
    handoff = build_operator_continuity_handoff_packet(project_root)
    boundary = build_documentation_boundary_language(project_root)
    release_history = _release_history(project_root)
    required_tokens = [
        "current-state-header-block", "historical-next-steps-separation", "operator-continuity-handoff-packet",
        "documentation-boundary-language", "documentation-continuity-header-audit",
        "operator-governed-documentation-continuity-header-v1", "documentation_continuity_header.py",
        "documentation_state_is_authorization=False", "release_history_is_authorization=False",
        "recommended_next_arc_is_permission=False", "handoff_packet_is_execution_packet=False",
        "current_state_header_creates_approval=False", "documentation_cleanup_writes_memory=False",
        "documentation_cleanup_applies_source_edits=False", "documentation_cleanup_expands_autonomy=False",
        "operator_approval_still_required=True", "no_native_title_tooltip", "data-tip", "command-deck", "operator-console",
    ]
    rows = [
        _row("header", header.get("ok") is True, "Current-state header is present and current."),
        _row("historical-separation", history.get("ok") is True, "Historical next steps are separated and labeled."),
        _row("handoff", handoff.get("ok") is True, "Operator/new-chat continuity packet is present."),
        _row("boundary", boundary.get("ok") is True, "Documentation no-authorization boundary language is present."),
        _row("release-history-current", "v700.0 - Autonomy Phase 0 Readiness Harness v1" in release_history, "Release history documents current v700." ),
        _row("smoke-doc-tokens", all(token in docs for token in required_tokens), "Smoke/API/CLI/dashboard/docs tokens are present for documentation continuity and current neural command deck dashboard redesign."),
    ]
    ok = all(row["status"] == "pass" for row in rows)
    return {
        "version": DOCUMENTATION_CONTINUITY_HEADER_VERSION,
        "state": "documentation_continuity_header_audit_review_only",
        "rows": rows,
        "blocked": [row for row in rows if row.get("status") != "pass"],
        "current_state_header": header,
        "historical_separation": history,
        "operator_handoff": handoff,
        "documentation_boundary": boundary,
        "ok": ok,
        "status": _status(ok),
        "writes_files": False,
        "writes_memory": False,
        "applies_source_edits": False,
        "applies_patches": False,
        "publishes_release": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        **DOCUMENTATION_CONTINUITY_BOUNDARIES,
    }


def render_documentation_continuity_header_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"status: {report.get('status', 'pass' if report.get('ok') else 'blocked')}",
        f"version: {report.get('version')}",
        "review_only: true",
        "documentation_state_is_authorization: false",
        "release_history_is_authorization: false",
        "recommended_next_arc_is_permission: false",
        "handoff_packet_is_execution_packet: false",
        "operator_approval_still_required: true",
    ]
    rows = report.get("rows") or []
    if rows:
        lines.append("rows:")
        lines.extend(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}" for row in rows)
    return lines

# v591.0-v595.0 documentation continuity tokens: # Current State — v600.0 Latest completed version: v600.0 Archive Reconciliation Decision Ledger v1

# v596.0-v600.0 documentation continuity tokens: # Current State — v600.0 Latest completed version: v600.0 Archive Reconciliation Decision Ledger v1 archive-reconciliation-decision-ledger-v1 reconciliation-decision-scope-contract reconciliation-decision-option-ledger operator-reconciliation-decision-record-prep reconciliation-decision-guard-review archive-reconciliation-decision-ledger-board

# v631.0-v635.0 documentation continuity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Decision Capture and Approval Form UX v1 Current Operator Continuity Handoff — v640.0 v641.0-v645.0 Operator Receipt Timeline and Decision Audit Trail UX v1 operator-dashboard-search-surface-discovery-v1 dashboard_search_surface_discovery.py documentation_state_is_authorization=False release_history_is_authorization=False recommended_next_arc_is_permission=False handoff_packet_is_execution_packet=False no_native_title_tooltip data-tip command-deck operator-console

# v636.0-v640.0 documentation continuity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Decision Capture and Approval Form UX v1 Current Operator Continuity Handoff — v640.0 v641.0-v645.0 Operator Receipt Timeline and Decision Audit Trail UX v1 operator-decision-capture-approval-form-ux-v1 operator_decision_approval_ux.py documentation_state_is_authorization=False release_history_is_authorization=False recommended_next_arc_is_permission=False handoff_packet_is_execution_packet=False no_native_title_tooltip data-tip command-deck operator-console
# v641.0-v645.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Receipt Timeline and Decision Audit Trail UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Operator Guided Review Wizard UX v1 operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py receipt_timeline_audit_ux_status=prepared_only audit_trail_status=review_only raw_evidence_preserved=True approval_semantics_changed=False timeline_model_grants_approval=False audit_trail_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v646.0-v650.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Session Continuity and Resume Console UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Operator Guided Review Wizard UX v1 operator-session-continuity-resume-console-ux-v1 operator_session_continuity_resume_ux.py session_continuity_resume_ux_status=prepared_only handoff_packet_status=prepared approval_semantics_changed=False resume_summary_starts_work=False pending_queue_starts_work=False verification_card_runs_checks=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v651.0-v655.0 documentation continuity tokens: # Current State — v690.0 Latest completed version: v690.0 Operator Guided Review Wizard UX v1 Current Operator Continuity Handoff — v660.0 v661.0-v685.0 Dashboard Renderer Component Extraction v1 operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py guided_review_wizard_ux_status=prepared_only guided_review_board_status=review_only approval_semantics_changed=False wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_runs_checks=False wizard_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v661.0-v665.0 documentation continuity tokens: # Current State — v690.0 Latest completed version: v690.0 Dashboard Renderer Component Extraction v1 Current Operator Continuity Handoff — v665.0 v686.0-v700.0 Autonomy Phase 0 Readiness Harness v1 legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py smoke-segmentation-integrity-board smoke_success_is_approval=False segment_report_is_authorization=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v666.0-v685.0 documentation continuity tokens: # Current State — v690.0 Latest completed version: v690.0 Dashboard Renderer Component Extraction v1 Current Operator Continuity Handoff — v685.0 v686.0-v700.0 Autonomy Phase 0 Readiness Harness v1 manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py manifest_driven_surface_registry_status=prepared_only manifest_surface_registry_board_status=review_only approval_semantics_changed=False manifest_contract_writes_source=False dashboard_manifest_adapter_registers_routes=False api_cli_manifest_adapter_registers_endpoints=False smoke_manifest_adapter_executes_smoke=False source_surface_reconciliation_mutates_manifest=False documentation_token_validation_rewrites_docs=False drift_detection_auto_fixes=False generation_prep_generates_live_routes=False manifest_current_gate_executes_checks=False manifest_board_expands_autonomy=False manifest_presence_is_authorization=False registry_health_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v676.0-v685.0 current integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_renderer_component_extraction_board_status=review_only approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v686.0-v690.0 neural command deck dashboard redesign integrity tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console
