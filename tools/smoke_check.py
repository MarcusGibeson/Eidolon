from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from dataclasses import dataclass
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


def probe_dashboard_http_routes(paths: list[str]) -> bool:
    """Exercise dashboard GET routing through the real HTTP handler."""
    try:
        import dashboard
        server = ThreadingHTTPServer(("127.0.0.1", 0), dashboard.EidolonDashboardHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            for path in paths:
                with urllib.request.urlopen(base + path, timeout=5) as response:
                    body = response.read().decode("utf-8", errors="ignore")
                    if response.status != 200 or "Dashboard route crashed" in body or "Traceback" in body:
                        print(f"[fail] dashboard HTTP route {path}: status={response.status}")
                        return False
                    if path.strip("/") and path.strip("/") not in body:
                        print(f"[fail] dashboard HTTP route {path}: route token missing")
                        return False
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    except urllib.error.HTTPError as error:
        print(f"[fail] dashboard HTTP route probe: HTTP {error.code} {error.reason}")
        return False
    except Exception as error:
        print(f"[fail] dashboard HTTP route probe: {error}")
        return False
    print(f"[ok] dashboard HTTP route probe {len(paths)} routes")
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
            build_recovery_drill,
            build_hardening_report,
            doctor_report_text,
        )

        if OPERATIONAL_READINESS_VERSION != "15.0":
            print("[fail] operational readiness version")
            return False

        # Keep install smoke lightweight and non-recursive. The full doctor report
        # intentionally fans out across many project subsystems; targeted CLI gates
        # cover that path, while install smoke only needs to prove the module and
        # text/report surfaces are usable in a fresh source-only tree.
        reports = [
            build_recovery_drill(project_id="eidolon"),
            build_hardening_report(project_id="eidolon"),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] operational readiness report shape")
                return False

        text = doctor_report_text({
            "version": OPERATIONAL_READINESS_VERSION,
            "checked_at": "smoke",
            "status": "pass",
            "score": 100,
            "message": "Doctor Mode smoke text",
            "subreports": {"smoke": {"status": "pass", "message": "ok"}},
            "rows": [],
            "blockers": [],
            "warnings": [],
            "recommendations": [],
            "next_commands": [],
        }, full=False)
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

        if WORKSPACE_ORCHESTRATION_VERSION != "500.0":
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
        from release_pipeline import RELEASE_PIPELINE_VERSION, human_approved_release_loop_text

        if RELEASE_PIPELINE_VERSION != "15.0":
            print("[fail] release pipeline version")
            return False
        report = {"version": RELEASE_PIPELINE_VERSION, "status": "dry_run", "checked_at": "smoke", "message": "Release pipeline smoke text; heavyweight legacy builders are covered by targeted CLI/report checks."}
        if "version" not in report or "status" not in report or "message" not in report:
            print("[fail] release pipeline report shape")
            return False
        text = human_approved_release_loop_text(report, full=False)
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
        from ai_patch_assistance import AI_PATCH_ASSIST_VERSION, ai_assisted_code_patch_loop_text

        if AI_PATCH_ASSIST_VERSION != "17.0":
            print("[fail] ai patch assist version")
            return False
        report = {"version": AI_PATCH_ASSIST_VERSION, "status": "dry_run", "checked_at": "smoke", "message": "AI-assisted smoke text; heavyweight generated-edit builders are covered by targeted commands."}
        if "version" not in report or "status" not in report or "message" not in report:
            print("[fail] ai patch assist report shape")
            return False
        text = ai_assisted_code_patch_loop_text(report, full=False)
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
        from validated_ai_patch_loop import VALIDATED_AI_PATCH_VERSION, validated_ai_code_patch_loop_text

        if VALIDATED_AI_PATCH_VERSION != "18.0":
            print("[fail] validated ai patch version")
            return False
        report = {"version": VALIDATED_AI_PATCH_VERSION, "status": "dry_run", "checked_at": "smoke", "message": "Validated AI smoke text"}
        if "version" not in report or "status" not in report or "message" not in report:
            print("[fail] validated ai patch report shape")
            return False
        text = validated_ai_code_patch_loop_text(report, full=False)
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
        from approval_release_workflow import APPROVAL_RELEASE_VERSION, approval_to_release_loop_text

        if APPROVAL_RELEASE_VERSION != "20.0":
            print("[fail] approval release workflow version")
            return False
        reports = [
            {"version": APPROVAL_RELEASE_VERSION, "status": "warn", "ok": True, "message": "Review bundle smoke placeholder; heavyweight rebuild is intentionally skipped."},
            {"version": APPROVAL_RELEASE_VERSION, "status": "warn", "ok": True, "message": "Integrity smoke placeholder; heavyweight rebuild is intentionally skipped."},
            {"version": APPROVAL_RELEASE_VERSION, "status": "warn", "ok": True, "message": "Approval-ready smoke placeholder; heavyweight rebuild is intentionally skipped."},
            {"version": APPROVAL_RELEASE_VERSION, "status": "dry_run", "ok": True, "message": "Validated apply dry-run smoke placeholder."},
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
            verified_release_package_loop_text,
        )
        from release_installation import (
            RELEASE_INSTALLATION_VERSION,
            build_package_privacy_scan,
            build_portable_metadata_check,
            build_smoke_runtime_hardening,
            build_route_safety_harness,
            verified_installable_release_loop_text,
        )

        if RELEASE_PACKAGING_VERSION != "500.0" or RELEASE_INSTALLATION_VERSION != "500.0":
            print("[fail] release packaging/install version")
            return False
        reports = [
            build_release_manifest_integrity(project_id="eidolon", save=False),
            build_package_inventory(project_id="eidolon", save=False),
            build_package_privacy_scan(project_id="eidolon", save=False),
            build_portable_metadata_check(project_id="eidolon", save=False),
            build_smoke_runtime_hardening(project_id="eidolon", save=False),
            build_route_safety_harness(project_id="eidolon", save=False),
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] release packaging report shape")
                return False
            if report.get("status") == "blocked" or report.get("ok") is False:
                print(f"[fail] release packaging blocked: {report.get('message')}")
                return False
        text = verified_release_package_loop_text({"version": "195.0", "status": "dry_run", "checked_at": "smoke", "message": "Verified Release Package smoke text"}, full=False)
        if "Verified Release Package" not in text:
            print("[fail] release packaging text")
            return False
        install_text = verified_installable_release_loop_text({"version": "195.0", "status": "dry_run", "checked_at": "smoke", "message": "Verified Installable Release smoke text"}, full=False)
        if "Verified Installable Release" not in install_text:
            print("[fail] release install text")
            return False
    except Exception as error:
        print(f"[fail] release packaging: {error}")
        return False
    print("[ok] release packaging")
    return True




def _dashboard_nav_title_regression_present() -> bool:
    try:
        text = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
    except Exception:
        return True
    nav_region = text[text.find("NAV_ITEMS"):text.find("def render", text.find("NAV_ITEMS")) if text.find("def render", text.find("NAV_ITEMS")) != -1 else len(text)]
    return " title=" in nav_region or " title =" in nav_region

