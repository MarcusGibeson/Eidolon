from __future__ import annotations

from pathlib import Path
from typing import Any

SMOKE_SEGMENT_REGISTRY_VERSION = "500.0"

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
    if "dashboard-route-health" in lowered or "dashboard-route" in lowered or "lazy-render" in lowered or "tooltip-regression" in lowered:
        return "install-dashboard"
    if "memory-lifecycle" in lowered or "lifecycle-review-board" in lowered:
        return "install-memory"
    if "authorization-firewall" in lowered or "authorization-" in lowered:
        return "install-governance"
    if "documentation-continuity" in lowered or "documentation-" in lowered or "current-state-header" in lowered:
        return "install-governance"
    if "read-only-observation" in lowered or "observation-" in lowered or "operator-observation" in lowered:
        return "install-governance"
    if "autonomy-readiness" in lowered or "autonomy-" in lowered or "phase-based-autonomy" in lowered:
        return "install-governance"
    if "source-surface-manifest" in lowered or "duplicate-cleanup" in lowered or "duplicate-definition" in lowered:
        return "install-governance"
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
    if 'SMOKE_SEGMENT_REGISTRY_VERSION = "500.0"' not in docs:
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
