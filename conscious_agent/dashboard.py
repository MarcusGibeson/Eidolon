
from __future__ import annotations

import json
import traceback
from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from approval_manager import approve_approval, approval_text, get_approval, list_approvals, reject_approval
from api_server import dispatch_api, parse_request_body, _to_jsonable
from chat_action_router import (
    propose_chat_action,
    execute_chat_action,
    list_chat_actions,
    load_chat_action,
    chat_action_text,
)
from dashboard_chat_console import (
    create_dashboard_chat_turn,
    dashboard_chat_turn_text,
    list_dashboard_chat_turns,
    load_dashboard_chat_turn,
)
from desktop_shell import desktop_status_text
from desktop_setup_helper import create_setup_report, list_setup_reports, load_setup_report, setup_report_text
from desktop_onboarding_wizard import build_onboarding_run, list_onboarding_runs, load_onboarding_run, onboarding_run_text
from diagnostics import (
    build_diagnostic_report,
    diagnostic_report_text,
    list_diagnostic_reports,
    load_diagnostic_report,
    save_diagnostic_report,
)
from goal_manager import add_goal, get_goal, list_goals
from maintenance_advisor import (
    list_maintenance_scans,
    load_maintenance_scan,
    maintenance_scan_text,
    run_maintenance_scan,
)
from notification_manager import (
    clear_dismissed_notifications,
    list_notifications,
    load_notification,
    notification_text,
    update_notification_status,
)
from memory import load_memories
from memory_compactor import (
    list_memory_summaries,
    load_memory_summary,
    memory_status_text,
    memory_summary_text,
)
from patch_suggester import list_patch_proposals, load_patch_proposal, patch_proposal_text, suggest_patch
from work_queue_patch_bridge import (
    create_patch_followup_items,
    create_patch_work_item,
    suggest_patch_for_work_item,
)
from project_manager import get_active_project
from session_planner import create_session_plan, list_session_plans, load_session_plan, session_plan_text
from settings_manager import get_setting, load_settings, set_setting, settings_health, settings_text
from task_queue import add_task, get_task, list_tasks, next_task, task_detail_text, task_status_counts
from work_queue import (
    add_work_item,
    find_work_item,
    format_work_item,
    list_work_items,
    summarize_queue,
    update_work_item,
)
from task_work_executor import execute_next_task_work, execute_task_work_item, task_work_execution_text
from task_approval_bridge import request_task_work_approval, task_approvals_text
from task_lifecycle import (
    STAGE_FILTER_LABELS,
    derive_task_lifecycle,
    lifecycle_stage_matches,
    list_task_lifecycles,
    normalize_lifecycle_stage_filter,
    task_lifecycle_summary,
    task_lifecycle_text,
)
from work_cycle import run_supervised_work_cycle, list_work_cycles, load_work_cycle, work_cycle_text
from test_runner import list_test_reports, load_test_report, test_report_text
from test_report_reviewer import list_test_reviews, load_test_review, test_review_text
from watch_mode import list_watch_reports, load_watch_report, run_watch_once, run_watch_loop, watch_report_text
from autonomous_dev_cycle import dev_cycle_text, get_dev_cycle, list_dev_cycles
from dev_loop_runner import get_dev_loop, list_dev_loops, run_dev_loop, dev_loop_text


DASHBOARD_TITLE = "Eidolon Dashboard"
DASHBOARD_VERSION = "5.7"


class DashboardState:
    message: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe(value: Any) -> str:
    return escape(str(value), quote=True)


def _fmt(value: Any) -> str:
    return _safe(value if value not in {None, ""} else "[none]")


def _json_block(data: Any) -> str:
    return f"<pre>{_safe(json.dumps(data, indent=2, default=str))}</pre>"


def _text_block(text: str) -> str:
    return f"<pre>{_safe(text)}</pre>"


def _card(title: str, body: str) -> str:
    return f"<section class='card'><h2>{_safe(title)}</h2>{body}</section>"


def _small_list(items: list[str]) -> str:
    if not items:
        return "<p class='muted'>None found.</p>"
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _button(label: str, action: str, **fields: Any) -> str:
    inputs = [f"<input type='hidden' name='action' value='{_safe(action)}'>"]
    for key, value in fields.items():
        inputs.append(f"<input type='hidden' name='{_safe(key)}' value='{_safe(value)}'>")
    return f"<form method='post' action='/action' class='inline'>{''.join(inputs)}<button type='submit'>{_safe(label)}</button></form>"


def _detail_link(kind: str, item_id: str, label: str | None = None, full: bool = False) -> str:
    if not item_id:
        return "<span class='muted'>[no id]</span>"
    full_q = "&full=1" if full else ""
    return f"<a href='/detail?kind={_safe(kind)}&id={_safe(item_id)}{full_q}'>{_safe(label or item_id)}</a>"


def _back_link(path: str, label: str = "Back") -> str:
    return f"<p><a href='{_safe(path)}'>← {_safe(label)}</a></p>"


def _goal_text(goal: dict[str, Any] | None, full: bool = False) -> str:
    if not goal:
        return "Goal not found."
    lines = [
        f"# Goal: {goal.get('id')}",
        f"Title: {goal.get('title')}",
        f"Status: {goal.get('status')}",
        f"Priority: {goal.get('priority')}",
        f"Project: {goal.get('project') or '[none]'}",
        f"Created: {goal.get('created_at')}",
        f"Updated: {goal.get('updated_at')}",
    ]
    if goal.get('description'):
        lines.extend(["", "## Description", str(goal.get('description'))])
    if goal.get('next_action'):
        lines.extend(["", "## Next action", str(goal.get('next_action'))])
    if goal.get('next_actions'):
        lines.append("")
        lines.append("## Next actions")
        lines.extend(f"- {action}" for action in goal.get('next_actions', []))
    if goal.get('blockers'):
        lines.append("")
        lines.append("## Blockers")
        lines.extend(f"- {blocker}" for blocker in goal.get('blockers', []))
    if goal.get('notes'):
        lines.append("")
        lines.append("## Notes")
        lines.extend(f"- {note}" for note in goal.get('notes', []))
    if full:
        lines.extend(["", "## Raw goal", json.dumps(goal, indent=2, default=str)])
    return "\n".join(lines)



def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in {None, ""}:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _live_refresh_bar(settings: dict[str, Any]) -> str:
    enabled = _as_bool(settings.get("dashboard_live_refresh_enabled"), True)
    interval = max(2, int(settings.get("dashboard_live_refresh_seconds", 5) or 5))
    if not enabled:
        return "<div class='livebar muted'><span>Live refresh disabled.</span></div>"
    return (
        "<div class='livebar'>"
        "<span id='live-refresh-dot' class='live-dot'>●</span> "
        "<span id='live-refresh-status'>Live refresh starting...</span> "
        f"<span class='muted'>Polling /api/status every {_safe(interval)}s.</span> "
        "<button type='button' onclick='window.eidolonRefreshNow && window.eidolonRefreshNow()'>Refresh now</button>"
        "</div>"
    )


def _live_refresh_script(settings: dict[str, Any]) -> str:
    enabled = _as_bool(settings.get("dashboard_live_refresh_enabled"), True)
    interval = max(2, int(settings.get("dashboard_live_refresh_seconds", 5) or 5))
    config = json.dumps({"enabled": enabled, "intervalMs": interval * 1000})
    script_body = r'''
(function () {
  const cfg = window.EIDOLON_LIVE || {};
  if (!cfg.enabled) return;

  function valueAt(root, path) {
    if (!root || !path) return undefined;
    return path.split('.').reduce(function (current, key) {
      if (current === undefined || current === null) return undefined;
      return current[key];
    }, root);
  }

  function displayValue(value) {
    if (value === undefined || value === null || value === '') return '[none]';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  function updateLiveDom(data) {
    document.querySelectorAll('[data-live-count]').forEach(function (el) {
      const value = valueAt(data, el.getAttribute('data-live-count'));
      if (value !== undefined && value !== null) el.textContent = String(value);
    });
    document.querySelectorAll('[data-live-text]').forEach(function (el) {
      const value = valueAt(data, el.getAttribute('data-live-text'));
      if (value !== undefined) el.textContent = displayValue(value);
    });
    document.querySelectorAll('[data-live-detail-href]').forEach(function (el) {
      const path = el.getAttribute('data-live-detail-href');
      const kind = el.getAttribute('data-live-detail-kind') || '';
      const value = valueAt(data, path);
      if (value && kind) el.setAttribute('href', '/detail?kind=' + encodeURIComponent(kind) + '&id=' + encodeURIComponent(value));
    });
  }

  async function pollStatus() {
    const status = document.getElementById('live-refresh-status');
    const dot = document.getElementById('live-refresh-dot');
    try {
      if (status) status.textContent = 'Live refresh: polling...';
      if (dot) dot.className = 'live-dot polling';
      const response = await fetch('/api/status?ts=' + Date.now(), { cache: 'no-store' });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || 'API status returned an error');
      const data = payload.data || {};
      updateLiveDom(data);
      const updated = new Date().toLocaleTimeString();
      if (status) status.textContent = 'Live refresh: updated ' + updated;
      if (dot) dot.className = 'live-dot ok';
      document.title = 'Eidolon Dashboard' +
        ' · approvals ' + displayValue(valueAt(data, 'counts.pending_approvals')) +
        ' · notes ' + displayValue(valueAt(data, 'counts.unread_notifications'));
    } catch (error) {
      if (status) status.textContent = 'Live refresh failed: ' + error.message;
      if (dot) dot.className = 'live-dot bad';
    }
  }

  window.eidolonRefreshNow = pollStatus;
  pollStatus();
  window.setInterval(pollStatus, Math.max(2000, cfg.intervalMs || 5000));
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) pollStatus();
  });
})();
'''
    return "<script>\nwindow.EIDOLON_LIVE = " + config + ";\n" + script_body + "\n</script>"


