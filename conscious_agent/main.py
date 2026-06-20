import argparse

from chat import run_chat
from code_reviewer import print_code_review
from patch_suggester import (
    print_patch_suggestion,
    print_patch_list,
    print_patch_proposal,
    list_patch_proposals,
    resolve_patch_id,
)
from patch_applier import (
    print_apply_patch,
    print_applied_patches,
    print_rollback_patch,
    print_rolled_back_patches,
)
from file_tools import list_project_files, read_project_file, search_project_files, project_tree_text
from command_runner import (
    print_allowed_commands,
    print_run_command,
    print_command_history,
)
from test_runner import (
    print_test_workflow,
    print_test_reports,
    print_test_report,
    list_test_reports,
)
from test_report_reviewer import (
    print_test_review,
    print_saved_test_review,
    print_test_reviews,
    list_test_reviews,
)
from self_improver import (
    print_self_improvement,
    print_self_improvement_apply,
    print_self_improvement_runs,
    print_self_improvement_run,
    list_self_improvement_runs,
    latest_self_improvement_patch_id,
)
from maintenance_advisor import (
    print_maintenance_scan,
    print_maintenance_scans,
    print_saved_maintenance_scan,
    list_maintenance_scans,
)
from memory_compactor import (
    print_memory_status,
    print_compact_memory,
    print_memory_summaries,
    print_memory_summary,
    list_memory_summaries,
)
from goal_manager import (
    print_goal_status,
    print_goal_list,
    print_goal_detail,
    print_add_goal,
    print_set_goal_status,
    print_add_goal_note,
    print_add_goal_next_action,
    print_block_goal,
    print_complete_goal,
    list_goals,
    resolve_goal_id,
)
from session_planner import (
    print_session_plan,
    print_session_plans,
    print_saved_session_plan,
    list_session_plans,
)
from work_queue import run_cli as run_work_queue_cli
from task_work_executor import print_execute_next_task_work_item, print_execute_task_work_item
from task_approval_bridge import (
    print_request_task_work_approval,
    print_request_next_task_work_approval,
    print_task_approvals,
)
from task_recovery import (
    print_task_recovery,
    print_task_recoveries,
    print_mark_task_ready_for_retry,
    print_retry_task_work,
)
from task_patch_bridge import (
    print_create_patch_task,
    print_suggest_patch_for_task,
    print_create_patch_task_followups,
)
from work_queue_patch_bridge import (
    print_create_patch_work_item,
    print_suggest_patch_for_work_item,
    print_create_patch_followups,
)
from work_cycle import (
    print_work_cycle,
    print_work_cycles,
    print_saved_work_cycle,
    list_work_cycles,
    resolve_work_cycle_id,
)
from stable_supervised_loop import (
    print_stable_loop_preflight,
    print_stable_loop,
    print_stable_loops,
    print_saved_stable_loop,
    list_stable_loops,
    resolve_stable_loop_id,
)
from stable_loop_review import (
    print_stable_loop_review_summary,
    print_stable_loop_review,
    print_update_stable_loop_review,
    print_run_approved_stable_loop_live,
    print_stable_loop_reviews,
    print_archive_stable_loop,
    print_cleanup_stable_loop_history,
)
from stable_loop_audit import print_stable_loop_audit
from stable_loop_operator_notes import (
    print_stable_loop_operator_notes,
    print_add_stable_loop_operator_note,
    print_update_stable_loop_check,
    print_set_stable_loop_final_decision,
)
from stable_loop_decision_report import (
    print_stable_loop_decision_report,
    print_stable_loop_decision_rows,
    print_cleanup_stable_loop_decisions,
)
from stable_loop_followup_tasks import (
    print_stable_loop_followup_summary,
    print_create_stable_loop_followups,
    print_create_stable_loop_followups_for_decisions,
)
from stable_loop_followup_lifecycle import (
    print_resolve_stable_loop_followups,
    print_resolve_task_stable_loop_followup,
    print_stable_loop_followup_lifecycle_summary,
    print_stable_loop_followup_task,
)
from stable_loop_followup_completion import (
    print_cleanup_stable_loop_followup_completions,
    print_mark_stable_loop_followup_closed,
    print_stable_loop_followup_completion_report,
    print_stable_loop_followup_completion_rows,
)
from stable_loop_guardrails import print_stable_loop_guardrails
from stabilization_checkpoint import print_stabilization_checkpoint
from operational_readiness import (
    print_doctor,
    print_repair_suggestions,
    print_patch_integrity,
    print_project_snapshot,
    print_task_review,
    print_recovery_drill,
    print_stable_loop_confidence,
    print_hardening_report,
    print_controlled_self_build,
)
from controlled_build_cycle import (
    print_controlled_task_selection,
    print_patch_plan,
    print_patch_workspace_status,
    print_stage_controlled_patch,
    print_preview_staged_diff,
    print_apply_staged_patch,
    print_verify_latest_patch,
    print_rollback_latest_patch,
    print_readme_gate,
    print_controlled_build_cycle,
    print_supervised_dev_loop,
)

from project_intelligence import (
    print_codebase_map,
    print_task_dependencies,
    print_test_plan,
    print_patch_risk,
    print_patch_review,
    print_project_memory_index,
    print_workspace_status,
    print_cross_project_task_review,
    print_asymmetric_dev_loop,
)
from workspace_orchestration import (
    print_project_registry,
    print_register_project,
    print_set_active_workspace_project,
    print_project_health,
    print_command_profiles,
    print_workspace_dependency_map,
    print_workspace_task_inbox,
    print_switch_workspace_project,
    print_project_context,
    print_workspace_timeline,
    print_workspace_dev_loop,
)
from workspace_execution import (
    print_workspace_registry_audit,
    print_workspace_repair_suggestions,
    print_project_registration_wizard,
    print_project_boundary_check,
    print_workspace_patch_plan,
    print_workspace_preview_diff,
    print_workspace_apply,
    print_workspace_verify_latest,
    print_guarded_workspace_dev_loop,
)
from patch_drafting import (
    print_patch_draft_request,
    print_draft_patch,
    print_patch_draft_status,
    print_patch_review_notes,
    print_draft_diff,
    print_draft_test_impact,
    print_approve_draft,
    print_reject_draft,
    print_apply_approved_draft,
    print_rollback_approved_draft,
    print_reopen_draft,
    print_human_approved_patch_loop,
    print_draft_quality,
    print_draft_file_targets,
    print_draft_intent_blocks,
    print_draft_conflicts,
    print_draft_verification_bundle,
    print_draft_review_checklist,
    print_approved_draft_execution_report,
    print_review_centered_patch_loop,
)
from release_pipeline import (
    print_code_edit_proposal,
    print_safe_rewrite_preview,
    print_generated_code_patch,
    print_test_suggestions,
    print_inline_review_note,
    print_apply_approved_code_patch,
    print_prepare_release_package,
    print_release_readiness,
    print_human_approved_release_loop,
)
from code_patch_release import (
    print_code_patch_status,
    print_symbol_scan,
    print_rewrite_plan,
    print_rewrite_conflicts,
    print_code_patch_diff_bundle,
    print_apply_code_patch_transaction,
    print_semantic_checks,
    print_release_artifact,
    print_release_audit_trail,
    print_generated_code_release_loop,
)
from ai_patch_assistance import (
    print_task_to_code_patch,
    print_code_context,
    print_patch_prompt,
    print_parse_generated_edits,
    print_edit_consistency,
    print_ai_code_patch_dry_run,
    print_patch_failure_analysis,
    print_patch_learning_notes,
    print_ai_assisted_code_patch_loop,
)
from validated_ai_patch_loop import (
    print_patch_objective_refinement,
    print_code_context_ranking,
    print_patch_safety_envelope,
    print_generated_patch_validation,
    print_patch_simulation,
    print_test_stub_plan,
    print_patch_review_score,
    print_patch_recovery_plan,
    print_validated_ai_code_patch_loop,
)
from approval_release_workflow import (
    print_bind_validated_approval,
    print_ai_patch_review_bundle,
    print_review_bundle_integrity,
    print_approval_ready,
    print_approval_ledger,
    print_apply_validated_ai_patch,
    print_post_apply_review,
    print_package_build_plan,
    print_approval_to_release_loop,
)
from release_packaging import (
    print_release_manifest_integrity,
    print_package_inventory,
    print_package_checksums,
    print_release_notes,
    print_release_handoff_report,
    print_build_release_zip,
    print_verify_release_unzip,
    print_release_pipeline_audit,
    print_verified_release_package_loop,
)
from task_queue import (
    print_task_status,
    print_task_list,
    print_task_detail,
    print_add_task,
    print_set_task_status,
    print_add_task_note,
    print_add_task_action,
    print_block_task,
    print_complete_task,
    print_start_task,
    print_next_task,
    print_queue_from_session,
    list_tasks,
    resolve_task_id,
)
from task_executor import (
    print_task_command_options,
    print_execute_task,
    print_task_execution_history,
)
from task_result_evaluator import (
    print_task_evaluation,
    print_task_evaluations,
    print_saved_task_evaluation,
    print_apply_task_evaluation,
    list_task_evaluations,
    resolve_task_evaluation_id,
)
from guided_work_session import (
    print_guided_work_session,
    print_advance_guided_work_session,
    print_guided_sessions,
    print_saved_guided_session,
    list_guided_sessions,
    resolve_guided_session_id,
)
from autonomous_dev_cycle import (
    print_dev_cycle,
    print_advance_dev_cycle,
    print_dev_cycles,
    print_saved_dev_cycle,
    list_dev_cycles,
    resolve_dev_cycle_id,
)
from dev_loop_runner import (
    print_dev_loop,
    print_dev_loops,
    print_saved_dev_loop,
    list_dev_loops,
    resolve_dev_loop_id,
)
from approval_manager import (
    print_approval_inbox,
    print_approval,
    print_approve,
    print_reject,
    list_approvals,
    resolve_approval_id,
)
from settings_manager import (
    print_settings,
    print_get_setting,
    print_set_setting,
    print_reset_settings,
    print_settings_health,
    get_setting,
)
from diagnostics import (
    print_diagnostics,
    print_diagnostic_reports,
    print_saved_diagnostic_report,
    list_diagnostic_reports,
)
from watch_mode import (
    print_watch_once,
    print_watch_loop,
    print_watch_reports,
    print_saved_watch_report,
    list_watch_reports,
    resolve_watch_report_id,
)
from notification_manager import (
    print_notifications,
    print_notification,
    print_mark_notification_read,
    print_dismiss_notification,
    print_clear_dismissed_notifications,
    list_notifications,
    resolve_notification_id,
)
from chat_action_router import (
    print_chat_action,
    print_execute_chat_action,
    print_chat_actions,
    print_saved_chat_action,
    list_chat_actions,
    resolve_chat_action_id,
)
from dashboard_chat_console import list_dashboard_chat_turns, resolve_dashboard_chat_turn_id
from dashboard import run_dashboard
from api_server import run_api_server
from desktop_shell import print_desktop_status, print_desktop_tray_status, run_desktop_shell
from desktop_setup_helper import (
    print_setup_check,
    print_setup_reports,
    print_saved_setup_report,
    list_setup_reports,
    resolve_setup_report_id,
)
from desktop_onboarding_wizard import (
    print_onboarding_run,
    print_onboarding_runs,
    print_saved_onboarding_run,
    list_onboarding_runs,
    resolve_onboarding_run_id,
)
from inner_loop import run_cycle, run_loop
from memory import load_memories, search_memories
from opinions import load_opinions
from project_manager import (
    add_project,
    add_project_item,
    print_project_status,
    set_active_project,
    get_active_project,
)
from project_indexer import (
    index_project,
    print_project_index_summary,
    print_project_index_search,
)
from self_model import load_self_model


def print_status() -> None:
    self_model = load_self_model()
    memories = load_memories()
    opinions = load_opinions()

    print(f"Name: {self_model.get('name', 'Eidolon')}")
    print(f"Stored memories: {len(memories)}")
    print(f"Opinions: {len(opinions)}")
    print("Active goals:")
    for goal in self_model.get("active_goals", []):
        print(f"- {goal}")
    print()
    print_project_status()


def print_keyword_search(query: str) -> None:
    matches = search_memories(query)
    if not matches:
        print("No keyword matches found.")
        return

    for match in matches:
        print(f"[{match.get('created_at', '?')}] {match.get('type', 'memory')}: {match.get('content', match)}")


def print_semantic_search(query: str) -> None:
    try:
        from vector_memory import search_memory_vectors
    except Exception as error:
        print(f"Semantic search unavailable: {error}")
        return

    matches = search_memory_vectors(query)
    if not matches:
        print("No semantic matches found. Make sure ChromaDB is installed and Ollama is running with nomic-embed-text pulled.")
        return

    for match in matches:
        print(f"[distance={match.get('distance')}] {match.get('content')}")


def rebuild_semantic_memory() -> None:
    try:
        from vector_memory import rebuild_vector_memory
    except Exception as error:
        print(f"Semantic memory rebuild unavailable: {error}")
        return

    memories = load_memories()
    count = rebuild_vector_memory(memories)
    print(f"Rebuilt semantic memory vectors for {count} memories.")


def ai_reviews_enabled() -> bool:
    return bool(get_setting("ai_reviews_enabled", True))


def print_project_tree(path: str = "") -> None:
    print(project_tree_text(relative_path=path))


def print_project_file(path: str) -> None:
    result = read_project_file(path)
    if not result.ok:
        print(f"Could not read {path}: {result.error}")
        return

    print(f"--- {result.path} ---")
    print(result.content)


def print_project_file_search(query: str, path: str = "") -> None:
    matches = search_project_files(query=query, relative_path=path)
    if not matches:
        print("No project file matches found.")
        return

    for match in matches:
        print(f"{match['path']}:{match['line']}: {match['preview']}")