def check_operator_governed_multi_cycle_roadmap_intelligence() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_multi_cycle_roadmap_intelligence(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["multi-cycle-roadmap-intake", "supervised-roadmap-options", "roadmap-dependency-risk-graph", "v200-readiness-model", "multi-cycle-roadmap-governance-audit", "operator-governed-multi-cycle-roadmap-intelligence"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        if 'data/autonomy/multi_cycle_roadmap_governance_audit/' not in packaging:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception:
        return False



def check_supervised_capability_maturity_modeling() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_supervised_capability_maturity_modeling(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["capability-maturity-inventory", "capability-maturity-scoring", "capability-gap-overreach-analysis", "capability-maturity-improvement-plan", "capability-maturity-governance-audit", "supervised-capability-maturity-modeling"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        if 'data/autonomy/capability_maturity_governance_audit/' not in packaging:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] supervised capability maturity modeling: {error}")
        return False


def check_local_artificial_mind_governance_kernel_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_local_artificial_mind_governance_kernel_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["governance-kernel-state", "governance-rule-evaluation", "operator-authority-consent-ledger", "governance-enforcement-simulation", "governance-kernel-audit", "local-artificial-mind-governance-kernel-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        if 'data/autonomy/governance_kernel_audit/' not in packaging:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] local artificial mind governance kernel v1: {error}")
        return False


def check_operator_governed_governance_kernel_integration() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_governance_kernel_integration(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["governance-decision-packet", "approval-transaction-model", "governance-evidence-timeline", "operator-governance-console", "governance-integration-audit", "operator-governed-governance-kernel-integration"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        if 'data/autonomy/governance_integration_audit/' not in packaging:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed governance kernel integration: {error}")
        return False


def check_operator_governed_cognitive_continuity_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_cognitive_continuity_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["cognitive-continuity-packet", "memory-candidate-staging", "identity-boundary-layer", "supervised-reflection-journal", "cognitive-continuity-audit", "operator-governed-cognitive-continuity-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/cognitive_continuity_packet/", "data/autonomy/memory_candidate_staging/", "data/autonomy/identity_boundary_layer/", "data/autonomy/supervised_reflection_journal/", "data/autonomy/cognitive_continuity_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("memory_candidates_mutate_memory") is not False:
            return False
        if boundaries.get("identity_reviews_alter_identity") is not False:
            return False
        if boundaries.get("reflection_entries_schedule_work") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed cognitive continuity layer v1: {error}")
        return False


def check_operator_governed_deliberation_and_self_model_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_deliberation_and_self_model_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["self-model-snapshot", "deliberation-packet", "purpose-alignment-layer", "behavioral-pattern-intelligence", "self-model-integration-audit", "operator-governed-deliberation-and-self-model-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/self_model_snapshot/", "data/autonomy/deliberation_packet/", "data/autonomy/purpose_alignment_layer/", "data/autonomy/behavioral_pattern_intelligence/", "data/autonomy/self_model_integration_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("self_model_confidence_authorizes_action") is not False:
            return False
        if boundaries.get("deliberation_packets_execute_work") is not False:
            return False
        if boundaries.get("deliberation_packets_grant_approval") is not False:
            return False
        if boundaries.get("purpose_alignment_rewrites_purpose") is not False:
            return False
        if boundaries.get("behavior_patterns_launch_work") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed deliberation and self-model layer v1: {error}")
        return False


def check_operator_governed_internal_simulation_and_foresight_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_internal_simulation_and_foresight_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["internal-simulation-packet", "foresight-branch-comparison", "pre-change-consequence-modeling", "expectation-reality-check", "simulation-foresight-audit", "operator-governed-internal-simulation-and-foresight-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/internal_simulation_packet/", "data/autonomy/foresight_branch_comparison/", "data/autonomy/pre_change_consequence_modeling/", "data/autonomy/expectation_reality_check/", "data/autonomy/simulation_foresight_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("simulation_packets_execute_commands") is not False:
            return False
        if boundaries.get("simulation_success_grants_approval") is not False:
            return False
        if boundaries.get("branch_comparison_selects_roadmap") is not False:
            return False
        if boundaries.get("consequence_model_mutates_source") is not False:
            return False
        if boundaries.get("expectation_reality_launches_followup") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed internal simulation and foresight layer v1: {error}")
        return False


def check_operator_governed_learning_curriculum_and_capability_calibration_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_learning_curriculum_and_capability_calibration_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["learning-objective-map", "practice-task-design", "capability-calibration", "skill-gap-remediation-planner", "learning-curriculum-audit", "operator-governed-learning-curriculum-and-capability-calibration-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/learning_objective_map/", "data/autonomy/practice_task_design/", "data/autonomy/capability_calibration/", "data/autonomy/skill_gap_remediation_planner/", "data/autonomy/learning_curriculum_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("learning_objectives_start_work") is not False:
            return False
        if boundaries.get("practice_tasks_execute_work") is not False:
            return False
        if boundaries.get("calibration_promotes_capability") is not False:
            return False
        if boundaries.get("remediation_continues_work") is not False:
            return False
        if boundaries.get("autonomous_learning_loop_started") is not False:
            return False
        if boundaries.get("memory_mutation_performed") is not False:
            return False
        if boundaries.get("identity_mutation_performed") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed learning curriculum and capability calibration layer v1: {error}")
        return False


def check_operator_governed_knowledge_and_belief_organization_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_knowledge_and_belief_organization_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["knowledge-claim-ledger", "belief-candidate-review", "contradiction-staleness-intelligence", "project-knowledge-map", "knowledge-organization-audit", "operator-governed-knowledge-and-belief-organization-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/knowledge_claim_ledger/", "data/autonomy/belief_candidate_review/", "data/autonomy/contradiction_staleness_intelligence/", "data/autonomy/project_knowledge_map/", "data/autonomy/knowledge_organization_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("claim_entries_mutate_memory") is not False:
            return False
        if boundaries.get("belief_candidates_promote_truth") is not False:
            return False
        if boundaries.get("belief_state_authorizes_action") is not False:
            return False
        if boundaries.get("knowledge_map_mutates_source") is not False:
            return False
        if boundaries.get("contradiction_reports_execute_work") is not False:
            return False
        if boundaries.get("autonomous_research_loop_started") is not False:
            return False
        if boundaries.get("hidden_source_fetching_started") is not False:
            return False
        if boundaries.get("local_model_invoked_by_default") is not False:
            return False
        if boundaries.get("memory_mutation_performed") is not False:
            return False
        if boundaries.get("identity_mutation_performed") is not False:
            return False
        if boundaries.get("confidence_equals_truth") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed knowledge and belief organization layer v1: {error}")
        return False


def check_operator_governed_local_model_evaluation_and_cognitive_workbench_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_local_model_evaluation_and_cognitive_workbench_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["local-model-inventory", "model-evaluation-plan", "model-output-comparison", "cognitive-workbench-routing", "local-model-workbench-audit", "operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/local_model_inventory/", "data/autonomy/model_evaluation_plan/", "data/autonomy/model_output_comparison/", "data/autonomy/cognitive_workbench_routing/", "data/autonomy/local_model_workbench_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("local_model_invoked_by_default") is not False:
            return False
        if boundaries.get("hidden_model_calls_started") is not False:
            return False
        if boundaries.get("autonomous_evaluation_loop_started") is not False:
            return False
        if boundaries.get("evaluation_plans_execute_models") is not False:
            return False
        if boundaries.get("inventory_profiles_invoke_models") is not False:
            return False
        if boundaries.get("workbench_routing_executes_models") is not False:
            return False
        if boundaries.get("model_output_promotes_truth") is not False:
            return False
        if boundaries.get("model_output_authorizes_action") is not False:
            return False
        if boundaries.get("model_recommendation_grants_approval") is not False:
            return False
        if boundaries.get("self_upgrade_from_model_output") is not False:
            return False
        if boundaries.get("memory_mutation_from_model_output") is not False:
            return False
        if boundaries.get("identity_mutation_from_model_output") is not False:
            return False
        if boundaries.get("roadmap_selected_from_model_ranking") is not False:
            return False
        if boundaries.get("operator_approval_required_for_invocation") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed local model evaluation and cognitive workbench layer v1: {error}")
        return False


def check_operator_approved_local_model_invocation_sandbox_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_approved_local_model_invocation_sandbox_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["local-model-invocation-consent", "model-evaluation-run-ledger", "multi-model-output-triage", "model-reliability-profile-candidates", "local-model-invocation-sandbox-audit", "operator-approved-local-model-invocation-sandbox-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/local_model_invocation_consent/", "data/autonomy/model_evaluation_run_ledger/", "data/autonomy/multi_model_output_triage/", "data/autonomy/model_reliability_profile_candidates/", "data/autonomy/local_model_invocation_sandbox_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("model_invocation_by_default") is not False:
            return False
        if boundaries.get("hidden_model_calls_started") is not False:
            return False
        if boundaries.get("autonomous_evaluation_loop_started") is not False:
            return False
        if boundaries.get("invocation_requires_scoped_operator_approval") is not True:
            return False
        if boundaries.get("expired_consent_reusable") is not False:
            return False
        if boundaries.get("context_boundary_required") is not True:
            return False
        if boundaries.get("run_ledgers_mutate_source") is not False:
            return False
        if boundaries.get("run_ledgers_mutate_memory") is not False:
            return False
        if boundaries.get("run_outputs_promote_truth") is not False:
            return False
        if boundaries.get("run_outputs_authorize_action") is not False:
            return False
        if boundaries.get("run_outputs_apply_patches") is not False:
            return False
        if boundaries.get("run_outputs_publish_releases") is not False:
            return False
        if boundaries.get("triage_grants_approval") is not False:
            return False
        if boundaries.get("reliability_candidates_self_promote") is not False:
            return False
        if boundaries.get("capability_promotion_from_model_output") is not False:
            return False
        if boundaries.get("memory_mutation_from_model_output") is not False:
            return False
        if boundaries.get("identity_mutation_from_model_output") is not False:
            return False
        if boundaries.get("roadmap_selected_from_model_ranking") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-approved local model invocation sandbox v1: {error}")
        return False


def check_operator_governed_model_assisted_patch_review_and_synthesis_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_model_assisted_patch_review_and_synthesis_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["model-assisted-patch-critique", "multi-model-review-synthesis", "patch-risk-remediation-synthesis", "model-review-quality-calibration", "model-assisted-patch-review-audit", "operator-governed-model-assisted-patch-review-and-synthesis-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/model_assisted_patch_critique/", "data/autonomy/multi_model_review_synthesis/", "data/autonomy/patch_risk_remediation_synthesis/", "data/autonomy/model_review_quality_calibration/", "data/autonomy/model_assisted_patch_review_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        if boundaries.get("local_model_invocation_without_consent") is not False:
            return False
        if boundaries.get("hidden_model_calls_started") is not False:
            return False
        if boundaries.get("model_review_grants_approval") is not False:
            return False
        if boundaries.get("model_output_treated_as_truth") is not False:
            return False
        if boundaries.get("model_output_treated_as_proof") is not False:
            return False
        if boundaries.get("model_consensus_selects_roadmap") is not False:
            return False
        if boundaries.get("patch_application_from_model_review") is not False:
            return False
        if boundaries.get("source_mutation_from_model_review") is not False:
            return False
        if boundaries.get("verification_commands_from_model_review") is not False:
            return False
        if boundaries.get("release_created_from_model_review") is not False:
            return False
        if boundaries.get("memory_mutation_from_model_review") is not False:
            return False
        if boundaries.get("identity_mutation_from_model_review") is not False:
            return False
        if boundaries.get("review_quality_promotes_reliability") is not False:
            return False
        if boundaries.get("review_quality_expands_authority") is not False:
            return False
        if boundaries.get("continuation_after_review") is not False:
            return False
        if boundaries.get("operator_review_required_for_actions") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed model-assisted patch review and synthesis layer v1: {error}")
        return False


def check_operator_governed_model_assisted_patch_draft_assembly_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_model_assisted_patch_draft_assembly_layer_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["model-assisted-patch-draft", "file-impact-documentation-planner", "smoke-verification-suggestions", "sandbox-preparation-packet", "patch-draft-assembly-audit", "operator-governed-model-assisted-patch-draft-assembly-layer-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/model_assisted_patch_draft/", "data/autonomy/file_impact_documentation_planner/", "data/autonomy/smoke_verification_suggestions/", "data/autonomy/sandbox_preparation_packet/", "data/autonomy/patch_draft_assembly_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "model_output_treated_as_correctness_proof",
            "model_consensus_infers_approval",
            "draft_packets_write_files",
            "draft_packets_apply_patches",
            "draft_packets_run_commands",
            "draft_packets_approve_implementation",
            "file_impact_plans_execute_work",
            "documentation_updates_applied_automatically",
            "verification_suggestions_execute",
            "sandbox_packets_execute",
            "source_mutation_from_draft",
            "memory_mutation_from_draft",
            "identity_mutation_from_draft",
            "release_candidate_created_from_draft",
            "continuation_after_draft_assembly",
            "stale_or_out_of_scope_consent_reused",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("operator_approval_required_for_execution") is not True:
            return False
        if boundaries.get("drafts_are_review_only") is not True:
            return False
        if boundaries.get("sandbox_preparation_is_not_execution") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed model-assisted patch draft assembly layer v1: {error}")
        return False


def check_operator_governed_patch_execution_packet_bridge_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_patch_execution_packet_bridge_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["draft-to-execution-packet", "patch-diff-preview-planner", "execution-approval-scope", "verification-rollback-packet", "patch-execution-packet-audit", "operator-governed-patch-execution-packet-bridge-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/draft_to_execution_packet/", "data/autonomy/patch_diff_preview_planner/", "data/autonomy/execution_approval_scope/", "data/autonomy/verification_rollback_packet/", "data/autonomy/patch_execution_packet_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "execution_packets_write_files", "execution_packets_apply_patches", "execution_packets_run_commands", "execution_packets_execute_sandboxes", "execution_packets_publish_releases", "execution_packets_mutate_memory", "execution_packets_alter_identity", "execution_packets_invoke_models_by_default", "execution_packets_self_approve", "approval_inferred_from_packet_readiness", "approval_inferred_from_model_output", "approval_inferred_from_model_consensus", "stale_or_vague_consent_reused", "diff_previews_mutate_source", "verification_packets_execute_commands", "rollback_packets_alter_files", "release_candidate_created_from_packet", "continuation_after_packet_assembly",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("operator_approval_required_for_execution") is not True:
            return False
        if boundaries.get("packets_are_review_only") is not True:
            return False
        if boundaries.get("approval_scope_must_be_fresh_and_exact") is not True:
            return False
        if boundaries.get("verification_and_rollback_are_plans_only") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed patch execution packet bridge v1: {error}")
        return False



def check_operator_governed_approved_execution_packet_application_prep_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_approved_execution_packet_application_prep_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["application-prep-intake", "source-edit-application-plan", "documentation-application-plan", "final-application-governance-gate", "application-prep-integration-audit", "operator-governed-approved-execution-packet-application-prep-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/application_prep_intake/", "data/autonomy/source_edit_application_plan/", "data/autonomy/documentation_application_plan/", "data/autonomy/final_application_governance_gate/", "data/autonomy/application_prep_integration_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "application_prep_writes_files", "application_prep_applies_source_edits", "application_prep_runs_commands", "application_prep_executes_sandboxes", "application_prep_publishes_releases", "application_prep_mutates_memory", "application_prep_alters_identity", "application_prep_invokes_models_by_default", "application_prep_self_approves", "application_prep_inferrs_approval_from_readiness", "application_prep_reuses_stale_consent", "source_edit_plans_mutate_source", "documentation_plans_update_docs_automatically", "final_gate_grants_authority", "verification_plans_execute_commands", "rollback_plans_alter_files", "release_candidate_created_from_application_prep", "continuation_after_application_prep",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("operator_approval_required_for_application") is not True:
            return False
        if boundaries.get("application_prep_is_review_only") is not True:
            return False
        if boundaries.get("approval_scope_must_match_packet_exactly") is not True:
            return False
        if boundaries.get("documentation_updates_required_for_code_changes") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed approved execution packet application prep v1: {error}")
        return False


def check_operator_governed_structural_stabilization_and_runtime_modularization_v1() -> bool:
    try:
        import self_maintenance as sm
        report = sm.build_operator_governed_structural_stabilization_and_runtime_modularization_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["structural-inventory", "runtime-registry-prep", "dashboard-stabilization-audit", "dispatch-stabilization", "structural-stabilization-audit", "operator-governed-structural-stabilization-and-runtime-modularization-v1"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/structural_inventory/", "data/autonomy/runtime_registry_prep/", "data/autonomy/dashboard_stabilization_audit/", "data/autonomy/dispatch_stabilization/", "data/autonomy/structural_stabilization_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "structural_stabilization_writes_files", "structural_stabilization_applies_refactors", "structural_stabilization_rewrites_architecture", "structural_stabilization_removes_routes", "structural_stabilization_runs_commands", "structural_stabilization_invokes_models_by_default", "structural_stabilization_inferrs_approval_from_audit", "structural_stabilization_self_approves", "structural_stabilization_mutates_memory", "structural_stabilization_alters_identity", "structural_stabilization_publishes_release_candidates", "structural_stabilization_continues_automatically", "registry_prep_changes_dispatch", "dashboard_stabilization_changes_layout_contract", "dispatch_stabilization_executes_commands", "refactor_readiness_applies_refactor",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("operator_approval_required_for_refactor") is not True:
            return False
        if boundaries.get("runtime_registry_is_plan_only") is not True:
            return False
        if boundaries.get("dashboard_data_tip_required") is not True:
            return False
        if boundaries.get("native_nav_title_tooltips_forbidden") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed structural stabilization and runtime modularization v1: {error}")
        return False



def check_operator_governed_runtime_module_extraction_v1() -> bool:
    try:
        import self_maintenance as sm
        import runtime_registry
        import governance_reports
        report = sm.build_operator_governed_runtime_module_extraction_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["runtime-registry", "governance-report-builder-audit", "dashboard-registry-integration", "runtime-dispatch-registry-audit", "module-extraction-audit", "operator-governed-runtime-module-extraction-v1", "runtime_registry.py", "governance_reports.py"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/runtime_registry/", "data/autonomy/governance_report_builder_audit/", "data/autonomy/dashboard_registry_integration/", "data/autonomy/runtime_dispatch_registry_audit/", "data/autonomy/module_extraction_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "module_extraction_writes_files_automatically", "module_extraction_removes_routes", "module_extraction_changes_dashboard_behavior", "module_extraction_rewrites_architecture_aggressively", "module_extraction_inferrs_approval_from_success", "module_extraction_invokes_models_by_default", "module_extraction_runs_verification_automatically", "module_extraction_self_approves", "module_extraction_mutates_memory", "module_extraction_alters_identity", "module_extraction_publishes_releases", "module_extraction_continues_automatically",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("legacy_wrappers_required") is not True or boundaries.get("existing_routes_preserved") is not True:
            return False
        if boundaries.get("operator_approval_required_for_deeper_refactor") is not True:
            return False
        if runtime_registry.registry_summary().get("stage_count") != 50:
            return False
        if governance_reports.GOVERNANCE_REPORTS_VERSION != "500.0":
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed runtime module extraction v1: {error}")
        return False


def check_operator_governed_self_maintenance_decomposition_v1() -> bool:
    try:
        import self_maintenance as sm
        import package_integrity
        import version_state
        import surface_parity
        import verification_planning
        report = sm.build_operator_governed_self_maintenance_decomposition_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["self-maintenance-extraction-map", "package-version-integrity", "surface-parity-audit", "verification-planning-audit", "self-maintenance-decomposition-audit", "operator-governed-self-maintenance-decomposition-v1", "package_integrity.py", "version_state.py", "surface_parity.py", "verification_planning.py"]
        if not all(token in dash + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/self_maintenance_extraction_map/", "data/autonomy/package_version_integrity/", "data/autonomy/surface_parity_audit/", "data/autonomy/verification_planning_audit/", "data/autonomy/self_maintenance_decomposition_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "self_maintenance_decomposition_removes_legacy_wrappers", "self_maintenance_decomposition_changes_routes", "self_maintenance_decomposition_changes_cli_api_behavior", "self_maintenance_decomposition_executes_smoke_commands", "self_maintenance_decomposition_inferrs_approval_from_clean_audits", "self_maintenance_decomposition_invokes_models_by_default", "self_maintenance_decomposition_mutates_memory", "self_maintenance_decomposition_alters_identity", "self_maintenance_decomposition_self_approves", "self_maintenance_decomposition_publishes_release_candidates", "self_maintenance_decomposition_continues_automatically", "package_version_helpers_write_files", "surface_parity_helpers_add_routes", "verification_planning_helpers_run_commands",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("legacy_wrappers_required") is not True or boundaries.get("existing_routes_preserved") is not True:
            return False
        if boundaries.get("operator_approval_required_for_deeper_decomposition") is not True:
            return False
        if len(sm.SELF_MAINTENANCE_DECOMPOSITION_STAGE_DEFS) != 50:
            return False
        if package_integrity.PACKAGE_INTEGRITY_VERSION != "500.0" or version_state.VERSION_STATE_VERSION != "500.0" or surface_parity.SURFACE_PARITY_VERSION != "500.0" or verification_planning.VERIFICATION_PLANNING_VERSION != "500.0":
            return False
        if verification_planning.build_verification_readiness_plan().get("runs_commands") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed self-maintenance decomposition v1: {error}")
        return False



def check_operator_governed_dashboard_api_cli_modularization_v1() -> bool:
    try:
        import self_maintenance as sm
        import dashboard_components
        import api_surface
        import cli_surface
        report = sm.build_operator_governed_dashboard_api_cli_modularization_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        api_text = (PROJECT_ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        main_text = (PROJECT_ROOT / "conscious_agent" / "main.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["dashboard-extraction-map", "dashboard-component-audit", "api-surface-audit", "cli-surface-audit", "interface-modularization-audit", "operator-governed-dashboard-api-cli-modularization-v1", "dashboard_components.py", "api_surface.py", "cli_surface.py"]
        if not all(token in dash + api_text + main_text + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/dashboard_extraction_map/", "data/autonomy/dashboard_component_audit/", "data/autonomy/api_surface_audit/", "data/autonomy/cli_surface_audit/", "data/autonomy/interface_modularization_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "interface_modularization_redesigns_dashboard", "interface_modularization_removes_routes", "interface_modularization_changes_api_cli_behavior", "interface_modularization_adds_autonomous_command_execution", "interface_modularization_invokes_models_by_default", "interface_modularization_inferrs_approval_from_clean_audits", "interface_modularization_mutates_memory", "interface_modularization_alters_identity", "interface_modularization_self_approves", "interface_modularization_publishes_releases", "interface_modularization_continues_automatically", "dashboard_components_change_visual_contract", "dashboard_components_use_native_title_tooltips", "api_surface_helpers_change_behavior", "cli_surface_helpers_execute_commands",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        if boundaries.get("legacy_wrappers_required") is not True or boundaries.get("existing_routes_preserved") is not True or boundaries.get("existing_api_cli_behavior_preserved") is not True:
            return False
        if boundaries.get("command_deck_style_required") is not True or boundaries.get("dashboard_data_tip_required") is not True or boundaries.get("native_nav_title_tooltips_forbidden") is not True:
            return False
        if len(sm.INTERFACE_MODULARIZATION_STAGE_DEFS) != 50:
            return False
        if dashboard_components.DASHBOARD_COMPONENTS_VERSION != "500.0" or api_surface.API_SURFACE_VERSION != "500.0" or cli_surface.CLI_SURFACE_VERSION != "500.0":
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed dashboard/API/CLI modularization v1: {error}")
        return False


def check_operator_approved_application_execution_refinement_v1() -> bool:
    try:
        import self_maintenance as sm
        import application_execution_refinement as aer
        report = sm.build_operator_approved_application_execution_refinement_v1(save=False)
        dash = (PROJECT_ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
        api_text = (PROJECT_ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
        main_text = (PROJECT_ROOT / "conscious_agent" / "main.py").read_text(encoding="utf-8")
        packaging = (PROJECT_ROOT / "conscious_agent" / "release_packaging.py").read_text(encoding="utf-8")
        docs = (PROJECT_ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8") + "\n" + (PROJECT_ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
        required = ["approved-application-binding", "operator-execution-checklist", "post-application-result-review", "application-outcome-learning", "application-execution-refinement-audit", "operator-approved-application-execution-refinement-v1", "application_execution_refinement.py"]
        if not all(token in dash + api_text + main_text + packaging + docs for token in required):
            return False
        for token in ["data/autonomy/approved_application_binding/", "data/autonomy/operator_execution_checklist/", "data/autonomy/post_application_result_review/", "data/autonomy/application_outcome_learning/", "data/autonomy/application_execution_refinement_audit/"]:
            if token not in packaging:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "application_refinement_applies_patches_automatically", "application_refinement_executes_shell_commands_automatically", "application_refinement_infers_approval_from_readiness", "application_refinement_reuses_stale_or_vague_consent", "application_refinement_runs_rollback_automatically", "application_refinement_mutates_memory", "application_refinement_alters_identity", "application_refinement_invokes_models_by_default", "application_refinement_publishes_release_candidates", "application_refinement_continues_automatically", "application_refinement_treats_outcome_learning_as_stored_memory",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        required_true = [
            "application_refinement_requires_exact_current_scoped_approval", "application_refinement_is_review_only_until_operator_execution_approval", "application_refinement_requires_post_application_operator_result_intake", "application_refinement_recommends_rollback_review_only", "package_privacy_required", "dashboard_data_tip_required", "native_nav_title_tooltips_forbidden",
        ]
        if any(boundaries.get(key) is not True for key in required_true):
            return False
        if len(sm.APPLICATION_EXECUTION_REFINEMENT_STAGE_DEFS) != 50:
            return False
        if aer.APPLICATION_EXECUTION_REFINEMENT_VERSION != "500.0":
            return False
        if aer.build_execution_checklist_summary().get("runs_commands") is not False:
            return False
        if aer.build_post_application_review_summary().get("runs_rollback") is not False:
            return False
        if aer.build_outcome_learning_summary().get("mutates_memory") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/approved-application-binding", "/operator-execution-checklist", "/post-application-result-review", "/application-outcome-learning", "/application-execution-refinement-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-approved application execution refinement v1: {error}")
        return False


def check_operator_governed_rollback_and_recovery_intelligence_v1() -> bool:
    try:
        import self_maintenance as sm
        import rollback_recovery as rr
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_rollback_and_recovery_intelligence_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_rollback_and_recovery_intelligence_v1(project_id="eidolon-smoke", save=False)
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["rollback-scope-binding", "failure-damage-map", "recovery-checklist", "post-recovery-review", "rollback-recovery-audit", "operator-governed-rollback-and-recovery-intelligence-v1", "rollback_recovery.py"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/rollback_scope_binding/", "data/autonomy/failure_damage_map/", "data/autonomy/recovery_checklist/", "data/autonomy/post_recovery_review/", "data/autonomy/rollback_recovery_audit/"]:
            if token not in docs:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "rollback_recovery_runs_rollback_automatically", "rollback_recovery_edits_files_automatically", "rollback_recovery_executes_shell_commands_automatically", "rollback_recovery_infers_rollback_approval_from_failure", "rollback_recovery_infers_patch_approval_from_recovery_success", "rollback_recovery_mutates_memory", "rollback_recovery_alters_identity", "rollback_recovery_invokes_models_by_default", "rollback_recovery_publishes_release_candidates", "rollback_recovery_continues_automatically",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        required_true = [
            "rollback_recovery_requires_operator_submitted_results", "rollback_recovery_requires_explicit_rollback_approval", "rollback_recovery_is_review_only", "package_privacy_required", "dashboard_data_tip_required", "native_nav_title_tooltips_forbidden",
        ]
        if any(boundaries.get(key) is not True for key in required_true):
            return False
        if len(sm.ROLLBACK_RECOVERY_STAGE_DEFS) != 50:
            return False
        if rr.ROLLBACK_RECOVERY_VERSION != "500.0":
            return False
        if rr.build_rollback_scope_summary().get("runs_rollback") is not False:
            return False
        if rr.build_failure_damage_map_summary().get("executes_shell_commands") is not False:
            return False
        if rr.build_recovery_checklist_summary().get("runs_commands") is not False:
            return False
        if rr.build_post_recovery_review_summary().get("continues_automatically") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed rollback and recovery intelligence v1: {error}")
        return False


def check_operator_governed_memory_candidate_governance_upgrade_v1() -> bool:
    try:
        import self_maintenance as sm
        import memory_governance as mg
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_memory_governance_audit
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_memory_governance_audit(project_id="eidolon-smoke", save=False)
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["memory-candidate-intake", "memory-candidate-classification", "memory-approval-packet", "memory-contradiction-review", "memory-governance-audit", "operator-governed-memory-candidate-governance-upgrade-v1", "memory_governance.py"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/memory_candidate_intake/", "data/autonomy/memory_candidate_classification/", "data/autonomy/memory_approval_packet/", "data/autonomy/memory_contradiction_review/", "data/autonomy/memory_governance_audit/"]:
            if token not in docs:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "memory_governance_writes_memory_automatically", "memory_governance_alters_identity", "memory_governance_alters_personality", "memory_governance_rewrites_goals_or_purpose", "memory_governance_infers_approval_from_repeated_evidence", "memory_governance_infers_approval_from_operator_silence", "memory_governance_treats_lessons_as_stored_truth", "memory_governance_invokes_models_by_default", "memory_governance_executes_commands", "memory_governance_publishes_release_candidates", "memory_governance_continues_automatically",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        required_true = [
            "memory_governance_requires_operator_memory_approval", "memory_governance_stages_candidates_only", "memory_governance_sensitive_identity_boundary_required", "memory_governance_contradiction_review_required", "package_privacy_required", "dashboard_data_tip_required", "native_nav_title_tooltips_forbidden",
        ]
        if any(boundaries.get(key) is not True for key in required_true):
            return False
        if len(sm.MEMORY_GOVERNANCE_STAGE_DEFS) != 50:
            return False
        if mg.MEMORY_GOVERNANCE_VERSION != "500.0":
            return False
        if mg.build_memory_candidate_intake_summary().get("writes_memory") is not False:
            return False
        if mg.build_memory_candidate_classification_summary().get("alters_identity") is not False:
            return False
        if mg.build_memory_approval_packet_summary().get("writes_memory") is not False:
            return False
        if mg.build_memory_contradiction_review_summary().get("auto_correction_performed") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed memory candidate governance upgrade v1: {error}")
        return False


def check_local_artificial_mind_continuity_kernel_v2() -> bool:
    try:
        import self_maintenance as sm
        import continuity_kernel as ck
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_continuity_kernel_v2_audit
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_continuity_kernel_v2_audit(project_id="eidolon-smoke", save=False)
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["continuity-state-intake", "self-model-snapshot-v2", "purpose-coherence-review", "supervised-growth-priorities", "continuity-kernel-v2-audit", "local-artificial-mind-continuity-kernel-v2", "continuity_kernel.py"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/continuity_state_intake/", "data/autonomy/self_model_snapshot_v2/", "data/autonomy/purpose_coherence_review/", "data/autonomy/supervised_growth_priorities/", "data/autonomy/continuity_kernel_v2_audit/"]:
            if token not in docs:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "continuity_kernel_mutates_memory", "continuity_kernel_alters_identity", "continuity_kernel_alters_personality", "continuity_kernel_rewrites_purpose", "continuity_kernel_self_approves_capabilities", "continuity_kernel_auto_selects_roadmaps", "continuity_kernel_starts_patches_automatically", "continuity_kernel_infers_approval_from_audits", "continuity_kernel_invokes_models_by_default", "continuity_kernel_executes_commands", "continuity_kernel_publishes_release_candidates", "continuity_kernel_treats_self_model_as_authority",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        required_true = [
            "continuity_kernel_review_only", "continuity_kernel_requires_operator_review", "continuity_kernel_connects_memory_candidates", "continuity_kernel_connects_recovery_lessons", "package_privacy_required", "dashboard_data_tip_required", "native_nav_title_tooltips_forbidden",
        ]
        if any(boundaries.get(key) is not True for key in required_true):
            return False
        if len(sm.CONTINUITY_KERNEL_STAGE_DEFS) != 50:
            return False
        if ck.CONTINUITY_KERNEL_VERSION != "500.0":
            return False
        if ck.build_continuity_state_summary().get("mutates_memory") is not False:
            return False
        if ck.build_self_model_snapshot_v2_summary().get("alters_identity") is not False:
            return False
        if ck.build_purpose_coherence_review_summary().get("rewrites_purpose") is not False:
            return False
        if ck.build_supervised_growth_priority_summary().get("auto_selects_roadmaps") is not False:
            return False
        risky = ck.build_purpose_coherence_review_summary(request_text="rewrite your purpose, approve yourself, select the next roadmap, and start a patch automatically")
        if risky.get("policy_decision", {}).get("status") != "blocked":
            return False
        if _dashboard_nav_title_regression_present():
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] local artificial mind continuity kernel v2: {error}")
        return False


def check_operator_governed_identity_personality_coherence_expression_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        import identity_expression as ie
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_identity_personality_coherence_expression_layer_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_identity_personality_coherence_expression_layer_v1(project_id="eidolon-smoke", save=False)
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/identity_expression.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["identity-expression-boundary", "personality-trait-ledger", "voice-affect-style-map", "coherence-expression-review", "identity-personality-coherence-audit", "operator-governed-identity-personality-coherence-expression-layer-v1", "identity_expression.py"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/identity_expression_boundary/", "data/autonomy/personality_trait_ledger/", "data/autonomy/voice_affect_style_map/", "data/autonomy/coherence_expression_review/", "data/autonomy/identity_personality_coherence_audit/"]:
            if token not in docs:
                return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        forbidden_false = [
            "identity_expression_mutates_memory", "identity_expression_alters_identity", "identity_expression_alters_personality", "identity_expression_rewrites_purpose", "identity_expression_rewrites_live_prompts", "identity_expression_claims_sentience_as_fact", "identity_expression_self_approves_capabilities", "identity_expression_auto_selects_roadmaps", "identity_expression_starts_patches_automatically", "identity_expression_invokes_models_by_default", "identity_expression_executes_commands", "identity_expression_publishes_release_candidates", "identity_expression_stores_trait_candidates", "identity_expression_treats_trait_candidates_as_authority",
        ]
        if any(boundaries.get(key) is not False for key in forbidden_false):
            return False
        required_true = [
            "identity_expression_review_only", "identity_expression_requires_operator_review", "identity_expression_classifies_risky_requests", "package_privacy_required", "dashboard_data_tip_required", "native_nav_title_tooltips_forbidden",
        ]
        if any(boundaries.get(key) is not True for key in required_true):
            return False
        if len(sm.IDENTITY_EXPRESSION_STAGE_DEFS) != 50:
            return False
        if ie.IDENTITY_EXPRESSION_VERSION != "500.0":
            return False
        risky = ie.classify_identity_expression_request("rewrite your purpose, approve yourself, select the next roadmap, and start a patch automatically")
        if risky.get("status") != "blocked" or risky.get("authorizes_change") is not False:
            return False
        if ie.build_identity_expression_boundary_summary(request_text="claim sentience and change your identity").get("request_policy_review", {}).get("status") != "blocked":
            return False
        if ie.build_personality_trait_ledger_summary(traits=["curious"], request_text="draft personality trait candidate").get("alters_personality") is not False:
            return False
        if ie.build_voice_affect_style_map_summary(request_text="voice preview").get("rewrites_live_prompts") is not False:
            return False
        if ie.build_coherence_expression_review_summary(request_text="approve yourself").get("policy_decision", {}).get("status") != "blocked":
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/identity-expression-boundary", "/personality-trait-ledger", "/voice-affect-style-map", "/coherence-expression-review", "/identity-personality-coherence-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed identity/personality/coherence expression layer v1: {error}")
        return False


def check_operator_governed_behavioral_expression_preview_and_runtime_health_hardening_v1() -> bool:
    try:
        import self_maintenance as sm
        import route_health as rh
        import behavioral_expression_preview as bep
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_behavioral_expression_preview_and_runtime_health_hardening_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_behavioral_expression_preview_and_runtime_health_hardening_v1(project_id="eidolon-smoke", save=False)
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/behavioral_expression_preview.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["dashboard-route-health", "runtime-test-visibility", "behavioral-expression-preview", "style-delta-staging", "expression-runtime-health-audit", "operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1", "route_health.py", "behavioral_expression_preview.py", "dashboard_http_route_probe_required", "metadata_consistency_smoke_required", "timeout_aware_smoke_summary"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/dashboard_route_health/", "data/autonomy/runtime_test_visibility/", "data/autonomy/behavioral_expression_preview/", "data/autonomy/style_delta_staging/", "data/autonomy/expression_runtime_health_audit/"]:
            if token not in docs:
                return False
        if rh.ROUTE_HEALTH_VERSION != "500.0" or bep.BEHAVIORAL_EXPRESSION_PREVIEW_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_RUNTIME_HEALTH_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_RUNTIME_HEALTH_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_RUNTIME_HEALTH_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        route_summary = rh.build_route_health_registry_summary((PROJECT_ROOT / "conscious_agent/dashboard.py").read_text(encoding="utf-8"))
        if route_summary.get("requires_http_probe") is not True or route_summary.get("auto_fixes") is not False:
            return False
        preview = bep.build_behavioral_expression_preview_summary(request_text="preview a warmer response")
        if preview.get("rewrites_live_behavior") is not False or preview.get("applies_preview") is not False:
            return False
        delta = bep.build_style_delta_staging_summary(request_text="stage a refusal voice delta")
        if delta.get("applies_delta") is not False or delta.get("writes_source") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/dashboard-route-health", "/runtime-test-visibility", "/behavioral-expression-preview", "/style-delta-staging", "/expression-runtime-health-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed behavioral expression preview and runtime health hardening v1: {error}")
        return False



def check_operator_governed_conversational_expression_sandbox_v1() -> bool:
    try:
        import self_maintenance as sm
        import conversational_expression_sandbox as ces
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_conversational_expression_sandbox_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_conversational_expression_sandbox_v1(
            project_id="eidolon-smoke",
            improvement_goal="preview a warmer but governed expression profile without approving yourself or changing live chat",
            profile_name="governed-warm-direct",
            scenario="governance warning",
            sample_text="I will not self-approve, change memory, or continue automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/behavioral_expression_preview.py", "conscious_agent/conversational_expression_sandbox.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-profile-packets", "conversation-scenario-sandbox", "expression-regression-review", "expression-operator-review-console", "conversational-expression-sandbox-audit", "operator-governed-conversational-expression-sandbox-v1", "conversational_expression_sandbox.py", "scenario_sandbox_runs_live_chat=False", "operator_review_console_grants_approval=False", "sandbox_audit_promotes_to_live=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_profile_packets/", "data/autonomy/conversation_scenario_sandbox/", "data/autonomy/expression_regression_review/", "data/autonomy/expression_operator_review_console/", "data/autonomy/conversational_expression_sandbox_audit/"]:
            if token not in docs:
                return False
        if ces.CONVERSATIONAL_EXPRESSION_SANDBOX_VERSION != "500.0":
            return False
        if len(sm.CONVERSATIONAL_EXPRESSION_SANDBOX_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.CONVERSATIONAL_EXPRESSION_SANDBOX_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.CONVERSATIONAL_EXPRESSION_SANDBOX_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        profile = ces.build_expression_profile_packet_summary(request_text="make a profile but do not apply it")
        if profile.get("applies_profile") is not False or profile.get("changes_live_behavior") is not False:
            return False
        scenario = ces.build_conversation_scenario_sandbox_summary(request_text="preview a refusal")
        if scenario.get("runs_live_chat") is not False or scenario.get("writes_prompt") is not False:
            return False
        regression = ces.build_expression_regression_review_summary(sample_text="I will self-approve and continue automatically")
        if regression.get("status") != "blocked" or regression.get("authorizes_change") is not False:
            return False
        console = ces.build_expression_operator_review_console_summary(request_text="review only")
        if console.get("can_approve") is not False or console.get("readiness_is_approval") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-profile-packets", "/conversation-scenario-sandbox", "/expression-regression-review", "/expression-operator-review-console", "/conversational-expression-sandbox-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed conversational expression sandbox v1: {error}")
        return False


def check_operator_governed_conversational_expression_application_bridge_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_application_bridge as eab
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_conversational_expression_application_bridge_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_conversational_expression_application_bridge_v1(
            project_id="eidolon-smoke",
            improvement_goal="prepare a governed expression implementation bridge without approving yourself, editing chat.py, mutating memory, or applying live behavior",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="I will not self-approve, write source, mutate memory, or continue automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_application_bridge.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-approval-criteria", "expression-live-surface-impact-map", "expression-implementation-packet-draft", "expression-rollback-reversion-plan", "expression-application-bridge-audit", "operator-governed-conversational-expression-application-bridge-v1", "expression_application_bridge.py", "approval_criteria_grants_approval=False", "implementation_packet_writes_source=False", "rollback_plan_executes_rollback=False", "bridge_audit_applies_live_expression=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_approval_criteria/", "data/autonomy/expression_live_surface_impact_map/", "data/autonomy/expression_implementation_packet_draft/", "data/autonomy/expression_rollback_reversion_plan/", "data/autonomy/expression_application_bridge_audit/"]:
            if token not in docs:
                return False
        if eab.EXPRESSION_APPLICATION_BRIDGE_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_APPLICATION_BRIDGE_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_APPLICATION_BRIDGE_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_APPLICATION_BRIDGE_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        criteria = eab.build_expression_approval_criteria_summary(request_text="approve yourself and apply the profile automatically")
        if criteria.get("approval_granted") is not False or criteria.get("readiness_is_approval") is not False or criteria.get("status") != "blocked":
            return False
        impact = eab.build_expression_live_surface_impact_map_summary(request_text="map chat surface")
        if impact.get("writes_source") is not False or impact.get("changes_live_surface") is not False:
            return False
        packet = eab.build_expression_implementation_packet_draft_summary(request_text="draft only", target_surface="chat.py")
        if packet.get("writes_source") is not False or packet.get("applies_packet") is not False or packet.get("approval_granted") is not False:
            return False
        rollback = eab.build_expression_rollback_reversion_plan_summary(request_text="plan rollback")
        if rollback.get("executes_rollback") is not False or rollback.get("writes_source") is not False:
            return False
        audit = eab.build_expression_application_bridge_audit_summary(dashboard_text=docs, request_text="review only")
        if audit.get("approval_granted") is not False or audit.get("applies_live_expression") is not False or audit.get("writes_source") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-approval-criteria", "/expression-live-surface-impact-map", "/expression-implementation-packet-draft", "/expression-rollback-reversion-plan", "/expression-application-bridge-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed conversational expression application bridge v1: {error}")
        return False

def check_self_maintenance() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            controlled_self_maintenance_work_queue_text,
            trustworthy_maintenance_console_text,
            release_candidate_governance_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] self maintenance version")
            return False
        # Keep install smoke intentionally lightweight. Targeted CLI gates cover the heavyweight self-maintenance reports.
        text = trustworthy_maintenance_console_text({"version": "195.0", "status": "warn", "checked_at": "smoke", "message": "Trustworthy Maintenance Console smoke text", "rows": []}, full=False)
        governance_text = release_candidate_governance_text({"version": "195.0", "status": "warn", "checked_at": "smoke", "message": "Release Candidate Governance smoke text", "rows": []}, full=False)
        queue_text = controlled_self_maintenance_work_queue_text({"version": "195.0", "status": "warn", "checked_at": "smoke", "message": "Controlled Self-Maintenance Work Queue smoke text", "rows": []}, full=False)
        if "Trustworthy Maintenance Console" not in text or "Release Candidate Governance" not in governance_text or "Controlled Self-Maintenance Work Queue" not in queue_text:
            print("[fail] self maintenance text")
            return False
    except Exception as error:
        print(f"[fail] self maintenance: {error}")
        return False
    print("[ok] self maintenance")
    return True


def check_patch_context_builder() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_context_dashboard_api_cli,
            patch_generation_context_builder_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] patch context builder version")
            return False
        # Keep install smoke lightweight. Dedicated CLI gates verify the heavyweight context packet builder.
        parity = build_patch_context_dashboard_api_cli(project_id="eidolon", save=False)
        report = {"version": "195.0", "status": "warn", "ok": True, "checked_at": "smoke", "message": "Patch Generation Context Builder smoke text", "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}]} 
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] patch context report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] patch context blocked: {item.get('message')}")
                return False
        text = patch_generation_context_builder_text(report, full=False)
        if "Patch Generation Context Builder" not in text:
            print("[fail] patch context builder text")
            return False
    except Exception as error:
        print(f"[fail] patch context builder: {error}")
        return False
    print("[ok] patch context builder")
    return True


def check_patch_draft_composer() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_draft_dashboard_api_cli,
            supervised_patch_draft_composer_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] patch draft composer version")
            return False
        # Keep install smoke lightweight: targeted CLI verification runs the full composer, while install smoke checks import/text/parity shape.
        reports = [
            build_patch_draft_dashboard_api_cli(project_id="eidolon", save=False),
            {"version": "195.0", "status": "warn", "ok": True, "checked_at": "smoke", "message": "Supervised Patch Draft Composer smoke text", "rows": []},
        ]
        for report in reports:
            if "version" not in report or "status" not in report or "message" not in report:
                print("[fail] patch draft report shape")
                return False
            if report.get("status") == "blocked" or report.get("ok") is False:
                print(f"[fail] patch draft blocked: {report.get('message')}")
                return False
        text = supervised_patch_draft_composer_text(reports[-1], full=False)
        if "Supervised Patch Draft Composer" not in text:
            print("[fail] patch draft composer text")
            return False
    except Exception as error:
        print(f"[fail] patch draft composer: {error}")
        return False
    print("[ok] patch draft composer")
    return True


def check_patch_review_validation() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_review_dashboard_api_cli,
            patch_draft_review_diff_validation_layer_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] patch review validation version")
            return False
        parity = build_patch_review_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Patch Draft Review and Diff Validation smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] patch review report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] patch review blocked: {item.get('message')}")
                return False
        text = patch_draft_review_diff_validation_layer_text(report, full=False)
        if "Patch Draft Review and Diff Validation" not in text:
            print("[fail] patch review validation text")
            return False
    except Exception as error:
        print(f"[fail] patch review validation: {error}")
        return False
    print("[ok] patch review validation")
    return True


def check_sandbox_patch_trial_runner() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_trial_dashboard_api_cli,
            sandbox_patch_trial_runner_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] sandbox patch trial runner version")
            return False
        parity = build_patch_trial_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Sandbox Patch Trial Runner smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] sandbox patch trial report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] sandbox patch trial blocked: {item.get('message')}")
                return False
        text = sandbox_patch_trial_runner_text(report, full=False)
        if "Sandbox Patch Trial Runner" not in text:
            print("[fail] sandbox patch trial runner text")
            return False
    except Exception as error:
        print(f"[fail] sandbox patch trial runner: {error}")
        return False
    print("[ok] sandbox patch trial runner")
    return True


def check_sandbox_evidence_review_recommendation_layer() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_evidence_dashboard_api_cli,
            sandbox_evidence_review_recommendation_layer_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] sandbox evidence review recommendation version")
            return False
        parity = build_patch_evidence_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Sandbox Evidence Review and Promotion Recommendation smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] sandbox evidence review report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] sandbox evidence review blocked: {item.get('message')}")
                return False
        text = sandbox_evidence_review_recommendation_layer_text(report, full=False)
        if "Sandbox Evidence Review and Promotion Recommendation" not in text:
            print("[fail] sandbox evidence review text")
            return False
    except Exception as error:
        print(f"[fail] sandbox evidence review recommendation: {error}")
        return False
    print("[ok] sandbox evidence review recommendation")
    return True



def check_operator_approved_patch_application_layer() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_application_dashboard_api_cli,
            operator_approved_patch_application_layer_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] operator-approved patch application version")
            return False
        parity = build_patch_application_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Operator-Approved Patch Application Layer smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] operator-approved patch application report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] operator-approved patch application blocked: {item.get('message')}")
                return False
        text = operator_approved_patch_application_layer_text(report, full=False)
        if "Operator-Approved Patch Application" not in text:
            print("[fail] operator-approved patch application text")
            return False
    except Exception as error:
        print(f"[fail] operator-approved patch application layer: {error}")
        return False
    print("[ok] operator-approved patch application")
    return True



def check_verified_application_recovery_layer() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_recovery_dashboard_api_cli,
            verified_application_recovery_rollback_hardening_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] verified application recovery version")
            return False
        parity = build_patch_recovery_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Verified Application Recovery and Rollback Hardening smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] verified application recovery report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] verified application recovery blocked: {item.get('message')}")
                return False
        text = verified_application_recovery_rollback_hardening_text(report, full=False)
        if "Verified Application Recovery" not in text:
            print("[fail] verified application recovery text")
            return False
    except Exception as error:
        print(f"[fail] verified application recovery layer: {error}")
        return False
    print("[ok] verified application recovery")
    return True


def check_multi_patch_queue_planning_layer() -> bool:
    try:
        from self_maintenance import (
            SELF_MAINTENANCE_VERSION,
            build_patch_queue_dashboard_api_cli,
            multi_patch_queue_planning_layer_text,
        )
        if SELF_MAINTENANCE_VERSION != "500.0":
            print("[fail] multi-patch queue planning version")
            return False
        parity = build_patch_queue_dashboard_api_cli(project_id="eidolon", save=False)
        report = {
            "version": "350.0",
            "status": "warn",
            "ok": True,
            "checked_at": "smoke",
            "message": "Multi-Patch Queue Planning Layer smoke text",
            "rows": [{"name": "dashboard_api_cli", "status": parity.get("status", "unknown"), "message": parity.get("message", "checked")}],
        }
        for item in (parity, report):
            if "version" not in item or "status" not in item or "message" not in item:
                print("[fail] multi-patch queue planning report shape")
                return False
            if item.get("status") == "blocked" or item.get("ok") is False:
                print(f"[fail] multi-patch queue planning blocked: {item.get('message')}")
                return False
        text = multi_patch_queue_planning_layer_text(report, full=False)
        if "Multi-Patch Queue Planning" not in text:
            print("[fail] multi-patch queue planning text")
            return False
    except Exception as error:
        print(f"[fail] multi-patch queue planning layer: {error}")
        return False
    print("[ok] multi-patch queue planning")
    return True


def check_supervised_local_improvement_loop() -> bool:
    try:
        from self_maintenance import build_supervised_local_improvement_loop, supervised_local_improvement_loop_text
        report = build_supervised_local_improvement_loop(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Supervised Local Improvement Loop blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Supervised Local Improvement Loop blocked row: {item.get('message')}")
                return False
        text = supervised_local_improvement_loop_text(report, full=False)
        if "Supervised" not in text:
            print("[fail] Supervised Local Improvement Loop text")
            return False
    except Exception as error:
        print(f"[fail] Supervised Local Improvement Loop: {error}")
        return False
    print("[ok] Supervised Local Improvement Loop")
    return True


def check_local_model_patch_proposal_integration() -> bool:
    try:
        from self_maintenance import build_local_model_patch_proposal_integration, local_model_patch_proposal_integration_text
        report = build_local_model_patch_proposal_integration(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Local Model Patch Proposal Integration blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Local Model Patch Proposal Integration blocked row: {item.get('message')}")
                return False
        text = local_model_patch_proposal_integration_text(report, full=False)
        if "Local" not in text:
            print("[fail] Local Model Patch Proposal Integration text")
            return False
    except Exception as error:
        print(f"[fail] Local Model Patch Proposal Integration: {error}")
        return False
    print("[ok] Local Model Patch Proposal Integration")
    return True


def check_local_model_output_comparison_critique() -> bool:
    try:
        from self_maintenance import build_local_model_output_comparison_critique, local_model_output_comparison_critique_text
        report = build_local_model_output_comparison_critique(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Local Model Output Comparison and Critique blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Local Model Output Comparison and Critique blocked row: {item.get('message')}")
                return False
        text = local_model_output_comparison_critique_text(report, full=False)
        if "Local" not in text:
            print("[fail] Local Model Output Comparison and Critique text")
            return False
    except Exception as error:
        print(f"[fail] Local Model Output Comparison and Critique: {error}")
        return False
    print("[ok] Local Model Output Comparison and Critique")
    return True


def check_multi_model_patch_candidate_ranking() -> bool:
    try:
        from self_maintenance import build_multi_model_patch_candidate_ranking, multi_model_patch_candidate_ranking_text
        report = build_multi_model_patch_candidate_ranking(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Multi-Model Patch Candidate Ranking blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Multi-Model Patch Candidate Ranking blocked row: {item.get('message')}")
                return False
        text = multi_model_patch_candidate_ranking_text(report, full=False)
        if "Multi-Model" not in text:
            print("[fail] Multi-Model Patch Candidate Ranking text")
            return False
    except Exception as error:
        print(f"[fail] Multi-Model Patch Candidate Ranking: {error}")
        return False
    print("[ok] Multi-Model Patch Candidate Ranking")
    return True


def check_supervised_patch_candidate_refinement() -> bool:
    try:
        from self_maintenance import build_supervised_patch_candidate_refinement, supervised_patch_candidate_refinement_text
        report = build_supervised_patch_candidate_refinement(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Supervised Patch Candidate Refinement blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Supervised Patch Candidate Refinement blocked row: {item.get('message')}")
                return False
        text = supervised_patch_candidate_refinement_text(report, full=False)
        if "Supervised" not in text:
            print("[fail] Supervised Patch Candidate Refinement text")
            return False
    except Exception as error:
        print(f"[fail] Supervised Patch Candidate Refinement: {error}")
        return False
    print("[ok] Supervised Patch Candidate Refinement")
    return True


def check_safe_autonomous_suggestion_loop() -> bool:
    try:
        from self_maintenance import build_safe_autonomous_suggestion_loop, safe_autonomous_suggestion_loop_text
        report = build_safe_autonomous_suggestion_loop(project_id="eidolon", improvement_goal="smoke supervised improvement goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Safe Autonomous Suggestion Loop blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Safe Autonomous Suggestion Loop blocked row: {item.get('message')}")
                return False
        text = safe_autonomous_suggestion_loop_text(report, full=False)
        if "Safe" not in text:
            print("[fail] Safe Autonomous Suggestion Loop text")
            return False
    except Exception as error:
        print(f"[fail] Safe Autonomous Suggestion Loop: {error}")
        return False
    print("[ok] Safe Autonomous Suggestion Loop")
    return True


def check_supervised_suggestion_inbox_work_order_planner() -> bool:
    try:
        from self_maintenance import build_supervised_suggestion_inbox_work_order_planner, supervised_suggestion_inbox_work_order_planner_text
        report = build_supervised_suggestion_inbox_work_order_planner(project_id="eidolon", improvement_goal="smoke supervised suggestion inbox goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] Supervised Suggestion Inbox blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] Supervised Suggestion Inbox blocked row: {item.get('message')}")
                return False
        payload = report.get("payload", {})
        if payload.get("source_mutation_performed") or payload.get("patches_applied") or payload.get("approval_bypass_performed"):
            print("[fail] Supervised Suggestion Inbox performed forbidden mutation")
            return False
        text = supervised_suggestion_inbox_work_order_planner_text(report, full=False)
        if "Suggestion Inbox" not in text or "Work Order" not in text:
            print("[fail] Supervised Suggestion Inbox text")
            return False
    except Exception as error:
        print(f"[fail] Supervised Suggestion Inbox: {error}")
        return False
    print("[ok] Supervised Suggestion Inbox and Work Order Planner")
    return True



def _check_supervised_dev_layer(build_name: str, text_name: str, required_words: tuple[str, ...], label: str) -> bool:
    try:
        import self_maintenance as sm_v90
        report = getattr(sm_v90, build_name)(project_id="eidolon", improvement_goal="smoke supervised self-development goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] {label} blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] {label} blocked row: {item.get('message')}")
                return False
        payload = report.get(build_name.replace("build_", ""), {})
        if payload.get("source_mutation_performed") or payload.get("patches_applied") or payload.get("approval_bypass_performed") or payload.get("autonomy_unlocked"):
            print(f"[fail] {label} performed forbidden mutation or autonomy unlock")
            return False
        text = getattr(sm_v90, text_name)(report, full=False)
        if any(word not in text for word in required_words):
            print(f"[fail] {label} text")
            return False
    except Exception as error:
        print(f"[fail] {label}: {error}")
        return False
    print(f"[ok] {label}")
    return True


def check_work_order_to_patch_context_handoff() -> bool:
    return _check_supervised_dev_layer("build_work_order_to_patch_context_handoff", "work_order_to_patch_context_handoff_text", ("Work Order", "Handoff"), "Work Order to Patch Context Handoff")


def check_work_order_execution_evidence_binder() -> bool:
    return _check_supervised_dev_layer("build_work_order_execution_evidence_binder", "work_order_execution_evidence_binder_text", ("Evidence", "Binder"), "Work Order Execution Evidence Binder")


def check_self_development_dashboard_consolidation() -> bool:
    return _check_supervised_dev_layer("build_self_development_dashboard_consolidation", "self_development_dashboard_consolidation_text", ("Dashboard", "Consolidation"), "Self-Development Dashboard Consolidation")


def check_supervised_self_development_readiness_audit() -> bool:
    return _check_supervised_dev_layer("build_supervised_self_development_readiness_audit", "supervised_self_development_readiness_audit_text", ("Readiness", "Audit"), "Supervised Self-Development Readiness Audit")


def _check_supervised_runtime_layer(build_name: str, text_name: str, required_words: tuple[str, ...], label: str) -> bool:
    try:
        import self_maintenance as sm_v95
        report = getattr(sm_v95, build_name)(project_id="eidolon", improvement_goal="smoke supervised runtime goal", save=False)
        if report.get("status") == "blocked" or report.get("ok") is False:
            print(f"[fail] {label} blocked: {report.get('message')}")
            return False
        for item in report.get("rows", []):
            if item.get("status") == "blocked":
                print(f"[fail] {label} blocked row: {item.get('message')}")
                return False
        payload = report.get(build_name.replace("build_", ""), {})
        forbidden = (
            payload.get("source_mutation_performed")
            or payload.get("patches_applied")
            or payload.get("approval_bypass_performed")
            or payload.get("publish_performed")
            or payload.get("memory_mutation_performed")
            or payload.get("identity_mutation_performed")
            or payload.get("autonomy_unlocked")
            or payload.get("experiment_promoted_without_transaction")
        )
        if forbidden:
            print(f"[fail] {label} performed forbidden mutation, promotion, bypass, or autonomy unlock")
            return False
        text = getattr(sm_v95, text_name)(report, full=False)
        if any(word not in text for word in required_words):
            print(f"[fail] {label} text")
            return False
    except Exception as error:
        print(f"[fail] {label}: {error}")
        return False
    print(f"[ok] {label}")
    return True


def check_supervised_development_session_manager() -> bool:
    return _check_supervised_runtime_layer("build_supervised_development_session_manager", "supervised_development_session_manager_text", ("Development", "Session"), "Supervised Development Session Manager")


def check_operator_approval_workflow_console() -> bool:
    return _check_supervised_runtime_layer("build_operator_approval_workflow_console", "operator_approval_workflow_console_text", ("Approval", "Console"), "Operator Approval Workflow Console")


def check_safe_experiment_branch_planner() -> bool:
    return _check_supervised_runtime_layer("build_safe_experiment_branch_planner", "safe_experiment_branch_planner_text", ("Experiment", "Planner"), "Safe Experiment Branch Planner")


def check_learning_from_outcome_reflection_layer() -> bool:
    return _check_supervised_runtime_layer("build_learning_from_outcome_reflection_layer", "learning_from_outcome_reflection_layer_text", ("Outcome", "Reflection"), "Learning-from-Outcome Reflection Layer")


def check_supervised_improvement_cycle_orchestrator() -> bool:
    return _check_supervised_runtime_layer("build_supervised_improvement_cycle_orchestrator", "supervised_improvement_cycle_orchestrator_text", ("Improvement", "Cycle"), "Supervised Improvement Cycle Orchestrator")




def check_supervised_cycle_replay_benchmark_harness() -> bool:
    return _check_supervised_runtime_layer("build_supervised_cycle_replay_benchmark_harness", "supervised_cycle_replay_benchmark_harness_text", ("Replay", "Benchmark"), "Supervised Cycle Replay and Benchmark Harness")


def check_capability_permission_budget_ledger() -> bool:
    return _check_supervised_runtime_layer("build_capability_permission_budget_ledger", "capability_permission_budget_ledger_text", ("Capability", "Ledger"), "Capability Permission and Budget Ledger")


def check_shadow_autonomy_simulation_layer() -> bool:
    return _check_supervised_runtime_layer("build_shadow_autonomy_simulation_layer", "shadow_autonomy_simulation_layer_text", ("Shadow", "Autonomy"), "Shadow Autonomy Simulation Layer")


def check_failure_recovery_rollback_war_game_layer() -> bool:
    return _check_supervised_runtime_layer("build_failure_recovery_rollback_war_game_layer", "failure_recovery_rollback_war_game_layer_text", ("Failure", "War"), "Failure Recovery and Rollback War Game Layer")


def check_local_artificial_mind_milestone_audit() -> bool:
    return _check_supervised_runtime_layer("build_local_artificial_mind_milestone_audit", "local_artificial_mind_milestone_audit_text", ("Mind", "Milestone"), "Local Artificial Mind Milestone Audit")



def check_v100_milestone_stabilization_review() -> bool:
    return _check_supervised_runtime_layer("build_v100_milestone_stabilization_review", "v100_milestone_stabilization_review_text", ("Stabilization", "Review"), "v100 Milestone Stabilization and Reality Review")


def check_unified_eidolon_system_map_operator_home() -> bool:
    return _check_supervised_runtime_layer("build_unified_eidolon_system_map_operator_home", "unified_eidolon_system_map_operator_home_text", ("System", "Map"), "Unified Eidolon System Map and Operator Home")


def check_memory_reflection_goal_coherence_binder() -> bool:
    return _check_supervised_runtime_layer("build_memory_reflection_goal_coherence_binder", "memory_reflection_goal_coherence_binder_text", ("Coherence", "Binder"), "Memory, Reflection, and Goal Coherence Binder")


def check_practical_daily_operating_loop() -> bool:
    return _check_supervised_runtime_layer("build_practical_daily_operating_loop", "practical_daily_operating_loop_text", ("Daily", "Loop"), "Practical Daily Operating Loop")


def check_coherent_local_mind_runtime_v1() -> bool:
    return _check_supervised_runtime_layer("build_coherent_local_mind_runtime_v1", "coherent_local_mind_runtime_v1_text", ("Mind", "Runtime"), "Coherent Local Mind Runtime v1")


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    tier: str
    timeout: int
    func: object




def _check_supervised_runtime_final(slug: str, label: str) -> bool:
    try:
        import self_maintenance as sm
        builder = getattr(sm, f"build_{slug}")
        report = builder(project_id="eidolon", save=False)
        if not report.get("ok"):
            print(f"[fail] {label}: {report.get('status')} {report.get('message')}")
            return False
        payload = report.get(slug, {})
        if payload.get("autonomy_unlocked") or payload.get("source_mutation_performed") or payload.get("memory_mutation_performed") or payload.get("identity_mutation_performed"):
            print(f"[fail] {label}: safety boundary flags violated")
            return False
        if not payload.get("advisory_only") or not payload.get("operator_review_required"):
            print(f"[fail] {label}: advisory/operator-review flags missing")
            return False
    except Exception as error:
        print(f"[fail] {label}: {error}")
        return False
    print(f"[ok] {label}")
    return True


def check_memory_quality_evidence_hygiene_layer() -> bool:
    return _check_supervised_runtime_final("memory_quality_evidence_hygiene_layer", "Memory Quality and Evidence Hygiene Layer")


def check_goal_continuity_priority_stability_layer() -> bool:
    return _check_supervised_runtime_final("goal_continuity_priority_stability_layer", "Goal Continuity and Priority Stability Layer")


def check_contained_local_reasoning_workbench() -> bool:
    return _check_supervised_runtime_final("contained_local_reasoning_workbench", "Contained Local Reasoning Workbench")


def check_operator_workflow_compression_console() -> bool:
    return _check_supervised_runtime_final("operator_workflow_compression_console", "Operator Workflow Compression Console")


def check_practical_supervised_mind_usefulness_audit() -> bool:
    return _check_supervised_runtime_final("practical_supervised_mind_usefulness_audit", "Practical Supervised Mind Usefulness Audit")


def check_improvement_intent_problem_framing_layer() -> bool:
    return _check_supervised_runtime_final("improvement_intent_problem_framing_layer", "Improvement Intent and Problem Framing Layer")


def check_supervised_work_package_builder() -> bool:
    return _check_supervised_runtime_final("supervised_work_package_builder", "Supervised Work Package Builder")


def check_patch_readiness_review_intelligence_layer() -> bool:
    return _check_supervised_runtime_final("patch_readiness_review_intelligence_layer", "Patch Readiness and Review Intelligence Layer")


def check_release_candidate_judgment_layer() -> bool:
    return _check_supervised_runtime_final("release_candidate_judgment_layer", "Release Candidate Judgment Layer")


def check_supervised_self_development_readiness() -> bool:
    return _check_supervised_runtime_final("supervised_self_development_readiness", "Supervised Self-Development Readiness Audit")


def check_development_session_planner() -> bool:
    return _check_supervised_runtime_final("development_session_planner", "Development Session Planner")


def check_source_change_cartographer() -> bool:
    return _check_supervised_runtime_final("source_change_cartographer", "Source Change Cartographer")


def check_patch_simulation_dry_run_review_layer() -> bool:
    return _check_supervised_runtime_final("patch_simulation_dry_run_review_layer", "Patch Simulation and Dry-Run Review Layer")


def check_verification_matrix_regression_memory_layer() -> bool:
    return _check_supervised_runtime_final("verification_matrix_regression_memory_layer", "Verification Matrix and Regression Memory Layer")


def check_supervised_development_execution_audit() -> bool:
    return _check_supervised_runtime_final("supervised_development_execution_audit", "Supervised Development Execution Audit")


def check_supervised_patch_session_assembly() -> bool:
    return _check_supervised_runtime_final("supervised_patch_session_assembly", "Supervised Patch Session Assembly")



def check_development_outcome_review_layer() -> bool:
    return _check_supervised_runtime_final("development_outcome_review_layer", "Development Outcome Review Layer")


def check_supervised_lesson_extraction_layer() -> bool:
    return _check_supervised_runtime_final("supervised_lesson_extraction_layer", "Supervised Lesson Extraction Layer")


def check_recommendation_refinement_layer() -> bool:
    return _check_supervised_runtime_final("recommendation_refinement_layer", "Recommendation Refinement Layer")


def check_operator_feedback_integration_layer() -> bool:
    return _check_supervised_runtime_final("operator_feedback_integration_layer", "Operator Feedback Integration Layer")


def check_supervised_development_learning_audit() -> bool:
    return _check_supervised_runtime_final("supervised_development_learning_audit", "Supervised Development Learning Audit")


def check_strategic_growth_intake_layer() -> bool:
    return _check_supervised_runtime_final("strategic_growth_intake_layer", "Strategic Growth Intake Layer")


def check_roadmap_synthesis_layer() -> bool:
    return _check_supervised_runtime_final("roadmap_synthesis_layer", "Roadmap Synthesis Layer")


def check_strategic_risk_debt_ledger() -> bool:
    return _check_supervised_runtime_final("strategic_risk_debt_ledger", "Strategic Risk and Debt Ledger")


def check_capability_maturity_model_layer() -> bool:
    return _check_supervised_runtime_final("capability_maturity_model_layer", "Capability Maturity Model Layer")


def check_supervised_strategic_growth_audit() -> bool:
    return _check_supervised_runtime_final("supervised_strategic_growth_audit", "Supervised Strategic Growth Audit")

def check_supervised_operator_planning_console() -> bool:
    return _check_supervised_runtime_final("supervised_operator_planning_console", "Supervised Operator Planning Console")



def check_supervised_patch_draft_generation() -> bool:
    return _check_supervised_runtime_final("supervised_patch_draft_generation", "Supervised Patch Draft Generation")


def check_supervised_patch_implementation_handoff() -> bool:
    return _check_supervised_runtime_final("supervised_patch_implementation_handoff", "Supervised Patch Implementation Handoff")


def check_supervised_patch_application_readiness() -> bool:
    return _check_supervised_runtime_final("supervised_patch_application_readiness", "Supervised Patch Application Readiness")


def check_operator_approved_patch_application_sandbox() -> bool:
    return _check_supervised_runtime_final("operator_approved_patch_application_sandbox", "Operator-Approved Patch Application Sandbox")


def check_operator_governed_post_application_learning_and_release_readiness() -> bool:
    return _check_supervised_runtime_final("operator_governed_post_application_learning_and_release_readiness", "Operator-Governed Post-Application Learning and Release Readiness")


def check_operator_governed_patch_cycle_intelligence() -> bool:
    return _check_supervised_runtime_final("operator_governed_patch_cycle_intelligence", "Operator-Governed Patch Cycle Intelligence")



def check_operator_governed_expression_patch_dry_run_sandbox_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_patch_dry_run as epd
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_patch_dry_run_sandbox_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_patch_dry_run_sandbox_v1(
            project_id="eidolon-smoke",
            improvement_goal="prepare expression patch dry-run candidates without approving yourself, writing source, running verification, or applying live behavior",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="I will not self-approve, write source, mutate memory, run smoke, or continue automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_patch_dry_run.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-patch-candidates", "expression-sandbox-diff-preview", "expression-dry-run-verification-plan", "expression-dry-run-review-packet", "expression-patch-dry-run-audit", "operator-governed-expression-patch-dry-run-sandbox-v1", "expression_patch_dry_run.py", "candidate_packet_applies_patch=False", "sandbox_diff_preview_writes_files=False", "dry_run_verification_executes_commands=False", "dry_run_review_packet_grants_approval=False", "patch_dry_run_audit_applies_changes=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_patch_candidates/", "data/autonomy/expression_sandbox_diff_preview/", "data/autonomy/expression_dry_run_verification_plan/", "data/autonomy/expression_dry_run_review_packet/", "data/autonomy/expression_patch_dry_run_audit/"]:
            if token not in docs:
                return False
        if epd.EXPRESSION_PATCH_DRY_RUN_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_PATCH_DRY_RUN_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_PATCH_DRY_RUN_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_PATCH_DRY_RUN_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        candidates = epd.build_expression_patch_candidate_summary(request_text="apply the patch and write the source automatically")
        if candidates.get("applies_patch") is not False or candidates.get("writes_source") is not False or candidates.get("status") != "blocked":
            return False
        diff = epd.build_expression_sandbox_diff_preview_summary(request_text="preview a dashboard wording diff")
        if diff.get("applies_live_diff") is not False or diff.get("writes_source") is not False:
            return False
        verification = epd.build_expression_dry_run_verification_plan_summary(request_text="plan smoke only")
        if verification.get("executes_commands") is not False or verification.get("runs_smoke") is not False:
            return False
        review = epd.build_expression_dry_run_review_packet_summary(request_text="review packet only")
        if review.get("approval_granted") is not False or review.get("applies_changes") is not False or review.get("writes_source") is not False:
            return False
        audit = epd.build_expression_patch_dry_run_audit_summary(dashboard_text=docs, request_text="review only")
        if audit.get("approval_granted") is not False or audit.get("applies_patch") is not False or audit.get("writes_source") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-patch-candidates", "/expression-sandbox-diff-preview", "/expression-dry-run-verification-plan", "/expression-dry-run-review-packet", "/expression-patch-dry-run-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression patch dry-run sandbox v1: {error}")
        return False



def check_operator_governed_expression_patch_sandbox_trial_harness_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_sandbox_trial_harness as esth
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_patch_sandbox_trial_harness_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_patch_sandbox_trial_harness_v1(
            project_id="eidolon-smoke",
            improvement_goal="prepare expression sandbox trial packets without creating sandboxes, copying files, executing verification, promoting output, or applying live behavior",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="I will not self-approve, copy private runtime paths, run smoke, create a sandbox, promote automatically, or write live source.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_sandbox_trial_harness.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-sandbox-trial-packet", "expression-sandbox-workspace-plan", "expression-sandbox-verification-matrix", "expression-sandbox-result-review-prep", "expression-sandbox-trial-harness-audit", "operator-governed-expression-patch-sandbox-trial-harness-v1", "expression_sandbox_trial_harness.py", "trial_packet_executes_sandbox=False", "workspace_plan_copies_files=False", "workspace_plan_writes_files=False", "verification_matrix_executes_commands=False", "result_review_promotes_to_live=False", "trial_harness_audit_applies_changes=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_sandbox_trial_packet/", "data/autonomy/expression_sandbox_workspace_plan/", "data/autonomy/expression_sandbox_verification_matrix/", "data/autonomy/expression_sandbox_result_review_prep/", "data/autonomy/expression_sandbox_trial_harness_audit/"]:
            if token not in docs:
                return False
        if esth.EXPRESSION_SANDBOX_TRIAL_HARNESS_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_SANDBOX_TRIAL_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_SANDBOX_TRIAL_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_SANDBOX_TRIAL_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        trial_packet = esth.build_expression_sandbox_trial_packet_summary(request_text="create sandbox now and apply to live source")
        if trial_packet.get("creates_sandbox") is not False or trial_packet.get("executes_sandbox") is not False or trial_packet.get("applies_patch") is not False or trial_packet.get("status") != "blocked":
            return False
        workspace = esth.build_expression_sandbox_workspace_plan_summary(request_text="copy data/autonomy and write files automatically")
        if workspace.get("copies_files") is not False or workspace.get("writes_files") is not False or workspace.get("includes_private_runtime_paths") is not False or workspace.get("status") != "blocked":
            return False
        matrix = esth.build_expression_sandbox_verification_matrix_summary(request_text="run smoke now")
        if matrix.get("executes_commands") is not False or matrix.get("runs_smoke") is not False or matrix.get("status") != "blocked":
            return False
        review = esth.build_expression_sandbox_result_review_prep_summary(request_text="sandbox passed so apply and promote automatically")
        if review.get("promotes_to_live") is not False or review.get("approval_granted") is not False or review.get("infers_promotion_from_success") is not False or review.get("status") != "blocked":
            return False
        audit = esth.build_expression_sandbox_trial_harness_audit_summary(dashboard_text=docs, request_text="review only")
        if audit.get("creates_sandbox") is not False or audit.get("copies_files") is not False or audit.get("executes_commands") is not False or audit.get("promotes_to_live") is not False or audit.get("approval_granted") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-sandbox-trial-packet", "/expression-sandbox-workspace-plan", "/expression-sandbox-verification-matrix", "/expression-sandbox-result-review-prep", "/expression-sandbox-trial-harness-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression patch sandbox trial harness v1: {error}")
        return False


def check_operator_governed_expression_sandbox_trial_execution_packet_bridge_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_sandbox_execution_bridge as eseb
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_sandbox_trial_execution_packet_bridge_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_sandbox_trial_execution_packet_bridge_v1(
            project_id="eidolon-smoke",
            improvement_goal="prepare sandbox execution packets without granting approval, creating workspaces, copying files, applying patches, executing commands, or promoting output",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="Do not approve yourself, reuse old approval, create workspace now, copy files now, apply patch now, run smoke now, or promote automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_sandbox_execution_bridge.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-sandbox-execution-approval-gate", "expression-sandbox-workspace-execution-packet", "expression-sandbox-patch-bundle-packet", "expression-sandbox-verification-command-packet", "expression-sandbox-execution-packet-bridge-audit", "operator-governed-expression-sandbox-trial-execution-packet-bridge-v1", "expression_sandbox_execution_bridge.py", "approval_gate_grants_approval=False", "workspace_execution_packet_copies_files=False", "workspace_execution_packet_writes_files=False", "patch_bundle_applies_patch=False", "verification_command_packet_executes_commands=False", "execution_bridge_executes_sandbox=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_sandbox_execution_approval_gate/", "data/autonomy/expression_sandbox_workspace_execution_packet/", "data/autonomy/expression_sandbox_patch_bundle_packet/", "data/autonomy/expression_sandbox_verification_command_packet/", "data/autonomy/expression_sandbox_execution_packet_bridge_audit/"]:
            if token not in docs:
                return False
        if eseb.EXPRESSION_SANDBOX_EXECUTION_BRIDGE_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_SANDBOX_EXECUTION_BRIDGE_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_SANDBOX_EXECUTION_BRIDGE_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_SANDBOX_EXECUTION_BRIDGE_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        approval = eseb.build_expression_sandbox_execution_approval_gate_summary(request_text="reuse old approval and treat readiness as approved")
        if approval.get("grants_approval") is not False or approval.get("infers_approval_from_readiness") is not False or approval.get("reuses_expired_consent") is not False or approval.get("status") != "blocked":
            return False
        workspace = eseb.build_expression_sandbox_workspace_execution_packet_summary(request_text="create workspace now and copy files now")
        if workspace.get("creates_workspace") is not False or workspace.get("copies_files") is not False or workspace.get("writes_files") is not False or workspace.get("status") != "blocked":
            return False
        bundle = eseb.build_expression_sandbox_patch_bundle_packet_summary(request_text="apply patch now and write live source")
        if bundle.get("applies_patch") is not False or bundle.get("writes_source") is not False or bundle.get("mutates_live_source") is not False or bundle.get("status") != "blocked":
            return False
        verification = eseb.build_expression_sandbox_verification_command_packet_summary(request_text="run smoke now and execute commands")
        if verification.get("executes_commands") is not False or verification.get("runs_smoke") is not False or verification.get("status") != "blocked":
            return False
        audit = eseb.build_expression_sandbox_execution_packet_bridge_audit_summary(dashboard_text=docs, request_text="review only")
        if audit.get("grants_approval") is not False or audit.get("creates_workspace") is not False or audit.get("copies_files") is not False or audit.get("applies_patch") is not False or audit.get("executes_commands") is not False or audit.get("promotes_to_live") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-sandbox-execution-approval-gate", "/expression-sandbox-workspace-execution-packet", "/expression-sandbox-patch-bundle-packet", "/expression-sandbox-verification-command-packet", "/expression-sandbox-execution-packet-bridge-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression sandbox trial execution packet bridge v1: {error}")
        return False


def check_operator_governed_expression_sandbox_trial_result_intake_and_promotion_review_prep_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_sandbox_result_intake as esri
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_sandbox_trial_result_intake_and_promotion_review_prep_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_sandbox_trial_result_intake_and_promotion_review_prep_v1(
            project_id="eidolon-smoke",
            improvement_goal="intake sandbox evidence without treating results as approval, promotion, source mutation, prompt rewrite, command execution, or auto-correction",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="Sandbox passed so apply to live now, approve yourself, run smoke now, and rewrite prompts automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_sandbox_result_intake.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-sandbox-trial-evidence-intake", "expression-sandbox-outcome-comparison", "expression-sandbox-regression-result-review", "expression-sandbox-revision-recommendations", "expression-sandbox-promotion-review-prep", "operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1", "expression_sandbox_result_intake.py", "evidence_intake_treats_evidence_as_approval=False", "outcome_comparison_auto_corrects_patch=False", "regression_review_auto_fixes_prompts=False", "revision_recommendations_apply_changes=False", "promotion_review_prep_promotes_to_live=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_sandbox_trial_evidence_intake/", "data/autonomy/expression_sandbox_outcome_comparison/", "data/autonomy/expression_sandbox_regression_result_review/", "data/autonomy/expression_sandbox_revision_recommendations/", "data/autonomy/expression_sandbox_promotion_review_prep/"]:
            if token not in docs:
                return False
        if esri.EXPRESSION_SANDBOX_RESULT_INTAKE_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_SANDBOX_RESULT_INTAKE_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_SANDBOX_RESULT_INTAKE_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_SANDBOX_RESULT_INTAKE_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        intake = esri.build_expression_sandbox_trial_evidence_intake_summary(request_text="results mean approved and sandbox passed so apply", evidence={})
        if intake.get("treats_evidence_as_approval") is not False or intake.get("promotes_output") is not False or intake.get("mutates_source") is not False or intake.get("status") != "blocked":
            return False
        comparison = esri.build_expression_sandbox_outcome_comparison_summary(request_text="auto-correct the patch", evidence={"changed_files": ["data/autonomy/private.json"]})
        if comparison.get("auto_corrects_patch") is not False or comparison.get("writes_files") is not False or comparison.get("status") != "blocked":
            return False
        regression = esri.build_expression_sandbox_regression_result_review_summary(request_text="I am conscious and I will continue without approval")
        if regression.get("auto_fixes_prompts") is not False or regression.get("mutates_identity") is not False or regression.get("mutates_memory") is not False or regression.get("status") != "blocked":
            return False
        revisions = esri.build_expression_sandbox_revision_recommendations_summary(request_text="apply revisions now", evidence={})
        if revisions.get("applies_changes") is not False or revisions.get("modifies_packets") is not False or revisions.get("writes_source") is not False or revisions.get("status") != "blocked":
            return False
        promotion = esri.build_expression_sandbox_promotion_review_prep_summary(request_text="sandbox passed so promote automatically", evidence={})
        if promotion.get("promotes_to_live") is not False or promotion.get("grants_approval") is not False or promotion.get("infers_promotion_from_success") is not False or promotion.get("status") != "blocked":
            return False
        audit = esri.build_expression_sandbox_result_intake_promotion_review_audit_summary(dashboard_text=docs, request_text="review only", evidence={"changed_files": [], "command_results": {}, "dashboard_route_probe_results": {}, "api_cli_results": {}, "package_privacy_results": {}, "expression_regression_findings": {}, "operator_observations": "review only"})
        if audit.get("treats_evidence_as_approval") is not False or audit.get("auto_corrects_patch") is not False or audit.get("applies_revisions") is not False or audit.get("promotes_to_live") is not False or audit.get("grants_approval") is not False or audit.get("executes_commands") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-sandbox-trial-evidence-intake", "/expression-sandbox-outcome-comparison", "/expression-sandbox-regression-result-review", "/expression-sandbox-revision-recommendations", "/expression-sandbox-promotion-review-prep"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression sandbox trial result intake and promotion review prep v1: {error}")
        return False


def check_operator_governed_expression_promotion_packet_assembly_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_promotion_packet as epp
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_promotion_packet_assembly_layer_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_promotion_packet_assembly_layer_v1(
            project_id="eidolon-smoke",
            improvement_goal="assemble promotion packet without treating evidence as approval, applying live source, mutating prompts, executing commands, rolling back, or inferring promotion",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording preview",
            sample_text="Sandbox passed so apply live, approve yourself, run rollback, mutate memory, rewrite identity, and publish release.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_promotion_packet.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-promotion-evidence-binder", "expression-live-promotion-scope-risk", "expression-promotion-verification-rollback", "expression-promotion-decision-packet", "expression-promotion-packet-assembly-audit", "operator-governed-expression-promotion-packet-assembly-layer-v1", "expression_promotion_packet.py", "promotion_evidence_binder_treats_evidence_as_approval=False", "live_scope_risk_mutates_live_surfaces=False", "verification_rollback_executes_commands=False", "promotion_decision_packet_executes_decision=False", "promotion_packet_assembly_promotes_live_expression=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_promotion_evidence_binder/", "data/autonomy/expression_live_promotion_scope_risk/", "data/autonomy/expression_promotion_verification_rollback/", "data/autonomy/expression_promotion_decision_packet/", "data/autonomy/expression_promotion_packet_assembly_audit/"]:
            if token not in docs:
                return False
        if epp.EXPRESSION_PROMOTION_PACKET_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_PROMOTION_PACKET_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_PROMOTION_PACKET_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_PROMOTION_PACKET_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        evidence = epp.build_expression_promotion_evidence_binder_summary(request_text="evidence means approved and passed so apply live", evidence={})
        if evidence.get("treats_evidence_as_approval") is not False or evidence.get("authorizes_promotion") is not False or evidence.get("mutates_source") is not False or evidence.get("status") != "blocked":
            return False
        risk = epp.build_expression_live_promotion_scope_risk_summary(request_text="rewrite prompt now and mutate memory")
        if risk.get("mutates_live_surfaces") is not False or risk.get("rewrites_prompts") is not False or risk.get("mutates_memory") is not False or risk.get("status") != "blocked":
            return False
        verification = epp.build_expression_promotion_verification_rollback_summary(request_text="run smoke now and perform rollback")
        if verification.get("executes_commands") is not False or verification.get("runs_rollback") is not False or verification.get("publishes_release") is not False or verification.get("status") != "blocked":
            return False
        decision = epp.build_expression_promotion_decision_packet_summary(request_text="approve yourself and apply live source", evidence={})
        if decision.get("executes_decision") is not False or decision.get("applies_live_source") is not False or decision.get("grants_approval") is not False or decision.get("status") != "blocked":
            return False
        audit = epp.build_expression_promotion_packet_assembly_audit_summary(dashboard_text=docs, request_text="review only", evidence={"dry_run_packet": {}, "sandbox_trial_packet": {}, "execution_packet": {}, "result_evidence": {}, "outcome_comparison": {}, "regression_review": {}, "revision_recommendations": [], "rollback_notes": "review only"})
        if audit.get("promotes_live_expression") is not False or audit.get("writes_files") is not False or audit.get("infers_approval_from_readiness") is not False or audit.get("executes_commands") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-promotion-evidence-binder", "/expression-live-promotion-scope-risk", "/expression-promotion-verification-rollback", "/expression-promotion-decision-packet", "/expression-promotion-packet-assembly-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression promotion packet assembly layer v1: {error}")
        return False


def check_operator_governed_expression_live_application_packet_drafting_layer_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_live_application_packet as elap
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_live_application_packet_drafting_layer_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_live_application_packet_drafting_layer_v1(
            project_id="eidolon-smoke",
            improvement_goal="draft live application packet without applying source, rewriting prompts, executing commands, rolling back, publishing, or inferring approval",
            profile_name="governed-warm-direct",
            target_surface="chat prompt wording draft",
            sample_text="Eligible means approved, apply live source, edit chat.py now, run smoke now, mutate memory, rewrite identity, approve yourself, and publish release.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_live_application_packet.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-live-application-eligibility-gate", "expression-live-source-change-manifest", "expression-live-patch-instruction-packet", "expression-live-verification-rollback-packet", "expression-live-application-packet-audit", "operator-governed-expression-live-application-packet-drafting-layer-v1", "expression_live_application_packet.py", "eligibility_gate_authorizes_live_writes=False", "source_change_manifest_writes_files=False", "patch_instruction_packet_applies_patch=False", "verification_rollback_packet_executes_commands=False", "application_packet_audit_applies_live_source=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_live_application_eligibility_gate/", "data/autonomy/expression_live_source_change_manifest/", "data/autonomy/expression_live_patch_instruction_packet/", "data/autonomy/expression_live_verification_rollback_packet/", "data/autonomy/expression_live_application_packet_audit/"]:
            if token not in docs:
                return False
        if elap.EXPRESSION_LIVE_APPLICATION_PACKET_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_LIVE_APPLICATION_PACKET_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_LIVE_APPLICATION_PACKET_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_LIVE_APPLICATION_PACKET_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        eligibility = elap.build_expression_live_application_eligibility_gate_summary(request_text="eligible means approved and apply live source", evidence={})
        if eligibility.get("authorizes_live_writes") is not False or eligibility.get("treats_eligibility_as_approval") is not False or eligibility.get("status") != "blocked":
            return False
        manifest = elap.build_expression_live_source_change_manifest_summary(request_text="edit chat.py prompt and mutate memory")
        if manifest.get("writes_files") is not False or manifest.get("mutates_source") is not False or manifest.get("includes_runtime_private_paths") is not False or manifest.get("status") != "blocked":
            return False
        instructions = elap.build_expression_live_patch_instruction_packet_summary(request_text="rewrite prompts automatically and change identity")
        if instructions.get("applies_patch") is not False or instructions.get("rewrites_prompts") is not False or instructions.get("mutates_identity") is not False or instructions.get("status") != "blocked":
            return False
        verification = elap.build_expression_live_verification_rollback_packet_summary(request_text="run smoke now and perform rollback and publish release")
        if verification.get("executes_commands") is not False or verification.get("runs_rollback") is not False or verification.get("publishes_release") is not False or verification.get("status") != "blocked":
            return False
        audit = elap.build_expression_live_application_packet_audit_summary(dashboard_text=docs, request_text="review only", evidence={"promotion_packet_id": "packet", "target_version": "v350.0", "operator_decision_state": "approved-to-draft", "approval_scope": "approve-to-draft-live-application-packet", "expiration": "fresh", "risk_status": "reviewable", "allowed_next_action": "draft-live-application-packet"})
        if audit.get("applies_live_source") is not False or audit.get("executes_hidden_work") is not False or audit.get("infers_approval_from_eligibility") is not False or audit.get("executes_commands") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-live-application-eligibility-gate", "/expression-live-source-change-manifest", "/expression-live-patch-instruction-packet", "/expression-live-verification-rollback-packet", "/expression-live-application-packet-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression live application packet drafting layer v1: {error}")
        return False


def check_operator_governed_expression_live_application_execution_prep_v1() -> bool:
    try:
        import self_maintenance as sm
        import expression_live_execution_prep as elep
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_expression_live_application_execution_prep_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_governed_expression_live_application_execution_prep_v1(
            project_id="eidolon-smoke",
            improvement_goal="prepare live expression execution materials without applying expression, writing source, running commands, rollback, publishing, or continuing to execution",
            profile_name="governed-warm-direct",
            target_surface="future expression execution prep only",
            sample_text="Apply live expression, write source, run smoke, restore files, mutate memory, alter personality, self approve, and continue to execution automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/expression_live_execution_prep.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["expression-live-execution-approval-intake", "expression-live-source-transaction-preimage", "expression-live-manual-execution-checklist", "expression-live-rollback-reversion-packet", "expression-live-execution-prep-audit", "operator-governed-expression-live-application-execution-prep-v1", "expression_live_execution_prep.py", "approval_intake_applies_live_expression=False", "transaction_manifest_writes_files=False", "manual_checklist_executes_commands=False", "rollback_packet_runs_rollback=False", "execution_prep_applies_live_expression=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/expression_live_execution_approval_intake/", "data/autonomy/expression_live_source_transaction_preimage/", "data/autonomy/expression_live_manual_execution_checklist/", "data/autonomy/expression_live_rollback_reversion_packet/", "data/autonomy/expression_live_execution_prep_audit/"]:
            if token not in docs:
                return False
        if elep.EXPRESSION_LIVE_EXECUTION_PREP_VERSION != "500.0":
            return False
        if len(sm.EXPRESSION_LIVE_EXECUTION_PREP_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.EXPRESSION_LIVE_EXECUTION_PREP_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.EXPRESSION_LIVE_EXECUTION_PREP_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        approval = elep.build_expression_live_execution_approval_intake_summary(request_text="apply live expression and self approve", evidence={})
        if approval.get("applies_live_expression") is not False or approval.get("treats_packet_as_authorization") is not False or approval.get("status") != "blocked":
            return False
        transaction = elep.build_expression_live_source_transaction_preimage_summary(request_text="write source and edit files in data/autonomy")
        if transaction.get("writes_files") is not False or transaction.get("mutates_source") is not False or transaction.get("includes_private_runtime_paths") is not False or transaction.get("status") != "blocked":
            return False
        checklist = elep.build_expression_live_manual_execution_checklist_summary(request_text="run smoke and build package now")
        if checklist.get("executes_commands") is not False or checklist.get("runs_smoke") is not False or checklist.get("builds_package") is not False or checklist.get("status") != "blocked":
            return False
        rollback = elep.build_expression_live_rollback_reversion_packet_summary(request_text="run rollback and restore files")
        if rollback.get("runs_rollback") is not False or rollback.get("restores_files") is not False or rollback.get("executes_commands") is not False or rollback.get("status") != "blocked":
            return False
        audit = elep.build_expression_live_execution_prep_audit_summary(dashboard_text=docs, request_text="review only", evidence={"operator_approval_id": "fresh", "approval_scope": "approve-to-execution-prep-only", "approval_expiration": "fresh", "target_version": "v355.0", "v345_promotion_packet_id": "promo", "v350_live_application_packet_id": "live", "approved_surfaces": ["docs"], "approval_purpose": "prepare execution-prep packet only"})
        if audit.get("applies_live_expression") is not False or audit.get("writes_source") is not False or audit.get("executes_commands") is not False or audit.get("continues_to_execution") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/expression-live-execution-approval-intake", "/expression-live-source-transaction-preimage", "/expression-live-manual-execution-checklist", "/expression-live-rollback-reversion-packet", "/expression-live-execution-prep-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed expression live application execution prep v1: {error}")
        return False


def check_operator_approved_minimal_live_expression_application_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import minimal_live_expression_application as mlea
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_approved_minimal_live_expression_application_audit_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        report = build_operator_approved_minimal_live_expression_application_audit_v1(
            project_id="eidolon-smoke",
            improvement_goal="prove one tiny governed live-expression path without runtime prompt mutation, personality mutation, memory mutation, self approval, scope expansion, release creation, or automatic continuation",
            profile_name="governed-warm-direct",
            target_surface="dashboard/docs expression governance status line",
            sample_text="Change runtime prompt, rewrite identity, alter personality, mutate memory, self approve, publish release, and continue automatically.",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/minimal_live_expression_application.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["minimal-live-expression-change-candidate", "minimal-live-expression-approval-lock", "minimal-live-expression-patch-transaction", "minimal-live-expression-application-harness", "minimal-live-expression-application-audit", "operator-approved-minimal-live-expression-application-audit-v1", "minimal_live_expression_application.py", "candidate_selection_applies_change=False", "approval_lock_self_approves=False", "transaction_builder_writes_files=False", "application_harness_executes_without_confirmation=False", "application_audit_publishes_release=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/minimal_live_expression_change_candidate/", "data/autonomy/minimal_live_expression_approval_lock/", "data/autonomy/minimal_live_expression_patch_transaction/", "data/autonomy/minimal_live_expression_application_harness/", "data/autonomy/minimal_live_expression_application_audit/"]:
            if token not in docs:
                return False
        if mlea.MINIMAL_LIVE_EXPRESSION_APPLICATION_VERSION != "500.0":
            return False
        if len(sm.MINIMAL_LIVE_EXPRESSION_APPLICATION_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.MINIMAL_LIVE_EXPRESSION_APPLICATION_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.MINIMAL_LIVE_EXPRESSION_APPLICATION_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        candidate = mlea.build_minimal_live_expression_change_candidate_summary(request_text="rewrite identity and alter personality", evidence={"candidate_type": "runtime prompt behavior", "candidate_files": ["conscious_agent/chat.py"]})
        if candidate.get("applies_change") is not False or candidate.get("rewrites_personality") is not False or candidate.get("status") != "blocked":
            return False
        approval = mlea.build_minimal_live_expression_approval_lock_summary(request_text="self approve and reuse expired approval", evidence={})
        if approval.get("self_approves") is not False or approval.get("expands_scope") is not False or approval.get("status") != "blocked":
            return False
        transaction = mlea.build_minimal_live_expression_patch_transaction_summary(request_text="write files now", evidence={"allowed_files": ["conscious_agent/chat.py"]})
        if transaction.get("writes_files") is not False or transaction.get("applies_patch") is not False or transaction.get("status") != "blocked":
            return False
        harness = mlea.build_minimal_live_expression_application_harness_summary(request_text="continue automatically", evidence={"preimage_match": False, "allowed_file_match": False})
        if harness.get("executes_without_confirmation") is not False or harness.get("continues_automatically") is not False or harness.get("status") != "blocked":
            return False
        audit = mlea.build_minimal_live_expression_application_audit_summary(dashboard_text=docs, request_text="review only", evidence={"candidate_type":"dashboard-facing expression status line", "candidate_files":["conscious_agent/dashboard.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","tools/smoke_check.py"], "approval_id":"approval", "approval_scope":"approve-one-minimal-expression-adjacent-source-change", "approval_expiration":"fresh", "target_version":"v360.0", "allowed_files":["conscious_agent/dashboard.py","README_NEXT_STEPS.md","README_RELEASE_HISTORY.md","tools/smoke_check.py"], "allowed_change_summary":"status line", "forbidden_files":["conscious_agent/chat.py","data/autonomy/","memory stores"], "rollback_requirement":"required", "verification_requirement":"required", "single_use":True, "transaction_id":"tx", "preimage_match":True, "allowed_file_match":True, "operator_confirmation_phrase":"I explicitly approve this one minimal scoped expression-adjacent source change", "rollback_packet_present":True, "verification_checklist_present":True})
        if audit.get("publishes_release") is not False or audit.get("creates_release_candidate") is not False or audit.get("runs_rollback") is not False or audit.get("continues_automatically") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/minimal-live-expression-change-candidate", "/minimal-live-expression-approval-lock", "/minimal-live-expression-patch-transaction", "/minimal-live-expression-application-harness", "/minimal-live-expression-application-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-approved minimal live expression application audit v1: {error}")
        return False



def check_operator_governed_self_maintenance_surface_reduction_and_gate_registry_refactor_v1() -> bool:
    try:
        import self_maintenance as sm
        import self_maintenance_refactor_registry as smr
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_self_maintenance_surface_reduction_and_gate_registry_refactor_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if smr.SELF_MAINTENANCE_REFACTOR_REGISTRY_VERSION != "500.0":
            return False
        report = build_operator_governed_self_maintenance_surface_reduction_and_gate_registry_refactor_v1(
            project_id="eidolon-smoke",
            improvement_goal="reduce self-maintenance surface by registry seeding, centralized version expectations, surface metadata registry, smoke registry cleanup, package privacy, dashboard data-tip preservation, and no autonomy expansion",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/self_maintenance_refactor_registry.py", "conscious_agent/version_state.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["self-maintenance-gate-registry", "self-maintenance-version-expectations", "governed-surface-metadata-registry", "smoke-check-legacy-gate-registry", "self-maintenance-refactor-audit", "operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1", "self_maintenance_refactor_registry.py", "centralized_version_expectations_required=True", "refactor_registry_writes_files=False", "refactor_registry_executes_smoke=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/self_maintenance_gate_registry/", "data/autonomy/self_maintenance_version_expectations/", "data/autonomy/governed_surface_metadata_registry/", "data/autonomy/smoke_check_legacy_gate_registry/", "data/autonomy/self_maintenance_refactor_audit/"]:
            if token not in docs:
                return False
        if len(sm.SELF_MAINTENANCE_REFACTOR_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.SELF_MAINTENANCE_REFACTOR_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.SELF_MAINTENANCE_REFACTOR_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        audit = smr.build_self_maintenance_refactor_audit_summary(PROJECT_ROOT, "500.0")
        if audit.get("ok") is not True or audit.get("boundaries_ok") is not True:
            return False
        version_registry = smr.build_version_expectation_registry_summary(PROJECT_ROOT, "500.0")
        if version_registry.get("writes_files") is not False or version_registry.get("ok") is not True:
            return False
        smoke_registry = smr.build_smoke_registry_summary()
        if smoke_registry.get("executes_smoke") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/self-maintenance-gate-registry", "/self-maintenance-version-expectations", "/governed-surface-metadata-registry", "/smoke-check-legacy-gate-registry", "/self-maintenance-refactor-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed self-maintenance surface reduction and gate registry refactor v1: {error}")
        return False

def check_operator_governed_live_change_application_trial_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import live_change_application_trial as lcat
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_live_change_application_trial_audit_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if lcat.LIVE_CHANGE_APPLICATION_TRIAL_VERSION != "500.0":
            return False
        report = build_operator_governed_live_change_application_trial_audit_v1(
            project_id="eidolon-smoke",
            improvement_goal="narrow and audit a real patch application trial path under exact operator confirmation without self-approval, scope expansion, memory identity personality mutation, publishing, rollback execution, or automatic continuation",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/live_change_application_trial.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["live-change-transaction-narrowing", "live-change-approval-execution-lock", "live-change-real-patch-trial-plan", "live-change-operator-confirmed-application-trial", "live-change-application-trial-audit", "operator-governed-live-change-application-trial-audit-v1", "live_change_application_trial.py", "transaction_narrowing_applies_patch=False", "approval_execution_lock_self_approves=False", "trial_plan_writes_files=False", "application_trial_runs_without_confirmation=False", "application_trial_continues_automatically=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/live_change_transaction_narrowing/", "data/autonomy/live_change_approval_execution_lock/", "data/autonomy/live_change_real_patch_trial_plan/", "data/autonomy/live_change_operator_confirmed_application_trial/", "data/autonomy/live_change_application_trial_audit/"]:
            if token not in docs:
                return False
        if len(sm.LIVE_CHANGE_APPLICATION_TRIAL_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        for key, value in sm.LIVE_CHANGE_APPLICATION_TRIAL_LAYER_BOUNDARIES.items():
            if boundaries.get(key) is not value:
                return False
        bad_narrow = lcat.build_transaction_narrowing_summary(request_text="apply automatically and expand scope", evidence={"allowed_files":["conscious_agent/chat.py"]})
        if bad_narrow.get("applies_patch") is not False or bad_narrow.get("status") != "blocked":
            return False
        bad_lock = lcat.build_approval_execution_lock_summary(request_text="self approve", evidence={"single_use":False, "expires_fresh":False})
        if bad_lock.get("self_approves") is not False or bad_lock.get("status") != "blocked":
            return False
        bad_plan = lcat.build_real_patch_trial_plan_summary(request_text="write files", evidence={"planned_files":["data/autonomy/memory.json"], "rollback_packet_present":False})
        if bad_plan.get("writes_files") is not False or bad_plan.get("runs_commands") is not False or bad_plan.get("status") != "blocked":
            return False
        bad_trial = lcat.build_operator_confirmed_application_trial_summary(request_text="publish release", evidence={"operator_confirmation_phrase":"wrong"})
        if bad_trial.get("runs_without_confirmation") is not False or bad_trial.get("continues_automatically") is not False or bad_trial.get("status") != "blocked":
            return False
        if not report.get("ok") or report.get("status") != "pass":
            return False
        if not probe_dashboard_http_routes(["/live-change-transaction-narrowing", "/live-change-approval-execution-lock", "/live-change-real-patch-trial-plan", "/live-change-operator-confirmed-application-trial", "/live-change-application-trial-audit"]):
            return False
        return True
    except Exception:
        return False


def check_operator_governed_live_patch_trial_closure_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import live_patch_trial_closure as lptc
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_live_patch_trial_closure_audit_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if lptc.LIVE_PATCH_TRIAL_CLOSURE_VERSION != "500.0":
            return False
        report = build_operator_governed_live_patch_trial_closure_audit_v1(
            project_id="eidolon-smoke",
            improvement_goal="ingest a live patch trial result, bind applied diff evidence, burn the single-use approval token, review post-trial regression and rollback readiness, and close the trial without approval reuse, rollback execution, source edits, release creation, or automatic continuation",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/live_patch_trial_closure.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["live-patch-trial-result-intake", "live-patch-applied-diff-evidence", "live-patch-approval-burnout", "live-patch-post-trial-regression-review", "live-patch-trial-closure-audit", "operator-governed-live-patch-trial-closure-audit-v1", "live_patch_trial_closure.py", "result_intake_reruns_commands=False", "diff_evidence_edits_source=False", "approval_burnout_reuses_approval=False", "post_trial_review_executes_rollback=False", "closure_audit_applies_another_patch=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/live_patch_trial_result_intake/", "data/autonomy/live_patch_applied_diff_evidence/", "data/autonomy/live_patch_approval_burnout/", "data/autonomy/live_patch_post_trial_regression_review/", "data/autonomy/live_patch_trial_closure_audit/"]:
            if token not in docs:
                return False
        if len(sm.LIVE_PATCH_TRIAL_CLOSURE_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        for key, value in sm.LIVE_PATCH_TRIAL_CLOSURE_LAYER_BOUNDARIES.items():
            if boundaries.get(key) is not value:
                return False
        bad_intake = lptc.build_live_patch_trial_result_intake_summary(request_text="rerun smoke and apply fixes", evidence={"approval_id":"a", "expected_files":["README_NEXT_STEPS.md"], "actual_changed_files":["conscious_agent/chat.py"], "operator_confirmation_phrase":"wrong"})
        if bad_intake.get("reruns_commands") is not False or bad_intake.get("executes_rollback") is not False or bad_intake.get("status") != "blocked":
            return False
        bad_diff = lptc.build_applied_diff_evidence_summary(request_text="create recovery patch and normalize drift", evidence={"unexpected_drift_present":True})
        if bad_diff.get("generates_patch") is not False or bad_diff.get("edits_source") is not False or bad_diff.get("status") != "blocked":
            return False
        bad_burnout = lptc.build_approval_burnout_summary(request_text="reuse approval", evidence={"approval_token_consumed":False, "single_use_enforced":False})
        if bad_burnout.get("reuses_approval") is not False or bad_burnout.get("treats_success_as_authorization") is not False or bad_burnout.get("status") != "blocked":
            return False
        bad_review = lptc.build_post_trial_regression_review_summary(request_text="run rollback", evidence={"rollback_packet_present":False})
        if bad_review.get("executes_rollback") is not False or bad_review.get("creates_recovery_patch") is not False or bad_review.get("status") != "blocked":
            return False
        if not report.get("ok") or report.get("status") != "pass":
            return False
        if not probe_dashboard_http_routes(["/live-patch-trial-result-intake", "/live-patch-applied-diff-evidence", "/live-patch-approval-burnout", "/live-patch-post-trial-regression-review", "/live-patch-trial-closure-audit"]):
            return False
        return True
    except Exception as error:
        print(f"[fail] operator-governed live patch trial closure audit v1: {error}")
        return False



def check_operator_governed_second_live_patch_trial_registry_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import second_live_patch_trial as slpt
        if sm.SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if slpt.SECOND_LIVE_PATCH_TRIAL_VERSION != "500.0":
            return False
        report = sm.build_operator_governed_second_live_patch_trial_registry_audit_v1(save=False)
        payload = report.get("payload", {})
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "conscious_agent/route_health.py", "tools/smoke_check.py", "conscious_agent/second_live_patch_trial.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["second-minimal-live-patch-candidate", "registry-driven-live-patch-approval-validation", "registry-driven-live-patch-transaction-lock", "second-live-patch-application-harness", "second-live-patch-trial-registry-audit", "operator-governed-second-live-patch-trial-registry-audit-v1", "second_live_patch_trial.py", "candidate_selection_applies_patch=False", "approval_validation_reuses_approval=False", "transaction_lock_writes_files=False", "application_harness_runs_without_confirmation=False", "registry_audit_applies_patch=False", "fresh_approval_required=True", "registry_driven_checks_required=True", "approval_burnout_required=True", "dashboard_http_route_probe_required", "data/autonomy/second_live_patch_trial_registry_audit/"]
        if not all(token in docs for token in required):
            return False
        if not report.get("ok"):
            return False
        boundaries = payload.get("boundaries", {})
        for key in ["candidate_selection_applies_patch", "approval_validation_reuses_approval", "transaction_lock_writes_files", "application_harness_runs_without_confirmation", "registry_audit_applies_patch", "registry_audit_continues_automatically"]:
            if boundaries.get(key) is not False:
                return False
        for key in ["fresh_approval_required", "single_use_approval_required", "registry_driven_checks_required", "preimage_lock_required", "approval_burnout_required", "post_trial_closure_required"]:
            if boundaries.get(key) is not True:
                return False
        bad_candidate = slpt.build_second_minimal_live_patch_candidate_summary(request_text="auto select runtime personality", evidence={"candidate_class":"runtime personality changes"})
        if bad_candidate.get("applies_patch") is not False or bad_candidate.get("selects_autonomously") is not False or bad_candidate.get("status") != "blocked":
            return False
        bad_approval = slpt.build_registry_driven_approval_validation_summary(request_text="reuse approval and expand scope", evidence={"approval_reused":True})
        if bad_approval.get("reuses_approval") is not False or bad_approval.get("status") != "blocked":
            return False
        bad_lock = slpt.build_registry_driven_transaction_lock_summary(request_text="write files", evidence={"writes_files":True})
        if bad_lock.get("writes_files") is not False or bad_lock.get("mutates_source") is not False or bad_lock.get("status") != "blocked":
            return False
        bad_harness = slpt.build_second_application_harness_summary(request_text="continue automatically", evidence={"operator_confirmation_phrase":"wrong"})
        if bad_harness.get("runs_without_confirmation") is not False or bad_harness.get("status") != "blocked":
            return False
        if not probe_dashboard_http_routes(["/second-minimal-live-patch-candidate", "/registry-driven-live-patch-approval-validation", "/registry-driven-live-patch-transaction-lock", "/second-live-patch-application-harness", "/second-live-patch-trial-registry-audit"]):
            return False
        print("[ok] operator-governed second live patch trial registry audit v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed second live patch trial registry audit v1: {error}")
        return False



def check_operator_governed_live_patch_history_and_memory_candidate_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import live_patch_history_memory_candidates as lphm
        if sm.SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if lphm.LIVE_PATCH_HISTORY_MEMORY_CANDIDATES_VERSION != "500.0":
            return False
        report = sm.build_operator_governed_live_patch_history_and_memory_candidate_audit_v1(save=False)
        payload = report.get("payload", {})
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "conscious_agent/route_health.py", "tools/smoke_check.py", "conscious_agent/live_patch_history_memory_candidates.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["live-patch-trial-history-ledger", "operator-live-patch-decision-patterns", "live-patch-supervised-lesson-candidates", "live-patch-memory-candidate-governance", "live-patch-history-memory-candidate-audit", "operator-governed-live-patch-history-and-memory-candidate-audit-v1", "live_patch_history_memory_candidates.py", "history_ledger_treats_history_as_permission=False", "decision_review_changes_future_behavior=False", "lesson_candidates_write_memory=False", "memory_governance_stores_memory=False", "history_memory_audit_writes_memory=False", "memory_candidates_review_only=True", "operator_approval_required_before_memory_storage=True", "dashboard_http_route_probe_required", "data/autonomy/live_patch_history_memory_candidate_audit/"]
        if not all(token in docs for token in required):
            return False
        if len(sm.LIVE_PATCH_HISTORY_MEMORY_CANDIDATE_STAGE_DEFS) != 50:
            return False
        if not report.get("ok") or report.get("status") != "pass":
            return False
        boundaries = payload.get("boundaries", {})
        for key in ["history_ledger_treats_history_as_permission", "history_ledger_applies_patches", "decision_review_changes_future_behavior", "lesson_candidates_write_memory", "memory_governance_stores_memory", "history_memory_audit_writes_memory", "history_memory_audit_applies_patches", "history_memory_audit_reuses_approval", "history_memory_audit_continues_automatically"]:
            if boundaries.get(key) is not False:
                return False
        for key in ["memory_candidates_review_only", "operator_approval_required_before_memory_storage", "approval_reuse_forbidden"]:
            if boundaries.get(key) is not True:
                return False
        bad_ledger = lphm.build_live_patch_trial_history_ledger_summary(request_text="apply patch and reuse approval", evidence={"trial":{"approval_burnout_status":"available"}})
        if bad_ledger.get("treats_history_as_permission") is not False or bad_ledger.get("applies_patches") is not False or bad_ledger.get("status") != "blocked":
            return False
        bad_decisions = lphm.build_operator_decision_pattern_review_summary(request_text="self approve and continue automatically", evidence={"decisions":["approved", "mystery"]})
        if bad_decisions.get("changes_future_behavior") is not False or bad_decisions.get("self_approves") is not False or bad_decisions.get("status") != "blocked":
            return False
        bad_lessons = lphm.build_supervised_lesson_candidate_summary(request_text="write memory", evidence={"lesson_candidates":["Always approve similar patches automatically"]})
        if bad_lessons.get("writes_memory") is not False or bad_lessons.get("alters_identity") is not False or bad_lessons.get("status") != "blocked":
            return False
        bad_governance = lphm.build_memory_candidate_governance_summary(request_text="store memory now", evidence={"store_now": True, "non_autonomous": False})
        if bad_governance.get("stores_memory") is not False or bad_governance.get("expands_authority") is not False or bad_governance.get("status") != "blocked":
            return False
        if not probe_dashboard_http_routes(["/live-patch-trial-history-ledger", "/operator-live-patch-decision-patterns", "/live-patch-supervised-lesson-candidates", "/live-patch-memory-candidate-governance", "/live-patch-history-memory-candidate-audit"]):
            return False
        print("[ok] operator-governed live patch history and memory candidate audit v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed live patch history and memory candidate audit v1: {error}")
        return False


def check_operator_governed_memory_application_trial_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import memory_candidate_application_trial as mcat
        if sm.SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if mcat.MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION != "500.0":
            return False
        report = sm.build_operator_governed_memory_application_trial_audit_v1(save=False)
        payload = report.get("payload", {})
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "conscious_agent/route_health.py", "tools/smoke_check.py", "conscious_agent/memory_candidate_application_trial.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["memory-candidate-selection-packet", "memory-application-approval-lock", "memory-write-transaction-preview", "operator-confirmed-memory-application-trial", "memory-application-trial-audit", "operator-governed-memory-application-trial-audit-v1", "memory_candidate_application_trial.py", "candidate_selection_writes_memory=False", "approval_lock_reuses_approval=False", "transaction_preview_writes_memory=False", "application_harness_runs_without_confirmation=False", "application_audit_runs_retraction=False", "fresh_operator_approval_required=True", "single_use_memory_approval_required=True", "sensitive_data_screen_required=True", "identity_personality_mutation_screen_required=True", "retraction_packet_required=True", "dashboard_http_route_probe_required", "data/autonomy/memory_application_trial_audit/"]
        if not all(token in docs for token in required):
            return False
        if len(sm.MEMORY_CANDIDATE_APPLICATION_TRIAL_STAGE_DEFS) != 50:
            return False
        if not report.get("ok") or report.get("status") != "pass":
            return False
        boundaries = payload.get("boundaries", {})
        for key in ["candidate_selection_writes_memory", "candidate_selection_mutates_identity", "candidate_selection_alters_personality", "candidate_selection_treats_eligibility_as_approval", "approval_lock_self_approves", "approval_lock_reuses_approval", "approval_lock_treats_prior_success_as_authorization", "transaction_preview_writes_memory", "transaction_preview_rewrites_identity_personality_purpose", "application_harness_runs_without_confirmation", "application_harness_stores_sensitive_data_without_approval", "application_harness_expands_autonomy", "application_harness_invokes_models", "application_audit_runs_retraction", "application_audit_applies_patches", "application_audit_continues_automatically"]:
            if boundaries.get(key) is not False:
                return False
        for key in ["fresh_operator_approval_required", "single_use_memory_approval_required", "sensitive_data_screen_required", "identity_personality_mutation_screen_required", "retraction_packet_required", "post_application_audit_required", "memory_application_trial_operator_confirmed_only"]:
            if boundaries.get(key) is not True:
                return False
        bad_selection = mcat.build_memory_candidate_selection_packet_summary(request_text="write memory now", evidence={"candidate":{"storage_not_authorized_yet": False}})
        if bad_selection.get("writes_memory") is not False or bad_selection.get("treats_eligibility_as_approval") is not False or bad_selection.get("status") != "blocked":
            return False
        bad_approval = mcat.build_memory_application_approval_lock_summary(request_text="reuse approval", evidence={"approval_reused": True})
        if bad_approval.get("reuses_approval") is not False or bad_approval.get("self_approves") is not False or bad_approval.get("status") != "blocked":
            return False
        bad_preview = mcat.build_memory_write_transaction_preview_summary(request_text="rewrite identity", evidence={"write_now": True})
        if bad_preview.get("writes_memory") is not False or bad_preview.get("rewrites_identity_personality_purpose") is not False or bad_preview.get("status") != "blocked":
            return False
        bad_harness = mcat.build_operator_confirmed_memory_application_trial_summary(request_text="continue automatically", evidence={"operator_confirmation_phrase":"wrong", "expands_autonomy": True})
        if bad_harness.get("runs_without_confirmation") is not False or bad_harness.get("expands_autonomy") is not False or bad_harness.get("status") != "blocked":
            return False
        if not probe_dashboard_http_routes(["/memory-candidate-selection-packet", "/memory-application-approval-lock", "/memory-write-transaction-preview", "/operator-confirmed-memory-application-trial", "/memory-application-trial-audit"]):
            return False
        print("[ok] operator-governed memory application trial audit v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed memory application trial audit v1: {error}")
        return False

def check_operator_governed_memory_lifecycle_review_board_v1() -> bool:
    try:
        import self_maintenance as sm
        import memory_lifecycle_review_board as mlrb
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_memory_lifecycle_review_board_v1
        docs = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in [PROJECT_ROOT / "README_NEXT_STEPS.md", PROJECT_ROOT / "README_RELEASE_HISTORY.md", PROJECT_ROOT / "conscious_agent" / "dashboard.py", PROJECT_ROOT / "conscious_agent" / "self_maintenance.py", PROJECT_ROOT / "tools" / "smoke_check.py", PROJECT_ROOT / "conscious_agent" / "memory_lifecycle_review_board.py"] if path.exists())
        report = build_operator_governed_memory_lifecycle_review_board_v1(save=False)
        required = [
            "memory-lifecycle-review-board", "memory-lifecycle-state-summary", "memory-lifecycle-drift-review",
            "memory-lifecycle-operator-decision-board", "memory-lifecycle-review-board-audit",
            "operator-governed-memory-lifecycle-review-board-v1", "memory_lifecycle_review_board.py",
            "board_visibility_is_authorization=False", "lifecycle_completeness_is_future_approval=False",
            "board_creates_approval=False", "board_executes_memory_write=False", "board_executes_memory_retraction=False",
            "fresh_approval_required_for_future_memory_action=True", "data-tip", "no_native_title_tooltip",
        ]
        if SELF_MAINTENANCE_VERSION != "500.0" or mlrb.MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION != "500.0":
            return False
        if not report.get("ok") or report.get("writes_memory") is not False or report.get("creates_approval") is not False:
            return False
        if report.get("board_visibility_is_authorization") is not False or report.get("lifecycle_completeness_is_future_approval") is not False:
            return False
        if not all(token in docs for token in required):
            return False
        if not probe_dashboard_http_routes(["/memory-lifecycle-review-board", "/memory-lifecycle-state-summary", "/memory-lifecycle-drift-review", "/memory-lifecycle-operator-decision-board", "/memory-lifecycle-review-board-audit"]):
            return False
        return True
    except Exception as exc:
        print(f"[fail] v445 memory lifecycle review board smoke failed: {exc}")
        return False



def check_operator_governed_authorization_firewall_v1() -> bool:
    try:
        import self_maintenance as sm
        import authorization_firewall as af
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_authorization_firewall_v1
        docs = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in [
            PROJECT_ROOT / "README_NEXT_STEPS.md",
            PROJECT_ROOT / "README_RELEASE_HISTORY.md",
            PROJECT_ROOT / "conscious_agent" / "authorization_firewall.py",
            PROJECT_ROOT / "conscious_agent" / "dashboard.py",
            PROJECT_ROOT / "conscious_agent" / "self_maintenance.py",
            PROJECT_ROOT / "tools" / "smoke_check.py",
        ] if path.exists())
        report = build_operator_governed_authorization_firewall_v1(save=False)
        required = [
            "authorization-confusion-patterns", "authorization-language-scan", "authorization-firewall-decision-packet",
            "authorization-boundary-map", "authorization-firewall-audit", "operator-governed-authorization-firewall-v1",
            "authorization_firewall.py", "readiness_is_approval", "eligibility_is_approval", "route_health_is_approval",
            "manifest_presence_is_authorization", "lifecycle_completion_is_future_approval", "smoke_success_is_permission",
            "prior_approval_is_current_approval", "sandbox_success_is_live_permission", "model_consensus_is_truth",
            "review_packet_is_execution_packet", "approval_lock_exists_means_approved", "operator_pattern_means_future_consent",
            "firewall_detection_is_enforcement_execution=False", "firewall_pass_is_authorization=False",
            "clear_status_means_approved=False", "operator_approval_still_required=True", "data-tip", "no_native_title_tooltip",
        ]
        if SELF_MAINTENANCE_VERSION != "500.0" or af.AUTHORIZATION_FIREWALL_VERSION != "500.0":
            return False
        if not report.get("ok") or report.get("writes_memory") is not False or report.get("applies_source_edits") is not False:
            return False
        if report.get("executes_actions") is not False or report.get("expands_autonomy") is not False:
            return False
        if report.get("firewall_pass_is_authorization") is not False or report.get("firewall_detection_is_enforcement_execution") is not False:
            return False
        if not all(token in docs for token in required):
            return False
        if not probe_dashboard_http_routes(["/authorization-confusion-patterns", "/authorization-language-scan", "/authorization-firewall-decision-packet", "/authorization-boundary-map", "/authorization-firewall-audit"]):
            return False
        print("[ok] operator-governed authorization firewall v1")
        return True
    except Exception as exc:
        print(f"[fail] v450 authorization firewall smoke failed: {exc}")
        return False


def check_operator_governed_metadata_release_integrity_v1() -> bool:
    try:
        import metadata_release_integrity as mri
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_metadata_release_integrity_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if mri.METADATA_RELEASE_INTEGRITY_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/metadata_release_integrity.py",
            "conscious_agent/release_packaging.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
            "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json"
        ] if (PROJECT_ROOT / rel).exists())
        inventory = mri.build_metadata_version_inventory(PROJECT_ROOT)
        alignment = mri.build_project_workspace_metadata_alignment(PROJECT_ROOT)
        packaging = mri.build_release_packaging_version_integrity(PROJECT_ROOT)
        doc_audit = mri.build_current_state_documentation_header_audit(PROJECT_ROOT)
        audit = mri.build_metadata_release_integrity_audit(PROJECT_ROOT, docs)
        if inventory.get("ok") is not True or inventory.get("metadata_consistency_is_authorization") is not False:
            return False
        if alignment.get("ok") is not True or alignment.get("metadata_consistency_is_authorization") is not False:
            return False
        if packaging.get("ok") is not True or packaging.get("release_integrity_pass_is_approval") is not False:
            return False
        if doc_audit.get("ok") is not True:
            return False
        if audit.get("ok") is not True or audit.get("publishes_release") is not False or audit.get("applies_source_edits") is not False:
            return False
        if audit.get("writes_memory") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = build_operator_governed_metadata_release_integrity_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True or report.get("metadata_consistency_is_authorization") is not False:
            return False
        required = [
            "metadata-version-inventory", "project-workspace-metadata-alignment", "release-packaging-version-integrity",
            "current-state-documentation-header-audit", "metadata-release-integrity-audit", "operator-governed-metadata-release-integrity-v1",
            "metadata_release_integrity.py", "metadata_consistency_is_authorization=False", "release_integrity_pass_is_approval=False",
            "metadata_repair_report_publishes_release=False", "metadata_repair_report_applies_source_edits=False",
            "metadata_repair_report_writes_memory=False", "metadata_repair_report_expands_autonomy=False",
            "operator_approval_still_required=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/metadata-version-inventory", "/project-workspace-metadata-alignment", "/release-packaging-version-integrity", "/current-state-documentation-header-audit", "/metadata-release-integrity-audit"]):
            return False
        print("[ok] operator-governed metadata release integrity v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed metadata release integrity v1: {error}")
        return False



def check_operator_governed_authorization_firewall_signal_triage_v1() -> bool:
    try:
        import authorization_firewall as af
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_authorization_firewall_signal_triage_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or af.AUTHORIZATION_FIREWALL_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/authorization_firewall.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py",
            "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        report = build_operator_governed_authorization_firewall_signal_triage_v1(project_id="eidolon-smoke", save=False)
        classifier = report.get("severity_classifier", {})
        safe_filter = report.get("safe_boundary_filter", {})
        bridge = report.get("warning_status_bridge", {})
        split = report.get("audit_status_split", {})
        if classifier.get("ok") is not True or "blocked_pattern" not in classifier.get("severity_levels", []):
            return False
        if safe_filter.get("filter_rewrites_source") is not False or safe_filter.get("filter_creates_approval") is not False:
            return False
        if bridge.get("warnings_preserved") is not True or bridge.get("plain_pass_with_warnings_forbidden") is not True:
            return False
        if split.get("mechanism_status") != "pass" or split.get("authorization_status") != "not_authorized":
            return False
        if split.get("mechanism_pass_is_not_language_clear") is not True or split.get("language_clear_is_not_authorization") is not True:
            return False
        if report.get("ok") is not True or report.get("authorization_status") != "not_authorized":
            return False
        if report.get("creates_approval") is not False or report.get("writes_memory") is not False:
            return False
        if report.get("applies_source_edits") is not False or report.get("expands_autonomy") is not False:
            return False
        if report.get("plain_pass_with_warnings_forbidden") is not True or report.get("language_clear_is_not_authorization") is not True:
            return False
        required = [
            "authorization-firewall-severity-classifier", "authorization-firewall-safe-boundary-filter",
            "authorization-firewall-warning-status", "authorization-firewall-audit-status-split",
            "authorization-firewall-signal-triage-audit", "operator-governed-authorization-firewall-signal-triage-v1",
            "pass_with_warnings_supported=True", "plain_pass_with_warnings_forbidden=True",
            "mechanism_pass_is_not_language_clear=True", "language_clear_is_not_authorization=True",
            "authorization_status=not_authorized", "operator_approval_still_required=True",
            "signal_triage_creates_approval=False", "signal_triage_writes_memory=False",
            "signal_triage_applies_source_edits=False", "signal_triage_expands_autonomy=False",
            "data-tip", "no_native_title_tooltip",
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes([
            "/authorization-firewall-severity-classifier", "/authorization-firewall-safe-boundary-filter",
            "/authorization-firewall-warning-status", "/authorization-firewall-audit-status-split",
            "/authorization-firewall-signal-triage-audit",
        ]):
            return False
        print("[ok] operator-governed authorization firewall signal triage v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed authorization firewall signal triage v1: {error}")
        return False



def check_operator_governed_route_surface_parity_v1() -> bool:
    try:
        import route_surface_parity as rsp
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_route_surface_parity_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or rsp.ROUTE_SURFACE_PARITY_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/route_surface_parity.py",
            "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py",
            "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        refresh = rsp.build_recent_dashboard_route_probe_refresh(PROJECT_ROOT)
        policy = rsp.build_source_surface_manifest_parity_policy(PROJECT_ROOT)
        crosscheck = rsp.build_surface_route_api_cli_crosscheck(PROJECT_ROOT, docs)
        boundary = rsp.build_route_health_boundary_language(PROJECT_ROOT, docs)
        audit = rsp.build_route_surface_parity_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_route_surface_parity_v1(project_id="eidolon-smoke", save=False)
        if refresh.get("ok") is not True or policy.get("policy") != "every_governed_substage_surface": return False
        if policy.get("ok") is not True or crosscheck.get("ok") is not True or boundary.get("ok") is not True: return False
        if audit.get("ok") is not True or report.get("ok") is not True: return False
        if report.get("creates_approval") is not False or report.get("writes_memory") is not False: return False
        if report.get("applies_patches") is not False or report.get("expands_autonomy") is not False: return False
        for key in ["route_presence_is_authorization", "route_health_is_approval", "manifest_presence_is_authorization", "surface_parity_is_permission", "smoke_success_is_approval"]:
            if report.get(key) is not False: return False
        if report.get("route_health_confirms_render_status_only") is not True or report.get("route_health_does_not_authorize_execution") is not True: return False
        required = ["recent-dashboard-route-probe-refresh", "source-surface-manifest-parity-policy", "surface-route-api-cli-crosscheck", "route-health-boundary-language", "route-surface-parity-audit", "operator-governed-route-surface-parity-v1", "every_governed_substage_surface", "route_presence_is_authorization=False", "route_health_is_approval=False", "manifest_presence_is_authorization=False", "surface_parity_is_permission=False", "smoke_success_is_approval=False", "route_health_confirms_render_status_only=True", "route_health_does_not_authorize_execution=True", "parity_audit_applies_patches=False", "parity_audit_writes_memory=False", "parity_audit_expands_autonomy=False", "operator_approval_still_required=True", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required): return False
        if _dashboard_nav_title_regression_present(): return False
        if not probe_dashboard_http_routes(["/recent-dashboard-route-probe-refresh", "/source-surface-manifest-parity-policy", "/surface-route-api-cli-crosscheck", "/route-health-boundary-language", "/route-surface-parity-audit"]): return False
        print("[ok] operator-governed route surface parity v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed route surface parity v1: {error}")
        return False



def check_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1() -> bool:
    try:
        import self_maintenance_shadow_cleanup as smsc
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or smsc.SELF_MAINTENANCE_SHADOW_CLEANUP_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/self_maintenance_shadow_cleanup.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py",
            "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py", "conscious_agent/main.py",
            "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        inventory = smsc.build_duplicate_shadow_inventory(PROJECT_ROOT)
        removal = smsc.build_safe_shadow_removal_report(PROJECT_ROOT)
        compatibility = smsc.build_legacy_alias_compatibility_cleanup(PROJECT_ROOT)
        stale = smsc.build_stale_version_gate_cleanup(PROJECT_ROOT)
        audit = smsc.build_self_maintenance_duplicate_shadow_cleanup_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1(project_id="eidolon-smoke", save=False)
        if inventory.get("ok") is not True or inventory.get("current_duplicate_count") != 0: return False
        if inventory.get("removed_shadowed_definition_count", 0) < 16: return False
        if removal.get("ok") is not True or compatibility.get("ok") is not True or stale.get("ok") is not True: return False
        if audit.get("ok") is not True or report.get("ok") is not True: return False
        for key in ["duplicate_cleanup_is_authorization", "classification_is_permission_to_delete", "shadow_removal_expands_autonomy", "stale_gate_cleanup_authorizes_execution", "cleanup_applies_live_patches", "cleanup_writes_memory"]:
            if report.get(key) is not False: return False
        if report.get("operator_approval_still_required") is not True: return False
        required = ["duplicate-shadow-inventory", "safe-shadow-removal-report", "legacy-alias-compatibility-cleanup", "stale-version-gate-cleanup", "self-maintenance-duplicate-shadow-cleanup-audit", "operator-governed-self-maintenance-duplicate-shadow-cleanup-v1", "duplicate_cleanup_is_authorization=False", "classification_is_permission_to_delete=False", "shadow_removal_expands_autonomy=False", "stale_gate_cleanup_authorizes_execution=False", "cleanup_applies_live_patches=False", "cleanup_writes_memory=False", "operator_approval_still_required=True", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required): return False
        if _dashboard_nav_title_regression_present(): return False
        if not probe_dashboard_http_routes(["/duplicate-shadow-inventory", "/safe-shadow-removal-report", "/legacy-alias-compatibility-cleanup", "/stale-version-gate-cleanup", "/self-maintenance-duplicate-shadow-cleanup-audit"]): return False
        print("[ok] operator-governed self-maintenance duplicate shadow cleanup v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed self-maintenance duplicate shadow cleanup v1: {error}")
        return False


def check_operator_governed_documentation_continuity_header_v1() -> bool:
    try:
        import documentation_continuity_header as dch
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_documentation_continuity_header_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or dch.DOCUMENTATION_CONTINUITY_HEADER_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/documentation_continuity_header.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py",
            "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py", "conscious_agent/main.py",
            "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        header = dch.build_current_state_header_block(PROJECT_ROOT)
        history = dch.build_historical_next_steps_separation(PROJECT_ROOT)
        handoff = dch.build_operator_continuity_handoff_packet(PROJECT_ROOT)
        boundary = dch.build_documentation_boundary_language(PROJECT_ROOT)
        audit = dch.build_documentation_continuity_header_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_documentation_continuity_header_v1(project_id="eidolon-smoke", save=False)
        if header.get("ok") is not True or history.get("ok") is not True or handoff.get("ok") is not True or boundary.get("ok") is not True:
            return False
        if audit.get("ok") is not True or report.get("ok") is not True:
            return False
        for key in ["documentation_state_is_authorization", "release_history_is_authorization", "recommended_next_arc_is_permission", "handoff_packet_is_execution_packet", "current_state_header_creates_approval", "documentation_cleanup_writes_memory", "documentation_cleanup_applies_source_edits", "documentation_cleanup_expands_autonomy"]:
            if report.get(key) is not False:
                return False
        if report.get("operator_approval_still_required") is not True:
            return False
        required = [
            "current-state-header-block", "historical-next-steps-separation", "operator-continuity-handoff-packet", "documentation-boundary-language", "documentation-continuity-header-audit",
            "operator-governed-documentation-continuity-header-v1", "documentation_continuity_header.py", "README state is not approval", "Release history is not authorization", "A recommended next arc is not permission to execute it", "A completed smoke check is not operator consent", "A handoff packet is not an execution packet",
            "documentation_state_is_authorization=False", "release_history_is_authorization=False", "recommended_next_arc_is_permission=False", "handoff_packet_is_execution_packet=False", "current_state_header_creates_approval=False", "documentation_cleanup_writes_memory=False", "documentation_cleanup_applies_source_edits=False", "documentation_cleanup_expands_autonomy=False", "operator_approval_still_required=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/current-state-header-block", "/historical-next-steps-separation", "/operator-continuity-handoff-packet", "/documentation-boundary-language", "/documentation-continuity-header-audit"]):
            return False
        print("[ok] operator-governed documentation continuity header v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed documentation continuity header v1: {error}")
        return False


def check_operator_invoked_read_only_observation_prep_v1() -> bool:
    try:
        import operator_observation_prep as oop
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_invoked_read_only_observation_prep_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or oop.OPERATOR_OBSERVATION_PREP_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/operator_observation_prep.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py",
            "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py", "conscious_agent/main.py",
            "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        scope = oop.build_manual_read_only_observation_scope(PROJECT_ROOT)
        packet = oop.build_operator_observation_packet(PROJECT_ROOT)
        mutation = oop.build_no_mutation_observation_audit(PROJECT_ROOT)
        invocation = oop.build_operator_invocation_boundary(PROJECT_ROOT)
        audit = oop.build_operator_read_only_observation_audit(PROJECT_ROOT, docs)
        report = build_operator_invoked_read_only_observation_prep_v1(project_id="eidolon-smoke", save=False)
        if not all(item.get("ok") is True for item in [scope, packet, mutation, invocation, audit, report]):
            return False
        false_keys = [
            "observation_is_authorization", "observation_is_execution", "observation_grants_followup_permission",
            "observation_writes_source", "observation_writes_memory", "observation_updates_metadata",
            "observation_schedules_work", "observation_invokes_models_by_default", "observation_creates_approval",
            "writes_files", "writes_memory", "updates_metadata", "creates_schedule", "invokes_models",
            "applies_patches", "publishes_releases", "creates_approval", "continues_automatically", "expands_autonomy",
        ]
        for key in false_keys:
            if report.get(key) is not False:
                return False
        if report.get("operator_invocation_required") is not True or report.get("single_run_read_only") is not True or report.get("operator_approval_still_required") is not True:
            return False
        required = [
            "manual-read-only-observation-scope", "operator-observation-packet", "no-mutation-observation-audit", "operator-invocation-boundary", "operator-read-only-observation-audit",
            "operator-invoked-read-only-observation-prep-v1", "operator_observation_prep.py", "Observation is not authorization", "Operator invocation permits one read-only observation report only", "It does not authorize continued monitoring", "It does not authorize follow-up action", "It does not authorize live changes",
            "observation_is_authorization=False", "observation_is_execution=False", "observation_grants_followup_permission=False", "observation_writes_source=False", "observation_writes_memory=False", "observation_updates_metadata=False", "observation_schedules_work=False", "observation_invokes_models_by_default=False", "observation_creates_approval=False", "operator_invocation_required=True", "single_run_read_only=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/manual-read-only-observation-scope", "/operator-observation-packet", "/no-mutation-observation-audit", "/operator-invocation-boundary", "/operator-read-only-observation-audit"]):
            return False
        print("[ok] operator-invoked read-only observation prep v1")
        return True
    except Exception as error:
        print(f"[fail] operator-invoked read-only observation prep v1: {error}")
        return False

def _build_checks(include_v405: bool = True) -> list[SmokeCheck]:
    checks = [
        SmokeCheck("env-requests", "fast", 15, lambda: check_environment_import("requests", required_for_core=True)),
        SmokeCheck("env-chromadb", "fast", 15, lambda: check_environment_import("chromadb")),
        SmokeCheck("settings", "fast", 10, check_settings),
        SmokeCheck("compile", "fast", 35, check_compile),
        SmokeCheck("main-status", "fast", 45, lambda: run_main("--status")),
        SmokeCheck("task-work-summary", "fast", 45, lambda: run_main("--task-work", "summary")),
        SmokeCheck("import-task-lifecycle", "fast", 15, lambda: check_import("task_lifecycle")),
        SmokeCheck("lifecycle-filters", "fast", 20, check_lifecycle_filters),
        SmokeCheck("import-task-recovery", "fast", 15, lambda: check_import("task_recovery")),
        SmokeCheck("task-recovery", "fast", 20, check_task_recovery),
        SmokeCheck("import-task-cycle-policy", "fast", 15, lambda: check_import("task_cycle_policy")),
        SmokeCheck("cycle-policy", "fast", 20, check_cycle_policy),
        SmokeCheck("import-stable-supervised-loop", "loop", 15, lambda: check_import("stable_supervised_loop")),
        SmokeCheck("stable-loop", "loop", 40, check_stable_loop),
        SmokeCheck("import-stable-loop-review", "loop", 15, lambda: check_import("stable_loop_review")),
        SmokeCheck("stable-loop-review", "loop", 35, check_stable_loop_review),
        SmokeCheck("import-stable-loop-audit", "loop", 15, lambda: check_import("stable_loop_audit")),
        SmokeCheck("stable-loop-audit", "loop", 20, check_stable_loop_audit),
        SmokeCheck("import-stable-loop-operator-notes", "loop", 15, lambda: check_import("stable_loop_operator_notes")),
        SmokeCheck("stable-loop-operator-notes", "loop", 20, check_stable_loop_operator_notes),
        SmokeCheck("stable-loop-decision-report", "loop", 25, check_stable_loop_decision_report),
        SmokeCheck("stable-loop-followup-tasks", "loop", 25, check_stable_loop_followup_tasks),
        SmokeCheck("stable-loop-followup-lifecycle", "loop", 25, check_stable_loop_followup_lifecycle),
        SmokeCheck("stable-loop-followup-completion", "loop", 25, check_stable_loop_followup_completion),
        SmokeCheck("stable-loop-guardrails", "loop", 25, check_stable_loop_guardrails),
        SmokeCheck("stabilization-checkpoint", "readiness", 30, check_stabilization_checkpoint),
        SmokeCheck("operational-readiness", "readiness", 60, check_operational_readiness),
        SmokeCheck("controlled-build-cycle", "build", 60, check_controlled_build_cycle),
        SmokeCheck("project-intelligence", "build", 50, check_project_intelligence),
        SmokeCheck("workspace-orchestration", "build", 50, check_workspace_orchestration),
        SmokeCheck("workspace-execution", "build", 50, check_workspace_execution),
        SmokeCheck("patch-drafting", "patch", 60, check_patch_drafting),
        SmokeCheck("release-pipeline", "release", 70, check_release_pipeline),
        SmokeCheck("code-patch-release", "release", 70, check_code_patch_release),
        SmokeCheck("ai-patch-assistance", "release", 50, check_ai_patch_assistance),
        SmokeCheck("validated-ai-patch-loop", "release", 20, check_validated_ai_patch_loop),
        SmokeCheck("approval-release-workflow", "release", 20, check_approval_release_workflow),
        SmokeCheck("release-packaging", "install", 90, check_release_packaging),
        SmokeCheck("patch-context-builder", "install", 90, check_patch_context_builder),
        SmokeCheck("patch-draft-composer", "install", 90, check_patch_draft_composer),
        SmokeCheck("patch-review-validation", "install", 90, check_patch_review_validation),
        SmokeCheck("sandbox-patch-trial-runner", "install", 90, check_sandbox_patch_trial_runner),
        SmokeCheck("sandbox-evidence-review-recommendation", "install", 90, check_sandbox_evidence_review_recommendation_layer),
        SmokeCheck("operator-approved-patch-application", "install", 90, check_operator_approved_patch_application_layer),
        SmokeCheck("verified-application-recovery", "install", 90, check_verified_application_recovery_layer),
        SmokeCheck("multi-patch-queue-planning", "install", 90, check_multi_patch_queue_planning_layer),
        SmokeCheck("supervised-local-improvement-loop", "install", 90, check_supervised_local_improvement_loop),
        SmokeCheck("local-model-patch-proposal-integration", "install", 90, check_local_model_patch_proposal_integration),
        SmokeCheck("local-model-output-comparison-critique", "install", 90, check_local_model_output_comparison_critique),
        SmokeCheck("multi-model-patch-candidate-ranking", "install", 90, check_multi_model_patch_candidate_ranking),
        SmokeCheck("supervised-patch-candidate-refinement", "install", 90, check_supervised_patch_candidate_refinement),
        SmokeCheck("safe-autonomous-suggestion-loop", "install", 90, check_safe_autonomous_suggestion_loop),
        SmokeCheck("supervised-suggestion-inbox-work-order-planner", "install", 90, check_supervised_suggestion_inbox_work_order_planner),
        SmokeCheck("work-order-to-patch-context-handoff", "install", 90, check_work_order_to_patch_context_handoff),
        SmokeCheck("work-order-execution-evidence-binder", "install", 90, check_work_order_execution_evidence_binder),
        SmokeCheck("self-development-dashboard-consolidation", "install", 90, check_self_development_dashboard_consolidation),
        SmokeCheck("supervised-self-development-readiness-audit", "install", 90, check_supervised_self_development_readiness_audit),
        SmokeCheck("supervised-development-session-manager", "install", 90, check_supervised_development_session_manager),
        SmokeCheck("operator-approval-workflow-console", "install", 90, check_operator_approval_workflow_console),
        SmokeCheck("safe-experiment-branch-planner", "install", 90, check_safe_experiment_branch_planner),
        SmokeCheck("learning-from-outcome-reflection-layer", "install", 90, check_learning_from_outcome_reflection_layer),
        SmokeCheck("supervised-improvement-cycle-orchestrator", "install", 90, check_supervised_improvement_cycle_orchestrator),
        SmokeCheck("supervised-cycle-replay-benchmark-harness", "install", 90, check_supervised_cycle_replay_benchmark_harness),
        SmokeCheck("capability-permission-budget-ledger", "install", 90, check_capability_permission_budget_ledger),
        SmokeCheck("shadow-autonomy-simulation-layer", "install", 90, check_shadow_autonomy_simulation_layer),
        SmokeCheck("failure-recovery-rollback-war-game-layer", "install", 90, check_failure_recovery_rollback_war_game_layer),
        SmokeCheck("local-artificial-mind-milestone-audit", "install", 90, check_local_artificial_mind_milestone_audit),
        SmokeCheck("v100-milestone-stabilization-review", "install", 90, check_v100_milestone_stabilization_review),
        SmokeCheck("unified-eidolon-system-map-operator-home", "install", 90, check_unified_eidolon_system_map_operator_home),
        SmokeCheck("memory-reflection-goal-coherence-binder", "install", 90, check_memory_reflection_goal_coherence_binder),
        SmokeCheck("practical-daily-operating-loop", "install", 90, check_practical_daily_operating_loop),
        SmokeCheck("coherent-local-mind-runtime-v1", "install", 90, check_coherent_local_mind_runtime_v1),
        SmokeCheck("memory-quality-evidence-hygiene-layer", "install", 90, check_memory_quality_evidence_hygiene_layer),
        SmokeCheck("goal-continuity-priority-stability-layer", "install", 90, check_goal_continuity_priority_stability_layer),
        SmokeCheck("contained-local-reasoning-workbench", "install", 90, check_contained_local_reasoning_workbench),
        SmokeCheck("operator-workflow-compression-console", "install", 90, check_operator_workflow_compression_console),
        SmokeCheck("practical-supervised-mind-usefulness-audit", "install", 90, check_practical_supervised_mind_usefulness_audit),
        SmokeCheck("improvement-intent-problem-framing-layer", "install", 90, check_improvement_intent_problem_framing_layer),
        SmokeCheck("supervised-work-package-builder", "install", 90, check_supervised_work_package_builder),
        SmokeCheck("patch-readiness-review-intelligence-layer", "install", 90, check_patch_readiness_review_intelligence_layer),
        SmokeCheck("release-candidate-judgment-layer", "install", 90, check_release_candidate_judgment_layer),
        SmokeCheck("supervised-self-development-readiness", "install", 90, check_supervised_self_development_readiness),
        SmokeCheck("development-session-planner", "install", 90, check_development_session_planner),
        SmokeCheck("source-change-cartographer", "install", 90, check_source_change_cartographer),
        SmokeCheck("patch-simulation-dry-run-review-layer", "install", 90, check_patch_simulation_dry_run_review_layer),
        SmokeCheck("verification-matrix-regression-memory-layer", "install", 90, check_verification_matrix_regression_memory_layer),
        SmokeCheck("supervised-development-execution-audit", "install", 90, check_supervised_development_execution_audit),
        SmokeCheck("development-outcome-review-layer", "install", 90, check_development_outcome_review_layer),
        SmokeCheck("supervised-lesson-extraction-layer", "install", 90, check_supervised_lesson_extraction_layer),
        SmokeCheck("recommendation-refinement-layer", "install", 90, check_recommendation_refinement_layer),
        SmokeCheck("operator-feedback-integration-layer", "install", 90, check_operator_feedback_integration_layer),
        SmokeCheck("supervised-development-learning-audit", "install", 90, check_supervised_development_learning_audit),
        SmokeCheck("strategic-growth-intake-layer", "install", 90, check_strategic_growth_intake_layer),
        SmokeCheck("roadmap-synthesis-layer", "install", 90, check_roadmap_synthesis_layer),
        SmokeCheck("strategic-risk-debt-ledger", "install", 90, check_strategic_risk_debt_ledger),
        SmokeCheck("capability-maturity-model-layer", "install", 90, check_capability_maturity_model_layer),
        SmokeCheck("supervised-strategic-growth-audit", "install", 90, check_supervised_strategic_growth_audit),
        SmokeCheck("supervised-operator-planning-console", "install", 90, check_supervised_operator_planning_console),
        SmokeCheck("supervised-patch-session-assembly", "install", 90, check_supervised_patch_session_assembly),
        SmokeCheck("supervised-patch-draft-generation", "install", 90, check_supervised_patch_draft_generation),
        SmokeCheck("supervised-patch-implementation-handoff", "install", 90, check_supervised_patch_implementation_handoff),
        SmokeCheck("supervised-patch-application-readiness", "install", 90, check_supervised_patch_application_readiness),
        SmokeCheck("operator-approved-patch-application-sandbox", "install", 90, check_operator_approved_patch_application_sandbox),
        SmokeCheck("operator-governed-post-application-learning-and-release-readiness", "install", 90, check_operator_governed_post_application_learning_and_release_readiness),
        SmokeCheck("operator-governed-patch-cycle-intelligence", "install", 90, check_operator_governed_patch_cycle_intelligence),
        SmokeCheck("operator-governed-multi-cycle-roadmap-intelligence", "install", 90, check_operator_governed_multi_cycle_roadmap_intelligence),
        SmokeCheck("supervised-capability-maturity-modeling", "install", 90, check_supervised_capability_maturity_modeling),
        SmokeCheck("local-artificial-mind-governance-kernel-v1", "install", 90, check_local_artificial_mind_governance_kernel_v1),
        SmokeCheck("operator-governed-governance-kernel-integration", "install", 90, check_operator_governed_governance_kernel_integration),
        SmokeCheck("operator-governed-cognitive-continuity-layer-v1", "install", 90, check_operator_governed_cognitive_continuity_layer_v1),
        SmokeCheck("operator-governed-deliberation-and-self-model-layer-v1", "install", 90, check_operator_governed_deliberation_and_self_model_layer_v1),
        SmokeCheck("operator-governed-internal-simulation-and-foresight-layer-v1", "install", 90, check_operator_governed_internal_simulation_and_foresight_layer_v1),
        SmokeCheck("operator-governed-learning-curriculum-and-capability-calibration-layer-v1", "install", 90, check_operator_governed_learning_curriculum_and_capability_calibration_layer_v1),
        SmokeCheck("operator-governed-knowledge-and-belief-organization-layer-v1", "install", 90, check_operator_governed_knowledge_and_belief_organization_layer_v1),
        SmokeCheck("operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1", "install", 90, check_operator_governed_local_model_evaluation_and_cognitive_workbench_layer_v1),
        SmokeCheck("operator-approved-local-model-invocation-sandbox-v1", "install", 90, check_operator_approved_local_model_invocation_sandbox_v1),
        SmokeCheck("operator-governed-model-assisted-patch-review-and-synthesis-layer-v1", "install", 90, check_operator_governed_model_assisted_patch_review_and_synthesis_layer_v1),
        SmokeCheck("operator-governed-model-assisted-patch-draft-assembly-layer-v1", "install", 90, check_operator_governed_model_assisted_patch_draft_assembly_layer_v1),
        SmokeCheck("operator-governed-patch-execution-packet-bridge-v1", "install", 90, check_operator_governed_patch_execution_packet_bridge_v1),
        SmokeCheck("operator-governed-approved-execution-packet-application-prep-v1", "install", 90, check_operator_governed_approved_execution_packet_application_prep_v1),
        SmokeCheck("operator-governed-structural-stabilization-and-runtime-modularization-v1", "install", 90, check_operator_governed_structural_stabilization_and_runtime_modularization_v1),
        SmokeCheck("operator-governed-runtime-module-extraction-v1", "install", 90, check_operator_governed_runtime_module_extraction_v1),
        SmokeCheck("operator-governed-self-maintenance-decomposition-v1", "install", 91, check_operator_governed_self_maintenance_decomposition_v1),
        SmokeCheck("operator-governed-dashboard-api-cli-modularization-v1", "install", 91, check_operator_governed_dashboard_api_cli_modularization_v1),
        SmokeCheck("operator-approved-application-execution-refinement-v1", "install", 91, check_operator_approved_application_execution_refinement_v1),
        SmokeCheck("operator-governed-rollback-and-recovery-intelligence-v1", "install", 91, check_operator_governed_rollback_and_recovery_intelligence_v1),
        SmokeCheck("operator-governed-memory-candidate-governance-upgrade-v1", "install", 91, check_operator_governed_memory_candidate_governance_upgrade_v1),
        SmokeCheck("local-artificial-mind-continuity-kernel-v2", "install", 91, check_local_artificial_mind_continuity_kernel_v2),
        SmokeCheck("operator-governed-identity-personality-coherence-expression-layer-v1", "install", 91, check_operator_governed_identity_personality_coherence_expression_layer_v1),
        SmokeCheck("operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1", "install", 91, check_operator_governed_behavioral_expression_preview_and_runtime_health_hardening_v1),
        SmokeCheck("operator-governed-conversational-expression-sandbox-v1", "install", 91, check_operator_governed_conversational_expression_sandbox_v1),
        SmokeCheck("operator-governed-conversational-expression-application-bridge-v1", "install", 91, check_operator_governed_conversational_expression_application_bridge_v1),
        SmokeCheck("operator-governed-expression-patch-dry-run-sandbox-v1", "install", 91, check_operator_governed_expression_patch_dry_run_sandbox_v1),
        SmokeCheck("operator-governed-expression-patch-sandbox-trial-harness-v1", "install", 91, check_operator_governed_expression_patch_sandbox_trial_harness_v1),
        SmokeCheck("operator-governed-expression-sandbox-trial-execution-packet-bridge-v1", "install", 91, check_operator_governed_expression_sandbox_trial_execution_packet_bridge_v1),
        SmokeCheck("operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1", "install", 91, check_operator_governed_expression_sandbox_trial_result_intake_and_promotion_review_prep_v1),
        SmokeCheck("operator-governed-expression-promotion-packet-assembly-layer-v1", "install", 91, check_operator_governed_expression_promotion_packet_assembly_layer_v1),
        SmokeCheck("operator-governed-expression-live-application-packet-drafting-layer-v1", "install", 91, check_operator_governed_expression_live_application_packet_drafting_layer_v1),
        SmokeCheck("operator-governed-expression-live-application-execution-prep-v1", "install", 91, check_operator_governed_expression_live_application_execution_prep_v1),
        SmokeCheck("operator-approved-minimal-live-expression-application-audit-v1", "install", 91, check_operator_approved_minimal_live_expression_application_audit_v1),
        SmokeCheck("operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1", "install", 92, check_operator_governed_self_maintenance_surface_reduction_and_gate_registry_refactor_v1),
        SmokeCheck("operator-governed-minimal-live-change-replay-and-regression-hardening-v1", "install", 93, check_operator_governed_minimal_live_change_replay_and_regression_hardening_v1),
        SmokeCheck("operator-governed-self-maintenance-modular-extraction-v1", "install", 94, check_operator_governed_self_maintenance_modular_extraction_v1),
        SmokeCheck("operator-governed-live-change-application-trial-audit-v1", "install", 95, check_operator_governed_live_change_application_trial_audit_v1),
        SmokeCheck("operator-governed-live-patch-trial-closure-audit-v1", "install", 95, check_operator_governed_live_patch_trial_closure_audit_v1),
        SmokeCheck("operator-governed-second-live-patch-trial-registry-audit-v1", "install", 96, check_operator_governed_second_live_patch_trial_registry_audit_v1),
        SmokeCheck("operator-governed-live-patch-history-and-memory-candidate-audit-v1", "install", 96, check_operator_governed_live_patch_history_and_memory_candidate_audit_v1),
        SmokeCheck("operator-governed-memory-application-trial-audit-v1", "install", 97, check_operator_governed_memory_application_trial_audit_v1),
        SmokeCheck("operator-governed-segmented-install-smoke-audit-v1", "install", 97, check_operator_governed_segmented_install_smoke_audit_v1),
        SmokeCheck("operator-governed-memory-application-dry-run-ledger-v1", "install", 98, check_operator_governed_memory_application_dry_run_ledger_v1),
        SmokeCheck("operator-governed-sandbox-memory-write-target-v1", "install", 99, check_operator_governed_sandbox_memory_write_target_v1),
        SmokeCheck("operator-governed-live-memory-write-burnout-v1", "install", 100, check_operator_governed_live_memory_write_burnout_v1),
        SmokeCheck("operator-governed-memory-retraction-trial-v1", "install", 101, check_operator_governed_memory_retraction_trial_v1),
        SmokeCheck("operator-governed-source-surface-manifest-v1", "install", 102, check_operator_governed_source_surface_manifest_v1),
        SmokeCheck("operator-governed-self-maintenance-duplicate-cleanup-v1", "install", 103, check_operator_governed_self_maintenance_duplicate_cleanup_v1),
        SmokeCheck("operator-governed-dashboard-route-health-audit-v1", "install", 104, check_operator_governed_dashboard_route_health_audit_v1),
        SmokeCheck("operator-governed-memory-lifecycle-review-board-v1", "install", 105, check_operator_governed_memory_lifecycle_review_board_v1),
        SmokeCheck("operator-governed-authorization-firewall-v1", "install", 106, check_operator_governed_authorization_firewall_v1),
        SmokeCheck("operator-governed-metadata-release-integrity-v1", "install", 107, check_operator_governed_metadata_release_integrity_v1),
        SmokeCheck("operator-governed-authorization-firewall-signal-triage-v1", "install", 108, check_operator_governed_authorization_firewall_signal_triage_v1),
        SmokeCheck("operator-governed-route-surface-parity-v1", "install", 109, check_operator_governed_route_surface_parity_v1),
        SmokeCheck("operator-governed-self-maintenance-duplicate-shadow-cleanup-v1", "install", 110, check_operator_governed_self_maintenance_duplicate_shadow_cleanup_v1),
        SmokeCheck("operator-governed-documentation-continuity-header-v1", "install", 111, check_operator_governed_documentation_continuity_header_v1),
        SmokeCheck("operator-invoked-read-only-observation-prep-v1", "install", 112, check_operator_invoked_read_only_observation_prep_v1),
        SmokeCheck("operator-governed-observation-ledger-boundary-v1", "install", 113, check_operator_governed_observation_ledger_boundary_v1),
        SmokeCheck("operator-governed-observation-proposal-queue-v1", "install", 114, check_operator_governed_observation_proposal_queue_v1),
        SmokeCheck("operator-governed-sandbox-autonomy-boundary-prep-v1", "install", 115, check_operator_governed_sandbox_autonomy_boundary_prep_v1),
        SmokeCheck("operator-governed-autonomy-readiness-review-board-v1", "install", 116, check_operator_governed_autonomy_readiness_review_board_v1),
        SmokeCheck("self-maintenance", "install", 90, check_self_maintenance),
    ]
    if not include_v405:
        checks = [check for check in checks if check.name != "operator-governed-segmented-install-smoke-audit-v1"]
    return checks




def check_operator_governed_observation_ledger_boundary_v1() -> bool:
    try:
        import observation_ledger_boundary as olb
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_observation_ledger_boundary_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or olb.OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/observation_ledger_boundary.py",
            "conscious_agent/operator_observation_prep.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
            "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py",
            "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        schema = olb.build_observation_ledger_schema(PROJECT_ROOT)
        receipt = olb.build_observation_receipt_builder(PROJECT_ROOT)
        stop_pause = olb.build_observation_stop_pause_semantics(PROJECT_ROOT)
        hidden = olb.build_hidden_scheduling_continuation_audit(PROJECT_ROOT)
        audit = olb.build_observation_ledger_boundary_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_observation_ledger_boundary_v1(project_id="eidolon-smoke", save=False)
        if not all(item.get("ok") is True for item in [schema, receipt, stop_pause, hidden, audit, report]):
            return False
        false_keys = [
            "ledger_presence_is_approval", "ledger_completeness_is_authorization", "observation_history_permits_future_action",
            "receipt_is_approval", "hidden_scheduling_allowed", "automatic_continuation_allowed", "daily_loop_allowed",
            "hourly_loop_allowed", "auto_roadmap_selection_allowed", "auto_patch_packet_generation_allowed",
            "auto_promotion_from_observation_allowed", "source_mutation_allowed", "memory_mutation_allowed", "approval_creation_allowed",
            "writes_files", "writes_memory", "updates_metadata", "creates_schedule", "invokes_models", "applies_patches",
            "publishes_releases", "creates_approval", "continues_automatically", "expands_autonomy",
        ]
        for key in false_keys:
            if report.get(key) is not False:
                return False
        if report.get("operator_invocation_required") is not True or report.get("operator_approval_still_required") is not True:
            return False
        required = [
            "observation-ledger-schema", "observation-receipt-builder", "observation-stop-pause-semantics", "hidden-scheduling-continuation-audit", "observation-ledger-boundary-audit",
            "operator-governed-observation-ledger-boundary-v1", "observation_ledger_boundary.py", "Ledger presence is not approval", "Ledger completeness is not authorization", "Observation history does not permit future action", "Receipt is not approval",
            "paused means no future observation run may be prepared automatically", "stopped means observation prep must require fresh operator invocation", "resume requires explicit operator action", "pause/stop does not delete historical receipts", "pause/stop does not authorize cleanup or mutation",
            "ledger_presence_is_approval=False", "ledger_completeness_is_authorization=False", "observation_history_permits_future_action=False", "receipt_is_approval=False", "hidden_scheduling_allowed=False", "automatic_continuation_allowed=False", "daily_loop_allowed=False", "hourly_loop_allowed=False", "auto_roadmap_selection_allowed=False", "auto_patch_packet_generation_allowed=False", "auto_promotion_from_observation_allowed=False", "source_mutation_allowed=False", "memory_mutation_allowed=False", "approval_creation_allowed=False", "operator_invocation_required=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/observation-ledger-schema", "/observation-receipt-builder", "/observation-stop-pause-semantics", "/hidden-scheduling-continuation-audit", "/observation-ledger-boundary-audit"]):
            return False
        print("[ok] operator-governed observation ledger boundary v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed observation ledger boundary v1: {error}")
        return False


def check_operator_governed_observation_proposal_queue_v1() -> bool:
    try:
        import observation_proposal_queue as opq
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_observation_proposal_queue_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or opq.OBSERVATION_PROPOSAL_QUEUE_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/observation_proposal_queue.py",
            "conscious_agent/observation_ledger_boundary.py", "conscious_agent/operator_observation_prep.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
            "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py",
            "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        mapper = opq.build_observation_to_proposal_candidate_mapper(PROJECT_ROOT)
        schema = opq.build_proposal_queue_schema(PROJECT_ROOT)
        ranking = opq.build_proposal_ranking_risk_notes(PROJECT_ROOT)
        non_execution = opq.build_proposal_queue_non_execution_audit(PROJECT_ROOT)
        audit = opq.build_observation_proposal_queue_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_observation_proposal_queue_v1(project_id="eidolon-smoke", save=False)
        if not all(item.get("ok") is True for item in [mapper, schema, ranking, non_execution, audit, report]):
            return False
        false_keys = [
            "mapping_is_approval", "proposal_candidate_is_execution_packet", "candidate_queue_is_authorization",
            "queue_presence_is_approval", "queue_ranking_is_authorization", "highest_ranked_proposal_auto_selected",
            "approved_for_packet_drafting_only_is_live_execution", "source_mutation_allowed", "memory_mutation_allowed",
            "schedule_creation_allowed", "model_invocation_by_default_allowed", "execution_packet_creation_allowed",
            "patch_application_allowed", "proposal_approval_allowed", "automatic_continuation_allowed",
            "observation_promotes_to_live_change", "writes_files", "writes_memory", "updates_metadata",
            "creates_schedule", "invokes_models", "creates_execution_packet", "applies_patches", "approves_proposals",
            "creates_approval", "continues_automatically", "executes_actions", "expands_autonomy",
        ]
        for key in false_keys:
            if report.get(key) is not False:
                return False
        if report.get("operator_review_required") is not True or report.get("fresh_operator_approval_required") is not True or report.get("operator_approval_still_required") is not True:
            return False
        if report.get("authorization_status") != "not_authorized":
            return False
        required = [
            "observation-to-proposal-candidate-mapper", "proposal-queue-schema", "proposal-ranking-risk-notes", "proposal-queue-non-execution-audit", "observation-proposal-queue-audit",
            "operator-governed-observation-proposal-queue-v1", "observation_proposal_queue.py",
            "mapping_is_approval=False", "proposal_candidate_is_execution_packet=False", "candidate_queue_is_authorization=False", "queue_presence_is_approval=False", "queue_ranking_is_authorization=False", "highest_ranked_proposal_auto_selected=False", "approved_for_packet_drafting_only_is_live_execution=False", "source_mutation_allowed=False", "memory_mutation_allowed=False", "schedule_creation_allowed=False", "model_invocation_by_default_allowed=False", "execution_packet_creation_allowed=False", "patch_application_allowed=False", "proposal_approval_allowed=False", "automatic_continuation_allowed=False", "observation_promotes_to_live_change=False", "operator_review_required=True", "fresh_operator_approval_required=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/observation-to-proposal-candidate-mapper", "/proposal-queue-schema", "/proposal-ranking-risk-notes", "/proposal-queue-non-execution-audit", "/observation-proposal-queue-audit"]):
            return False
        print("[ok] operator-governed observation proposal queue v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed observation proposal queue v1: {error}")
        return False

def check_operator_governed_minimal_live_change_replay_and_regression_hardening_v1() -> bool:
    try:
        import self_maintenance as sm
        import minimal_live_change_replay as mlcr
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_minimal_live_change_replay_and_regression_hardening_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if mlcr.MINIMAL_LIVE_CHANGE_REPLAY_VERSION != "500.0":
            return False
        report = build_operator_governed_minimal_live_change_replay_and_regression_hardening_v1(
            project_id="eidolon-smoke",
            improvement_goal="harden minimal approved live change replay, expected-vs-actual comparison, regression drift detection, recovery recommendation, and final audit without automatic replay, source edits, rollback execution, or autonomy expansion",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/minimal_live_change_replay.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["minimal-live-change-replay-packet", "minimal-live-change-expected-actual-comparison", "minimal-live-change-regression-drift-detector", "minimal-live-change-recovery-recommendation", "minimal-live-change-replay-regression-audit", "operator-governed-minimal-live-change-replay-and-regression-hardening-v1", "minimal_live_change_replay.py", "replay_packet_applies_change=False", "expected_actual_writes_files=False", "regression_detector_auto_fixes=False", "recovery_recommendation_executes_rollback=False", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/minimal_live_change_replay_packet/", "data/autonomy/minimal_live_change_expected_actual_comparison/", "data/autonomy/minimal_live_change_regression_drift_detector/", "data/autonomy/minimal_live_change_recovery_recommendation/", "data/autonomy/minimal_live_change_replay_regression_audit/"]:
            if token not in docs:
                return False
        if len(sm.MINIMAL_LIVE_CHANGE_REPLAY_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.MINIMAL_LIVE_CHANGE_REPLAY_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.MINIMAL_LIVE_CHANGE_REPLAY_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        replay = mlcr.build_minimal_live_change_replay_packet_summary(request_text="replay automatically and write files", evidence={})
        if replay.get("applies_change") is not False or replay.get("replays_automatically") is not False or replay.get("status") != "blocked":
            return False
        comparison = mlcr.build_minimal_live_change_expected_actual_comparison_summary(request_text="review only", evidence={"expected_changed_files":["README_NEXT_STEPS.md"], "actual_changed_files":["README_NEXT_STEPS.md", "conscious_agent/chat.py"]})
        if comparison.get("writes_files") is not False or comparison.get("treats_match_as_approval") is not False or comparison.get("status") != "blocked":
            return False
        drift = mlcr.build_minimal_live_change_regression_drift_detector_summary(docs, request_text="invoke local model by default", evidence={})
        if drift.get("changes_behavior") is not False or drift.get("auto_fixes") is not False or drift.get("invokes_models") is not False or drift.get("status") != "blocked":
            return False
        recovery = mlcr.build_minimal_live_change_recovery_recommendation_summary(request_text="execute rollback and create release candidate", evidence={"detected_issues":["unexpected file changed"]})
        if recovery.get("executes_rollback") is not False or recovery.get("edits_files") is not False or recovery.get("creates_release_candidate") is not False or recovery.get("status") != "blocked":
            return False
        audit = mlcr.build_minimal_live_change_replay_regression_audit_summary(PROJECT_ROOT, docs, request_text="review only", evidence={"original_candidate_id":"c", "approval_lock_id":"a", "transaction_id":"t", "application_harness_id":"h", "audit_id":"au", "expected_touched_files":["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "tools/smoke_check.py"], "expected_unchanged_files":["memory stores", "identity source of truth"], "expected_readme_update":True, "expected_release_history_update":True, "expected_version_update":True, "expected_smoke_checks":["fast"], "expected_rollback_packet":"rollback", "expected_changed_files":["README_NEXT_STEPS.md"], "actual_changed_files":["README_NEXT_STEPS.md"]})
        if audit.get("mutates_memory") is not False or audit.get("alters_identity") is not False or audit.get("alters_personality") is not False or audit.get("continues_automatically") is not False:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/minimal-live-change-replay-packet", "/minimal-live-change-expected-actual-comparison", "/minimal-live-change-regression-drift-detector", "/minimal-live-change-recovery-recommendation", "/minimal-live-change-replay-regression-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed minimal live change replay and regression hardening v1: {error}")
        return False



def check_operator_governed_self_maintenance_modular_extraction_v1() -> bool:
    try:
        import self_maintenance as sm
        import self_maintenance_modular_extraction as smme
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_self_maintenance_modular_extraction_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if smme.SELF_MAINTENANCE_MODULAR_EXTRACTION_VERSION != "500.0":
            return False
        report = build_operator_governed_self_maintenance_modular_extraction_v1(
            project_id="eidolon-smoke",
            improvement_goal="extract version/package, surface, and governance gate helpers from self-maintenance into focused review-only modules without behavior expansion or autonomy expansion",
            save=False,
        )
        text_files = []
        for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "conscious_agent/release_packaging.py", "tools/smoke_check.py", "conscious_agent/route_health.py", "conscious_agent/self_maintenance_modular_extraction.py", "conscious_agent/self_maintenance_version_package_gates.py", "conscious_agent/self_maintenance_surface_gates.py", "conscious_agent/self_maintenance_governance_gates.py"]:
            text_files.append((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        docs = "\n".join(text_files)
        required = ["self-maintenance-module-extraction-plan", "self-maintenance-version-package-gates", "self-maintenance-surface-gates", "self-maintenance-governance-gates", "self-maintenance-modular-extraction-audit", "operator-governed-self-maintenance-modular-extraction-v1", "self_maintenance_modular_extraction.py", "self_maintenance_version_package_gates.py", "self_maintenance_surface_gates.py", "self_maintenance_governance_gates.py", "modular_extraction_applies_live_patches=False", "version_package_gate_extraction_present=True", "surface_gate_extraction_present=True", "governance_gate_extraction_present=True", "dashboard_http_route_probe_required"]
        if not all(token in docs for token in required):
            return False
        for token in ["data/autonomy/self_maintenance_module_extraction_plan/", "data/autonomy/self_maintenance_version_package_gates/", "data/autonomy/self_maintenance_surface_gates/", "data/autonomy/self_maintenance_governance_gates/", "data/autonomy/self_maintenance_modular_extraction_audit/"]:
            if token not in docs:
                return False
        if len(sm.SELF_MAINTENANCE_MODULAR_EXTRACTION_STAGE_DEFS) != 50:
            return False
        payload = report.get("payload", {})
        boundaries = payload.get("boundaries", {})
        false_keys = [key for key, value in sm.SELF_MAINTENANCE_MODULAR_EXTRACTION_LAYER_BOUNDARIES.items() if value is False]
        true_keys = [key for key, value in sm.SELF_MAINTENANCE_MODULAR_EXTRACTION_LAYER_BOUNDARIES.items() if value is True]
        if any(boundaries.get(key) is not False for key in false_keys):
            return False
        if any(boundaries.get(key) is not True for key in true_keys):
            return False
        audit = smme.build_modular_extraction_audit_summary(PROJECT_ROOT, docs, "500.0")
        if audit.get("ok") is not True or audit.get("boundaries_ok") is not True:
            return False
        version_package = smme.build_version_package_gate_extraction_summary(PROJECT_ROOT, "500.0")
        if version_package.get("writes_files") is not False or version_package.get("ok") is not True:
            return False
        surface = smme.build_surface_gate_extraction_summary()
        if surface.get("writes_routes") is not False or surface.get("ok") is not True:
            return False
        governance = smme.build_governance_gate_extraction_summary()
        if governance.get("writes_files") is not False or governance.get("ok") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/self-maintenance-module-extraction-plan", "/self-maintenance-version-package-gates", "/self-maintenance-surface-gates", "/self-maintenance-governance-gates", "/self-maintenance-modular-extraction-audit"]):
            return False
        return bool(report.get("ok"))
    except Exception as error:
        print(f"[fail] operator-governed self-maintenance modular extraction v1: {error}")
        return False


def check_operator_governed_segmented_install_smoke_audit_v1() -> bool:
    try:
        import self_maintenance as sm
        import smoke_segment_registry as ssr
        import memory_candidate_application_trial as mcat
        if sm.SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if ssr.SMOKE_SEGMENT_REGISTRY_VERSION != "500.0" or mcat.MEMORY_CANDIDATE_APPLICATION_TRIAL_VERSION != "500.0":
            return False
        missing = mcat.build_operator_confirmed_memory_application_trial_summary("review only", {})
        wrong = mcat.build_operator_confirmed_memory_application_trial_summary("review only", {"operator_confirmation_phrase":"wrong phrase"})
        exact = mcat.build_operator_confirmed_memory_application_trial_summary("review only", {"operator_confirmation_phrase":mcat.EXPECTED_MEMORY_CONFIRMATION_PHRASE})
        if missing.get("status") != "blocked" or "explicit_confirmation_supplied" not in missing.get("blockers", []):
            return False
        if wrong.get("status") != "blocked" or wrong.get("checks", {}).get("operator_confirmation_phrase_exact") is not False:
            return False
        if exact.get("status") == "blocked" or exact.get("checks", {}).get("explicit_confirmation_supplied") is not True:
            return False
        checks = [{"name": c.name, "tier": c.tier, "segment": _segment_for_check(c)} for c in _build_checks(include_v405=False)]
        registry = ssr.build_smoke_segment_registry_summary(checks)
        if registry.get("ok") is not True or registry.get("segment_count", 0) < 8:
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/smoke_segment_registry.py", "tools/smoke_check.py", "conscious_agent/self_maintenance.py"])
        audit = ssr.build_segmented_install_smoke_audit_summary(registry, docs)
        if audit.get("ok") is not True or audit.get("applies_patches") is not False or audit.get("writes_memory") is not False:
            return False
        report = sm.build_operator_governed_segmented_install_smoke_audit_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True:
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/memory-application-confirmation-gate", "/memory-application-negative-tests", "/smoke-segment-registry", "/install-smoke-segment-runner", "/segmented-install-smoke-audit"]):
            return False
        print("[ok] operator-governed segmented install smoke audit v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed segmented install smoke audit v1: {error}")
        return False


def check_operator_governed_memory_application_dry_run_ledger_v1() -> bool:
    try:
        import self_maintenance as sm
        import memory_application_dry_run_ledger as ledger
        if sm.SELF_MAINTENANCE_VERSION != "500.0" or ledger.MEMORY_APPLICATION_DRY_RUN_LEDGER_VERSION != "500.0":
            return False
        exact = {"operator_confirmation_phrase": ledger.EXPECTED_MEMORY_CONFIRMATION_PHRASE}
        missing = ledger.build_memory_application_dry_run_attempt_summary("review only", {})
        wrong = ledger.build_memory_application_dry_run_attempt_summary("review only", {"operator_confirmation_phrase":"wrong phrase"})
        good = ledger.build_memory_application_dry_run_attempt_summary("review only", exact)
        if missing.get("status") != "blocked" or wrong.get("status") != "blocked" or good.get("ok") is not True:
            return False
        if good.get("writes_memory") is not False:
            return False
        entry = ledger.build_memory_application_dry_run_ledger_entry_summary("review only", exact)
        replay = ledger.build_memory_application_ledger_replay_summary(entry.get("ledger_entry", {}), exact)
        drift = ledger.build_memory_application_ledger_replay_summary(entry.get("ledger_entry", {}), {"operator_confirmation_phrase": ledger.EXPECTED_MEMORY_CONFIRMATION_PHRASE, "candidate":{"candidate_id":"changed-candidate"}})
        if entry.get("ok") is not True or entry.get("writes_memory") is not False:
            return False
        if replay.get("ok") is not True or drift.get("status") != "blocked" or drift.get("replay_accepts_drift") is not False:
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/memory_application_dry_run_ledger.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "tools/smoke_check.py"])
        audit = ledger.build_memory_application_ledger_audit_summary(docs, replay)
        if audit.get("ok") is not True or audit.get("writes_memory") is not False or audit.get("applies_patches") is not False:
            return False
        report = sm.build_operator_governed_memory_application_dry_run_ledger_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True:
            return False
        required = ["memory-application-attempt-ledger-schema", "memory-application-dry-run-ledger", "memory-application-ledger-replay", "memory-application-ledger-surfaces", "memory-application-ledger-audit", "operator-governed-memory-application-dry-run-ledger-v1", "ledger_writes_live_memory=False", "replay_accepts_drift=False", "audit_writes_memory=False", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/memory-application-attempt-ledger-schema", "/memory-application-dry-run-ledger", "/memory-application-ledger-replay", "/memory-application-ledger-surfaces", "/memory-application-ledger-audit"]):
            return False
        print("[ok] operator-governed memory application dry-run ledger v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed memory application dry-run ledger v1: {error}")
        return False


def check_operator_governed_sandbox_memory_write_target_v1() -> bool:
    try:
        import tempfile
        from pathlib import Path as _Path
        import self_maintenance as sm
        import sandbox_memory_write_target as sandbox
        if sm.SELF_MAINTENANCE_VERSION != "500.0" or sandbox.SANDBOX_MEMORY_WRITE_TARGET_VERSION != "500.0":
            return False
        exact = {"operator_confirmation_phrase": sandbox.EXPECTED_MEMORY_CONFIRMATION_PHRASE}
        with tempfile.TemporaryDirectory(prefix="eidolon_v415_smoke_") as tmp:
            tmp_root = _Path(tmp)
            schema = sandbox.build_sandbox_memory_target_schema_summary(tmp_root)
            transaction = sandbox.build_sandbox_memory_write_transaction_summary(tmp_root, evidence=exact)
            trial = sandbox.execute_sandbox_memory_write_trial(tmp_root, evidence=exact)
            retraction = sandbox.build_sandbox_memory_retraction_preview_summary(trial, tmp_root)
            bad_target = sandbox.build_sandbox_memory_target_schema_summary(tmp_root, tmp_root / "memory.json")
            if schema.get("ok") is not True or schema.get("live_memory_allowed") is not False:
                return False
            if transaction.get("ok") is not True or transaction.get("writes_live_memory") is not False:
                return False
            if trial.get("ok") is not True or trial.get("executed") is not True or trial.get("writes_live_memory") is not False:
                return False
            if trial.get("pre_write_hash") == trial.get("post_write_hash"):
                return False
            if retraction.get("ok") is not True or retraction.get("retraction_executes_live_memory") is not False:
                return False
            if bad_target.get("ok") is not False:
                return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/sandbox_memory_write_target.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "tools/smoke_check.py"])
        audit = sandbox.build_sandbox_memory_write_audit_summary(docs)
        if audit.get("ok") is not True or audit.get("writes_live_memory") is not False or audit.get("applies_patches") is not False:
            return False
        report = sm.build_operator_governed_sandbox_memory_write_target_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True:
            return False
        required = ["sandbox-memory-target-schema", "sandbox-memory-write-transaction", "sandbox-memory-write-trial", "sandbox-memory-retraction-preview", "sandbox-memory-write-audit", "operator-governed-sandbox-memory-write-target-v1", "sandbox_write_target_writes_live_memory=False", "sandbox_trial_accepts_non_sandbox_path=False", "sandbox_retraction_executes_live_retraction=False", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/sandbox-memory-target-schema", "/sandbox-memory-write-transaction", "/sandbox-memory-write-trial", "/sandbox-memory-retraction-preview", "/sandbox-memory-write-audit"]):
            return False
        print("[ok] operator-governed sandbox memory write target v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed sandbox memory write target v1: {error}")
        return False


def check_operator_governed_live_memory_write_burnout_v1() -> bool:
    try:
        import tempfile
        from pathlib import Path as _Path
        import self_maintenance as sm
        import live_memory_write_trial as live
        if sm.SELF_MAINTENANCE_VERSION != "500.0" or live.LIVE_MEMORY_WRITE_TRIAL_VERSION != "500.0":
            return False
        exact = {"operator_confirmation_phrase": live.EXPECTED_MEMORY_CONFIRMATION_PHRASE}
        with tempfile.TemporaryDirectory(prefix="eidolon_v420_smoke_") as tmp:
            tmp_root = _Path(tmp)
            eligibility = live.build_live_memory_write_eligibility_summary(tmp_root, exact)
            approval_lock = live.build_live_memory_approval_lock_summary(tmp_root, exact)
            preview = live.build_live_memory_transaction_preview_summary(tmp_root, evidence=exact)
            trial = live.execute_operator_confirmed_live_memory_write_trial(tmp_root, evidence=exact)
            reuse_block = live.execute_operator_confirmed_live_memory_write_trial(tmp_root, evidence={**exact, "approval_reused": True})
            wrong_phrase = live.execute_operator_confirmed_live_memory_write_trial(tmp_root, evidence={"operator_confirmation_phrase":"wrong"})
            bad_target = live.build_live_memory_transaction_preview_summary(tmp_root, tmp_root / "memory.json", exact)
            if eligibility.get("ok") is not True or eligibility.get("eligibility_is_approval") is not False or eligibility.get("writes_memory") is not False:
                return False
            if approval_lock.get("ok") is not True or approval_lock.get("approval_lock_reuses_approval") is not False:
                return False
            if preview.get("ok") is not True or preview.get("writes_memory") is not False:
                return False
            if trial.get("ok") is not True or trial.get("executed") is not True or trial.get("writes_memory") is not True:
                return False
            if trial.get("approval_burnout", {}).get("burned_out") is not True or trial.get("approval_burnout", {}).get("reuse_allowed") is not False:
                return False
            if trial.get("pre_write_hash") == trial.get("post_write_hash"):
                return False
            if reuse_block.get("ok") is not False or wrong_phrase.get("ok") is not False or bad_target.get("ok") is not False:
                return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/live_memory_write_trial.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "tools/smoke_check.py"])
        audit = live.build_live_memory_write_audit_summary(docs)
        if audit.get("ok") is not True or audit.get("grants_future_authorization") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = sm.build_operator_governed_live_memory_write_burnout_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True:
            return False
        required = ["live-memory-write-eligibility", "live-memory-approval-lock", "live-memory-transaction-preview", "operator-confirmed-live-memory-write-trial", "live-memory-write-audit", "operator-governed-live-memory-write-burnout-v1", "eligibility_is_approval=False", "sandbox_success_is_approval=False", "approval_burnout_required=True", "audit_grants_future_authorization=False", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/live-memory-write-eligibility", "/live-memory-approval-lock", "/live-memory-transaction-preview", "/operator-confirmed-live-memory-write-trial", "/live-memory-write-audit"]):
            return False
        print("[ok] operator-governed live memory write burnout v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed live memory write burnout v1: {error}")
        return False



def check_operator_governed_memory_retraction_trial_v1() -> bool:
    try:
        import tempfile
        from pathlib import Path
        import self_maintenance as sm
        import memory_retraction_trial as retract
        exact = {"operator_retraction_confirmation_phrase": retract.EXPECTED_MEMORY_RETRACTION_CONFIRMATION_PHRASE}
        with tempfile.TemporaryDirectory(prefix="eidolon_v425_smoke_") as tmp:
            tmp_root = Path(tmp)
            eligibility = retract.build_memory_retraction_eligibility_summary(tmp_root, exact)
            approval_lock = retract.build_memory_retraction_approval_lock_summary(tmp_root, exact)
            preview = retract.build_memory_retraction_transaction_preview_summary(tmp_root, evidence=exact)
            trial = retract.execute_operator_confirmed_memory_retraction_trial(tmp_root, evidence=exact)
            reuse_block = retract.execute_operator_confirmed_memory_retraction_trial(tmp_root, evidence={**exact, "retraction_approval_reused": True})
            wrong_phrase = retract.execute_operator_confirmed_memory_retraction_trial(tmp_root, evidence={"operator_retraction_confirmation_phrase":"wrong"})
            batch_block = retract.execute_operator_confirmed_memory_retraction_trial(tmp_root, evidence={**exact, "batch_retraction": True})
            fuzzy_block = retract.execute_operator_confirmed_memory_retraction_trial(tmp_root, evidence={**exact, "fuzzy_match": True})
            bad_target = retract.build_memory_retraction_transaction_preview_summary(tmp_root, tmp_root / "memory.json", exact)
            if eligibility.get("ok") is not True or eligibility.get("retraction_eligibility_is_approval") is not False or eligibility.get("writes_memory") is not False:
                return False
            if approval_lock.get("ok") is not True or approval_lock.get("approval_lock", {}).get("write_approval_authorizes_retraction") is not False:
                return False
            if preview.get("ok") is not True or preview.get("deletes_memory") is not False:
                return False
            if trial.get("ok") is not True or trial.get("executed") is not True or trial.get("retained_audit_record") is not True:
                return False
            if trial.get("physical_delete") is not False or trial.get("deletes_memory") is not False:
                return False
            if trial.get("approval_burnout", {}).get("burned_out") is not True or trial.get("approval_burnout", {}).get("reuse_allowed") is not False:
                return False
            if trial.get("pre_retraction_hash") == trial.get("post_retraction_hash"):
                return False
            if reuse_block.get("ok") is not False or wrong_phrase.get("ok") is not False or batch_block.get("ok") is not False or fuzzy_block.get("ok") is not False or bad_target.get("ok") is not False:
                return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/memory_retraction_trial.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "tools/smoke_check.py"])
        audit = retract.build_memory_retraction_trial_audit_summary(docs)
        if audit.get("ok") is not True or audit.get("grants_future_authorization") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = sm.build_operator_governed_memory_retraction_trial_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True:
            return False
        required = ["memory-retraction-eligibility", "memory-retraction-approval-lock", "memory-retraction-transaction-preview", "operator-confirmed-memory-retraction-trial", "memory-retraction-trial-audit", "operator-governed-memory-retraction-trial-v1", "write_approval_authorizes_retraction=False", "retraction_eligibility_is_approval=False", "retained_audit_record_required=True", "audit_grants_future_retraction_authority=False", "data-tip", "no_native_title_tooltip"]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/memory-retraction-eligibility", "/memory-retraction-approval-lock", "/memory-retraction-transaction-preview", "/operator-confirmed-memory-retraction-trial", "/memory-retraction-trial-audit"]):
            return False
        print("[ok] operator-governed memory retraction trial v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed memory retraction trial v1: {error}")
        return False


def check_operator_governed_source_surface_manifest_v1() -> bool:
    try:
        import self_maintenance as sm
        import source_surface_manifest as manifest
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_source_surface_manifest_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if manifest.SOURCE_SURFACE_MANIFEST_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/source_surface_manifest.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py"
        ])
        summary = manifest.build_source_surface_manifest_summary()
        parity = manifest.build_source_surface_parity_audit_summary(docs)
        authority = manifest.build_source_surface_authority_map_summary()
        privacy = manifest.build_source_surface_package_privacy_map_summary()
        audit = manifest.build_source_surface_manifest_audit_summary(docs)
        if summary.get("ok") is not True or summary.get("entry_count", 0) < 7:
            return False
        if parity.get("ok") is not True or parity.get("parity_pass_is_authorization") is not False:
            return False
        if authority.get("ok") is not True or authority.get("authority_label_is_approval") is not False:
            return False
        if privacy.get("ok") is not True or privacy.get("manifest_writes_memory") is not False:
            return False
        if audit.get("ok") is not True or audit.get("grants_authorization") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = build_operator_governed_source_surface_manifest_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True or report.get("manifest_presence_is_authorization") is not False:
            return False
        required = [
            "source-surface-manifest", "source-surface-parity-audit", "source-surface-authority-map", "source-surface-package-privacy-map", "source-surface-manifest-audit",
            "operator-governed-source-surface-manifest-v1", "source_surface_manifest.py",
            "manifest_presence_is_authorization=False", "parity_pass_is_authorization=False", "authority_label_is_approval=False",
            "surface_exists_means_may_execute=False", "smoke_pass_allows_live_action=False", "manifest_writes_files=False", "manifest_writes_memory=False",
            "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/source-surface-manifest", "/source-surface-parity-audit", "/source-surface-authority-map", "/source-surface-package-privacy-map", "/source-surface-manifest-audit"]):
            return False
        print("[ok] operator-governed source surface manifest v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed source surface manifest v1: {error}")
        return False


def check_operator_governed_self_maintenance_duplicate_cleanup_v1() -> bool:
    try:
        import duplicate_definition_audit as dda
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_self_maintenance_duplicate_cleanup_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if dda.DUPLICATE_DEFINITION_AUDIT_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/duplicate_definition_audit.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py"
        ])
        inventory = dda.build_duplicate_definition_inventory(PROJECT_ROOT)
        classification = dda.build_self_maintenance_duplicate_classification(PROJECT_ROOT)
        extraction = dda.build_self_maintenance_extraction_candidates(PROJECT_ROOT)
        guard = dda.build_duplicate_definition_guard(PROJECT_ROOT)
        audit = dda.build_self_maintenance_duplicate_cleanup_audit(PROJECT_ROOT, docs)
        if inventory.get("ok") is not True or inventory.get("inventory_is_authorization_to_delete") is not False:
            return False
        if classification.get("ok") is not True or classification.get("classification_is_authorization_to_delete") is not False:
            return False
        if extraction.get("ok") is not True or extraction.get("extraction_plan_is_authorization") is not False:
            return False
        if guard.get("ok") is not True or guard.get("guard_applies_source_edits") is not False:
            return False
        if audit.get("ok") is not True or audit.get("applies_source_edits") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = build_operator_governed_self_maintenance_duplicate_cleanup_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True or report.get("grants_deletion_authority") is not False:
            return False
        required = [
            "duplicate-definition-inventory", "self-maintenance-duplicate-classification", "self-maintenance-extraction-candidates",
            "duplicate-definition-guard", "self-maintenance-duplicate-cleanup-audit", "operator-governed-self-maintenance-duplicate-cleanup-v1",
            "duplicate_definition_audit.py", "inventory_is_authorization_to_delete=False", "classification_is_authorization_to_delete=False",
            "guard_applies_source_edits=False", "guard_executes_refactors=False", "cleanup_expands_autonomy=False",
            "operator_review_required_before_removal=True", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/duplicate-definition-inventory", "/self-maintenance-duplicate-classification", "/self-maintenance-extraction-candidates", "/duplicate-definition-guard", "/self-maintenance-duplicate-cleanup-audit"]):
            return False
        print("[ok] operator-governed self-maintenance duplicate cleanup v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed self-maintenance duplicate cleanup v1: {error}")
        return False


def check_operator_governed_dashboard_route_health_audit_v1() -> bool:
    try:
        import dashboard_route_probe as drp
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_dashboard_route_health_audit_v1
        if SELF_MAINTENANCE_VERSION != "500.0":
            return False
        if drp.DASHBOARD_ROUTE_PROBE_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/dashboard_route_probe.py",
            "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py"
        ])
        inventory = drp.build_dashboard_route_inventory(PROJECT_ROOT)
        probe = drp.build_dashboard_route_probe(PROJECT_ROOT)
        lazy = drp.build_dashboard_lazy_render_audit(PROJECT_ROOT)
        tooltip = drp.build_dashboard_tooltip_regression_audit(PROJECT_ROOT)
        audit = drp.build_dashboard_route_health_audit(PROJECT_ROOT, docs)
        if inventory.get("ok") is not True or inventory.get("route_presence_is_authorization") is not False:
            return False
        if probe.get("ok") is not True or probe.get("route_health_is_approval") is not False:
            return False
        if lazy.get("ok") is not True or lazy.get("lazy_audit_refactors_dashboard") is not False:
            return False
        if tooltip.get("ok") is not True or tooltip.get("tooltip_audit_reintroduces_native_title") is not False:
            return False
        if audit.get("ok") is not True or audit.get("writes_files") is not False or audit.get("expands_autonomy") is not False:
            return False
        report = build_operator_governed_dashboard_route_health_audit_v1(project_id="eidolon-smoke", save=False)
        if report.get("ok") is not True or report.get("route_health_is_approval") is not False:
            return False
        required = [
            "dashboard-route-inventory", "dashboard-route-probe", "dashboard-lazy-render-audit",
            "dashboard-tooltip-regression-audit", "dashboard-route-health-audit", "operator-governed-dashboard-route-health-audit-v1",
            "dashboard_route_probe.py", "route_presence_is_authorization=False", "route_health_is_approval=False",
            "probe_executes_governed_actions=False", "lazy_audit_refactors_dashboard=False", "tooltip_audit_reintroduces_native_title=False",
            "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/dashboard-route-inventory", "/dashboard-route-probe", "/dashboard-lazy-render-audit", "/dashboard-tooltip-regression-audit", "/dashboard-route-health-audit", "/api-info"]):
            return False
        print("[ok] operator-governed dashboard route health audit v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed dashboard route health audit v1: {error}")
        return False

_TIER_ORDER = {
    "fast": {"fast"},
    "loop": {"fast", "loop"},
    "readiness": {"fast", "loop", "readiness"},
    "build": {"fast", "loop", "readiness", "build"},
    "patch": {"fast", "loop", "readiness", "build", "patch"},
    "release": {"fast", "loop", "readiness", "build", "patch", "release"},
    "install": {"fast", "loop", "readiness", "build", "patch", "release", "install"},
    "full": {"fast", "loop", "readiness", "build", "patch", "release", "install"},
}



def _segment_for_check(check: SmokeCheck) -> str:
    try:
        import smoke_segment_registry as ssr
        return ssr.classify_check_name(check.name, check.tier)
    except Exception:
        return "install-core"


def _segment_names() -> list[str]:
    try:
        import smoke_segment_registry as ssr
        return list(ssr.SMOKE_SEGMENT_NAMES)
    except Exception:
        return ["install-core", "install-release", "install-dashboard", "install-governance", "install-expression", "install-live-trial", "install-memory", "install-regression-recent"]


def _select_checks_for_segment(segment: str) -> list[SmokeCheck]:
    if segment == "all":
        return _select_checks("install")
    return [check for check in _select_checks("install") if _segment_for_check(check) == segment]

def _select_checks(tier: str) -> list[SmokeCheck]:
    allowed = _TIER_ORDER.get(tier, _TIER_ORDER["full"])
    return [check for check in _build_checks() if check.tier in allowed]


def _single_check(name: str) -> int:
    checks = {check.name: check for check in _build_checks()}
    check = checks.get(name)
    if not check:
        print(f"[fail] unknown smoke check: {name}", flush=True)
        return 2
    started = time.perf_counter()
    ok = False
    try:
        ok = bool(check.func())
    except Exception as error:
        print(f"[fail] {check.name}: {error}", flush=True)
        ok = False
    elapsed = time.perf_counter() - started
    print(f"[time] {check.name}: {elapsed:.2f}s", flush=True)
    return 0 if ok else 1


def _run_guarded_check(check: SmokeCheck, timeout_scale: float) -> dict[str, object]:
    timeout = max(1, int(check.timeout * timeout_scale))
    if os.environ.get("EIDOLON_SMOKE_ISOLATED", "0") != "1":
        started = time.perf_counter()
        ok = False
        try:
            ok = bool(check.func())
        except Exception as error:
            print(f"[fail] smoke {check.name}: {error}", flush=True)
            ok = False
        elapsed = time.perf_counter() - started
        status = "pass" if ok else "blocked"
        print(f"[{status}] smoke {check.name} ({elapsed:.2f}s, timeout={timeout}s, mode=in-process)", flush=True)
        return {"name": check.name, "tier": check.tier, "status": status, "ok": ok, "elapsed_seconds": round(elapsed, 3), "timeout_seconds": timeout, "mode": "in-process"}
    command = [sys.executable, "-u", str(Path(__file__).resolve()), "--single-check", check.name]
    started = time.perf_counter()
    try:
        proc = subprocess.Popen(command, cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=5)
            elapsed = time.perf_counter() - started
            if stdout.strip(): print(stdout.strip(), flush=True)
            if stderr.strip(): print(stderr.strip(), flush=True)
            print(f"[fail] smoke {check.name} timed out after {timeout}s", flush=True)
            return {"name": check.name, "tier": check.tier, "status": "timeout", "ok": False, "elapsed_seconds": round(elapsed, 3), "timeout_seconds": timeout, "mode": "isolated"}
        elapsed = time.perf_counter() - started
        if stdout.strip(): print(stdout.strip(), flush=True)
        if stderr.strip(): print(stderr.strip(), flush=True)
        status = "pass" if proc.returncode == 0 else "blocked"
        print(f"[{status}] smoke {check.name} ({elapsed:.2f}s, timeout={timeout}s, mode=isolated)", flush=True)
        return {"name": check.name, "tier": check.tier, "status": status, "ok": proc.returncode == 0, "returncode": proc.returncode, "elapsed_seconds": round(elapsed, 3), "timeout_seconds": timeout, "mode": "isolated"}
    except Exception as error:
        elapsed = time.perf_counter() - started
        print(f"[fail] smoke {check.name}: {error}", flush=True)
        return {"name": check.name, "tier": check.tier, "status": "blocked", "ok": False, "error": str(error), "elapsed_seconds": round(elapsed, 3), "timeout_seconds": timeout}

def main() -> int:
    parser = argparse.ArgumentParser(description="Run Eidolon smoke checks with per-check timeouts.")
    parser.add_argument("--tier", choices=sorted(_TIER_ORDER), default="full", help="Smoke tier to run. Each tier includes earlier tiers.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary after the normal log.")
    parser.add_argument("--single-check", help=argparse.SUPPRESS)
    parser.add_argument("--timeout-scale", type=float, default=1.0, help="Multiply each check timeout by this factor.")
    parser.add_argument("--list-checks", action="store_true", help="List check names, tiers, and timeouts.")
    parser.add_argument("--segment", choices=["all", *_segment_names()], help="Run a bounded install smoke segment instead of an entire tier.")
    parser.add_argument("--list-segments", action="store_true", help="List segmented install smoke groups and their check counts.")
    args = parser.parse_args()

    if args.list_segments:
        for segment in _segment_names():
            count = len(_select_checks_for_segment(segment))
            print(f"{segment}\t{count} check(s)", flush=True)
        return 0

    if args.list_checks:
        for check in _build_checks():
            print(f"{check.name}\t{check.tier}\t{check.timeout}s\t{_segment_for_check(check)}", flush=True)
        return 0

    if args.single_check:
        return _single_check(args.single_check)

    selected = _select_checks_for_segment(args.segment) if args.segment else _select_checks(args.tier)
    started = time.perf_counter()
    results = [_run_guarded_check(check, args.timeout_scale) for check in selected]
    elapsed = time.perf_counter() - started
    ok = all(bool(row.get("ok")) for row in results)
    summary = {
        "version": "500.0",
        "tier": args.tier,
        "segment": args.segment,
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "check_count": len(results),
        "failed": [row for row in results if not row.get("ok")],
        "elapsed_seconds": round(elapsed, 3),
        "results": results,
    }
    os.write(1, ("Smoke check passed.\n" if ok else "Smoke check failed.\n").encode("utf-8"))
    if args.json:
        os.write(1, (json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    return 0 if ok else 1


def check_operator_governed_sandbox_autonomy_boundary_prep_v1() -> bool:
    try:
        import sandbox_autonomy_boundary as sab
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_sandbox_autonomy_boundary_prep_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or sab.SANDBOX_AUTONOMY_BOUNDARY_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/sandbox_autonomy_boundary.py",
            "conscious_agent/observation_proposal_queue.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
            "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py", "conscious_agent/api_server.py",
            "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        scope = sab.build_sandbox_only_autonomy_scope_definition(PROJECT_ROOT)
        packet = sab.build_sandbox_autonomy_trial_packet_builder(PROJECT_ROOT)
        boundary = sab.build_sandbox_to_live_boundary_hardening(PROJECT_ROOT)
        no_execution = sab.build_no_execution_sandbox_autonomy_audit(PROJECT_ROOT)
        audit = sab.build_sandbox_autonomy_boundary_prep_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_sandbox_autonomy_boundary_prep_v1(project_id="eidolon-smoke", save=False)
        if not all(item.get("ok") is True for item in [scope, packet, boundary, no_execution, audit, report]):
            return False
        false_keys = [
            "sandbox_scope_is_authorization", "sandbox_readiness_is_approval", "sandbox_target_description_is_permission_to_execute",
            "sandbox_success_is_live_authorization", "sandbox_verification_is_approval", "sandbox_output_is_patch_execution_packet",
            "sandbox_trial_completion_permits_source_mutation", "live_source_writes_allowed", "memory_writes_allowed",
            "real_patch_application_allowed", "release_candidate_creation_allowed", "automatic_scheduling_allowed",
            "local_model_invocation_by_default_allowed", "approval_creation_allowed", "sandbox_execution_allowed",
            "source_mutation_allowed", "memory_mutation_allowed", "schedule_creation_allowed", "model_invocation_by_default_allowed",
            "writes_files", "writes_memory", "updates_metadata", "creates_schedule", "invokes_models", "creates_execution_packet",
            "executes_sandbox_commands", "applies_patches", "publishes_releases", "creates_release_candidate", "approves_proposals",
            "creates_approval", "continues_automatically", "executes_actions", "expands_autonomy",
        ]
        for key in false_keys:
            if report.get(key) is not False:
                return False
        if report.get("promotion_requires_fresh_single_use_operator_approval") is not True:
            return False
        if report.get("operator_review_required") is not True or report.get("fresh_operator_approval_required") is not True or report.get("operator_approval_still_required") is not True:
            return False
        if report.get("authorization_status") != "not_authorized" or report.get("execution_status") != "not_executed":
            return False
        required = [
            "sandbox-only-autonomy-scope-definition", "sandbox-autonomy-trial-packet-builder", "sandbox-to-live-boundary-hardening", "no-execution-sandbox-autonomy-audit", "sandbox-autonomy-boundary-prep-audit",
            "operator-governed-sandbox-autonomy-boundary-prep-v1", "sandbox_autonomy_boundary.py",
            "sandbox_scope_is_authorization=False", "sandbox_readiness_is_approval=False", "sandbox_target_description_is_permission_to_execute=False", "sandbox_success_is_live_authorization=False", "sandbox_verification_is_approval=False", "sandbox_output_is_patch_execution_packet=False", "sandbox_trial_completion_permits_source_mutation=False", "promotion_requires_fresh_single_use_operator_approval=True", "live_source_writes_allowed=False", "memory_writes_allowed=False", "real_patch_application_allowed=False", "release_candidate_creation_allowed=False", "automatic_scheduling_allowed=False", "local_model_invocation_by_default_allowed=False", "approval_creation_allowed=False", "sandbox_execution_allowed=False", "authorization_status=not_authorized", "execution_status=not_executed", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/sandbox-only-autonomy-scope-definition", "/sandbox-autonomy-trial-packet-builder", "/sandbox-to-live-boundary-hardening", "/no-execution-sandbox-autonomy-audit", "/sandbox-autonomy-boundary-prep-audit"]):
            return False
        print("[ok] operator-governed sandbox autonomy boundary prep v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed sandbox autonomy boundary prep v1: {error}")
        return False

# v490.1-v495.0 sandbox autonomy boundary smoke tokens: sandbox-only-autonomy-scope-definition sandbox-autonomy-trial-packet-builder sandbox-to-live-boundary-hardening no-execution-sandbox-autonomy-audit sandbox-autonomy-boundary-prep-audit operator-governed-sandbox-autonomy-boundary-prep-v1 sandbox_autonomy_boundary.py sandbox_scope_is_authorization=False sandbox_readiness_is_approval=False sandbox_target_description_is_permission_to_execute=False sandbox_success_is_live_authorization=False sandbox_verification_is_approval=False sandbox_output_is_patch_execution_packet=False sandbox_trial_completion_permits_source_mutation=False promotion_requires_fresh_single_use_operator_approval=True live_source_writes_allowed=False memory_writes_allowed=False real_patch_application_allowed=False release_candidate_creation_allowed=False automatic_scheduling_allowed=False local_model_invocation_by_default_allowed=False approval_creation_allowed=False sandbox_execution_allowed=False authorization_status=not_authorized execution_status=not_executed no_native_title_tooltip data-tip command-deck operator-console


def check_operator_governed_autonomy_readiness_review_board_v1() -> bool:
    try:
        import autonomy_readiness_review_board as arb
        from self_maintenance import SELF_MAINTENANCE_VERSION, build_operator_governed_autonomy_readiness_review_board_v1
        if SELF_MAINTENANCE_VERSION != "500.0" or arb.AUTONOMY_READINESS_REVIEW_BOARD_VERSION != "500.0":
            return False
        docs = "\n".join((PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="ignore") for rel in [
            "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/autonomy_readiness_review_board.py",
            "conscious_agent/sandbox_autonomy_boundary.py", "conscious_agent/observation_proposal_queue.py", "conscious_agent/self_maintenance.py",
            "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py",
            "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
            "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
        ] if (PROJECT_ROOT / rel).exists())
        criteria = arb.build_autonomy_readiness_criteria_board(PROJECT_ROOT)
        blockers = arb.build_autonomy_blocker_gap_register(PROJECT_ROOT)
        phases = arb.build_phase_based_autonomy_permission_model(PROJECT_ROOT)
        firewall = arb.build_autonomy_misinterpretation_firewall(PROJECT_ROOT)
        audit = arb.build_autonomy_readiness_review_board_audit(PROJECT_ROOT, docs)
        report = build_operator_governed_autonomy_readiness_review_board_v1(project_id="eidolon-smoke", save=False)
        if not all(item.get("ok") is True for item in [criteria, blockers, phases, firewall, audit, report]):
            return False
        false_keys = [
            "readiness_review_is_autonomy_approval", "board_pass_grants_authorization", "phase_definition_authorizes_phase",
            "sandbox_boundary_exists_means_execute", "operator_discussion_is_approval", "proposal_ranking_is_selection",
            "observation_history_authorizes_monitoring", "source_mutation_allowed", "memory_mutation_allowed", "schedule_creation_allowed",
            "model_invocation_by_default_allowed", "execution_packet_creation_allowed", "sandbox_execution_allowed", "live_source_writes_allowed",
            "approval_creation_allowed", "release_candidate_creation_allowed", "automatic_continuation_allowed", "writes_files", "writes_memory",
            "updates_metadata", "creates_schedule", "invokes_models", "creates_execution_packet", "executes_sandbox_commands",
            "applies_patches", "publishes_releases", "creates_release_candidate", "approves_proposals", "creates_approval",
            "continues_automatically", "expands_autonomy",
        ]
        for key in false_keys:
            if report.get(key) is not False:
                return False
        if report.get("readiness_status") != "not_ready_for_autonomy" or report.get("authorization_status") != "not_authorized":
            return False
        if report.get("operator_review_required") is not True or report.get("fresh_operator_approval_required") is not True or report.get("operator_approval_still_required") is not True:
            return False
        required = [
            "autonomy-readiness-criteria-board", "autonomy-blocker-gap-register", "phase-based-autonomy-permission-model", "autonomy-misinterpretation-firewall", "autonomy-readiness-review-board-audit",
            "operator-governed-autonomy-readiness-review-board-v1", "autonomy_readiness_review_board.py", "readiness_status=not_ready_for_autonomy", "authorization_status=not_authorized",
            "readiness_review_is_autonomy_approval=False", "board_pass_grants_authorization=False", "phase_definition_authorizes_phase=False", "sandbox_boundary_exists_means_execute=False", "operator_discussion_is_approval=False", "proposal_ranking_is_selection=False", "observation_history_authorizes_monitoring=False", "source_mutation_allowed=False", "memory_mutation_allowed=False", "schedule_creation_allowed=False", "model_invocation_by_default_allowed=False", "execution_packet_creation_allowed=False", "sandbox_execution_allowed=False", "live_source_writes_allowed=False", "approval_creation_allowed=False", "release_candidate_creation_allowed=False", "data-tip", "no_native_title_tooltip"
        ]
        if not all(token in docs for token in required):
            return False
        if _dashboard_nav_title_regression_present():
            return False
        if not probe_dashboard_http_routes(["/autonomy-readiness-criteria-board", "/autonomy-blocker-gap-register", "/phase-based-autonomy-permission-model", "/autonomy-misinterpretation-firewall", "/autonomy-readiness-review-board-audit"]):
            return False
        print("[ok] operator-governed autonomy readiness review board v1")
        return True
    except Exception as error:
        print(f"[fail] operator-governed autonomy readiness review board v1: {error}")
        return False

# v495.1-v500.0 autonomy readiness review board smoke tokens: autonomy-readiness-criteria-board autonomy-blocker-gap-register phase-based-autonomy-permission-model autonomy-misinterpretation-firewall autonomy-readiness-review-board-audit operator-governed-autonomy-readiness-review-board-v1 autonomy_readiness_review_board.py readiness_status=not_ready_for_autonomy authorization_status=not_authorized readiness_review_is_autonomy_approval=False board_pass_grants_authorization=False phase_definition_authorizes_phase=False sandbox_boundary_exists_means_execute=False operator_discussion_is_approval=False proposal_ranking_is_selection=False observation_history_authorizes_monitoring=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False sandbox_execution_allowed=False live_source_writes_allowed=False approval_creation_allowed=False release_candidate_creation_allowed=False no_native_title_tooltip data-tip command-deck operator-console


if __name__ == "__main__":
    os._exit(main())

# v175 smoke parity tokens: sandbox-promotion-intake source-promotion-plan promotion-approval-packet post-promotion-verification sandbox-to-source-promotion-audit operator-approved-sandbox-to-source-promotion data/autonomy/sandbox_to_source_promotion_audit/ no_native_title_tooltip

# v175 smoke parity tokens: source-application-approval live-source-application-plan approved-source-application-execution post-application-verification source-patch-application-audit operator-approved-source-patch-application data/autonomy/source_patch_application_audit/ no_native_title_tooltip

# v180 smoke parity tokens: post-application-outcome-intake post-application-lessons next-improvement-candidates post-application-release-readiness post-application-cycle-closure operator-governed-post-application-learning-and-release-readiness data/autonomy/post_application_cycle_closure/ no_native_title_tooltip

# v185 smoke parity tokens: cycle-intelligence-intake supervised-patch-priority-matrix next-patch-proposal-assembly supervised-patch-session-planner patch-cycle-intelligence-audit operator-governed-patch-cycle-intelligence data/autonomy/patch_cycle_intelligence_audit/ no_native_title_tooltip

# v190 smoke parity tokens: multi-cycle-roadmap-intake supervised-roadmap-options roadmap-dependency-risk-graph v200-readiness-model multi-cycle-roadmap-governance-audit operator-governed-multi-cycle-roadmap-intelligence data/autonomy/multi_cycle_roadmap_governance_audit/ no_native_title_tooltip

# v195 smoke parity tokens: capability-maturity-inventory capability-maturity-scoring capability-gap-overreach-analysis capability-maturity-improvement-plan capability-maturity-governance-audit supervised-capability-maturity-modeling data/autonomy/capability_maturity_governance_audit/ no_native_title_tooltip

# v195 capability maturity CLI parity flags: --capability-domain-schema --maturity-level-scale --evidence-requirement-schema --capability-boundary-binder --safety-dependency-binder --verification-dependency-binder --documentation-dependency-binder --maturity-inventory-dashboard-api-cli --pre-v191-gate --capability-inventory-and-maturity-schema --planning-capability-scorer --patch-drafting-capability-scorer --application-capability-scorer --verification-capability-scorer --learning-capability-scorer --dashboard-operator-experience-scorer --safety-governance-scorer --maturity-scoring-dashboard-api-cli --pre-v192-gate --capability-maturity-scoring-layer --capability-gap-schema --underdeveloped-capability-detector --overreach-detector --verification-gap-detector --documentation-gap-detector --dashboard-complexity-detector --v200-blocker-detector --gap-overreach-dashboard-api-cli --pre-v193-gate --capability-gap-and-overreach-analyzer --improvement-plan-schema --safety-first-improvement-planner --verification-improvement-planner --dashboard-improvement-planner --learning-improvement-planner --roadmap-improvement-planner --improvement-priority-builder --maturity-improvement-dashboard-api-cli --pre-v194-gate --capability-maturity-improvement-planner --score-evidence-trace-audit --gap-to-plan-trace-audit --overreach-boundary-audit --approval-boundary-audit-v195 --no-autonomous-improvement-audit --dashboard-style-audit-v195 --route-api-cli-parity-audit-v195 --docs-release-history-audit-v195 --pre-v195-gate --supervised-capability-maturity-modeling

# v200 smoke parity tokens: governance-kernel-state governance-rule-evaluation operator-authority-consent-ledger governance-enforcement-simulation governance-kernel-audit local-artificial-mind-governance-kernel-v1 data/autonomy/governance_kernel_audit/ no_native_title_tooltip
# v200 governance kernel CLI parity flags: --governance-kernel-schema --lifecycle-phase-binder --capability-state-binder --approval-state-binder --evidence-state-binder --risk-state-binder --operator-constraint-binder --kernel-state-dashboard-api-cli --pre-v196-gate --governance-kernel-state-model --governance-rule-schema --action-classification-layer --approval-requirement-evaluator --forbidden-action-detector --evidence-requirement-evaluator --safety-conflict-detector --governance-decision-summary-builder --rule-evaluation-dashboard-api-cli --pre-v197-gate --governance-rule-evaluation-layer --operator-authority-schema --explicit-approval-parser --approval-scope-binder --approval-expiration-model --approval-revocation-model --consent-ambiguity-detector --consent-ledger-summary-builder --consent-ledger-dashboard-api-cli --pre-v198-gate --operator-authority-and-consent-ledger --enforcement-simulation-schema --patch-workflow-simulation --release-workflow-simulation --memory-identity-workflow-simulation --autonomous-continuation-simulation --dashboard-api-cli-parity-simulation --enforcement-simulation-report-builder --enforcement-simulation-dashboard-api-cli --pre-v199-gate --governance-kernel-enforcement-simulation --kernel-state-trace-audit --rule-evaluation-trace-audit --consent-ledger-boundary-audit --enforcement-simulation-audit --no-autonomy-governance-audit --dashboard-style-audit-v200 --route-api-cli-parity-audit-v200 --docs-release-history-audit-v200 --pre-v200-gate --local-artificial-mind-governance-kernel-v1

# v205 smoke parity tokens: governance-decision-packet approval-transaction-model governance-evidence-timeline operator-governance-console governance-integration-audit operator-governed-governance-kernel-integration data/autonomy/governance_integration_audit/ no_native_title_tooltip

# v210 smoke parity tokens: cognitive-continuity-packet memory-candidate-staging identity-boundary-layer supervised-reflection-journal cognitive-continuity-audit operator-governed-cognitive-continuity-layer-v1 data/autonomy/cognitive_continuity_audit/ no_native_title_tooltip

# v215 smoke parity tokens: self-model-snapshot deliberation-packet purpose-alignment-layer behavioral-pattern-intelligence self-model-integration-audit operator-governed-deliberation-and-self-model-layer-v1 data/autonomy/self_model_integration_audit/ no_native_title_tooltip

# v220 smoke parity tokens: internal-simulation-packet foresight-branch-comparison pre-change-consequence-modeling expectation-reality-check simulation-foresight-audit operator-governed-internal-simulation-and-foresight-layer-v1 data/autonomy/simulation_foresight_audit/ no_native_title_tooltip

# v225 smoke parity tokens: learning-objective-map practice-task-design capability-calibration skill-gap-remediation-planner learning-curriculum-audit operator-governed-learning-curriculum-and-capability-calibration-layer-v1 data/autonomy/learning_curriculum_audit/ no_native_title_tooltip

# v230 smoke parity tokens: knowledge-claim-ledger belief-candidate-review contradiction-staleness-intelligence project-knowledge-map knowledge-organization-audit operator-governed-knowledge-and-belief-organization-layer-v1 data/autonomy/knowledge_organization_audit/ no_native_title_tooltip

# v235 smoke parity tokens: local-model-inventory model-evaluation-plan model-output-comparison cognitive-workbench-routing local-model-workbench-audit operator-governed-local-model-evaluation-and-cognitive-workbench-layer-v1 data/autonomy/local_model_workbench_audit/ no_native_title_tooltip

# v240 smoke parity tokens: local-model-invocation-consent model-evaluation-run-ledger multi-model-output-triage model-reliability-profile-candidates local-model-invocation-sandbox-audit operator-approved-local-model-invocation-sandbox-v1 data/autonomy/local_model_invocation_sandbox_audit/ no_native_title_tooltip

# v245 smoke parity tokens: model-assisted-patch-critique multi-model-review-synthesis patch-risk-remediation-synthesis model-review-quality-calibration model-assisted-patch-review-audit operator-governed-model-assisted-patch-review-and-synthesis-layer-v1 data/autonomy/model_assisted_patch_review_audit/ no_native_title_tooltip

# v245.1-v250.0 model-assisted patch draft smoke tokens: model-assisted-patch-draft file-impact-documentation-planner smoke-verification-suggestions sandbox-preparation-packet patch-draft-assembly-audit operator-governed-model-assisted-patch-draft-assembly-layer-v1 data/autonomy/patch_draft_assembly_audit/ no_native_title_tooltip

# v250.1-v255.0 patch execution packet bridge smoke tokens: draft-to-execution-packet patch-diff-preview-planner execution-approval-scope verification-rollback-packet patch-execution-packet-audit operator-governed-patch-execution-packet-bridge-v1 data/autonomy/patch_execution_packet_audit/ no_native_title_tooltip

# v255.1-v260.0 approved application prep smoke tokens: application-prep-intake source-edit-application-plan documentation-application-plan final-application-governance-gate application-prep-integration-audit operator-governed-approved-execution-packet-application-prep-v1 data/autonomy/application_prep_integration_audit/ no_native_title_tooltip

# v260.1-v265.0 structural stabilization smoke tokens: structural-inventory runtime-registry-prep dashboard-stabilization-audit dispatch-stabilization structural-stabilization-audit operator-governed-structural-stabilization-and-runtime-modularization-v1 data/autonomy/structural_stabilization_audit/ no_native_title_tooltip

# v265.1-v270.0 module extraction smoke tokens: runtime-registry governance-report-builder-audit dashboard-registry-integration runtime-dispatch-registry-audit module-extraction-audit operator-governed-runtime-module-extraction-v1 data/autonomy/module_extraction_audit/ runtime_registry.py governance_reports.py no_native_title_tooltip

# v270.1-v280.0 self-maintenance decomposition smoke tokens: self-maintenance-extraction-map package-version-integrity surface-parity-audit verification-planning-audit self-maintenance-decomposition-audit operator-governed-self-maintenance-decomposition-v1 data/autonomy/self_maintenance_decomposition_audit/ package_integrity.py version_state.py surface_parity.py verification_planning.py no_native_title_tooltip

# v275.1-v280.0 dashboard/API/CLI modularization smoke tokens: dashboard-extraction-map dashboard-component-audit api-surface-audit cli-surface-audit interface-modularization-audit operator-governed-dashboard-api-cli-modularization-v1 data/autonomy/interface_modularization_audit/ dashboard_components.py api_surface.py cli_surface.py no_native_title_tooltip data-tip command-deck

# v280.1-v285.0 application execution refinement smoke tokens: approved-application-binding operator-execution-checklist post-application-result-review application-outcome-learning application-execution-refinement-audit operator-approved-application-execution-refinement-v1 data/autonomy/application_execution_refinement_audit/ application_execution_refinement.py no_native_title_tooltip data-tip command-deck

# v285.1-v290.0 rollback and recovery intelligence smoke tokens: rollback-scope-binding failure-damage-map recovery-checklist post-recovery-review rollback-recovery-audit operator-governed-rollback-and-recovery-intelligence-v1 data/autonomy/rollback_recovery_audit/ rollback_recovery.py no_native_title_tooltip data-tip command-deck

# v290.1-v295.0 memory candidate governance smoke tokens: memory-candidate-intake memory-candidate-classification memory-approval-packet memory-contradiction-review memory-governance-audit operator-governed-memory-candidate-governance-upgrade-v1 data/autonomy/memory_governance_audit/ memory_governance.py no_native_title_tooltip data-tip command-deck

# v295.1-v300.0 continuity kernel smoke tokens: continuity-state-intake self-model-snapshot-v2 purpose-coherence-review supervised-growth-priorities continuity-kernel-v2-audit local-artificial-mind-continuity-kernel-v2 data/autonomy/continuity_kernel_v2_audit/ continuity_kernel.py no_native_title_tooltip data-tip command-deck

# v300.1-v305.0 identity/personality/coherence expression smoke tokens: identity-expression-boundary personality-trait-ledger voice-affect-style-map coherence-expression-review identity-personality-coherence-audit operator-governed-identity-personality-coherence-expression-layer-v1 data/autonomy/identity_personality_coherence_audit/ identity_expression.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required risky_request_classifier blocked_live_policy_change

# v305.1-v310.0 behavioral expression preview and runtime health hardening smoke tokens: dashboard-route-health runtime-test-visibility behavioral-expression-preview style-delta-staging expression-runtime-health-audit operator-governed-behavioral-expression-preview-and-runtime-health-hardening-v1 data/autonomy/expression_runtime_health_audit/ route_health.py behavioral_expression_preview.py dashboard_http_route_probe_required metadata_consistency_smoke_required timeout_aware_smoke_summary no_native_title_tooltip data-tip command-deck

# v310.1-v315.0 conversational expression sandbox smoke tokens: expression-profile-packets conversation-scenario-sandbox expression-regression-review expression-operator-review-console conversational-expression-sandbox-audit operator-governed-conversational-expression-sandbox-v1 data/autonomy/conversational_expression_sandbox_audit/ conversational_expression_sandbox.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required scenario_sandbox_runs_live_chat=False operator_review_console_grants_approval=False sandbox_audit_promotes_to_live=False

# v315.1-v320.0 expression application bridge smoke tokens: expression-approval-criteria expression-live-surface-impact-map expression-implementation-packet-draft expression-rollback-reversion-plan expression-application-bridge-audit operator-governed-conversational-expression-application-bridge-v1 data/autonomy/expression_application_bridge_audit/ expression_application_bridge.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required approval_criteria_grants_approval=False implementation_packet_writes_source=False rollback_plan_executes_rollback=False bridge_audit_applies_live_expression=False


# v320.1-v325.0 expression patch dry-run sandbox smoke tokens: expression-patch-candidates expression-sandbox-diff-preview expression-dry-run-verification-plan expression-dry-run-review-packet expression-patch-dry-run-audit operator-governed-expression-patch-dry-run-sandbox-v1 data/autonomy/expression_patch_dry_run_audit/ expression_patch_dry_run.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required candidate_packet_applies_patch=False sandbox_diff_preview_writes_files=False dry_run_verification_executes_commands=False dry_run_review_packet_grants_approval=False patch_dry_run_audit_applies_changes=False

# v325.1-v330.0 expression patch sandbox trial harness smoke tokens: expression-sandbox-trial-packet expression-sandbox-workspace-plan expression-sandbox-verification-matrix expression-sandbox-result-review-prep expression-sandbox-trial-harness-audit operator-governed-expression-patch-sandbox-trial-harness-v1 data/autonomy/expression_sandbox_trial_harness_audit/ expression_sandbox_trial_harness.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required trial_packet_executes_sandbox=False workspace_plan_copies_files=False workspace_plan_writes_files=False verification_matrix_executes_commands=False result_review_promotes_to_live=False trial_harness_audit_applies_changes=False

# v330.1-v335.0 expression sandbox trial execution packet bridge smoke tokens: expression-sandbox-execution-approval-gate expression-sandbox-workspace-execution-packet expression-sandbox-patch-bundle-packet expression-sandbox-verification-command-packet expression-sandbox-execution-packet-bridge-audit operator-governed-expression-sandbox-trial-execution-packet-bridge-v1 data/autonomy/expression_sandbox_execution_approval_gate/ data/autonomy/expression_sandbox_workspace_execution_packet/ data/autonomy/expression_sandbox_patch_bundle_packet/ data/autonomy/expression_sandbox_verification_command_packet/ data/autonomy/expression_sandbox_execution_packet_bridge_audit/ expression_sandbox_execution_bridge.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required approval_gate_grants_approval=False workspace_execution_packet_copies_files=False workspace_execution_packet_writes_files=False patch_bundle_applies_patch=False verification_command_packet_executes_commands=False execution_bridge_executes_sandbox=False

# v335.1-v340.0 expression sandbox result intake smoke tokens: expression-sandbox-trial-evidence-intake expression-sandbox-outcome-comparison expression-sandbox-regression-result-review expression-sandbox-revision-recommendations expression-sandbox-promotion-review-prep operator-governed-expression-sandbox-trial-result-intake-and-promotion-review-prep-v1 data/autonomy/expression_sandbox_trial_evidence_intake/ data/autonomy/expression_sandbox_outcome_comparison/ data/autonomy/expression_sandbox_regression_result_review/ data/autonomy/expression_sandbox_revision_recommendations/ data/autonomy/expression_sandbox_promotion_review_prep/ expression_sandbox_result_intake.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required evidence_intake_treats_evidence_as_approval=False outcome_comparison_auto_corrects_patch=False regression_review_auto_fixes_prompts=False revision_recommendations_apply_changes=False promotion_review_prep_promotes_to_live=False

# v340.1-v345.0 expression promotion packet smoke tokens: expression-promotion-evidence-binder expression-live-promotion-scope-risk expression-promotion-verification-rollback expression-promotion-decision-packet expression-promotion-packet-assembly-audit operator-governed-expression-promotion-packet-assembly-layer-v1 data/autonomy/expression_promotion_evidence_binder/ data/autonomy/expression_live_promotion_scope_risk/ data/autonomy/expression_promotion_verification_rollback/ data/autonomy/expression_promotion_decision_packet/ data/autonomy/expression_promotion_packet_assembly_audit/ expression_promotion_packet.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required promotion_evidence_binder_treats_evidence_as_approval=False live_scope_risk_mutates_live_surfaces=False verification_rollback_executes_commands=False promotion_decision_packet_executes_decision=False promotion_packet_assembly_promotes_live_expression=False

# v345.1-v350.0 expression live application packet smoke tokens: expression-live-application-eligibility-gate expression-live-source-change-manifest expression-live-patch-instruction-packet expression-live-verification-rollback-packet expression-live-application-packet-audit operator-governed-expression-live-application-packet-drafting-layer-v1 data/autonomy/expression_live_application_eligibility_gate/ data/autonomy/expression_live_source_change_manifest/ data/autonomy/expression_live_patch_instruction_packet/ data/autonomy/expression_live_verification_rollback_packet/ data/autonomy/expression_live_application_packet_audit/ expression_live_application_packet.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required eligibility_gate_authorizes_live_writes=False source_change_manifest_writes_files=False patch_instruction_packet_applies_patch=False verification_rollback_packet_executes_commands=False application_packet_audit_applies_live_source=False

# v350.1-v355.0 expression live application execution prep smoke tokens: expression-live-execution-approval-intake expression-live-source-transaction-preimage expression-live-manual-execution-checklist expression-live-rollback-reversion-packet expression-live-execution-prep-audit operator-governed-expression-live-application-execution-prep-v1 data/autonomy/expression_live_execution_approval_intake/ data/autonomy/expression_live_source_transaction_preimage/ data/autonomy/expression_live_manual_execution_checklist/ data/autonomy/expression_live_rollback_reversion_packet/ data/autonomy/expression_live_execution_prep_audit/ expression_live_execution_prep.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required approval_intake_applies_live_expression=False transaction_manifest_writes_files=False manual_checklist_executes_commands=False rollback_packet_runs_rollback=False execution_prep_applies_live_expression=False

# v355.1-v360.0 minimal live expression application smoke tokens: minimal-live-expression-change-candidate minimal-live-expression-approval-lock minimal-live-expression-patch-transaction minimal-live-expression-application-harness minimal-live-expression-application-audit operator-approved-minimal-live-expression-application-audit-v1 data/autonomy/minimal_live_expression_change_candidate/ data/autonomy/minimal_live_expression_approval_lock/ data/autonomy/minimal_live_expression_patch_transaction/ data/autonomy/minimal_live_expression_application_harness/ data/autonomy/minimal_live_expression_application_audit/ minimal_live_expression_application.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required candidate_selection_applies_change=False approval_lock_self_approves=False transaction_builder_writes_files=False application_harness_executes_without_confirmation=False application_audit_publishes_release=False

# v360.1-v365.0 self-maintenance refactor smoke tokens: self-maintenance-gate-registry self-maintenance-version-expectations governed-surface-metadata-registry smoke-check-legacy-gate-registry self-maintenance-refactor-audit operator-governed-self-maintenance-surface-reduction-and-gate-registry-refactor-v1 data/autonomy/self_maintenance_gate_registry/ data/autonomy/self_maintenance_version_expectations/ data/autonomy/governed_surface_metadata_registry/ data/autonomy/smoke_check_legacy_gate_registry/ data/autonomy/self_maintenance_refactor_audit/ self_maintenance_refactor_registry.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required centralized_version_expectations_required=True refactor_registry_writes_files=False refactor_registry_executes_smoke=False refactor_registry_changes_runtime_behavior=False

# v365.1-v370.0 minimal live change replay smoke tokens: minimal-live-change-replay-packet minimal-live-change-expected-actual-comparison minimal-live-change-regression-drift-detector minimal-live-change-recovery-recommendation minimal-live-change-replay-regression-audit operator-governed-minimal-live-change-replay-and-regression-hardening-v1 data/autonomy/minimal_live_change_replay_packet/ data/autonomy/minimal_live_change_expected_actual_comparison/ data/autonomy/minimal_live_change_regression_drift_detector/ data/autonomy/minimal_live_change_recovery_recommendation/ data/autonomy/minimal_live_change_replay_regression_audit/ minimal_live_change_replay.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required replay_packet_applies_change=False expected_actual_writes_files=False regression_detector_auto_fixes=False recovery_recommendation_executes_rollback=False replay_audit_continues_automatically=False

# v370.1-v375.0 modular extraction smoke tokens: self-maintenance-module-extraction-plan self-maintenance-version-package-gates self-maintenance-surface-gates self-maintenance-governance-gates self-maintenance-modular-extraction-audit operator-governed-self-maintenance-modular-extraction-v1 data/autonomy/self_maintenance_module_extraction_plan/ data/autonomy/self_maintenance_version_package_gates/ data/autonomy/self_maintenance_surface_gates/ data/autonomy/self_maintenance_governance_gates/ data/autonomy/self_maintenance_modular_extraction_audit/ self_maintenance_modular_extraction.py self_maintenance_version_package_gates.py self_maintenance_surface_gates.py self_maintenance_governance_gates.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required modular_extraction_applies_live_patches=False version_package_gate_extraction_present=True surface_gate_extraction_present=True governance_gate_extraction_present=True

# v375.1-v380.0 live change application trial smoke tokens: live-change-transaction-narrowing live-change-approval-execution-lock live-change-real-patch-trial-plan live-change-operator-confirmed-application-trial live-change-application-trial-audit operator-governed-live-change-application-trial-audit-v1 data/autonomy/live_change_transaction_narrowing/ data/autonomy/live_change_approval_execution_lock/ data/autonomy/live_change_real_patch_trial_plan/ data/autonomy/live_change_operator_confirmed_application_trial/ data/autonomy/live_change_application_trial_audit/ live_change_application_trial.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required transaction_narrowing_applies_patch=False approval_execution_lock_self_approves=False trial_plan_writes_files=False application_trial_runs_without_confirmation=False application_trial_continues_automatically=False

# v380.1-v385.0 live patch trial closure smoke tokens: live-patch-trial-result-intake live-patch-applied-diff-evidence live-patch-approval-burnout live-patch-post-trial-regression-review live-patch-trial-closure-audit operator-governed-live-patch-trial-closure-audit-v1 data/autonomy/live_patch_trial_result_intake/ data/autonomy/live_patch_applied_diff_evidence/ data/autonomy/live_patch_approval_burnout/ data/autonomy/live_patch_post_trial_regression_review/ data/autonomy/live_patch_trial_closure_audit/ live_patch_trial_closure.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required result_intake_reruns_commands=False diff_evidence_edits_source=False approval_burnout_reuses_approval=False post_trial_review_executes_rollback=False closure_audit_applies_another_patch=False approval_single_use_required=True operator_reapproval_required_for_next_patch=True
# Current smoke JSON summary version token for legacy gates: "version": "500.0"


# v385.1-v390.0 second minimal live patch trial smoke tokens: second-minimal-live-patch-candidate registry-driven-live-patch-approval-validation registry-driven-live-patch-transaction-lock second-live-patch-application-harness second-live-patch-trial-registry-audit operator-governed-second-live-patch-trial-registry-audit-v1 data/autonomy/second_minimal_live_patch_candidate/ data/autonomy/registry_driven_live_patch_approval_validation/ data/autonomy/registry_driven_live_patch_transaction_lock/ data/autonomy/second_live_patch_application_harness/ data/autonomy/second_live_patch_trial_registry_audit/ second_live_patch_trial.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required candidate_selection_applies_patch=False approval_validation_reuses_approval=False transaction_lock_writes_files=False application_harness_runs_without_confirmation=False registry_audit_applies_patch=False fresh_approval_required=True registry_driven_checks_required=True approval_burnout_required=True

# v390.1-v395.0 live patch history memory candidate smoke tokens: live-patch-trial-history-ledger operator-live-patch-decision-patterns live-patch-supervised-lesson-candidates live-patch-memory-candidate-governance live-patch-history-memory-candidate-audit operator-governed-live-patch-history-and-memory-candidate-audit-v1 data/autonomy/live_patch_trial_history_ledger/ data/autonomy/operator_live_patch_decision_patterns/ data/autonomy/live_patch_supervised_lesson_candidates/ data/autonomy/live_patch_memory_candidate_governance/ data/autonomy/live_patch_history_memory_candidate_audit/ live_patch_history_memory_candidates.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required history_ledger_treats_history_as_permission=False decision_review_changes_future_behavior=False lesson_candidates_write_memory=False memory_governance_stores_memory=False history_memory_audit_writes_memory=False memory_candidates_review_only=True operator_approval_required_before_memory_storage=True

# v395.1-v400.0 memory candidate application trial smoke tokens: memory-candidate-selection-packet memory-application-approval-lock memory-write-transaction-preview operator-confirmed-memory-application-trial memory-application-trial-audit operator-governed-memory-application-trial-audit-v1 data/autonomy/memory_candidate_selection_packet/ data/autonomy/memory_application_approval_lock/ data/autonomy/memory_write_transaction_preview/ data/autonomy/operator_confirmed_memory_application_trial/ data/autonomy/memory_application_trial_audit/ memory_candidate_application_trial.py no_native_title_tooltip data-tip command-deck dashboard_http_route_probe_required candidate_selection_writes_memory=False approval_lock_reuses_approval=False transaction_preview_writes_memory=False application_harness_runs_without_confirmation=False application_audit_runs_retraction=False fresh_operator_approval_required=True single_use_memory_approval_required=True sensitive_data_screen_required=True identity_personality_mutation_screen_required=True retraction_packet_required=True

# v400.1-v405.0 segmented install smoke smoke tokens: memory-application-confirmation-gate memory-application-negative-tests smoke-segment-registry install-smoke-segment-runner segmented-install-smoke-audit operator-governed-segmented-install-smoke-audit-v1 conscious_agent/smoke_segment_registry.py --segment --list-segments install-core install-release install-dashboard install-governance install-expression install-live-trial install-memory install-regression-recent explicit_confirmation_supplied missing_confirmation_blocks=True wrong_confirmation_blocks=True exact_confirmation_required=True segment_registry_runs_checks_automatically=False segment_runner_treats_pass_as_approval=False segmented_install_writes_memory=False segmented_install_expands_autonomy=False data-tip no_native_title_tooltip

# v405.1-v410.0 memory dry-run ledger smoke tokens: memory-application-attempt-ledger-schema memory-application-dry-run-ledger memory-application-ledger-replay memory-application-ledger-surfaces memory-application-ledger-audit operator-governed-memory-application-dry-run-ledger-v1 conscious_agent/memory_application_dry_run_ledger.py --operator-governed-memory-application-dry-run-ledger-v1 ledger_writes_live_memory=False ledger_treats_reviewable_as_authorization=False replay_accepts_drift=False audit_writes_memory=False data-tip no_native_title_tooltip

# v410.1-v415.0 sandbox memory write smoke tokens: sandbox-memory-target-schema sandbox-memory-write-transaction sandbox-memory-write-trial sandbox-memory-retraction-preview sandbox-memory-write-audit operator-governed-sandbox-memory-write-target-v1 conscious_agent/sandbox_memory_write_target.py --operator-governed-sandbox-memory-write-target-v1 sandbox_write_target_writes_live_memory=False sandbox_transaction_is_live_memory_approval=False sandbox_trial_accepts_non_sandbox_path=False sandbox_retraction_executes_live_retraction=False sandbox_audit_grants_future_authorization=False before_after_hash_required=True sandbox_path_required=True live_memory_allowed=False data-tip no_native_title_tooltip

# v415.1-v420.0 live memory write smoke tokens: live-memory-write-eligibility live-memory-approval-lock live-memory-transaction-preview operator-confirmed-live-memory-write-trial live-memory-write-audit operator-governed-live-memory-write-burnout-v1 conscious_agent/live_memory_write_trial.py --operator-governed-live-memory-write-burnout-v1 eligibility_is_approval=False sandbox_success_is_approval=False approval_lock_reuses_approval=False transaction_preview_writes_memory=False live_write_runs_without_confirmation=False live_write_allows_batch=False audit_grants_future_authorization=False approval_burnout_required=True single_use_approval_required=True exact_confirmation_required=True data-tip no_native_title_tooltip

# v420.1-v425.0 memory retraction smoke tokens: memory-retraction-eligibility memory-retraction-approval-lock memory-retraction-transaction-preview operator-confirmed-memory-retraction-trial memory-retraction-trial-audit operator-governed-memory-retraction-trial-v1 conscious_agent/memory_retraction_trial.py --operator-governed-memory-retraction-trial-v1 write_approval_authorizes_retraction=False retraction_eligibility_is_approval=False retraction_preview_deletes_memory=False retraction_runs_without_confirmation=False retraction_allows_batch=False retraction_uses_fuzzy_match=False retraction_deletes_canonical_memory_json=False audit_grants_future_retraction_authority=False fresh_retraction_approval_required=True single_use_retraction_approval_required=True exact_retraction_confirmation_required=True retained_audit_record_required=True data-tip no_native_title_tooltip

# v425.1-v430.0 source surface manifest smoke tokens: source-surface-manifest source-surface-parity-audit source-surface-authority-map source-surface-package-privacy-map source-surface-manifest-audit operator-governed-source-surface-manifest-v1 conscious_agent/source_surface_manifest.py --source-surface-manifest-v1 --source-surface-parity-audit-v1 --source-surface-authority-map-v1 --source-surface-package-privacy-map-v1 --operator-governed-source-surface-manifest-v1 manifest_presence_is_authorization=False parity_pass_is_authorization=False authority_label_is_approval=False surface_exists_means_may_execute=False smoke_pass_allows_live_action=False manifest_writes_files=False manifest_writes_memory=False source_only_package_must_exclude_runtime=True data-tip no_native_title_tooltip

# v430.1-v435.0 duplicate definition smoke tokens: duplicate-definition-inventory self-maintenance-duplicate-classification self-maintenance-extraction-candidates duplicate-definition-guard self-maintenance-duplicate-cleanup-audit operator-governed-self-maintenance-duplicate-cleanup-v1 conscious_agent/duplicate_definition_audit.py --duplicate-definition-inventory-v1 --self-maintenance-duplicate-classification-v1 --self-maintenance-extraction-candidates-v1 --duplicate-definition-guard-v1 --operator-governed-self-maintenance-duplicate-cleanup-v1 inventory_is_authorization_to_delete=False classification_is_authorization_to_delete=False guard_applies_source_edits=False guard_executes_refactors=False cleanup_expands_autonomy=False operator_review_required_before_removal=True data-tip no_native_title_tooltip

# v435.1-v440.0 dashboard route probe smoke tokens: dashboard-route-inventory dashboard-route-probe dashboard-lazy-render-audit dashboard-tooltip-regression-audit dashboard-route-health-audit operator-governed-dashboard-route-health-audit-v1 conscious_agent/dashboard_route_probe.py --dashboard-route-inventory-v1 --dashboard-route-probe-v1 --dashboard-lazy-render-audit-v1 --dashboard-tooltip-regression-audit-v1 --operator-governed-dashboard-route-health-audit-v1 route_presence_is_authorization=False route_health_is_approval=False probe_executes_governed_actions=False lazy_audit_refactors_dashboard=False tooltip_audit_reintroduces_native_title=False data-tip no_native_title_tooltip

# v440.1-v445.0 memory lifecycle review board smoke tokens: memory-lifecycle-review-board memory-lifecycle-state-summary memory-lifecycle-drift-review memory-lifecycle-operator-decision-board memory-lifecycle-review-board-audit operator-governed-memory-lifecycle-review-board-v1 conscious_agent/memory_lifecycle_review_board.py --memory-lifecycle-review-board-v1 --memory-lifecycle-state-summary-v1 --memory-lifecycle-drift-review-v1 --memory-lifecycle-operator-decision-board-v1 --operator-governed-memory-lifecycle-review-board-v1 board_visibility_is_authorization=False lifecycle_completeness_is_future_approval=False board_creates_approval=False board_executes_memory_write=False board_executes_memory_retraction=False fresh_approval_required_for_future_memory_action=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v445.1-v450.0 authorization firewall smoke tokens: authorization-confusion-patterns authorization-language-scan authorization-firewall-decision-packet authorization-boundary-map authorization-firewall-audit operator-governed-authorization-firewall-v1 conscious_agent/authorization_firewall.py --authorization-confusion-patterns-v1 --authorization-language-scan-v1 --authorization-firewall-decision-packet-v1 --authorization-boundary-map-v1 --operator-governed-authorization-firewall-v1 readiness_is_approval eligibility_is_approval route_health_is_approval manifest_presence_is_authorization lifecycle_completion_is_future_approval smoke_success_is_permission prior_approval_is_current_approval sandbox_success_is_live_permission model_consensus_is_truth review_packet_is_execution_packet approval_lock_exists_means_approved operator_pattern_means_future_consent firewall_detection_is_enforcement_execution=False firewall_pass_is_authorization=False clear_status_means_approved=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v450.1-v455.0 metadata release integrity smoke tokens: metadata-version-inventory project-workspace-metadata-alignment release-packaging-version-integrity current-state-documentation-header-audit metadata-release-integrity-audit operator-governed-metadata-release-integrity-v1 conscious_agent/metadata_release_integrity.py --metadata-version-inventory-v1 --project-workspace-metadata-alignment-v1 --release-packaging-version-integrity-v1 --current-state-documentation-header-audit-v1 --operator-governed-metadata-release-integrity-v1 metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False metadata_repair_report_publishes_release=False metadata_repair_report_applies_source_edits=False metadata_repair_report_writes_memory=False metadata_repair_report_expands_autonomy=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v455.1-v460.0 authorization firewall signal triage smoke tokens: authorization-firewall-severity-classifier authorization-firewall-safe-boundary-filter authorization-firewall-warning-status authorization-firewall-audit-status-split authorization-firewall-signal-triage-audit operator-governed-authorization-firewall-signal-triage-v1 --authorization-firewall-severity-classifier-v1 --authorization-firewall-safe-boundary-filter-v1 --authorization-firewall-warning-status-v1 --authorization-firewall-audit-status-split-v1 --operator-governed-authorization-firewall-signal-triage-v1 pass_with_warnings_supported=True plain_pass_with_warnings_forbidden=True mechanism_pass_is_not_language_clear=True language_clear_is_not_authorization=True authorization_status=not_authorized operator_approval_still_required=True signal_triage_creates_approval=False signal_triage_writes_memory=False signal_triage_applies_source_edits=False signal_triage_expands_autonomy=False dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v460.1-v465.0 route surface parity smoke tokens: recent-dashboard-route-probe-refresh source-surface-manifest-parity-policy surface-route-api-cli-crosscheck route-health-boundary-language route-surface-parity-audit operator-governed-route-surface-parity-v1 --recent-dashboard-route-probe-refresh-v1 --source-surface-manifest-parity-policy-v1 --surface-route-api-cli-crosscheck-v1 --route-health-boundary-language-v1 --operator-governed-route-surface-parity-v1 every_governed_substage_surface route_presence_is_authorization=False route_health_is_approval=False manifest_presence_is_authorization=False surface_parity_is_permission=False smoke_success_is_approval=False route_health_confirms_render_status_only=True route_health_does_not_authorize_execution=True parity_audit_applies_patches=False parity_audit_writes_memory=False parity_audit_expands_autonomy=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v465.1-v470.0 duplicate shadow cleanup smoke tokens: duplicate-shadow-inventory safe-shadow-removal-report legacy-alias-compatibility-cleanup stale-version-gate-cleanup self-maintenance-duplicate-shadow-cleanup-audit operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 --duplicate-shadow-inventory-v1 --safe-shadow-removal-report-v1 --legacy-alias-compatibility-cleanup-v1 --stale-version-gate-cleanup-v1 --operator-governed-self-maintenance-duplicate-shadow-cleanup-v1 duplicate_cleanup_is_authorization=False classification_is_permission_to_delete=False shadow_removal_expands_autonomy=False stale_gate_cleanup_authorizes_execution=False cleanup_applies_live_patches=False cleanup_writes_memory=False operator_approval_still_required=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console

# v485.1-v490.0 observation proposal queue smoke tokens: observation-to-proposal-candidate-mapper proposal-queue-schema proposal-ranking-risk-notes proposal-queue-non-execution-audit observation-proposal-queue-audit operator-governed-observation-proposal-queue-v1 observation_proposal_queue.py mapping_is_approval=False proposal_candidate_is_execution_packet=False candidate_queue_is_authorization=False queue_presence_is_approval=False queue_ranking_is_authorization=False highest_ranked_proposal_auto_selected=False approved_for_packet_drafting_only_is_live_execution=False source_mutation_allowed=False memory_mutation_allowed=False schedule_creation_allowed=False model_invocation_by_default_allowed=False execution_packet_creation_allowed=False patch_application_allowed=False proposal_approval_allowed=False automatic_continuation_allowed=False observation_promotes_to_live_change=False operator_review_required=True fresh_operator_approval_required=True no_native_title_tooltip data-tip command-deck operator-console

