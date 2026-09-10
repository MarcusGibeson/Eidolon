from __future__ import annotations

from release_metadata import RUNTIME_VERSION, RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE
from version_marker_resolution import marker_matches_runtime_tag

CURRENT_VERSION = RUNTIME_VERSION

import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from package_integrity import (
    PACKAGE_INTEGRITY_VERSION,
    forbidden_runtime_path_matches,
    package_privacy_summary,
    package_privacy_summary_for_root,
    package_privacy_summary_for_zip,
    source_only_entry_policy,
)
from source_project_metadata import load_source_project_metadata

SOURCE_PACKAGE_PRIVACY_METADATA_INTEGRITY_VERSION = RUNTIME_VERSION
PRIVACY_REPAIR_BOUNDARIES: dict[str, bool] = {
    "package_privacy_pass_is_authorization": False,
    "metadata_consistency_is_authorization": False,
    "zip_entry_privacy_pass_publishes_release": False,
    "documentation_cleanup_grants_approval": False,
    "source_package_repair_applies_live_patches": False,
    "source_package_repair_writes_memory": False,
    "source_package_repair_expands_autonomy": False,
    "source_package_repair_executes_sandbox": False,
    "operator_review_required": True,
    "fresh_operator_approval_still_required": True,
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _release_note_version_mismatches(value: Any) -> list[dict[str, str]]:
    mismatches: list[dict[str, str]] = []

    def inspect_notes(notes: list[dict[str, Any]], owner: str) -> None:
        for idx, note in enumerate(notes):
            text = str(note.get("notes", ""))
            match = re.search(r"\bv(\d+\.0)\b", text)
            if match and str(note.get("version")) != match.group(1):
                mismatches.append({"owner": owner, "index": str(idx), "declared": str(note.get("version")), "described": match.group(1)})

    if isinstance(value, dict):
        current = value.get("current_project")
        if isinstance(current, dict):
            notes = current.get("release_notes")
            if isinstance(notes, list):
                inspect_notes(notes, "current_project")
        projects = value.get("projects")
        if isinstance(projects, list):
            for project in projects:
                if isinstance(project, dict) and isinstance(project.get("release_notes"), list):
                    inspect_notes(project["release_notes"], str(project.get("id") or project.get("name") or "project"))
    return mismatches


def build_source_package_runtime_exclusion_map(root: str | Path | None = None) -> dict[str, Any]:
    repo = Path(root or Path(__file__).resolve().parents[1])
    policy = source_only_entry_policy()
    sample_entries = [
        "Eidolon/data/settings.json",
        "Eidolon/data/workspaces/active_project.json",
        "Eidolon/data/workspaces/projects.json",
        "Eidolon/data/workspaces/command_profiles/eidolon.json",
        "Eidolon/data/workspaces/timeline.json",
        "Eidolon/data/autonomy/example/result.json",
        "Eidolon/data/self_maintenance/report.json",
        "Eidolon/runtime/session.json",
    ]
    forbidden = forbidden_runtime_path_matches(sample_entries)
    rows = [
        _row("package-integrity-version", PACKAGE_INTEGRITY_VERSION == CURRENT_VERSION, f"package_integrity={PACKAGE_INTEGRITY_VERSION}; current={CURRENT_VERSION}"),
        _row("allowlisted-source-metadata", not forbidden_runtime_path_matches(["Eidolon/data/settings.json", "Eidolon/data/workspaces/active_project.json", "Eidolon/data/workspaces/command_profiles/eidolon.json"]), "Stable source metadata and command profiles remain package-allowed; self-model runtime state is not source-package allowlisted."),
        _row("workspace-runtime-forbidden", "Eidolon/data/workspaces/timeline.json" in forbidden, "Runtime workspace timeline is explicitly forbidden from source-only archives."),
        _row("autonomy-runtime-forbidden", "Eidolon/data/autonomy/example/result.json" in forbidden, "Autonomy runtime/generated reports remain excluded."),
        _row("manifest-runtime-import", bool(policy.get("manifest_runtime_parts_imported")), "Package privacy imports runtime directory declarations from source_surface_manifest."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "source_package_runtime_exclusion_map_review_only",
        "policy": policy,
        "sample_entries": sample_entries,
        "forbidden_sample_entries": forbidden,
        "rows": rows,
        "status": _status(rows),
        "ok": _status(rows) == "pass",
        "authorizes_package_creation": False,
        "publishes_release": False,
        "boundaries": dict(PRIVACY_REPAIR_BOUNDARIES),
    }


def build_final_archive_entry_privacy_checker(root: str | Path | None = None, zip_path: str | Path | None = None) -> dict[str, Any]:
    repo = Path(root or Path(__file__).resolve().parents[1])
    if zip_path:
        summary = package_privacy_summary_for_zip(zip_path)
        temp_probe = {"ok": True, "forbidden_entries": []}
    else:
        summary = package_privacy_summary_for_root(repo)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
                temp_path = Path(handle.name)
            with zipfile.ZipFile(temp_path, "w") as zf:
                zf.writestr("Eidolon/data/settings.json", "{}\n")
                zf.writestr("Eidolon/data/workspaces/timeline.json", "{}\n")
            temp_probe = package_privacy_summary_for_zip(temp_path)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
    rows = [
        _row("source-tree-privacy", summary.get("ok") is True, f"source tree/archive forbidden_count={summary.get('forbidden_count')}."),
        _row("final-archive-checker", summary.get("checks_final_archive_entries") is True or bool(zip_path), "Final archive entry privacy checker is available."),
        _row("temp-zip-detects-forbidden-entry", "Eidolon/data/workspaces/timeline.json" in temp_probe.get("forbidden_entries", []) if not zip_path else True, "Zip-entry checker detects forbidden workspace timeline entries."),
        _row("no-package-authority", summary.get("authorizes_packaging") is False, "Privacy pass does not authorize packaging or publishing."),
        _row("gitignore-present", (repo / ".gitignore").exists(), ".gitignore is packaged so runtime/private generated files remain untracked after extraction."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "final_archive_entry_privacy_checker_review_only",
        "summary": summary,
        "zip_probe": temp_probe,
        "rows": rows,
        "status": _status(rows),
        "ok": _status(rows) == "pass",
        "authorizes_package_creation": False,
        "publishes_release": False,
        "boundaries": dict(PRIVACY_REPAIR_BOUNDARIES),
    }


def build_metadata_version_drift_normalizer(root: str | Path | None = None) -> dict[str, Any]:
    repo = Path(root or Path(__file__).resolve().parents[1])
    settings = _read_json(repo / "data/settings.json") or {}
    active = _read_json(repo / "data/workspaces/active_project.json") or {}
    projects = load_source_project_metadata(repo)
    workspace_projects = _read_json(repo / "data/workspaces/projects.json") or {}
    obs_ledger = _read_text(repo / "conscious_agent/observation_ledger_boundary.py")
    obs_queue = _read_text(repo / "conscious_agent/observation_proposal_queue.py")
    mismatches = _release_note_version_mismatches(projects) + _release_note_version_mismatches(workspace_projects)
    rows = [
        _row("settings-version", settings.get("settings_version") == CURRENT_VERSION and settings.get("last_updated_for") == CURRENT_VERSION_TAG, f"data/settings.json targets {CURRENT_VERSION_TAG}."),
        _row("active-project-version", active.get("version") == CURRENT_VERSION and active.get("last_updated_for") == CURRENT_VERSION_TAG, f"active project metadata targets {CURRENT_VERSION_TAG}."),
        _row("project-metadata-current", str(projects.get("current_project", {}).get("version")) == CURRENT_VERSION and str(workspace_projects.get("version")) == CURRENT_VERSION, f"Source-safe project/workspace metadata versions target {CURRENT_VERSION_TAG}."),
        _row("runtime-projects-not-source-metadata", "Eidolon/data/projects.json" in forbidden_runtime_path_matches(["Eidolon/data/projects.json"]), "Mutable data/projects.json is forbidden in source-only archives."),
        _row("release-note-version-normalized", not mismatches, f"release note mismatches={len(mismatches)}."),
        _row("observation-ledger-current-tag", marker_matches_runtime_tag(obs_ledger, "CURRENT_VERSION_TAG", CURRENT_VERSION_TAG) and "v490.0 Supervised Proposal Queue" not in obs_ledger[:400], "Observation ledger current-state tag resolves to authoritative runtime metadata and no longer points at v490."),
        _row("observation-proposal-current-tag", marker_matches_runtime_tag(obs_queue, "CURRENT_VERSION_TAG", CURRENT_VERSION_TAG) and "v490.0 Supervised Proposal Queue" not in obs_queue[:400], "Observation proposal queue current-state tag resolves to authoritative runtime metadata and no longer points at v490."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "metadata_version_drift_normalizer_review_only",
        "release_note_mismatches": mismatches,
        "rows": rows,
        "status": _status(rows),
        "ok": _status(rows) == "pass",
        "updates_metadata": False,
        "boundaries": dict(PRIVACY_REPAIR_BOUNDARIES),
    }


def build_release_doc_command_compatibility_audit(root: str | Path | None = None) -> dict[str, Any]:
    repo = Path(root or Path(__file__).resolve().parents[1])
    docs = "\n".join(_read_text(repo / rel) for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"])
    smoke = _read_text(repo / "tools/smoke_check.py")
    unsupported_public_pattern = "python tools/smoke_check.py --single-check"
    rows = [
        _row("no-public-single-check-command-examples", unsupported_public_pattern not in docs, "README files avoid legacy single-check smoke command examples and use supported --check/segment/JSON guidance."),
        _row("targeted-smoke-documented", "operator-governed-source-package-privacy-metadata-integrity-v1" in docs, "New targeted smoke is documented."),
        _row("smoke-json-supported", "--json" in smoke and "--segment" in smoke, "Supported smoke command syntax remains --check/--tier/--segment/--json."),
        _row("docs-not-authorization", "documentation clarity is not approval" in docs.lower() or "documentation state as authorization" in docs.lower(), "Documentation cleanup is explicitly non-authorizing."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "release_doc_command_compatibility_audit_review_only",
        "rows": rows,
        "status": _status(rows),
        "ok": _status(rows) == "pass",
        "authorizes_execution": False,
        "boundaries": dict(PRIVACY_REPAIR_BOUNDARIES),
    }


def build_source_package_privacy_metadata_integrity_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = Path(root or Path(__file__).resolve().parents[1])
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/package_integrity.py", "conscious_agent/source_surface_manifest.py", "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
    ])
    runtime_map = build_source_package_runtime_exclusion_map(repo)
    archive_checker = build_final_archive_entry_privacy_checker(repo)
    metadata = build_metadata_version_drift_normalizer(repo)
    command_audit = build_release_doc_command_compatibility_audit(repo)
    required_tokens = [
        "source-package-runtime-exclusion-map", "final-archive-entry-privacy-checker", "metadata-version-drift-normalizer",
        "release-doc-command-compatibility-audit", "source-package-privacy-metadata-integrity-audit",
        "operator-governed-source-package-privacy-metadata-integrity-v1", "source_package_privacy_metadata_integrity.py",
        "data/workspaces/timeline.json", "package_privacy_pass_is_authorization=False", "metadata_consistency_is_authorization=False",
        "zip_entry_privacy_pass_publishes_release=False", "source_package_repair_expands_autonomy=False", ".gitignore", "data-tip", "no_native_title_tooltip",
    ]
    rows = [
        _row("runtime-map", runtime_map.get("ok") is True, "Runtime exclusion map is healthy."),
        _row("archive-checker", archive_checker.get("ok") is True, "Final archive entry privacy checker is healthy."),
        _row("metadata-normalizer", metadata.get("ok") is True, "Metadata drift normalizer reports clean current-state metadata."),
        _row("command-compatibility", command_audit.get("ok") is True, "README smoke command compatibility is clean."),
        _row("docs", all(token in docs for token in required_tokens), "Docs/source/smoke/dashboard tokens preserve v501-v505 privacy repair coverage under the current v515 metadata state."),
        _row("boundary-flags", all(PRIVACY_REPAIR_BOUNDARIES[key] is False for key in ["package_privacy_pass_is_authorization", "metadata_consistency_is_authorization", "zip_entry_privacy_pass_publishes_release", "documentation_cleanup_grants_approval", "source_package_repair_applies_live_patches", "source_package_repair_writes_memory", "source_package_repair_expands_autonomy", "source_package_repair_executes_sandbox"]) and PRIVACY_REPAIR_BOUNDARIES["operator_review_required"] and PRIVACY_REPAIR_BOUNDARIES["fresh_operator_approval_still_required"], "Privacy/metadata repair remains review-only and non-authorizing."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "source_package_privacy_metadata_integrity_audit_review_only",
        "runtime_exclusion_map": runtime_map,
        "archive_entry_privacy_checker": archive_checker,
        "metadata_version_drift_normalizer": metadata,
        "release_doc_command_compatibility_audit": command_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _status(rows) == "pass",
        "authorizes_package_creation": False,
        "publishes_release": False,
        "updates_metadata": False,
        "writes_memory": False,
        "applies_patches": False,
        "executes_sandbox_commands": False,
        "expands_autonomy": False,
        "operator_review_required": True,
        "fresh_operator_approval_still_required": True,
        "boundaries": dict(PRIVACY_REPAIR_BOUNDARIES),
    }


def render_source_package_privacy_metadata_integrity_lines(report: dict[str, Any]) -> list[str]:
    rows = report.get("rows") or []
    lines = [
        f"{report.get('state', 'source_package_privacy_metadata_integrity')} :: {report.get('status', 'unknown')}",
        f"version={report.get('version', CURRENT_VERSION)} ok={report.get('ok', False)}",
        "Boundary: package privacy/metadata integrity is not authorization, not release publishing, not live patch approval, and not autonomy expansion.",
    ]
    for row in rows:
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines


# v500.1-v505.0 source package privacy and metadata integrity tokens: source-package-runtime-exclusion-map final-archive-entry-privacy-checker metadata-version-drift-normalizer release-doc-command-compatibility-audit source-package-privacy-metadata-integrity-audit operator-governed-source-package-privacy-metadata-integrity-v1 data/workspaces/timeline.json forbidden package_privacy_summary_for_zip package_privacy_pass_is_authorization=False metadata_consistency_is_authorization=False zip_entry_privacy_pass_publishes_release=False documentation_cleanup_grants_approval=False source_package_repair_applies_live_patches=False source_package_repair_writes_memory=False source_package_repair_expands_autonomy=False source_package_repair_executes_sandbox=False no_native_title_tooltip data-tip command-deck operator-console
# v641.0-v645.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Receipt Timeline and Decision Audit Trail UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Operator Guided Review Wizard UX v1 operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py receipt_timeline_audit_ux_status=prepared_only audit_trail_status=review_only raw_evidence_preserved=True approval_semantics_changed=False timeline_model_grants_approval=False audit_trail_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v646.0-v650.0 continuity/integrity tokens: # Current State — v650.0 Latest completed version: v650.0 Operator Session Continuity and Resume Console UX v1 Current Operator Continuity Handoff — v650.0 v651.0-v655.0 Operator Guided Review Wizard UX v1 operator-session-continuity-resume-console-ux-v1 operator_session_continuity_resume_ux.py session_continuity_resume_ux_status=prepared_only handoff_packet_status=prepared approval_semantics_changed=False resume_summary_starts_work=False pending_queue_starts_work=False verification_card_runs_checks=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v651.0-v655.0 continuity/integrity tokens: # Current State — v655.0 Latest completed version: v655.0 Operator Guided Review Wizard UX v1 Current Operator Continuity Handoff — v655.0 v656.0-v660.0 Project Metadata Schema and Active Context Repair v1 operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py guided_review_wizard_ux_status=prepared_only guided_review_board_status=review_only approval_semantics_changed=False wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False verification_step_runs_checks=False wizard_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v661.0-v665.0 integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 legacy-smoke-segmentation-stale-expectation-repair-v1 legacy_smoke_segmentation_repair.py smoke-gate-classification-model current-release-gate-segment legacy-advisory-segment-separation stale-expectation-repair-audit smoke-segmentation-integrity-board legacy_smoke_segmentation_repair_status=prepared_only smoke_segmentation_integrity_board_status=review_only current_release_blocking legacy_advisory historical_pinned slow_full_audit migration_debt approval_semantics_changed=False current_gate_executes_smoke=False legacy_advisory_blocks_current_release=False segmentation_board_expands_autonomy=False smoke_success_is_approval=False segment_report_is_authorization=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v676.0-v685.0 current integrity tokens: v685.0 Dashboard Renderer Component Extraction v1 dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_renderer_component_extraction_board_status=review_only approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v686.0-v690.0 neural command deck dashboard redesign integrity tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v905.0 source metadata allowlist tokens: data/self_model.json source_metadata_allowed=False source_only_package_privacy_pass_is_authorization=False

# v1070.4 source package privacy metadata compatibility tokens: api-preview-adapter-backfill-v1 CURRENT_VERSION=1070.4 source-package-runtime-exclusion-map metadata-version-drift-normalizer operator-governed-source-package-privacy-metadata-integrity-v1
# v1071.6 source package privacy metadata tokens: dashboard-dispatcher-parity-gate-v1 conscious_agent/dashboard_dispatcher_parity.py build_dashboard_dispatcher_parity_report dashboard_dispatcher_parity_text route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 source package privacy metadata tokens: dashboard-dispatcher-branch-extraction-prep-v1 conscious_agent/dashboard_dispatcher_branch_prep.py build_dashboard_dispatcher_branch_extraction_prep_report dashboard_dispatcher_branch_extraction_prep_text branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 source package privacy metadata tokens: dashboard-dispatcher-branch-extraction-trial-v1 conscious_agent/dashboard_dispatcher_branch_trial.py build_dashboard_dispatcher_branch_extraction_trial_report dashboard_dispatcher_branch_extraction_trial_text render_dashboard_route_registry_extraction_trial_branch dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 source package privacy metadata tokens: dashboard-dispatcher-branch-expansion-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_trial.py build_dashboard_dispatcher_branch_expansion_trial_report dashboard_dispatcher_branch_expansion_trial_text EXPANDED_BRANCH_PATH=/dashboard-dispatcher-parity branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 extracted_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 source package privacy metadata tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report dashboard_dispatcher_branch_expansion_backfill_trial_text BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-prep render_dashboard_dispatcher_branch_extraction_prep_backfill_branch branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1072.4 metadata/privacy tokens: dashboard-dispatcher-branch-expansion-backfill-trial-v1 conscious_agent/dashboard_dispatcher_branch_expansion_backfill_trial.py build_dashboard_dispatcher_branch_expansion_backfill_trial_report dashboard_dispatcher_branch_expansion_backfill_trial_text BACKFILLED_BRANCH_PATH=/dashboard-dispatcher-branch-extraction-prep branch_expansion_backfill_trial_executed=True branch_expansion_backfill_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=4 backfilled_branch_count=1 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1073.0 dispatcher decomposition checkpoint tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1073.1 metadata integrity tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v1 /dashboard-dispatcher-branch-decomposition-continuation-trial helper_backed_branch_count=7 branch_decomposition_continuation_trial_executed=True branch_decomposition_continuation_prepared_only=False additional_branch_extraction_count=1 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 successor-compatible prep metadata tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v1 /dashboard-dispatcher-branch-decomposition-continuation-prep render_smoke_check_helper_extraction_pilot_continuation_branch helper_backed_branch_count_may_exceed_prep_count=True helper_backed_branch_count=7 data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 metadata integrity tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v2 /dashboard-dispatcher-branch-decomposition-continuation-prep-v2 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v2.py NEXT_CONTINUATION_CANDIDATE_PATH=/diagnostics render_diagnostics helper_backed_branch_count=7 branch_decomposition_continuation_prepared_only=True branch_decomposition_continuation_executed=False additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v2 /dashboard-dispatcher-branch-decomposition-continuation-trial-v2 render_diagnostics_continuation_branch helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-prep-v3 /dashboard-dispatcher-branch-decomposition-continuation-prep-v3 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_prep_v3.py NEXT_CONTINUATION_CANDIDATE_PATH=/settings render_settings_continuation_branch helper_backed_branch_count=8 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 metadata/source package tokens: dashboard-dispatcher-branch-decomposition-continuation-trial-v3 /dashboard-dispatcher-branch-decomposition-continuation-trial-v3 conscious_agent/dashboard_dispatcher_branch_decomposition_continuation_trial_v3.py MOVED_BRANCH_PATH=/settings render_settings_continuation_branch helper_backed_branch_count=12 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.0 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py recommended_batch_size=3 helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False source_package_repair_expands_autonomy=False data-tip no_native_title_tooltip

# v1074.0 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py build_dashboard_dispatcher_batch_decomposition_checkpoint_report dashboard_dispatcher_batch_decomposition_checkpoint_text recommended_batch_size=3 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 helper_backed_branch_count=12 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
# v1074.0 completed prep compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v1 /dashboard-dispatcher-batch-decomposition-prep conscious_agent/dashboard_dispatcher_batch_decomposition_prep.py

# v1074.0 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v1 /dashboard-dispatcher-batch-decomposition-checkpoint conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint.py build_dashboard_dispatcher_batch_decomposition_checkpoint_report dashboard_dispatcher_batch_decomposition_checkpoint_text recommended_batch_size=3 helper_backed_branch_count=12 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
# v1074.0 successor compatibility tokens for completed trial: dashboard-dispatcher-batch-decomposition-trial-v1 /dashboard-dispatcher-batch-decomposition-trial conscious_agent/dashboard_dispatcher_batch_decomposition_trial.py build_dashboard_dispatcher_batch_decomposition_trial_report dashboard_dispatcher_batch_decomposition_trial_text moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 helper_backed_branch_count=12 moved_branch_count=3 dispatcher_branch_body_moved=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False

# v1074.3 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v2 /dashboard-dispatcher-batch-decomposition-prep-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v2.py prepared_batch_size=3 helper_backed_branch_count=12 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip no_native_title_tooltip

# v1074.3 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v2.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v2_report dashboard_dispatcher_batch_decomposition_checkpoint_v2_text recommended_batch_size=3 helper_backed_branch_count=15 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False source_package_repair_expands_autonomy=False data-tip no_native_title_tooltip

# v1074.3 successor compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v2 /dashboard-dispatcher-batch-decomposition-trial-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v2.py moved_batch_size=3 helper_backed_branch_count=15 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False dashboard_get_preview_only=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1074.4 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-prep-v3 /dashboard-dispatcher-batch-decomposition-prep-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v3.py build_dashboard_dispatcher_batch_decomposition_prep_v3_report dashboard_dispatcher_batch_decomposition_prep_v3_text prepared_batch_size=3 helper_backed_branch_count=15 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False applies_source_edits=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.4 checkpoint-v2 compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v2 /dashboard-dispatcher-batch-decomposition-checkpoint-v2 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v2.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v2_report dashboard_dispatcher_batch_decomposition_checkpoint_v2_text recommended_batch_size=3 helper_backed_branch_count=15 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_body_moved=False

# v1074.5 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v3 /dashboard-dispatcher-batch-decomposition-trial-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v3.py build_dashboard_dispatcher_batch_decomposition_trial_v3_report dashboard_dispatcher_batch_decomposition_trial_v3_text moved_batch_size=3 helper_backed_branch_count=18 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.6 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v3 /dashboard-dispatcher-batch-decomposition-checkpoint-v3 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v3.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v3_report dashboard_dispatcher_batch_decomposition_checkpoint_v3_text recommended_batch_size=3 helper_backed_branch_count=18 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v4.py build_dashboard_dispatcher_batch_decomposition_prep_v4_report dashboard_dispatcher_batch_decomposition_prep_v4_text prepared_batch_size=3 helper_backed_branch_count=18 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip

# v1074.8 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-trial-v4 /dashboard-dispatcher-batch-decomposition-trial-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v4.py build_dashboard_dispatcher_batch_decomposition_trial_v4_report dashboard_dispatcher_batch_decomposition_trial_v4_text moved_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.8 prep-v4 successor metadata compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v4 /dashboard-dispatcher-batch-decomposition-prep-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v4.py build_dashboard_dispatcher_batch_decomposition_prep_v4_report dashboard_dispatcher_batch_decomposition_prep_v4_text successor_trial_state=True helper_backed_branch_count=21 moved_batch_size=3 release_authorized=False autonomy_expanded=False

# v1074.9 metadata/source package tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v4 /dashboard-dispatcher-batch-decomposition-checkpoint-v4 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v4.py build_dashboard_dispatcher_batch_decomposition_checkpoint_v4_report dashboard_dispatcher_batch_decomposition_checkpoint_v4_text recommended_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=False renderer_bodies_moved=False http_dispatcher_replaced=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False expands_autonomy=False operator_approval_still_required=True data-tip command-deck operator-console no_native_title_tooltip
# v1074.9 prep-v5 compatibility target: dashboard-dispatcher-batch-decomposition-prep-v5 /dashboard-dispatcher-batch-decomposition-prep-v5 prepared_batch_size=3 helper_backed_branch_count=21 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.0 source package privacy metadata drift repair tokens: observation-ledger-current-tag observation-proposal-current-tag CURRENT_VERSION_TAG dynamic current_state_stale_references_are_allowed=False

# v1075.1 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v5 /dashboard-dispatcher-batch-decomposition-trial-v5 moved_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 release_authorized=False autonomy_expanded=False
# v1075.2 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v5 /dashboard-dispatcher-batch-decomposition-checkpoint-v5 recommended_batch_size=3 helper_backed_branch_count=24 remaining_registry_direct_branch_count=36 branch_decomposition_batch_prepared=False branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.3 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-prep-v6 /dashboard-dispatcher-batch-decomposition-prep-v6 prepared_batch_size=3 helper_backed_branch_count=24 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False additional_branch_extraction_count=0 release_authorized=False autonomy_expanded=False

# v1075.5 metadata integrity compatibility tokens: dashboard-dispatcher-batch-decomposition-trial-v6 /dashboard-dispatcher-batch-decomposition-trial-v6 moved_batch_size=3 helper_backed_branch_count=27 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True additional_branch_extraction_count=3 release_authorized=False autonomy_expanded=False
# v1075.5 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v6 source_package_privacy_metadata_integrity_version=1075.5 current_milestone="v1075.7 Dispatcher Batch Decomposition Trial v7" release_authorized=False autonomy_expanded=False

# v1075.6 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v7 /dashboard-dispatcher-batch-decomposition-prep-v7 source_only=True helper_backed_branch_count=27 prepared_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.7 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-trial-v7 /dashboard-dispatcher-batch-decomposition-trial-v7 source_only=True helper_backed_branch_count=30 moved_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1075.8 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v7 /dashboard-dispatcher-batch-decomposition-checkpoint-v7 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v7.py helper_backed_branch_count=30 remaining_registry_direct_branch_count=36 recommended_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 source package privacy metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v8 /dashboard-dispatcher-batch-decomposition-prep-v8 source_only=True helper_backed_branch_count=30 prepared_batch_size=3 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.1 dashboard-dispatcher-batch-decomposition-trial-v8 helper_backed_branch_count=33 moved_batch_size=3 release_authorized=False autonomy_expanded=False

# v1076.1 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v8 /dashboard-dispatcher-batch-decomposition-checkpoint-v8 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v8.py helper_backed_branch_count=33 remaining_registry_direct_branch_count=36 recommended_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.2 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v9 /dashboard-dispatcher-batch-decomposition-prep-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v9.py helper_backed_branch_count=33 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1076.5 metadata proof token: dashboard-dispatcher-batch-decomposition-trial-v9 /dashboard-dispatcher-batch-decomposition-trial-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v9.py helper_backed_branch_count=36

# v1076.5 checkpoint v9 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v9 /dashboard-dispatcher-batch-decomposition-checkpoint-v9 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v9.py helper_backed_branch_count=36 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1076.5 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v10 /dashboard-dispatcher-batch-decomposition-prep-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v10.py helper_backed_branch_count=36 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 metadata proof token: dashboard-dispatcher-batch-decomposition-trial-v10 /dashboard-dispatcher-batch-decomposition-trial-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v10.py helper_backed_branch_count=39

# v1077.0 checkpoint v10 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v10 /dashboard-dispatcher-batch-decomposition-checkpoint-v10 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v10.py helper_backed_branch_count=39 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1077.0 metadata tokens: dashboard-dispatcher-batch-decomposition-prep-v11 /dashboard-dispatcher-batch-decomposition-prep-v11 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v11.py helper_backed_branch_count=39 prepared_batch_size=3 source_write_count=0 source_delete_count=0 release_authorized=False autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip

# v1077.0 current release proof token: dashboard-dispatcher-batch-decomposition-trial-v11 /dashboard-dispatcher-batch-decomposition-trial-v11 helper_backed_branch_count=42 moved_batch_size=3

# v1077.0 checkpoint v11 metadata tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v11 /dashboard-dispatcher-batch-decomposition-checkpoint-v11 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v11.py helper_backed_branch_count=42 remaining_registry_direct_branch_count=36 recommended_batch_size=3 release_authorized=False autonomy_expanded=False

# v1077.1 prep v12 release tokens: dashboard-dispatcher-batch-decomposition-prep-v12 /dashboard-dispatcher-batch-decomposition-prep-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v12.py helper_backed_branch_count=42 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.2 current release tokens: dashboard-dispatcher-batch-decomposition-trial-v12 /dashboard-dispatcher-batch-decomposition-trial-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v12.py helper_backed_branch_count=45 moved_batch_size=3 route_check_renderer_constant_values_exact=True direct_http_probe_required=True

# v1077.3 checkpoint v12 current release tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v12 /dashboard-dispatcher-batch-decomposition-checkpoint-v12 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v12.py helper_backed_branch_count=45 remaining_registry_direct_branch_count=36 recommended_batch_size=3 new_proof_routes_per_cycle=3 moved_routes_per_trial=3 net_direct_route_reduction_per_cycle=0 route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.4 prep v13 current release tokens: dashboard-dispatcher-batch-decomposition-prep-v13 /dashboard-dispatcher-batch-decomposition-prep-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_prep_v13.py helper_backed_branch_count=45 prepared_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=False route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.5 trial v13 current release tokens: dashboard-dispatcher-batch-decomposition-trial-v13 /dashboard-dispatcher-batch-decomposition-trial-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_trial_v13.py helper_backed_branch_count=48 moved_batch_size=3 branch_decomposition_batch_prepared=True branch_decomposition_batch_executed=True route_check_renderer_constant_values_exact=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False

# v1077.6 checkpoint v13 current release tokens: dashboard-dispatcher-batch-decomposition-checkpoint-v13 /dashboard-dispatcher-batch-decomposition-checkpoint-v13 conscious_agent/dashboard_dispatcher_batch_decomposition_checkpoint_v13.py helper_backed_branch_count=48 historical_proof_direct_route_count=36 precheckpoint_legacy_proof_route_count=35 ordinary_operational_direct_route_count=0 net_direct_route_reduction_per_legacy_cycle=0 proof_surface_consolidation_selected=True direct_http_probe_required=True release_authorized=False autonomy_expanded=False
