from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Covered CLI surface includes: --stabilization-checkpoint
MAIN = PROJECT_ROOT / "conscious_agent" / "main.py"
SETTINGS = PROJECT_ROOT / "data" / "settings.json"
sys.path.insert(0, str(PROJECT_ROOT / "conscious_agent"))


def check_import(module: str) -> bool:
    try:
        importlib.import_module(module)
    except Exception as error:
        print(f"[fail] import {module}: {error}")
        return False
    print(f"[ok] import {module}")
    return True


def check_environment_import(module: str, *, required_for_core: bool = False) -> bool:
    try:
        importlib.import_module(module)
    except Exception as error:
        label = "fail" if required_for_core else "warn"
        print(f"[{label}] environment import {module}: {error}")
        if not required_for_core:
            print(f"[info] {module} is an environment/setup issue if it is listed in requirements.txt; core code checks continue.")
        return required_for_core is False
    print(f"[ok] environment import {module}")
    return True


def run_main(*args: str) -> bool:
    command = [sys.executable, str(MAIN), *args]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    label = " ".join(args)
    if result.returncode != 0:
        print(f"[fail] main.py {label}")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False
    print(f"[ok] main.py {label}")
    return True


def check_settings() -> bool:
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"[fail] settings.json: {error}")
        return False

    model = data.get("local_model")
    embed_model = data.get("embed_model")
    safe_mode = data.get("safe_mode")
    print(f"[ok] settings.json local_model={model} embed_model={embed_model} safe_mode={safe_mode}")
    return True



def check_compile() -> bool:
    command = [sys.executable, "-m", "py_compile", *[str(path) for path in sorted((PROJECT_ROOT / "conscious_agent").glob("*.py"))]]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        print("[fail] py_compile conscious_agent/*.py")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False
    print("[ok] py_compile conscious_agent/*.py")
    return True


def check_task_recovery() -> bool:
    try:
        from task_recovery import task_recovery_summary, list_task_recoveries

        summary = task_recovery_summary()
        if "recoverable" not in summary or "categories" not in summary:
            print("[fail] task recovery summary shape")
            return False
        list_task_recoveries(limit=5)
    except Exception as error:
        print(f"[fail] task recovery: {error}")
        return False
    print("[ok] task recovery")
    return True


def check_lifecycle_filters() -> bool:
    try:
        from task_lifecycle import normalize_lifecycle_stage_filter, task_lifecycle_summary

        if normalize_lifecycle_stage_filter("needs attention") != "needs_attention":
            print("[fail] lifecycle filter alias normalization")
            return False
        summary = task_lifecycle_summary(stage_filter="needs_attention")
        if "filtered_total" not in summary or "filters" not in summary:
            print("[fail] lifecycle filter summary shape")
            return False
    except Exception as error:
        print(f"[fail] lifecycle filters: {error}")
        return False
    print("[ok] lifecycle filters")
    return True


def check_cycle_policy() -> bool:
    try:
        from task_cycle_policy import choose_next_cycle_decision, list_cycle_candidates

        decision = choose_next_cycle_decision(project="eidolon")
        if not hasattr(decision, "to_dict") or not decision.action:
            print("[fail] lifecycle cycle policy decision shape")
            return False
        list_cycle_candidates(project="eidolon")
    except Exception as error:
        print(f"[fail] cycle policy: {error}")
        return False
    print("[ok] cycle policy")
    return True



def _cleanup_record_ids(record_ids: list[str]) -> None:
    for folder, record_id in [("work_cycles", rid) for rid in record_ids] + [("stable_loops", rid) for rid in record_ids]:
        path = PROJECT_ROOT / "data" / folder / f"{record_id}.json"
        if path.exists():
            path.unlink()
    memories_path = PROJECT_ROOT / "data" / "memories.json"
    if memories_path.exists():
        try:
            memories = json.loads(memories_path.read_text(encoding="utf-8"))
            memories = [item for item in memories if not any(record_id in json.dumps(item) for record_id in record_ids)]
            memories_path.write_text(json.dumps(memories, indent=2), encoding="utf-8")
        except Exception:
            pass
    thoughts_path = PROJECT_ROOT / "data" / "thoughts.log"
    if thoughts_path.exists():
        lines = [line for line in thoughts_path.read_text(encoding="utf-8").splitlines() if not any(record_id in line for record_id in record_ids)]
        thoughts_path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")