def print_latest_ids() -> None:
    """Prints the newest ids and the aliases that resolve to them."""
    patches = list_patch_proposals()
    proposed_patch = resolve_patch_id("latest-proposed")
    applied_patch = resolve_patch_id("latest-applied")
    rolled_back_patch = resolve_patch_id("latest-rolled-back")
    any_patch = resolve_patch_id("latest")

    runs = list_self_improvement_runs()
    reports = list_test_reports()
    reviews = list_test_reviews()
    maintenance_scans = list_maintenance_scans()
    memory_summaries = list_memory_summaries()
    goals = list_goals()
    session_plans = list_session_plans()
    tasks = list_tasks()
    task_evaluations = list_task_evaluations()
    guided_sessions = list_guided_sessions()
    latest_guided_session = resolve_guided_session_id("latest")
    latest_guided_overview = resolve_guided_session_id("latest-overview")
    latest_guided_dry_run = resolve_guided_session_id("latest-dry-run")
    latest_guided_execute = resolve_guided_session_id("latest-execute")
    latest_guided_evaluate = resolve_guided_session_id("latest-evaluate")
    dev_cycles = list_dev_cycles()
    latest_dev_cycle = resolve_dev_cycle_id("latest")
    latest_dev_review = resolve_dev_cycle_id("latest-review-proposed-patch")
    latest_dev_advance = resolve_dev_cycle_id("latest-advance-task")
    latest_dev_plan = resolve_dev_cycle_id("latest-plan-and-queue")
    dev_loops = list_dev_loops()
    latest_dev_loop = resolve_dev_loop_id("latest")
    latest_dev_loop_approval = resolve_dev_loop_id("latest-approval_required")
    latest_dev_loop_max = resolve_dev_loop_id("latest-max_steps_reached")
    latest_dev_loop_dry = resolve_dev_loop_id("latest-dry_run_complete")
    approvals = list_approvals()
    diagnostic_reports = list_diagnostic_reports()
    latest_diagnostic = diagnostic_reports[0].get("id") if diagnostic_reports else None
    watch_reports = list_watch_reports()
    latest_watch = resolve_watch_report_id("latest")
    latest_watch_attention = resolve_watch_report_id("latest-attention_needed")
    latest_watch_error = resolve_watch_report_id("latest-error")
    latest_watch_healthy = resolve_watch_report_id("latest-healthy")
    notifications = list_notifications(include_dismissed=True)
    latest_notification = resolve_notification_id("latest")
    latest_unread_notification = resolve_notification_id("latest-unread")
    latest_read_notification = resolve_notification_id("latest-read")
    latest_dismissed_notification = resolve_notification_id("latest-dismissed")
    latest_warning_notification = resolve_notification_id("latest-warning")
    latest_critical_notification = resolve_notification_id("latest-critical")
    latest_approval = resolve_approval_id("latest")
    latest_pending_approval = resolve_approval_id("latest-pending")
    latest_approved_approval = resolve_approval_id("latest-approved")
    latest_rejected_approval = resolve_approval_id("latest-rejected")
    latest_task = resolve_task_id("latest")
    latest_open_task = resolve_task_id("latest-open")
    latest_ready_task = resolve_task_id("latest-ready")
    latest_active_task = resolve_task_id("latest-active")
    latest_blocked_task = resolve_task_id("latest-blocked")
    latest_done_task = resolve_task_id("latest-done")
    latest_task_eval = resolve_task_evaluation_id("latest")
    latest_complete_task_eval = resolve_task_evaluation_id("latest-complete")
    latest_block_task_eval = resolve_task_evaluation_id("latest-block")
    latest_retry_task_eval = resolve_task_evaluation_id("latest-retry")
    latest_goal = resolve_goal_id("latest")
    latest_open_goal = resolve_goal_id("latest-open")
    latest_active_goal = resolve_goal_id("latest-active")
    latest_blocked_goal = resolve_goal_id("latest-blocked")
    latest_completed_goal = resolve_goal_id("latest-completed")
    chat_actions = list_chat_actions(include_closed=True)
    dashboard_chat_turns = list_dashboard_chat_turns()
    latest_dashboard_chat = resolve_dashboard_chat_turn_id("latest")
    latest_chat_action = resolve_chat_action_id("latest")
    latest_proposed_chat_action = resolve_chat_action_id("latest-proposed")
    latest_executed_chat_action = resolve_chat_action_id("latest-executed")
    latest_approval_chat_action = resolve_chat_action_id("latest-approval")
    latest_blocked_chat_action = resolve_chat_action_id("latest-blocked")
    setup_reports = list_setup_reports()
    latest_setup_report = resolve_setup_report_id("latest")
    latest_ready_setup_report = resolve_setup_report_id("latest-ready")
    latest_attention_setup_report = resolve_setup_report_id("latest-attention_needed")
    latest_critical_setup_report = resolve_setup_report_id("latest-critical")
    onboarding_runs = list_onboarding_runs()
    latest_onboarding = resolve_onboarding_run_id("latest")
    latest_ready_onboarding = resolve_onboarding_run_id("latest-ready")
    latest_action_onboarding = resolve_onboarding_run_id("latest-needs_action")
    latest_blocked_onboarding = resolve_onboarding_run_id("latest-blocked")

    print("# Latest shortcuts")
    print()
    print("Patch aliases:")
    print(f"  latest: {any_patch or '[none]'}")
    print(f"  latest-proposed: {proposed_patch or '[none]'}")
    print(f"  latest-applied: {applied_patch or '[none]'}")
    print(f"  latest-rolled-back: {rolled_back_patch or '[none]'}")
    print()
    print("Self-improvement aliases:")
    print(f"  latest run: {(runs[0].get('id') if runs else '[none]')}")
    print(f"  latest self-improvement patch: {latest_self_improvement_patch_id() or '[none]'}")
    print()
    print("Test aliases:")
    print(f"  latest report: {(reports[0].get('id') if reports else '[none]')}")
    print(f"  latest review: {(reviews[0].get('id') if reviews else '[none]')}")
    print()
    print("Maintenance aliases:")
    print(f"  latest maintenance scan: {(maintenance_scans[0].get('id') if maintenance_scans else '[none]')}")
    print()
    print("Memory aliases:")
    print(f"  latest memory summary: {(memory_summaries[0].get('id') if memory_summaries else '[none]')}")
    print()
    print("Session aliases:")
    print(f"  latest session plan: {(session_plans[0].get('id') if session_plans else '[none]')}")
    print()
    print("Task aliases:")
    print(f"  latest task: {latest_task or '[none]'}")
    print(f"  latest-open task: {latest_open_task or '[none]'}")
    print(f"  latest-ready task: {latest_ready_task or '[none]'}")
    print(f"  latest-active task: {latest_active_task or '[none]'}")
    print(f"  latest-blocked task: {latest_blocked_task or '[none]'}")
    print(f"  latest-done task: {latest_done_task or '[none]'}")
    print()
    print("Task evaluation aliases:")
    print(f"  latest task evaluation: {latest_task_eval or '[none]'}")
    print(f"  latest-complete task evaluation: {latest_complete_task_eval or '[none]'}")
    print(f"  latest-block task evaluation: {latest_block_task_eval or '[none]'}")
    print(f"  latest-retry task evaluation: {latest_retry_task_eval or '[none]'}")
    print()
    print("Guided work session aliases:")
    print(f"  latest guided session: {latest_guided_session or '[none]'}")
    print(f"  latest-overview guided session: {latest_guided_overview or '[none]'}")
    print(f"  latest-dry-run guided session: {latest_guided_dry_run or '[none]'}")
    print(f"  latest-execute guided session: {latest_guided_execute or '[none]'}")
    print(f"  latest-evaluate guided session: {latest_guided_evaluate or '[none]'}")
    print()
    print("Dev cycle aliases:")
    print(f"  latest dev cycle: {latest_dev_cycle or '[none]'}")
    print(f"  latest-review-proposed-patch dev cycle: {latest_dev_review or '[none]'}")
    print(f"  latest-advance-task dev cycle: {latest_dev_advance or '[none]'}")
    print(f"  latest-plan-and-queue dev cycle: {latest_dev_plan or '[none]'}")
    print()
    print("Dev loop aliases:")
    print(f"  latest dev loop: {latest_dev_loop or '[none]'}")
    print(f"  latest-approval_required dev loop: {latest_dev_loop_approval or '[none]'}")
    print(f"  latest-max_steps_reached dev loop: {latest_dev_loop_max or '[none]'}")
    print(f"  latest-dry_run_complete dev loop: {latest_dev_loop_dry or '[none]'}")
    print()
    print("Diagnostic aliases:")
    print(f"  latest diagnostic report: {latest_diagnostic or '[none]'}")
    print()
    print("Watch report aliases:")
    print(f"  latest watch report: {latest_watch or '[none]'}")
    print(f"  latest-attention_needed watch report: {latest_watch_attention or '[none]'}")
    print(f"  latest-error watch report: {latest_watch_error or '[none]'}")
    print(f"  latest-healthy watch report: {latest_watch_healthy or '[none]'}")
    print()
    print("Notification aliases:")
    print(f"  latest notification: {latest_notification or '[none]'}")
    print(f"  latest-unread notification: {latest_unread_notification or '[none]'}")
    print(f"  latest-read notification: {latest_read_notification or '[none]'}")
    print(f"  latest-dismissed notification: {latest_dismissed_notification or '[none]'}")
    print(f"  latest-warning notification: {latest_warning_notification or '[none]'}")
    print(f"  latest-critical notification: {latest_critical_notification or '[none]'}")
    print()
    print("Approval aliases:")
    print(f"  latest approval: {latest_approval or '[none]'}")
    print(f"  latest-pending approval: {latest_pending_approval or '[none]'}")
    print(f"  latest-approved approval: {latest_approved_approval or '[none]'}")
    print(f"  latest-rejected approval: {latest_rejected_approval or '[none]'}")
    print()
    print("Dashboard chat aliases:")
    print(f"  latest dashboard chat: {latest_dashboard_chat or '[none]'}")
    print()
    print("Chat action aliases:")
    print(f"  latest chat action: {latest_chat_action or '[none]'}")
    print(f"  latest-proposed chat action: {latest_proposed_chat_action or '[none]'}")
    print(f"  latest-executed chat action: {latest_executed_chat_action or '[none]'}")
    print(f"  latest-approval chat action: {latest_approval_chat_action or '[none]'}")
    print(f"  latest-blocked chat action: {latest_blocked_chat_action or '[none]'}")
    print()
    print("Setup aliases:")
    print(f"  latest setup report: {latest_setup_report or '[none]'}")
    print(f"  latest-ready setup report: {latest_ready_setup_report or '[none]'}")
    print(f"  latest-attention_needed setup report: {latest_attention_setup_report or '[none]'}")
    print(f"  latest-critical setup report: {latest_critical_setup_report or '[none]'}")
    print()
    print("Onboarding aliases:")
    print(f"  latest onboarding run: {latest_onboarding or '[none]'}")
    print(f"  latest-ready onboarding run: {latest_ready_onboarding or '[none]'}")
    print(f"  latest-needs_action onboarding run: {latest_action_onboarding or '[none]'}")
    print(f"  latest-blocked onboarding run: {latest_blocked_onboarding or '[none]'}")
    print()
    print("Goal aliases:")
    print(f"  latest goal: {latest_goal or '[none]'}")
    print(f"  latest-open goal: {latest_open_goal or '[none]'}")
    print(f"  latest-active goal: {latest_active_goal or '[none]'}")
    print(f"  latest-blocked goal: {latest_blocked_goal or '[none]'}")
    print(f"  latest-completed goal: {latest_completed_goal or '[none]'}")
    print()
    print("Common no-copy commands:")
    print("  python conscious_agent/main.py --chat-action \"run diagnostics\"")
    print("  python conscious_agent/main.py --show-chat-action latest")
    print("  python conscious_agent/main.py --execute-chat-action latest --dry-run")
    print("  python conscious_agent/main.py --show-patch latest")
    print("  python conscious_agent/main.py --apply-patch latest --dry-run")
    print("  python conscious_agent/main.py --rollback-patch latest --dry-run")
    print("  python conscious_agent/main.py --show-self-improvement latest")
    print("  python conscious_agent/main.py --self-improve-apply latest --dry-run")
    print("  python conscious_agent/main.py --show-test-report latest")
    print("  python conscious_agent/main.py --review-test-report latest")
    print("  python conscious_agent/main.py --show-test-review latest")
    print("  python conscious_agent/main.py --show-maintenance-scan latest")
    print("  python conscious_agent/main.py --show-memory-summary latest")
    print("  python conscious_agent/main.py --show-session-plan latest")
    print("  python conscious_agent/main.py --queue-from-session latest")
    print("  python conscious_agent/main.py --next-task")
    print("  python conscious_agent/main.py --show-task latest-ready")
    print("  python conscious_agent/main.py --start-task latest-ready")
    print("  python conscious_agent/main.py --complete-task latest-active")
    print("  python conscious_agent/main.py --evaluate-task latest")
    print("  python conscious_agent/main.py --show-task-evaluation latest")
    print("  python conscious_agent/main.py --apply-task-evaluation latest")
    print("  python conscious_agent/main.py --guided-work-session latest-ready")
    print("  python conscious_agent/main.py --advance-work-session latest-ready")
    print("  python conscious_agent/main.py --show-guided-session latest")
    print("  python conscious_agent/main.py --dev-cycle")
    print("  python conscious_agent/main.py --advance-dev-cycle --dry-run")
    print("  python conscious_agent/main.py --show-dev-cycle latest")
    print("  python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop")
    print("  python conscious_agent/main.py --dev-loop")
    print("  python conscious_agent/main.py --show-dev-loop latest")
    print("  python conscious_agent/main.py --settings")
    print("  python conscious_agent/main.py --settings-health")
    print("  python conscious_agent/main.py --work-cycle --dry-run")
    print("  python conscious_agent/main.py --work-cycle --work-cycle-steps 3")
    print("  python conscious_agent/main.py --show-work-cycle latest")
    print("  python conscious_agent/main.py --diagnostics")
    print("  python conscious_agent/main.py --dashboard")
    print("  python conscious_agent/main.py --diagnostics --diagnostics-full")
    print("  python conscious_agent/main.py --show-diagnostic-report latest")
    print("  python conscious_agent/main.py --watch-once --no-ai-watch")
    print("  python conscious_agent/main.py --watch-loop --watch-cycles 3 --no-ai-watch")
    print("  python conscious_agent/main.py --show-watch-report latest")
    print("  python conscious_agent/main.py --notifications")
    print("  python conscious_agent/main.py --show-notification latest-unread")
    print("  python conscious_agent/main.py --mark-notification-read latest-unread")
    print("  python conscious_agent/main.py --dismiss-notification latest-unread")
    print("  python conscious_agent/main.py --approval-inbox")
    print("  python conscious_agent/main.py --show-approval latest-pending")
    print("  python conscious_agent/main.py --approve latest-pending --dry-run")
    print("  python conscious_agent/main.py --reject latest-pending --approval-note \"Reason here\"")
    print("  python conscious_agent/main.py --show-goal latest-open")
    print("  python conscious_agent/main.py --complete-goal latest-active")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eidolon autonomous inner-thought prototype")
    parser.add_argument("--once", action="store_true", help="Run one inner-thought cycle")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--search", type=str, help="Search memories by keyword")
    parser.add_argument("--semantic-search", type=str, help="Search memories by meaning")
    parser.add_argument("--rebuild-semantic-memory", action="store_true", help="Vectorize existing JSON memories")
    parser.add_argument("--chat", action="store_true", help="Start terminal chat mode")
    parser.add_argument(
        "--work-queue",
        nargs=argparse.REMAINDER,
        help="Legacy alias: manage task-backed tasks through the old work-queue CLI.",
    )
    parser.add_argument(
        "--task-work",
        nargs=argparse.REMAINDER,
        help="Manage canonical task-backed tasks through the Tasks / Work CLI.",
    )
    parser.add_argument("--execute-task-work", action="store_true", help="Execute the next safe planned/active task through the task work executor")
    parser.add_argument("--execute-task-work-id", type=str, help="Execute one specific task through the task work executor")
    parser.add_argument("--execute-task-work-project", type=str, default="", help="Optional project filter for --execute-task-work")
    parser.add_argument("--execute-work", action="store_true", help="Legacy alias: execute the next safe task-backed task")
    parser.add_argument("--execute-work-id", type=str, help="Legacy alias: execute one specific task-backed task by id")
    parser.add_argument("--execute-work-project", type=str, default="", help="Legacy alias project filter for --execute-work")
    parser.add_argument("--approve-task-work-execution", action="store_true", help="Allow approval-required task work to execute; use carefully")
    parser.add_argument("--approve-work-execution", action="store_true", help="Legacy alias: allow approval-required task-backed tasks to execute; use carefully")
    parser.add_argument("--no-ai-task-work-executor", action="store_true", help="Disable local AI during task work execution")
    parser.add_argument("--no-ai-work-executor", action="store_true", help="Legacy alias: disable local AI during task work execution")
    parser.add_argument("--task-work-executor-full", action="store_true", help="Show full task work executor output")
    parser.add_argument("--work-executor-full", action="store_true", help="Legacy alias: show full task work executor output")
    parser.add_argument("--request-task-approval", type=str, help="Create an approval request for executing one approval-gated task")
    parser.add_argument("--request-next-task-approval", action="store_true", help="Create an approval request for the next approval-gated task")
    parser.add_argument("--task-approval-project", type=str, default="", help="Optional project filter for --request-next-task-approval")
    parser.add_argument("--task-approval-reason", type=str, default="", help="Reason to store on a task approval request")
    parser.add_argument("--force-task-approval", action="store_true", help="Create a task approval even if the task is not currently risk-gated")
    parser.add_argument("--show-task-approvals", type=str, help="Show approval requests linked to a task")
    parser.add_argument("--task-approval-full", action="store_true", help="Show full task approval request details")
    parser.add_argument("--task-recovery-summary", action="store_true", help="Show recoverable blocked/failed task summary")
    parser.add_argument("--list-task-recoveries", action="store_true", help="List recoverable blocked/failed tasks and suggested recovery actions")
    parser.add_argument("--show-task-recovery", type=str, help="Show recovery plan for a task by id or alias")
    parser.add_argument("--mark-task-ready-for-retry", type=str, help="Clear failed/blocked work markers and mark a task planned for retry")
    parser.add_argument("--retry-task-work", type=str, help="Retry a recoverable task through the task work executor; use --dry-run first")
    parser.add_argument("--task-recovery-project", type=str, default="", help="Optional project filter for task recovery listing")
    parser.add_argument("--task-recovery-note", type=str, default="", help="Optional note for --mark-task-ready-for-retry")
    parser.add_argument("--task-recovery-full", action="store_true", help="Show full task recovery details")
    parser.add_argument("--queue-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Legacy alias: create a task-backed patch-generation item for a file")
    parser.add_argument("--queue-task-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Create a task-backed item that will generate a patch proposal for a file")
    parser.add_argument("--queue-patch-project", type=str, default="eidolon", help="Project id for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-priority", type=int, default=7, help="Priority 1-10 for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-risk", type=str, default="low", choices=["low", "medium", "high"], help="Risk level for --queue-patch / --queue-task-patch")
    parser.add_argument("--queue-patch-requires-approval", action="store_true", help="Force the queued patch task to require approval")
    parser.add_argument("--suggest-patch-for-work", type=str, help="Legacy alias: generate and link a patch proposal from a task-backed task")
    parser.add_argument("--suggest-patch-for-task", type=str, help="Generate and link a patch proposal from a task")
    parser.add_argument("--create-patch-followups", type=str, help="Legacy alias: create review/apply/test follow-up tasks for a patch id")
    parser.add_argument("--create-patch-task-followups", type=str, help="Create review/apply/test follow-up tasks for a patch id")
    parser.add_argument("--patch-followup-project", type=str, default="eidolon", help="Project id for --create-patch-followups")
    parser.add_argument("--work-cycle", action="store_true", help="Run one supervised autonomous work cycle over task-backed tasks")
    parser.add_argument("--work-cycle-project", type=str, default="eidolon", help="Project id for --work-cycle")
    parser.add_argument("--work-cycle-steps", type=int, default=1, help="Maximum tasks to advance during --work-cycle, capped at 10")
    parser.add_argument("--approve-work-cycle-actions", action="store_true", help="Allow approval-required tasks during --work-cycle; use carefully")
    parser.add_argument("--no-ai-work-cycle", action="store_true", help="Disable local AI during --work-cycle")
    parser.add_argument("--no-work-cycle-seed", action="store_true", help="Do not create seed tasks when the queue is empty")
    parser.add_argument("--no-work-cycle-followups", action="store_true", help="Do not auto-create review/apply/test follow-ups for proposed patches")
    parser.add_argument("--no-work-cycle-approval-requests", action="store_true", help="Do not auto-create approval requests for approval-required tasks during --work-cycle")
    parser.add_argument("--work-cycle-auto-retry-recovery", action="store_true", help="Allow --work-cycle to mark recovery-needed tasks ready for retry; default only reports recovery plans")
    parser.add_argument("--work-cycle-full", action="store_true", help="Show full supervised work cycle details")
    parser.add_argument("--list-work-cycles", action="store_true", help="List saved supervised work cycle records")
    parser.add_argument("--show-work-cycle", nargs="?", const="latest", help="Show a saved supervised work cycle by id or alias")
    parser.add_argument("--stable-loop-preflight", action="store_true", help="Preview stable supervised loop health and next lifecycle decision")
    parser.add_argument("--stable-loop", action="store_true", help="Run the v6.9 stable supervised loop; preview-only unless --stable-loop-live is used")
    parser.add_argument("--stable-loop-project", type=str, default="eidolon", help="Project id for --stable-loop")
    parser.add_argument("--stable-loop-steps", type=int, default=1, help="Maximum stable loop steps, capped at 5")
    parser.add_argument("--stable-loop-live", action="store_true", help="Allow the stable loop to run a live cycle after its dry-run preview")
    parser.add_argument("--approve-stable-loop-actions", action="store_true", help="Allow approval-required task work during a live stable loop; use carefully")
    parser.add_argument("--no-ai-stable-loop", action="store_true", help="Disable local AI during stable loop preview/live cycle")
    parser.add_argument("--no-stable-loop-seed", action="store_true", help="Do not create seed tasks when stable loop finds an empty queue")
    parser.add_argument("--no-stable-loop-followups", action="store_true", help="Do not auto-create patch follow-up tasks during stable loop")
    parser.add_argument("--no-stable-loop-approval-requests", action="store_true", help="Do not auto-create task approval requests during stable loop")
    parser.add_argument("--stable-loop-auto-retry-recovery", action="store_true", help="Allow live stable loop to mark recovery-needed tasks ready for retry")
    parser.add_argument("--stable-loop-full", action="store_true", help="Show full stable loop details")
    parser.add_argument("--stable-loop-guardrails", action="store_true", help="Show closure-aware guardrails for stable-loop live advancement")
    parser.add_argument("--stable-loop-bypass-closure-guardrails", action="store_true", help="Explicitly bypass unresolved follow-up guardrails for a live stable-loop run")
    parser.add_argument("--stabilization-checkpoint", action="store_true", help="Run the v8.0 read-only stabilization checkpoint across CLI/API/dashboard/task/stable-loop surfaces")
    parser.add_argument("--stabilization-full", action="store_true", help="Include every stabilization checkpoint item and raw report details")
    parser.add_argument("--stabilization-json", action="store_true", help="Print the stabilization checkpoint report as JSON")
    parser.add_argument("--doctor", action="store_true", help="Run the v7.2 one-command doctor report")
    parser.add_argument("--doctor-full", action="store_true", help="Include raw JSON/details for doctor and operational readiness reports")
    parser.add_argument("--readiness-json", action="store_true", help="Print new operational readiness reports as JSON")
    parser.add_argument("--repair-suggestions", action="store_true", help="Show v7.3 self-repair suggestions based on current diagnostics")
    parser.add_argument("--patch-integrity", action="store_true", help="Show v7.4 patch metadata and rollback integrity report")
    parser.add_argument("--project-snapshot", action="store_true", help="Show v7.5 project state snapshot")
    parser.add_argument("--task-review", action="store_true", help="Show v7.6 task queue risk/lifecycle review")
    parser.add_argument("--recovery-drill", action="store_true", help="Run v7.7 read-only recovery drill scenarios")
    parser.add_argument("--stable-loop-confidence", action="store_true", help="Show v7.8 stable-loop confidence score")
    parser.add_argument("--hardening-report", action="store_true", help="Show v7.9 pre-v8 hardening report")
    parser.add_argument("--controlled-self-build", action="store_true", help="Run v8.0 controlled self-build preview unless live approval flags are supplied")
    parser.add_argument("--controlled-self-build-live", action="store_true", help="Allow controlled self-build/supervised loop commands to attempt live work after doctor/guardrail gates")
    parser.add_argument("--approve-controlled-self-build", action="store_true", help="Explicit operator approval required for live controlled self-build, apply, or rollback actions")
    parser.add_argument("--controlled-self-build-steps", type=int, default=1, help="Bounded step count for controlled self-build, capped internally")
    parser.add_argument("--select-task", action="store_true", help="Run v8.1 controlled self-build task selection")
    parser.add_argument("--plan-patch", action="store_true", help="Run v8.2 controlled patch planner and save data/patch_workspace/current_plan.json")
    parser.add_argument("--patch-workspace-status", action="store_true", help="Show v8.3 controlled patch workspace status")
    parser.add_argument("--stage-patch", action="store_true", help="Run v8.3 patch staging into data/patch_workspace without touching source files")
    parser.add_argument("--preview-diff", action="store_true", help="Run v8.4 staged file diff preview")
    parser.add_argument("--apply-staged-patch", action="store_true", help="Run v8.5 apply staged patch; writes only with --approve-controlled-self-build")
    parser.add_argument("--verify-latest-patch", action="store_true", help="Run v8.6 verification for the latest controlled patch/apply report")
    parser.add_argument("--rollback-latest-patch", action="store_true", help="Run v8.7 rollback for the latest controlled patch; writes only with --approve-controlled-self-build")
    parser.add_argument("--readme-gate", action="store_true", help="Run v8.8 README enforcement gate")
    parser.add_argument("--controlled-self-build-cycle", action="store_true", help="Run v8.9 full controlled build cycle; preview by default")
    parser.add_argument("--supervised-dev-loop", action="store_true", help="Run v9.0 one-cycle supervised autonomous development loop; preview by default")
    parser.add_argument("--codebase-map", action="store_true", help="Run v9.1 codebase map")
    parser.add_argument("--task-dependencies", action="store_true", help="Run v9.2 dependency-aware task planning")
    parser.add_argument("--test-plan", action="store_true", help="Run v9.3 test planner")
    parser.add_argument("--patch-risk", action="store_true", help="Run v9.4 patch risk analyzer")
    parser.add_argument("--patch-review", action="store_true", help="Run v9.5 patch review report")
    parser.add_argument("--project-memory-index", action="store_true", help="Run v9.7 project memory index")
    parser.add_argument("--workspace-status", action="store_true", help="Run v9.8 multi-project workspace status")
    parser.add_argument("--cross-project-task-review", action="store_true", help="Run v9.9 cross-project task review")
    parser.add_argument("--asymmetric-dev-loop", action="store_true", help="Run v10.0 asymmetric multi-project dev loop preview")
    parser.add_argument("--project-registry", action="store_true", help="Run v10.1 workspace project registry report")
    parser.add_argument("--register-project", help="Register or update a workspace project by name")
    parser.add_argument("--workspace-project-id", help="Workspace project id for registration/context commands")
    parser.add_argument("--workspace-project-root", help="Workspace project root; use . to derive from ROOT_DIR")
    parser.add_argument("--workspace-project-version", default="unknown", help="Workspace project version metadata")
    parser.add_argument("--workspace-project-language", default="unknown", help="Workspace project language metadata")
    parser.add_argument("--workspace-project-framework", default="unknown", help="Workspace project framework/type metadata")
    parser.add_argument("--workspace-project-readme", default="README_NEXT_STEPS.md", help="Workspace project README path")
    parser.add_argument("--workspace-project-test-command", action="append", default=[], help="Project-specific test command; may be provided multiple times")
    parser.add_argument("--workspace-command-profile", default="default_python", help="Project safe command profile id")
    parser.add_argument("--set-active-workspace-project", help="Set the active workspace project id")
    parser.add_argument("--project-health", action="store_true", help="Run v10.2 per-project health check")
    parser.add_argument("--project-health-all", action="store_true", help="Run v10.2 health check across all registered projects")
    parser.add_argument("--command-profiles", action="store_true", help="Run v10.3 project command profile report and seed defaults")
    parser.add_argument("--workspace-dependency-map", action="store_true", help="Run v10.4 cross-project dependency map")
    parser.add_argument("--workspace-task-inbox", action="store_true", help="Run v10.5 multi-project task inbox")
    parser.add_argument("--switch-project", help="Safely switch active workspace project, blocked by dirty patch workspace unless forced")
    parser.add_argument("--force-switch-project", action="store_true", help="Force workspace project switch despite patch workspace state")
    parser.add_argument("--project-context", action="store_true", help="Run v10.7 project context bundle")
    parser.add_argument("--workspace-timeline", action="store_true", help="Run v10.8 workspace timeline")
    parser.add_argument("--workspace-dev-loop", action="store_true", help="Run v11.0 workspace-orchestrated development loop preview")
    parser.add_argument("--workspace-registry-audit", action="store_true", help="Run v11.1 workspace registry persistence audit")
    parser.add_argument("--workspace-repair-suggestions", action="store_true", help="Run v11.2 workspace repair suggestions")
    parser.add_argument("--project-registration-wizard", nargs="?", const="Workspace Project", help="Run v11.3 project registration wizard preview")
    parser.add_argument("--project-boundary-check", action="store_true", help="Run v11.4 project boundary guard")
    parser.add_argument("--workspace-patch-plan", action="store_true", help="Run v11.5 workspace patch plan")
    parser.add_argument("--workspace-preview-diff", action="store_true", help="Run v11.6 workspace diff preview")
    parser.add_argument("--workspace-apply", action="store_true", help="Run v11.7/v11.8 workspace apply; dry-run unless --approve-controlled-self-build is provided")
    parser.add_argument("--workspace-verify-latest", action="store_true", help="Run v11.9 workspace verification pipeline")
    parser.add_argument("--guarded-workspace-dev-loop", action="store_true", help="Run v12.0 guarded workspace development loop; dry-run unless approved")
    parser.add_argument("--patch-draft-request", action="store_true", help="Run v12.1 patch draft request format and save data/patch_drafts/draft_request.json")
    parser.add_argument("--draft-patch", action="store_true", help="Run v12.2 AI patch drafting interface without applying source edits")
    parser.add_argument("--patch-draft-status", action="store_true", help="Run v12.3 patch draft workspace status")
    parser.add_argument("--patch-review-notes", action="store_true", help="Run v12.4 human patch review notes")
    parser.add_argument("--patch-review-note", help="Review note text to attach to the current patch draft")
    parser.add_argument("--draft-diff", action="store_true", help="Run v12.5 draft diff generator")
    parser.add_argument("--draft-test-impact", action="store_true", help="Run v12.6 draft test impact planner")
    parser.add_argument("--approve-draft", action="store_true", help="Run v12.7 approval gate and approve the current draft for one apply if gates pass")
    parser.add_argument("--reject-draft", action="store_true", help="Reject the current patch draft")
    parser.add_argument("--apply-approved-draft", action="store_true", help="Run v12.8 approved draft apply; use --dry-run to preview without writing")
    parser.add_argument("--rollback-approved-draft", action="store_true", help="Run v12.9 approved draft rollback; writes only with --approve-controlled-self-build")
    parser.add_argument("--reopen-draft", action="store_true", help="Run v12.9 reopen draft and clear approval state")
    parser.add_argument("--human-approved-patch-loop", action="store_true", help="Run v13.0 human-approved autonomous patch loop; stops unless a draft is already approved")
    parser.add_argument("--draft-quality", action="store_true", help="Run v13.1 draft quality scoring")
    parser.add_argument("--draft-file-targets", action="store_true", help="Run v13.2 draft file target resolver")
    parser.add_argument("--draft-intent-blocks", action="store_true", help="Run v13.3 draft change intent blocks")
    parser.add_argument("--draft-conflicts", action="store_true", help="Run v13.4 draft conflict detector")
    parser.add_argument("--draft-verification-bundle", action="store_true", help="Run v13.7 draft verification bundle")
    parser.add_argument("--draft-review-checklist", action="store_true", help="Run v13.8 human review checklist")
    parser.add_argument("--approved-draft-execution-report", action="store_true", help="Run v13.9 approved draft execution report")
    parser.add_argument("--review-centered-patch-loop", action="store_true", help="Run v14.0 review-centered patch loop; stops unless approval exists and apply is approved")
    parser.add_argument("--code-edit-proposal", action="store_true", help="Run v14.1 real code edit proposal format")
    parser.add_argument("--safe-rewrite-preview", action="store_true", help="Run v14.2 safe file rewrite preview with hash checks")
    parser.add_argument("--generate-code-patch", action="store_true", help="Run v14.3 generated code patch artifact builder")
    parser.add_argument("--test-suggestions", action="store_true", help="Run v14.4 unit/manual test suggestion generator")
    parser.add_argument("--inline-review-note", action="store_true", help="Run v14.6 inline patch review note capture")
    parser.add_argument("--inline-review-file", help="File path for --inline-review-note")
    parser.add_argument("--inline-review-intent", help="Intent block id/title for --inline-review-note")
    parser.add_argument("--apply-approved-code-patch", action="store_true", help="Run v14.7 approved generated code patch apply; dry-run unless approved")
    parser.add_argument("--prepare-release-package", action="store_true", help="Run v14.8 release package metadata preparation")
    parser.add_argument("--release-package-name", default="Eidolon_v20_0.zip", help="Package name for release preparation metadata")
    parser.add_argument("--release-readiness", action="store_true", help="Run v14.9 release readiness gate")
    parser.add_argument("--human-approved-release-loop", action="store_true", help="Run v15.0 human-approved release loop; stops after one approval/apply decision")
    parser.add_argument("--code-patch-status", action="store_true", help="Run v15.1 generated-code patch workspace status")
    parser.add_argument("--symbol-scan", action="store_true", help="Run v15.2 symbol-aware target file scanner")
    parser.add_argument("--rewrite-plan", action="store_true", help="Run v15.3 targeted rewrite planner")
    parser.add_argument("--rewrite-conflicts", action="store_true", help="Run v15.4 rewrite conflict detector")
    parser.add_argument("--code-patch-diff-bundle", action="store_true", help="Run v15.5 generated code patch diff bundle")
    parser.add_argument("--apply-code-patch-transaction", action="store_true", help="Run v15.6 guarded code patch apply transaction; dry-run unless approved")
    parser.add_argument("--semantic-checks", action="store_true", help="Run v15.7 post-apply semantic checks")
    parser.add_argument("--release-artifact", action="store_true", help="Run v15.8 release artifact manifest builder")
    parser.add_argument("--release-audit-trail", action="store_true", help="Run v15.9 release audit trail")
    parser.add_argument("--generated-code-release-loop", action="store_true", help="Run v16.0 generated code patch release loop; one bounded dry-run/apply then stop")
    parser.add_argument("--task-to-code-patch", action="store_true", help="Run v16.1 task-to-code patch translator")
    parser.add_argument("--code-context", action="store_true", help="Run v16.2 focused code context extractor")
    parser.add_argument("--patch-prompt", action="store_true", help="Run v16.3 structured patch prompt builder")
    parser.add_argument("--parse-generated-edits", action="store_true", help="Run v16.4 generated edit parser")
    parser.add_argument("--edit-consistency", action="store_true", help="Run v16.5 multi-edit consistency checker")
    parser.add_argument("--ai-code-patch-dry-run", action="store_true", help="Run v16.6 AI-assisted patch dry-run without source writes")
    parser.add_argument("--patch-failure-analysis", action="store_true", help="Run v16.8 generated patch failure classifier")
    parser.add_argument("--patch-learning-notes", action="store_true", help="Run v16.9 generated patch learning notes")
    parser.add_argument("--ai-assisted-code-patch-loop", action="store_true", help="Run v17.0 AI-assisted human-approved code patch loop; bounded and approval-gated")
    parser.add_argument("--refine-patch-objective", action="store_true", help="Run v17.1 patch objective refinement")
    parser.add_argument("--rank-code-context", action="store_true", help="Run v17.2 code context ranking")
    parser.add_argument("--patch-safety-envelope", action="store_true", help="Run v17.3 prompt safety envelope")
    parser.add_argument("--validate-generated-patch", action="store_true", help="Run v17.4 generated patch validator")
    parser.add_argument("--patch-simulation", action="store_true", help="Run v17.5 patch simulation without source writes")
    parser.add_argument("--test-stub-plan", action="store_true", help="Run v17.6 test stub planner")
    parser.add_argument("--patch-review-score", action="store_true", help="Run v17.7 patch review scoring")
    parser.add_argument("--patch-recovery-plan", action="store_true", help="Run v17.9 patch failure recovery plan")
    parser.add_argument("--validated-ai-code-patch-loop", action="store_true", help="Run v18.0 validated AI code patch loop; validates, simulates, scores, and stops for approval")
    parser.add_argument("--ai-patch-review-bundle", action="store_true", help="Run v18.1 AI patch review bundle")
    parser.add_argument("--ai-patch-review-integrity", action="store_true", help="Run v18.2 review bundle integrity check")
    parser.add_argument("--approval-ready", action="store_true", help="Run v18.3 approval-ready gate")
    parser.add_argument("--approval-ledger", action="store_true", help="Run v18.5 human approval ledger")
    parser.add_argument("--apply-validated-ai-patch", action="store_true", help="Run v18.6 validated AI patch apply; dry-run unless approved")
    parser.add_argument("--post-apply-review", action="store_true", help="Run v18.7 post-apply review comparison")
    parser.add_argument("--package-build-plan", action="store_true", help="Run v18.9 package build plan")
    parser.add_argument("--approval-to-release-loop", action="store_true", help="Run v19.0 approval-to-release loop")
    parser.add_argument("--bind-validated-approval", action="store_true", help="Bind the current approved draft to the saved validated AI patch manifest before real validated apply")
    parser.add_argument("--refresh-ai-patch-review-bundle", action="store_true", help="Refresh and save the authoritative validated AI patch review bundle/manifest")
    parser.add_argument("--release-manifest-integrity", action="store_true", help="Run v19.1 release manifest integrity check")
    parser.add_argument("--package-inventory", action="store_true", help="Run v19.2 package file inventory")
    parser.add_argument("--package-checksums", action="store_true", help="Run v19.3 package checksum builder")
    parser.add_argument("--release-notes", action="store_true", help="Run v19.4 release notes generator")
    parser.add_argument("--release-handoff-report", action="store_true", help="Run v19.5 release handoff report")
    parser.add_argument("--build-release-zip", action="store_true", help="Run v19.6 guarded release zip builder; dry-run unless --approve-controlled-self-build is provided")
    parser.add_argument("--verify-release-unzip", action="store_true", help="Run v19.7 install/unzip verification for the latest release zip")
    parser.add_argument("--release-pipeline-audit", action="store_true", help="Run v19.9 release pipeline audit")
    parser.add_argument("--verified-release-package-loop", action="store_true", help="Run v20.0 verified release package loop")
    parser.add_argument("--patch-draft-task", help="Patch draft task title/summary")
    parser.add_argument("--patch-draft-intent", help="Patch draft intent/why this patch exists")
    parser.add_argument("--patch-draft-target-version", default="20.0", help="Target version for a patch draft request")
    parser.add_argument("--patch-draft-risk-limit", default="medium", help="Maximum accepted draft risk for approval")
    parser.add_argument("--list-stable-loops", action="store_true", help="List saved stable supervised loop records")
    parser.add_argument("--show-stable-loop", nargs="?", const="latest", help="Show a saved stable supervised loop by id or alias")
    parser.add_argument("--stable-loop-review-summary", action="store_true", help="Summarize stable loop operator review states")
    parser.add_argument("--show-stable-loop-review", nargs="?", const="latest", help="Show review metadata for a saved stable loop")
    parser.add_argument("--mark-stable-loop-reviewed", type=str, help="Mark a stable loop reviewed")
    parser.add_argument("--approve-stable-loop-live", type=str, help="Mark a preview stable loop approved for explicit live run")
    parser.add_argument("--reject-stable-loop", type=str, help="Reject a stable loop review record")
    parser.add_argument("--run-approved-stable-loop-live", type=str, help="Run a live stable loop from a preview already approved for live")
    parser.add_argument("--stable-loop-review-note", type=str, default="", help="Optional note for stable loop review actions")
    parser.add_argument("--stable-loop-review-full", action="store_true", help="Show full stable loop review details")
    parser.add_argument("--list-stable-loop-reviews", nargs="?", const="all", help="List stable loop review/history records by filter")
    parser.add_argument("--stable-loop-review-filter", type=str, default="all", help="Review/history filter for stable loop review listings and cleanup")
    parser.add_argument("--include-archived-stable-loops", action="store_true", help="Include archived stable loop history records in listings")
    parser.add_argument("--archive-stable-loop", type=str, help="Archive one stable loop history record without deleting it")
    parser.add_argument("--restore-stable-loop", type=str, help="Restore one archived stable loop history record")
    parser.add_argument("--cleanup-stable-loop-history", action="store_true", help="Archive old stable loop history records matching a filter; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--cleanup-stable-loop-limit", type=int, default=25, help="Maximum stable loop records to archive during cleanup")
    parser.add_argument("--cleanup-stable-loop-confirm", action="store_true", help="Actually archive cleanup candidates instead of previewing them")
    parser.add_argument("--cleanup-stable-loop-exclude-live", action="store_true", help="Do not archive live stable-loop records during cleanup")
    parser.add_argument("--show-stable-loop-audit", nargs="?", const="latest", help="Show audit, rollback, and verification notes for a stable-loop record")
    parser.add_argument("--refresh-stable-loop-audit", nargs="?", const="latest", help="Refresh and save the audit block for a stable-loop record")
    parser.add_argument("--stable-loop-audit-full", action="store_true", help="Include raw audit JSON when showing stable-loop audit notes")
    parser.add_argument("--show-stable-loop-operator-notes", nargs="?", const="latest", help="Show post-run checklist, operator notes, and final decision for a stable-loop record")
    parser.add_argument("--add-stable-loop-operator-note", type=str, help="Add an operator note to a stable-loop record")
    parser.add_argument("--complete-stable-loop-check", nargs=2, metavar=("LOOP_ID", "CHECK_ID"), help="Mark one stable-loop post-run checklist item done")
    parser.add_argument("--skip-stable-loop-check", nargs=2, metavar=("LOOP_ID", "CHECK_ID"), help="Mark one stable-loop post-run checklist item skipped")
    parser.add_argument("--set-stable-loop-final-decision", type=str, help="Set final operator decision for a stable-loop record")
    parser.add_argument("--stable-loop-final-decision", type=str, default="undecided", choices=["undecided", "keep", "fix_forward", "rollback", "needs_review"], help="Final stable-loop decision value")
    parser.add_argument("--stable-loop-operator-note", type=str, default="", help="Operator note for stable-loop checklist or final decision actions")
    parser.add_argument("--stable-loop-operator-full", action="store_true", help="Include raw operator-note JSON when showing post-run checklist details")
    parser.add_argument("--stable-loop-decision-report", nargs="?", const="all", help="Show stable-loop final-decision report by decision filter")
    parser.add_argument("--list-stable-loop-decisions", nargs="?", const="all", help="List stable-loop records by final-decision filter")
    parser.add_argument("--stable-loop-decision-filter", type=str, default="all", help="Final-decision filter for stable-loop decision reporting and cleanup")
    parser.add_argument("--include-live-stable-loop-decisions", action="store_true", help="Include live stable-loop records in decision reports and cleanup; enabled by default for cleanup")
    parser.add_argument("--cleanup-stable-loop-decisions", action="store_true", help="Archive stable-loop history by final decision; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--stable-loop-decision-full", action="store_true", help="Include raw decision report/cleanup JSON")
    parser.add_argument("--stable-loop-followup-summary", nargs="?", const="action_required", help="Summarize decision-aware stable-loop follow-up task needs by final-decision filter")
    parser.add_argument("--create-stable-loop-followups", type=str, help="Create or preview follow-up tasks for one stable-loop final decision")
    parser.add_argument("--create-stable-loop-decision-followups", nargs="?", const="action_required", help="Create or preview follow-up tasks for stable-loop records matching a final-decision filter")
    parser.add_argument("--stable-loop-followup-force", action="store_true", help="Allow stable-loop follow-up task creation even when the final decision is not normally action-required")
    parser.add_argument("--stable-loop-followup-full", action="store_true", help="Include raw stable-loop follow-up task JSON output")
    parser.add_argument("--stable-loop-followup-lifecycle-summary", nargs="?", const="all", help="Summarize stable-loop decision follow-up tasks and lifecycle resolution state")
    parser.add_argument("--show-task-stable-loop-followup", type=str, help="Show stable-loop decision follow-up metadata for a task")
    parser.add_argument("--resolve-stable-loop-followups", type=str, help="Mark a stable-loop decision follow-up chain resolved once linked follow-up tasks are done")
    parser.add_argument("--resolve-task-stable-loop-followup", type=str, help="Resolve the stable-loop decision follow-up chain linked to a completed follow-up task")
    parser.add_argument("--archive-resolved-stable-loop", action="store_true", help="Archive the stable-loop record after resolving its follow-up task chain")
    parser.add_argument("--force-stable-loop-followup-resolution", action="store_true", help="Allow resolving stable-loop follow-ups even when linked tasks are still open")
    parser.add_argument("--stable-loop-followup-note", type=str, default="", help="Optional note for stable-loop follow-up lifecycle resolution")
    parser.add_argument("--stable-loop-followup-completion-report", nargs="?", const="all", help="Show stable-loop follow-up completion report by closure filter")
    parser.add_argument("--list-stable-loop-followup-completions", nargs="?", const="all", help="List stable-loop follow-up completion rows by closure filter")
    parser.add_argument("--stable-loop-followup-completion-filter", type=str, default="all", help="Filter for stable-loop follow-up completion reporting and cleanup")
    parser.add_argument("--mark-stable-loop-followup-closed", type=str, help="Mark a resolved stable-loop follow-up chain closed after operator review")
    parser.add_argument("--cleanup-stable-loop-followup-completions", action="store_true", help="Archive resolved stable-loop follow-up completion records; dry-run unless --cleanup-stable-loop-confirm is used")
    parser.add_argument("--stable-loop-followup-completion-full", action="store_true", help="Include raw follow-up completion report/cleanup JSON")
    parser.add_argument("--project-status", action="store_true", help="Show tracked projects")
    parser.add_argument("--add-project", type=str, help="Add a project and set it active")
    parser.add_argument("--project-path", type=str, default="", help="Path for --add-project")
    parser.add_argument("--project-language", type=str, default="Unknown", help="Language for --add-project")
    parser.add_argument("--project-description", type=str, default="", help="Description for --add-project")
    parser.add_argument("--set-active-project", type=str, help="Set the active project by name")
    parser.add_argument("--add-project-goal", type=str, help="Add a goal to the active project")
    parser.add_argument("--add-project-issue", type=str, help="Add a known issue to the active project")
    parser.add_argument("--add-project-next-step", type=str, help="Add a next step to the active project")
    parser.add_argument("--project-tree", nargs="?", const="", help="List files under the active project path")
    parser.add_argument("--read-project-file", type=str, help="Read a text file from the active project path")
    parser.add_argument("--search-project-files", type=str, help="Search active project files for exact text")
    parser.add_argument("--project-file-path", type=str, default="", help="Optional subfolder/file path for file search/tree commands")
    parser.add_argument("--index-project", nargs="?", const="", help="Build a read-only index of the active project or optional subfolder")
    parser.add_argument("--project-index-summary", action="store_true", help="Show saved project index summary")
    parser.add_argument("--search-project-index", type=str, help="Search the saved project index")
    parser.add_argument("--review-project-file", type=str, help="Review a project file without editing it")
    parser.add_argument("--no-ai-review", action="store_true", help="Use static review only, without the local Ollama model")
    parser.add_argument("--suggest-patch", nargs=2, metavar=("FILE", "REQUEST"), help="Suggest a patch for a project file without applying it")
    parser.add_argument("--list-patches", action="store_true", help="List saved patch proposals")
    parser.add_argument("--show-patch", type=str, help="Show a saved patch proposal by id")
    parser.add_argument("--show-patch-full", action="store_true", help="Include full proposed file content with --show-patch")
    parser.add_argument("--apply-patch", type=str, help="Apply a saved patch proposal by id")
    parser.add_argument("--dry-run", action="store_true", help="Preview patch apply checks without writing files")
    parser.add_argument("--list-applied-patches", action="store_true", help="List patches that have been applied")
    parser.add_argument("--rollback-patch", type=str, help="Rollback an applied patch using its saved backup")
    parser.add_argument("--list-rolled-back-patches", action="store_true", help="List patches that have been rolled back")
    parser.add_argument("--run-command", type=str, help="Run an approved whitelisted command")
    parser.add_argument("--list-allowed-commands", action="store_true", help="List approved command patterns")
    parser.add_argument("--command-history", action="store_true", help="Show recent approved command execution history")
    parser.add_argument("--run-test-workflow", nargs="?", const="", help="Run approved test workflow, optionally for a patch id")
    parser.add_argument("--test-command", action="append", default=[], help="Approved command to include in --run-test-workflow; can be repeated")
    parser.add_argument("--list-test-reports", action="store_true", help="List saved test workflow reports")
    parser.add_argument("--show-test-report", type=str, help="Show a saved test workflow report by id")
    parser.add_argument("--show-test-output", action="store_true", help="Include stdout/stderr when showing a test report")
    parser.add_argument("--review-test-report", type=str, help="Auto-review a test workflow report by id, or use latest")
    parser.add_argument("--auto-review", action="store_true", help="After --run-test-workflow, immediately review the newest test report")
    parser.add_argument("--no-ai-test-review", action="store_true", help="Use heuristic test report review only, without the local Ollama model")
    parser.add_argument("--list-test-reviews", action="store_true", help="List saved test report reviews")
    parser.add_argument("--show-test-review", type=str, help="Show a saved test report review by id")
    parser.add_argument("--hide-ai-review", action="store_true", help="Hide local AI section when showing a saved test review")
    parser.add_argument("--self-improve", nargs=2, metavar=("FILE", "REQUEST"), help="Start supervised self-improvement: review file and propose a patch, but do not apply it")
    parser.add_argument("--self-improve-apply", type=str, help="Apply a proposed self-improvement patch, then run tests and review the report")
    parser.add_argument("--self-improve-ai-review", action="store_true", help="Use local AI during the initial self-improvement code review")
    parser.add_argument("--no-ai-self-review", action="store_true", help="Disable local AI during self-improvement test report review")
    parser.add_argument("--list-self-improvements", action="store_true", help="List saved self-improvement runs")
    parser.add_argument("--show-self-improvement", type=str, help="Show a saved self-improvement run by id")
    parser.add_argument("--show-self-improvement-full", action="store_true", help="Include stored review/report details when showing a self-improvement run")
    parser.add_argument("--latest-ids", action="store_true", help="Show newest patch/run/report/review ids and no-copy aliases")
    parser.add_argument("--settings", action="store_true", help="Show Eidolon settings from data/settings.json")
    parser.add_argument("--get-setting", type=str, help="Show one setting by key")
    parser.add_argument("--set-setting", nargs=2, metavar=("KEY", "VALUE"), help="Update one setting in data/settings.json")
    parser.add_argument("--reset-settings", action="store_true", help="Reset settings to defaults")
    parser.add_argument("--settings-health", action="store_true", help="Check configured Ollama URL and model availability")
    parser.add_argument("--diagnostics", action="store_true", help="Run full Eidolon diagnostics and save a report")
    parser.add_argument("--diagnostics-full", action="store_true", help="Show detailed diagnostic JSON sections")
    parser.add_argument("--list-diagnostic-reports", action="store_true", help="List saved diagnostic reports")
    parser.add_argument("--show-diagnostic-report", nargs="?", const="latest", help="Show a saved diagnostic report by id or alias")
    parser.add_argument("--watch-once", action="store_true", help="Run one background watch-mode check and save a report")
    parser.add_argument("--watch-loop", action="store_true", help="Run a bounded background watch-mode loop")
    parser.add_argument("--watch-interval", type=int, default=int(get_setting("watch_interval_seconds", 300)), help="Seconds between watch-loop cycles")
    parser.add_argument("--watch-cycles", type=int, default=int(get_setting("watch_default_cycles", 3)), help="Number of cycles for --watch-loop")
    parser.add_argument("--no-ai-watch", action="store_true", help="Run watch mode without local AI summary")
    parser.add_argument("--watch-full", action="store_true", help="Include raw details when showing watch reports")
    parser.add_argument("--list-watch-reports", action="store_true", help="List saved background watch reports")
    parser.add_argument("--show-watch-report", nargs="?", const="latest", help="Show a saved watch report by id or alias")
    parser.add_argument("--hide-watch-ai", action="store_true", help="Hide local AI summary when showing a watch report")
    parser.add_argument("--notifications", action="store_true", help="Show unread notifications")
    parser.add_argument("--list-notifications", action="store_true", help="List notifications")
    parser.add_argument("--notification-filter-status", type=str, default="", help="Optional status filter for --list-notifications")
    parser.add_argument("--include-dismissed-notifications", action="store_true", help="Include dismissed notifications when listing")
    parser.add_argument("--show-notification", nargs="?", const="latest-unread", help="Show a notification by id or alias")
    parser.add_argument("--notification-full", action="store_true", help="Include raw notification JSON when showing a notification")
    parser.add_argument("--mark-notification-read", nargs="?", const="latest-unread", help="Mark a notification read by id or alias")
    parser.add_argument("--dismiss-notification", nargs="?", const="latest-unread", help="Dismiss a notification by id or alias")
    parser.add_argument("--notification-note", type=str, default="", help="Optional note for notification status changes")
    parser.add_argument("--clear-dismissed-notifications", action="store_true", help="Delete dismissed notification records")
    parser.add_argument("--chat-action", type=str, help="Translate a plain-English request into a safe proposed Eidolon action")
    parser.add_argument("--execute-chat-action", nargs="?", const="latest", help="Execute or create approval for a saved chat action by id or alias")
    parser.add_argument("--list-chat-actions", action="store_true", help="List saved chat-to-action proposals")
    parser.add_argument("--chat-action-filter-status", type=str, default="", help="Optional status filter for --list-chat-actions")
    parser.add_argument("--show-chat-action", nargs="?", const="latest", help="Show a saved chat action by id or alias")
    parser.add_argument("--chat-action-full", action="store_true", help="Include raw chat action JSON when showing a chat action")
    parser.add_argument("--dashboard", action="store_true", help="Start the local web dashboard with integrated /api routes")
    parser.add_argument("--dashboard-host", type=str, default=str(get_setting("dashboard_host", "127.0.0.1")), help="Host/interface for --dashboard")
    parser.add_argument("--dashboard-port", type=int, default=int(get_setting("dashboard_port", 8765)), help="Port for --dashboard")
    parser.add_argument("--api-server", action="store_true", help="Start the standalone local JSON API server")
    parser.add_argument("--api-host", type=str, default=str(get_setting("api_host", "127.0.0.1")), help="Host/interface for --api-server")
    parser.add_argument("--api-port", type=int, default=int(get_setting("api_port", 8766)), help="Port for --api-server")
    parser.add_argument("--desktop", action="store_true", help="Start the local desktop companion shell")
    parser.add_argument("--desktop-status", action="store_true", help="Show desktop companion shell launch info and URLs")
    parser.add_argument("--desktop-tray-status", action="store_true", help="Show optional real system tray availability and settings")
    parser.add_argument("--setup-check", action="store_true", help="Run and save a first-run/desktop startup setup check")
    parser.add_argument("--setup-full", action="store_true", help="Include detailed setup check diagnostics")
    parser.add_argument("--list-setup-reports", action="store_true", help="List saved setup helper reports")
    parser.add_argument("--show-setup-report", nargs="?", const="latest", help="Show a saved setup helper report by id or alias")
    parser.add_argument("--onboarding", action="store_true", help="Run and save the guided desktop onboarding wizard")
    parser.add_argument("--onboarding-full", action="store_true", help="Include detailed setup report and raw onboarding data")
    parser.add_argument("--onboarding-use-latest-setup", action="store_true", help="Build onboarding from latest setup report instead of running a fresh setup check")
    parser.add_argument("--list-onboarding-runs", action="store_true", help="List saved guided onboarding wizard runs")
    parser.add_argument("--show-onboarding-run", nargs="?", const="latest", help="Show a saved onboarding run by id or alias")
    parser.add_argument("--maintenance-scan", action="store_true", help="Create read-only maintenance suggestions for the active project")
    parser.add_argument("--no-ai-maintenance", action="store_true", help="Create maintenance suggestions without local AI summary")
    parser.add_argument("--list-maintenance-scans", action="store_true", help="List saved maintenance suggestion scans")
    parser.add_argument("--show-maintenance-scan", type=str, help="Show a saved maintenance scan by id, or use latest")
    parser.add_argument("--show-maintenance-full", action="store_true", help="Include detailed notes when showing a maintenance scan")
    parser.add_argument("--hide-maintenance-ai", action="store_true", help="Hide local AI summary when showing a maintenance scan")
    parser.add_argument("--memory-status", action="store_true", help="Show active memory counts and compaction status")
    parser.add_argument("--compact-memory", action="store_true", help="Archive and summarize older memories")
    parser.add_argument("--keep-recent-memories", type=int, default=int(get_setting("memory_keep_recent", 40)), help="How many recent memories to keep active during compaction")
    parser.add_argument("--min-memories-to-compact", type=int, default=int(get_setting("memory_min_count", 80)), help="Minimum active memory count before compaction runs")
    parser.add_argument("--no-ai-memory-compact", action="store_true", help="Compact memory using heuristic summary only, without local AI")
    parser.add_argument("--list-memory-summaries", action="store_true", help="List saved memory compaction summaries")
    parser.add_argument("--show-memory-summary", type=str, help="Show a memory summary by id, or use latest")
    parser.add_argument("--show-memory-summary-full", action="store_true", help="Include heuristic and local AI details when showing a memory summary")
    parser.add_argument("--plan-session", action="store_true", help="Create a read-only recommended session plan")
    parser.add_argument("--no-ai-session", action="store_true", help="Create session plan without local AI brief")
    parser.add_argument("--list-session-plans", action="store_true", help="List saved session plans")
    parser.add_argument("--show-session-plan", type=str, help="Show a saved session plan by id, or use latest")
    parser.add_argument("--show-session-plan-full", action="store_true", help="Include context details and all recommendations when showing a session plan")
    parser.add_argument("--hide-session-ai", action="store_true", help="Hide local AI brief when showing a session plan")
    parser.add_argument("--task-status", action="store_true", help="Show task queue status")
    parser.add_argument("--list-tasks", action="store_true", help="List task queue items")
    parser.add_argument("--task-filter-status", type=str, default="", help="Optional status filter for --list-tasks")
    parser.add_argument("--task-filter-project", type=str, default="", help="Optional project filter for --list-tasks")
    parser.add_argument("--hide-cancelled-tasks", action="store_true", help="Hide cancelled tasks when listing tasks")
    parser.add_argument("--show-task", type=str, help="Show a task by id, or use latest/latest-open/latest-ready/latest-active/latest-blocked/latest-done")
    parser.add_argument("--show-task-full", action="store_true", help="Include notes when showing a task")
    parser.add_argument("--add-task", type=str, help="Add a task to the queue")
    parser.add_argument("--task-description", type=str, default="", help="Description for --add-task")
    parser.add_argument("--task-priority", type=str, default="medium", help="Priority for --add-task: low, medium, high, critical")
    parser.add_argument("--task-initial-status", type=str, default="planned", help="Initial status for --add-task")
    parser.add_argument("--task-project", type=str, default="", help="Project name for --add-task or task list filter")
    parser.add_argument("--task-command", type=str, default="", help="Recommended command for --add-task")
    parser.add_argument("--task-next-action", type=str, default="", help="First next action for --add-task")
    parser.add_argument("--task-goal", type=str, default="", help="Linked goal id for --add-task")
    parser.add_argument("--task-risk", type=str, default="low", help="Risk label for --add-task")
    parser.add_argument("--set-task-status", nargs=2, metavar=("TASK", "STATUS"), help="Set a task status")
    parser.add_argument("--task-note", type=str, default="", help="Optional note for --set-task-status, --start-task, or --complete-task")
    parser.add_argument("--add-task-note", nargs=2, metavar=("TASK", "NOTE"), help="Add a note to a task")
    parser.add_argument("--add-task-action", nargs=2, metavar=("TASK", "ACTION"), help="Add a next action to a task")
    parser.add_argument("--start-task", type=str, help="Mark a task active")
    parser.add_argument("--complete-task", type=str, help="Mark a task done")
    parser.add_argument("--block-task", nargs=2, metavar=("TASK", "REASON"), help="Mark a task blocked with a blocker reason")
    parser.add_argument("--next-task", action="store_true", help="Show the highest-priority ready task")
    parser.add_argument("--queue-from-session", nargs="?", const="latest", help="Create task queue items from a saved session plan")
    parser.add_argument("--queue-task-limit", type=int, default=6, help="Maximum tasks to create from a session plan")
    parser.add_argument("--task-command-options", nargs="?", const="latest-ready", help="Show command options for a task")
    parser.add_argument("--execute-task", nargs="?", const="latest-ready", help="Run a queued task command through the approved command runner")
    parser.add_argument("--task-command-index", type=int, default=0, help="Command option index for --execute-task; 0 is primary, 1+ are follow-ups")
    parser.add_argument("--complete-on-success", action="store_true", help="Mark task done if --execute-task succeeds")
    parser.add_argument("--task-execution-history", nargs="?", const="latest", help="Show command execution history for a task")
    parser.add_argument("--evaluate-task", nargs="?", const="latest", help="Evaluate a task's execution history and recommend the next safe action")
    parser.add_argument("--no-ai-task-evaluation", action="store_true", help="Skip local AI summary when evaluating a task")
    parser.add_argument("--list-task-evaluations", action="store_true", help="List saved task result evaluations")
    parser.add_argument("--show-task-evaluation", nargs="?", const="latest", help="Show a saved task evaluation by id or alias")
    parser.add_argument("--hide-task-evaluation-ai", action="store_true", help="Hide AI section when showing a saved task evaluation")
    parser.add_argument("--apply-task-evaluation", nargs="?", const="latest", help="Apply a saved task evaluation when it recommends a safe status change")
    parser.add_argument("--task-evaluation-follow-up", action="store_true", help="Create a follow-up task when applying a task evaluation")
    parser.add_argument("--guided-work-session", nargs="?", const="latest-ready", help="Show and save a guided next-step plan for a task")
    parser.add_argument("--advance-work-session", nargs="?", const="latest-ready", help="Advance a task by one safe guided step")
    parser.add_argument("--apply-guided-evaluation", action="store_true", help="Allow --advance-work-session to apply a safe task evaluation recommendation")
    parser.add_argument("--guided-session-full", action="store_true", help="Include full task details when showing guided session output")
    parser.add_argument("--list-guided-sessions", action="store_true", help="List saved guided work sessions")
    parser.add_argument("--show-guided-session", nargs="?", const="latest", help="Show a saved guided work session by id or alias")
    parser.add_argument("--dev-cycle", nargs="?", const="latest-ready", help="Inspect the next supervised autonomous development step")
    parser.add_argument("--advance-dev-cycle", nargs="?", const="latest-ready", help="Advance the supervised autonomous dev cycle by one safe step")
    parser.add_argument("--approve-dev-cycle-apply", action="store_true", help="Allow --advance-dev-cycle to apply or rollback a patch when that is the selected step")
    parser.add_argument("--apply-dev-cycle-evaluation", action="store_true", help="Allow --advance-dev-cycle to apply a safe task evaluation recommendation")
    parser.add_argument("--no-ai-dev-cycle", action="store_true", help="Skip local AI summaries during dev-cycle advancement")
    parser.add_argument("--dev-cycle-full", action="store_true", help="Include full state details when showing dev cycle output")
    parser.add_argument("--list-dev-cycles", action="store_true", help="List saved supervised dev cycle records")
    parser.add_argument("--show-dev-cycle", nargs="?", const="latest", help="Show a saved supervised dev cycle by id or alias")
    parser.add_argument("--dev-loop", nargs="?", const="latest-ready", help="Run a bounded autonomous dev loop for a task alias/id")
    parser.add_argument("--dev-loop-steps", type=int, default=int(get_setting("default_dev_loop_steps", 3)), help="Maximum number of bounded dev-loop steps to run, capped by settings max_dev_loop_steps")
    parser.add_argument("--approve-dev-loop-actions", action="store_true", help="Allow dev loop to apply or rollback patches when that approved step is selected")
    parser.add_argument("--apply-dev-loop-evaluation", action="store_true", help="Allow dev loop to apply safe task evaluation recommendations")
    parser.add_argument("--no-ai-dev-loop", action="store_true", help="Skip local AI summaries during bounded dev-loop actions")
    parser.add_argument("--dev-loop-full", action="store_true", help="Include raw loop details when showing dev-loop output")
    parser.add_argument("--list-dev-loops", action="store_true", help="List saved bounded autonomous dev-loop records")
    parser.add_argument("--show-dev-loop", nargs="?", const="latest", help="Show a saved bounded dev loop by id or alias")
    parser.add_argument("--approval-inbox", action="store_true", help="Show pending approval requests")
    parser.add_argument("--list-approvals", action="store_true", help="List approval requests, including closed ones")
    parser.add_argument("--approval-filter-status", type=str, default="", help="Optional status filter for --list-approvals")
    parser.add_argument("--show-approval", nargs="?", const="latest-pending", help="Show an approval request by id or alias")
    parser.add_argument("--approval-full", action="store_true", help="Include raw approval JSON when showing an approval")
    parser.add_argument("--approve", nargs="?", const="latest-pending", help="Execute a pending approval request by id or alias")
    parser.add_argument("--reject", nargs="?", const="latest-pending", help="Reject a pending approval request by id or alias")
    parser.add_argument("--approval-note", type=str, default="", help="Optional note for --reject")
    parser.add_argument("--goal-status", action="store_true", help="Show structured goal counts and open goal context")
    parser.add_argument("--list-goals", action="store_true", help="List structured goals")
    parser.add_argument("--goal-filter-status", type=str, default="", help="Optional status filter for --list-goals")
    parser.add_argument("--goal-filter-project", type=str, default="", help="Optional project filter for --list-goals")
    parser.add_argument("--hide-cancelled-goals", action="store_true", help="Hide cancelled goals when listing goals")
    parser.add_argument("--show-goal", type=str, help="Show a goal by id, or use latest/latest-open/latest-active/latest-blocked/latest-completed")
    parser.add_argument("--show-goal-full", action="store_true", help="Include notes when showing a goal")
    parser.add_argument("--add-goal-structured", type=str, help="Add a structured goal")
    parser.add_argument("--goal-description", type=str, default="", help="Description for --add-goal-structured")
    parser.add_argument("--goal-priority", type=str, default="medium", help="Priority for --add-goal-structured: low, medium, high, critical")
    parser.add_argument("--goal-initial-status", type=str, default="planned", help="Initial status for --add-goal-structured")
    parser.add_argument("--goal-project", type=str, default="", help="Project name for --add-goal-structured or --list-goals filter")
    parser.add_argument("--goal-next-action", type=str, default="", help="First next action for --add-goal-structured")
    parser.add_argument("--set-goal-status", nargs=2, metavar=("GOAL", "STATUS"), help="Set a structured goal status")
    parser.add_argument("--goal-note", type=str, default="", help="Optional note used with --set-goal-status or --complete-goal")
    parser.add_argument("--add-goal-note", nargs=2, metavar=("GOAL", "NOTE"), help="Add a note to a structured goal")
    parser.add_argument("--add-goal-action", nargs=2, metavar=("GOAL", "ACTION"), help="Add a next action to a structured goal")
    parser.add_argument("--block-goal", nargs=2, metavar=("GOAL", "REASON"), help="Mark a goal blocked with a blocker reason")
    parser.add_argument("--complete-goal", type=str, help="Mark a structured goal completed")
    parser.add_argument("--delay", type=int, default=10, help="Seconds between loop cycles")
    args = parser.parse_args()

    if args.work_queue is not None:
        raise SystemExit(run_work_queue_cli(args.work_queue))

    if args.task_work is not None:
        raise SystemExit(run_work_queue_cli(args.task_work))

    task_work_full = args.task_work_executor_full or args.work_executor_full
    allow_task_work_approval = args.approve_task_work_execution or args.approve_work_execution
    use_task_work_ai = not (args.no_ai_task_work_executor or args.no_ai_work_executor)

    if args.request_task_approval:
        print_request_task_work_approval(
            args.request_task_approval,
            reason=args.task_approval_reason,
            use_ai=use_task_work_ai,
            full_output=task_work_full,
            force=args.force_task_approval,
            dry_run=args.dry_run,
            full=args.task_approval_full,
        )
        return

    if args.request_next_task_approval:
        print_request_next_task_work_approval(
            project_id=args.task_approval_project or None,
            reason=args.task_approval_reason,
            use_ai=use_task_work_ai,
            full_output=task_work_full,
            force=args.force_task_approval,
            dry_run=args.dry_run,
            full=args.task_approval_full,
        )
        return

    if args.show_task_approvals:
        print_task_approvals(
            args.show_task_approvals,
            include_closed=True,
            full=args.task_approval_full,
        )
        return

    if args.task_recovery_summary:
        print_task_recoveries(
            project=args.task_recovery_project,
            include_nonrecoverable=False,
            full=False,
        )
        return

    if args.list_task_recoveries:
        print_task_recoveries(
            project=args.task_recovery_project,
            include_nonrecoverable=False,
            full=args.task_recovery_full,
        )
        return

    if args.show_task_recovery:
        print_task_recovery(args.show_task_recovery, full=args.task_recovery_full)
        return

    if args.mark_task_ready_for_retry:
        print_mark_task_ready_for_retry(
            args.mark_task_ready_for_retry,
            note=args.task_recovery_note,
            full=args.task_recovery_full,
        )
        return

    if args.retry_task_work:
        print_retry_task_work(
            args.retry_task_work,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=args.task_recovery_full or task_work_full,
        )
        return

    if args.execute_task_work_id or args.execute_work_id:
        target_task_id = args.execute_task_work_id or args.execute_work_id
        print_execute_task_work_item(
            target_task_id,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=task_work_full,
        )
        return

    if args.execute_task_work or args.execute_work:
        project_filter = args.execute_task_work_project or args.execute_work_project or None
        print_execute_next_task_work_item(
            project_id=project_filter,
            dry_run=args.dry_run,
            allow_approval_required=allow_task_work_approval,
            use_ai=use_task_work_ai,
            full=task_work_full,
        )
        return

    if args.queue_task_patch:
        target_file, request = args.queue_task_patch
        print_create_patch_task(
            target_file=target_file,
            request=request,
            project_id=args.queue_patch_project,
            priority=args.queue_patch_priority,
            risk=args.queue_patch_risk,
            requires_approval=args.queue_patch_requires_approval or None,
        )
        return

    if args.queue_patch:
        target_file, request = args.queue_patch
        print_create_patch_work_item(
            target_file=target_file,
            request=request,
            project_id=args.queue_patch_project,
            priority=args.queue_patch_priority,
            risk=args.queue_patch_risk,
            requires_approval=args.queue_patch_requires_approval or None,
        )
        return

    if args.suggest_patch_for_task:
        print_suggest_patch_for_task(
            args.suggest_patch_for_task,
            use_ai=not args.no_ai_work_executor,
            dry_run=args.dry_run,
            full=args.work_executor_full,
        )
        return

    if args.suggest_patch_for_work:
        print_suggest_patch_for_work_item(
            args.suggest_patch_for_work,
            use_ai=not args.no_ai_work_executor,
            dry_run=args.dry_run,
            full=args.work_executor_full,
        )
        return

    if args.create_patch_task_followups:
        print_create_patch_task_followups(args.create_patch_task_followups, project_id=args.patch_followup_project)
        return

    if args.create_patch_followups:
        print_create_patch_followups(args.create_patch_followups, project_id=args.patch_followup_project)
        return

    if args.work_cycle:
        print_work_cycle(
            project_id=args.work_cycle_project,
            max_steps=args.work_cycle_steps,
            dry_run=args.dry_run,
            use_ai=not args.no_ai_work_cycle,
            approve_work_execution=args.approve_work_cycle_actions,
            seed_if_empty=not args.no_work_cycle_seed,
            auto_create_patch_followups=not args.no_work_cycle_followups,
            auto_request_approvals=not args.no_work_cycle_approval_requests,
            auto_retry_recovery=args.work_cycle_auto_retry_recovery,
            full=args.work_cycle_full,
        )
        return

    if args.list_work_cycles:
        print_work_cycles()
        return

    if args.show_work_cycle:
        print_saved_work_cycle(args.show_work_cycle, full=args.work_cycle_full)
        return

    if args.stable_loop_preflight:
        print_stable_loop_preflight(
            project_id=args.stable_loop_project,
            max_steps=args.stable_loop_steps,
            full=args.stable_loop_full,
        )
        return

    if args.stable_loop_guardrails:
        print_stable_loop_guardrails(
            project_id=args.stable_loop_project,
            bypass=args.stable_loop_bypass_closure_guardrails,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_full,
        )
        return

    if args.stabilization_checkpoint:
        print_stabilization_checkpoint(
            project_id=args.stable_loop_project,
            full=args.stabilization_full,
            json_output=args.stabilization_json,
        )
        return

    if args.doctor:
        print_doctor(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.repair_suggestions:
        print_repair_suggestions(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.patch_integrity:
        print_patch_integrity(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_snapshot:
        print_project_snapshot(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.task_review:
        print_task_review(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.recovery_drill:
        print_recovery_drill(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.stable_loop_confidence:
        print_stable_loop_confidence(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.hardening_report:
        print_hardening_report(
            project_id=args.stable_loop_project,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.controlled_self_build and args.select_task:
        print_controlled_task_selection(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.plan_patch:
        print_patch_plan(project_id=args.stable_loop_project, target_version="12.0", full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_workspace_status or (args.controlled_self_build and args.patch_workspace_status):
        print_patch_workspace_status(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.stage_patch:
        print_stage_controlled_patch(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.preview_diff:
        print_preview_staged_diff(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build and args.apply_staged_patch:
        print_apply_staged_patch(
            project_id=args.stable_loop_project,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.verify_latest_patch:
        print_verify_latest_patch(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rollback_latest_patch:
        print_rollback_latest_patch(
            project_id=args.stable_loop_project,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.readme_gate:
        print_readme_gate(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.controlled_self_build_cycle:
        print_controlled_build_cycle(
            project_id=args.stable_loop_project,
            live=args.controlled_self_build_live,
            approve=args.approve_controlled_self_build,
            dry_run=args.dry_run or not args.controlled_self_build_live,
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return

    if args.supervised_dev_loop:
        print_supervised_dev_loop(
            project_id=args.stable_loop_project,
            live=args.controlled_self_build_live,
            approve=args.approve_controlled_self_build,
            use_ai=(not args.no_ai_stable_loop and ai_reviews_enabled()),
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return

    if args.controlled_self_build:
        print_controlled_self_build(
            project_id=args.stable_loop_project,
            max_steps=args.controlled_self_build_steps,
            live=args.controlled_self_build_live,
            approve_live=args.approve_controlled_self_build,
            use_ai=(not args.no_ai_stable_loop and ai_reviews_enabled()),
            full=args.doctor_full or args.stable_loop_full,
            json_output=args.readiness_json,
        )
        return


    if args.codebase_map:
        print_codebase_map(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.task_dependencies:
        print_task_dependencies(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_plan:
        print_test_plan(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_risk:
        print_patch_risk(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review:
        print_patch_review(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_memory_index:
        print_project_memory_index(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_status:
        print_workspace_status(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.cross_project_task_review:
        print_cross_project_task_review(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.asymmetric_dev_loop:
        print_asymmetric_dev_loop(project_id=args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_registry:
        print_project_registry(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.register_project:
        print_register_project(
            name=args.register_project,
            root=args.workspace_project_root,
            version=args.workspace_project_version,
            language=args.workspace_project_language,
            framework_type=args.workspace_project_framework,
            readme_path=args.workspace_project_readme,
            test_commands=args.workspace_project_test_command,
            profile=args.workspace_command_profile,
            project_id=args.workspace_project_id,
            full=args.doctor_full,
            json_output=args.readiness_json,
        )
        return

    if args.set_active_workspace_project:
        print_set_active_workspace_project(args.set_active_workspace_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_health or args.project_health_all:
        print_project_health(project_id=args.workspace_project_id or args.stable_loop_project, all_projects=args.project_health_all, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.command_profiles:
        print_command_profiles(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_dependency_map:
        print_workspace_dependency_map(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_task_inbox:
        print_workspace_task_inbox(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.switch_project:
        print_switch_workspace_project(args.switch_project, force=args.force_switch_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_context:
        print_project_context(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_timeline:
        print_workspace_timeline(full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_dev_loop:
        print_workspace_dev_loop(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_registry_audit:
        print_workspace_registry_audit(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json, archive_stale=True)
        return

    if args.workspace_repair_suggestions:
        print_workspace_repair_suggestions(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_registration_wizard:
        print_project_registration_wizard(name=args.project_registration_wizard, root=args.workspace_project_root, project_id=args.workspace_project_id, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.project_boundary_check:
        print_project_boundary_check(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_patch_plan:
        print_workspace_patch_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_preview_diff:
        print_workspace_preview_diff(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_apply:
        approved = bool(args.approve_controlled_self_build)
        print_workspace_apply(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.workspace_verify_latest:
        print_workspace_verify_latest(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.guarded_workspace_dev_loop:
        approved = bool(args.approve_controlled_self_build)
        print_guarded_workspace_dev_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_draft_request:
        print_patch_draft_request(project_id=args.workspace_project_id or args.stable_loop_project, target_version=args.patch_draft_target_version, task=args.patch_draft_task, intent=args.patch_draft_intent, risk_limit=args.patch_draft_risk_limit, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_patch:
        print_draft_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_draft_status:
        print_patch_draft_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review_notes:
        print_patch_review_notes(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_diff:
        print_draft_diff(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_test_impact:
        print_draft_test_impact(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approve_draft:
        print_approve_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reject_draft:
        print_reject_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_approved_draft:
        print_apply_approved_draft(project_id=args.workspace_project_id or args.stable_loop_project, dry_run=args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rollback_approved_draft:
        approved = bool(args.approve_controlled_self_build)
        print_rollback_approved_draft(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.reopen_draft:
        print_reopen_draft(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.human_approved_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_human_approved_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_quality:
        print_draft_quality(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_file_targets:
        print_draft_file_targets(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_intent_blocks:
        print_draft_intent_blocks(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_conflicts:
        print_draft_conflicts(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_verification_bundle:
        print_draft_verification_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.draft_review_checklist:
        print_draft_review_checklist(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approved_draft_execution_report:
        print_approved_draft_execution_report(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.review_centered_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_review_centered_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_edit_proposal:
        print_code_edit_proposal(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.safe_rewrite_preview:
        print_safe_rewrite_preview(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.generate_code_patch:
        print_generated_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_suggestions:
        print_test_suggestions(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.inline_review_note:
        print_inline_review_note(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, file_path=args.inline_review_file, intent_block=args.inline_review_intent, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_approved_code_patch:
        approved = bool(args.approve_controlled_self_build)
        print_apply_approved_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.prepare_release_package:
        print_prepare_release_package(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_readiness:
        print_release_readiness(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.human_approved_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_human_approved_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve_apply=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_patch_status:
        print_code_patch_status(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.symbol_scan:
        print_symbol_scan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rewrite_plan:
        print_rewrite_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rewrite_conflicts:
        print_rewrite_conflicts(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_patch_diff_bundle:
        print_code_patch_diff_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_code_patch_transaction:
        approved = bool(args.approve_controlled_self_build)
        print_apply_code_patch_transaction(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.semantic_checks:
        print_semantic_checks(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_artifact:
        print_release_artifact(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_audit_trail:
        print_release_audit_trail(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.generated_code_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_generated_code_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.task_to_code_patch:
        print_task_to_code_patch(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.code_context:
        print_code_context(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_prompt:
        print_patch_prompt(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.parse_generated_edits:
        print_parse_generated_edits(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.edit_consistency:
        print_edit_consistency(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_code_patch_dry_run:
        print_ai_code_patch_dry_run(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_failure_analysis:
        print_patch_failure_analysis(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_learning_notes:
        print_patch_learning_notes(project_id=args.workspace_project_id or args.stable_loop_project, note=args.patch_review_note, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_assisted_code_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_ai_assisted_code_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.refine_patch_objective:
        print_patch_objective_refinement(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.rank_code_context:
        print_code_context_ranking(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_safety_envelope:
        print_patch_safety_envelope(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.validate_generated_patch:
        print_generated_patch_validation(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_simulation:
        print_patch_simulation(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.test_stub_plan:
        print_test_stub_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_review_score:
        print_patch_review_score(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.patch_recovery_plan:
        print_patch_recovery_plan(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.validated_ai_code_patch_loop:
        approved = bool(args.approve_controlled_self_build)
        print_validated_ai_code_patch_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_patch_review_bundle:
        print_ai_patch_review_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.ai_patch_review_integrity:
        print_review_bundle_integrity(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_ready:
        print_approval_ready(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_ledger:
        print_approval_ledger(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.apply_validated_ai_patch:
        approved = bool(args.approve_controlled_self_build)
        print_apply_validated_ai_patch(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.post_apply_review:
        print_post_apply_review(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_build_plan:
        print_package_build_plan(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.approval_to_release_loop:
        approved = bool(args.approve_controlled_self_build)
        print_approval_to_release_loop(project_id=args.workspace_project_id or args.stable_loop_project, approve=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.bind_validated_approval:
        print_bind_validated_approval(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.refresh_ai_patch_review_bundle:
        print_ai_patch_review_bundle(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_manifest_integrity:
        print_release_manifest_integrity(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_inventory:
        print_package_inventory(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.package_checksums:
        print_package_checksums(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_notes:
        print_release_notes(project_id=args.workspace_project_id or args.stable_loop_project, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_handoff_report:
        print_release_handoff_report(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.build_release_zip:
        approved = bool(args.approve_controlled_self_build)
        print_build_release_zip(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verify_release_unzip:
        print_verify_release_unzip(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.release_pipeline_audit:
        print_release_pipeline_audit(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.verified_release_package_loop:
        approved = bool(args.approve_controlled_self_build)
        print_verified_release_package_loop(project_id=args.workspace_project_id or args.stable_loop_project, package_name=args.release_package_name, confirm=approved, dry_run=not approved or args.dry_run, full=args.doctor_full, json_output=args.readiness_json)
        return

    if args.stable_loop:
        print_stable_loop(
            project_id=args.stable_loop_project,
            max_steps=args.stable_loop_steps,
            live=args.stable_loop_live,
            use_ai=not args.no_ai_stable_loop,
            approve_work_execution=args.approve_stable_loop_actions,
            seed_if_empty=not args.no_stable_loop_seed,
            auto_create_patch_followups=not args.no_stable_loop_followups,
            auto_request_approvals=not args.no_stable_loop_approval_requests,
            auto_retry_recovery=args.stable_loop_auto_retry_recovery,
            bypass_closure_guardrails=args.stable_loop_bypass_closure_guardrails,
            full=args.stable_loop_full,
        )
        return

    if args.list_stable_loops:
        print_stable_loops()
        return

    if args.stable_loop_review_summary:
        print_stable_loop_review_summary(full=args.stable_loop_review_full)
        return

    if args.list_stable_loop_reviews is not None:
        filter_value = args.list_stable_loop_reviews or args.stable_loop_review_filter
        print_stable_loop_reviews(
            review_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_review_full,
        )
        return

    if args.archive_stable_loop:
        print_archive_stable_loop(
            args.archive_stable_loop,
            archived=True,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.restore_stable_loop:
        print_archive_stable_loop(
            args.restore_stable_loop,
            archived=False,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.cleanup_stable_loop_history:
        print_cleanup_stable_loop_history(
            review_filter=args.stable_loop_review_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_review_full,
        )
        return

    if args.show_stable_loop_review:
        print_stable_loop_review(args.show_stable_loop_review, full=args.stable_loop_review_full)
        return

    if args.show_stable_loop_audit:
        print_stable_loop_audit(args.show_stable_loop_audit, refresh=False, full=args.stable_loop_audit_full)
        return

    if args.refresh_stable_loop_audit:
        print_stable_loop_audit(args.refresh_stable_loop_audit, refresh=True, full=args.stable_loop_audit_full)
        return

    if args.show_stable_loop_operator_notes:
        print_stable_loop_operator_notes(args.show_stable_loop_operator_notes, full=args.stable_loop_operator_full)
        return

    if args.add_stable_loop_operator_note:
        print_add_stable_loop_operator_note(
            args.add_stable_loop_operator_note,
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.complete_stable_loop_check:
        loop_id, check_id = args.complete_stable_loop_check
        print_update_stable_loop_check(
            loop_id,
            check_id,
            status="done",
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.skip_stable_loop_check:
        loop_id, check_id = args.skip_stable_loop_check
        print_update_stable_loop_check(
            loop_id,
            check_id,
            status="skipped",
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.set_stable_loop_final_decision:
        print_set_stable_loop_final_decision(
            args.set_stable_loop_final_decision,
            decision=args.stable_loop_final_decision,
            note=args.stable_loop_operator_note,
            full=args.stable_loop_operator_full,
        )
        return

    if args.stable_loop_decision_report is not None:
        filter_value = args.stable_loop_decision_report or args.stable_loop_decision_filter
        print_stable_loop_decision_report(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=True,
            full=args.stable_loop_decision_full,
        )
        return

    if args.list_stable_loop_decisions is not None:
        filter_value = args.list_stable_loop_decisions or args.stable_loop_decision_filter
        print_stable_loop_decision_rows(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=True,
        )
        return

    if args.cleanup_stable_loop_decisions:
        print_cleanup_stable_loop_decisions(
            decision_filter=args.stable_loop_decision_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_decision_full,
        )
        return

    if args.cleanup_stable_loop_followup_completions:
        print_cleanup_stable_loop_followup_completions(
            completion_filter=args.stable_loop_followup_completion_filter,
            limit=args.cleanup_stable_loop_limit,
            dry_run=not args.cleanup_stable_loop_confirm,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.mark_stable_loop_followup_closed:
        print_mark_stable_loop_followup_closed(
            args.mark_stable_loop_followup_closed,
            note=args.stable_loop_followup_note,
            archive=args.archive_resolved_stable_loop,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.stable_loop_followup_completion_report is not None:
        filter_value = args.stable_loop_followup_completion_report or args.stable_loop_followup_completion_filter or "all"
        print_stable_loop_followup_completion_report(
            completion_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_completion_full,
        )
        return

    if args.list_stable_loop_followup_completions is not None:
        filter_value = args.list_stable_loop_followup_completions or args.stable_loop_followup_completion_filter or "all"
        print_stable_loop_followup_completion_rows(
            completion_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            limit=args.cleanup_stable_loop_limit,
        )
        return

    if args.stable_loop_followup_lifecycle_summary is not None:
        filter_value = args.stable_loop_followup_lifecycle_summary or "all"
        print_stable_loop_followup_lifecycle_summary(
            decision_filter=filter_value,
            include_closed=True,
            include_archived=args.include_archived_stable_loops,
            full=args.stable_loop_followup_full,
        )
        return

    if args.show_task_stable_loop_followup:
        print_stable_loop_followup_task(args.show_task_stable_loop_followup, full=args.stable_loop_followup_full)
        return

    if args.resolve_stable_loop_followups:
        print_resolve_stable_loop_followups(
            args.resolve_stable_loop_followups,
            archive=args.archive_resolved_stable_loop,
            force=args.force_stable_loop_followup_resolution,
            note=args.stable_loop_followup_note,
            full=args.stable_loop_followup_full,
        )
        return

    if args.resolve_task_stable_loop_followup:
        print_resolve_task_stable_loop_followup(
            args.resolve_task_stable_loop_followup,
            archive=args.archive_resolved_stable_loop,
            force=args.force_stable_loop_followup_resolution,
            note=args.stable_loop_followup_note,
            full=args.stable_loop_followup_full,
        )
        return

    if args.stable_loop_followup_summary is not None:
        filter_value = args.stable_loop_followup_summary or args.stable_loop_decision_filter or "action_required"
        print_stable_loop_followup_summary(
            decision_filter=filter_value,
            include_archived=args.include_archived_stable_loops,
            include_live=not args.cleanup_stable_loop_exclude_live,
            full=args.stable_loop_followup_full,
        )
        return

    if args.create_stable_loop_followups:
        print_create_stable_loop_followups(
            args.create_stable_loop_followups,
            dry_run=args.dry_run,
            force=args.stable_loop_followup_force,
            full=args.stable_loop_followup_full,
        )
        return

    if args.create_stable_loop_decision_followups is not None:
        filter_value = args.create_stable_loop_decision_followups or args.stable_loop_decision_filter or "action_required"
        print_create_stable_loop_followups_for_decisions(
            decision_filter=filter_value,
            dry_run=args.dry_run,
            include_archived=args.include_archived_stable_loops,
            include_live=not args.cleanup_stable_loop_exclude_live,
            limit=args.cleanup_stable_loop_limit,
            force=args.stable_loop_followup_force,
            full=args.stable_loop_followup_full,
        )
        return

    if args.mark_stable_loop_reviewed:
        print_update_stable_loop_review(
            args.mark_stable_loop_reviewed,
            status="reviewed",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.approve_stable_loop_live:
        print_update_stable_loop_review(
            args.approve_stable_loop_live,
            status="approved_for_live",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.reject_stable_loop:
        print_update_stable_loop_review(
            args.reject_stable_loop,
            status="rejected",
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full,
        )
        return

    if args.run_approved_stable_loop_live:
        print_run_approved_stable_loop_live(
            args.run_approved_stable_loop_live,
            note=args.stable_loop_review_note,
            full=args.stable_loop_review_full or args.stable_loop_full,
        )
        return

    if args.status:
        print_status()
        return

    if args.latest_ids:
        print_latest_ids()
        return

    if args.settings:
        print_settings()
        return

    if args.get_setting:
        print_get_setting(args.get_setting)
        return

    if args.set_setting:
        key, value = args.set_setting
        print_set_setting(key, value)
        return

    if args.reset_settings:
        print_reset_settings()
        return

    if args.settings_health:
        print_settings_health()
        return

    if args.watch_once:
        print_watch_once(use_ai=(not args.no_ai_watch and ai_reviews_enabled()), full=args.watch_full)
        return

    if args.watch_loop:
        print_watch_loop(
            cycles=args.watch_cycles,
            interval_seconds=args.watch_interval,
            use_ai=(not args.no_ai_watch and ai_reviews_enabled()),
            full=args.watch_full,
        )
        return

    if args.list_watch_reports:
        print_watch_reports()
        return

    if args.show_watch_report is not None:
        print_saved_watch_report(args.show_watch_report, full=args.watch_full, include_ai=not args.hide_watch_ai)
        return

    if args.notifications:
        print_notifications(status="unread", include_dismissed=False)
        return

    if args.list_notifications:
        print_notifications(status=args.notification_filter_status, include_dismissed=args.include_dismissed_notifications)
        return

    if args.show_notification is not None:
        print_notification(args.show_notification, full=args.notification_full)
        return

    if args.mark_notification_read is not None:
        print_mark_notification_read(args.mark_notification_read, note=args.notification_note)
        return

    if args.dismiss_notification is not None:
        print_dismiss_notification(args.dismiss_notification, note=args.notification_note)
        return

    if args.clear_dismissed_notifications:
        print_clear_dismissed_notifications()
        return

    if args.chat_action:
        print_chat_action(args.chat_action)
        return

    if args.execute_chat_action is not None:
        print_execute_chat_action(args.execute_chat_action, dry_run=args.dry_run)
        return

    if args.list_chat_actions:
        print_chat_actions(status=args.chat_action_filter_status, include_closed=True)
        return

    if args.show_chat_action is not None:
        print_saved_chat_action(args.show_chat_action, full=args.chat_action_full)
        return

    if args.dashboard:
        run_dashboard(host=args.dashboard_host, port=args.dashboard_port)
        return

    if args.api_server:
        run_api_server(host=args.api_host, port=args.api_port)
        return

    if args.desktop_status:
        print_desktop_status()
        return

    if args.desktop_tray_status:
        print_desktop_tray_status()
        return

    if args.setup_check:
        print_setup_check(full=args.setup_full)
        return

    if args.list_setup_reports:
        print_setup_reports()
        return

    if args.show_setup_report is not None:
        print_saved_setup_report(args.show_setup_report, full=args.setup_full)
        return

    if args.onboarding:
        print_onboarding_run(full=args.onboarding_full, refresh_setup=not args.onboarding_use_latest_setup)
        return

    if args.list_onboarding_runs:
        print_onboarding_runs()
        return

    if args.show_onboarding_run is not None:
        print_saved_onboarding_run(args.show_onboarding_run, full=args.onboarding_full)
        return

    if args.desktop:
        run_desktop_shell()
        return

    if args.diagnostics:
        print_diagnostics(include_full=args.diagnostics_full)
        return

    if args.list_diagnostic_reports:
        print_diagnostic_reports()
        return

    if args.show_diagnostic_report:
        print_saved_diagnostic_report(args.show_diagnostic_report, include_full=args.diagnostics_full)
        return

    if args.maintenance_scan:
        print_maintenance_scan(use_ai=(not args.no_ai_maintenance and ai_reviews_enabled()))
        return

    if args.list_maintenance_scans:
        print_maintenance_scans()
        return

    if args.show_maintenance_scan:
        print_saved_maintenance_scan(
            args.show_maintenance_scan,
            include_ai=not args.hide_maintenance_ai,
            full=args.show_maintenance_full,
        )
        return

    if args.memory_status:
        print_memory_status()
        return

    if args.compact_memory:
        print_compact_memory(
            keep_recent=args.keep_recent_memories,
            min_memories=args.min_memories_to_compact,
            use_ai=(not args.no_ai_memory_compact and ai_reviews_enabled()),
            dry_run=args.dry_run,
        )
        return

    if args.list_memory_summaries:
        print_memory_summaries()
        return

    if args.show_memory_summary:
        print_memory_summary(args.show_memory_summary, include_full=args.show_memory_summary_full)
        return

    if args.plan_session:
        print_session_plan(use_ai=(not args.no_ai_session and ai_reviews_enabled()))
        return

    if args.list_session_plans:
        print_session_plans()
        return

    if args.show_session_plan:
        print_saved_session_plan(
            args.show_session_plan,
            include_ai=not args.hide_session_ai,
            full=args.show_session_plan_full,
        )
        return

    if args.task_status:
        print_task_status()
        return

    if args.list_tasks:
        print_task_list(
            status=args.task_filter_status,
            project=args.task_filter_project or args.task_project,
            include_cancelled=not args.hide_cancelled_tasks,
        )
        return

    if args.show_task:
        print_task_detail(args.show_task, full=args.show_task_full)
        return

    if args.add_task:
        print_add_task(
            title=args.add_task,
            description=args.task_description,
            priority=args.task_priority,
            status=args.task_initial_status,
            project=args.task_project,
            command=args.task_command,
            next_action=args.task_next_action,
            linked_goal=args.task_goal,
            risk=args.task_risk,
        )
        return

    if args.set_task_status:
        task_id, status = args.set_task_status
        print_set_task_status(task_id, status, note=args.task_note)
        return

    if args.add_task_note:
        task_id, note = args.add_task_note
        print_add_task_note(task_id, note)
        return

    if args.add_task_action:
        task_id, action = args.add_task_action
        print_add_task_action(task_id, action)
        return

    if args.start_task:
        print_start_task(args.start_task, note=args.task_note)
        return

    if args.complete_task:
        print_complete_task(args.complete_task, note=args.task_note)
        return

    if args.block_task:
        task_id, reason = args.block_task
        print_block_task(task_id, reason)
        return

    if args.next_task:
        print_next_task()
        return

    if args.queue_from_session is not None:
        print_queue_from_session(args.queue_from_session, limit=args.queue_task_limit)
        return

    if args.task_command_options is not None:
        print_task_command_options(args.task_command_options)
        return

    if args.execute_task is not None:
        print_execute_task(
            args.execute_task,
            command_index=args.task_command_index,
            dry_run=args.dry_run,
            complete_on_success=args.complete_on_success,
        )
        return

    if args.task_execution_history is not None:
        print_task_execution_history(args.task_execution_history)
        return

    if args.evaluate_task is not None:
        print_task_evaluation(args.evaluate_task, use_ai=(not args.no_ai_task_evaluation and ai_reviews_enabled()))
        return

    if args.list_task_evaluations:
        print_task_evaluations()
        return

    if args.show_task_evaluation is not None:
        print_saved_task_evaluation(args.show_task_evaluation, include_ai=not args.hide_task_evaluation_ai)
        return

    if args.apply_task_evaluation is not None:
        print_apply_task_evaluation(args.apply_task_evaluation, create_follow_up=args.task_evaluation_follow_up)
        return

    if args.guided_work_session is not None:
        print_guided_work_session(args.guided_work_session, full=args.guided_session_full)
        return

    if args.advance_work_session is not None:
        print_advance_guided_work_session(
            args.advance_work_session,
            command_index=args.task_command_index,
            dry_run=args.dry_run,
            use_ai=(not args.no_ai_task_evaluation and ai_reviews_enabled()),
            apply_guided_evaluation=args.apply_guided_evaluation,
            full=args.guided_session_full,
        )
        return

    if args.list_guided_sessions:
        print_guided_sessions()
        return

    if args.show_guided_session is not None:
        print_saved_guided_session(args.show_guided_session, full=args.guided_session_full)
        return

    if args.dev_cycle is not None:
        print_dev_cycle(args.dev_cycle, full=args.dev_cycle_full)
        return

    if args.advance_dev_cycle is not None:
        print_advance_dev_cycle(
            args.advance_dev_cycle,
            dry_run=args.dry_run,
            approve_apply=args.approve_dev_cycle_apply,
            apply_evaluation=args.apply_dev_cycle_evaluation,
            use_ai=(not args.no_ai_dev_cycle and ai_reviews_enabled()),
            full=args.dev_cycle_full,
        )
        return

    if args.list_dev_cycles:
        print_dev_cycles()
        return

    if args.show_dev_cycle is not None:
        print_saved_dev_cycle(args.show_dev_cycle, full=args.dev_cycle_full)
        return

    if args.dev_loop is not None:
        print_dev_loop(
            args.dev_loop,
            max_steps=args.dev_loop_steps,
            dry_run=args.dry_run,
            approve_apply=args.approve_dev_loop_actions,
            apply_evaluation=args.apply_dev_loop_evaluation,
            use_ai=(not args.no_ai_dev_loop and ai_reviews_enabled()),
            full=args.dev_loop_full,
        )
        return

    if args.list_dev_loops:
        print_dev_loops()
        return

    if args.show_dev_loop is not None:
        print_saved_dev_loop(args.show_dev_loop, full=args.dev_loop_full)
        return

    if args.approval_inbox:
        print_approval_inbox(status="pending", include_closed=False)
        return

    if args.list_approvals:
        print_approval_inbox(status=args.approval_filter_status, include_closed=True)
        return

    if args.show_approval is not None:
        print_approval(args.show_approval, full=args.approval_full)
        return

    if args.approve is not None:
        print_approve(args.approve, dry_run=args.dry_run)
        return

    if args.reject is not None:
        print_reject(args.reject, note=args.approval_note)
        return

    if args.goal_status:
        print_goal_status()
        return

    if args.list_goals:
        print_goal_list(
            status=args.goal_filter_status,
            project=args.goal_filter_project or args.goal_project,
            include_cancelled=not args.hide_cancelled_goals,
        )
        return

    if args.show_goal:
        print_goal_detail(args.show_goal, full=args.show_goal_full)
        return

    if args.add_goal_structured:
        print_add_goal(
            title=args.add_goal_structured,
            description=args.goal_description,
            priority=args.goal_priority,
            status=args.goal_initial_status,
            project=args.goal_project,
            next_action=args.goal_next_action,
        )
        return

    if args.set_goal_status:
        goal_id, status = args.set_goal_status
        print_set_goal_status(goal_id, status, note=args.goal_note)
        return

    if args.add_goal_note:
        goal_id, note = args.add_goal_note
        print_add_goal_note(goal_id, note)
        return

    if args.add_goal_action:
        goal_id, action = args.add_goal_action
        print_add_goal_next_action(goal_id, action)
        return

    if args.block_goal:
        goal_id, reason = args.block_goal
        print_block_goal(goal_id, reason)
        return

    if args.complete_goal:
        print_complete_goal(args.complete_goal, note=args.goal_note)
        return

    if args.search:
        print_keyword_search(args.search)
        return

    if args.semantic_search:
        print_semantic_search(args.semantic_search)
        return

    if args.rebuild_semantic_memory:
        rebuild_semantic_memory()
        return

    if args.project_status:
        print_project_status()
        return

    if args.add_project:
        project = add_project(
            name=args.add_project,
            path=args.project_path,
            language=args.project_language,
            description=args.project_description,
        )
        print(f"Added/set active project: {project.get('name')}")
        return

    if args.set_active_project:
        if set_active_project(args.set_active_project):
            print(f"Active project set to: {args.set_active_project}")
        else:
            print(f"Project not found: {args.set_active_project}")
        return

    active_project = get_active_project()
    active_name = active_project.get("name") if active_project else ""

    if args.add_project_goal:
        if active_name and add_project_item(active_name, "goals", args.add_project_goal):
            print(f"Added goal to {active_name}: {args.add_project_goal}")
        else:
            print("No active project found.")
        return

    if args.add_project_issue:
        if active_name and add_project_item(active_name, "known_issues", args.add_project_issue):
            print(f"Added known issue to {active_name}: {args.add_project_issue}")
        else:
            print("No active project found.")
        return

    if args.add_project_next_step:
        if active_name and add_project_item(active_name, "next_steps", args.add_project_next_step):
            print(f"Added next step to {active_name}: {args.add_project_next_step}")
        else:
            print("No active project found.")
        return

    if args.project_tree is not None:
        print_project_tree(args.project_tree or args.project_file_path)
        return

    if args.read_project_file:
        print_project_file(args.read_project_file)
        return

    if args.search_project_files:
        print_project_file_search(args.search_project_files, path=args.project_file_path)
        return

    if args.index_project is not None:
        result = index_project(relative_path=args.index_project or args.project_file_path)
        print(result.get("message"))
        print(f"Files indexed: {result.get('files_indexed')}")
        if result.get("index_file"):
            print(f"Index file: {result.get('index_file')}")
        return

    if args.project_index_summary:
        print_project_index_summary()
        return

    if args.search_project_index:
        print_project_index_search(args.search_project_index)
        return

    if args.review_project_file:
        print_code_review(args.review_project_file, use_ai=(not args.no_ai_review and ai_reviews_enabled()))
        return

    if args.suggest_patch:
        target_file, request = args.suggest_patch
        print_patch_suggestion(target_file, request, use_ai=True)
        return

    if args.list_patches:
        print_patch_list()
        return

    if args.show_patch:
        print_patch_proposal(args.show_patch, include_full_content=args.show_patch_full)
        return

    if args.apply_patch:
        print_apply_patch(args.apply_patch, dry_run=args.dry_run)
        return

    if args.list_applied_patches:
        print_applied_patches()
        return

    if args.rollback_patch:
        print_rollback_patch(args.rollback_patch, dry_run=args.dry_run)
        return

    if args.list_rolled_back_patches:
        print_rolled_back_patches()
        return

    if args.list_allowed_commands:
        print_allowed_commands()
        return

    if args.run_command:
        print_run_command(args.run_command, dry_run=args.dry_run)
        return

    if args.command_history:
        print_command_history()
        return

    if args.run_test_workflow is not None:
        print_test_workflow(
            patch_id=args.run_test_workflow,
            commands=args.test_command,
            dry_run=args.dry_run,
        )
        if args.auto_review:
            print()
            print("# Auto-review")
            print_test_review("latest", use_ai=(not args.no_ai_test_review and ai_reviews_enabled()))
        return

    if args.list_test_reports:
        print_test_reports()
        return

    if args.show_test_report:
        print_test_report(args.show_test_report, include_output=args.show_test_output)
        return

    if args.review_test_report:
        print_test_review(args.review_test_report, use_ai=(not args.no_ai_test_review and ai_reviews_enabled()))
        return

    if args.list_test_reviews:
        print_test_reviews()
        return

    if args.show_test_review:
        print_saved_test_review(args.show_test_review, include_ai=not args.hide_ai_review)
        return

    if args.self_improve:
        target_file, request = args.self_improve
        print_self_improvement(target_file, request, use_ai_review=(args.self_improve_ai_review and ai_reviews_enabled()))
        return

    if args.self_improve_apply:
        print_self_improvement_apply(
            args.self_improve_apply,
            commands=args.test_command,
            use_ai_review=(not args.no_ai_self_review and ai_reviews_enabled()),
            dry_run=args.dry_run,
        )
        return

    if args.list_self_improvements:
        print_self_improvement_runs()
        return

    if args.show_self_improvement:
        print_self_improvement_run(args.show_self_improvement, include_review=args.show_self_improvement_full)
        return

    if args.chat:
        run_chat()
        return

    if args.loop:
        run_loop(delay_seconds=args.delay)
        return

    # Default behavior: one cycle, so it does not trap beginners in an infinite loop immediately.
    run_cycle(verbose=True)


if __name__ == "__main__":
    main()
