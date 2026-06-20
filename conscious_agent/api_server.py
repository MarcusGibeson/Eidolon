from __future__ import annotations

import json
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from approval_manager import approve_approval, get_approval, list_approvals, reject_approval
from chat_action_router import execute_chat_action, list_chat_actions, load_chat_action, propose_chat_action
from dashboard_chat_console import create_dashboard_chat_turn, list_dashboard_chat_turns, load_dashboard_chat_turn
from diagnostics import build_diagnostic_report, list_diagnostic_reports, load_diagnostic_report, save_diagnostic_report
from goal_manager import add_goal, get_goal, list_goals
from maintenance_advisor import list_maintenance_scans, load_maintenance_scan, run_maintenance_scan
from memory import load_memories
from notification_manager import (
    clear_dismissed_notifications,
    list_notifications,
    load_notification,
    update_notification_status,
)
from patch_suggester import list_patch_proposals, load_patch_proposal, suggest_patch
from task_patch_bridge import (
    create_patch_followup_tasks,
    create_patch_task,
    suggest_patch_for_task,
)
from work_queue_patch_bridge import (
    create_patch_followup_items,
    create_patch_work_item,
    suggest_patch_for_work_item,
)
from project_manager import get_active_project
from session_planner import create_session_plan, list_session_plans, load_session_plan
from settings_manager import get_setting, load_settings
from desktop_setup_helper import create_setup_report, list_setup_reports, load_setup_report
from desktop_onboarding_wizard import build_onboarding_run, list_onboarding_runs, load_onboarding_run
from task_queue import add_task, get_task, list_tasks, task_status_counts, update_task_fields
from work_queue import (
    add_work_item,
    find_work_item,
    list_work_items,
    summarize_queue,
    update_work_item,
)
from task_work_executor import execute_next_task_work, execute_task_work_item
from task_approval_bridge import (
    list_task_approvals,
    request_next_task_work_approval,
    request_task_work_approval,
)
from task_lifecycle import derive_task_lifecycle, list_task_lifecycles, normalize_lifecycle_stage_filter, task_lifecycle_summary
from task_recovery import (
    build_task_recovery,
    list_task_recoveries,
    mark_task_ready_for_retry,
    retry_task_work,
    task_recovery_summary,
)
from work_cycle import list_work_cycles, load_work_cycle, run_supervised_work_cycle
from stable_supervised_loop import (
    build_stable_loop_preflight,
    list_stable_loops,
    load_stable_loop,
    run_stable_supervised_loop,
)
from stable_loop_review import (
    cleanup_stable_loop_history,
    list_stable_loop_reviews,
    run_approved_stable_loop_live,
    set_stable_loop_archived,
    stable_loop_review_summary,
    update_stable_loop_review,
)
from stable_loop_audit import build_stable_loop_audit, refresh_stable_loop_audit
from stable_loop_operator_notes import (
    add_stable_loop_operator_note,
    get_stable_loop_operator_notes,
    set_stable_loop_final_decision,
    update_stable_loop_check,
)
from stable_loop_decision_report import (
    cleanup_stable_loop_decision_history,
    list_stable_loop_decision_rows,
    stable_loop_decision_summary,
)
from stable_loop_followup_tasks import (
    create_stable_loop_followup_tasks,
    create_stable_loop_followups_for_decisions,
    plan_stable_loop_followups,
    stable_loop_followup_summary,
)
from stable_loop_followup_lifecycle import (
    list_stable_loop_followup_task_rows,
    resolve_stable_loop_followups,
    resolve_task_stable_loop_followup,
    stable_loop_followup_lifecycle_summary,
    stable_loop_followup_task_row,
)
from stable_loop_followup_completion import (
    cleanup_stable_loop_followup_completions,
    list_stable_loop_followup_completion_rows,
    mark_stable_loop_followup_chain_closed,
    stable_loop_followup_completion_summary,
)
from stable_loop_guardrails import stable_loop_guardrail_summary
from stabilization_checkpoint import build_stabilization_checkpoint
from operational_readiness import (
    build_doctor_report,
    build_repair_suggestions,
    build_patch_integrity_report,
    build_project_snapshot,
    build_task_review,
    build_recovery_drill,
    build_stable_loop_confidence,
    build_hardening_report,
    build_controlled_self_build,
)
from controlled_build_cycle import (
    build_controlled_task_selection,
    build_patch_plan,
    patch_workspace_status,
    stage_controlled_patch,
    preview_staged_diff,
    apply_staged_patch,
    verify_latest_patch,
    rollback_latest_patch,
    readme_gate,
    build_controlled_build_cycle,
    build_supervised_dev_loop,
)

from project_intelligence import (
    build_codebase_map,
    build_task_dependencies,
    build_test_plan,
    build_patch_risk,
    build_patch_review,
    build_project_memory_index,
    build_workspace_status,
    build_cross_project_task_review,
    build_asymmetric_dev_loop,
)
from workspace_orchestration import (
    build_project_registry,
    register_project,
    set_active_workspace_project,
    build_project_health,
    build_command_profiles,
    build_workspace_dependency_map,
    build_workspace_task_inbox,
    switch_workspace_project,
    build_project_context,
    build_workspace_timeline,
    build_workspace_dev_loop,
)
from workspace_execution import (
    build_workspace_registry_audit,
    build_workspace_repair_suggestions,
    build_project_registration_wizard,
    build_project_boundary_check,
    build_workspace_patch_plan,
    build_workspace_preview_diff,
    build_workspace_apply,
    build_workspace_verify_latest,
    build_guarded_workspace_dev_loop,
)
from patch_drafting import (
    build_patch_draft_request,
    build_draft_patch,
    build_patch_draft_status,
    build_patch_review_notes,
    build_draft_diff,
    build_draft_test_impact,
    build_approval_gate,
    approve_draft,
    reject_draft,
    build_apply_approved_draft,
    build_rollback_approved_draft,
    reopen_draft,
    build_human_approved_patch_loop,
    build_draft_quality,
    build_draft_file_targets,
    build_draft_intent_blocks,
    build_draft_conflicts,
    build_draft_verification_bundle,
    build_draft_review_checklist,
    build_approved_draft_execution_report,
    build_review_centered_patch_loop,
)
from release_pipeline import (
    build_code_edit_proposal,
    build_safe_rewrite_preview,
    build_generated_code_patch,
    build_test_suggestions,
    build_inline_review_note,
    build_apply_approved_code_patch,
    build_prepare_release_package,
    build_release_readiness,
    build_human_approved_release_loop,
)
from code_patch_release import (
    build_code_patch_status,
    build_symbol_scan,
    build_rewrite_plan,
    build_rewrite_conflicts,
    build_code_patch_diff_bundle,
    build_apply_code_patch_transaction,
    build_semantic_checks,
    build_release_artifact,
    build_release_audit_trail,
    build_generated_code_release_loop,
)
from ai_patch_assistance import (
    build_task_to_code_patch,
    build_code_context,
    build_patch_prompt,
    build_parse_generated_edits,
    build_edit_consistency,
    build_ai_code_patch_dry_run,
    build_patch_failure_analysis,
    build_patch_learning_notes,
    build_ai_assisted_code_patch_loop,
)
from validated_ai_patch_loop import (
    build_patch_objective_refinement,
    build_code_context_ranking,
    build_patch_safety_envelope,
    build_generated_patch_validation,
    build_patch_simulation,
    build_test_stub_plan,
    build_patch_review_score,
    build_patch_recovery_plan,
    build_validated_ai_code_patch_loop,
)
from approval_release_workflow import (
    bind_current_approval_to_validated_manifest,
    build_ai_patch_review_bundle,
    build_review_bundle_integrity,
    build_approval_ready,
    build_approval_ledger,
    build_apply_validated_ai_patch,
    build_post_apply_review,
    build_package_build_plan,
    build_approval_to_release_loop,
)
from release_packaging import (
    build_release_manifest_integrity,
    build_package_inventory,
    build_package_checksums,
    build_release_notes,
    build_release_handoff_report,
    build_release_zip,
    build_verify_release_unzip,
    build_release_pipeline_audit,
    build_verified_release_package_loop,
    summarize_release_report,
    _package_name,
)
from release_installation import (
    build_release_profiles,
    build_package_privacy_scan,
    build_portable_metadata_check,
    build_first_run_check,
    build_dependency_advisor,
    build_upgrade_notes,
    build_runtime_migration_check,
    build_release_install_verification,
    build_verified_installable_release_loop,
    build_smoke_runtime_hardening,
    build_external_zip_install_verification,
    build_deterministic_release_manifest,
    build_update_dry_run_plan,
    build_atomic_source_update,
    build_runtime_migration_assistant,
    build_route_safety_harness,
    build_release_dashboard_command_center,
    build_clean_room_install_harness,
    build_verified_self_update_release_pipeline,
    build_trial_upgrade_harness,
    build_backup_rollback_drill,
    build_update_collision_detector,
    build_version_registry_report,
    build_release_provenance_report,
    build_dashboard_upgrade_wizard_preview,
    build_api_upgrade_wizard_preview,
    build_staged_apply_drill,
    build_real_apply_guard_rails,
    build_real_apply_rollback_verification,
    build_self_update_ux_polish,
    build_v23_readiness_gate,
    build_controlled_self_maintenance_loop,
    summarize_installation_report,
)
from self_maintenance import (
    build_self_maintenance_proposal_sandbox,
    build_patch_plan_builder,
    build_dry_run_patch_generator,
    build_patch_safety_auditor,
    build_apply_patch_to_temp_clone,
    build_maintenance_review_bundle,
    build_human_approval_binding,
    build_real_maintenance_patch_apply,
    build_post_apply_health_monitor,
    build_controlled_maintenance_cycle,
    build_assisted_self_improvement_release,
    build_improvement_candidate_scan,
    build_candidate_prioritizer,
    build_candidate_to_proposal_bridge,
    build_maintenance_backlog_registry,
    build_dashboard_maintenance_backlog,
    build_api_maintenance_backlog,
    build_candidate_regression_detector,
    build_release_memory_privacy,
    build_candidate_verification_recipes,
    build_assisted_improvement_cycle,
    build_semi_autonomous_maintenance_review,
    build_hotfix_regression_lockdown,
    build_dashboard_route_coverage_auditor,
    build_api_default_source_audit,
    build_nested_readiness_severity_engine,
    build_review_bundle_approval_contract,
    build_maintenance_report_diff_viewer,
    build_release_gate_composition_test,
    build_dashboard_api_parity_audit,
    build_operator_trust_report,
    build_trustworthy_maintenance_console,
    build_trust_console_drill,
    build_trust_console_snapshot,
    build_trust_console_diff,
    build_release_candidate_freezer,
    build_frozen_release_zip_verification,
    build_approval_evidence_ledger,
    build_release_command_reproducer,
    build_console_readme_consistency,
    build_pre_v27_safety_audit,
    build_release_candidate_governance,
    build_release_governance_drill,
    build_release_evidence_bundle,
    build_release_evidence_bundle_verifier,
    build_release_governance_page,
    build_governance_api_read_only_surface,
    build_release_artifact_diff,
    build_release_signing_preparation,
    build_local_trust_policy,
    build_release_governance_ux_polish,
    build_pre_v28_governance_audit,
    build_verifiable_release_evidence_system,
    build_evidence_replay_drill,
    build_evidence_bundle_persistence,
    build_replay_release_evidence,
    build_evidence_timeline,
    build_evidence_operator_summary,
    build_dashboard_evidence_viewer,
    build_api_evidence_viewer,
    build_evidence_retention_policy,
    build_evidence_regression_lockdown,
    build_pre_v29_evidence_audit,
    build_durable_release_evidence_archive,
    build_signing_readiness_audit,
    build_canonical_manifest_format,
    build_canonical_evidence_schema,
    build_release_signing_status,
    build_signature_placeholder_contract,
    build_key_policy_preparation,
    build_signature_verification_placeholder,
    build_dashboard_signing_status,
    build_api_signing_status,
    build_pre_v30_signing_prep_audit,
    build_signed_release_preparation_system,
    summarize_self_maintenance_report,
)
from dev_loop_runner import get_dev_loop, list_dev_loops, run_dev_loop
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports
from watch_mode import list_watch_reports, load_watch_report, run_watch_loop, run_watch_once


API_VERSION = "30.0"


