from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from guided_work_session import create_guided_work_session, advance_guided_work_session, guided_session_text
from approval_manager import create_approval_from_dev_step
from memory import store_memory
from patch_applier import apply_patch, rollback_patch
from patch_suggester import list_patch_proposals, resolve_patch_id
from paths import DATA_DIR
from session_planner import create_session_plan, load_session_plan, session_plan_text
from task_queue import get_task, next_task, queue_tasks_from_session, resolve_task_id, task_detail_text
from test_report_reviewer import list_test_reviews, review_test_report, test_review_text
from test_runner import list_test_reports, run_test_workflow, test_report_text


DEV_CYCLES_DIR = DATA_DIR / "dev_cycles"
DEV_CYCLES_README = DEV_CYCLES_DIR / "README.md"
SAFE_REVIEW_KEEP_RECOMMENDATIONS = {"keep_patch", "checks_passed", "safe_to_apply_then_retest"}
SAFE_REVIEW_ROLLBACK_RECOMMENDATIONS = {"rollback_patch"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_storage() -> None:
    DEV_CYCLES_DIR.mkdir(parents=True, exist_ok=True)
    if not DEV_CYCLES_README.exists():
        DEV_CYCLES_README.write_text(
            "Saved supervised autonomous development cycle records. "
            "These records show what Eidolon chose, what it did, and what the next safe command is.\n",
            encoding="utf-8",
        )


def _new_cycle_id(step: str) -> str:
    safe_step = "".join(char if char.isalnum() or char in {"_", "-"} else "-" for char in step).strip("-") or "cycle"
    return f"devcycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_step}"


def _cycle_path(cycle_id: str) -> Path:
    _ensure_storage()
    return DEV_CYCLES_DIR / f"{cycle_id}.json"


def _save_cycle(cycle: dict[str, Any]) -> None:
    _ensure_storage()
    with _cycle_path(cycle["id"]).open("w", encoding="utf-8") as file:
        json.dump(cycle, file, indent=2)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_dev_cycles() -> list[dict[str, Any]]:
    _ensure_storage()
    cycles: list[dict[str, Any]] = []
    for path in DEV_CYCLES_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            cycles.append(data)
    return sorted(cycles, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_dev_cycle_id(cycle_id: str) -> str:
    token = (cycle_id or "").strip()
    token_lower = token.lower()
    cycles = list_dev_cycles()

    if token_lower in {"latest", "last"}:
        return cycles[0].get("id", "") if cycles else ""

    if token_lower.startswith("latest-"):
        desired = token_lower.replace("latest-", "", 1)
        matches = [cycle for cycle in cycles if str(cycle.get("step", "")).lower() == desired]
        return matches[0].get("id", "") if matches else ""

    return token


def get_dev_cycle(cycle_id: str) -> dict[str, Any] | None:
    resolved = resolve_dev_cycle_id(cycle_id)
    if not resolved:
        return None
    for cycle in list_dev_cycles():
        if cycle.get("id") == resolved:
            return cycle
    return None


def _latest_patch(status: str) -> dict[str, Any] | None:
    for patch in list_patch_proposals():
        if patch.get("status") == status:
            return patch
    return None


def _latest_report_for_patch(patch_id: str) -> dict[str, Any] | None:
    reports = [report for report in list_test_reports() if (report.get("patch", {}) or {}).get("patch_id") == patch_id]
    return reports[0] if reports else None


def _latest_review_for_report(report_id: str) -> dict[str, Any] | None:
    reviews = [review for review in list_test_reviews() if review.get("test_report_id") == report_id]
    return reviews[0] if reviews else None


def _safe_cycle(step: str, mode: str = "inspect") -> dict[str, Any]:
    return {
        "id": _new_cycle_id(step),
        "type": "autonomous_dev_cycle",
        "created_at": _now(),
        "mode": mode,
        "step": step,
        "ok": True,
        "decision": {},
        "action_result": {},
        "next_command": "",
        "useful_commands": [],
        "notes": [],
    }


def _state_snapshot() -> dict[str, Any]:
    proposed_patch = _latest_patch("proposed")
    applied_patch = _latest_patch("applied")
    ready_task = next_task()
    latest_report = _latest_report_for_patch(applied_patch.get("id", "")) if applied_patch else None
    latest_review = _latest_review_for_report(latest_report.get("id", "")) if latest_report else None

    return {
        "proposed_patch_id": proposed_patch.get("id", "") if proposed_patch else "",
        "proposed_patch_file": proposed_patch.get("target_file", "") if proposed_patch else "",
        "applied_patch_id": applied_patch.get("id", "") if applied_patch else "",
        "applied_patch_file": applied_patch.get("target_file", "") if applied_patch else "",
        "ready_task_id": ready_task.get("id", "") if ready_task else "",
        "ready_task_title": ready_task.get("title", "") if ready_task else "",
        "latest_patch_report_id": latest_report.get("id", "") if latest_report else "",
        "latest_patch_report_status": latest_report.get("status", "") if latest_report else "",
        "latest_patch_review_id": latest_review.get("id", "") if latest_review else "",
        "latest_patch_review_recommendation": latest_review.get("recommendation", "") if latest_review else "",
    }


def _decision_from_state(state: dict[str, Any], task_id: str = "latest-ready") -> dict[str, Any]:
    if state.get("proposed_patch_id"):
        return {
            "step": "review-proposed-patch",
            "reason": "A proposed patch exists. Review it before any file write.",
            "object_id": state["proposed_patch_id"],
            "next_command": "python conscious_agent/main.py --show-patch latest-proposed",
            "approval_command": "python conscious_agent/main.py --advance-dev-cycle --approve-dev-cycle-apply --dry-run",
        }

    if state.get("applied_patch_id"):
        patch_id = state["applied_patch_id"]
        report_id = state.get("latest_patch_report_id", "")
        review_id = state.get("latest_patch_review_id", "")
        recommendation = state.get("latest_patch_review_recommendation", "")

        if not report_id:
            return {
                "step": "test-applied-patch",
                "reason": "An applied patch exists with no saved test report yet.",
                "object_id": patch_id,
                "next_command": "python conscious_agent/main.py --run-test-workflow latest-applied --auto-review",
            }

        if report_id and not review_id:
            return {
                "step": "review-test-report",
                "reason": "The applied patch has a test report but no saved test review yet.",
                "object_id": report_id,
                "next_command": f"python conscious_agent/main.py --review-test-report {report_id}",
            }

        if recommendation in SAFE_REVIEW_ROLLBACK_RECOMMENDATIONS:
            return {
                "step": "awaiting-rollback-approval",
                "reason": f"Latest review recommends {recommendation}. Rollback requires explicit approval.",
                "object_id": patch_id,
                "next_command": "python conscious_agent/main.py --rollback-patch latest-applied --dry-run",
                "approval_command": "python conscious_agent/main.py --advance-dev-cycle --approve-dev-cycle-apply --dry-run",
            }

        if recommendation in SAFE_REVIEW_KEEP_RECOMMENDATIONS:
            return {
                "step": "patch-looks-safe",
                "reason": f"Latest review recommends {recommendation}. Next useful work should come from the task queue.",
                "object_id": review_id,
                "next_command": f"python conscious_agent/main.py --show-test-review {review_id}",
            }

        return {
            "step": "manual-review",
            "reason": f"Latest patch review recommendation is {recommendation or '[missing]'}. Manual review is safer than continuing automatically.",
            "object_id": review_id or report_id or patch_id,
            "next_command": f"python conscious_agent/main.py --show-test-review {review_id}" if review_id else f"python conscious_agent/main.py --show-test-report {report_id}",
        }

    resolved_task_id = resolve_task_id(task_id)
    task = get_task(resolved_task_id) if resolved_task_id else None
    if task:
        guided = create_guided_work_session(resolved_task_id)
        next_step = guided.get("next_step", {}) or {}
        return {
            "step": "advance-task",
            "reason": f"A ready task exists: {task.get('title')}. Use the guided work-session system for one safe step.",
            "object_id": resolved_task_id,
            "next_command": next_step.get("next_command", f"python conscious_agent/main.py --advance-work-session {resolved_task_id}"),
            "guided_session_id": guided.get("id", ""),
            "guided_next_step": next_step,
        }

    return {
        "step": "plan-and-queue",
        "reason": "No ready task exists. Create a session plan and queue tasks from it.",
        "object_id": "",
        "next_command": "python conscious_agent/main.py --advance-dev-cycle",
    }


def create_dev_cycle(task_id: str = "latest-ready") -> dict[str, Any]:
    state = _state_snapshot()
    decision = _decision_from_state(state, task_id=task_id)
    cycle = _safe_cycle(decision.get("step", "inspect"), mode="inspect")
    cycle["state"] = state
    cycle["decision"] = decision
    cycle["next_command"] = decision.get("next_command", "")
    cycle["useful_commands"] = [
        "python conscious_agent/main.py --dev-cycle",
        "python conscious_agent/main.py --advance-dev-cycle --dry-run",
        decision.get("next_command", ""),
        f"python conscious_agent/main.py --show-dev-cycle {cycle['id']}",
    ]
    _save_cycle(cycle)
    store_memory({
        "type": "autonomous_dev_cycle",
        "content": f"Created supervised dev cycle {cycle['id']}. Step: {cycle['step']}. Reason: {decision.get('reason')}",
        "source": "autonomous_dev_cycle",
        "dev_cycle_id": cycle["id"],
        "step": cycle["step"],
    })
    return cycle


def advance_dev_cycle(
    task_id: str = "latest-ready",
    dry_run: bool = False,
    approve_apply: bool = False,
    apply_evaluation: bool = False,
    use_ai: bool = True,
) -> dict[str, Any]:
    state = _state_snapshot()
    decision = _decision_from_state(state, task_id=task_id)
    step = decision.get("step", "inspect")
    cycle = _safe_cycle(step, mode="advance")
    cycle["state"] = state
    cycle["decision"] = decision
    cycle["dry_run"] = dry_run
    cycle["approve_apply"] = approve_apply
    cycle["apply_evaluation"] = apply_evaluation

    if step == "review-proposed-patch":
        if not approve_apply:
            approval = create_approval_from_dev_step(
                step=step,
                object_id=decision.get("object_id", ""),
                source="autonomous_dev_cycle",
                reason=decision.get("reason", ""),
            )
            cycle["ok"] = False
            cycle["action_result"] = {
                "action": "await-approval",
                "ok": False,
                "approval_id": approval.get("id") if approval else "",
                "message": "A proposed patch exists. Review it first. Applying requires explicit approval.",
            }
            cycle["next_command"] = f"python conscious_agent/main.py --show-approval {approval.get('id')}" if approval else decision.get("approval_command", "")
        else:
            result = apply_patch("latest-proposed", dry_run=dry_run)
            cycle["action_result"] = {
                "action": "apply-patch-dry-run" if dry_run else "apply-patch",
                "ok": result.ok,
                "patch_id": result.patch_id,
                "target_file": result.target_file,
                "message": result.message,
                "error": result.error,
                "backup_path": result.backup_path,
            }
            cycle["next_command"] = (
                "python conscious_agent/main.py --advance-dev-cycle --approve-dev-cycle-apply"
                if dry_run and result.ok else
                "python conscious_agent/main.py --run-test-workflow latest-applied --auto-review"
                if result.ok else
                "python conscious_agent/main.py --show-patch latest-proposed"
            )

    elif step == "awaiting-rollback-approval":
        if not approve_apply:
            approval = create_approval_from_dev_step(
                step=step,
                object_id=decision.get("object_id", ""),
                source="autonomous_dev_cycle",
                reason=decision.get("reason", ""),
            )
            cycle["ok"] = False
            cycle["action_result"] = {
                "action": "await-rollback-approval",
                "ok": False,
                "approval_id": approval.get("id") if approval else "",
                "message": "Rollback was recommended, but rollback requires explicit approval.",
            }
            cycle["next_command"] = f"python conscious_agent/main.py --show-approval {approval.get('id')}" if approval else decision.get("approval_command", "")
        else:
            result = rollback_patch("latest-applied", dry_run=dry_run)
            cycle["action_result"] = {
                "action": "rollback-patch-dry-run" if dry_run else "rollback-patch",
                "ok": result.ok,
                "patch_id": result.patch_id,
                "target_file": result.target_file,
                "message": result.message,
                "error": result.error,
                "backup_path": result.backup_path,
            }
            cycle["next_command"] = (
                "python conscious_agent/main.py --advance-dev-cycle --approve-dev-cycle-apply"
                if dry_run and result.ok else
                "python conscious_agent/main.py --plan-session --no-ai-session"
            )

    elif step == "test-applied-patch":
        result = run_test_workflow("latest-applied", commands=[], dry_run=dry_run)
        cycle["action_result"] = {
            "action": "test-workflow-dry-run" if dry_run else "test-workflow",
            "ok": result.ok,
            "report_id": result.report_id,
            "status": result.status,
            "recommendation": result.recommendation,
            "error": result.error,
        }
        cycle["next_command"] = (
            "python conscious_agent/main.py --advance-dev-cycle" if result.ok else "python conscious_agent/main.py --show-test-report latest"
        )

    elif step == "review-test-report":
        report_id = decision.get("object_id", "latest")
        result = review_test_report(report_id, use_ai=use_ai)
        cycle["action_result"] = {
            "action": "review-test-report",
            "ok": result.ok,
            "review_id": result.review_id,
            "recommendation": result.recommendation,
            "error": result.error,
        }
        cycle["next_command"] = "python conscious_agent/main.py --dev-cycle"

    elif step == "advance-task":
        task_ref = decision.get("object_id", task_id) or task_id
        guided = advance_guided_work_session(
            task_ref,
            dry_run=dry_run,
            use_ai=use_ai,
            apply_guided_evaluation=apply_evaluation,
        )
        cycle["action_result"] = {
            "action": "advance-guided-work-session",
            "ok": guided.get("ok", False),
            "guided_session_id": guided.get("id", ""),
            "step": guided.get("step", ""),
            "result": guided.get("result", {}),
            "final_task_status": guided.get("final_task_status", ""),
        }
        next_step = guided.get("next_step", {}) or {}
        cycle["next_command"] = next_step.get("next_command", "python conscious_agent/main.py --dev-cycle")

    elif step == "plan-and-queue":
        if dry_run:
            cycle["action_result"] = {
                "action": "plan-and-queue-dry-run",
                "ok": True,
                "message": "Dry run only. No session plan or tasks were created.",
            }
            cycle["next_command"] = "python conscious_agent/main.py --advance-dev-cycle"
        else:
            plan_result = create_session_plan(use_ai=use_ai)
            if not plan_result.ok:
                cycle["ok"] = False
                cycle["action_result"] = {
                    "action": "plan-session",
                    "ok": False,
                    "error": plan_result.error,
                }
                cycle["next_command"] = "python conscious_agent/main.py --maintenance-scan --no-ai-maintenance"
            else:
                queued = queue_tasks_from_session(plan_result.plan_id, limit=4)
                cycle["action_result"] = {
                    "action": "plan-and-queue",
                    "ok": bool(queued.get("ok")),
                    "plan_id": plan_result.plan_id,
                    "created_task_ids": [task.get("id") for task in queued.get("created", [])],
                    "skipped": queued.get("skipped", []),
                    "error": queued.get("error", ""),
                }
                cycle["next_command"] = "python conscious_agent/main.py --next-task"

    else:
        cycle["ok"] = False
        cycle["action_result"] = {
            "action": "manual-review",
            "ok": False,
            "message": decision.get("reason", "No safe automatic action was selected."),
        }
        cycle["next_command"] = decision.get("next_command", "python conscious_agent/main.py --dev-cycle")

    refreshed_state = _state_snapshot()
    refreshed_decision = _decision_from_state(refreshed_state, task_id=task_id)
    cycle["final_state"] = refreshed_state
    cycle["next_decision"] = refreshed_decision
    cycle["useful_commands"] = [
        "python conscious_agent/main.py --dev-cycle",
        cycle.get("next_command", ""),
        refreshed_decision.get("next_command", ""),
        f"python conscious_agent/main.py --show-dev-cycle {cycle['id']}",
    ]
    _save_cycle(cycle)
    store_memory({
        "type": "autonomous_dev_cycle_advance",
        "content": f"Advanced supervised dev cycle {cycle['id']}. Step: {cycle['step']}. OK: {cycle.get('action_result', {}).get('ok')}",
        "source": "autonomous_dev_cycle",
        "dev_cycle_id": cycle["id"],
        "step": cycle["step"],
        "ok": cycle.get("action_result", {}).get("ok"),
    })
    return cycle


def dev_cycle_text(cycle: dict[str, Any], full: bool = False) -> str:
    if not cycle:
        return "Dev cycle not found."

    lines = [
        f"# Supervised Dev Cycle: {cycle.get('id')}",
        f"Created: {cycle.get('created_at')}",
        f"Mode: {cycle.get('mode')}",
        f"Step: {cycle.get('step')}",
        f"OK: {cycle.get('ok')}",
    ]

    decision = cycle.get("decision", {}) or {}
    if decision:
        lines.append("")
        lines.append("## Decision")
        lines.append(f"Step: {decision.get('step')}")
        lines.append(f"Reason: {decision.get('reason')}")
        if decision.get("object_id"):
            lines.append(f"Object: {decision.get('object_id')}")
        if decision.get("next_command"):
            lines.append(f"Next command: {decision.get('next_command')}")
        if decision.get("approval_command"):
            lines.append(f"Approval command: {decision.get('approval_command')}")

    action = cycle.get("action_result", {}) or {}
    if action:
        lines.append("")
        lines.append("## Action result")
        lines.append(f"Action: {action.get('action')}")
        lines.append(f"OK: {action.get('ok')}")
        for key in ["message", "error", "approval_id", "patch_id", "report_id", "review_id", "guided_session_id", "status", "recommendation", "final_task_status"]:
            if action.get(key) not in {None, ""}:
                lines.append(f"{key.replace('_', ' ').title()}: {action.get(key)}")

    next_decision = cycle.get("next_decision", {}) or {}
    if next_decision:
        lines.append("")
        lines.append("## Next decision")
        lines.append(f"Step: {next_decision.get('step')}")
        lines.append(f"Reason: {next_decision.get('reason')}")
        if next_decision.get("next_command"):
            lines.append(f"Command: {next_decision.get('next_command')}")

    useful = [command for command in cycle.get("useful_commands", []) if command]
    if useful:
        lines.append("")
        lines.append("## Useful commands")
        for command in useful:
            lines.append(command)

    if full:
        lines.append("")
        lines.append("## State")
        lines.append(json.dumps(cycle.get("state", {}), indent=2))
        if cycle.get("final_state"):
            lines.append("")
            lines.append("## Final state")
            lines.append(json.dumps(cycle.get("final_state", {}), indent=2))
        if action.get("result"):
            lines.append("")
            lines.append("## Nested result")
            lines.append(json.dumps(action.get("result"), indent=2))

    return "\n".join(lines)


def print_dev_cycle(task_id: str = "latest-ready", full: bool = False) -> None:
    cycle = create_dev_cycle(task_id=task_id)
    print(dev_cycle_text(cycle, full=full))


def print_advance_dev_cycle(
    task_id: str = "latest-ready",
    dry_run: bool = False,
    approve_apply: bool = False,
    apply_evaluation: bool = False,
    use_ai: bool = True,
    full: bool = False,
) -> None:
    cycle = advance_dev_cycle(
        task_id=task_id,
        dry_run=dry_run,
        approve_apply=approve_apply,
        apply_evaluation=apply_evaluation,
        use_ai=use_ai,
    )
    print(dev_cycle_text(cycle, full=full))


def print_dev_cycles() -> None:
    cycles = list_dev_cycles()
    if not cycles:
        print("No dev cycle records found.")
        return
    for cycle in cycles:
        decision = cycle.get("decision", {}) or {}
        action = cycle.get("action_result", {}) or {}
        print(
            f"{cycle.get('id')} | {cycle.get('mode')} | {cycle.get('step')} | "
            f"ok={cycle.get('ok')} | action_ok={action.get('ok')} | {decision.get('reason', '')}"
        )


def print_saved_dev_cycle(cycle_id: str = "latest", full: bool = False) -> None:
    cycle = get_dev_cycle(cycle_id)
    if not cycle:
        print(f"Dev cycle not found: {cycle_id}")
        return
    print(dev_cycle_text(cycle, full=full))
