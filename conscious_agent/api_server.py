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
from work_cycle import list_work_cycles, load_work_cycle, run_supervised_work_cycle
from dev_loop_runner import get_dev_loop, list_dev_loops, run_dev_loop
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports
from watch_mode import list_watch_reports, load_watch_report, run_watch_loop, run_watch_once


API_VERSION = "5.7"


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
            "GET /api/tasks/{id}/lifecycle": "Get one task lifecycle record.",
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
    work_cycles = list_work_cycles()
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
            "work_cycles": len(work_cycles),
        },
        "task_lifecycle": lifecycle_summary,
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
        if len(parts) == 3 and parts[2] == "approvals":
            include_closed = _query_bool(query, "include_closed", True)
            return 200, _ok(list_task_approvals(parts[1], include_closed=include_closed))
        if len(parts) == 3 and parts[2] == "lifecycle":
            task = get_task(parts[1])
            if not task:
                raise ApiError(404, f"Task not found: {parts[1]}")
            return 200, _ok(derive_task_lifecycle(task))
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

    if parts == ["work-cycles", "run"]:
        project_id = str(body.get("project_id") or body.get("project") or "eidolon")
        max_steps = int(body.get("max_steps", body.get("steps", 1)) or 1)
        dry_run = _body_bool(body, "dry_run", True)
        use_ai = _body_bool(body, "use_ai", True)
        approve_work_execution = _body_bool(body, "approve_work_execution", False)
        seed_if_empty = _body_bool(body, "seed_if_empty", True)
        auto_followups = _body_bool(body, "auto_create_patch_followups", True)
        result = run_supervised_work_cycle(
            project_id=project_id,
            max_steps=max_steps,
            dry_run=dry_run,
            use_ai=use_ai,
            approve_work_execution=approve_work_execution,
            seed_if_empty=seed_if_empty,
            auto_create_patch_followups=auto_followups,
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
    server_version = "EidolonAPI/5.7"

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