class ApiError(Exception):
    def __init__(self, status: int, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return _to_jsonable(dict(value.__dict__))
    return value


def _ok(data: Any | None = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "api_version": API_VERSION,
        "served_at": _now(),
    }
    if data is not None:
        payload["data"] = _to_jsonable(data)
    payload.update({key: _to_jsonable(value) for key, value in extra.items()})
    return payload


def _error(status: int, message: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": False,
        "api_version": API_VERSION,
        "served_at": _now(),
        "error": message,
    }
    if details is not None:
        payload["details"] = _to_jsonable(details)
    return payload


def _path_parts(path: str) -> list[str]:
    parts = [part for part in path.strip("/").split("/") if part]
    if parts and parts[0] == "api":
        return parts[1:]
    return parts


def _query_bool(query: dict[str, list[str]], key: str, default: bool = False) -> bool:
    raw = query.get(key, [str(default)])[0]
    return str(raw).lower() in {"1", "true", "yes", "on"}


def _body_bool(data: dict[str, Any], key: str, default: bool = False) -> bool:
    if key not in data:
        return default
    raw = data.get(key)
    if isinstance(raw, bool):
        return raw
    return str(raw).lower() in {"1", "true", "yes", "on"}


def _require_confirmation(body: dict[str, Any], expected: str) -> None:
    if str(body.get("confirm", "")) != expected:
        raise ApiError(400, f"Live controlled work requires JSON field confirm={expected!r}.")


def parse_request_body(body: bytes, content_type: str = "") -> dict[str, Any]:
    if not body:
        return {}
    text = body.decode("utf-8")
    if "application/json" in content_type.lower():
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ApiError(400, f"Invalid JSON body: {error}") from error
        if not isinstance(data, dict):
            raise ApiError(400, "JSON body must be an object.")
        return data
    parsed = parse_qs(text)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _api_index() -> dict[str, Any]:
    return {
        "name": "Eidolon Local API",
        "version": API_VERSION,
        "safety": "Local-only by default. API routes call existing safety, approval, and command gates.",
        "endpoints": {
            "GET /api/status": "Overall counts and active project.",
            "GET /api/stabilization-checkpoint": "Run the v8.0 read-only stabilization checkpoint. Supports ?full=true.",
            "GET /api/doctor": "Run the v7.2/v8.0 one-command doctor report. Supports ?full=true.",
            "GET /api/repair-suggestions": "Return v7.3 self-repair suggestions.",
            "GET /api/patch-integrity": "Return v7.4 patch metadata and rollback integrity report.",
            "GET /api/project-snapshot": "Return v7.5 project state snapshot.",
            "GET /api/tasks/review": "Return v7.6 task queue lifecycle/risk review.",
            "GET /api/recovery-drill": "Run v7.7 read-only recovery drill scenarios.",
            "GET /api/stable-loops/confidence": "Return v7.8 stable-loop confidence score.",
            "GET /api/hardening-report": "Return v7.9 pre-v8 hardening report.",
            "GET /api/controlled-self-build": "Run v8.0 controlled self-build preview only. Live work is POST-only.",
            "POST /api/controlled-self-build": "Run controlled self-build; live mode requires approve=true and confirm=LIVE_CONTROLLED_BUILD.",
            "GET /api/controlled-build/select-task": "Run v8.1 controlled task selection.",
            "GET /api/controlled-build/plan-patch": "Preview v8.2 patch planner without saving workspace state.",
            "POST /api/controlled-build/plan-patch": "Run v8.2 patch planner and save workspace plan.",
            "GET /api/controlled-build/workspace": "Show v8.3 patch workspace status.",
            "GET /api/controlled-build/stage-patch": "Preview v8.3 patch staging without saving workspace state.",
            "POST /api/controlled-build/stage-patch": "Run v8.3 patch staging into data/patch_workspace.",
            "GET /api/controlled-build/preview-diff": "Preview v8.4 staged diff without saving validation state.",
            "POST /api/controlled-build/preview-diff": "Run v8.4 staged diff preview and save validation state.",
            "POST /api/controlled-build/apply-staged-patch": "Run v8.5 staged patch apply; writes only when approve=true.",
            "POST /api/controlled-build/verify-latest-patch": "Run v8.6 verification for the latest real controlled patch.",
            "POST /api/controlled-build/rollback-latest-patch": "Run v8.7 rollback; writes only when approve=true and hashes still match.",
            "GET /api/controlled-build/readme-gate": "Run v8.8 README enforcement gate.",
            "POST /api/controlled-build/cycle": "Run v8.9 full controlled build cycle; live mode requires confirmation.",
            "POST /api/supervised-dev-loop": "Run v9.0 one-cycle supervised autonomous development loop; live mode requires confirmation.",
            "GET /api/codebase-map": "Run v9.1 codebase map.",
            "GET /api/task-dependencies": "Run v9.2 dependency-aware task planning.",
            "GET /api/test-plan": "Run v9.3 test planner.",
            "GET /api/patch-risk": "Run v9.4 patch risk analyzer.",
            "GET /api/patch-review": "Run v9.5 patch review report.",
            "GET /api/project-memory-index": "Run v9.7 project memory index.",
            "GET /api/workspace-status": "Run v9.8 multi-project workspace status.",
            "GET /api/cross-project-task-review": "Run v9.9 cross-project task review.",
            "GET /api/asymmetric-dev-loop": "Run v10.0 asymmetric multi-project dev loop preview.",
            "GET /api/project-registry": "Run v10.1 workspace project registry report.",
            "POST /api/projects/register": "Register or update a workspace project.",
            "POST /api/projects/active": "Set the active workspace project.",
            "GET /api/project-health": "Run v10.2 per-project health checks. Supports ?all=true.",
            "GET /api/command-profiles": "Run v10.3 command profile report and seed default profiles.",
            "GET /api/workspace-dependency-map": "Run v10.4 cross-project dependency map.",
            "GET /api/workspace-task-inbox": "Run v10.5 workspace task inbox.",
            "POST /api/workspace/switch-project": "Safely switch active workspace project; force requires explicit body flag.",
            "GET /api/project-context": "Run v10.7 project context bundle.",
            "GET /api/workspace-timeline": "Run v10.8 workspace timeline.",
            "GET /api/workspace-dev-loop": "Run v11.0 workspace-orchestrated dev loop preview.",
            "GET /api/diagnostics/latest": "Latest diagnostic report.",
            "POST /api/diagnostics/run": "Run and save diagnostics.",
            "GET /api/watch/latest": "Latest watch report.",
            "POST /api/watch/run-once": "Run one watch check.",
            "POST /api/watch/run-loop": "Run bounded watch loop.",
            "GET /api/notifications": "List notifications.",
            "POST /api/notifications/{id}/read": "Mark notification read.",
            "POST /api/notifications/{id}/dismiss": "Dismiss notification.",
            "POST /api/notifications/clear-dismissed": "Delete dismissed notification records.",
            "GET /api/approvals": "List approval requests.",
            "POST /api/approvals/{id}/approve": "Approve through approval manager.",
            "POST /api/approvals/{id}/reject": "Reject approval request.",
            "POST /api/chat-actions": "Create a chat-to-action proposal.",
            "POST /api/chat-actions/{id}/dry-run": "Dry-run a saved chat action.",
            "POST /api/chat-actions/{id}/execute": "Execute safe action or create approval for risky action.",
            "GET /api/tasks": "List tasks.",
            "GET /api/tasks/summary": "Summarize canonical task-backed work state.",
            "GET /api/tasks/lifecycle": "Summarize task lifecycle stages derived from status, approvals, and patch metadata. Supports ?stage=... filters.",
            "GET /api/tasks/recovery": "List blocked/failed tasks with recovery recommendations.",
            "GET /api/tasks/recovery/summary": "Summarize recoverable blocked/failed tasks by category.",
            "GET /api/tasks/{id}/lifecycle": "Get one task lifecycle record.",
            "GET /api/tasks/{id}/recovery": "Get a recovery plan for one task.",
            "POST /api/tasks/request-approvals": "Create approval requests for tasks matching a lifecycle stage, normally approval_required.",
            "GET /api/tasks/{id}": "Get a task detail record.",
            "POST /api/tasks": "Create a task.",
            "POST /api/tasks/next/dry-run": "Dry-run the next safe task.",
            "POST /api/tasks/next/execute": "Execute the next safe task.",
            "POST /api/tasks/{id}/dry-run": "Dry-run one task through the task work executor.",
            "POST /api/tasks/{id}/execute": "Execute one task through the task work executor.",
            "POST /api/tasks/{id}/request-approval": "Create an approval request for executing one approval-gated task.",
            "GET /api/tasks/{id}/approvals": "List approval requests linked to one task.",
            "POST /api/tasks/next/request-approval": "Create an approval request for the next approval-gated task.",
            "POST /api/tasks/{id}/done": "Mark one task done.",
            "POST /api/tasks/{id}/block": "Block one task.",
            "POST /api/tasks/{id}/cancel": "Cancel one task.",
            "POST /api/tasks/{id}/ready-for-retry": "Mark a failed/blocked task planned and ready for retry.",
            "POST /api/tasks/{id}/retry": "Retry a recoverable task through the task work executor; dry_run defaults true.",
            "GET /api/work-queue": "Legacy alias: list task-backed tasks.",
            "GET /api/work-queue/summary": "Legacy alias: summarize task-backed tasks.",
            "GET /api/work-queue/{id}": "Legacy alias: get one task-backed task.",
            "POST /api/work-queue": "Legacy alias: create a task-backed task.",
            "POST /api/tasks/patch-request": "Create a task-backed patch-generation item.",
            "POST /api/work-queue/patch-request": "Legacy alias: create a patch-generation task.",
            "POST /api/work-queue/next/dry-run": "Legacy alias: dry-run the next safe task.",
            "POST /api/work-queue/next/execute": "Legacy alias: execute the next safe task.",
            "POST /api/work-queue/{id}/dry-run": "Legacy alias: dry-run one task.",
            "POST /api/work-queue/{id}/execute": "Legacy alias: execute one task.",
            "POST /api/work-queue/{id}/done": "Legacy alias: mark one task done.",
            "POST /api/work-queue/{id}/block": "Legacy alias: block one task.",
            "POST /api/work-queue/{id}/cancel": "Legacy alias: cancel one task.",
            "POST /api/tasks/{id}/suggest-patch": "Generate and link a patch proposal from one task.",
            "POST /api/work-queue/{id}/suggest-patch": "Legacy alias: generate and link a patch proposal from one task.",
            "GET /api/work-cycles": "List saved supervised work cycle records.",
            "GET /api/work-cycles/{id}": "Get one supervised work cycle record.",
            "POST /api/work-cycles/run": "Run a supervised work cycle over task-backed tasks.",
            "GET /api/stable-loops": "List saved v6.9 stable supervised loop records. Supports ?review=..., ?decision=..., and ?include_archived=true.",
            "GET /api/stable-loops/preflight": "Preview stable loop health, closure guardrails, and next lifecycle decision.",
            "GET /api/stable-loops/guardrails": "Show closure-aware live-run guardrails for unresolved stable-loop follow-up chains.",
            "GET /api/stable-loops/{id}": "Get one saved stable loop record.",
            "GET /api/stable-loops/reviews": "Summarize saved stable loop review states. Supports ?review=... and ?include_archived=true.",
            "GET /api/stable-loops/history": "List stable loop review/history rows with filters.",
            "GET /api/stable-loops/{id}/review": "Get one stable loop record with review metadata.",
            "GET /api/stable-loops/{id}/audit": "Get audit, rollback, and verification notes for one stable loop. Supports ?refresh=true.",
            "POST /api/stable-loops/run": "Run a stable supervised loop preview, or a live loop only when live=true and closure guardrails are clear or explicitly bypassed.",
            "POST /api/stable-loops/{id}/review": "Set one stable loop review status.",
            "POST /api/stable-loops/{id}/approve-live": "Mark a preview stable loop approved for explicit live run.",
            "POST /api/stable-loops/{id}/reject": "Reject one stable loop review record.",
            "POST /api/stable-loops/{id}/archive": "Archive one stable loop history record without deleting it.",
            "POST /api/stable-loops/{id}/restore": "Restore one archived stable loop history record.",
            "POST /api/stable-loops/{id}/refresh-audit": "Refresh and save audit notes for one stable loop.",
            "GET /api/stable-loops/{id}/operator-notes": "Get post-run checklist, operator notes, and final decision for one stable loop.",
            "POST /api/stable-loops/{id}/operator-notes": "Append an operator note to a stable-loop record.",
            "POST /api/stable-loops/{id}/decision": "Set final keep/fix/rollback decision for a stable-loop record.",
            "POST /api/stable-loops/{id}/checklist/{check_id}": "Mark one stable-loop post-run checklist item done, skipped, or pending.",
            "POST /api/stable-loops/history/cleanup": "Archive stable loop history records matching a review filter; dry_run defaults true.",
            "GET /api/stable-loops/decisions": "Summarize/filter stable-loop final decisions. Supports ?decision=... and ?include_archived=true.",
            "GET /api/stable-loops/decisions/report": "Return a decision-aware stable-loop report with matching rows.",
            "POST /api/stable-loops/decisions/cleanup": "Archive stable-loop records matching a final-decision filter; dry_run defaults true.",
            "GET /api/stable-loops/followups": "Summarize stable-loop final-decision follow-up task needs. Supports ?decision=...",
            "GET /api/stable-loops/{id}/followups": "Preview follow-up tasks for one stable-loop final decision.",
            "GET /api/stable-loops/followups/completion": "Report stable-loop follow-up completion/closure state. Supports ?completion=...",
            "GET /api/stable-loops/followups/completion/report": "Detailed stable-loop follow-up completion report with matching rows.",
            "POST /api/stable-loops/followups/completion/cleanup": "Archive resolved follow-up completion records; dry_run defaults true.",
            "POST /api/stable-loops/{id}/mark-followups-closed": "Mark a resolved stable-loop follow-up chain closed after operator review.",
            "POST /api/stable-loops/{id}/create-followups": "Create task-backed follow-ups for one stable-loop final decision; dry_run defaults true.",
            "POST /api/stable-loops/decisions/create-followups": "Create task-backed follow-ups for matching stable-loop final decisions; dry_run defaults true.",
            "POST /api/stable-loops/{id}/run-approved-live": "Run a live stable loop from an approved preview record.",
            "GET /api/goals": "List goals.",
            "GET /api/goals/{id}": "Get a goal detail record.",
            "POST /api/goals": "Create a goal.",
            "GET /api/session-plans": "List saved session plans.",
            "GET /api/session-plans/{id}": "Get a saved session plan.",
            "POST /api/session-plans/run": "Create a session plan.",
            "GET /api/maintenance": "List saved maintenance scans.",
            "GET /api/maintenance/{id}": "Get a saved maintenance scan.",
            "POST /api/maintenance/run": "Create a read-only maintenance scan.",
            "GET /api/dev-loops": "List saved dev loops.",
            "GET /api/dev-loops/{id}": "Get a saved dev loop.",
            "POST /api/dev-loops/run": "Run a bounded dev loop, normally dry-run from desktop quick actions.",
            "GET /api/desktop/attention": "Compact attention payload for desktop quick actions.",
            "GET /api/setup": "List saved setup helper reports.",
            "GET /api/setup/latest": "Latest setup helper report.",
            "POST /api/setup/run": "Run and save a first-run setup check.",
            "GET /api/onboarding": "List saved guided onboarding wizard runs.",
            "GET /api/onboarding/latest": "Latest guided onboarding wizard run.",
            "POST /api/onboarding/run": "Run and save a guided onboarding wizard run.",
            "GET /api/patches": "List patch proposals.",
            "GET /api/patches/{id}": "Get a patch proposal.",
            "POST /api/patches/suggest": "Create a patch proposal through patch suggestion mode.",
            "POST /api/patches/{id}/create-task-followups": "Create review/apply/test task follow-ups for a patch.",
            "POST /api/patches/{id}/create-followups": "Legacy alias: create review/apply/test work queue follow-ups for a patch.",
            "POST /api/dashboard-chat": "Create a dashboard chat turn with action card.",
            "GET /api/dashboard-chat/latest": "Latest dashboard chat turn.",
        },
    }


def build_status_payload() -> dict[str, Any]:
    tasks = list_tasks(include_cancelled=False)
    approvals = list_approvals(include_closed=True)
    pending_approvals = [item for item in approvals if item.get("status") == "pending"]
    notifications = list_notifications(include_dismissed=True)
    unread_notifications = [item for item in notifications if item.get("status") == "unread"]
    patches = list_patch_proposals()
    reports = list_test_reports()
    reviews = list_test_reviews()
    watch_reports = list_watch_reports()
    diagnostics = list_diagnostic_reports()
    setup_reports = list_setup_reports()
    onboarding_runs = list_onboarding_runs()
    work_summary = summarize_queue()
    lifecycle_summary = task_lifecycle_summary()
    recovery_summary = task_recovery_summary()
    work_cycles = list_work_cycles()
    stable_loops = list_stable_loops()
    stable_review_summary = stable_loop_review_summary()
    stable_decision_summary = stable_loop_decision_summary()
    try:
        stable_guardrails = stable_loop_guardrail_summary(project_id="eidolon")
    except Exception as guardrail_error:
        stable_guardrails = {"ok": False, "error": str(guardrail_error), "unresolved_count": 0, "ok_for_live": False}
    next_work = work_summary.get("next_item") or {}
    settings = load_settings()

    return {
        "name": "Eidolon",
        "api_version": API_VERSION,
        "active_project": get_active_project(),
        "counts": {
            "memories": len(load_memories()),
            "tasks": len(tasks),
            "task_status": task_status_counts(),
            "approvals": len(approvals),
            "pending_approvals": len(pending_approvals),
            "notifications": len(notifications),
            "unread_notifications": len(unread_notifications),
            "patches": len(patches),
            "test_reports": len(reports),
            "test_reviews": len(reviews),
            "watch_reports": len(watch_reports),
            "diagnostic_reports": len(diagnostics),
            "session_plans": len(list_session_plans()),
            "maintenance_scans": len(list_maintenance_scans()),
            "chat_actions": len(list_chat_actions(include_closed=True)),
            "dashboard_chat_turns": len(list_dashboard_chat_turns()),
            "goals": len(list_goals()),
            "setup_reports": len(setup_reports),
            "onboarding_runs": len(onboarding_runs),
            "work_queue_total": work_summary.get("total", 0),
            "work_queue_pending": work_summary.get("pending", 0),
            "work_queue_active": work_summary.get("active", 0),
            "work_queue_blocked": work_summary.get("blocked", 0),
            "work_queue_done": work_summary.get("done", 0),
            "work_queue_failed": work_summary.get("failed", 0),
            "work_queue_approval_required": work_summary.get("approval_required", 0),
            "task_lifecycle_needs_attention": lifecycle_summary.get("needs_attention", 0),
            "task_lifecycle_open": lifecycle_summary.get("open", 0),
            "task_recovery_needed": recovery_summary.get("recoverable", 0),
            "work_cycles": len(work_cycles),
            "stable_loops": len(stable_loops),
            "stable_loop_unreviewed": stable_review_summary.get("unreviewed_preview_count", 0),
            "stable_loop_approved_ready": stable_review_summary.get("approved_ready_count", 0),
            "stable_loop_decision_action_required": stable_decision_summary.get("action_required_count", 0),
            "stable_loop_decision_cleanup_candidates": stable_decision_summary.get("cleanup_candidate_count", 0),
            "stable_loop_guardrail_unresolved": stable_guardrails.get("unresolved_count", 0),
            "stable_loop_guardrail_live_ready": bool(stable_guardrails.get("ok_for_live")),
        },
        "task_lifecycle": lifecycle_summary,
        "task_recovery": recovery_summary,
        "stable_loop_review": stable_review_summary,
        "stable_loop_decisions": stable_decision_summary,
        "stable_loop_guardrails": stable_guardrails,
        "latest": {
            "diagnostic_report_id": diagnostics[0].get("id") if diagnostics else "",
            "watch_report_id": watch_reports[0].get("id") if watch_reports else "",
            "pending_approval_id": pending_approvals[0].get("id") if pending_approvals else "",
            "unread_notification_id": unread_notifications[0].get("id") if unread_notifications else "",
            "maintenance_scan_id": list_maintenance_scans()[0].get("id") if list_maintenance_scans() else "",
            "dev_loop_id": list_dev_loops()[0].get("id") if list_dev_loops() else "",
            "setup_report_id": setup_reports[0].get("id") if setup_reports else "",
            "setup_status": setup_reports[0].get("status") if setup_reports else "",
            "onboarding_run_id": onboarding_runs[0].get("id") if onboarding_runs else "",
            "onboarding_status": onboarding_runs[0].get("status") if onboarding_runs else "",
            "work_item_id": next_work.get("id", ""),
            "work_item_title": next_work.get("title", ""),
            "work_cycle_id": work_cycles[0].get("id") if work_cycles else "",
            "stable_loop_id": stable_loops[0].get("id") if stable_loops else "",
        },
        "settings": {
            "dashboard_host": settings.get("dashboard_host"),
            "dashboard_port": settings.get("dashboard_port"),
            "api_host": settings.get("api_host"),
            "api_port": settings.get("api_port"),
            "safe_mode": settings.get("safe_mode"),
            "dashboard_live_refresh_enabled": settings.get("dashboard_live_refresh_enabled"),
            "dashboard_live_refresh_seconds": settings.get("dashboard_live_refresh_seconds"),
        },
        "live_refresh": {
            "enabled": bool(settings.get("dashboard_live_refresh_enabled", True)),
            "interval_seconds": int(settings.get("dashboard_live_refresh_seconds", 5) or 5),
        },
    }


def build_desktop_attention_payload() -> dict[str, Any]:
    """Compact desktop-focused status payload for quick actions.

    This is read-only. It exists so the desktop shell can display the most
    important pending items without scraping several endpoints like a raccoon
    in a JSON dumpster.
    """
    status = build_status_payload()
    unread = list_notifications(status="unread", include_dismissed=False)
    pending = list_approvals(status="pending", include_closed=False)

    quick_actions = [
        {
            "id": "run_diagnostics",
            "label": "Run diagnostics",
            "method": "POST",
            "endpoint": "/api/diagnostics/run",
            "risk": "read_only",
        },
        {
            "id": "watch_once",
            "label": "Run watch once",
            "method": "POST",
            "endpoint": "/api/watch/run-once",
            "risk": "read_only",
        },
        {
            "id": "maintenance_scan",
            "label": "Run maintenance scan",
            "method": "POST",
            "endpoint": "/api/maintenance/run",
            "risk": "read_only",
        },
        {
            "id": "plan_session",
            "label": "Plan session",
            "method": "POST",
            "endpoint": "/api/session-plans/run",
            "risk": "read_only",
        },
        {
            "id": "mark_latest_unread_read",
            "label": "Mark latest unread notification read",
            "method": "POST",
            "endpoint": "/api/notifications/latest-unread/read",
            "risk": "metadata_only",
        },
        {
            "id": "dismiss_latest_unread",
            "label": "Dismiss latest unread notification",
            "method": "POST",
            "endpoint": "/api/notifications/latest-unread/dismiss",
            "risk": "metadata_only",
        },
        {
            "id": "dry_run_latest_approval",
            "label": "Dry-run latest pending approval",
            "method": "POST",
            "endpoint": "/api/approvals/latest-pending/approve",
            "risk": "dry_run",
        },
    ]

    return {
        "status": status,
        "top_unread_notifications": unread[:5],
        "top_pending_approvals": pending[:5],
        "quick_actions": quick_actions,
        "safety": "Desktop quick actions are local API calls. File edits and approval-gated actions still use existing safety gates.",
    }


def handle_api_get(path: str, query: dict[str, list[str]] | None = None) -> tuple[int, dict[str, Any]]:
    query = query or {}
    parts = _path_parts(path)

    if not parts:
        return 200, _ok(_api_index())

    if parts == ["status"]:
        return 200, _ok(build_status_payload())

    if parts == ["stabilization-checkpoint"]:
        project_id = query.get("project", ["eidolon"])[0]
        full = _query_bool(query, "full", False)
        return 200, _ok(build_stabilization_checkpoint(project_id=project_id, full=full))

    if parts == ["doctor"]:
        project_id = query.get("project", ["eidolon"])[0]
        full = _query_bool(query, "full", False)
        return 200, _ok(build_doctor_report(project_id=project_id, full=full))

    if parts == ["repair-suggestions"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_repair_suggestions(project_id=project_id))

    if parts == ["patch-integrity"]:
        return 200, _ok(build_patch_integrity_report())

    if parts == ["project-snapshot"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_snapshot(project_id=project_id))

    if parts == ["recovery-drill"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_recovery_drill(project_id=project_id))

    if parts == ["hardening-report"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_hardening_report(project_id=project_id))

    if parts == ["controlled-self-build"]:
        project_id = query.get("project", ["eidolon"])[0]
        max_steps = int(query.get("steps", ["1"])[0] or 1)
        report = build_controlled_self_build(project_id=project_id, max_steps=max_steps, live=False, approve_live=False, use_ai=False)
        if _query_bool(query, "live", False) or _query_bool(query, "approve", False):
            report.setdefault("warnings", []).append("GET is preview-only. Use POST /api/controlled-self-build with explicit JSON confirmation for live work.")
        return 200, _ok(report)

    if len(parts) >= 2 and parts[0] == "controlled-build":
        project_id = query.get("project", ["eidolon"])[0]
        action = parts[1]
        if action == "select-task":
            return 200, _ok(build_controlled_task_selection(project_id=project_id))
        if action == "plan-patch":
            return 200, _ok(build_patch_plan(project_id=project_id, target_version=query.get("version", ["10.0"])[0], save=False))
        if action == "workspace":
            return 200, _ok(patch_workspace_status())
        if action == "stage-patch":
            return 200, _ok(stage_controlled_patch(project_id=project_id, save=False))
        if action == "preview-diff":
            return 200, _ok(preview_staged_diff(project_id=project_id, stage_if_missing=False, save=False))
        if action == "readme-gate":
            return 200, _ok(readme_gate(project_id=project_id))

    if parts == ["supervised-dev-loop"]:
        raise ApiError(405, "GET /api/supervised-dev-loop is disabled. Use POST with explicit JSON confirmation for live behavior or dry_run=true for preview.")


    if parts == ["codebase-map"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_codebase_map(project_id=project_id))

    if parts == ["task-dependencies"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_dependencies(project_id=project_id))

    if parts == ["test-plan"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_plan(project_id=project_id))

    if parts == ["patch-risk"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_risk(project_id=project_id))

    if parts == ["patch-review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review(project_id=project_id))

    if parts == ["project-memory-index"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_memory_index(project_id=project_id))

    if parts == ["workspace-status"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_status(project_id=project_id))

    if parts == ["cross-project-task-review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_cross_project_task_review(project_id=project_id))

    if parts == ["asymmetric-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_asymmetric_dev_loop(project_id=project_id))

    if parts == ["project-registry"]:
        return 200, _ok(build_project_registry(repair=False))

    if parts == ["project-health"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_health(project_id=project_id, all_projects=_query_bool(query, "all", False)))

    if parts == ["command-profiles"]:
        return 200, _ok(build_command_profiles(save=False))

    if parts == ["workspace-dependency-map"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_dependency_map(project_id=project_id))

    if parts == ["workspace-task-inbox"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_task_inbox(project_id=project_id))

    if parts == ["project-context"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_context(project_id=project_id))

    if parts == ["workspace-timeline"]:
        return 200, _ok(build_workspace_timeline())

    if parts == ["workspace-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_dev_loop(project_id=project_id, live=False, save_timeline=False))

    if parts == ["workspace-registry-audit"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_registry_audit(project_id=project_id, archive_stale=False))

    if parts == ["workspace-repair-suggestions"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_repair_suggestions(project_id=project_id))

    if parts == ["project-registration-wizard"]:
        name = query.get("name", ["Workspace Project"])[0]
        root = query.get("root", [None])[0]
        project_id = query.get("project_id", [None])[0]
        return 200, _ok(build_project_registration_wizard(name=name, root=root, project_id=project_id))

    if parts == ["project-boundary-check"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_project_boundary_check(project_id=project_id))

    if parts == ["workspace-patch-plan"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_patch_plan(project_id=project_id, target_version=query.get("version", ["12.0"])[0], save=False))

    if parts == ["workspace-preview-diff"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_preview_diff(project_id=project_id, save=False))

    if parts == ["workspace-verify-latest"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_workspace_verify_latest(project_id=project_id, save=False))

    if parts == ["guarded-workspace-dev-loop"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_guarded_workspace_dev_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["patch-draft-status"], ["patch-drafts", "status"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_draft_status(project_id=project_id))

    if parts in (["patch-draft-request"], ["patch-drafts", "request"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_draft_request(project_id=project_id, target_version=query.get("version", ["20.0.1"])[0], task=query.get("task", [None])[0], intent=query.get("intent", [None])[0], risk_limit=query.get("risk_limit", ["medium"])[0], save=False))

    if parts in (["draft-patch"], ["patch-drafts", "draft"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_patch(project_id=project_id, save=False))

    if parts in (["patch-review-notes"], ["patch-drafts", "notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review_notes(project_id=project_id, save=False))

    if parts in (["draft-diff"], ["patch-drafts", "diff"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_diff(project_id=project_id, save=False))

    if parts in (["draft-test-impact"], ["patch-drafts", "test-impact"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_test_impact(project_id=project_id, save=False))

    if parts in (["approval-gate"], ["patch-drafts", "approval-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_gate(project_id=project_id))

    if parts in (["human-approved-patch-loop"], ["patch-drafts", "human-approved-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_human_approved_patch_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    # v13.1-v14.0 draft review endpoints are read-only GET previews.
    if parts in (["patch-drafts", "quality"], ["draft-quality"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_quality(project_id=project_id, save=False))

    if parts in (["patch-drafts", "file-targets"], ["draft-file-targets"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_file_targets(project_id=project_id, save=False))

    if parts in (["patch-drafts", "intent-blocks"], ["draft-intent-blocks"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_intent_blocks(project_id=project_id, save=False))

    if parts in (["patch-drafts", "conflicts"], ["draft-conflicts"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_conflicts(project_id=project_id, save=False))

    if parts in (["patch-drafts", "verification-bundle"], ["draft-verification-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_verification_bundle(project_id=project_id, save=False))

    if parts in (["patch-drafts", "review-checklist"], ["draft-review-checklist"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_review_checklist(project_id=project_id, save=False))

    if parts in (["patch-drafts", "execution-report"], ["approved-draft-execution-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approved_draft_execution_report(project_id=project_id, save=False))

    if parts in (["patch-drafts", "review-loop"], ["review-centered-patch-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_review_centered_patch_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    if parts == ["patch-drafts", "review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_draft_verification_bundle(project_id=project_id, save=False))

    # v14.1-v15.0 release pipeline endpoints are read-only GET previews.
    if parts in (["code-edit-proposal"], ["patch-drafts", "code-edit-proposal"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_edit_proposal(project_id=project_id, save=False))

    if parts in (["safe-rewrite-preview"], ["patch-drafts", "safe-rewrite-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_safe_rewrite_preview(project_id=project_id, save=False))

    if parts in (["generate-code-patch"], ["patch-drafts", "generated-code-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_code_patch(project_id=project_id, save=False))

    if parts in (["test-suggestions"], ["patch-drafts", "test-suggestions"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_suggestions(project_id=project_id, save=False))

    if parts in (["inline-review-notes"], ["patch-drafts", "inline-review-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_inline_review_note(project_id=project_id, save=False))

    if parts in (["approved-code-apply-report"], ["patch-drafts", "approved-code-apply-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_approved_code_patch(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["prepare-release-package"], ["release", "package"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_prepare_release_package(project_id=project_id, package_name=query.get("package", [None])[0], save=False))

    if parts in (["release-readiness"], ["release", "readiness"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_readiness(project_id=project_id, save=False))

    if parts in (["human-approved-release-loop"], ["release", "human-approved-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_human_approved_release_loop(project_id=project_id, approve_apply=False, dry_run=True, save=False))

    # v15.1-v16.0 generated code release endpoints are read-only GET previews.
    if parts in (["code-patch-status"], ["code-patches", "status"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_patch_status(project_id=project_id, save=False))

    if parts in (["symbol-scan"], ["code-patches", "symbol-scan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_symbol_scan(project_id=project_id, save=False))

    if parts in (["rewrite-plan"], ["code-patches", "rewrite-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_rewrite_plan(project_id=project_id, save=False))

    if parts in (["rewrite-conflicts"], ["code-patches", "rewrite-conflicts"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_rewrite_conflicts(project_id=project_id, save=False))

    if parts in (["code-patch-diff-bundle"], ["code-patches", "diff-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_patch_diff_bundle(project_id=project_id, save=False))

    if parts in (["apply-code-patch-transaction"], ["code-patches", "apply-transaction"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_code_patch_transaction(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["semantic-checks"], ["code-patches", "semantic-checks"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_semantic_checks(project_id=project_id, save=False))

    if parts in (["release-artifact"], ["release", "artifact"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_artifact(project_id=project_id, package_name=query.get("package", [None])[0], save=False))

    if parts in (["release-audit-trail"], ["release", "audit-trail"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_audit_trail(project_id=project_id, save=False))

    if parts in (["generated-code-release-loop"], ["release", "generated-code-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_code_release_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v16.1-v17.0 AI-assisted code patch endpoints are read-only GET previews.
    if parts in (["task-to-code-patch"], ["code-patches", "task-to-code-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_to_code_patch(project_id=project_id, save=False))

    if parts in (["code-context"], ["code-patches", "code-context"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_context(project_id=project_id, save=False))

    if parts in (["patch-prompt"], ["code-patches", "patch-prompt"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_prompt(project_id=project_id, save=False))

    if parts in (["parse-generated-edits"], ["code-patches", "parse-generated-edits"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_parse_generated_edits(project_id=project_id, save=False))

    if parts in (["edit-consistency"], ["code-patches", "edit-consistency"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_edit_consistency(project_id=project_id, save=False))

    if parts in (["ai-code-patch-dry-run"], ["code-patches", "ai-dry-run"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_code_patch_dry_run(project_id=project_id, save=False))

    if parts in (["patch-failure-analysis"], ["code-patches", "failure-analysis"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_failure_analysis(project_id=project_id, save=False))

    if parts in (["patch-learning-notes"], ["code-patches", "learning-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_learning_notes(project_id=project_id, save=False))

    if parts in (["ai-assisted-code-patch-loop"], ["code-patches", "ai-assisted-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_assisted_code_patch_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v17.1-v18.0 validated AI code patch endpoints are read-only GET previews.
    if parts in (["refine-patch-objective"], ["code-patches", "objective-refinement"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_objective_refinement(project_id=project_id, save=False))

    if parts in (["rank-code-context"], ["code-patches", "context-ranking"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_code_context_ranking(project_id=project_id, save=False))

    if parts in (["patch-safety-envelope"], ["code-patches", "safety-envelope"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_safety_envelope(project_id=project_id, save=False))

    if parts in (["validate-generated-patch"], ["code-patches", "validate-generated-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_generated_patch_validation(project_id=project_id, save=False))

    if parts in (["patch-simulation"], ["code-patches", "simulation"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_simulation(project_id=project_id, save=False))

    if parts in (["test-stub-plan"], ["code-patches", "test-stub-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_test_stub_plan(project_id=project_id, save=False))

    if parts in (["patch-review-score"], ["code-patches", "review-score"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_review_score(project_id=project_id, save=False))

    if parts in (["patch-recovery-plan"], ["code-patches", "recovery-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_patch_recovery_plan(project_id=project_id, save=False))

    if parts in (["validated-ai-code-patch-loop"], ["code-patches", "validated-ai-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_validated_ai_code_patch_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    # v18.1-v19.0 approval-to-release endpoints are read-only GET previews.
    if parts in (["ai-patch-review-bundle"], ["code-patches", "review-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_ai_patch_review_bundle(project_id=project_id, save=False))

    if parts in (["ai-patch-review-integrity"], ["code-patches", "review-integrity"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_review_bundle_integrity(project_id=project_id, save=False))

    if parts in (["approval-ready"], ["code-patches", "approval-ready"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_ready(project_id=project_id, save=False))

    if parts in (["approval-ledger"], ["code-patches", "approval-ledger"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_ledger(project_id=project_id, save=False))

    if parts in (["apply-validated-ai-patch"], ["code-patches", "apply-validated-ai-patch"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_apply_validated_ai_patch(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["post-apply-review"], ["code-patches", "post-apply-review"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_post_apply_review(project_id=project_id, save=False))

    if parts in (["package-build-plan"], ["release", "package-build-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_package_build_plan(project_id=project_id, package_name=package_name, save=False))

    if parts in (["approval-to-release-loop"], ["release", "approval-to-release-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_approval_to_release_loop(project_id=project_id, approve=False, dry_run=True, save=False))

    if parts in (["release-manifest-integrity"], ["release", "manifest-integrity"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_manifest_integrity(project_id=project_id, package_name=package_name, save=False))

    if parts in (["package-inventory"], ["release", "package-inventory"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_inventory(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["package-checksums"], ["release", "package-checksums"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_checksums(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["release-notes"], ["release", "notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_release_notes(project_id=project_id, save=False))

    if parts in (["release-handoff-report"], ["release", "handoff"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_handoff_report(project_id=project_id, package_name=package_name, save=False))

    if parts in (["build-release-zip"], ["release", "build-zip"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_release_zip(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False))

    if parts in (["verify-release-unzip"], ["release", "verify-unzip"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        return 200, _ok(build_verify_release_unzip(project_id=project_id, package_name=package_name, save=False))

    if parts in (["release-pipeline-audit"], ["release", "pipeline-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_pipeline_audit(project_id=project_id, package_name=package_name, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["verified-release-package-loop"], ["release", "verified-package-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_release_package_loop(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_release_report(report))

    if parts in (["release-profiles"], ["release", "profiles"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_profiles(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["package-privacy-scan"], ["release", "privacy-scan"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_package_privacy_scan(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["portable-metadata-check"], ["release", "portable-metadata"]):
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_portable_metadata_check(project_id=project_id, save=False))

    if parts in (["first-run-check"], ["release", "first-run-check"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_first_run_check(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["dependency-advisor"], ["release", "dependency-advisor"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dependency_advisor(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["upgrade-notes"], ["release", "upgrade-notes"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_upgrade_notes(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["runtime-migration-check"], ["release", "runtime-migration"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_runtime_migration_check(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-install-verification"], ["release", "install-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_install_verification(project_id=project_id, package_name=package_name, run_smoke=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["verified-installable-release-loop"], ["release", "verified-installable-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_installable_release_loop(project_id=project_id, package_name=package_name, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["smoke-runtime-hardening"], ["release", "smoke-runtime-hardening"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_smoke_runtime_hardening(project_id=project_id, tier=query.get("tier", ["full"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["external-zip-install-verification"], ["release", "external-zip-install-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_external_zip_install_verification(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], run_compile=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["deterministic-release-manifest"], ["release", "deterministic-release-manifest"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_deterministic_release_manifest(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["update-dry-run-plan"], ["release", "update-dry-run-plan"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_update_dry_run_plan(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["atomic-source-update"], ["release", "atomic-source-update"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_atomic_source_update(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], expected_manifest_hash=query.get("expected_manifest_hash", [None])[0], confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["runtime-migration-assistant"], ["release", "runtime-migration-assistant"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_runtime_migration_assistant(project_id=project_id, confirm=False, dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["route-safety-harness"], ["release", "route-safety-harness"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_route_safety_harness(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-dashboard-command-center"], ["release", "dashboard-command-center"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_dashboard_command_center(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["clean-room-install-harness"], ["release", "clean-room-install-harness"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_clean_room_install_harness(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], run_smoke_tier=query.get("tier", ["fast"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["verified-self-update-release-pipeline"], ["release", "verified-self-update-release-pipeline"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_verified_self_update_release_pipeline(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], confirm=False, dry_run=True, run_clean_room=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["trial-upgrade-from-zip"], ["release", "trial-upgrade-from-zip"], ["release", "trial-upgrade"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_trial_upgrade_harness(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], run_smoke_tier=query.get("tier", ["fast"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["backup-rollback-drill"], ["release", "backup-rollback-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_backup_rollback_drill(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["update-collision-detector"], ["release", "update-collision-detector"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_update_collision_detector(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["version-registry-report"], ["release", "version-registry-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_version_registry_report(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["release-provenance-report"], ["release", "provenance-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_release_provenance_report(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["dashboard-upgrade-wizard-preview"], ["release", "dashboard-upgrade-wizard-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_dashboard_upgrade_wizard_preview(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["api-upgrade-wizard-preview"], ["release", "api-upgrade-wizard-preview"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_api_upgrade_wizard_preview(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["staged-apply-drill"], ["release", "staged-apply-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_staged_apply_drill(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["real-apply-guard-rails"], ["release", "real-apply-guard-rails"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_real_apply_guard_rails(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], expected_manifest_hash=query.get("expected_manifest_hash", [None])[0], confirm_phrase=query.get("confirm_phrase", [""])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["real-apply-rollback-verification"], ["release", "real-apply-rollback-verification"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_real_apply_rollback_verification(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["self-update-ux-polish"], ["release", "self-update-ux-polish"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_self_update_ux_polish(project_id=project_id, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["v23-readiness-gate"], ["release", "v23-readiness-gate"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_v23_readiness_gate(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], run_heavy=query.get("run_heavy", ["false"])[0].lower() == "true", save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))

    if parts in (["controlled-self-maintenance-loop"], ["release", "controlled-self-maintenance-loop"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        report = build_controlled_self_maintenance_loop(project_id=project_id, package_name=package_name, zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_installation_report(report))



    if parts in (["self-maintenance", "proposal"], ["release", "self-maintenance-proposal"], ["self-maintenance-proposal"]):
        report = build_self_maintenance_proposal_sandbox(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "patch-plan"], ["release", "build-patch-plan"], ["build-patch-plan"]):
        report = build_patch_plan_builder(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "patch-preview"], ["release", "generate-maintenance-patch"], ["generate-maintenance-patch"]):
        report = build_dry_run_patch_generator(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "safety-audit"], ["release", "patch-safety-audit"], ["patch-safety-audit"]):
        report = build_patch_safety_auditor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "temp-apply-drill"], ["release", "apply-maintenance-patch-to-temp"], ["apply-maintenance-patch-to-temp"]):
        report = build_apply_patch_to_temp_clone(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "review-bundle"], ["release", "maintenance-review-bundle"], ["maintenance-review-bundle"]):
        report = build_maintenance_review_bundle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-binding"], ["release", "approve-maintenance-bundle"], ["approve-maintenance-bundle"]):
        report = build_human_approval_binding(project_id=query.get("project", ["eidolon"])[0], bundle_hash=query.get("bundle_hash", [None])[0], confirm=False, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "apply-gate"], ["release", "real-maintenance-patch-apply"], ["real-maintenance-patch-apply"]):
        report = build_real_maintenance_patch_apply(project_id=query.get("project", ["eidolon"])[0], bundle_hash=query.get("bundle_hash", [None])[0], dry_run=True, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "post-apply-health"], ["release", "post-apply-health-monitor"], ["post-apply-health-monitor"]):
        report = build_post_apply_health_monitor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "controlled-cycle"], ["release", "controlled-maintenance-cycle"], ["controlled-maintenance-cycle"]):
        report = build_controlled_maintenance_cycle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "assisted-release"], ["release", "assisted-self-improvement-release"], ["assisted-self-improvement-release"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        zip_path = query.get("zip_path", [None])[0]
        report = build_assisted_self_improvement_release(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "improvement-candidates"], ["release", "improvement-candidate-scan"], ["improvement-candidate-scan"]):
        report = build_improvement_candidate_scan(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "candidate-prioritizer"], ["release", "candidate-prioritizer"], ["candidate-prioritizer"]):
        report = build_candidate_prioritizer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "candidate-to-proposal"], ["release", "candidate-to-proposal"], ["candidate-to-proposal"]):
        report = build_candidate_to_proposal_bridge(project_id=query.get("project", ["eidolon"])[0], candidate_id=query.get("candidate_id", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "maintenance-backlog"], ["release", "maintenance-backlog"], ["maintenance-backlog"]):
        report = build_maintenance_backlog_registry(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-backlog"], ["release", "dashboard-maintenance-backlog"], ["dashboard-maintenance-backlog"]):
        report = build_dashboard_maintenance_backlog(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-backlog"], ["release", "api-maintenance-backlog"], ["api-maintenance-backlog"]):
        report = build_api_maintenance_backlog(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "regression-detector"], ["release", "candidate-regression-detector"], ["candidate-regression-detector"]):
        report = build_candidate_regression_detector(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-memory-privacy"], ["release", "release-memory-privacy"], ["release-memory-privacy"]):
        report = build_release_memory_privacy(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verification-recipes"], ["release", "candidate-verification-recipes"], ["candidate-verification-recipes"]):
        report = build_candidate_verification_recipes(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "assisted-improvement-cycle"], ["release", "assisted-improvement-cycle"], ["assisted-improvement-cycle"]):
        report = build_assisted_improvement_cycle(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "semi-autonomous-review"], ["release", "semi-autonomous-maintenance-review"], ["semi-autonomous-maintenance-review"]):
        project_id = query.get("project", ["eidolon"])[0]
        package_name = query.get("package_name", [_package_name()])[0]
        zip_path = query.get("zip_path", [None])[0]
        report = build_semi_autonomous_maintenance_review(project_id=project_id, package_name=package_name, zip_path=zip_path, save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "hotfix-regression-lockdown"], ["release", "hotfix-regression-lockdown"], ["hotfix-regression-lockdown"]):
        report = build_hotfix_regression_lockdown(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-route-coverage"], ["release", "dashboard-route-coverage"], ["dashboard-route-coverage"]):
        report = build_dashboard_route_coverage_auditor(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-default-source-audit"], ["release", "api-default-source-audit"], ["api-default-source-audit"]):
        report = build_api_default_source_audit(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "nested-readiness-severity"], ["release", "nested-readiness-severity"], ["nested-readiness-severity"]):
        report = build_nested_readiness_severity_engine(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "review-bundle-approval-contract"], ["release", "review-bundle-approval-contract"], ["review-bundle-approval-contract"]):
        report = build_review_bundle_approval_contract(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "maintenance-report-diff"], ["release", "maintenance-report-diff"], ["maintenance-report-diff"]):
        report = build_maintenance_report_diff_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-gate-composition-test"], ["release", "release-gate-composition-test"], ["release-gate-composition-test"]):
        report = build_release_gate_composition_test(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-api-parity-audit"], ["release", "dashboard-api-parity-audit"], ["dashboard-api-parity-audit"]):
        report = build_dashboard_api_parity_audit(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "operator-trust-report"], ["release", "operator-trust-report"], ["operator-trust-report"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_operator_trust_report(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trustworthy-maintenance-console"], ["release", "trustworthy-maintenance-console"], ["trustworthy-maintenance-console"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trustworthy_maintenance_console(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-drill"], ["release", "trust-console-drill"], ["trust-console-drill"]):
        report = build_trust_console_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-snapshot"], ["release", "trust-console-snapshot"], ["trust-console-snapshot"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_trust_console_snapshot(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "trust-console-diff"], ["release", "trust-console-diff"], ["trust-console-diff"]):
        report = build_trust_console_diff(project_id=query.get("project", ["eidolon"])[0], before_path=query.get("before", [None])[0], after_path=query.get("after", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "freeze-release-candidate"], ["release", "freeze-release-candidate"], ["freeze-release-candidate"]):
        report = build_release_candidate_freezer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-frozen-release-zip"], ["release", "verify-frozen-release-zip"], ["verify-frozen-release-zip"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_frozen_release_zip_verification(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "approval-evidence-ledger"], ["release", "approval-evidence-ledger"], ["approval-evidence-ledger"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_approval_evidence_ledger(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-command-reproducer"], ["release", "release-command-reproducer"], ["release-command-reproducer"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_command_reproducer(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "console-readme-consistency"], ["release", "console-readme-consistency"], ["console-readme-consistency"]):
        report = build_console_readme_consistency(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v27-safety-audit"], ["release", "pre-v27-safety-audit"], ["pre-v27-safety-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v27_safety_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-candidate-governance"], ["release", "release-candidate-governance"], ["release-candidate-governance"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_candidate_governance(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))


    if parts in (["self-maintenance", "release-governance-drill"], ["release", "release-governance-drill"], ["release-governance-drill"]):
        report = build_release_governance_drill(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-evidence-bundle"], ["release", "release-evidence-bundle"], ["release-evidence-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_evidence_bundle(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-release-evidence-bundle"], ["release", "verify-release-evidence-bundle"], ["verify-release-evidence-bundle"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_evidence_bundle_verifier(project_id=project_id, bundle_path=query.get("bundle_path", [None])[0], package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-governance-page"], ["release", "release-governance-page"], ["release-governance-page"]):
        report = build_release_governance_page(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "governance-api-read-only"], ["release", "governance-api-read-only"], ["governance-api-read-only"]):
        report = build_governance_api_read_only_surface(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-artifact-diff"], ["release", "release-artifact-diff"], ["release-artifact-diff"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_artifact_diff(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-signing-preparation"], ["release", "release-signing-preparation"], ["release-signing-preparation"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_signing_preparation(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "local-trust-policy"], ["release", "local-trust-policy"], ["local-trust-policy"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_local_trust_policy(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-governance-ux-polish"], ["release", "release-governance-ux-polish"], ["release-governance-ux-polish"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_governance_ux_polish(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v28-governance-audit"], ["release", "pre-v28-governance-audit"], ["pre-v28-governance-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v28_governance_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verifiable-release-evidence-system"], ["release", "verifiable-release-evidence-system"], ["verifiable-release-evidence-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_verifiable_release_evidence_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))



    if parts in (["self-maintenance", "evidence-replay-drill"], ["release", "evidence-replay-drill"], ["evidence-replay-drill"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_replay_drill(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "persist-release-evidence"], ["release", "persist-release-evidence"], ["persist-release-evidence"], ["release", "evidence"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_bundle_persistence(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "replay-release-evidence"], ["release", "replay-release-evidence"], ["replay-release-evidence"], ["release", "evidence", "replay"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_replay_release_evidence(project_id=project_id, bundle_path=query.get("bundle_path", [None])[0], package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-timeline"], ["release", "evidence-timeline"], ["evidence-timeline"]):
        report = build_evidence_timeline(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-summary"], ["release", "evidence-summary"], ["evidence-summary"], ["release", "evidence", "summary"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_evidence_operator_summary(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-evidence-viewer"], ["release", "dashboard-evidence-viewer"], ["dashboard-evidence-viewer"]):
        report = build_dashboard_evidence_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-evidence-viewer"], ["release", "api-evidence-viewer"], ["api-evidence-viewer"]):
        report = build_api_evidence_viewer(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-retention-policy"], ["release", "evidence-retention-policy"], ["evidence-retention-policy"]):
        report = build_evidence_retention_policy(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "evidence-regression-lockdown"], ["release", "evidence-regression-lockdown"], ["evidence-regression-lockdown"]):
        report = build_evidence_regression_lockdown(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v29-evidence-audit"], ["release", "pre-v29-evidence-audit"], ["pre-v29-evidence-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v29_evidence_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "durable-release-evidence-archive"], ["release", "durable-release-evidence-archive"], ["durable-release-evidence-archive"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_durable_release_evidence_archive(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signing-readiness-audit"], ["release", "signing-readiness-audit"], ["signing-readiness-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signing_readiness_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "canonical-manifest-format"], ["release", "canonical-manifest-format"], ["canonical-manifest-format"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_canonical_manifest_format(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "canonical-evidence-schema"], ["release", "canonical-evidence-schema"], ["canonical-evidence-schema"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_canonical_evidence_schema(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "release-signing-status"], ["release", "release-signing-status"], ["release", "signing"], ["release-signing-status"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_release_signing_status(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signature-placeholder-contract"], ["release", "signature-placeholder-contract"], ["signature-placeholder-contract"]):
        report = build_signature_placeholder_contract(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "key-policy-preparation"], ["release", "key-policy-preparation"], ["release", "signing-policy"], ["signing-policy"]):
        report = build_key_policy_preparation(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "verify-release-signature"], ["release", "verify-release-signature"], ["release", "signature", "verify"], ["verify-release-signature"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signature_verification_placeholder(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "dashboard-signing-status"], ["release", "dashboard-signing-status"], ["dashboard-signing-status"]):
        report = build_dashboard_signing_status(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "api-signing-status"], ["release", "api-signing-status"], ["api-signing-status"]):
        report = build_api_signing_status(project_id=query.get("project", ["eidolon"])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "pre-v30-signing-prep-audit"], ["release", "pre-v30-signing-prep-audit"], ["pre-v30-signing-prep-audit"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_pre_v30_signing_prep_audit(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts in (["self-maintenance", "signed-release-preparation-system"], ["release", "signed-release-preparation-system"], ["signed-release-preparation-system"]):
        project_id = query.get("project", ["eidolon"])[0]
        report = build_signed_release_preparation_system(project_id=project_id, package_name=query.get("package_name", [_package_name()])[0], zip_path=query.get("zip_path", [None])[0], save=False)
        return 200, _ok(report if query.get("full", ["false"])[0].lower() == "true" else summarize_self_maintenance_report(report))

    if parts[0] == "diagnostics":
        reports = list_diagnostic_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_diagnostic_report(report_id)
        if not report:
            raise ApiError(404, f"Diagnostic report not found: {report_id}")
        return 200, _ok(report)

    if parts[0] == "watch":
        reports = list_watch_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_watch_report(report_id)
        if not report:
            raise ApiError(404, f"Watch report not found: {report_id}")
        return 200, _ok(report)

    if parts == ["tasks", "review"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_task_review(project_id=project_id))

    if parts == ["stable-loops", "confidence"]:
        project_id = query.get("project", ["eidolon"])[0]
        return 200, _ok(build_stable_loop_confidence(project_id=project_id))

    if parts[0] == "session-plans":
        plans = list_session_plans()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(plans[: max(1, min(limit, 100))])
        plan_id = "latest" if parts[1] == "latest" else parts[1]
        plan = plans[0] if plan_id == "latest" and plans else load_session_plan(plan_id)
        if not plan:
            raise ApiError(404, f"Session plan not found: {plan_id}")
        return 200, _ok(plan)

    if parts[0] == "maintenance":
        scans = list_maintenance_scans()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(scans[: max(1, min(limit, 100))])
        scan_id = "latest" if parts[1] == "latest" else parts[1]
        scan = scans[0] if scan_id == "latest" and scans else load_maintenance_scan(scan_id)
        if not scan:
            raise ApiError(404, f"Maintenance scan not found: {scan_id}")
        return 200, _ok(scan)

    if parts[0] == "dev-loops":
        loops = list_dev_loops()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(loops[: max(1, min(limit, 100))])
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        loop = loops[0] if loop_id == "latest" and loops else get_dev_loop(loop_id)
        if not loop:
            raise ApiError(404, f"Dev loop not found: {loop_id}")
        return 200, _ok(loop)

    if parts[0] == "setup":
        reports = list_setup_reports()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(reports[: max(1, min(limit, 100))])
        report_id = "latest" if parts[1] == "latest" else parts[1]
        report = reports[0] if report_id == "latest" and reports else load_setup_report(report_id)
        if not report:
            raise ApiError(404, f"Setup report not found: {report_id}")
        return 200, _ok(report)

    if parts[0] == "onboarding":
        runs = list_onboarding_runs()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(runs[: max(1, min(limit, 100))])
        run_id = "latest" if parts[1] == "latest" else parts[1]
        run = runs[0] if run_id == "latest" and runs else load_onboarding_run(run_id)
        if not run:
            raise ApiError(404, f"Onboarding run not found: {run_id}")
        return 200, _ok(run)

    if parts == ["desktop", "attention"]:
        return 200, _ok(build_desktop_attention_payload())

    if parts[0] == "notifications":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            severity = query.get("severity", [""])[0]
            include_dismissed = _query_bool(query, "include_dismissed", True)
            return 200, _ok(list_notifications(status=status, severity=severity, include_dismissed=include_dismissed))
        note = load_notification(parts[1])
        if not note:
            raise ApiError(404, f"Notification not found: {parts[1]}")
        return 200, _ok(note)

    if parts[0] == "approvals":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_approvals(status=status, include_closed=include_closed))
        approval = get_approval(parts[1])
        if not approval:
            raise ApiError(404, f"Approval not found: {parts[1]}")
        return 200, _ok(approval)

    if parts[0] == "chat-actions":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_chat_actions(status=status, include_closed=include_closed))
        action = load_chat_action(parts[1])
        if not action:
            raise ApiError(404, f"Chat action not found: {parts[1]}")
        return 200, _ok(action)

    if parts[0] == "stable-loops":
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            decision_filter = query.get("decision", query.get("final_decision", [""]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            if decision_filter:
                include_live = not _query_bool(query, "exclude_live", False)
                return 200, _ok(list_stable_loop_decision_rows(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live, limit=limit))
            return 200, _ok(list_stable_loop_reviews(review_filter=review_filter, include_archived=include_archived, limit=limit))
        if len(parts) == 2 and parts[1] == "preflight":
            project_id = query.get("project", ["eidolon"])[0]
            max_steps = int(query.get("max_steps", query.get("steps", ["1"]))[0] or 1)
            return 200, _ok(build_stable_loop_preflight(project_id=project_id, max_steps=max_steps))
        if len(parts) == 2 and parts[1] == "guardrails":
            project_id = query.get("project", ["eidolon"])[0]
            include_archived = _query_bool(query, "include_archived", False)
            bypass = _query_bool(query, "bypass", False)
            return 200, _ok(stable_loop_guardrail_summary(project_id=project_id, bypass=bypass, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "reviews":
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_review_summary(review_filter=review_filter, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "history":
            limit = int(query.get("limit", ["50"])[0] or 50)
            review_filter = query.get("review", query.get("status", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(list_stable_loop_reviews(review_filter=review_filter, include_archived=include_archived, limit=limit))
        if len(parts) == 2 and parts[1] == "decisions":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            return 200, _ok(stable_loop_decision_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live))
        if len(parts) == 3 and parts[1] == "decisions" and parts[2] == "report":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            limit = int(query.get("limit", ["50"])[0] or 50)
            report = stable_loop_decision_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live)
            report["rows"] = list_stable_loop_decision_rows(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live, limit=limit)
            return 200, _ok(report)
        if len(parts) == 2 and parts[1] == "followups":
            decision_filter = query.get("decision", query.get("filter", ["action_required"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            include_live = not _query_bool(query, "exclude_live", False)
            return 200, _ok(stable_loop_followup_summary(decision_filter=decision_filter, include_archived=include_archived, include_live=include_live))
        if len(parts) == 3 and parts[1] == "followups" and parts[2] == "completion":
            completion_filter = query.get("completion", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_followup_completion_summary(completion_filter=completion_filter, include_archived=include_archived))
        if len(parts) == 4 and parts[1] == "followups" and parts[2] == "completion" and parts[3] == "report":
            completion_filter = query.get("completion", query.get("filter", ["all"]))[0]
            include_archived = _query_bool(query, "include_archived", False)
            limit = int(query.get("limit", ["50"])[0] or 50)
            report = stable_loop_followup_completion_summary(completion_filter=completion_filter, include_archived=include_archived)
            report["rows"] = list_stable_loop_followup_completion_rows(completion_filter=completion_filter, include_archived=include_archived, limit=limit)
            return 200, _ok(report)
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        loop = load_stable_loop(loop_id)
        if not loop:
            raise ApiError(404, f"Stable loop not found: {loop_id}")
        if len(parts) == 3 and parts[2] == "review":
            return 200, _ok(loop)
        if len(parts) == 3 and parts[2] == "audit":
            if _query_bool(query, "refresh", False):
                result = refresh_stable_loop_audit(loop_id)
                if not result.ok:
                    raise ApiError(404, result.error, result.to_dict())
                return 200, _ok(result.audit, message=result.message)
            return 200, _ok(loop.get("audit") if isinstance(loop.get("audit"), dict) else build_stable_loop_audit(loop))
        if len(parts) == 3 and parts[2] == "operator-notes":
            result = get_stable_loop_operator_notes(loop_id, ensure=True, save=_query_bool(query, "save", True))
            if not result.ok:
                raise ApiError(404, result.error, result.to_dict())
            return 200, _ok(result.operator_notes, message=result.message)
        if len(parts) == 3 and parts[2] == "followups":
            result = plan_stable_loop_followups(loop_id=loop_id, force=_query_bool(query, "force", False))
            if not result.ok:
                raise ApiError(404, result.error, result.to_dict())
            return 200, _ok(result.to_dict(), message=result.message)
        if len(parts) == 3 and parts[2] == "followup-lifecycle":
            return 200, _ok(stable_loop_followup_lifecycle_summary(loop_id=loop_id, include_closed=True, include_archived=True))
        return 200, _ok(loop)

    if parts[0] == "work-cycles":
        cycles = list_work_cycles()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(cycles[: max(1, min(limit, 100))])
        cycle_id = "latest" if parts[1] == "latest" else parts[1]
        cycle = cycles[0] if cycle_id == "latest" and cycles else load_work_cycle(cycle_id)
        if not cycle:
            raise ApiError(404, f"Work cycle not found: {cycle_id}")
        return 200, _ok(cycle)

    if parts[0] == "work-queue":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            project_id = query.get("project", [""])[0]
            include_done = _query_bool(query, "include_done", False)
            return 200, _ok(list_work_items(status=status or None, project_id=project_id or None, include_done=include_done))
        if len(parts) == 2 and parts[1] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(summarize_queue(project_id=project_id or None))
        item = find_work_item(parts[1])
        if not item:
            raise ApiError(404, f"Task not found through legacy alias: {parts[1]}")
        return 200, _ok(item)

    if parts[0] == "tasks":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            stage = query.get("stage", [""])[0]
            project_id = query.get("project", [""])[0]
            include_cancelled = _query_bool(query, "include_cancelled", False)
            if stage:
                rows = list_task_lifecycles(project=project_id or "", include_closed=include_cancelled, stage_filter=stage)
                ids = {str(row.get("task_id") or "") for row in rows}
                return 200, _ok([task for task in list_tasks(status=status, project=project_id or "", include_cancelled=include_cancelled) if task.get("id") in ids])
            return 200, _ok(list_tasks(status=status, project=project_id or "", include_cancelled=include_cancelled))
        if len(parts) == 2 and parts[1] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(summarize_queue(project_id=project_id or None))
        if len(parts) == 2 and parts[1] == "lifecycle":
            project_id = query.get("project", [""])[0]
            stage = query.get("stage", [""])[0]
            return 200, _ok(task_lifecycle_summary(project=project_id or "", stage_filter=stage))
        if len(parts) == 2 and parts[1] == "stable-loop-followups":
            decision_filter = query.get("decision", query.get("filter", ["all"]))[0]
            include_closed = _query_bool(query, "include_closed", True)
            include_archived = _query_bool(query, "include_archived", False)
            return 200, _ok(stable_loop_followup_lifecycle_summary(decision_filter=decision_filter, include_closed=include_closed, include_archived=include_archived))
        if len(parts) == 2 and parts[1] == "recovery":
            project_id = query.get("project", [""])[0]
            include_nonrecoverable = _query_bool(query, "include_nonrecoverable", False)
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(list_task_recoveries(project=project_id or "", include_nonrecoverable=include_nonrecoverable, limit=limit))
        if len(parts) == 3 and parts[1] == "recovery" and parts[2] == "summary":
            project_id = query.get("project", [""])[0]
            return 200, _ok(task_recovery_summary(project=project_id or ""))
        if len(parts) == 3 and parts[2] == "approvals":
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_task_approvals(parts[1], include_closed=include_closed))
        if len(parts) == 3 and parts[2] == "lifecycle":
            task = get_task(parts[1])
            if not task:
                raise ApiError(404, f"Task not found: {parts[1]}")
            return 200, _ok(derive_task_lifecycle(task))
        if len(parts) == 3 and parts[2] == "stable-loop-followup":
            row = stable_loop_followup_task_row(parts[1])
            if not row.get("ok"):
                raise ApiError(404, str(row.get("message") or "Task not found."), row)
            return 200, _ok(row)
        if len(parts) == 3 and parts[2] == "recovery":
            recovery = build_task_recovery(parts[1])
            if not recovery.get("ok"):
                raise ApiError(404, str(recovery.get("message") or "Task not found."), recovery)
            return 200, _ok(recovery)
        task = get_task(parts[1])
        if not task:
            raise ApiError(404, f"Task not found: {parts[1]}")
        return 200, _ok(task)

    if parts[0] == "goals":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            include_cancelled = _query_bool(query, "include_cancelled", False)
            return 200, _ok(list_goals(status=status, include_cancelled=include_cancelled))
        goal = get_goal(parts[1])
        if not goal:
            raise ApiError(404, f"Goal not found: {parts[1]}")
        return 200, _ok(goal)

    if parts[0] == "patches":
        if len(parts) == 1:
            status = query.get("status", [""])[0]
            patches = list_patch_proposals()
            if status:
                patches = [patch for patch in patches if patch.get("status") == status]
            return 200, _ok(patches)
        patch = load_patch_proposal(parts[1])
        if not patch:
            raise ApiError(404, f"Patch proposal not found: {parts[1]}")
        return 200, _ok(patch)

    if parts[0] == "dashboard-chat":
        turns = list_dashboard_chat_turns()
        if len(parts) == 1:
            limit = int(query.get("limit", ["25"])[0] or 25)
            return 200, _ok(turns[: max(1, min(limit, 100))])
        turn_id = "latest" if parts[1] == "latest" else parts[1]
        turn = turns[0] if turn_id == "latest" and turns else load_dashboard_chat_turn(turn_id)
        if not turn:
            raise ApiError(404, f"Dashboard chat turn not found: {turn_id}")
        return 200, _ok(turn)

    raise ApiError(404, f"Unknown API endpoint: /api/{'/'.join(parts)}")


def handle_api_post(path: str, body: dict[str, Any] | None = None, query: dict[str, list[str]] | None = None) -> tuple[int, dict[str, Any]]:
    body = body or {}
    query = query or {}
    parts = _path_parts(path)

    if parts == ["controlled-self-build"]:
        project_id = str(body.get("project", "eidolon"))
        max_steps = int(body.get("steps", body.get("max_steps", 1)) or 1)
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        use_ai = _body_bool(body, "use_ai", False)
        if live:
            _require_confirmation(body, "LIVE_CONTROLLED_BUILD")
        return 200, _ok(build_controlled_self_build(project_id=project_id, max_steps=max_steps, live=live, approve_live=approve, use_ai=use_ai))

    if len(parts) >= 2 and parts[0] == "controlled-build":
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        live = _body_bool(body, "live", False)
        action = parts[1]
        if action == "plan-patch":
            return 200, _ok(build_patch_plan(project_id=project_id, target_version=str(body.get("version", "10.0")), save=True))
        if action == "stage-patch":
            return 200, _ok(stage_controlled_patch(project_id=project_id, save=True))
        if action == "preview-diff":
            return 200, _ok(preview_staged_diff(project_id=project_id, stage_if_missing=True, save=True))
        if action == "apply-staged-patch":
            if not dry_run and approve:
                _require_confirmation(body, "APPLY_STAGED_PATCH")
            return 200, _ok(apply_staged_patch(project_id=project_id, approve=approve, dry_run=dry_run))
        if action == "verify-latest-patch":
            return 200, _ok(verify_latest_patch(project_id=project_id))
        if action == "rollback-latest-patch":
            if not dry_run and approve:
                _require_confirmation(body, "ROLLBACK_LATEST_PATCH")
            return 200, _ok(rollback_latest_patch(project_id=project_id, approve=approve, dry_run=dry_run))
        if action == "cycle":
            if live:
                _require_confirmation(body, "LIVE_CONTROLLED_BUILD_CYCLE")
            return 200, _ok(build_controlled_build_cycle(project_id=project_id, live=live, approve=approve, dry_run=dry_run or not live))

    if parts == ["controlled-build-cycle"]:
        project_id = str(body.get("project", "eidolon"))
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if live:
            _require_confirmation(body, "LIVE_CONTROLLED_BUILD_CYCLE")
        return 200, _ok(build_controlled_build_cycle(project_id=project_id, live=live, approve=approve, dry_run=dry_run or not live))

    if parts == ["supervised-dev-loop"]:
        project_id = str(body.get("project", "eidolon"))
        live = _body_bool(body, "live", False)
        approve = _body_bool(body, "approve", False)
        use_ai = _body_bool(body, "use_ai", False)
        if live:
            _require_confirmation(body, "LIVE_SUPERVISED_DEV_LOOP")
        return 200, _ok(build_supervised_dev_loop(project_id=project_id, live=live, approve=approve, use_ai=use_ai))

    if parts == ["workspace", "apply"]:
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GUARDED_WORKSPACE_APPLY")
        return 200, _ok(build_workspace_apply(project_id=project_id, approve=approve, dry_run=dry_run or not approve))

    if parts == ["workspace", "guarded-dev-loop"]:
        project_id = str(body.get("project", "eidolon"))
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GUARDED_WORKSPACE_DEV_LOOP")
        return 200, _ok(build_guarded_workspace_dev_loop(project_id=project_id, approve=approve, dry_run=dry_run or not approve, save=bool(approve and not dry_run)))

    if parts == ["patch-draft-request"]:
        return 200, _ok(build_patch_draft_request(
            project_id=str(body.get("project", "eidolon")),
            target_version=str(body.get("target_version") or body.get("version") or "20.0.1"),
            task=str(body.get("task")) if body.get("task") is not None else None,
            intent=str(body.get("intent")) if body.get("intent") is not None else None,
            constraints=[str(item) for item in body.get("constraints", [])] if isinstance(body.get("constraints", []), list) else None,
            expected_files=[str(item) for item in body.get("expected_files", [])] if isinstance(body.get("expected_files", []), list) else None,
            risk_limit=str(body.get("risk_limit") or "medium"),
            save=True,
        ))

    if parts == ["draft-patch"]:
        return 200, _ok(build_draft_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["patch-review-notes"]:
        return 200, _ok(build_patch_review_notes(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["draft-diff"]:
        return 200, _ok(build_draft_diff(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["draft-test-impact"]:
        return 200, _ok(build_draft_test_impact(project_id=str(body.get("project", "eidolon")), save=True))

    if parts == ["approve-draft"]:
        return 200, _ok(approve_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["reject-draft"]:
        return 200, _ok(reject_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["apply-approved-draft"]:
        dry_run = _body_bool(body, "dry_run", True)
        if not dry_run:
            _require_confirmation(body, "APPLY_APPROVED_DRAFT")
        return 200, _ok(build_apply_approved_draft(project_id=str(body.get("project", "eidolon")), dry_run=dry_run, save=True))

    if parts == ["rollback-approved-draft"]:
        dry_run = _body_bool(body, "dry_run", True)
        approve = _body_bool(body, "approve", False)
        if approve and not dry_run:
            _require_confirmation(body, "ROLLBACK_APPROVED_DRAFT")
        return 200, _ok(build_rollback_approved_draft(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts == ["reopen-draft"]:
        return 200, _ok(reopen_draft(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") is not None else None, save=True))

    if parts == ["human-approved-patch-loop"]:
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "HUMAN_APPROVED_PATCH_LOOP")
        return 200, _ok(build_human_approved_patch_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["patch-drafts", "quality"], ["draft-quality"]):
        return 200, _ok(build_draft_quality(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "file-targets"], ["draft-file-targets"]):
        return 200, _ok(build_draft_file_targets(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "intent-blocks"], ["draft-intent-blocks"]):
        return 200, _ok(build_draft_intent_blocks(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "conflicts"], ["draft-conflicts"]):
        return 200, _ok(build_draft_conflicts(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "verification-bundle"], ["draft-verification-bundle"]):
        return 200, _ok(build_draft_verification_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "review-checklist"], ["draft-review-checklist"]):
        return 200, _ok(build_draft_review_checklist(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "execution-report"], ["approved-draft-execution-report"]):
        return 200, _ok(build_approved_draft_execution_report(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["patch-drafts", "review-loop"], ["review-centered-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "REVIEW_CENTERED_PATCH_LOOP")
        return 200, _ok(build_review_centered_patch_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-edit-proposal"], ["patch-drafts", "code-edit-proposal"]):
        return 200, _ok(build_code_edit_proposal(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["safe-rewrite-preview"], ["patch-drafts", "safe-rewrite-preview"]):
        return 200, _ok(build_safe_rewrite_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["generate-code-patch"], ["patch-drafts", "generated-code-patch"]):
        return 200, _ok(build_generated_code_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["test-suggestions"], ["patch-drafts", "test-suggestions"]):
        return 200, _ok(build_test_suggestions(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["inline-review-note"], ["patch-drafts", "inline-review-note"]):
        return 200, _ok(build_inline_review_note(
            project_id=str(body.get("project", "eidolon")),
            note=str(body.get("note")) if body.get("note") is not None else None,
            file_path=str(body.get("file")) if body.get("file") is not None else None,
            intent_block=str(body.get("intent_block")) if body.get("intent_block") is not None else None,
            save=True,
        ))

    if parts in (["apply-approved-code-patch"], ["patch-drafts", "apply-approved-code-patch"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_APPROVED_CODE_PATCH")
        return 200, _ok(build_apply_approved_code_patch(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["prepare-release-package"], ["release", "package"]):
        return 200, _ok(build_prepare_release_package(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name")) if body.get("package_name") is not None else None, save=True))

    if parts in (["release-readiness"], ["release", "readiness"]):
        return 200, _ok(build_release_readiness(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["human-approved-release-loop"], ["release", "human-approved-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "HUMAN_APPROVED_RELEASE_LOOP")
        return 200, _ok(build_human_approved_release_loop(project_id=str(body.get("project", "eidolon")), approve_apply=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "status"], ["code-patch-status"]):
        return 200, _ok(build_code_patch_status(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "symbol-scan"], ["symbol-scan"]):
        return 200, _ok(build_symbol_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "rewrite-plan"], ["rewrite-plan"]):
        return 200, _ok(build_rewrite_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "rewrite-conflicts"], ["rewrite-conflicts"]):
        return 200, _ok(build_rewrite_conflicts(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "diff-bundle"], ["code-patch-diff-bundle"]):
        return 200, _ok(build_code_patch_diff_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "apply-transaction"], ["apply-code-patch-transaction"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_CODE_PATCH_TRANSACTION")
        return 200, _ok(build_apply_code_patch_transaction(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "semantic-checks"], ["semantic-checks"]):
        return 200, _ok(build_semantic_checks(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "artifact"], ["release-artifact"]):
        return 200, _ok(build_release_artifact(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name")) if body.get("package_name") is not None else None, save=True))

    if parts in (["release", "audit-trail"], ["release-audit-trail"]):
        return 200, _ok(build_release_audit_trail(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "generated-code-loop"], ["generated-code-release-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "GENERATED_CODE_RELEASE_LOOP")
        return 200, _ok(build_generated_code_release_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "task-to-code-patch"], ["task-to-code-patch"]):
        return 200, _ok(build_task_to_code_patch(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "code-context"], ["code-context"]):
        return 200, _ok(build_code_context(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "patch-prompt"], ["patch-prompt"]):
        return 200, _ok(build_patch_prompt(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "parse-generated-edits"], ["parse-generated-edits"]):
        return 200, _ok(build_parse_generated_edits(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "edit-consistency"], ["edit-consistency"]):
        return 200, _ok(build_edit_consistency(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "ai-dry-run"], ["ai-code-patch-dry-run"]):
        return 200, _ok(build_ai_code_patch_dry_run(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "failure-analysis"], ["patch-failure-analysis"]):
        return 200, _ok(build_patch_failure_analysis(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "learning-notes"], ["patch-learning-notes"]):
        return 200, _ok(build_patch_learning_notes(project_id=str(body.get("project", "eidolon")), note=str(body.get("note")) if body.get("note") else None, save=True))

    if parts in (["code-patches", "ai-assisted-loop"], ["ai-assisted-code-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "AI_ASSISTED_CODE_PATCH_LOOP")
        return 200, _ok(build_ai_assisted_code_patch_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "objective-refinement"], ["refine-patch-objective"]):
        return 200, _ok(build_patch_objective_refinement(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "context-ranking"], ["rank-code-context"]):
        return 200, _ok(build_code_context_ranking(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "safety-envelope"], ["patch-safety-envelope"]):
        return 200, _ok(build_patch_safety_envelope(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "validate-generated-patch"], ["validate-generated-patch"]):
        return 200, _ok(build_generated_patch_validation(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "simulation"], ["patch-simulation"]):
        return 200, _ok(build_patch_simulation(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "test-stub-plan"], ["test-stub-plan"]):
        return 200, _ok(build_test_stub_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "review-score"], ["patch-review-score"]):
        return 200, _ok(build_patch_review_score(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "recovery-plan"], ["patch-recovery-plan"]):
        return 200, _ok(build_patch_recovery_plan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "validated-ai-loop"], ["validated-ai-code-patch-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "VALIDATED_AI_CODE_PATCH_LOOP")
        return 200, _ok(build_validated_ai_code_patch_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "apply-validated-ai-patch"], ["apply-validated-ai-patch"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPLY_VALIDATED_AI_PATCH")
        return 200, _ok(build_apply_validated_ai_patch(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["release", "approval-to-release-loop"], ["approval-to-release-loop"]):
        approve = _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if approve and not dry_run:
            _require_confirmation(body, "APPROVAL_TO_RELEASE_LOOP")
        return 200, _ok(build_approval_to_release_loop(project_id=str(body.get("project", "eidolon")), approve=approve, dry_run=dry_run or not approve, save=True))

    if parts in (["code-patches", "refresh-review-bundle"], ["refresh-ai-patch-review-bundle"]):
        return 200, _ok(build_ai_patch_review_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["code-patches", "bind-validated-approval"], ["bind-validated-approval"]):
        return 200, _ok(bind_current_approval_to_validated_manifest(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "manifest-integrity"], ["release-manifest-integrity"]):
        return 200, _ok(build_release_manifest_integrity(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "package-inventory"], ["package-inventory"]):
        return 200, _ok(build_package_inventory(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "package-checksums"], ["package-checksums"]):
        return 200, _ok(build_package_checksums(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "notes"], ["release-notes"]):
        return 200, _ok(build_release_notes(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "handoff"], ["release-handoff-report"]):
        return 200, _ok(build_release_handoff_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "build-zip"], ["build-release-zip"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "BUILD_RELEASE_ZIP")
        return 200, _ok(build_release_zip(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "verify-unzip"], ["verify-release-unzip"]):
        return 200, _ok(build_verify_release_unzip(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "pipeline-audit"], ["release-pipeline-audit"]):
        return 200, _ok(build_release_pipeline_audit(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), save=True))

    if parts in (["release", "verified-package-loop"], ["verified-release-package-loop"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_RELEASE_PACKAGE_LOOP")
        return 200, _ok(build_verified_release_package_loop(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "profiles"], ["release-profiles"]):
        return 200, _ok(build_release_profiles(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "privacy-scan"], ["package-privacy-scan"]):
        return 200, _ok(build_package_privacy_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "portable-metadata"], ["portable-metadata-check"]):
        return 200, _ok(build_portable_metadata_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "first-run-check"], ["first-run-check"]):
        return 200, _ok(build_first_run_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "dependency-advisor"], ["dependency-advisor"]):
        return 200, _ok(build_dependency_advisor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "upgrade-notes"], ["upgrade-notes"]):
        return 200, _ok(build_upgrade_notes(project_id=str(body.get("project", "eidolon")), to_version=str(body.get("to_version") or "21.0"), save=True))

    if parts in (["release", "runtime-migration"], ["runtime-migration-check"]):
        return 200, _ok(build_runtime_migration_check(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "install-verification"], ["release-install-verification"]):
        return 200, _ok(build_release_install_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), run_smoke=_body_bool(body, "run_smoke", False), save=True))

    if parts in (["release", "verified-installable-loop"], ["verified-installable-release-loop"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_INSTALLABLE_RELEASE_LOOP")
        return 200, _ok(build_verified_installable_release_loop(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), confirm=confirm, dry_run=dry_run or not confirm, run_smoke=_body_bool(body, "run_smoke", False), save=True))

    if parts in (["release", "smoke-runtime-hardening"], ["smoke-runtime-hardening"]):
        return 200, _ok(build_smoke_runtime_hardening(project_id=str(body.get("project", "eidolon")), tier=str(body.get("tier") or "full"), save=True))

    if parts in (["release", "external-zip-install-verification"], ["external-zip-install-verification"]):
        return 200, _ok(build_external_zip_install_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "deterministic-release-manifest"], ["deterministic-release-manifest"]):
        return 200, _ok(build_deterministic_release_manifest(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "update-dry-run-plan"], ["update-dry-run-plan"]):
        return 200, _ok(build_update_dry_run_plan(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "atomic-source-update"], ["atomic-source-update"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "ATOMIC_SOURCE_UPDATE")
        return 200, _ok(build_atomic_source_update(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "runtime-migration-assistant"], ["runtime-migration-assistant"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "RUNTIME_MIGRATION_ASSISTANT")
        return 200, _ok(build_runtime_migration_assistant(project_id=str(body.get("project", "eidolon")), confirm=confirm, dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "route-safety-harness"], ["route-safety-harness"]):
        return 200, _ok(build_route_safety_harness(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "dashboard-command-center"], ["release-dashboard-command-center"]):
        return 200, _ok(build_release_dashboard_command_center(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "clean-room-install-harness"], ["clean-room-install-harness"]):
        return 200, _ok(build_clean_room_install_harness(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_smoke_tier=str(body.get("tier") or "fast"), save=True))

    if parts in (["release", "verified-self-update-release-pipeline"], ["verified-self-update-release-pipeline"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "VERIFIED_SELF_UPDATE_RELEASE_PIPELINE")
        return 200, _ok(build_verified_self_update_release_pipeline(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm=confirm, dry_run=dry_run or not confirm, run_clean_room=_body_bool(body, "run_clean_room", False), save=True))

    if parts in (["release", "trial-upgrade-from-zip"], ["trial-upgrade-from-zip"], ["release", "trial-upgrade"]):
        return 200, _ok(build_trial_upgrade_harness(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_smoke_tier=str(body.get("tier") or "fast"), save=True))

    if parts in (["release", "backup-rollback-drill"], ["backup-rollback-drill"]):
        return 200, _ok(build_backup_rollback_drill(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "update-collision-detector"], ["update-collision-detector"]):
        return 200, _ok(build_update_collision_detector(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "version-registry-report"], ["version-registry-report"]):
        return 200, _ok(build_version_registry_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), dry_run=not _body_bool(body, "confirm", False), save=True))

    if parts in (["release", "release-provenance-report"], ["release-provenance-report"]):
        return 200, _ok(build_release_provenance_report(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "dashboard-upgrade-wizard-preview"], ["dashboard-upgrade-wizard-preview"]):
        return 200, _ok(build_dashboard_upgrade_wizard_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "api-upgrade-wizard-preview"], ["api-upgrade-wizard-preview"]):
        return 200, _ok(build_api_upgrade_wizard_preview(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "staged-apply-drill"], ["staged-apply-drill"]):
        return 200, _ok(build_staged_apply_drill(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "real-apply-guard-rails"], ["real-apply-guard-rails"]):
        return 200, _ok(build_real_apply_guard_rails(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), expected_manifest_hash=body.get("expected_manifest_hash"), confirm_phrase=str(body.get("confirm_phrase") or ""), save=True))

    if parts in (["release", "real-apply-rollback-verification"], ["real-apply-rollback-verification"]):
        return 200, _ok(build_real_apply_rollback_verification(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "self-update-ux-polish"], ["self-update-ux-polish"]):
        return 200, _ok(build_self_update_ux_polish(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "v23-readiness-gate"], ["v23-readiness-gate"]):
        return 200, _ok(build_v23_readiness_gate(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), run_heavy=_body_bool(body, "run_heavy", False), save=True))

    if parts in (["release", "controlled-self-maintenance-loop"], ["controlled-self-maintenance-loop"]):
        return 200, _ok(build_controlled_self_maintenance_loop(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))


    if parts in (["release", "self-maintenance-proposal"], ["self-maintenance-proposal"]):
        return 200, _ok(build_self_maintenance_proposal_sandbox(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "build-patch-plan"], ["build-patch-plan"]):
        return 200, _ok(build_patch_plan_builder(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "generate-maintenance-patch"], ["generate-maintenance-patch"]):
        return 200, _ok(build_dry_run_patch_generator(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "patch-safety-audit"], ["patch-safety-audit"]):
        return 200, _ok(build_patch_safety_auditor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "apply-maintenance-patch-to-temp"], ["apply-maintenance-patch-to-temp"]):
        return 200, _ok(build_apply_patch_to_temp_clone(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "maintenance-review-bundle"], ["maintenance-review-bundle"]):
        return 200, _ok(build_maintenance_review_bundle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "approve-maintenance-bundle"], ["approve-maintenance-bundle"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        if confirm:
            _require_confirmation(body, "APPROVE_MAINTENANCE_BUNDLE")
        return 200, _ok(build_human_approval_binding(project_id=str(body.get("project", "eidolon")), bundle_hash=body.get("bundle_hash"), confirm=confirm, save=True))

    if parts in (["release", "real-maintenance-patch-apply"], ["real-maintenance-patch-apply"]):
        confirm = _body_bool(body, "confirm", False) or _body_bool(body, "approve", False)
        dry_run = _body_bool(body, "dry_run", True)
        if confirm and not dry_run:
            _require_confirmation(body, "APPLY EXACT REVIEWED MAINTENANCE BUNDLE")
        return 200, _ok(build_real_maintenance_patch_apply(project_id=str(body.get("project", "eidolon")), bundle_hash=body.get("bundle_hash"), confirm_phrase=str(body.get("confirm_phrase") or body.get("confirmation") or ""), dry_run=dry_run or not confirm, save=True))

    if parts in (["release", "improvement-candidate-scan"], ["improvement-candidate-scan"]):
        return 200, _ok(build_improvement_candidate_scan(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-prioritizer"], ["candidate-prioritizer"]):
        return 200, _ok(build_candidate_prioritizer(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-to-proposal"], ["candidate-to-proposal"]):
        return 200, _ok(build_candidate_to_proposal_bridge(project_id=str(body.get("project", "eidolon")), candidate_id=body.get("candidate_id"), save=True))

    if parts in (["release", "maintenance-backlog"], ["maintenance-backlog"]):
        return 200, _ok(build_maintenance_backlog_registry(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-regression-detector"], ["candidate-regression-detector"]):
        return 200, _ok(build_candidate_regression_detector(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "release-memory-privacy"], ["release-memory-privacy"]):
        return 200, _ok(build_release_memory_privacy(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "candidate-verification-recipes"], ["candidate-verification-recipes"]):
        return 200, _ok(build_candidate_verification_recipes(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "assisted-improvement-cycle"], ["assisted-improvement-cycle"]):
        return 200, _ok(build_assisted_improvement_cycle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "semi-autonomous-maintenance-review"], ["semi-autonomous-maintenance-review"]):
        return 200, _ok(build_semi_autonomous_maintenance_review(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts in (["release", "set-maintenance-candidate-status"], ["set-maintenance-candidate-status"]):
        _require_confirmation(body, "ACCEPT_MAINTENANCE_CANDIDATE_STATUS")
        return 200, _ok({"status": "preview_saved", "message": "Candidate status mutation requires POST confirmation; runtime backlog writes remain outside source-only packages.", "candidate_id": body.get("candidate_id"), "new_status": body.get("status")})

    if parts in (["release", "post-apply-health-monitor"], ["post-apply-health-monitor"]):
        return 200, _ok(build_post_apply_health_monitor(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "controlled-maintenance-cycle"], ["controlled-maintenance-cycle"]):
        return 200, _ok(build_controlled_maintenance_cycle(project_id=str(body.get("project", "eidolon")), save=True))

    if parts in (["release", "assisted-self-improvement-release"], ["assisted-self-improvement-release"]):
        return 200, _ok(build_assisted_self_improvement_release(project_id=str(body.get("project", "eidolon")), package_name=str(body.get("package_name") or _package_name()), zip_path=body.get("zip_path"), save=True))

    if parts == ["projects", "register"]:
        name = str(body.get("name") or body.get("project") or "Workspace Project")
        tests = body.get("test_commands", [])
        if isinstance(tests, str):
            tests = [tests]
        if not isinstance(tests, list):
            tests = []
        return 200, _ok(register_project(
            name=name,
            root=str(body.get("root") or "."),
            version=str(body.get("version") or "unknown"),
            language=str(body.get("language") or "unknown"),
            framework_type=str(body.get("framework_type") or body.get("framework") or "unknown"),
            readme_path=str(body.get("readme_path") or "README_NEXT_STEPS.md"),
            test_commands=[str(item) for item in tests],
            safe_command_profile=str(body.get("safe_command_profile") or "default_python"),
            project_id=str(body.get("id") or body.get("project_id") or "") or None,
        ))

    if parts == ["projects", "active"]:
        project_id = str(body.get("project_id") or body.get("id") or "")
        if not project_id:
            raise ApiError(400, "project_id is required.")
        return 200, _ok(set_active_workspace_project(project_id))

    if parts == ["workspace", "switch-project"]:
        project_id = str(body.get("project_id") or body.get("id") or "")
        if not project_id:
            raise ApiError(400, "project_id is required.")
        return 200, _ok(switch_workspace_project(project_id=project_id, force=_body_bool(body, "force", False)))

    if parts == ["setup", "run"]:
        report = create_setup_report(save=True)
        return 201, _ok(report, message=f"Setup report saved: {report.get('id')}")

    if parts == ["onboarding", "run"]:
        refresh_setup = _body_bool(body, "refresh_setup", True)
        run = build_onboarding_run(save=True, refresh_setup=refresh_setup)
        return 201, _ok(run, message=f"Onboarding run saved: {run.get('id')} ({run.get('status')})")

    if parts == ["diagnostics", "run"]:
        include_full = _body_bool(body, "include_full", False) or _query_bool(query, "include_full", False)
        report = build_diagnostic_report(include_full=include_full)
        save_diagnostic_report(report)
        return 201, _ok(report, message=f"Diagnostic report saved: {report.get('id')}")

    if parts == ["watch", "run-once"]:
        use_ai = _body_bool(body, "use_ai", False)
        create_maintenance = _body_bool(body, "create_maintenance", True)
        create_session = _body_bool(body, "create_session", True)
        result = run_watch_once(use_ai=use_ai, create_maintenance=create_maintenance, create_session=create_session)
        report = load_watch_report(result.report_id) if result.report_id else None
        return 201, _ok({"result": result, "report": report}, message=result.text.splitlines()[0] if result.text else "Watch report saved.")

    if parts == ["watch", "run-loop"]:
        cycles = int(body.get("cycles", query.get("cycles", [2])[0]) or 2)
        interval = int(body.get("interval_seconds", body.get("interval", query.get("interval", [5])[0])) or 5)
        use_ai = _body_bool(body, "use_ai", False)
        create_maintenance = _body_bool(body, "create_maintenance", True)
        create_session = _body_bool(body, "create_session", True)
        loop = run_watch_loop(cycles=cycles, interval_seconds=interval, use_ai=use_ai, create_maintenance=create_maintenance, create_session=create_session)
        return 201, _ok(loop, message=f"Watch loop saved: {loop.get('id')}")

    if parts == ["session-plans", "run"]:
        use_ai = _body_bool(body, "use_ai", bool(get_setting("ai_reviews_enabled", True)))
        result = create_session_plan(use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Session plan creation failed.", result)
        plan = load_session_plan(result.plan_id)
        return 201, _ok({"result": result, "plan": plan}, message=f"Session plan saved: {result.plan_id}")

    if parts == ["maintenance", "run"]:
        use_ai = _body_bool(body, "use_ai", False)
        result = run_maintenance_scan(use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Maintenance scan failed.", result)
        scan = load_maintenance_scan(result.scan_id)
        return 201, _ok({"result": result, "scan": scan}, message=f"Maintenance scan saved: {result.scan_id}")

    if parts == ["dev-loops", "run"]:
        task_id = str(body.get("task_id") or "latest-ready")
        max_steps = int(body.get("max_steps", body.get("steps", 3)) or 3)
        dry_run = _body_bool(body, "dry_run", True)
        approve_apply = _body_bool(body, "approve_apply", False)
        apply_evaluation = _body_bool(body, "apply_evaluation", False)
        use_ai = _body_bool(body, "use_ai", False)
        loop = run_dev_loop(
            task_id=task_id,
            max_steps=max_steps,
            dry_run=dry_run,
            approve_apply=approve_apply,
            apply_evaluation=apply_evaluation,
            use_ai=use_ai,
        )
        return 201, _ok(loop, message=f"Dev loop saved: {loop.get('id')}")

    if len(parts) == 3 and parts[0] == "stable-loops" and parts[1] not in {"decisions", "followups"} and parts[2] in {"review", "approve-live", "reject", "archive", "restore", "run-approved-live", "refresh-audit", "operator-notes", "decision", "create-followups", "resolve-followups", "mark-followups-closed"}:
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        note = str(body.get("note") or "")
        if parts[2] == "review":
            status = str(body.get("status") or "reviewed")
            result = update_stable_loop_review(loop_id, status=status, note=note, reviewer="api")
        elif parts[2] == "approve-live":
            result = update_stable_loop_review(loop_id, status="approved_for_live", note=note or "Approved for live through local API.", reviewer="api")
        elif parts[2] == "reject":
            result = update_stable_loop_review(loop_id, status="rejected", note=note or "Rejected through local API.", reviewer="api")
        elif parts[2] == "archive":
            result = set_stable_loop_archived(loop_id, archived=True, note=note or "Archived through local API.", reviewer="api")
        elif parts[2] == "restore":
            result = set_stable_loop_archived(loop_id, archived=False, note=note or "Restored through local API.", reviewer="api")
        elif parts[2] == "refresh-audit":
            result = refresh_stable_loop_audit(loop_id)
        elif parts[2] == "operator-notes":
            result = add_stable_loop_operator_note(loop_id, note=note, reviewer="api")
        elif parts[2] == "decision":
            result = set_stable_loop_final_decision(
                loop_id,
                decision=str(body.get("decision") or body.get("final_decision") or "needs_review"),
                note=note,
                reviewer="api",
            )
        elif parts[2] == "create-followups":
            result = create_stable_loop_followup_tasks(
                loop_id=loop_id,
                dry_run=_body_bool(body, "dry_run", True),
                force=_body_bool(body, "force", False),
                reviewer="api",
            )
        elif parts[2] == "resolve-followups":
            result = resolve_stable_loop_followups(
                loop_id=loop_id,
                archive=_body_bool(body, "archive", False),
                force=_body_bool(body, "force", False),
                note=note or "Resolved through local API.",
                reviewer="api",
            )
        elif parts[2] == "mark-followups-closed":
            result = mark_stable_loop_followup_chain_closed(
                loop_id=loop_id,
                note=note or "Follow-up chain closure confirmed through local API.",
                reviewer="api",
                archive=_body_bool(body, "archive", False),
            )
        else:
            use_ai = body.get("use_ai")
            approve_work_execution = body.get("approve_work_execution")
            result = run_approved_stable_loop_live(
                loop_id,
                use_ai=None if use_ai is None else _body_bool(body, "use_ai", False),
                approve_work_execution=None if approve_work_execution is None else _body_bool(body, "approve_work_execution", False),
                note=note or "Live stable loop launched through local API review action.",
            )
        result_ok = result.get("ok") if isinstance(result, dict) else result.ok
        result_error = result.get("error", "") if isinstance(result, dict) else result.error
        result_message = result.get("message", "") if isinstance(result, dict) else result.message
        if not result_ok:
            raise ApiError(400, result_error or "Stable loop review action failed.", result)
        return 200, _ok(result, message=result_message)

    if len(parts) == 4 and parts[0] == "stable-loops" and parts[2] == "checklist":
        loop_id = "latest" if parts[1] == "latest" else parts[1]
        result = update_stable_loop_check(
            loop_id,
            check_id=parts[3],
            status=str(body.get("status") or "done"),
            note=str(body.get("note") or ""),
            reviewer="api",
        )
        if not result.ok:
            raise ApiError(400, result.error or "Stable loop checklist action failed.", result)
        return 200, _ok(result, message=result.message)

    if len(parts) == 4 and parts[0] == "tasks" and parts[2] == "stable-loop-followup" and parts[3] == "resolve":
        result = resolve_task_stable_loop_followup(
            parts[1],
            archive=_body_bool(body, "archive", False),
            force=_body_bool(body, "force", False),
            note=str(body.get("note") or "Resolved through local API task endpoint."),
            reviewer="api",
        )
        if not result.ok:
            raise ApiError(400, result.error or "Stable-loop follow-up resolution failed.", result.to_dict())
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "followups", "completion", "cleanup"]:
        completion_filter = str(body.get("completion") or body.get("filter") or query.get("completion", ["cleanup_default"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_archived = _body_bool(body, "include_archived", False)
        result = cleanup_stable_loop_followup_completions(
            completion_filter=completion_filter,
            limit=limit,
            dry_run=dry_run,
            include_archived=include_archived,
            reviewer="api",
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "decisions", "cleanup"]:
        decision_filter = str(body.get("decision") or body.get("filter") or query.get("decision", ["cleanup_default"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        result = cleanup_stable_loop_decision_history(
            decision_filter=decision_filter,
            limit=limit,
            dry_run=dry_run,
            include_live=include_live,
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "decisions", "create-followups"]:
        decision_filter = str(body.get("decision") or body.get("filter") or query.get("decision", ["action_required"])[0])
        limit = int(body.get("limit") or query.get("limit", ["25"])[0] or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        include_archived = _body_bool(body, "include_archived", False)
        result = create_stable_loop_followups_for_decisions(
            decision_filter=decision_filter,
            dry_run=dry_run,
            include_archived=include_archived,
            include_live=include_live,
            limit=limit,
            force=_body_bool(body, "force", False),
            reviewer="api",
        )
        return 200, _ok(result.to_dict(), message=result.message)

    if parts == ["stable-loops", "history", "cleanup"]:
        review_filter = str(body.get("review") or body.get("status") or "cleanup_default")
        limit = int(body.get("limit", 25) or 25)
        dry_run = _body_bool(body, "dry_run", True)
        include_live = _body_bool(body, "include_live", True)
        result = cleanup_stable_loop_history(
            review_filter=review_filter,
            limit=limit,
            dry_run=dry_run,
            include_live=include_live,
            reviewer="api",
        )
        return 200, _ok(result, message=result.get("message", "Stable loop history cleanup complete."))

    if parts == ["stable-loops", "run"]:
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        max_steps = int(body.get("max_steps", body.get("steps", 1)) or 1)
        live = _body_bool(body, "live", False)
        use_ai = _body_bool(body, "use_ai", True)
        approve_work_execution = _body_bool(body, "approve_work_execution", False)
        seed_if_empty = _body_bool(body, "seed_if_empty", True)
        auto_followups = _body_bool(body, "auto_create_patch_followups", True)
        auto_request_approvals = _body_bool(body, "auto_request_approvals", True)
        auto_retry_recovery = _body_bool(body, "auto_retry_recovery", False)
        bypass_closure_guardrails = _body_bool(body, "bypass_closure_guardrails", False)
        result = run_stable_supervised_loop(
            project_id=project_id,
            max_steps=max_steps,
            live=live,
            use_ai=use_ai,
            approve_work_execution=approve_work_execution,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_followups,
            auto_request_approvals=auto_request_approvals,
            auto_retry_recovery=auto_retry_recovery,
            bypass_closure_guardrails=bypass_closure_guardrails,
        )
        loop = load_stable_loop(result.loop_id)
        return 201, _ok({"result": result, "loop": loop}, message=result.message)

    if parts == ["work-cycles", "run"]:
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        max_steps = int(body.get("max_steps", body.get("steps", 1)) or 1)
        dry_run = _body_bool(body, "dry_run", True)
        use_ai = _body_bool(body, "use_ai", True)
        approve_work_execution = _body_bool(body, "approve_work_execution", False)
        seed_if_empty = _body_bool(body, "seed_if_empty", True)
        auto_followups = _body_bool(body, "auto_create_patch_followups", True)
        auto_request_approvals = _body_bool(body, "auto_request_approvals", True)
        auto_retry_recovery = _body_bool(body, "auto_retry_recovery", False)
        result = run_supervised_work_cycle(
            project_id=project_id,
            max_steps=max_steps,
            dry_run=dry_run,
            use_ai=use_ai,
            approve_work_execution=approve_work_execution,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_followups,
            auto_request_approvals=auto_request_approvals,
            auto_retry_recovery=auto_retry_recovery,
        )
        cycle = load_work_cycle(result.cycle_id)
        return 201, _ok({"result": result, "cycle": cycle}, message=result.message)

    if parts and parts[0] == "notifications":
        if parts == ["notifications", "clear-dismissed"]:
            count = clear_dismissed_notifications()
            return 200, _ok({"cleared": count}, message=f"Cleared {count} dismissed notification(s).")
        if len(parts) == 3 and parts[2] in {"read", "dismiss"}:
            status = "read" if parts[2] == "read" else "dismissed"
            note = body.get("note", f"Marked {status} through local API.")
            result = update_notification_status(parts[1], status, note=note)
            if not result.get("ok"):
                raise ApiError(404, str(result.get("error", "Notification update failed.")), result)
            return 200, _ok(result, message=f"Notification marked {status}.")

    if parts and parts[0] == "approvals" and len(parts) == 3:
        approval_id = parts[1]
        if parts[2] == "approve":
            dry_run = _body_bool(body, "dry_run", False)
            result = approve_approval(approval_id, dry_run=dry_run)
            if not result.get("ok"):
                raise ApiError(400, str(result.get("error", "Approval failed.")), result)
            return 200, _ok(result, message=str(result.get("message") or result.get("status") or "Approval handled."))
        if parts[2] == "reject":
            note = str(body.get("note", "Rejected through local API."))
            result = reject_approval(approval_id, note=note)
            if not result.get("ok"):
                raise ApiError(400, str(result.get("error", "Approval reject failed.")), result)
            return 200, _ok(result, message=f"Approval rejected: {result.get('id', approval_id)}")

    if parts == ["chat-actions"]:
        message = str(body.get("message") or body.get("request") or "").strip()
        if not message:
            raise ApiError(400, "message is required.")
        action = propose_chat_action(message, save=True)
        return 201, _ok(action, message=f"Chat action saved: {action.get('id')}")

    if parts and parts[0] == "chat-actions" and len(parts) == 3:
        action_id = parts[1]
        if parts[2] in {"dry-run", "execute"}:
            dry_run = parts[2] == "dry-run" or _body_bool(body, "dry_run", False)
            result = execute_chat_action(action_id, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or result.message or "Chat action failed.", result)
            saved = load_chat_action(result.chat_action_id)
            return 200, _ok({"result": result, "chat_action": saved}, message=result.message)

    if parts == ["tasks", "request-approvals"]:
        stage = normalize_lifecycle_stage_filter(str(body.get("stage") or "approval_required"))
        project_id = str(body.get("project_id") or body.get("project") or "").strip()
        dry_run = _body_bool(body, "dry_run", False)
        use_ai = _body_bool(body, "use_ai", True)
        force = _body_bool(body, "force", False)
        reason = str(body.get("reason") or "Batch approval request from lifecycle filter.")
        rows = list_task_lifecycles(project=project_id, include_closed=False, stage_filter=stage)
        results = []
        created = 0
        failed = 0
        for row in rows:
            task_id = str(row.get("task_id") or "").strip()
            if not task_id:
                continue
            result = request_task_work_approval(task_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            result_data = _to_jsonable(result)
            result_data["stage"] = row.get("stage")
            results.append(result_data)
            if result.ok:
                created += 1
            else:
                failed += 1
        return 200 if dry_run else 201, _ok({
            "stage": stage,
            "dry_run": dry_run,
            "matched": len(rows),
            "created_or_valid": created,
            "failed": failed,
            "results": results,
        }, message=f"Handled approval requests for {created} of {len(rows)} task(s).")

    if parts == ["tasks", "patch-request"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("description") or body.get("message") or "").strip()
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        task = create_patch_task(
            target_file=target_file,
            request=request,
            project_id=str(body.get("project_id") or body.get("project") or "eidolon"),
            priority=int(body.get("priority") or 7),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
        )
        return 201, _ok(task, message=f"Patch task created: {task.get('id')}")

    if parts == ["work-queue", "patch-request"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("description") or body.get("message") or "").strip()
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        item = create_patch_work_item(
            target_file=target_file,
            request=request,
            project_id=str(body.get("project_id") or body.get("project") or "eidolon"),
            priority=int(body.get("priority") or 7),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
        )
        return 201, _ok(item, message=f"Patch task created through legacy alias: {item.id}")

    if parts == ["work-queue"]:
        title = str(body.get("title") or "").strip()
        if not title:
            raise ApiError(400, "title is required.")
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        item = add_work_item(
            title=title,
            description=str(body.get("description") or ""),
            project_id=str(body.get("project_id") or body.get("project") or "default"),
            priority=int(body.get("priority") or 5),
            risk=str(body.get("risk") or "low"),
            source="dashboard" if str(body.get("source") or "") == "dashboard" else "system",
            requires_approval=requires_approval,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
        )
        return 201, _ok(item, message=f"Task created through legacy alias: {item.id}")

    if parts and parts[0] == "tasks" and len(parts) == 3 and parts[2] == "suggest-patch":
        task_id = parts[1]
        dry_run = _body_bool(body, "dry_run", False)
        use_ai = _body_bool(body, "use_ai", True)
        result = suggest_patch_for_task(task_id, use_ai=use_ai, dry_run=dry_run)
        if not result.ok:
            raise ApiError(400, result.error or "Patch suggestion from task failed.", result)
        patch = load_patch_proposal(result.patch_id) if result.patch_id else None
        return 200, _ok({"result": result, "patch": patch}, message=result.message or "Patch suggestion handled.")

    if parts and parts[0] == "tasks" and len(parts) == 3:
        task_id = parts[1]
        operation = parts[2]
        if task_id == "next" and operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            result = execute_next_task_work(project_id=project_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if task_id == "next" and operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            reason = str(body.get("reason") or "")
            result = request_next_task_work_approval(project_id=project_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            reason = str(body.get("reason") or "")
            result = request_task_work_approval(task_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = execute_task_work_item(task_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if operation == "ready-for-retry":
            note = str(body.get("note") or "Marked ready for retry through local API.")
            result = mark_task_ready_for_retry(task_id, note=note)
            if not result.ok:
                raise ApiError(400, result.error or "Could not mark task ready for retry.", result)
            return 200, _ok(result, message=result.message)
        if operation == "retry":
            dry_run = _body_bool(body, "dry_run", True)
            use_ai = _body_bool(body, "use_ai", True)
            allow_approval_required = _body_bool(body, "allow_approval_required", False)
            result = retry_task_work(task_id, dry_run=dry_run, allow_approval_required=allow_approval_required, use_ai=use_ai)
            if not result.ok and not dry_run:
                raise ApiError(400, result.error or "Task retry failed.", result)
            return 200, _ok(result, message=result.message or result.error or "Task retry handled.")
        if operation == "done":
            result_text = str(body.get("result") or "Marked done through local API.")
            mutation = update_task_fields(task_id, status="done", result=result_text)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task marked done: {task_id}")
        if operation == "block":
            reason = str(body.get("reason") or "Blocked through local API.")
            mutation = update_task_fields(task_id, status="blocked", blocked_reason=reason)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task blocked: {task_id}")
        if operation == "cancel":
            result_text = str(body.get("result") or "Cancelled through local API.")
            mutation = update_task_fields(task_id, status="cancelled", result=result_text)
            if not mutation.ok:
                raise ApiError(404, mutation.error or f"Task not found: {task_id}", mutation)
            return 200, _ok(mutation.task, message=f"Task cancelled: {task_id}")

    if parts and parts[0] == "work-queue" and len(parts) == 3:
        item_id = parts[1]
        operation = parts[2]
        if item_id == "next" and operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            result = execute_next_task_work(project_id=project_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if item_id == "next" and operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            project_id = str(body.get("project_id") or body.get("project") or "").strip() or None
            reason = str(body.get("reason") or "")
            result = request_next_task_work_approval(project_id=project_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "request-approval":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            force = _body_bool(body, "force", False)
            reason = str(body.get("reason") or "")
            result = request_task_work_approval(item_id, reason=reason, use_ai=use_ai, force=force, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Task approval request failed.", result)
            return 201, _ok(result, message=result.message or "Task approval request handled.")
        if operation == "suggest-patch":
            dry_run = _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = suggest_patch_for_work_item(item_id, use_ai=use_ai, dry_run=dry_run)
            if not result.ok:
                raise ApiError(400, result.error or "Patch suggestion from task failed.", result)
            patch = load_patch_proposal(result.patch_id) if result.patch_id else None
            return 200, _ok({"result": result, "patch": patch}, message=result.message or "Patch suggestion handled.")
        if operation in {"dry-run", "execute"}:
            dry_run = operation == "dry-run" or _body_bool(body, "dry_run", False)
            use_ai = _body_bool(body, "use_ai", True)
            result = execute_task_work_item(item_id, dry_run=dry_run, use_ai=use_ai)
            return 200, _ok(result, message=result.message or result.error or "Task work executor finished.")
        if operation == "done":
            item = update_work_item(item_id, status="done", result=str(body.get("result") or "Marked done through local API."))
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task marked done through legacy alias: {item_id}")
        if operation == "block":
            reason = str(body.get("reason") or "Blocked through local API.")
            item = update_work_item(item_id, status="blocked", blocked_reason=reason)
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task blocked through legacy alias: {item_id}")
        if operation == "cancel":
            item = update_work_item(item_id, status="cancelled", result=str(body.get("result") or "Cancelled through local API."))
            if not item:
                raise ApiError(404, f"Task not found: {item_id}")
            return 200, _ok(item, message=f"Task cancelled through legacy alias: {item_id}")

    if parts == ["tasks"]:
        requires_raw = body.get("requires_approval", None)
        if requires_raw is None:
            requires_approval = None
        elif isinstance(requires_raw, bool):
            requires_approval = requires_raw
        else:
            requires_approval = str(requires_raw).lower() in {"1", "true", "yes", "on"}
        result = add_task(
            title=str(body.get("title") or ""),
            description=str(body.get("description") or ""),
            priority=str(body.get("priority") or "medium"),
            status=str(body.get("status") or "planned"),
            project=str(body.get("project_id") or body.get("project") or ""),
            command=str(body.get("command") or ""),
            next_action=str(body.get("next_action") or ""),
            linked_goal=str(body.get("linked_goal") or ""),
            risk=str(body.get("risk") or "low"),
            source="local_api",
            requires_approval=requires_approval,
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else {},
        )
        if not result.ok:
            raise ApiError(400, result.error or "Task creation failed.", result)
        return 201, _ok(result.task, message=result.message)

    if parts == ["goals"]:
        result = add_goal(
            title=str(body.get("title") or ""),
            description=str(body.get("description") or ""),
            priority=str(body.get("priority") or "medium"),
            status=str(body.get("status") or "planned"),
            next_action=str(body.get("next_action") or ""),
        )
        if not result.ok:
            raise ApiError(400, result.error or "Goal creation failed.", result)
        return 201, _ok(result.goal, message=result.message)

    if parts and parts[0] == "patches" and len(parts) == 3 and parts[2] == "create-task-followups":
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        result = create_patch_followup_tasks(parts[1], project_id=project_id)
        if not result.ok:
            raise ApiError(400, result.error or "Could not create patch follow-up tasks.", result)
        return 201, _ok(result, message=result.message)

    if parts and parts[0] == "patches" and len(parts) == 3 and parts[2] == "create-followups":
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        result = create_patch_followup_items(parts[1], project_id=project_id)
        if not result.ok:
            raise ApiError(400, result.error or "Could not create patch follow-up tasks.", result)
        return 201, _ok(result, message=result.message)

    if parts == ["patches", "suggest"]:
        target_file = str(body.get("target_file") or body.get("file") or "").strip()
        request = str(body.get("request") or body.get("message") or "").strip()
        use_ai = _body_bool(body, "use_ai", True)
        if not target_file:
            raise ApiError(400, "target_file is required.")
        if not request:
            raise ApiError(400, "request is required.")
        result = suggest_patch(target_file, request, use_ai=use_ai)
        if not result.ok:
            raise ApiError(400, result.error or "Patch suggestion failed.", result)
        patch = load_patch_proposal(result.patch_id)
        return 201, _ok({"result": result, "patch": patch}, message=f"Patch proposal saved: {result.patch_id}")

    if parts == ["dashboard-chat"]:
        message = str(body.get("message") or "").strip()
        if not message:
            raise ApiError(400, "message is required.")
        use_ai = _body_bool(body, "use_ai", bool(get_setting("dashboard_chat_use_ai_default", True)))
        turn = create_dashboard_chat_turn(message, use_ai=use_ai)
        return 201, _ok(turn, message=f"Dashboard chat turn saved: {turn.get('id')}")

    raise ApiError(404, f"Unknown API endpoint: /api/{'/'.join(parts)}")


def dispatch_api(method: str, path: str, query: dict[str, list[str]] | None = None, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    try:
        if method.upper() == "GET":
            return handle_api_get(path, query=query)
        if method.upper() == "POST":
            return handle_api_post(path, body=body, query=query)
        raise ApiError(405, f"Unsupported API method: {method}")
    except ApiError as error:
        return error.status, _error(error.status, error.message, error.details)
    except Exception as error:
        return 500, _error(500, f"API route crashed: {error}", traceback.format_exc())


class EidolonApiHandler(BaseHTTPRequestHandler):
    server_version = "EidolonAPI/10.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(_to_jsonable(payload), indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:
        self._send_json(_ok({"methods": ["GET", "POST", "OPTIONS"]}))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api"):
            self._send_json(_error(404, "This server exposes only /api routes."), status=404)
            return
        status, payload = dispatch_api("GET", parsed.path, query=parse_qs(parsed.query))
        self._send_json(payload, status=status)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api"):
            self._send_json(_error(404, "This server exposes only /api routes."), status=404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        try:
            body = parse_request_body(raw_body, self.headers.get("Content-Type", ""))
        except ApiError as error:
            self._send_json(_error(error.status, error.message, error.details), status=error.status)
            return
        status, payload = dispatch_api("POST", parsed.path, query=parse_qs(parsed.query), body=body)
        self._send_json(payload, status=status)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_api_server(host: str | None = None, port: int | None = None) -> None:
    settings = load_settings()
    host = host or str(settings.get("api_host", "127.0.0.1"))
    port = int(port or settings.get("api_port", 8766))
    server = ThreadingHTTPServer((host, port), EidolonApiHandler)
    print(f"Eidolon local API running at http://{host}:{port}/api")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI server stopped.")
    finally:
        server.server_close()