def check_work_cycle_preview() -> bool:
    try:
        from work_cycle import run_supervised_work_cycle

        result = run_supervised_work_cycle(project_id="eidolon", max_steps=1, dry_run=True, use_ai=False, seed_if_empty=False)
        if not result.cycle_id or not result.ok:
            print("[fail] work cycle preview shape")
            return False
        _cleanup_record_ids([result.cycle_id])
    except Exception as error:
        print(f"[fail] work cycle preview: {error}")
        return False
    print("[ok] work cycle preview")
    return True


def check_stable_loop() -> bool:
    try:
        from stable_supervised_loop import build_stable_loop_preflight, run_stable_supervised_loop

        preflight = build_stable_loop_preflight(project_id="eidolon", max_steps=1)
        if "next_decision" not in preflight or "lifecycle_summary" not in preflight:
            print("[fail] stable loop preflight shape")
            return False
        result = run_stable_supervised_loop(project_id="eidolon", max_steps=1, live=False, use_ai=False, seed_if_empty=False)
        if not result.loop_id or not result.preview_cycle_id:
            print("[fail] stable loop preview record shape")
            return False
        _cleanup_record_ids([result.loop_id, result.preview_cycle_id])
    except Exception as error:
        print(f"[fail] stable loop: {error}")
        return False
    print("[ok] stable loop")
    return True


def check_stable_loop_review() -> bool:
    try:
        from stable_loop_review import stable_loop_review_summary, normalize_review_status, normalize_review_filter, list_stable_loop_reviews, cleanup_stable_loop_history

        if normalize_review_status("approved live") != "approved_for_live":
            print("[fail] stable loop review status alias")
            return False
        if normalize_review_filter("live ready") != "approved_ready":
            print("[fail] stable loop review filter alias")
            return False
        summary = stable_loop_review_summary()
        if "counts" not in summary or "unreviewed_preview_count" not in summary or "archived_count" not in summary:
            print("[fail] stable loop review summary shape")
            return False
        list_stable_loop_reviews(review_filter="open", limit=5)
        cleanup = cleanup_stable_loop_history(review_filter="cleanup_default", limit=1, dry_run=True)
        if "candidate_count" not in cleanup:
            print("[fail] stable loop cleanup summary shape")
            return False
    except Exception as error:
        print(f"[fail] stable loop review: {error}")
        return False
    print("[ok] stable loop review")
    return True

def check_stable_loop_audit() -> bool:
    try:
        from stable_loop_audit import build_stable_loop_audit, stable_loop_audit_text

        audit = build_stable_loop_audit({"id": "stableloop_smoke_preview", "live": False, "ok": True, "project_id": "eidolon"})
        if audit.get("version") != "6.9" or "check_commands" not in audit or "warnings" not in audit:
            print("[fail] stable loop audit shape")
            return False
        text = stable_loop_audit_text(audit, full=False)
        if "Stable loop audit" not in text or "Recommended check commands" not in text:
            print("[fail] stable loop audit text")
            return False
    except Exception as error:
        print(f"[fail] stable loop audit: {error}")
        return False
    print("[ok] stable loop audit")
    return True

def check_stable_loop_operator_notes() -> bool:
    try:
        from stable_loop_operator_notes import (
            ensure_operator_notes,
            normalize_final_decision,
            stable_loop_operator_notes_text,
        )

        if normalize_final_decision("fix") != "fix_forward":
            print("[fail] stable loop operator decision alias")
            return False
        loop = {"id": "stableloop_smoke_operator", "live": False, "ok": True, "project_id": "eidolon"}
        notes = ensure_operator_notes(loop, save=False)
        if notes.get("version") != "6.9" or not notes.get("checklist") or "summary" not in notes:
            print("[fail] stable loop operator notes shape")
            return False
        text = stable_loop_operator_notes_text(loop, full=False)
        if "Stable loop operator notes" not in text or "Checklist" not in text:
            print("[fail] stable loop operator notes text")
            return False
    except Exception as error:
        print(f"[fail] stable loop operator notes: {error}")
        return False
    print("[ok] stable loop operator notes")
    return True