def _layout(path: str, content: str) -> str:
    settings = load_settings()
    nav_items = [
        ("/", "Overview"),
        ("/actions", "Action Center"),
        ("/chat-console", "Chat Console"),
        ("/chat-actions", "Chat Actions <span class='nav-badge' data-live-count='counts.chat_actions'></span>"),
        ("/create", "Create"),
        ("/tasks", "Tasks <span class='nav-badge' data-live-count='counts.tasks'></span>"),
        ("/tasks-work", "Tasks / Work <span class='nav-badge' data-live-count='counts.work_queue_pending'></span>"),
        ("/work-cycle", "Work Cycle <span class='nav-badge' data-live-count='counts.work_cycles'></span>"),
        ("/approvals", "Approvals <span class='nav-badge warn-badge' data-live-count='counts.pending_approvals'></span>"),
        ("/notifications", "Notifications <span class='nav-badge warn-badge' data-live-count='counts.unread_notifications'></span>"),
        ("/watch", "Watch <span class='nav-badge' data-live-count='counts.watch_reports'></span>"),
        ("/patches", "Patches <span class='nav-badge' data-live-count='counts.patches'></span>"),
        ("/goals", "Goals <span class='nav-badge' data-live-count='counts.goals'></span>"),
        ("/diagnostics", "Diagnostics <span class='nav-badge' data-live-count='counts.diagnostic_reports'></span>"),
        ("/settings", "Settings"),
        ("/api-info", "API"),
        ("/desktop", "Desktop"),
        ("/setup", "Setup <span class='nav-badge' data-live-count='counts.setup_reports'></span>"),
        ("/onboarding", "Onboarding <span class='nav-badge' data-live-count='counts.onboarding_runs'></span>"),
        ("/activity", "Activity"),
    ]
    nav = "".join(
        f"<a class='{('active' if href == path else '')}' href='{href}'>{label}</a>"
        for href, label in nav_items
    )
    msg = f"<div class='notice ok'>{_safe(DashboardState.message)}</div>" if DashboardState.message else ""
    err = f"<div class='notice bad'>{_safe(DashboardState.error)}</div>" if DashboardState.error else ""
    DashboardState.message = ""
    DashboardState.error = ""

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{DASHBOARD_TITLE}</title>
<style>
:root {{ --bg:#101217; --panel:#171b23; --panel2:#202634; --text:#eef1f7; --muted:#9aa5b5; --accent:#8fb3ff; --good:#77d192; --bad:#ff8f8f; --warn:#ffd27d; --border:#30384a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Segoe UI, system-ui, -apple-system, sans-serif; background:var(--bg); color:var(--text); }}
header {{ padding:18px 24px; border-bottom:1px solid var(--border); background:#0d0f14; position:sticky; top:0; z-index:2; }}
h1 {{ margin:0 0 4px 0; font-size:22px; }}
.subtitle {{ color:var(--muted); font-size:13px; }}
nav {{ display:flex; flex-wrap:wrap; gap:8px; padding:12px 24px; border-bottom:1px solid var(--border); background:#11151d; }}
nav a {{ color:var(--text); text-decoration:none; padding:8px 10px; border:1px solid var(--border); border-radius:10px; background:var(--panel); }}
nav a.active {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
a {{ color:var(--accent); }} a:hover {{ color:#dbe7ff; }}
main {{ max-width:1200px; margin:0 auto; padding:22px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; }}
.card {{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:16px; margin-bottom:16px; }}
.card h2 {{ margin:0 0 12px; font-size:18px; }}
.card h3 {{ margin:14px 0 8px; font-size:15px; color:var(--accent); }}
.kpi {{ font-size:30px; font-weight:700; }}
.muted {{ color:var(--muted); }}
.good {{ color:var(--good); }} .badtext {{ color:var(--bad); }} .warn {{ color:var(--warn); }}
pre {{ white-space:pre-wrap; word-break:break-word; background:#0b0d12; border:1px solid var(--border); border-radius:12px; padding:12px; max-height:520px; overflow:auto; }}
button, input, select {{ background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:8px 10px; }}
button {{ cursor:pointer; }} button:hover {{ border-color:var(--accent); }}
form.inline {{ display:inline-block; margin:2px 4px 2px 0; }}
form.stack {{ display:grid; gap:8px; max-width:760px; }}
textarea {{ width:100%; background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:10px; padding:10px; font-family:inherit; }}
.action-card {{ border:1px solid var(--border); border-radius:14px; padding:12px; background:#121720; }}
.notice {{ padding:12px 14px; border-radius:12px; margin-bottom:14px; border:1px solid var(--border); }}
.notice.ok {{ background:#122619; color:#d7ffe0; }} .notice.bad {{ background:#2b1515; color:#ffdada; }}
table {{ width:100%; border-collapse:collapse; }} th,td {{ border-bottom:1px solid var(--border); padding:8px; vertical-align:top; text-align:left; }} th {{ color:var(--muted); font-weight:600; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--border); color:var(--muted); font-size:12px; }}
.stage-pill {{ display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid var(--border); font-size:12px; font-weight:600; background:#151b26; color:var(--muted); }}
.stage-ready {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-active {{ color:#dbe7ff; border-color:#365c9b; background:#111d35; }}
.stage-approval-required, .stage-approval-pending, .stage-approved-ready {{ color:var(--warn); border-color:#6a4c18; background:#23190b; }}
.stage-approval-rejected, .stage-approval-failed, .stage-blocked {{ color:var(--bad); border-color:#6d3030; background:#261111; }}
.stage-patch-proposed {{ color:#cdb7ff; border-color:#514277; background:#1c1730; }}
.stage-done {{ color:var(--good); border-color:#315f43; background:#102016; }}
.stage-cancelled, .stage-unknown {{ color:var(--muted); }}
.lifecycle-strip {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
.lifecycle-step {{ padding:8px 10px; border:1px solid var(--border); border-radius:12px; background:#10151e; color:var(--muted); font-size:12px; }}
.lifecycle-step.current {{ border-color:var(--accent); color:#fff; box-shadow:0 0 0 1px var(--accent) inset; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:10px 0; }}
	.filter-chip {{ display:inline-block; padding:7px 10px; border:1px solid var(--border); border-radius:999px; background:#111722; color:var(--text); text-decoration:none; font-size:12px; }}
	.filter-chip.active {{ border-color:var(--accent); box-shadow:0 0 0 1px var(--accent) inset; }}
.footer {{ color:var(--muted); font-size:12px; margin-top:30px; }}
.nav-badge {{ display:inline-block; min-width:20px; margin-left:5px; padding:1px 6px; border-radius:999px; background:#253047; color:#dbe7ff; font-size:11px; text-align:center; }}
.nav-badge:empty {{ display:none; }}
.warn-badge:not(:empty) {{ background:#4a3215; color:#ffd27d; }}
.livebar {{ display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px; padding:10px 12px; border:1px solid var(--border); border-radius:12px; background:#0f141d; color:var(--muted); }}
.live-dot {{ color:var(--muted); }} .live-dot.ok {{ color:var(--good); }} .live-dot.bad {{ color:var(--bad); }} .live-dot.polling {{ color:var(--warn); }}
</style>
</head>
<body>
<header><h1>{DASHBOARD_TITLE}</h1><div class='subtitle'>Local-only dashboard at {_safe(settings.get('dashboard_host','127.0.0.1'))}:{_safe(settings.get('dashboard_port',8765))}. The ghost gets a browser tab. Somehow this is progress.</div></header>
<nav>{nav}</nav>
<main>{_live_refresh_bar(settings)}{msg}{err}{content}<div class='footer'>Generated at {_safe(_now())}. Approval gates still apply. No browser button bypasses safety checks, because we enjoy not crying.</div></main>
{_live_refresh_script(settings)}
</body>
</html>"""


def _status_cards() -> str:
    tasks = list_tasks(include_cancelled=False)
    approvals = list_approvals(status="pending", include_closed=False)
    notifications = list_notifications(status="unread", include_dismissed=False)
    patches = list_patch_proposals()
    memories = load_memories()
    reports = list_test_reports()
    reviews = list_test_reviews()
    project = get_active_project() or {}
    counts = task_status_counts()
    work_summary = summarize_queue()
    cards = [
        _card("Active Project", f"<div class='kpi' data-live-text='active_project.name'>{_fmt(project.get('name','[none]'))}</div><p class='muted' data-live-text='active_project.path'>{_fmt(project.get('path',''))}</p>"),
        _card("Tasks", f"<div class='kpi' data-live-count='counts.tasks'>{len(tasks)}</div><p class='muted'>Ready: <span data-live-count='counts.task_status.ready'>{counts.get('ready',0)}</span> · Active: <span data-live-count='counts.task_status.active'>{counts.get('active',0)}</span> · Blocked: <span data-live-count='counts.task_status.blocked'>{counts.get('blocked',0)}</span></p>"),
        _card("Tasks / Work", f"<div class='kpi' data-live-count='counts.work_queue_pending'>{work_summary.get('pending',0)}</div><p class='muted'>Active: <span data-live-count='counts.work_queue_active'>{work_summary.get('active',0)}</span> · Blocked: <span data-live-count='counts.work_queue_blocked'>{work_summary.get('blocked',0)}</span> · Approval: <span data-live-count='counts.work_queue_approval_required'>{work_summary.get('approval_required',0)}</span></p>"),
        _card("Work Cycles", f"<div class='kpi' data-live-count='counts.work_cycles'>{len(list_work_cycles())}</div><p class='muted'>Bounded supervised queue cycles.</p>"),
        _card("Pending Approvals", f"<div class='kpi' data-live-count='counts.pending_approvals'>{len(approvals)}</div><p class='muted'>Things waiting for your glorious human permission.</p>"),
        _card("Unread Notifications", f"<div class='kpi' data-live-count='counts.unread_notifications'>{len(notifications)}</div><p class='muted'>Saved alerts from watch mode and other systems.</p>"),
        _card("Patches", f"<div class='kpi' data-live-count='counts.patches'>{len(patches)}</div><p class='muted'>Proposed/applied/rolled back patch records.</p>"),
        _card("Memories", f"<div class='kpi' data-live-count='counts.memories'>{len(memories)}</div><p class='muted'>Active JSON memories.</p>"),
        _card("Tests", f"<div class='kpi' data-live-count='counts.test_reports'>{len(reports)}</div><p class='muted'>Reports: <span data-live-count='counts.test_reports'>{len(reports)}</span> · Reviews: <span data-live-count='counts.test_reviews'>{len(reviews)}</span></p>"),
    ]
    return "<div class='grid'>" + "".join(cards) + "</div>"


def render_overview() -> str:
    next_item = next_task()
    next_task_html = task_detail_text(next_item, full=False) if next_item else "No ready task found. Suspiciously peaceful."
    actions = "".join([
        "<p><a href='/actions'><button type='button'>Open Action Center</button></a> <a href='/chat-console'><button type='button'>Open Chat Console</button></a> <a href='/tasks-work'><button type='button'>Open Tasks / Work</button></a> <a href='/work-cycle'><button type='button'>Open Work Cycle</button></a> <a href='/create'><button type='button'>Create Task / Goal / Patch</button></a> <a href='/onboarding'><button type='button'>Open Onboarding</button></a></p>",
        _button("Run diagnostics", "run_diagnostics"),
        _button("Plan session", "plan_session"),
        _button("Maintenance scan", "maintenance_scan"),
        _button("Watch once", "watch_once_no_ai"),
        _button("Run onboarding", "run_onboarding"),
        _button("Dry-run next work", "work_queue_execute_next", dry_run="true"),
        _button("Dry-run dev loop", "dev_loop_dry"),
    ])
    return _layout("/", _status_cards() + _card("Quick Actions", actions) + _card("Next Task", _text_block(next_task_html)) + _card("Memory Status", _text_block(memory_status_text())))




def _action_panel(title: str, description: str, controls: str, priority: str = "normal") -> str:
    badge = f"<span class='badge'>{_safe(priority)}</span> " if priority else ""
    return (
        "<div class='card'>"
        f"<h3>{badge}{_safe(title)}</h3>"
        f"<p class='muted'>{_safe(description)}</p>"
        f"<div>{controls}</div>"
        "</div>"
    )


def _action_link(label: str, href: str) -> str:
    return f"<a href='{_safe(href)}'><button type='button'>{_safe(label)}</button></a>"


def render_action_center() -> str:
    pending_approvals = list_approvals(status="pending", include_closed=False)
    unread_notifications = list_notifications(status="unread", include_dismissed=False)
    proposed_patches = [patch for patch in list_patch_proposals() if patch.get("status") == "proposed"]
    tasks = list_tasks(include_cancelled=False)
    ready_tasks = [task for task in tasks if task.get("status") in {"ready", "planned"}]
    active_tasks = [task for task in tasks if task.get("status") == "active"]
    blocked_tasks = [task for task in tasks if task.get("status") == "blocked"]
    diagnostic_reports = list_diagnostic_reports()
    latest_diag = diagnostic_reports[0] if diagnostic_reports else None
    latest_diag_status = latest_diag.get("overall_status") if latest_diag else "missing"
    watch_reports = list_watch_reports()
    latest_watch = watch_reports[0] if watch_reports else None
    latest_watch_status = latest_watch.get("status") or latest_watch.get("stopped_reason") if latest_watch else "missing"

    recommendations: list[str] = []
    panels: list[str] = []

    if pending_approvals:
        approval = pending_approvals[0]
        approval_id = approval.get("id", "latest-pending")
        recommendations.append(f"Review pending approval: {approval.get('summary', approval_id)}")
        controls = " ".join([
            _action_link("Open latest approval", f"/detail?kind=approval&id={_safe(approval_id)}"),
            _button("Dry-run approval", "approve", approval_id=approval_id, dry_run="true"),
            _button("Approve", "approve", approval_id=approval_id),
            _button("Reject", "reject", approval_id=approval_id),
        ])
        panels.append(_action_panel("Pending approval", "An action is waiting for your explicit approval. Dry-run first, because apparently consequences exist.", controls, "high"))

    if unread_notifications:
        note = unread_notifications[0]
        note_id = note.get("id", "latest-unread")
        recommendations.append(f"Read notification: {note.get('title', note_id)}")
        controls = " ".join([
            _action_link("Open notification", f"/detail?kind=notification&id={_safe(note_id)}"),
            _button("Mark read", "notification_read", notification_id=note_id),
            _button("Dismiss", "notification_dismiss", notification_id=note_id),
        ])
        panels.append(_action_panel("Unread notification", "Watch mode or another system surfaced something worth attention.", controls, "medium"))

    if latest_diag_status in {"fail", "warn", "missing", None, "[none]"}:
        recommendations.append("Run diagnostics before advancing more work.")
        controls = " ".join([
            _button("Run diagnostics", "run_diagnostics"),
            _action_link("Open diagnostics", "/diagnostics"),
        ])
        panels.append(_action_panel("Diagnostics", f"Latest diagnostic status: {latest_diag_status}. Software organs should be checked before the ghost does cardio.", controls, "medium"))

    if proposed_patches and not pending_approvals:
        patch = proposed_patches[0]
        patch_id = patch.get("id", "latest-proposed")
        recommendations.append(f"Inspect proposed patch for {patch.get('target_file', '[unknown file]')}.")
        controls = " ".join([
            _action_link("Open latest proposed patch", f"/detail?kind=patch&id={_safe(patch_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
        ])
        panels.append(_action_panel("Proposed patch", "A patch exists but has not been applied. Inspect it or let a dev-loop dry-run create the next approval.", controls, "medium"))

    if active_tasks:
        task = active_tasks[0]
        task_id = task.get("id", "latest-active")
        recommendations.append(f"Continue active task: {task.get('title', task_id)}")
        controls = " ".join([
            _action_link("Open active task", f"/detail?kind=task&id={_safe(task_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
            _button("Run safe dev loop", "dev_loop_safe"),
        ])
        panels.append(_action_panel("Active task", "A task is already active. Continue that before inventing new work like a productivity gremlin.", controls, "medium"))
    elif ready_tasks:
        task = ready_tasks[0]
        task_id = task.get("id", "latest-ready")
        recommendations.append(f"Start or advance ready task: {task.get('title', task_id)}")
        controls = " ".join([
            _action_link("Open ready task", f"/detail?kind=task&id={_safe(task_id)}"),
            _button("Dry-run dev loop", "dev_loop_dry"),
            _button("Run safe dev loop", "dev_loop_safe"),
        ])
        panels.append(_action_panel("Ready task", "A queued task is ready. The dev loop can advance one safe step through existing gates.", controls, "normal"))

    if blocked_tasks:
        recommendations.append(f"Review {len(blocked_tasks)} blocked task(s).")
        panels.append(_action_panel("Blocked tasks", f"{len(blocked_tasks)} task(s) are blocked. Read them before generating yet another plan-shaped pile.", _action_link("Open tasks", "/tasks"), "normal"))

    if not ready_tasks and not active_tasks:
        recommendations.append("Create a fresh session plan and queue tasks from it.")
        controls = " ".join([
            _button("Plan session", "plan_session"),
            _action_link("Open activity", "/activity"),
        ])
        panels.append(_action_panel("Plan next session", "No ready or active task was found. Create a session plan before the project starts wandering in circles.", controls, "normal"))

    watch_controls = " ".join([
        _button("Watch once", "watch_once_no_ai"),
        _button("Watch once with AI", "watch_once_ai"),
        _action_link("Open Watch", "/watch"),
    ])
    panels.append(_action_panel("Watch and scan", f"Latest watch status: {latest_watch_status}. Run a quick watch check to refresh recommendations and notifications.", watch_controls, "normal"))

    maintenance_controls = " ".join([
        _button("Maintenance scan", "maintenance_scan"),
        _action_link("Open recent activity", "/activity"),
    ])
    panels.append(_action_panel("Maintenance", "Run a no-AI maintenance scan for chores like pending tests, memory size, stale reports, and other thrilling chores.", maintenance_controls, "low"))

    if not recommendations:
        recommendations.append("No urgent action found. Run a watch check or plan a session.")

    rec_html = _small_list([_safe(item) for item in recommendations])
    command_cheatsheet = """
<pre>Useful matching terminal commands:
python conscious_agent/main.py --diagnostics
python conscious_agent/main.py --watch-once --no-ai-watch
python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop
python conscious_agent/main.py --approval-inbox
python conscious_agent/main.py --plan-session --no-ai-session</pre>
"""
    content = (
        _card("Recommended Next Actions", rec_html)
        + "<div class='grid'>" + "".join(panels) + "</div>"
        + _card("Terminal equivalents", command_cheatsheet)
    )
    return _layout("/actions", content)




def _chat_action_card(action: dict[str, Any] | None) -> str:
    if not action:
        return "<p class='muted'>No action was proposed.</p>"
    action_id = action.get("id", "")
    mode = action.get("execution_mode", "")
    status = action.get("status", "")
    controls = ""
    if action_id and mode in {"direct_command", "direct_function", "approval"} and status in {"proposed", "approval_required", "failed"}:
        controls = " ".join([
            _button("Dry-run action", "chat_action_execute", chat_action_id=action_id, dry_run="true"),
            _button("Execute action", "chat_action_execute", chat_action_id=action_id),
            _detail_link("chat_action", action_id, "Details"),
        ])
    elif action_id:
        controls = _detail_link("chat_action", action_id, "Details")
    return (
        "<div class='action-card'>"
        f"<p><span class='badge'>{_safe(status)}</span> <span class='badge'>{_safe(mode)}</span> <span class='badge'>risk: {_safe(action.get('risk_level',''))}</span></p>"
        f"<h3>{_safe(action.get('title','Proposed action'))}</h3>"
        f"<p>{_safe(action.get('summary',''))}</p>"
        f"<p class='muted'>{_safe(action.get('explanation',''))}</p>"
        f"<pre>{_safe(action.get('command') or action.get('approval_command') or action.get('function_name') or '[no direct command]')}</pre>"
        f"<div>{controls}</div>"
        "</div>"
    )


def render_chat_console() -> str:
    turns = list_dashboard_chat_turns()
    latest = turns[0] if turns else None
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_chat_send'>
<label>Message Marcus → Eidolon
<textarea name='message' rows='4' placeholder='Check what needs attention, review conscious_agent/memory.py, suggest improvement for conscious_agent/local_brain.py...'></textarea></label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI conversational response</label>
<button type='submit'>Send + Propose Safe Action</button>
</form>
"""

    latest_html = "<p class='muted'>No dashboard chat turns yet.</p>"
    if latest:
        latest_html = (
            f"<p><span class='badge'>{_safe(latest.get('created_at',''))}</span> {_detail_link('dashboard_chat', latest.get('id',''), 'Open full turn')}</p>"
            f"<h3>Marcus</h3>{_text_block(latest.get('user_message',''))}"
            f"<h3>Eidolon</h3>{_text_block(latest.get('eidolon_response',''))}"
            f"<h3>Safe action card</h3>{_chat_action_card(latest.get('action'))}"
        )

    rows = []
    for turn in turns[:50]:
        turn_id = turn.get('id', '')
        action = turn.get('action') or {}
        action_id = turn.get('action_id', '')
        request = turn.get('user_message', '')
        action_link = _detail_link('chat_action', action_id, 'Action') if action_id else "<span class='muted'>[none]</span>"
        rows.append(
            f"<tr><td>{_safe(turn.get('created_at',''))}</td>"
            f"<td>{_detail_link('dashboard_chat', turn_id, request[:90] or turn_id)}</td>"
            f"<td>{_safe(action.get('intent','[none]'))}</td>"
            f"<td><span class='badge'>{_safe(action.get('status',''))}</span></td>"
            f"<td>{action_link}</td></tr>"
        )
    history = "<table><tr><th>Created</th><th>Message</th><th>Intent</th><th>Status</th><th>Action</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No chat history yet.</p>"
    examples = _text_block("""Try:
Check what needs attention
Run diagnostics
Show pending approvals
Plan the next session
Review conscious_agent/memory.py
Suggest improvement for conscious_agent/local_brain.py to improve Ollama error messages
Apply the latest patch
Rollback the latest patch""")
    content = (
        _card("Chat Console", form)
        + _card("Latest Conversation Turn", latest_html)
        + _card("Examples", examples)
        + _card("Recent Dashboard Chat Turns", history)
    )
    return _layout("/chat-console", content)



def _priority_options(selected: str = "medium") -> str:
    values = ["low", "medium", "high", "urgent"]
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _status_options(values: list[str], selected: str) -> str:
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _risk_options(selected: str = "low") -> str:
    values = ["low", "medium", "high"]
    return "".join(f"<option value='{_safe(value)}' {'selected' if value == selected else ''}>{_safe(value)}</option>" for value in values)


def _task_create_form() -> str:
    priority_options = _priority_options("medium")
    status_options = _status_options(["planned", "ready", "active", "blocked"], "planned")
    risk_options = _risk_options("low")
    goals = list_goals(include_cancelled=False)
    goal_options = "<option value=''>[none]</option>" + "".join(
        f"<option value='{_safe(goal.get('id',''))}'>{_safe(goal.get('title') or goal.get('id',''))}</option>"
        for goal in goals[:80]
    )
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_task'>
<label>Title <input name='title' required placeholder='Review dashboard form handling'></label>
<label>Description <textarea name='description' rows='4' placeholder='What should Eidolon do and why?'></textarea></label>
<label>Priority <select name='priority'>{priority_options}</select></label>
<label>Status <select name='status'>{status_options}</select></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label>Recommended command <input name='command' placeholder='python conscious_agent/main.py --diagnostics'></label>
<label>Next action <input name='next_action' placeholder='Run a dry-run first, inspect latest report, etc.'></label>
<label>Linked goal <select name='linked_goal'>{goal_options}</select></label>
<button type='submit'>Create Task</button>
</form>
"""


def _goal_create_form() -> str:
    priority_options = _priority_options("medium")
    status_options = _status_options(["planned", "active", "blocked", "completed"], "planned")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_goal'>
<label>Title <input name='title' required placeholder='Improve dashboard usability'></label>
<label>Description <textarea name='description' rows='4' placeholder='What outcome should Eidolon work toward?'></textarea></label>
<label>Priority <select name='priority'>{priority_options}</select></label>
<label>Status <select name='status'>{status_options}</select></label>
<label>Next action <input name='next_action' placeholder='Create the first task or run a session plan'></label>
<button type='submit'>Create Goal</button>
</form>
"""


def _patch_request_form() -> str:
    return """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_suggest_patch'>
<label>Target file inside active project <input name='target_file' required placeholder='conscious_agent/dashboard.py'></label>
<label>Requested change <textarea name='request' rows='5' required placeholder='Add a button that opens the create page from the overview.'></textarea></label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI to generate the patch proposal</label>
<button type='submit'>Create Patch Proposal</button>
</form>
<p class='muted'>This creates a proposed patch only. It does not apply the patch. The goblin may write suggestions, but it still cannot grab the wrench without approval.</p>
"""


def render_create() -> str:
    project = get_active_project() or {}
    intro = (
        f"<p>Active project: <b>{_safe(project.get('name','[none]'))}</b></p>"
        f"<p class='muted'>{_safe(project.get('path',''))}</p>"
        "<p>Use this page to create tasks, goals, and patch proposals from the browser. It still routes through the existing managers and safety rails, because apparently we learned something from all of human software history.</p>"
    )
    content = (
        _card("Create Dashboard Items", intro)
        + "<div class='grid'>"
        + _card("New Task", _task_create_form())
        + _card("New Goal", _goal_create_form())
        + _card("Patch Request", _patch_request_form())
        + "</div>"
    )
    return _layout("/create", content)

def render_chat_actions() -> str:
    actions = list_chat_actions(include_closed=True)
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='chat_action_propose'>
<label>Plain-English request
<input name='request' placeholder='Run diagnostics, check approvals, suggest improvement for conscious_agent/memory.py'></label>
<button type='submit'>Propose safe action</button>
</form>
"""
    rows = []
    for item in actions[:80]:
        item_id = item.get("id", "")
        status = item.get("status", "")
        intent = item.get("intent", "")
        mode = item.get("execution_mode", "")
        request = item.get("user_request", "")
        buttons = ""
        if mode in {"direct_command", "direct_function", "approval"} and status in {"proposed", "approval_required", "failed"}:
            buttons += _button("Dry-run", "chat_action_execute", chat_action_id=item_id, dry_run="true")
            buttons += _button("Execute", "chat_action_execute", chat_action_id=item_id)
        rows.append(
            f"<tr><td><span class='badge'>{_safe(status)}</span></td>"
            f"<td>{_safe(intent)}</td><td>{_safe(mode)}</td>"
            f"<td><b>{_detail_link('chat_action', item_id, request[:80] or item_id)}</b><br><span class='muted'>{_safe(item_id)}</span></td>"
            f"<td>{buttons} {_detail_link('chat_action', item_id, 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Status</th><th>Intent</th><th>Mode</th><th>Request</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No chat actions found.</p>"
    examples = _text_block("""Try:
run diagnostics
check what needs attention
show pending approvals
plan the next session
review conscious_agent/memory.py
suggest improvement for conscious_agent/local_brain.py to improve Ollama error messages
apply the latest patch
rollback the latest patch""")
    return _layout("/chat-actions", _card("Chat-to-Action", form) + _card("Examples", examples) + _card("Saved Chat Actions", table))

def render_tasks() -> str:
    tasks = list_tasks(include_cancelled=False)
    rows = []
    for task in tasks[:80]:
        task_id = task.get("id", "")
        title = task.get("title", "")
        status = task.get("status", "")
        priority = task.get("priority", "")
        cmd = task.get("recommended_command", "") or task.get("command", "")
        rows.append(f"<tr><td><span class='badge'>{_safe(status)}</span></td><td>{_safe(priority)}</td><td><b>{_detail_link('task', task_id, title)}</b><br><span class='muted'>{_safe(task_id)}</span></td><td>{_safe(cmd)}</td><td>{_detail_link('task', task_id, 'Details')}</td></tr>")
    table = "<table><tr><th>Status</th><th>Priority</th><th>Task</th><th>Command</th><th></th></tr>" + "".join(rows) + "</table>" if rows else "<p>No tasks found.</p>"
    next_item = next_task()
    detail = task_detail_text(next_item, full=True) if next_item else "No ready task."
    return _layout("/tasks", _card("Create Task", _task_create_form()) + _card("Next Ready Task", _text_block(detail)) + _card("Task Queue", table))


def _work_status_options(selected: str = "pending") -> str:
    return _status_options(["pending", "active", "blocked", "done", "failed", "cancelled"], selected)


def _work_item_create_form() -> str:
    risk_options = _risk_options("low")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_add_work_item'>
<label>Title <input name='title' required placeholder='Review conscious_agent/dashboard.py'></label>
<label>Description <textarea name='description' rows='4' placeholder='Describe the task. Include a target file, command:, or metadata-style hint when useful.'></textarea></label>
<label>Project ID <input name='project_id' value='eidolon' placeholder='eidolon'></label>
<label>Priority <input name='priority' type='number' min='1' max='10' value='5'></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label><input type='checkbox' name='requires_approval' value='true'> Requires approval</label>
<button type='submit'>Create Task</button>
</form>
<p class='muted'>Tasks are the canonical work records. Low-risk tasks can be dry-run or executed through the conservative task work executor. Medium/high-risk tasks stay approval-gated, because the machine does not get a tiny crown.</p>
"""


def _patch_work_item_create_form() -> str:
    risk_options = _risk_options("low")
    return f"""
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='dashboard_queue_patch'>
<label>Target file <input name='target_file' required placeholder='conscious_agent/dashboard.py'></label>
<label>Patch request <textarea name='request' rows='4' required placeholder='Describe the change Eidolon should propose as a patch.'></textarea></label>
<label>Project ID <input name='project_id' value='eidolon' placeholder='eidolon'></label>
<label>Priority <input name='priority' type='number' min='1' max='10' value='7'></label>
<label>Risk <select name='risk'>{risk_options}</select></label>
<label><input type='checkbox' name='requires_approval' value='true'> Requires approval before patch generation</label>
<button type='submit'>Queue Patch Task</button>
</form>
<p class='muted'>This creates a task-backed item with <code>action_type=suggest_patch</code>. Executing it creates a proposed patch and links the patch back to the task. Documentation, meet accountability. Finally.</p>
"""



def _stage_pill(lifecycle: dict[str, Any]) -> str:
    stage = str(lifecycle.get("stage") or "unknown")
    label = str(lifecycle.get("stage_label") or stage)
    css = str(lifecycle.get("css_class") or f"stage-{stage.replace('_', '-')}")
    return f"<span class='stage-pill {_safe(css)}'>{_safe(label)}</span>"


def _task_lifecycle_for_work_item(item: Any) -> dict[str, Any]:
    task = get_task(getattr(item, "id", "")) if item else None
    if task:
        return derive_task_lifecycle(task)
    metadata = getattr(item, "metadata", {}) if item else {}
    return {
        "stage": "unknown",
        "stage_label": "Unknown",
        "css_class": "stage-unknown",
        "next_action": "Inspect the raw task/work record.",
        "approval_id": str((metadata or {}).get("approval_id") or "") if isinstance(metadata, dict) else "",
        "approval_status": str((metadata or {}).get("approval_status") or "") if isinstance(metadata, dict) else "",
        "patch_id": str((metadata or {}).get("patch_id") or "") if isinstance(metadata, dict) else "",
        "patch_status": str((metadata or {}).get("patch_status") or "") if isinstance(metadata, dict) else "",
    }


def _lifecycle_flow(stage: str) -> str:
    stages = [
        ("ready", "Ready"),
        ("approval_required", "Needs approval"),
        ("approval_pending", "Pending"),
        ("approved_ready", "Approved"),
        ("active", "Active"),
        ("done", "Done"),
    ]
    blocked = {"blocked", "approval_rejected", "approval_failed", "cancelled"}
    parts = []
    for key, label in stages:
        current = " current" if key == stage else ""
        parts.append(f"<span class='lifecycle-step{current}'>{_safe(label)}</span>")
    if stage in blocked:
        parts.append(f"<span class='lifecycle-step current'>{_safe(stage.replace('_', ' ').title())}</span>")
    return "<div class='lifecycle-strip'>" + "".join(parts) + "</div>"


def _lifecycle_summary_cards() -> str:
    summary = task_lifecycle_summary()
    counts = summary.get("counts", {})
    return (
        "<div class='grid'>"
        + _card("Open Tasks", f"<div class='kpi'>{_safe(summary.get('open', 0))}</div><p class='muted'>Total task records: {_safe(summary.get('total', 0))}</p>")
        + _card("Ready / Active", f"<div class='kpi'>{_safe(counts.get('ready', 0) + counts.get('active', 0))}</div><p class='muted'>Ready: {_safe(counts.get('ready', 0))} · Active: {_safe(counts.get('active', 0))}</p>")
        + _card("Approval Flow", f"<div class='kpi'>{_safe(counts.get('approval_required', 0) + counts.get('approval_pending', 0) + counts.get('approved_ready', 0))}</div><p class='muted'>Required: {_safe(counts.get('approval_required', 0))} · Pending: {_safe(counts.get('approval_pending', 0))} · Approved: {_safe(counts.get('approved_ready', 0))}</p>")
        + _card("Needs Attention", f"<div class='kpi'>{_safe(summary.get('needs_attention', 0))}</div><p class='muted'>Blocked/rejected/failed/approval waiting.</p>")
        + "</div>"
    )


def _lifecycle_legend() -> str:
    return (
        "<div class='toolbar'>"
        "<span class='stage-pill stage-ready'>Ready</span>"
        "<span class='stage-pill stage-approval-required'>Needs approval request</span>"
        "<span class='stage-pill stage-approval-pending'>Approval pending</span>"
        "<span class='stage-pill stage-approved-ready'>Approved, ready to run</span>"
        "<span class='stage-pill stage-active'>Active</span>"
        "<span class='stage-pill stage-blocked'>Blocked</span>"
        "<span class='stage-pill stage-done'>Done</span>"
        "</div>"
        "<p class='muted'>v5.7 derives lifecycle stages from canonical task status, risk, linked approvals, and patch metadata, then lets the dashboard filter and act on them. Same data, fewer riddles. Allegedly.</p>"
    )

def _work_item_controls(item_id: str, status: str) -> str:
    controls = []
    item = find_work_item(item_id)
    metadata = item.metadata if item and isinstance(item.metadata, dict) else {}
    lifecycle = _task_lifecycle_for_work_item(item)
    stage = str(lifecycle.get("stage") or "unknown")
    is_patch_item = str(metadata.get("action_type") or "").lower() == "suggest_patch" or bool(metadata.get("patch_target_file") or metadata.get("target_file"))
    approval_id = str(lifecycle.get("approval_id") or metadata.get("approval_id") or "").strip()

    if stage in {"ready", "active", "approved_ready", "patch_proposed"} or status == "pending":
        controls.append(_button("Dry-run", "work_queue_execute", work_item_id=item_id, dry_run="true", use_ai="true"))
    if stage in {"ready", "active", "approved_ready"} or status == "pending":
        controls.append(_button("Execute", "work_queue_execute", work_item_id=item_id, use_ai="true"))
    if is_patch_item and stage in {"ready", "active", "patch_proposed"}:
        controls.append(_button("Suggest Patch", "work_queue_suggest_patch", work_item_id=item_id, use_ai="true"))
    if stage in {"approval_required", "blocked", "approval_rejected", "approval_failed"}:
        controls.append(_button("Request Approval", "task_request_approval", work_item_id=item_id, use_ai="true"))
    if approval_id:
        controls.append(_detail_link("approval", approval_id, "Open Approval"))
    if status in {"pending", "active", "blocked", "failed"}:
        controls.append(_button("Mark done", "work_queue_done", work_item_id=item_id))
        controls.append(_button("Cancel", "work_queue_cancel", work_item_id=item_id))
    if status in {"pending", "active"}:
        controls.append(_button("Block", "work_queue_block", work_item_id=item_id, reason="Blocked from dashboard."))
    controls.append(_detail_link("work_item", item_id, "Details", full=True))
    return " ".join(controls)


def _work_item_patch_hint(item: Any) -> str:
    metadata = item.metadata if hasattr(item, "metadata") and isinstance(item.metadata, dict) else {}
    lifecycle = _task_lifecycle_for_work_item(item)
    patch_id = str(lifecycle.get("patch_id") or metadata.get("patch_id") or "").strip()
    target_file = str(lifecycle.get("target_file") or metadata.get("patch_target_file") or metadata.get("target_file") or "").strip()
    approval_id = str(lifecycle.get("approval_id") or metadata.get("approval_id") or "").strip()
    approval_status = str(lifecycle.get("approval_status") or metadata.get("approval_status") or "").strip()
    bits = []
    if target_file:
        bits.append(f"<span class='muted'>Patch target: {_safe(target_file)}</span>")
    if patch_id:
        bits.append(f"<span class='muted'>Patch: {_detail_link('patch', patch_id, patch_id)}</span>")
    if approval_id:
        label = f"{approval_id} ({approval_status or 'pending'})"
        bits.append(f"<span class='muted'>Approval: {_detail_link('approval', approval_id, label)}</span>")
    return "<br>" + "<br>".join(bits) if bits else ""


def _lifecycle_filter_controls(selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    summary = task_lifecycle_summary()
    filters = summary.get("filters", [])
    preferred = ["all", "open", "needs_attention", "ready_to_act", "ready", "approval_required", "approval_pending", "approved_ready", "blocked", "patch_proposed", "done", "cancelled"]
    by_key = {str(item.get("key")): item for item in filters if isinstance(item, dict)}
    chips = []
    for key in preferred:
        item = by_key.get(key) or {"key": key, "label": STAGE_FILTER_LABELS.get(key, key.replace("_", " ").title()), "count": 0}
        active = " active" if key == selected_stage else ""
        href = "/tasks-work" if key == "all" else f"/tasks-work?stage={_safe(key)}"
        chips.append(f"<a class='filter-chip{active}' href='{href}'>{_safe(item.get('label', key))} <span class='badge'>{_safe(item.get('count', 0))}</span></a>")
    return "<div class='toolbar'>" + "".join(chips) + "</div>"


def _batch_lifecycle_actions(selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    approval_count = len(list_task_lifecycles(stage_filter="approval_required", include_closed=False))
    ready_count = len(list_task_lifecycles(stage_filter="ready_to_act", include_closed=False))
    return f"""
<div class='toolbar'>
<form method='post' action='/action' class='inline'>
<input type='hidden' name='action' value='task_batch_request_approvals'>
<input type='hidden' name='stage' value='approval_required'>
<button type='submit'>Request approvals for approval-required tasks ({_safe(approval_count)})</button>
</form>
<form method='post' action='/action' class='inline'>
<input type='hidden' name='action' value='work_queue_execute_next'>
<input type='hidden' name='dry_run' value='true'>
<input type='hidden' name='use_ai' value='true'>
<button type='submit'>Dry-run next ready task ({_safe(ready_count)})</button>
</form>
<a class='filter-chip' href='/tasks-work?stage=approved_ready'>Show approved-ready tasks</a>
<a class='filter-chip' href='/tasks-work?stage=blocked'>Show blocked tasks</a>
</div>
<p class='muted'>v5.7 deliberately does not add an “execute all” button. That button is how dashboards become confession letters.</p>
"""


def _filter_work_items_by_lifecycle(items: list[Any], selected_stage: str = "all") -> list[Any]:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    if selected_stage == "all":
        return items
    return [item for item in items if lifecycle_stage_matches(_task_lifecycle_for_work_item(item), selected_stage)]


def _work_queue_table(items: list[Any], selected_stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(selected_stage)
    filtered_items = _filter_work_items_by_lifecycle(items, selected_stage)
    rows = []
    for item in filtered_items[:120]:
        approval = "approval" if item.requires_approval else "safe"
        lifecycle = _task_lifecycle_for_work_item(item)
        lifecycle_cell = (
            f"{_stage_pill(lifecycle)}"
            f"<br><span class='muted'>{_safe(lifecycle.get('next_action', ''))}</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{lifecycle_cell}</td>"
            f"<td><span class='badge'>{_safe(item.status)}</span></td>"
            f"<td>{_safe(item.priority)}</td>"
            f"<td><span class='badge'>{_safe(item.risk)}</span><br><span class='muted'>{_safe(approval)}</span></td>"
            f"<td><b>{_detail_link('work_item', item.id, item.title)}</b><br><span class='muted'>{_safe(item.id)}</span><br><span class='muted'>Project: {_safe(item.project_id)}</span>{_work_item_patch_hint(item)}</td>"
            f"<td>{_safe(item.description[:180])}{'...' if len(item.description) > 180 else ''}</td>"
            f"<td>{_work_item_controls(item.id, item.status)}</td>"
            "</tr>"
        )
    if not rows:
        label = STAGE_FILTER_LABELS.get(selected_stage, selected_stage.replace("_", " ").title())
        return f"<p class='muted'>No task-backed tasks found for filter: {_safe(label)}.</p>"
    caption = "" if selected_stage == "all" else f"<p class='muted'>Showing {_safe(len(filtered_items))} task(s) matching {_safe(STAGE_FILTER_LABELS.get(selected_stage, selected_stage))}.</p>"
    return caption + "<table><tr><th>Lifecycle</th><th>Status</th><th>Priority</th><th>Risk</th><th>Task / Work</th><th>Description</th><th>Actions</th></tr>" + "".join(rows) + "</table>"


def render_work_queue(stage: str = "all") -> str:
    selected_stage = normalize_lifecycle_stage_filter(stage)
    summary = summarize_queue()
    active_items = list_work_items(include_done=False)
    all_items = list_work_items(include_done=True)
    next_item = summary.get("next_item") or {}

    next_text = "No pending task-backed task found. Either victory or neglect. Hard to tell."
    next_controls = ""
    if next_item:
        next_obj = find_work_item(str(next_item.get("id", ""))) if next_item.get("id") else None
        next_text = format_work_item(next_obj, full=True) if next_obj else json.dumps(next_item, indent=2)
        next_controls = (
            _button("Dry-run next", "work_queue_execute_next", dry_run="true", use_ai="true")
            + _button("Execute next", "work_queue_execute_next", use_ai="true")
            + " "
            + _detail_link("work_item", str(next_item.get("id", "")), "Open next item", full=True)
        )

    summary_html = _lifecycle_summary_cards()

    consolidation_note = _card(
        "v5.7 Task Lifecycle Actions / Filters",
        "<p class='muted'>This page uses <code>task_queue.py</code> and <code>data/tasks.json</code> as the canonical store. "
        "v5.7 adds lifecycle filters, stage-aware task tables, and safe batch approval requests. Legacy <code>/work-queue</code> aliases still work, because compatibility is ugly but cheaper than tears.</p>"
        + _lifecycle_legend()
    )

    body = (
        consolidation_note
        + summary_html
        + _card("Lifecycle Filters", _lifecycle_filter_controls(selected_stage))
        + _card("Lifecycle Batch Actions", _batch_lifecycle_actions(selected_stage))
        + _card("Lifecycle Legend", _lifecycle_legend())
        + _card("Create Task", _work_item_create_form())
        + _card("Create Patch Task", _patch_work_item_create_form())
        + _card("Next Recommended Task", _text_block(next_text) + next_controls)
        + _card("Open Tasks / Work", _work_queue_table(active_items, selected_stage))
        + _card("All Tasks / Work", _work_queue_table(all_items, selected_stage))
    )
    return _layout("/tasks-work", body)


def _work_cycle_controls() -> str:
    return """
<form method='post' action='/action'>
<input type='hidden' name='action' value='work_cycle_run'>
<label>Project <input name='project_id' value='eidolon'></label>
<label>Max steps <input name='max_steps' type='number' min='1' max='10' value='1'></label>
<label><input type='checkbox' name='dry_run' value='true' checked> Dry run</label>
<label><input type='checkbox' name='use_ai' value='true' checked> Use local AI when a selected step needs it</label>
<label><input type='checkbox' name='seed_if_empty' value='true' checked> Seed queue if empty</label>
<label><input type='checkbox' name='auto_followups' value='true' checked> Auto-create patch follow-ups</label>
<label><input type='checkbox' name='approve_work_execution' value='true'> Allow approval-required work this run</label>
<button type='submit'>Run supervised work cycle</button>
</form>
<p class='muted'>Default mode is dry-run. Non-dry-run still uses the task work executor, patch proposal rules, command whitelist, and approval gates. So, disappointingly for chaos enthusiasts, this is not a permission slip for mayhem.</p>
"""


def render_work_cycle() -> str:
    cycles = list_work_cycles()
    latest = cycles[0] if cycles else None
    rows = []
    for cycle in cycles[:50]:
        cycle_id = str(cycle.get('id', ''))
        rows.append(
            "<tr>"
            f"<td><span class='badge'>{_safe('ok' if cycle.get('ok') else 'attention')}</span></td>"
            f"<td>{_safe(cycle.get('dry_run'))}</td>"
            f"<td><b>{_detail_link('work_cycle', cycle_id, cycle_id)}</b><br><span class='muted'>Project: {_safe(cycle.get('project_id',''))}</span></td>"
            f"<td>{_safe(cycle.get('steps_completed',0))}/{_safe(cycle.get('steps_requested',0))}</td>"
            f"<td>{_safe(cycle.get('stopped_reason',''))}</td>"
            "</tr>"
        )
    table = "<table><tr><th>Status</th><th>Dry Run</th><th>Cycle</th><th>Steps</th><th>Stopped</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>No work cycles found.</p>"
    latest_text = work_cycle_text(latest, full=False) if latest else "No supervised work cycles saved yet. The clipboard is empty. Horrifyingly peaceful."
    body = (
        _card("Run Supervised Work Cycle", _work_cycle_controls())
        + _card("Latest Work Cycle", _text_block(latest_text))
        + _card("Saved Work Cycles", table)
    )
    return _layout("/work-cycle", body)


def render_approvals() -> str:
    approvals = list_approvals(include_closed=True)
    rows = []
    for approval in approvals[:80]:
        approval_id = approval.get("id", "")
        status = approval.get("status", "")
        action_type = approval.get("type", approval.get("action_type", ""))
        summary = approval.get("summary", "")
        buttons = ""
        if status == "pending":
            buttons += _button("Dry-run", "approve", approval_id=approval_id, dry_run="true")
            buttons += _button("Approve", "approve", approval_id=approval_id)
            buttons += _button("Reject", "reject", approval_id=approval_id)
        rows.append(f"<tr><td><span class='badge'>{_safe(status)}</span></td><td>{_safe(action_type)}</td><td><b>{_detail_link('approval', approval_id, summary)}</b><br><span class='muted'>{_safe(approval_id)}</span></td><td>{buttons} {_detail_link('approval', approval_id, 'Details')}</td></tr>")
    table = "<table><tr><th>Status</th><th>Type</th><th>Approval</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No approvals found.</p>"
    latest = list_approvals(status="pending", include_closed=False)
    latest_text = approval_text(latest[0], full=True) if latest else "No pending approvals. A rare bureaucratic victory."
    return _layout("/approvals", _card("Latest Pending Approval", _text_block(latest_text)) + _card("Approval Inbox", table))


def render_notifications() -> str:
    notifications = list_notifications(include_dismissed=True)
    rows = []
    for note in notifications[:100]:
        note_id = note.get("id", "")
        status = note.get("status", "")
        severity = note.get("severity", "")
        title = note.get("title", "")
        command = note.get("recommended_command", "")
        buttons = ""
        if status == "unread":
            buttons += _button("Mark read", "notification_read", notification_id=note_id)
            buttons += _button("Dismiss", "notification_dismiss", notification_id=note_id)
        rows.append(
            f"<tr><td><span class='badge'>{_safe(status)}</span></td>"
            f"<td>{_safe(severity)}</td>"
            f"<td><b>{_detail_link('notification', note_id, title)}</b><br><span class='muted'>{_safe(note_id)}</span></td>"
            f"<td>{_safe(command)}</td><td>{buttons} {_detail_link('notification', note_id, 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Status</th><th>Severity</th><th>Notification</th><th>Recommended Command</th><th>Actions</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No notifications found.</p>"
    unread = list_notifications(status="unread", include_dismissed=False)
    latest_text = notification_text(unread[0], full=False) if unread else "No unread notifications. Suspiciously peaceful."
    actions = _button("Clear dismissed", "notifications_clear_dismissed")
    return _layout("/notifications", _card("Latest Unread Notification", _text_block(latest_text)) + _card("Notification Actions", actions) + _card("Notifications", table))


def _watch_loop_form() -> str:
    return """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='watch_loop'>
<label>Cycles <input name='cycles' value='2'></label>
<label>Interval seconds <input name='interval' value='5'></label>
<label><input type='checkbox' name='use_ai' value='true'> Use local AI summary</label>
<button type='submit'>Run bounded watch loop</button>
</form>
"""


def render_watch() -> str:
    reports = list_watch_reports()
    latest = reports[0] if reports else None
    latest_text = watch_report_text(latest, full=False, include_ai=True) if latest else "No watch reports yet. Run a check, because apparently even ghosts need status meetings."

    actions = "".join([
        _button("Run watch once", "watch_once_no_ai"),
        _button("Run watch once with AI", "watch_once_ai"),
    ])

    rows = []
    for report in reports[:40]:
        if report.get("type") == "background_watch_loop":
            kind = "loop"
            status = report.get("stopped_reason", "")
            detail = f"cycles={report.get('cycle_count', len(report.get('reports', [])))} / {report.get('cycles_requested')}"
        else:
            kind = "report"
            status = report.get("status", "")
            detail = f"recommendations={len(report.get('recommendations', []) or [])}"
        rows.append(
            f"<tr><td><span class='badge'>{_safe(kind)}</span></td>"
            f"<td>{_safe(status)}</td>"
            f"<td><b>{_detail_link('watch', report.get('id',''), report.get('id',''))}</b><br><span class='muted'>{_safe(report.get('created_at',''))}</span></td>"
            f"<td>{_safe(detail)}</td><td>{_detail_link('watch', report.get('id',''), 'Details')}</td></tr>"
        )
    table = "<table><tr><th>Type</th><th>Status</th><th>Report</th><th>Details</th><th></th></tr>" + "".join(rows) + "</table>" if rows else "<p>No watch reports found.</p>"

    return _layout(
        "/watch",
        _card("Watch Controls", actions)
        + _card("Bounded Watch Loop", _watch_loop_form())
        + _card("Latest Watch Report", _text_block(latest_text))
        + _card("Saved Watch Reports", table),
    )


def render_patches() -> str:
    patches = list_patch_proposals()
    rows = []
    for patch in patches[:80]:
        patch_id = str(patch.get('id', ''))
        task_id = str(patch.get('task_id') or patch.get('work_item_id') or '')
        linked = _detail_link('work_item', task_id, task_id) if task_id else "<span class='muted'>[none]</span>"
        controls = _button("Create Follow-ups", "patch_create_followups", patch_id=patch_id) if patch_id else ""
        rows.append(f"<tr><td><span class='badge'>{_safe(patch.get('status',''))}</span></td><td>{_safe(patch.get('risk_level',''))}</td><td><b>{_detail_link('patch', patch_id, patch.get('target_file',''))}</b><br><span class='muted'>{_safe(patch_id)}</span><br><span class='muted'>Task: {linked}</span></td><td>{_safe(patch.get('request',''))}<br>{_detail_link('patch', patch_id, 'Details')} {controls}</td></tr>")
    table = "<table><tr><th>Status</th><th>Risk</th><th>File</th><th>Request</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No patches found.</p>"
    latest = patches[0] if patches else None
    latest_text = patch_proposal_text(latest, include_full_content=False) if latest else "No patch proposals yet."
    return _layout("/patches", _card("Request Patch", _patch_request_form()) + _card("Latest Patch", _text_block(latest_text)) + _card("Patch Records", table))


def render_goals() -> str:
    goals = list_goals(include_cancelled=False)
    rows = []
    for goal in goals[:80]:
        rows.append(f"<tr><td><span class='badge'>{_safe(goal.get('status',''))}</span></td><td>{_safe(goal.get('priority',''))}</td><td><b>{_detail_link('goal', goal.get('id',''), goal.get('title',''))}</b><br><span class='muted'>{_safe(goal.get('id',''))}</span></td><td>{_safe(goal.get('next_action','') or (goal.get('next_actions') or [''])[0])}</td></tr>")
    table = "<table><tr><th>Status</th><th>Priority</th><th>Goal</th><th>Next Action</th></tr>" + "".join(rows) + "</table>" if rows else "<p>No goals found.</p>"
    return _layout("/goals", _card("Create Goal", _goal_create_form()) + _card("Structured Goals", table))


def render_diagnostics() -> str:
    reports = list_diagnostic_reports()
    latest = reports[0] if reports else None
    status = latest.get("overall_status", "[none]") if latest else "[none]"
    body = f"<p>Latest diagnostic status: <b>{_safe(status)}</b></p>" + _button("Run diagnostics", "run_diagnostics")
    if latest:
        body += " " + _detail_link('diagnostic', latest.get('id',''), 'Open latest diagnostic')
    if latest:
        body += _text_block(diagnostic_report_text(latest, include_full=False))
    return _layout("/diagnostics", _card("Diagnostics", body))


def render_settings() -> str:
    settings = load_settings()
    rows = "".join(f"<tr><td>{_safe(k)}</td><td>{_safe(v)}</td></tr>" for k, v in sorted(settings.items()))
    form = """
<form method='post' action='/action' class='stack'>
<input type='hidden' name='action' value='set_setting'>
<label>Setting key <input name='key' placeholder='local_model'></label>
<label>Value <input name='value' placeholder='qwen2.5:7b'></label>
<button type='submit'>Update setting</button>
</form>
"""
    health = settings_health()
    return _layout("/settings", _card("Settings", f"<table><tr><th>Key</th><th>Value</th></tr>{rows}</table>") + _card("Update Setting", form) + _card("Settings Health", _json_block(health)))



def render_api_info() -> str:
    body = """
<p>The dashboard exposes a local JSON API under <code>/api</code>. Current task/work controls use the task-centered <code>/api/tasks/...</code> routes. Older <code>/api/work-queue/...</code> routes remain compatibility aliases. Browser pages use <code>/api/status</code> for live refresh/polling. The standalone server can also run on its own with <code>--api-server</code>.</p>
<pre>GET  /api
GET  /api/status    # live dashboard status payload
GET  /api/diagnostics/latest
POST /api/diagnostics/run
GET  /api/watch/latest
POST /api/watch/run-once
POST /api/watch/run-loop
GET  /api/notifications
POST /api/notifications/latest-unread/read
POST /api/notifications/latest-unread/dismiss
GET  /api/approvals
POST /api/approvals/latest-pending/approve
POST /api/approvals/latest-pending/reject
POST /api/chat-actions
POST /api/chat-actions/latest/dry-run
POST /api/chat-actions/latest/execute
POST /api/dashboard-chat
GET  /api/dashboard-chat/latest
GET  /api/session-plans/latest
POST /api/session-plans/run
GET  /api/maintenance/latest
POST /api/maintenance/run
GET  /api/dev-loops/latest
POST /api/dev-loops/run
GET  /api/desktop/attention
GET  /api/setup/latest
POST /api/setup/run
GET  /api/tasks
GET  /api/tasks/summary
POST /api/tasks
POST /api/tasks/next/dry-run
POST /api/tasks/next/execute
POST /api/tasks/{id}/dry-run
POST /api/tasks/{id}/execute
POST /api/tasks/{id}/done
POST /api/tasks/{id}/block
POST /api/tasks/{id}/cancel
POST /api/tasks/patch-request
POST /api/tasks/{id}/suggest-patch
POST /api/patches/{id}/create-task-followups

Legacy aliases still supported:
GET  /api/work-queue
GET  /api/work-queue/summary
POST /api/work-queue
POST /api/work-queue/{id}/execute</pre>
<p class='muted'>The API calls existing safety, approval, and command gates. It is convenience plumbing, not a magical permission bypass. Tragic for chaos, nice for your files.</p>
<pre>curl http://127.0.0.1:8765/api/status
# Browser pages poll this route automatically when dashboard_live_refresh_enabled is true.
curl -X POST http://127.0.0.1:8765/api/diagnostics/run
curl -X POST http://127.0.0.1:8765/api/chat-actions -H "Content-Type: application/json" -d '{"message":"run diagnostics"}'
curl -X POST http://127.0.0.1:8765/api/chat-actions/latest/dry-run
curl -X POST http://127.0.0.1:8765/api/tasks -H "Content-Type: application/json" -d '{"title":"Test dashboard form task","status":"planned"}'
curl -X POST http://127.0.0.1:8765/api/goals -H "Content-Type: application/json" -d '{"title":"Test dashboard form goal","next_action":"Create a task"}'</pre>
"""
    return _layout("/api-info", _card("Local API", body))



def render_desktop_info() -> str:
    body = """
<p>The desktop companion is a tiny local Tkinter shell that talks to the dashboard-integrated API or the standalone API. It can launch local services, show live counts, show advisory desktop notifications, hide to a watcher window or optional real system tray, open dashboard pages, run read-only diagnostics/watch/maintenance/session planning/dev-loop dry-runs, handle notification status, and send dashboard-chat messages.</p>
<pre>python conscious_agent/main.py --desktop
python conscious_agent/main.py --desktop-status
python conscious_agent/main.py --desktop-tray-status
python conscious_agent/main.py --setup-check
python conscious_agent/main.py --onboarding</pre>
<p class='muted'>It does not bypass approvals, patch gates, rollback checks, or command safety. v4.5 desktop actions can mark/dismiss notifications, run read-only workflows through the local API, use optional pystray/Pillow tray controls when installed, run first-run setup checks, and launch the guided onboarding wizard. The shell is a steering wheel, not bolt cutters.</p>
""" + _text_block(desktop_status_text())
    return _layout("/desktop", _card("Desktop Companion", body))


def render_setup() -> str:
    reports = list_setup_reports()
    rows = []
    for report in reports[:20]:
        counts = report.get("counts") or {}
        rows.append(
            "<tr>"
            f"<td>{_detail_link('setup', str(report.get('id')))}</td>"
            f"<td>{_fmt(report.get('status'))}</td>"
            f"<td>{_fmt(counts.get('warning', 0))}</td>"
            f"<td>{_fmt(counts.get('error', 0))}</td>"
            f"<td>{_fmt(report.get('created_at'))}</td>"
            "</tr>"
        )
    table = "<p class='muted'>No setup reports saved yet.</p>"
    if rows:
        table = "<table><tr><th>ID</th><th>Status</th><th>Warnings</th><th>Errors</th><th>Created</th></tr>" + "".join(rows) + "</table>"
    body = f"""
<p>Run a first-run setup check for desktop startup, optional tray packages, Ollama, configured models, service ports, local-only host settings, and writable data files.</p>
<div class='action-card'>
{_button('Run setup check', 'run_setup_check')}
{_button('Run diagnostics too', 'run_diagnostics')}
</div>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --setup-check
python conscious_agent/main.py --setup-check --setup-full
python conscious_agent/main.py --show-setup-report latest --setup-full
python conscious_agent/main.py --desktop-status
python conscious_agent/main.py --desktop-tray-status</pre>
<h3>Saved setup reports</h3>
{table}
"""
    return _layout("/setup", _card("Startup / First-Run Setup", body))



def _onboarding_step_html(step: dict[str, Any]) -> str:
    commands = step.get("commands") or []
    links = step.get("links") or []
    suggestions = step.get("suggestions") or []
    command_html = ""
    if commands:
        command_html = "<h4>Commands</h4><pre>" + _safe("\n".join(commands)) + "</pre>"
    link_html = ""
    if links:
        link_html = "<h4>Links</h4><ul>" + "".join(
            f"<li><a href='{_safe(link.get('url', ''))}'>{_safe(link.get('label', link.get('url', '')))}</a></li>"
            for link in links
        ) + "</ul>"
    suggestion_html = ""
    if suggestions:
        suggestion_html = "<h4>Suggestions</h4>" + _small_list([_safe(item) for item in suggestions])
    return (
        "<div class='action-card'>"
        f"<h3>{_safe(step.get('title'))} <span class='badge'>{_safe(step.get('status'))}</span> <span class='badge'>{_safe(step.get('priority'))}</span></h3>"
        f"<p>{_safe(step.get('description'))}</p>"
        f"{suggestion_html}{command_html}{link_html}"
        "</div>"
    )


def render_onboarding() -> str:
    runs = list_onboarding_runs()
    latest = runs[0] if runs else None
    latest_body = "<p class='muted'>No onboarding run saved yet.</p>"
    if latest:
        next_step = latest.get("next_step") or {}
        steps_html = "".join(_onboarding_step_html(step) for step in latest.get("steps", [])[:12])
        next_html = ""
        if next_step:
            next_html = _card("Next Recommended Step", _onboarding_step_html(next_step))
        latest_body = f"""
<p><strong>Status:</strong> {_fmt(latest.get('status'))}</p>
<p><strong>Summary:</strong> {_safe(latest.get('summary'))}</p>
<p><strong>Setup report:</strong> {_detail_link('setup', str(latest.get('setup_report_id') or ''), str(latest.get('setup_report_id') or '[none]'))}</p>
<p>{_detail_link('onboarding', str(latest.get('id')), 'Open full onboarding detail', full=True)}</p>
{next_html}
<h3>Guided steps</h3>
{steps_html}
"""

    rows = []
    for run in runs[:20]:
        counts = run.get("counts") or {}
        rows.append(
            "<tr>"
            f"<td>{_detail_link('onboarding', str(run.get('id')))}</td>"
            f"<td>{_fmt(run.get('status'))}</td>"
            f"<td>{_fmt(counts.get('blocked', 0))}</td>"
            f"<td>{_fmt(counts.get('needs_action', 0))}</td>"
            f"<td>{_fmt(counts.get('optional', 0))}</td>"
            f"<td>{_fmt(run.get('created_at'))}</td>"
            "</tr>"
        )
    table = "<p class='muted'>No onboarding runs saved yet.</p>"
    if rows:
        table = "<table><tr><th>ID</th><th>Status</th><th>Blocked</th><th>Action</th><th>Optional</th><th>Created</th></tr>" + "".join(rows) + "</table>"

    body = f"""
<p>The onboarding wizard converts setup checks into a guided, ordered runbook. It recommends commands and links, but does not install packages, change settings, start services, approve actions, or edit files. Apparently the machine must ask before touching the sacred mess.</p>
<div class='action-card'>
{_button('Run onboarding wizard', 'run_onboarding')}
{_button('Run onboarding from latest setup', 'run_onboarding_latest_setup')}
{_button('Run setup check', 'run_setup_check')}
</div>
<h3>Useful commands</h3>
<pre>python conscious_agent/main.py --onboarding
python conscious_agent/main.py --onboarding --onboarding-use-latest-setup
python conscious_agent/main.py --show-onboarding-run latest --onboarding-full
python conscious_agent/main.py --list-onboarding-runs</pre>
"""
    return _layout("/onboarding", _card("Guided Onboarding Wizard", body) + _card("Latest Onboarding Run", latest_body) + _card("Saved Onboarding Runs", table))

def render_activity() -> str:
    scans = list_maintenance_scans()
    plans = list_session_plans()
    reports = list_test_reports()
    reviews = list_test_reviews()
    diagnostic_reports = list_diagnostic_reports()
    watch_reports = list_watch_reports()
    dev_cycles = list_dev_cycles()
    dev_loops = list_dev_loops()
    memory_summaries = list_memory_summaries()
    setup_reports = list_setup_reports()
    onboarding_runs = list_onboarding_runs()

    def _rows(items: list[dict[str, Any]], kind: str, label_key: str = "id", time_key: str = "created_at") -> str:
        rows = []
        for item in items[:25]:
            item_id = item.get("id", "")
            label = item.get(label_key) or item_id
            rows.append(
                f"<tr><td>{_detail_link(kind, item_id, label)}</td>"
                f"<td>{_safe(item.get(time_key, item.get('created_at','')))}</td>"
                f"<td>{_safe(item.get('status', item.get('overall_status', item.get('recommendation', ''))))}</td></tr>"
            )
        return "<table><tr><th>Item</th><th>Created</th><th>Status/Recommendation</th></tr>" + "".join(rows) + "</table>" if rows else "<p class='muted'>None found.</p>"

    chunks = []
    chunks.append(_card("Recent Maintenance Scans", _rows(scans, "maintenance")))
    chunks.append(_card("Recent Session Plans", _rows(plans, "session_plan")))
    chunks.append(_card("Recent Watch Reports", _rows(watch_reports, "watch")))
    chunks.append(_card("Recent Test Reports", _rows(reports, "test_report")))
    chunks.append(_card("Recent Test Reviews", _rows(reviews, "test_review", label_key="id")))
    chunks.append(_card("Recent Diagnostic Reports", _rows(diagnostic_reports, "diagnostic")))
    chunks.append(_card("Recent Dev Cycles", _rows(dev_cycles, "dev_cycle")))
    chunks.append(_card("Recent Dev Loops", _rows(dev_loops, "dev_loop")))
    chunks.append(_card("Recent Memory Summaries", _rows(memory_summaries, "memory_summary")))
    chunks.append(_card("Recent Setup Reports", _rows(setup_reports, "setup")))
    chunks.append(_card("Recent Onboarding Runs", _rows(onboarding_runs, "onboarding")))
    return _layout("/activity", "".join(chunks))


def _detail_card(kind: str, item_id: str, title: str, body: str, back_path: str, extra: str = "") -> str:
    return _layout(
        "/detail",
        _back_link(back_path) + _card(title, body) + extra,
    )


def render_detail(query: dict[str, list[str]]) -> str:
    kind = query.get("kind", [""])[0]
    item_id = query.get("id", ["latest"])[0]
    full = query.get("full", [""])[0] in {"1", "true", "yes"}

    if kind == "dashboard_chat":
        item = load_dashboard_chat_turn(item_id)
        body = _text_block(dashboard_chat_turn_text(item, full=True) if item else f"Dashboard chat turn not found: {item_id}")
        buttons = ""
        if item and item.get("action_id"):
            action_id = item.get("action_id")
            buttons = _card("Proposed Action Controls", _button("Dry-run action", "chat_action_execute", chat_action_id=action_id, dry_run="true") + _button("Execute action", "chat_action_execute", chat_action_id=action_id) + " " + _detail_link("chat_action", action_id, "Open action detail"))
        return _detail_card(kind, item_id, "Dashboard Chat Turn", body, "/chat-console", buttons)

    if kind == "chat_action":
        item = load_chat_action(item_id)
        body = _text_block(chat_action_text(item, full=True) if item else f"Chat action not found: {item_id}")
        buttons = ""
        if item and item.get("execution_mode") in {"direct_command", "direct_function", "approval"}:
            cid = item.get("id", item_id)
            buttons = _card("Chat Action Controls", _button("Dry-run", "chat_action_execute", chat_action_id=cid, dry_run="true") + _button("Execute", "chat_action_execute", chat_action_id=cid))
        return _detail_card(kind, item_id, "Chat Action Detail", body, "/chat-actions", buttons)

    if kind == "task":
        item = get_task(item_id)
        body = _text_block(task_detail_text(item, full=True) if item else f"Task not found: {item_id}")
        return _detail_card(kind, item_id, "Task Detail", body, "/tasks")

    if kind == "approval":
        item = get_approval(item_id)
        body = _text_block(approval_text(item, full=True) if item else f"Approval not found: {item_id}")
        buttons = ""
        if item and item.get("status") == "pending":
            approval_id = item.get("id", item_id)
            buttons = _card("Approval Actions", _button("Dry-run approval", "approve", approval_id=approval_id, dry_run="true") + _button("Approve", "approve", approval_id=approval_id) + _button("Reject", "reject", approval_id=approval_id))
        return _detail_card(kind, item_id, "Approval Detail", body, "/approvals", buttons)

    if kind == "notification":
        item = load_notification(item_id)
        body = _text_block(notification_text(item, full=True) if item else f"Notification not found: {item_id}")
        buttons = ""
        if item and item.get("status") == "unread":
            note_id = item.get("id", item_id)
            buttons = _card("Notification Actions", _button("Mark read", "notification_read", notification_id=note_id) + _button("Dismiss", "notification_dismiss", notification_id=note_id))
        return _detail_card(kind, item_id, "Notification Detail", body, "/notifications", buttons)

    if kind == "work_cycle":
        item = load_work_cycle(item_id)
        body = _text_block(work_cycle_text(item, full=full) if item else f"Work cycle not found: {item_id}")
        return _detail_card(kind, item_id, "Work Cycle Detail", body, "/work-cycle")

    if kind == "patch":
        item = load_patch_proposal(item_id)
        body = _text_block(patch_proposal_text(item, include_full_content=True) if item else f"Patch not found: {item_id}")
        buttons = _card("Patch Queue Controls", _button("Create Follow-up Work Items", "patch_create_followups", patch_id=item_id)) if item else ""
        return _detail_card(kind, item_id, "Patch Detail", body, "/patches", buttons)

    if kind == "goal":
        item = get_goal(item_id)
        body = _text_block(_goal_text(item, full=True))
        return _detail_card(kind, item_id, "Goal Detail", body, "/goals")

    if kind == "diagnostic":
        item = load_diagnostic_report(item_id)
        body = _text_block(diagnostic_report_text(item, include_full=True) if item else f"Diagnostic report not found: {item_id}")
        return _detail_card(kind, item_id, "Diagnostic Detail", body, "/diagnostics")

    if kind == "watch":
        item = load_watch_report(item_id)
        body = _text_block(watch_report_text(item, full=True, include_ai=True) if item else f"Watch report not found: {item_id}")
        return _detail_card(kind, item_id, "Watch Report Detail", body, "/watch")

    if kind == "session_plan":
        item = load_session_plan(item_id)
        body = _text_block(session_plan_text(item, include_ai=True, full=True) if item else f"Session plan not found: {item_id}")
        return _detail_card(kind, item_id, "Session Plan Detail", body, "/activity")

    if kind == "maintenance":
        item = load_maintenance_scan(item_id)
        body = _text_block(maintenance_scan_text(item, include_ai=True, full=True) if item else f"Maintenance scan not found: {item_id}")
        return _detail_card(kind, item_id, "Maintenance Scan Detail", body, "/activity")

    if kind == "test_report":
        item = load_test_report(item_id)
        body = _text_block(test_report_text(item, include_output=True) if item else f"Test report not found: {item_id}")
        return _detail_card(kind, item_id, "Test Report Detail", body, "/activity")

    if kind == "test_review":
        item = load_test_review(item_id)
        body = _text_block(test_review_text(item, include_ai=True) if item else f"Test review not found: {item_id}")
        return _detail_card(kind, item_id, "Test Review Detail", body, "/activity")

    if kind == "dev_cycle":
        item = get_dev_cycle(item_id)
        body = _text_block(dev_cycle_text(item, full=True) if item else f"Dev cycle not found: {item_id}")
        return _detail_card(kind, item_id, "Dev Cycle Detail", body, "/activity")

    if kind == "dev_loop":
        item = get_dev_loop(item_id)
        body = _text_block(dev_loop_text(item, full=True) if item else f"Dev loop not found: {item_id}")
        return _detail_card(kind, item_id, "Dev Loop Detail", body, "/activity")

    if kind == "memory_summary":
        item = load_memory_summary(item_id)
        body = _text_block(memory_summary_text(item, include_full=True) if item else f"Memory summary not found: {item_id}")
        return _detail_card(kind, item_id, "Memory Summary Detail", body, "/activity")

    if kind == "setup":
        item = load_setup_report(item_id)
        body = _text_block(setup_report_text(item, full=True) if item else f"Setup report not found: {item_id}")
        buttons = _card("Setup Actions", _button("Run setup check", "run_setup_check") + _button("Run onboarding", "run_onboarding") + _button("Run diagnostics", "run_diagnostics"))
        return _detail_card(kind, item_id, "Setup Report Detail", body, "/setup", buttons)

    if kind == "onboarding":
        item = load_onboarding_run(item_id)
        body = _text_block(onboarding_run_text(item, full=True) if item else f"Onboarding run not found: {item_id}")
        buttons = _card("Onboarding Actions", _button("Run onboarding wizard", "run_onboarding") + _button("Use latest setup", "run_onboarding_latest_setup") + _button("Run setup check", "run_setup_check"))
        return _detail_card(kind, item_id, "Onboarding Run Detail", body, "/onboarding", buttons)


    if kind == "work_item":
        item = find_work_item(item_id)
        body = _text_block(format_work_item(item, full=True) if item else f"Task not found: {item_id}")
        buttons = ""
        if item:
            lifecycle = _task_lifecycle_for_work_item(item)
            lifecycle_card = _card(
                "Lifecycle",
                _lifecycle_flow(str(lifecycle.get("stage") or "unknown"))
                + f"<p>{_stage_pill(lifecycle)}</p>"
                + _text_block(task_lifecycle_text(item.id, full=False))
            )
            approvals = _text_block(task_approvals_text(item.id, include_closed=True, full=False))
            buttons = lifecycle_card + _card("Task / Work Controls", _work_item_controls(item.id, item.status)) + _card("Linked Approvals", approvals)
        return _detail_card(kind, item_id, "Task Work Detail", body, "/tasks-work", buttons)

    return _layout("/detail", _card("Unknown detail type", f"<p>No detail renderer for <code>{_safe(kind)}</code>.</p>"))


def handle_action(form: dict[str, list[str]]) -> None:
    action = form.get("action", [""])[0]
    try:
        if action == "run_setup_check":
            report = create_setup_report(save=True)
            DashboardState.message = f"Setup report saved: {report.get('id')} ({report.get('status')})"
        elif action == "run_onboarding":
            run = build_onboarding_run(save=True, refresh_setup=True)
            DashboardState.message = f"Onboarding run saved: {run.get('id')} ({run.get('status')})"
        elif action == "run_onboarding_latest_setup":
            run = build_onboarding_run(save=True, refresh_setup=False)
            DashboardState.message = f"Onboarding run saved from latest setup: {run.get('id')} ({run.get('status')})"
        elif action == "run_diagnostics":
            report = build_diagnostic_report(include_full=False)
            save_diagnostic_report(report)
            DashboardState.message = f"Diagnostic report saved: {report.get('id')}"
        elif action == "maintenance_scan":
            result = run_maintenance_scan(use_ai=False)
            DashboardState.message = f"Maintenance scan saved: {result.scan.get('id')}"
        elif action == "plan_session":
            result = create_session_plan(use_ai=False)
            DashboardState.message = f"Session plan saved: {result.plan.get('id')}"
        elif action == "dev_loop_dry":
            loop = run_dev_loop(max_steps=3, dry_run=True, allow_approval_actions=False, apply_task_evaluation=False, use_ai=False)
            DashboardState.message = f"Dry-run dev loop saved: {loop.get('id')}"
        elif action == "dev_loop_safe":
            loop = run_dev_loop(max_steps=3, dry_run=False, allow_approval_actions=False, apply_task_evaluation=False, use_ai=False)
            DashboardState.message = f"Safe dev loop saved: {loop.get('id')} ({loop.get('stopped_reason')})"
        elif action == "watch_once_no_ai":
            result = run_watch_once(use_ai=False)
            DashboardState.message = f"Watch report saved: {result.report_id} ({result.status})"
        elif action == "watch_once_ai":
            result = run_watch_once(use_ai=True)
            DashboardState.message = f"Watch report saved: {result.report_id} ({result.status})"
        elif action == "watch_loop":
            cycles_raw = form.get("cycles", ["2"])[0]
            interval_raw = form.get("interval", ["5"])[0]
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            cycles = max(1, int(cycles_raw or 2))
            interval = max(1, int(interval_raw or 5))
            loop = run_watch_loop(cycles=cycles, interval_seconds=interval, use_ai=use_ai)
            DashboardState.message = f"Watch loop saved: {loop.get('id')} ({loop.get('stopped_reason')})"
        elif action == "approve":
            approval_id = form.get("approval_id", ["latest-pending"])[0]
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            result = approve_approval(approval_id, dry_run=dry_run)
            DashboardState.message = f"Approval result: {result.get('message') or result.get('status') or result.get('ok')}"
        elif action == "reject":
            approval_id = form.get("approval_id", ["latest-pending"])[0]
            result = reject_approval(approval_id, note="Rejected from dashboard.")
            DashboardState.message = f"Rejected approval: {result.get('id', approval_id)}"
        elif action == "notification_read":
            note_id = form.get("notification_id", ["latest-unread"])[0]
            result = update_notification_status(note_id, "read", note="Marked read from dashboard.")
            DashboardState.message = "Marked notification read." if result.get("ok") else str(result.get("error"))
        elif action == "notification_dismiss":
            note_id = form.get("notification_id", ["latest-unread"])[0]
            result = update_notification_status(note_id, "dismissed", note="Dismissed from dashboard.")
            DashboardState.message = "Dismissed notification." if result.get("ok") else str(result.get("error"))
        elif action == "notifications_clear_dismissed":
            count = clear_dismissed_notifications()
            DashboardState.message = f"Cleared {count} dismissed notification(s)."
        elif action == "dashboard_chat_send":
            message = form.get("message", [""])[0].strip()
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            turn = create_dashboard_chat_turn(message, use_ai=use_ai)
            DashboardState.message = f"Dashboard chat turn saved: {turn.get('id')}"
        elif action == "chat_action_propose":
            request = form.get("request", [""])[0].strip()
            item = propose_chat_action(request, save=True)
            DashboardState.message = f"Chat action saved: {item.get('id')}"
        elif action == "chat_action_execute":
            chat_action_id = form.get("chat_action_id", ["latest"])[0]
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            result = execute_chat_action(chat_action_id, dry_run=dry_run)
            DashboardState.message = result.message if result.ok else (result.error or result.message)
        elif action == "dashboard_add_task":
            result = add_task(
                title=form.get("title", [""])[0],
                description=form.get("description", [""])[0],
                priority=form.get("priority", ["medium"])[0],
                status=form.get("status", ["planned"])[0],
                command=form.get("command", [""])[0],
                next_action=form.get("next_action", [""])[0],
                linked_goal=form.get("linked_goal", [""])[0],
                risk=form.get("risk", ["low"])[0],
                source="dashboard_form",
            )
            DashboardState.message = result.message if result.ok else f"Task creation failed: {result.error}"
        elif action == "dashboard_add_goal":
            result = add_goal(
                title=form.get("title", [""])[0],
                description=form.get("description", [""])[0],
                priority=form.get("priority", ["medium"])[0],
                status=form.get("status", ["planned"])[0],
                next_action=form.get("next_action", [""])[0],
            )
            DashboardState.message = result.message if result.ok else f"Goal creation failed: {result.error}"
        elif action == "dashboard_suggest_patch":
            target_file = form.get("target_file", [""])[0].strip()
            request = form.get("request", [""])[0].strip()
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            result = suggest_patch(target_file, request, use_ai=use_ai)
            DashboardState.message = f"Patch proposal saved: {result.patch_id}" if result.ok else f"Patch suggestion failed: {result.error}"
        elif action == "dashboard_queue_patch":
            target_file = form.get("target_file", [""])[0].strip()
            request = form.get("request", [""])[0].strip()
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            priority = int(form.get("priority", ["7"])[0] or 7)
            risk = form.get("risk", ["low"])[0].strip() or "low"
            requires_raw = form.get("requires_approval", [""])[0]
            requires_approval = True if requires_raw else None
            item = create_patch_work_item(
                target_file=target_file,
                request=request,
                project_id=project_id,
                priority=priority,
                risk=risk,
                source="dashboard",
                requires_approval=requires_approval,
            )
            DashboardState.message = f"Patch task queued: {item.id}"
        elif action == "work_queue_suggest_patch":
            work_item_id = form.get("work_item_id", [""])[0]
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = suggest_patch_for_work_item(work_item_id, use_ai=use_ai, dry_run=False)
            DashboardState.message = result.message if result.ok else f"Patch-from-task failed: {result.error}"
        elif action == "patch_create_followups":
            patch_id = form.get("patch_id", [""])[0]
            result = create_patch_followup_items(patch_id)
            DashboardState.message = result.message if result.ok else f"Patch follow-up task creation failed: {result.error}"
        elif action == "dashboard_add_work_item":
            title = form.get("title", [""])[0].strip()
            description = form.get("description", [""])[0].strip()
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            priority = int(form.get("priority", ["5"])[0] or 5)
            risk = form.get("risk", ["low"])[0]
            requires_approval = form.get("requires_approval", [""])[0].lower() == "true"
            item = add_work_item(
                title=title,
                description=description,
                project_id=project_id,
                priority=priority,
                risk=risk,
                source="dashboard",
                requires_approval=requires_approval if requires_approval else None,
            )
            DashboardState.message = f"Task created: {item.id}"
        elif action == "work_queue_execute_next":
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = execute_next_task_work(dry_run=dry_run, use_ai=use_ai)
            DashboardState.message = task_work_execution_text(result, full=False)
        elif action == "work_queue_execute":
            item_id = form.get("work_item_id", [""])[0].strip()
            dry_run = form.get("dry_run", ["false"])[0].lower() == "true"
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = execute_task_work_item(item_id, dry_run=dry_run, use_ai=use_ai)
            DashboardState.message = task_work_execution_text(result, full=False)
        elif action == "task_request_approval":
            item_id = form.get("work_item_id", [""])[0].strip()
            use_ai = form.get("use_ai", ["true"])[0].lower() == "true"
            result = request_task_work_approval(item_id, use_ai=use_ai, force=True)
            DashboardState.message = result.message if result.ok else f"Approval request failed: {result.error}"
        elif action == "work_queue_done":
            item_id = form.get("work_item_id", [""])[0].strip()
            item = update_work_item(item_id, status="done", result="Marked done from dashboard.")
            DashboardState.message = f"Marked task done: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "work_queue_cancel":
            item_id = form.get("work_item_id", [""])[0].strip()
            item = update_work_item(item_id, status="cancelled", result="Cancelled from dashboard.")
            DashboardState.message = f"Cancelled task: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "work_queue_block":
            item_id = form.get("work_item_id", [""])[0].strip()
            reason = form.get("reason", ["Blocked from dashboard."])[0].strip() or "Blocked from dashboard."
            item = update_work_item(item_id, status="blocked", blocked_reason=reason)
            DashboardState.message = f"Blocked task: {item_id}" if item else f"Task not found: {item_id}"
        elif action == "task_batch_request_approvals":
            stage = form.get("stage", ["approval_required"])[0]
            rows = list_task_lifecycles(stage_filter=stage, include_closed=False)
            created = []
            failed = []
            for row in rows:
                task_id = str(row.get("task_id") or "").strip()
                if not task_id:
                    continue
                result = request_task_work_approval(task_id, use_ai=True, force=False)
                if result.ok:
                    created.append(result.approval_id or result.task_id)
                else:
                    failed.append(f"{task_id}: {result.error}")
            DashboardState.message = f"Requested approvals for {len(created)} task(s)."
            if failed:
                DashboardState.error = "Some approval requests failed: " + "; ".join(failed[:3])
        elif action == "work_cycle_run":
            project_id = form.get("project_id", ["eidolon"])[0].strip() or "eidolon"
            max_steps = int(form.get("max_steps", ["1"])[0] or 1)
            dry_run = form.get("dry_run", [""])[0].lower() == "true"
            use_ai = form.get("use_ai", [""])[0].lower() == "true"
            seed_if_empty = form.get("seed_if_empty", [""])[0].lower() == "true"
            auto_followups = form.get("auto_followups", [""])[0].lower() == "true"
            approve_work_execution = form.get("approve_work_execution", [""])[0].lower() == "true"
            result = run_supervised_work_cycle(
                project_id=project_id,
                max_steps=max_steps,
                dry_run=dry_run,
                use_ai=use_ai,
                approve_work_execution=approve_work_execution,
                seed_if_empty=seed_if_empty,
                auto_create_patch_followups=auto_followups,
            )
            DashboardState.message = work_cycle_text(result, full=False)
        elif action == "set_setting":
            key = form.get("key", [""])[0].strip()
            value = form.get("value", [""])[0].strip()
            set_setting(key, value)
            DashboardState.message = f"Updated setting {key}."
        else:
            DashboardState.error = f"Unknown dashboard action: {action}"
    except Exception as error:
        DashboardState.error = f"Action failed: {error}"


class EidolonDashboardHandler(BaseHTTPRequestHandler):
    server_version = "EidolonDashboard/5.7"

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

    def _send_html(self, html: str, status: int = 200) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str = "/") -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True, "methods": ["GET", "POST", "OPTIONS"]})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api"):
            status, payload = dispatch_api("GET", path, query=parse_qs(parsed.query))
            self._send_json(payload, status=status)
            return
        try:
            if path == "/":
                html = render_overview()
            elif path == "/actions":
                html = render_action_center()
            elif path == "/chat-console":
                html = render_chat_console()
            elif path == "/chat-actions":
                html = render_chat_actions()
            elif path == "/create":
                html = render_create()
            elif path == "/tasks":
                html = render_tasks()
            elif path in {"/work-queue", "/tasks-work"}:
                html = render_work_queue(stage=parse_qs(parsed.query).get("stage", ["all"])[0])
            elif path == "/work-cycle":
                html = render_work_cycle()
            elif path == "/approvals":
                html = render_approvals()
            elif path == "/notifications":
                html = render_notifications()
            elif path == "/watch":
                html = render_watch()
            elif path == "/patches":
                html = render_patches()
            elif path == "/goals":
                html = render_goals()
            elif path == "/diagnostics":
                html = render_diagnostics()
            elif path == "/settings":
                html = render_settings()
            elif path == "/api-info":
                html = render_api_info()
            elif path == "/desktop":
                html = render_desktop_info()
            elif path == "/setup":
                html = render_setup()
            elif path == "/onboarding":
                html = render_onboarding()
            elif path == "/activity":
                html = render_activity()
            elif path == "/detail":
                html = render_detail(parse_qs(parsed.query))
            else:
                html = _layout(path, _card("Not found", f"<p>No dashboard route for <code>{_safe(path)}</code>.</p>"))
                self._send_html(html, status=404)
                return
            self._send_html(html)
        except Exception:
            err = traceback.format_exc()
            self._send_html(_layout(path, _card("Dashboard error", _text_block(err))), status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        if parsed.path.startswith("/api"):
            try:
                body = parse_request_body(raw_body, self.headers.get("Content-Type", ""))
            except Exception as error:
                self._send_json({"ok": False, "error": str(error)}, status=400)
                return
            status, payload = dispatch_api("POST", parsed.path, query=parse_qs(parsed.query), body=body)
            self._send_json(payload, status=status)
            return
        if parsed.path != "/action":
            self._send_html(_layout(parsed.path, _card("Not found", "<p>Unknown action path.</p>")), status=404)
            return
        form = parse_qs(raw_body.decode("utf-8"))
        handle_action(form)
        referer = self.headers.get("Referer", "/")
        target = urlparse(referer).path or "/"
        self._redirect(target)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the terminal readable. Humans panic when logs look like a raccoon ran across the keyboard.
        return


def run_dashboard(host: str | None = None, port: int | None = None) -> None:
    settings = load_settings()
    host = host or str(settings.get("dashboard_host", "127.0.0.1"))
    port = int(port or settings.get("dashboard_port", 8765))
    server = ThreadingHTTPServer((host, port), EidolonDashboardHandler)
    print(f"Eidolon dashboard running at http://{host}:{port}")
    print(f"Local API available at http://{host}:{port}/api")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
