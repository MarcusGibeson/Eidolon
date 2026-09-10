from __future__ import annotations

from release_metadata import RUNTIME_VERSION

from pathlib import Path
from typing import Any

SMOKE_SEGMENT_REGISTRY_VERSION = RUNTIME_VERSION
SMOKE_SEGMENT_NAMES = [
    "install-core",
    "install-release",
    "install-dashboard",
    "install-governance",
    "install-expression",
    "install-live-trial",
    "install-memory",
    "install-regression-recent",
]

SMOKE_SEGMENT_BOUNDARIES: dict[str, bool] = {
    "segment_registry_runs_checks_automatically": False,
    "segment_runner_treats_pass_as_approval": False,
    "segmented_install_applies_patches": False,
    "segmented_install_writes_memory": False,
    "segmented_install_expands_autonomy": False,
    "segmented_install_invokes_models": False,
    "segment_report_is_authorization": False,
    "operator_review_required": True,
    "resume_metadata_required": True,
    "full_install_smoke_remains_available": True,
}


def classify_check_name(name: str, tier: str = "install") -> str:
    lowered = name.lower()
    if tier in {"fast", "loop", "readiness", "build", "patch"}:
        return "install-core"
    if "dashboard-route-registry-extraction" in lowered or "dashboard-renderer-metadata-extraction" in lowered or "dashboard-dispatcher-parity" in lowered or "dashboard-dispatcher-branch-extraction" in lowered:
        return "install-release"
    if "dashboard-route-health" in lowered or "dashboard-route" in lowered or "lazy-render" in lowered or "tooltip-regression" in lowered:
        return "install-dashboard"
    if "memory-lifecycle" in lowered or "lifecycle-review-board" in lowered:
        return "install-memory"
    if "authorization-firewall" in lowered or "authorization-" in lowered:
        return "install-governance"
    if "documentation-continuity" in lowered or "documentation-" in lowered or "current-state-header" in lowered:
        return "install-governance"
    if "sandbox-execution-dry-run" in lowered or "dry-run-receipt" in lowered or "transcript-preview" in lowered or "diff-receipt" in lowered or "dry-run-misinterpretation" in lowered:
        return "install-governance"
    if "operator-decision-capture" in lowered or "decision-capture-form" in lowered or "scope-target-binding" in lowered or "expiration-burnout-form" in lowered or "denial-deferral-revision" in lowered or "operator-decision-approval-ux" in lowered:
        return "install-dashboard"
    if "operator-receipt-timeline" in lowered or "decision-audit-trail" in lowered or "operator-decision-timeline" in lowered or "approval-burnout-consumption" in lowered or "blocked-action-safety-event" in lowered or "verification-receipt-timeline" in lowered:
        return "install-dashboard"
    if "operator-guided-review-wizard" in lowered or "guided-review-wizard" in lowered or "guided-evidence-warning" in lowered or "guided-decision-approval" in lowered or "guided-verification-resume" in lowered:
        return "install-dashboard"
    if "dashboard-renderer-component" in lowered or "dashboard-component-contract" in lowered or "shared-review-packet-renderer" in lowered or "shared-boundary-matrix-renderer" in lowered or "shared-evidence-warning-renderer" in lowered or "shared-decision-approval-renderer" in lowered or "shared-resume-continuity-renderer" in lowered or "dashboard-route-renderer-adapter" in lowered or "dashboard-style-regression-guard" in lowered or "legacy-renderer-duplication-audit" in lowered:
        return "install-dashboard"
    if "sandbox-execution-approval" in lowered or "approval-gate" in lowered or "approval-burnout" in lowered or "command-allowlist" in lowered:
        return "install-governance"
    if "manual-observation-to-sandbox" in lowered or "observation-to-sandbox" in lowered or "sandbox-packet" in lowered or "sandbox-candidate" in lowered:
        return "install-governance"
    if "read-only-observation" in lowered or "observation-" in lowered or "operator-observation" in lowered:
        return "install-governance"
    if "autonomy-readiness" in lowered or "autonomy-" in lowered or "phase-based-autonomy" in lowered:
        return "install-governance"
    if "archive-reconciliation-application" in lowered or "reconciliation-application" in lowered or "dry-run-application" in lowered:
        return "install-governance"
    if "operator-command-center-ui" in lowered or "command-center" in lowered or "operator-queue-panel" in lowered or "safety-state-panel" in lowered or "workflow-navigation" in lowered or "system-health-summary" in lowered:
        return "install-dashboard"
    if "operator-action-semantics" in lowered or "universal-action-label" in lowered or "blocked-action-explanation" in lowered or "one-time-approval-burnout" in lowered or "safe-preview-before-action" in lowered:
        return "install-dashboard"
    if "current-state-integrity" in lowered or "staleness-hardening" in lowered or "stale-version" in lowered:
        return "install-regression-recent"
    if "source-surface-manifest" in lowered or "duplicate-cleanup" in lowered or "duplicate-definition" in lowered:
        return "install-governance"
    if "dashboard-api-smoke-shared-utility-adoption" in lowered:
        return "install-release"
    if "dashboard-review-component-extraction-pilot" in lowered:
        return "install-release"
    if "smoke-check-helper-extraction-pilot" in lowered:
        return "install-release"
    if "api-preview-adapter-extraction-pilot" in lowered:
        return "install-release"
    if "api-preview-adapter-backfill" in lowered:
        return "install-release"
    if "api-server-dispatch-route-table" in lowered or "api-server-dispatch-helper-backfill" in lowered or "api-server-dispatch-helper-extraction-pilot" in lowered or "api-server-dispatch-helper" in lowered:
        return "install-release"
    if "audited-sandbox-backend-evidence-interface" in lowered:
        return "install-release"
    if "dashboard-dispatcher-branch-extraction-prep" in lowered or "dashboard-dispatcher-branch" in lowered:
        return "install-release"
    if "dashboard-dispatcher-parity" in lowered or "dashboard-renderer-metadata-extraction" in lowered or "dashboard-route-registry-extraction" in lowered:
        return "install-release"
    if "smoke-check-decomposition-extraction" in lowered or "smoke-result-formatting" in lowered:
        return "install-release"
    if "smoke-registry-check-row-extraction" in lowered or "smoke-registry-check-rows" in lowered:
        return "install-release"
    if "smoke-registry-metadata-extraction" in lowered or "smoke-registry-metadata" in lowered:
        return "install-release"
    if "manifest-fixture-receipt-consolidation" in lowered or "fixture-receipt" in lowered or "receipt-consolidation" in lowered:
        return "install-release"
    if any(token in lowered for token in ["release", "package", "candidate", "signing", "install"]):
        return "install-release"
    if any(token in lowered for token in ["dashboard", "api", "cli", "surface", "route"]):
        return "install-dashboard"
    if any(token in lowered for token in ["governance", "approval", "consent", "boundary", "kernel", "safety"]):
        return "install-governance"
    if any(token in lowered for token in ["expression", "behavioral", "conversational"]):
        return "install-expression"
    if any(token in lowered for token in ["memory", "continuity", "identity", "belief", "lesson"]):
        return "install-memory"
    if any(token in lowered for token in ["live", "trial", "patch-history", "burnout", "replay"]):
        return "install-live-trial"
    if any(token in lowered for token in ["modular", "refactor", "self-maintenance", "registry", "regression"]):
        return "install-regression-recent"
    return "install-core"