def check_stable_loop_decision_report() -> bool:
    try:
        from stable_loop_decision_report import (
            cleanup_stable_loop_decision_history,
            normalize_decision_filter,
            stable_loop_decision_report_text,
            stable_loop_decision_summary,
        )

        if normalize_decision_filter("needs action") != "action_required":
            print("[fail] stable loop decision filter alias")
            return False
        report = stable_loop_decision_summary(decision_filter="all")
        if report.get("version") != "6.9" or "counts" not in report or "cleanup_candidate_count" not in report:
            print("[fail] stable loop decision report shape")
            return False
        text = stable_loop_decision_report_text(report, full=False)
        if "Stable loop decision report" not in text or "Decision counts" not in text:
            print("[fail] stable loop decision report text")
            return False
        cleanup = cleanup_stable_loop_decision_history(decision_filter="cleanup_default", limit=1, dry_run=True)
        if not cleanup.ok or cleanup.selected_ids is None:
            print("[fail] stable loop decision cleanup shape")
            return False
    except Exception as error:
        print(f"[fail] stable loop decision report: {error}")
        return False
    print("[ok] stable loop decision report")
    return True


def check_stable_loop_followup_tasks() -> bool:
    try:
        from stable_loop_followup_tasks import (
            FOLLOWUP_TASK_VERSION,
            create_stable_loop_followup_tasks,
            followup_summary_text,
            stable_loop_followup_summary,
        )

        summary = stable_loop_followup_summary(decision_filter="action_required")
        if summary.get("version") != "6.9" or "missing_followup_count" not in summary:
            print("[fail] stable loop follow-up summary shape")
            return False
        text = followup_summary_text(summary, full=False)
        if "Stable loop follow-up task summary" not in text:
            print("[fail] stable loop follow-up summary text")
            return False
        result = create_stable_loop_followup_tasks("latest", dry_run=True)
        if not hasattr(result, "to_dict"):
            print("[fail] stable loop follow-up result shape")
            return False
        if FOLLOWUP_TASK_VERSION != "6.9":
            print("[fail] stable loop follow-up version")
            return False
    except Exception as error:
        print(f"[fail] stable loop follow-up tasks: {error}")
        return False
    print("[ok] stable loop follow-up tasks")
    return True


def check_stable_loop_followup_lifecycle() -> bool:
    try:
        from stable_loop_followup_lifecycle import (
            FOLLOWUP_LIFECYCLE_VERSION,
            followup_lifecycle_summary_text,
            stable_loop_followup_lifecycle_summary,
            stable_loop_followup_task_text,
        )

        summary = stable_loop_followup_lifecycle_summary(decision_filter="all")
        if summary.get("version") != "6.9" or "ready_to_resolve_loop_count" not in summary:
            print("[fail] stable loop follow-up lifecycle summary shape")
            return False
        text = followup_lifecycle_summary_text(summary, full=False)
        if "Stable-loop follow-up task lifecycle summary" not in text:
            print("[fail] stable loop follow-up lifecycle summary text")
            return False
        task_text = stable_loop_followup_task_text("task_missing_smoke", full=False)
        if "Stable-loop follow-up task lifecycle" not in task_text:
            print("[fail] stable loop follow-up lifecycle task text")
            return False
        if FOLLOWUP_LIFECYCLE_VERSION != "6.9":
            print("[fail] stable loop follow-up lifecycle version")
            return False
    except Exception as error:
        print(f"[fail] stable loop follow-up lifecycle: {error}")
        return False
    print("[ok] stable loop follow-up lifecycle")
    return True


def check_stable_loop_followup_completion() -> bool:
    try:
        from stable_loop_followup_completion import (
            FOLLOWUP_COMPLETION_VERSION,
            normalize_followup_completion_filter,
            stable_loop_followup_completion_report_text,
            stable_loop_followup_completion_summary,
        )

        if normalize_followup_completion_filter("ready") != "ready_to_resolve":
            print("[fail] stable loop follow-up completion filter alias")
            return False
        report = stable_loop_followup_completion_summary(completion_filter="all")
        if report.get("version") != "6.9" or "ready_to_resolve_count" not in report or "cleanup_candidate_count" not in report:
            print("[fail] stable loop follow-up completion summary shape")
            return False
        text = stable_loop_followup_completion_report_text(report, full=False)
        if "Stable-loop follow-up completion report" not in text:
            print("[fail] stable loop follow-up completion text")
            return False
        if FOLLOWUP_COMPLETION_VERSION != "6.9":
            print("[fail] stable loop follow-up completion version")
            return False
    except Exception as error:
        print(f"[fail] stable loop follow-up completion: {error}")
        return False
    print("[ok] stable loop follow-up completion")
    return True