def build_smoke_segment_registry_summary(checks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    checks = list(checks or [])
    segments = {name: [] for name in SMOKE_SEGMENT_NAMES}
    for check in checks:
        name = str(check.get("name", ""))
        tier = str(check.get("tier", "install"))
        segment = check.get("segment") or classify_check_name(name, tier)
        segments.setdefault(str(segment), []).append(name)
    coverage = {name: len(items) for name, items in segments.items()}
    return {
        "version": SMOKE_SEGMENT_REGISTRY_VERSION,
        "state": "segmented_install_smoke_registry_review_only",
        "segments": segments,
        "coverage": coverage,
        "segment_count": len(segments),
        "registered_check_count": sum(coverage.values()),
        "empty_segments": [name for name, items in segments.items() if not items],
        "boundaries": dict(SMOKE_SEGMENT_BOUNDARIES),
        "runs_checks_automatically": False,
        "treats_pass_as_approval": False,
        "review_only": True,
        "ok": not [name for name, items in segments.items() if not items],
    }


def build_segment_resume_metadata_summary(segment: str, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    results = list(results or [])
    failed = [row for row in results if not row.get("ok")]
    completed = [str(row.get("name", "")) for row in results if row.get("ok")]
    return {
        "version": SMOKE_SEGMENT_REGISTRY_VERSION,
        "state": "install_smoke_segment_resume_metadata",
        "segment": segment,
        "completed_count": len(completed),
        "failed_count": len(failed),
        "last_completed_check": completed[-1] if completed else None,
        "next_recommended_segment": None if failed else segment,
        "failed": failed,
        "operator_review_required": True,
        "treats_pass_as_approval": False,
        "ok": not failed,
    }


def build_segmented_install_smoke_audit_summary(registry: dict[str, Any] | None = None, docs: str = "") -> dict[str, Any]:
    registry = dict(registry or build_smoke_segment_registry_summary([]))
    boundaries = dict(SMOKE_SEGMENT_BOUNDARIES)
    blockers: list[str] = []
    if registry.get("segment_count", 0) < len(SMOKE_SEGMENT_NAMES):
        blockers.append("segment registry incomplete")
    if registry.get("empty_segments"):
        blockers.append("empty smoke segments:" + ",".join(registry.get("empty_segments", [])))
    if "v405.0 - Segmented Install Smoke and Self-Maintenance Confirmation Hardening v1" not in docs:
        blockers.append("docs missing v405.0")
    if 'SMOKE_SEGMENT_REGISTRY_VERSION = "1035.0"' not in docs:
        blockers.append("version marker missing")
    for key, value in boundaries.items():
        if key in {"operator_review_required", "resume_metadata_required", "full_install_smoke_remains_available"}:
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": SMOKE_SEGMENT_REGISTRY_VERSION,
        "state": "segmented_install_smoke_audit_review_only",
        "registry": registry,
        "boundaries": boundaries,
        "blockers": blockers,
        "ok": not blockers,
        "status": "pass" if not blockers else "blocked",
        "applies_patches": False,
        "writes_memory": False,
        "expands_autonomy": False,
        "invokes_models": False,
        "treats_smoke_pass_as_authorization": False,
        "safe_next_action": "Operator may run a named smoke segment and review resume metadata. Segment success is not approval for patches, memory writes, releases, or autonomous continuation.",
    }

# v445.1-v450.0 authorization firewall segment tokens: operator-governed-authorization-firewall-v1 authorization-firewall-audit install-governance firewall_pass_is_authorization=False segment_report_is_authorization=False
# v450.1-v455.0 metadata release integrity segment tokens: operator-governed-metadata-release-integrity-v1 metadata-release-integrity-audit install-release metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False segment_report_is_authorization=False
# v455.1-v460.0 authorization firewall signal triage segment tokens: operator-governed-authorization-firewall-signal-triage-v1 authorization-firewall-signal-triage-audit install-governance pass_with_warnings_supported=True plain_pass_with_warnings_forbidden=True mechanism_pass_is_not_language_clear=True language_clear_is_not_authorization=True authorization_status=not_authorized segment_report_is_authorization=False

# v460.1-v465.0 route surface parity segment tokens: operator-governed-route-surface-parity-v1 route-surface-parity-audit install-dashboard route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False surface_parity_is_permission=False smoke_success_is_approval=False route_health_confirms_render_status_only=True route_health_does_not_authorize_execution=True segment_report_is_authorization=False
# v465.1-v470.0 duplicate shadow cleanup segment tokens: operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 self-maintenance-duplicate-shadow-cleanup-audit install-regression-recent duplicate_cleanup_is_authorization=False classification_is_permission_to_delete=False shadow_removal_expands_autonomy=False stale_gate_cleanup_authorizes_execution=False cleanup_applies_live_patches=False cleanup_writes_memory=False segment_report_is_authorization=False

# v470.1-v480.0 documentation continuity segment tokens: operator-governed-documentation-continuity-header-v1 documentation-continuity-header-audit install-governance documentation_state_is_authorization=False release_history_is_authorization=False recommended_next_arc_is_permission=False handoff_packet_is_execution_packet=False current_state_header_creates_approval=False documentation_cleanup_writes_memory=False documentation_cleanup_applies_source_edits=False documentation_cleanup_expands_autonomy=False segment_report_is_authorization=False

# v475.1-v480.0 operator observation prep segment tokens: operator-invoked-read-only-observation-prep-v1 operator-read-only-observation-audit install-governance observation_is_authorization=False observation_is_execution=False observation_grants_followup_permission=False observation_writes_source=False observation_writes_memory=False observation_updates_metadata=False observation_schedules_work=False observation_invokes_models_by_default=False observation_creates_approval=False operator_invocation_required=True single_run_read_only=True segment_report_is_authorization=False
# v480.1-v485.0 observation ledger boundary segment tokens: operator-governed-observation-ledger-boundary-v1 observation-ledger-boundary-audit install-governance ledger_presence_is_approval=False ledger_completeness_is_authorization=False observation_history_permits_future_action=False receipt_is_approval=False hidden_scheduling_allowed=False automatic_continuation_allowed=False segment_report_is_authorization=False
# v485.1-v490.0 observation proposal queue segment tokens: operator-governed-observation-proposal-queue-v1 observation-proposal-queue-audit install-governance mapping_is_approval=False proposal_candidate_is_execution_packet=False candidate_queue_is_authorization=False queue_presence_is_approval=False queue_ranking_is_authorization=False highest_ranked_proposal_auto_selected=False approved_for_packet_drafting_only_is_live_execution=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False patch_application_allowed=False proposal_approval_allowed=False automatic_continuation_allowed=False observation_promotes_to_live_change=False segment_report_is_authorization=False

# v490.1-v495.0 sandbox autonomy boundary segment tokens: operator-governed-sandbox-autonomy-boundary-prep-v1 sandbox-autonomy-boundary-prep-audit install-governance sandbox_scope_is_authorization=False sandbox_readiness_is_approval=False sandbox_target_description_is_permission_to_execute=False sandbox_success_is_live_authorization=False sandbox_verification_is_approval=False sandbox_output_is_patch_execution_packet=False sandbox_trial_completion_permits_source_mutation=False promotion_requires_fresh_single_use_operator_approval=True live_source_writes_allowed=False memory_writes_allowed=False real_patch_application_allowed=False release_candidate_creation_allowed=False automatic_scheduling_allowed=False local_model_invocation_by_default_allowed=False approval_creation_allowed=False sandbox_execution_allowed=False segment_report_is_authorization=False

# v495.1-v500.0 autonomy readiness review board segment tokens: operator-governed-autonomy-readiness-review-board-v1 autonomy-readiness-review-board-audit install-governance readiness_status=not_ready_for_autonomy authorization_status=not_authorized readiness_review_is_autonomy_approval=False board_pass_grants_authorization=False phase_definition_authorizes_phase=False sandbox_boundary_exists_means_execute=False operator_discussion_is_approval=False proposal_ranking_is_selection=False observation_history_authorizes_monitoring=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False sandbox_execution_allowed=False live_source_writes_allowed=False approval_creation_allowed=False release_candidate_creation_allowed=False segment_report_is_authorization=False
# v500.1-v505.0 package privacy metadata integrity segment tokens: operator-governed-source-package-privacy-metadata-integrity-v1 source-package-privacy-metadata-integrity-audit install-release package_privacy_pass_is_authorization=False metadata_consistency_is_authorization=False zip_entry_privacy_pass_publishes_release=False documentation_cleanup_grants_approval=False source_package_repair_expands_autonomy=False segment_report_is_authorization=False

# v505.1-v510.0 manual observation-to-sandbox bridge segment tokens: manual-observation-to-sandbox-packet-bridge-v1 manual-observation-to-sandbox-bridge-audit install-governance observation_report_is_approval=False candidate_ranking_is_operator_selection=False sandbox_packet_exists_is_execution_permission=False sandbox_readiness_is_authorization=False packet_assembly_executes_sandbox=False bridge_status=prepared authorization_status=not_authorized execution_status=not_executed autonomy_status=not_autonomous segment_report_is_authorization=False

# v510.1-v515.0 sandbox execution approval gate segment tokens: sandbox-execution-approval-gate-v1 install-governance approval_contract_exists_is_approval_granted=False confirmation_phrase_generated_is_confirmation_entered=False command_preview_executes_commands=False approval_status=not_granted execution_status=not_executed sandbox_status=not_started autonomy_status=not_autonomous segment_report_is_authorization=False

# v515.1-v520.0 sandbox execution dry-run receipt segment tokens: sandbox-execution-dry-run-receipt-v1 install-governance dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_pass_is_approval=False dry_run_success_is_authorization=False dry_run_receipt_status=prepared actual_execution_status=not_executed approval_status=not_granted authorization_status=not_authorized sandbox_status=not_started autonomy_status=not_autonomous segment_report_is_authorization=False

# v520.1-v525.0 first sandbox execution trial smoke segment token: first-operator-approved-sandbox-execution-trial-v1 install-governance sandbox_execution_status=not_run_by_default autonomy_status=not_autonomous

# v525.1-v530.0 sandbox execution runner smoke segment tokens: operator-approved-sandbox-execution-runner-v1 install-governance runner_contract_exists_is_execution_permission=False phrase_validated_is_command_executed=False sandbox_command_success_is_live_patch_approval=False receipt_success_is_future_authorization=False runner_status=available_under_approval_only execution_status=not_executed_by_default approval_status=required live_source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False

# v530.1-v540.0 sandbox-to-source promotion packet smoke segment tokens: sandbox-to-source-promotion-packet-v1 install-governance sandbox_evidence_exists_is_live_source_approval=False promotion_diff_preview_is_live_source_mutation=False rollback_packet_exists_is_rollback_executed=False promotion_packet_status=prepared live_source_status=untouched approval_status=required rollback_status=planned_not_executed release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False
# v535.1-v540.0 narrow live patch promotion gate smoke segment tokens: operator-approved-narrow-live-patch-promotion-gate-v1 install-governance live_patch_scope_defined_is_live_patch_approved=False approval_phrase_template_is_operator_approval=False preflight_pass_is_live_patch_permission=False live_promotion_readiness_is_live_promotion_authorization=False live_patch_gate_status=defined live_patch_status=not_applied approval_status=required source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False
# v540.1-v545.0 first narrow live patch application trial smoke segment tokens: first-single-use-narrow-live-patch-application-trial-v1 install-governance candidate_selected_is_live_patch_approved=False approval_receipt_template_is_approval_granted=False application_harness_exists_is_patch_applied=False candidate_selection_is_approval=False approval_receipt_template_is_approval=False preflight_pass_is_patch_permission=False sandbox_success_is_live_patch_permission=False one_live_approval_is_future_approval=False live_patch_success_is_future_authorization=False trial_status=prepared live_patch_status=not_applied_by_default approval_status=required source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous segment_report_is_authorization=False
# v545.1-v550.0 current version staleness smoke segment tokens: current-version-staleness-and-post-patch-verification-v1 install-governance historical_version_references_are_blocked=False current_state_stale_references_are_allowed=False matching_version_marker_alone_is_metadata_integrity=False verification_plan_exists_is_patch_applied=False stale_audit_pass_is_live_patch_permission=False stale_audit_pass_is_release_approval=False stale_version_audit_status=clean_or_blocked metadata_current_state_status=aligned_or_blocked post_patch_verification_status=prepared live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous segment_report_is_authorization=False

# v550.1-v551.0 evidence intake segment tokens: post-live-patch-evidence-intake-contract-v1 install-governance evidence_intake_status=awaiting_operator_supplied_evidence verification_receipt_status=not_supplied rollback_status=not_executed segment_report_is_authorization=False smoke_success_is_approval=False

# v552.0-v555.0 post live patch verification rollback segment tokens: post-live-patch-verification-and-rollback-trial-v1 install-governance verification_receipt_status=awaiting_operator_supplied_evidence rollback_status=planned_not_executed receipt_review_does_not_execute_commands=True rollback_plan_is_rollback_execution=False regression_audit_pass_is_release_approval=False trial_board_is_autonomy_approval=False segment_report_is_authorization=False smoke_success_is_approval=False

# v556.0-v565.0 recovery drill release closure segment tokens: recovery-drill-and-release-closure-v1 install-governance recovery_drill_status=prepared_not_executed rollback_decision_status=review_prepared release_closure_status=evidence_prepared closure_approval_status=required recovery_board_is_rollback_permission=False recovery_board_is_release_approval=False recovery_board_executes_commands=False recovery_board_executes_rollback=False segment_report_is_authorization=False smoke_success_is_approval=False

# v561.0-v565.0 release candidate integrity handoff segment tokens: release-candidate-integrity-and-operator-handoff-v1 install-governance release_candidate_status=prepared_not_created package_integrity_status=review_prepared verification_evidence_status=matrix_prepared operator_handoff_status=prepared release_status=not_created publish_status=not_authorized candidate_board_is_release_creation=False candidate_board_is_publish_approval=False candidate_board_executes_commands=False candidate_board_creates_release=False candidate_board_publishes_release=False segment_report_is_authorization=False smoke_success_is_approval=False

# v566.0-v570.0 release decision archive ledger segment tokens: release-decision-and-archive-ledger-v1 install-governance release_decision_status=prepared_for_operator operator_decision_status=required archive_ledger_status=prepared_not_written_externally archive_integrity_status=review_prepared release_decision_board_is_release_approval=False release_decision_board_is_publish_permission=False release_decision_board_selects_decision=False release_decision_board_writes_external_archive=False release_decision_board_executes_commands=False segment_report_is_authorization=False smoke_success_is_approval=False

# v571.0-v575.0 release archive continuity index segment tokens: release-archive-retrieval-and-continuity-index-v1 install-governance archive_retrieval_status=prepared_read_only continuity_index_status=prepared historical_reference_status=classified stale_current_reference_status=blocked_if_detected retrieval_packet_status=prepared archive_continuity_board_is_release_approval=False archive_continuity_board_is_publish_permission=False archive_continuity_board_writes_archive=False archive_continuity_board_executes_commands=False segment_report_is_authorization=False smoke_success_is_approval=False

# v576.0-v580.0 release archive search handoff segment tokens: release-archive-search-and-handoff-review-v1 install-governance archive_search_status=prepared_read_only release_record_query_status=matrix_prepared search_result_review_status=prepared archive_handoff_status=prepared archive_write_status=not_performed archive_search_board_is_release_approval=False archive_search_board_is_publish_permission=False archive_search_board_writes_archive=False archive_search_board_executes_commands=False segment_report_is_authorization=False smoke_success_is_approval=False
# v581.0-v585.0 release archive export closure segment tokens: release-archive-export-and-decision-closure-v1 install-governance archive_export_status=prepared_not_written_externally export_packet_status=prepared operator_decision_closure_status=required archive_export_integrity_status=review_prepared external_archive_write_status=not_performed archive_export_board_is_release_approval=False archive_export_board_is_publish_permission=False archive_export_board_writes_external_archive=False archive_export_board_executes_commands=False segment_report_is_authorization=False smoke_success_is_approval=False

# v586.0-v590.0 smoke registry tokens: release-archive-import-and-closure-recall-v1 archive_import_status=prepared_not_written import_packet_status=review_prepared closure_recall_status=historical_review_prepared imported_archive_continuity_status=guarded current_state_mutation_status=not_performed

# v591.0-v595.0 smoke registry tokens: imported-archive-conflict-reconciliation-v1 archive_conflict_status=detected_or_review_prepared conflict_classification_status=matrix_prepared reconciliation_option_status=prepared_for_operator conflict_guard_status=guarded current_state_mutation_status=not_performed archive_write_status=not_performed

# v596.0-v600.0 smoke registry tokens: archive-reconciliation-decision-ledger-v1 reconciliation_decision_status=operator_required decision_ledger_status=prepared_not_written_externally operator_decision_record_status=prepared_not_supplied decision_guard_status=guarded current_state_mutation_status=not_performed archive_write_status=not_performed external_ledger_write_status=not_performed decision_ledger_board_is_operator_approval=False decision_ledger_board_is_release_approval=False decision_ledger_board_is_publish_permission=False decision_ledger_board_selects_decision=False decision_ledger_board_executes_decision=False decision_ledger_board_writes_external_ledger=False decision_ledger_board_writes_archive_records=False segment_report_is_authorization=False smoke_success_is_approval=False
# v601.0-v605.0 smoke registry tokens: current-state-integrity-staleness-hardening-v1 smoke_summary_version_status=aligned_or_blocked nested_metadata_root_version_status=aligned_or_blocked readme_current_handoff_status=current_or_historical_only setup_smoke_scope_status=bounded_install_segment hardening_report_writes_source=False hardening_report_writes_metadata=False hardening_report_executes_smoke=False audit_pass_is_release_approval=False audit_pass_is_live_patch_permission=False segment_report_is_authorization=False smoke_success_is_approval=False
# v606.0-v610.0 smoke registry tokens: archive-reconciliation-application-prep-v1 application_prep_status=prepared_only dry_run_receipt_status=prepared_not_executed application_prep_board_is_operator_approval=False application_prep_board_writes_archive_records=False application_prep_board_mutates_current_state=False segment_report_is_authorization=False smoke_success_is_approval=False

# v611.0-v615.0 smoke segment registry tokens: operator-command-center-ui-consolidation-v1 command-center-landing-screen operator-queue-panel safety-state-panel workflow-navigation-groups system-health-summary-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False

# v616.0-v620.0 smoke segment registry tokens: dashboard-workflow-simplification-legacy-drawer-v1 workflow-group-route-index legacy-route-drawer archive-workflow-pipeline-view patch-safety-memory-group-views dashboard-simplification-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False

# v621.0-v625.0 smoke segment registry tokens: operator-action-semantics-approval-ux-v1 universal-action-label-standard blocked-action-explanation-cards one-time-approval-burnout-ux safe-preview-before-action-summary operator-action-semantics-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False

# v626.0-v630.0 smoke segment registry tokens: review-packet-readability-evidence-ux-v1 review-packet-summary-header evidence-grouping-priority-layout receipt-ledger-readability-cards system-health-evidence-ux review-packet-evidence-ux-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False raw_evidence_preserved=True
# v631.0-v635.0 smoke segment registry tokens: operator-dashboard-search-surface-discovery-v1 surface-search-index route-module-smoke-discovery-cards workflow-aware-search-filters current-historical-surface-guard dashboard-search-discovery-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False raw_routes_preserved=True legacy_surfaces_preserved=True

# v636.0-v640.0 smoke segment registry tokens: operator-decision-capture-approval-form-ux-v1 decision-capture-form-schema approval-scope-target-binding-panel approval-expiration-burnout-form-ux denial-deferral-revision-decision-capture operator-decision-approval-ux-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False approval_semantics_changed=False
# v641.0-v645.0 smoke segment registry tokens: operator-receipt-timeline-decision-audit-trail-ux-v1 operator-decision-timeline-model approval-burnout-consumption-timeline-cards blocked-action-safety-event-timeline-cards verification-receipt-timeline-cards decision-audit-trail-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False raw_evidence_preserved=True audit_trail_status=review_only

# v646.0-v650.0 smoke segment registry tokens: operator-session-continuity-resume-console-ux-v1 session-resume-state-summary unresolved-warning-blocker-carryover pending-decisions-prepared-work-resume-queue verification-state-resume-card operator-session-continuity-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False handoff_packet_is_approval=False continuity_board_expands_autonomy=False

# v651.0-v655.0 smoke segment registry tokens: operator-guided-review-wizard-ux-v1 guided-review-wizard-entry-model guided-evidence-warning-step-cards guided-decision-approval-step-ux guided-verification-resume-step-summary operator-guided-review-wizard-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False guided_review_board_status=review_only wizard_board_expands_autonomy=False

# v656.0-v660.0 smoke segment registry tokens: project-metadata-schema-active-context-repair-v1 metadata-schema-contract active-project-resolution-audit project-status-rendering-hardening release-note-version-semantics-audit metadata-integrity-board-smoke-gate install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False metadata_integrity_board_status=review_only metadata_integrity_board_expands_autonomy=False

# v661.0-v665.0 smoke segment classification tokens: legacy-smoke-segmentation-stale-expectation-repair-v1 current_release_blocking current_release_advisory legacy_advisory historical_pinned slow_full_audit migration_debt install-core install-governance install-live-trial install-memory install-release install-regression-recent legacy_advisory_blocks_current_release=False smoke_success_is_approval=False segment_report_is_authorization=False smoke_segmentation_integrity_board_status=review_only segmentation_board_expands_autonomy=False

# v666.0-v685.0 smoke segment registry tokens: manifest-driven-surface-registry-v1 surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False manifest_presence_is_authorization=False registry_health_is_approval=False manifest_surface_registry_board_status=review_only manifest_board_expands_autonomy=False

# v676.0-v685.0 smoke segment registry tokens: dashboard-renderer-component-extraction-v1 dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board install-dashboard segment_report_is_authorization=False smoke_success_is_approval=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False component_board_expands_autonomy=False

# v686.0-v690.0 neural command deck dashboard redesign integrity tokens: v690.0 Neural Command Deck Dashboard Redesign v1 neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only approval_semantics_changed=False layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 smoke segment registry tokens: neural-command-deck-interaction-refinement-v1 interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board current_release_blocking legacy_advisory no_native_title_tooltip data-tip command-deck operator-console

# v696.0-v700.0 autonomy phase zero readiness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only approval_semantics_changed=False phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v1066.1-v1069.0 bundled milestone smoke segment tokens: audited-sandbox-backend-preflight-contract-v1 sandbox-backend-capability-evidence-gate-v1 fixture-execution-admission-gate-v1 sandboxed-fixture-execution-trial-v1 sandboxed-fixture-batch-execution-v1 generated-dispatch-promotion-readiness-ledger-v1 source-decomposition-batch-i-v1 autonomy-phase-zero-observation-contract-v1 install-release actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.1 source decomposition batch ii smoke segment tokens: source-decomposition-batch-ii-v1 review-surface-shared-v1 install-release actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.1 dashboard API smoke shared utility adoption smoke segment tokens: dashboard-api-smoke-shared-utility-adoption-v1 sandbox-backend-adapter-skeleton-v1 review-surface-shared-v1 install-release actual_fixture_execution_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.1 dashboard review component extraction pilot smoke segment tokens: dashboard-review-component-extraction-pilot-v1 render_review_card_component render_review_table_component install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.2 smoke check helper extraction smoke segment tokens: smoke-check-helper-extraction-pilot-v1 smoke-check-shared-v1 read_docs_bundle missing_required_tokens authority_boundary_violations smoke_token_validation_row install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.3 API preview adapter extraction smoke segment tokens: api-preview-adapter-extraction-pilot-v1 api-preview-adapter-shared-v1 build_api_preview_envelope api_preview_adapter_rows install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.5 API preview adapter backfill smoke segment tokens: api-preview-adapter-backfill-v1 api-preview-adapter-backfill-v1 build_api_preview_envelope api_preview_adapter_backfill_rows install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.5 API server dispatch helper extraction smoke segment tokens: api-server-dispatch-helper-extraction-pilot-v1 api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_rows install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.7 API server dispatch helper backfill smoke segment tokens: api-server-dispatch-helper-backfill-v1 api-server-dispatch-helper-shared-v1 source_surface_route_matches build_manual_preview_dispatch_payload api_dispatch_helper_backfill_rows install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.7 API server dispatch route table smoke segment tokens: api-server-dispatch-helper-route-table-extraction-v1 api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 audited_os_sandbox_backend_integrated=False sandbox_backend_adapter_integrated=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.8 API server dispatch route table backfill smoke segment tokens: api-server-dispatch-route-table-backfill-v1 api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows api_dispatch_route_table_backfill_rows build_route_table_preview_payload install-release route_table_backfilled_route_count=1 route_table_route_count=3 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1070.9 API server dispatch route table safety parity smoke segment tokens: api-server-dispatch-route-table-safety-parity-v1 api-server-dispatch-route-table-v1 API_SERVER_DISPATCH_ROUTE_TABLE api_dispatch_route_table_rows build_route_table_preview_payload build_manual_preview_dispatch_payload install-release route_table_payload_manual_helper_parity=True route_table_safety_key_parity=True route_table_safe_preview_row_count=4 route_table_newly_migrated_route_count=1 old_direct_branch_removed=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 audited_os_sandbox_backend_integrated=False actual_fixture_execution_allowed=False generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False no_native_title_tooltip data-tip command-deck operator-console

# v1071.5 audited sandbox evidence interface smoke segment tokens: audited-sandbox-backend-evidence-interface-v1 install-release sandbox_backend_admitted=False fixture_execution_remains_blocked=True route_table_safe_preview_row_count=5 superseded_rows_have_replacements=True release_docs_monotonic=True cold_dashboard_performance_diagnosis_recorded=True actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False data-tip command-deck operator-console no_native_title_tooltip

# v1071.5 smoke check decomposition extraction smoke segment tokens: smoke-check-decomposition-extraction-v1 smoke-result-formatting-v1 tools/smoke_result_formatting.py build_smoke_summary validate_smoke_summary_honesty INSTALL_RELEASE_SUPERSEDED_REPLACEMENTS install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False

# v1071.5 smoke registry metadata extraction smoke segment tokens: smoke-registry-metadata-extraction-v1 smoke-registry-metadata-v1 tools/smoke_registry_metadata.py SMOKE_TIER_ORDER FALLBACK_SMOKE_SEGMENT_NAMES allowed_tiers_for fallback_segment_names install-release actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False

# v1071.5 smoke registry check row extraction segment tokens: smoke-registry-check-row-extraction-v1 tools/smoke_registry_check_rows.py SMOKE_REGISTRY_CHECK_ROW_SPECS build_smoke_checks_from_specs manual_smoke_remains_authoritative=True check_discovery_changed=False check_execution_changed=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False

# v1071.5 dashboard route registry extraction segment tokens: dashboard-route-registry-extraction-v1 install-release dashboard_route_registry.py DASHBOARD_ROUTE_REGISTRY_ITEMS manual_dashboard_remains_authoritative=True http_dispatcher_changed=False renderer_bodies_moved=False actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False autonomy_expanded=False smoke_success_is_approval=False segment_report_is_authorization=False data-tip command-deck operator-console no_native_title_tooltip
# v1071.6 dashboard dispatcher parity segment tokens: dashboard-dispatcher-parity-gate-v1 install-release route_registry_renderer_metadata_dispatcher_parity=True dispatcher_branches_moved=False renderer_bodies_moved=False
# v1072.3 dashboard dispatcher branch extraction prep segment tokens: dashboard-dispatcher-branch-extraction-prep-v1 install-release branch_extraction_prepared_only=True branch_extraction_executed=False dispatcher_branches_moved=False renderer_bodies_moved=False http_dispatcher_changed_for_candidates=False

# v1072.3 dashboard dispatcher branch extraction trial segment tokens: dashboard-dispatcher-branch-extraction-trial-v1 install-release dispatcher_branch_helper_adopted=True dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True branch_extraction_executed=True branch_extraction_prepared_only=False extracted_branch_count=1 renderer_bodies_moved=False http_dispatcher_replaced=False

# v1072.3 dashboard dispatcher branch extraction expansion prep segment tokens: dashboard-dispatcher-branch-expansion-trial-v1 install-release branch_expansion_trial_executed=True branch_expansion_prepared_only=False additional_branch_extraction_count=1 existing_helper_backed_branch_count=3 dispatcher_branch_condition_moved=False dispatcher_branch_body_moved=True renderer_bodies_moved=False http_dispatcher_replaced=False

# v1073.0 dispatcher decomposition checkpoint tokens: dashboard-dispatcher-branch-expansion-backfill-prep-v2 dashboard-dispatcher-branch-expansion-backfill-trial-v2 dashboard-dispatcher-branch-expansion-backfill-prep-v3 dashboard-dispatcher-branch-expansion-backfill-trial-v3 dashboard-dispatcher-branch-decomposition-hardening-v1 eidolon-v1073-source-review-checkpoint-v1 helper_backed_branch_count=6 actual_fixture_execution_count=0 subprocess_spawn_count=0 source_write_count=0 source_delete_count=0 generated_wiring_activated=False release_authorized=False review_only=True autonomy_expanded=False data-tip command-deck operator-console no_native_title_tooltip