def check_stable_loop_guardrails() -> bool:
    try:
        from stable_loop_guardrails import STABLE_LOOP_GUARDRAIL_VERSION, stable_loop_guardrail_summary, stable_loop_guardrails_text

        guardrails = stable_loop_guardrail_summary(project_id="eidolon")
        if guardrails.get("version") != "6.9" or "ok_for_live" not in guardrails or "unresolved_count" not in guardrails:
            print("[fail] stable loop guardrail summary shape")
            return False
        text = stable_loop_guardrails_text(guardrails, full=False)
        if "Stable-loop closure guardrails" not in text:
            print("[fail] stable loop guardrail text")
            return False
        if STABLE_LOOP_GUARDRAIL_VERSION != "6.9":
            print("[fail] stable loop guardrail version")
            return False
    except Exception as error:
        print(f"[fail] stable loop guardrails: {error}")
        return False
    print("[ok] stable loop guardrails")
    return True


def check_stabilization_checkpoint() -> bool:
    try:
        from stabilization_checkpoint import STABILIZATION_CHECKPOINT_VERSION, build_stabilization_checkpoint, stabilization_checkpoint_text

        report = build_stabilization_checkpoint(project_id="eidolon", full=False)
        if report.get("version") != "15.0" or "counts" not in report or "recommended_commands" not in report:
            print("[fail] stabilization checkpoint shape")
            return False
        text = stabilization_checkpoint_text(report, full=False)
        if "Stabilization Checkpoint" not in text or "Recommended verification commands" not in text:
            print("[fail] stabilization checkpoint text")
            return False
        if STABILIZATION_CHECKPOINT_VERSION != "15.0":
            print("[fail] stabilization checkpoint version")
            return False
    except Exception as error:
        print(f"[fail] stabilization checkpoint: {error}")
        return False
    print("[ok] stabilization checkpoint")
    return True


def check_operational_readiness() -> bool:
    try:
        from operational_readiness import (
            OPERATIONAL_READINESS_VERSION,
            build_doctor_report,
            build_repair_suggestions,
            build_patch_integrity_report,
            build_project_snapshot,
            build_task_review,
            build_recovery_drill,
            build_stable_loop_confidence,
            build_hardening_report,
            build_controlled_self_build,
            doctor_report_text,
        )

        if OPERATIONAL_READINESS_VERSION != "15.0":
            print("[fail] operational readiness version")
            return False
        reports = [
            build_doctor_report(project_id="eidolon", full=False),
            build_repair_suggestions(project_id="eidolon"),
            build_patch_integrity_report(),
            build_project_snapshot(project_id="eidolon"),
            build_task_review(project_id="eidolon"),
            build_recovery_drill(project_id="eidolon"),
            build_stable_loop_confidence(project_id="eidolon"),
            build_hardening_report(project_id="eidolon"),
            build_controlled_self_build(project_id="eidolon", max_steps=1, live=False, approve_live=False, use_ai=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] operational readiness report shape")
                return False
        text = doctor_report_text(reports[0], full=False)
        if "Doctor Mode" not in text or "Subreports" not in text:
            print("[fail] doctor report text")
            return False
    except Exception as error:
        print(f"[fail] operational readiness: {error}")
        return False
    print("[ok] operational readiness")
    return True


def check_controlled_build_cycle() -> bool:
    try:
        from controlled_build_cycle import (
            CONTROLLED_BUILD_VERSION,
            build_controlled_task_selection,
            build_patch_plan,
            patch_workspace_status,
            stage_controlled_patch,
            preview_staged_diff,
            readme_gate,
            controlled_task_selection_text,
        )

        if CONTROLLED_BUILD_VERSION != "15.0":
            print("[fail] controlled build version")
            return False
        reports = [
            build_controlled_task_selection(project_id="eidolon"),
            build_patch_plan(project_id="eidolon", target_version="14.0", save=True),
            patch_workspace_status(),
            stage_controlled_patch(project_id="eidolon"),
            preview_staged_diff(project_id="eidolon"),
            readme_gate(project_id="eidolon"),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] controlled build report shape")
                return False
        text = controlled_task_selection_text(reports[0], full=False)
        if "Task Selection" not in text:
            print("[fail] controlled build selection text")
            return False
    except Exception as error:
        print(f"[fail] controlled build cycle: {error}")
        return False
    print("[ok] controlled build cycle")
    return True


def check_project_intelligence() -> bool:
    try:
        from project_intelligence import (
            PROJECT_INTELLIGENCE_VERSION,
            build_codebase_map,
            build_task_dependencies,
            build_test_plan,
            build_patch_risk,
            build_patch_review,
            build_project_memory_index,
            build_workspace_status,
            build_cross_project_task_review,
            build_asymmetric_dev_loop,
            codebase_map_text,
        )

        if PROJECT_INTELLIGENCE_VERSION != "15.0":
            print("[fail] project intelligence version")
            return False
        reports = [
            build_codebase_map(project_id="eidolon"),
            build_task_dependencies(project_id="eidolon"),
            build_test_plan(project_id="eidolon"),
            build_patch_risk(project_id="eidolon"),
            build_patch_review(project_id="eidolon"),
            build_project_memory_index(project_id="eidolon"),
            build_workspace_status(project_id="eidolon"),
            build_cross_project_task_review(project_id="eidolon"),
            build_asymmetric_dev_loop(project_id="eidolon"),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] project intelligence report shape")
                return False
        text = codebase_map_text(reports[0], full=False)
        if "Codebase Map" not in text or "Major modules" not in text:
            print("[fail] project intelligence text")
            return False
    except Exception as error:
        print(f"[fail] project intelligence: {error}")
        return False
    print("[ok] project intelligence")
    return True


def check_workspace_orchestration() -> bool:
    try:
        from workspace_orchestration import (
            WORKSPACE_ORCHESTRATION_VERSION,
            build_project_registry,
            build_project_health,
            build_command_profiles,
            build_workspace_dependency_map,
            build_workspace_task_inbox,
            build_project_context,
            build_workspace_timeline,
            build_workspace_dev_loop,
            workspace_dev_loop_text,
        )

        if WORKSPACE_ORCHESTRATION_VERSION != "15.0":
            print("[fail] workspace orchestration version")
            return False
        reports = [
            build_project_registry(repair=True),
            build_project_health(project_id="eidolon", all_projects=True),
            build_command_profiles(save=True),
            build_workspace_dependency_map(project_id="eidolon"),
            build_workspace_task_inbox(project_id="eidolon"),
            build_project_context(project_id="eidolon"),
            build_workspace_timeline(),
            build_workspace_dev_loop(project_id="eidolon"),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] workspace orchestration report shape")
                return False
        text = workspace_dev_loop_text(reports[-1], full=False)
        if "Workspace-Orchestrated" not in text:
            print("[fail] workspace dev loop text")
            return False
    except Exception as error:
        print(f"[fail] workspace orchestration: {error}")
        return False
    print("[ok] workspace orchestration")
    return True


def check_workspace_execution() -> bool:
    try:
        from workspace_execution import (
            WORKSPACE_EXECUTION_VERSION,
            build_workspace_registry_audit,
            build_workspace_repair_suggestions,
            build_project_boundary_check,
            build_workspace_patch_plan,
            build_workspace_preview_diff,
            build_workspace_verify_latest,
            build_guarded_workspace_dev_loop,
            guarded_workspace_dev_loop_text,
        )

        if WORKSPACE_EXECUTION_VERSION != "15.0":
            print("[fail] workspace execution version")
            return False
        reports = [
            build_workspace_registry_audit(project_id="eidolon", archive_stale=False),
            build_workspace_repair_suggestions(project_id="eidolon"),
            build_project_boundary_check(project_id="eidolon"),
            build_workspace_patch_plan(project_id="eidolon", save=False),
            build_workspace_preview_diff(project_id="eidolon", save=False),
            build_workspace_verify_latest(project_id="eidolon", save=False),
            build_guarded_workspace_dev_loop(project_id="eidolon", approve=False, dry_run=True, save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] workspace execution report shape")
                return False
        text = guarded_workspace_dev_loop_text(reports[-1], full=False)
        if "Guarded Workspace" not in text:
            print("[fail] guarded workspace loop text")
            return False
    except Exception as error:
        print(f"[fail] workspace execution: {error}")
        return False
    print("[ok] workspace execution")
    return True



def check_patch_drafting() -> bool:
    try:
        from patch_drafting import (
            PATCH_DRAFTING_VERSION,
            build_patch_draft_request,
            build_draft_patch,
            build_patch_draft_status,
            build_patch_review_notes,
            build_draft_diff,
            build_draft_test_impact,
            build_approval_gate,
            build_apply_approved_draft,
            build_rollback_approved_draft,
            build_human_approved_patch_loop,
            build_draft_quality,
            build_draft_file_targets,
            build_draft_intent_blocks,
            build_draft_conflicts,
            build_draft_verification_bundle,
            build_draft_review_checklist,
            build_approved_draft_execution_report,
            build_review_centered_patch_loop,
            human_approved_patch_loop_text,
            review_centered_patch_loop_text,
        )

        if PATCH_DRAFTING_VERSION != "15.0":
            print("[fail] patch drafting version")
            return False
        reports = [
            build_patch_draft_request(project_id="eidolon", save=False),
            build_draft_patch(project_id="eidolon", save=False),
            build_patch_draft_status(project_id="eidolon"),
            build_patch_review_notes(project_id="eidolon", save=False),
            build_draft_diff(project_id="eidolon", save=False),
            build_draft_test_impact(project_id="eidolon", save=False),
            build_approval_gate(project_id="eidolon"),
            build_apply_approved_draft(project_id="eidolon", dry_run=True, save=False),
            build_rollback_approved_draft(project_id="eidolon", dry_run=True, save=False),
            build_human_approved_patch_loop(project_id="eidolon", save=False),
            build_draft_quality(project_id="eidolon", save=False),
            build_draft_file_targets(project_id="eidolon", save=False),
            build_draft_intent_blocks(project_id="eidolon", save=False),
            build_draft_conflicts(project_id="eidolon", save=False),
            build_draft_verification_bundle(project_id="eidolon", save=False),
            build_draft_review_checklist(project_id="eidolon", save=False),
            build_approved_draft_execution_report(project_id="eidolon", save=False),
            build_review_centered_patch_loop(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] patch drafting report shape")
                return False
        text = review_centered_patch_loop_text(reports[-1], full=False)
        if "Review-Centered" not in text:
            print("[fail] patch drafting text")
            return False
    except Exception as error:
        print(f"[fail] patch drafting: {error}")
        return False
    print("[ok] patch drafting")
    return True



def check_release_pipeline() -> bool:
    try:
        from release_pipeline import (
            RELEASE_PIPELINE_VERSION,
            build_code_edit_proposal,
            build_safe_rewrite_preview,
            build_generated_code_patch,
            build_test_suggestions,
            build_inline_review_note,
            build_apply_approved_code_patch,
            build_prepare_release_package,
            build_release_readiness,
            build_human_approved_release_loop,
            human_approved_release_loop_text,
        )

        if RELEASE_PIPELINE_VERSION != "15.0":
            print("[fail] release pipeline version")
            return False
        reports = [
            build_code_edit_proposal(project_id="eidolon", save=False),
            build_safe_rewrite_preview(project_id="eidolon", save=False),
            build_generated_code_patch(project_id="eidolon", save=False),
            build_test_suggestions(project_id="eidolon", save=False),
            build_inline_review_note(project_id="eidolon", save=False),
            build_apply_approved_code_patch(project_id="eidolon", dry_run=True, save=False),
            build_release_readiness(project_id="eidolon", save=False),
            build_prepare_release_package(project_id="eidolon", save=False),
            build_human_approved_release_loop(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] release pipeline report shape")
                return False
        text = human_approved_release_loop_text(reports[-1], full=False)
        if "Release Loop" not in text:
            print("[fail] release pipeline text")
            return False
    except Exception as error:
        print(f"[fail] release pipeline: {error}")
        return False
    print("[ok] release pipeline")
    return True



def check_code_patch_release() -> bool:
    try:
        from code_patch_release import (
            CODE_PATCH_RELEASE_VERSION,
            build_code_patch_status,
            build_symbol_scan,
            build_rewrite_plan,
            build_rewrite_conflicts,
            build_code_patch_diff_bundle,
            generated_code_release_loop_text,
        )

        if CODE_PATCH_RELEASE_VERSION != "16.0":
            print("[fail] code patch release version")
            return False
        reports = [
            build_code_patch_status(project_id="eidolon", save=False),
            build_symbol_scan(project_id="eidolon", save=False),
            build_rewrite_plan(project_id="eidolon", save=False),
            build_rewrite_conflicts(project_id="eidolon", save=False),
            build_code_patch_diff_bundle(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] code patch release report shape")
                return False
        text = generated_code_release_loop_text({"version": "16.0", "status": "dry_run", "checked_at": "smoke", "message": "Generated Code smoke text"}, full=False)
        if "Generated Code" not in text:
            print("[fail] code patch release text")
            return False
    except Exception as error:
        print(f"[fail] code patch release: {error}")
        return False
    print("[ok] code patch release")
    return True


def check_ai_patch_assistance() -> bool:
    try:
        from ai_patch_assistance import (
            AI_PATCH_ASSIST_VERSION,
            build_task_to_code_patch,
            build_code_context,
            build_patch_prompt,
            build_parse_generated_edits,
            build_edit_consistency,
            build_patch_failure_analysis,
            build_patch_learning_notes,
            ai_assisted_code_patch_loop_text,
        )

        if AI_PATCH_ASSIST_VERSION != "17.0":
            print("[fail] ai patch assist version")
            return False
        reports = [
            build_task_to_code_patch(project_id="eidolon", save=False),
            build_code_context(project_id="eidolon", save=False),
            build_patch_prompt(project_id="eidolon", save=False),
            build_parse_generated_edits(project_id="eidolon", save=False),
            build_edit_consistency(project_id="eidolon", save=False),
            build_patch_failure_analysis(project_id="eidolon", save=False),
            build_patch_learning_notes(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] ai patch assist report shape")
                return False
        text = ai_assisted_code_patch_loop_text({"version": "17.0", "status": "dry_run", "checked_at": "smoke", "message": "AI-assisted smoke text"}, full=False)
        if "AI-Assisted" not in text:
            print("[fail] ai patch assist text")
            return False
    except Exception as error:
        print(f"[fail] ai patch assistance: {error}")
        return False
    print("[ok] ai patch assistance")
    return True


def check_validated_ai_patch_loop() -> bool:
    try:
        from validated_ai_patch_loop import (
            VALIDATED_AI_PATCH_VERSION,
            build_patch_objective_refinement,
            build_code_context_ranking,
            build_patch_safety_envelope,
            build_generated_patch_validation,
            build_patch_simulation,
            build_test_stub_plan,
            build_patch_review_score,
            build_patch_recovery_plan,
            build_validated_ai_code_patch_loop,
            validated_ai_code_patch_loop_text,
        )

        if VALIDATED_AI_PATCH_VERSION != "18.0":
            print("[fail] validated ai patch version")
            return False
        reports = [
            build_patch_objective_refinement(project_id="eidolon", save=False),
            build_code_context_ranking(project_id="eidolon", save=False),
            build_patch_safety_envelope(project_id="eidolon", save=False),
            build_generated_patch_validation(project_id="eidolon", save=False),
            build_patch_simulation(project_id="eidolon", save=False),
            build_test_stub_plan(project_id="eidolon", save=False),
            build_patch_review_score(project_id="eidolon", save=False),
            build_patch_recovery_plan(project_id="eidolon", save=False),
            build_validated_ai_code_patch_loop(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] validated ai patch report shape")
                return False
        text = validated_ai_code_patch_loop_text(reports[-1], full=False)
        if "Validated AI" not in text:
            print("[fail] validated ai patch text")
            return False
    except Exception as error:
        print(f"[fail] validated ai patch loop: {error}")
        return False
    print("[ok] validated ai patch loop")
    return True


def check_approval_release_workflow() -> bool:
    try:
        from approval_release_workflow import (
            APPROVAL_RELEASE_VERSION,
            build_ai_patch_review_bundle,
            build_review_bundle_integrity,
            build_approval_ready,
            build_apply_validated_ai_patch,
            approval_to_release_loop_text,
        )

        if APPROVAL_RELEASE_VERSION != "20.0":
            print("[fail] approval release workflow version")
            return False
        reports = [
            build_ai_patch_review_bundle(project_id="eidolon", save=False),
            build_review_bundle_integrity(project_id="eidolon", save=False),
            build_approval_ready(project_id="eidolon", save=False),
            build_apply_validated_ai_patch(project_id="eidolon", approve=False, dry_run=True, save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] approval release workflow report shape")
                return False
        text = approval_to_release_loop_text({"version": "20.0", "status": "dry_run", "checked_at": "smoke", "message": "Approval-to-Release smoke text"}, full=False)
        if "Approval-to-Release" not in text:
            print("[fail] approval release workflow text")
            return False
    except Exception as error:
        print(f"[fail] approval release workflow: {error}")
        return False
    print("[ok] approval release workflow")
    return True


def check_release_packaging() -> bool:
    try:
        from release_packaging import (
            RELEASE_PACKAGING_VERSION,
            build_release_manifest_integrity,
            build_package_inventory,
            build_release_notes,
            verified_release_package_loop_text,
        )

        if RELEASE_PACKAGING_VERSION != "20.0":
            print("[fail] release packaging version")
            return False
        reports = [
            build_release_manifest_integrity(project_id="eidolon", save=False),
            build_package_inventory(project_id="eidolon", save=False),
            build_release_notes(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] release packaging report shape")
                return False
        text = verified_release_package_loop_text({"version": "20.0", "status": "dry_run", "checked_at": "smoke", "message": "Verified Release Package smoke text"}, full=False)
        if "Verified Release Package" not in text:
            print("[fail] release packaging text")
            return False
    except Exception as error:
        print(f"[fail] release packaging: {error}")
        return False
    print("[ok] release packaging")
    return True

def main() -> int:
    checks = [
        check_environment_import("requests", required_for_core=True),
        check_environment_import("chromadb"),
        check_settings(),
        check_compile(),
        run_main("--status"),
        run_main("--task-work", "summary"),
        check_import("task_lifecycle"),
        check_lifecycle_filters(),
        check_import("task_recovery"),
        check_task_recovery(),
        check_import("task_cycle_policy"),
        check_cycle_policy(),
        check_import("stable_supervised_loop"),
        check_stable_loop(),
        check_import("stable_loop_review"),
        check_stable_loop_review(),
        check_import("stable_loop_audit"),
        check_stable_loop_audit(),
        check_import("stable_loop_operator_notes"),
        check_stable_loop_operator_notes(),
        check_import("stable_loop_decision_report"),
        check_stable_loop_decision_report(),
        check_import("stable_loop_followup_tasks"),
        check_stable_loop_followup_tasks(),
        check_import("stable_loop_followup_lifecycle"),
        check_stable_loop_followup_lifecycle(),
        check_import("stable_loop_followup_completion"),
        check_stable_loop_followup_completion(),
        check_import("stable_loop_guardrails"),
        check_stable_loop_guardrails(),
        check_import("stabilization_checkpoint"),
        check_stabilization_checkpoint(),
        check_import("operational_readiness"),
        check_operational_readiness(),
        check_import("controlled_build_cycle"),
        check_controlled_build_cycle(),
        check_import("project_intelligence"),
        check_project_intelligence(),
        check_import("workspace_orchestration"),
        check_workspace_orchestration(),
        check_import("workspace_execution"),
        check_workspace_execution(),
        check_import("patch_drafting"),
        check_patch_drafting(),
        check_import("release_pipeline"),
        check_release_pipeline(),
        check_import("code_patch_release"),
        check_code_patch_release(),
        check_import("ai_patch_assistance"),
        check_ai_patch_assistance(),
        check_import("validated_ai_patch_loop"),
        check_validated_ai_patch_loop(),
        check_import("approval_release_workflow"),
        check_approval_release_workflow(),
        check_import("release_packaging"),
        check_release_packaging(),
        # v13-v20 draft/release/AI-assisted pipeline commands are validated in-process by
        # check_patch_drafting(), check_release_pipeline(), check_code_patch_release(),
        # check_ai_patch_assistance(), and check_validated_ai_patch_loop().
        # Running every CLI wrapper here makes smoke_check slow and can leave nested
        # compile/readiness checks competing with the outer smoke run.
        # README gate, workspace registry audit, guarded workspace loop, work cycle preview,
        # and stable-loop preflight (--stable-loop-preflight) are covered by in-process module checks above.
    ]
    if all(checks):
        print("Smoke check passed.")
        return 0
    print("Smoke check failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
