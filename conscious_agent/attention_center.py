from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from approval_manager import list_approvals
from chat_action_router import list_chat_actions
from conversation_action_portal import build_action_portal_state
from notification_manager import list_notifications
from project_manager import get_active_project
from provider_recovery_evidence import provider_resume_cue
from task_queue import list_tasks


ATTENTION_CENTER_VERSION = "v1080.7"
MAX_ATTENTION_ITEMS = 32
MAX_RECENT_RESULTS = 6

_SEVERITY_RANK = {"critical": 0, "error": 1, "warning": 2, "info": 3}
_KIND_RANK = {
    "approval": 0,
    "task": 1,
    "conversation": 2,
    "action": 3,
    "notification": 4,
    "provider": 2,
    "project": 5,
}
_ACTION_ATTENTION_STATES = {
    "approval_required",
    "approval_created",
    "awaiting_approval",
    "failed",
    "timed_out",
    "interrupted",
    "blocked",
    "cancelled",
}
_ACTION_TERMINAL_STATES = _ACTION_ATTENTION_STATES | {"executed", "completed"}
_OPEN_TASK_STATES = {"planned", "active", "blocked", "paused"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clip(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _severity_for_task(task: dict[str, Any]) -> str:
    status = str(task.get("status") or "planned").lower()
    priority = str(task.get("priority") or "medium").lower()
    if status == "blocked" or priority == "critical":
        return "error"
    if priority == "high" or status == "paused":
        return "warning"
    return "info"


def _severity_for_action(status: str) -> str:
    if status in {"failed", "timed_out", "interrupted"}:
        return "error"
    if status in {"blocked", "cancelled", "approval_required", "approval_created", "awaiting_approval"}:
        return "warning"
    return "info"


def _item(
    *,
    kind: str,
    item_id: str,
    status: str,
    severity: str,
    title: Any,
    summary: Any,
    created_at: Any = "",
    related_id: Any = "",
    href: str = "",
    requires_operator: bool = False,
    restored: bool = False,
) -> dict[str, Any]:
    return {
        "id": _clip(item_id, 120),
        "kind": kind,
        "status": _clip(status, 48),
        "severity": severity if severity in _SEVERITY_RANK else "info",
        "title": _clip(title, 120),
        "summary": _clip(summary, 220),
        "created_at": _clip(created_at, 64),
        "related_id": _clip(related_id, 120),
        "href": href if href.startswith("/") else "",
        "requires_operator": bool(requires_operator),
        "restored": bool(restored),
    }


def _notification_items(include_read: bool) -> list[dict[str, Any]]:
    rows = list_notifications(include_dismissed=False, create_if_missing=False)
    if not include_read:
        rows = [row for row in rows if str(row.get("status") or "unread") == "unread"]
    result = []
    for row in rows:
        status = str(row.get("status") or "unread").lower()
        severity = str(row.get("severity") or "info").lower()
        result.append(_item(
            kind="notification",
            item_id=str(row.get("id") or ""),
            status=status,
            severity=severity,
            title=row.get("title") or "Notification",
            summary=row.get("message") or "A local notification is available.",
            created_at=row.get("last_seen_at") or row.get("created_at") or "",
            related_id=row.get("related_id") or "",
            href="/notifications",
            requires_operator=status == "unread" and severity in {"critical", "error", "warning"},
        ))
    return result


def _approval_items() -> list[dict[str, Any]]:
    result = []
    for row in list_approvals(status="pending", include_closed=False, create_if_missing=False):
        result.append(_item(
            kind="approval",
            item_id=str(row.get("id") or ""),
            status="pending",
            severity="warning",
            title=row.get("summary") or "Approval waiting",
            summary=f"{str(row.get('action_type') or 'protected action').replace('_', ' ')} · risk {row.get('risk_level') or 'unknown'}",
            created_at=row.get("updated_at") or row.get("created_at") or "",
            related_id=row.get("object_id") or "",
            href="/approvals",
            requires_operator=True,
        ))
    return result


def _task_items() -> list[dict[str, Any]]:
    result = []
    for row in list_tasks(include_cancelled=False, create_if_missing=False):
        status = str(row.get("status") or "planned").lower()
        if status not in _OPEN_TASK_STATES:
            continue
        priority = str(row.get("priority") or "medium").lower()
        summary_parts = [status, f"priority {priority}"]
        if row.get("requires_approval"):
            summary_parts.append("approval required")
        blockers = row.get("blockers") if isinstance(row.get("blockers"), list) else []
        if blockers:
            summary_parts.append(_clip(blockers[-1], 100))
        result.append(_item(
            kind="task",
            item_id=str(row.get("id") or ""),
            status=status,
            severity=_severity_for_task(row),
            title=row.get("title") or "Untitled task",
            summary=" · ".join(summary_parts),
            created_at=row.get("updated_at") or row.get("created_at") or "",
            related_id=row.get("project") or "",
            href="/tasks",
            requires_operator=status == "blocked" or bool(row.get("requires_approval")),
        ))
    return result


def _project_items() -> list[dict[str, Any]]:
    project = get_active_project() or {}
    if not project:
        return []
    known_issues = project.get("known_issues") if isinstance(project.get("known_issues"), list) else []
    next_steps = project.get("next_steps") if isinstance(project.get("next_steps"), list) else []
    status = str(project.get("status") or "active").lower()
    severity = "warning" if known_issues or status not in {"active", "ready"} else "info"
    summary_parts = [f"{len(next_steps)} next step(s)", f"{len(known_issues)} known issue(s)"]
    if next_steps:
        summary_parts.append(f"Next: {_clip(next_steps[0], 120)}")
    elif known_issues:
        summary_parts.append(f"Issue: {_clip(known_issues[0], 120)}")
    return [_item(
        kind="project",
        item_id=f"project:{project.get('name') or 'active'}",
        status=status,
        severity=severity,
        title=f"Active project: {project.get('name') or 'Unknown'}",
        summary=" · ".join(summary_parts),
        created_at=project.get("last_worked_on") or "",
        related_id=project.get("name") or "",
        href="/",
        requires_operator=bool(known_issues),
    )]


def _action_items() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attention: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    for row in list_chat_actions(include_closed=True):
        status = str(row.get("status") or "proposed").lower()
        if status not in _ACTION_TERMINAL_STATES:
            continue
        portal = build_action_portal_state(
            row,
            row.get("result") if isinstance(row.get("result"), dict) else None,
        ) or {}
        public_status = str(portal.get("status") or status).lower()
        title = row.get("title") or "Supervised action"
        summary = portal.get("summary") or row.get("summary") or f"Action state: {public_status}"
        item = _item(
            kind="action",
            item_id=str(row.get("id") or ""),
            status=public_status,
            severity=_severity_for_action(public_status),
            title=title,
            summary=summary,
            created_at=row.get("updated_at") or row.get("executed_at") or row.get("created_at") or "",
            related_id=row.get("operation_id") or "",
            href="/chat-actions",
            requires_operator=public_status in {"approval_required", "approval_created", "awaiting_approval", "failed", "timed_out", "interrupted", "blocked"},
            restored=bool(portal.get("restored")),
        )
        if public_status in _ACTION_ATTENTION_STATES or status in _ACTION_ATTENTION_STATES:
            attention.append(item)
        if len(recent) < MAX_RECENT_RESULTS:
            recent.append(item)
    return attention, recent


def _provider_recovery_items() -> list[dict[str, Any]]:
    cue = provider_resume_cue()
    if not cue.get("visible"):
        return []
    state = str(cue.get("state") or "unknown")
    generation_available = bool(cue.get("generation_available"))
    recovery_proven = bool(cue.get("recovery_proven"))
    if recovery_proven:
        severity = "info"
        requires_operator = False
    elif state == "degraded" and generation_available:
        severity = "warning"
        requires_operator = False
    else:
        severity = "warning"
        requires_operator = True
    checked = str(cue.get("checked_at") or "time unavailable")
    return [_item(
        kind="provider",
        item_id="provider:latest-readiness",
        status=state,
        severity=severity,
        title=cue.get("label") or "Provider readiness",
        summary=f"{cue.get('detail') or ''} Last persisted check: {checked}.",
        created_at=cue.get("checked_at") or "",
        href="/local-model?return_to=chat#local-model-availability",
        requires_operator=requires_operator,
        restored=True,
    )]


def _conversation_items(rows: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result = []
    for row in rows or []:
        session_id = str(row.get("session_id") or row.get("id") or "")
        kind = str(row.get("kind") or "conversation_update")
        label = row.get("label") or row.get("status") or "Conversation update"
        result.append(_item(
            kind="conversation",
            item_id=f"conversation:{session_id}",
            status=kind,
            severity="warning" if kind in {"needs_recovery", "still_responding", "uncertain", "completion_uncertain"} else "info",
            title=row.get("title") or "Conversation update",
            summary=label,
            created_at=row.get("updated_at") or "",
            related_id=session_id,
            href="/chat-console",
            requires_operator=kind in {"needs_recovery", "uncertain", "completion_uncertain"},
            restored=True,
        ))
    return result


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return sorted(
        ordered,
        key=lambda row: (
            0 if row.get("requires_operator") else 1,
            _SEVERITY_RANK.get(str(row.get("severity") or "info"), 9),
            _KIND_RANK.get(str(row.get("kind") or ""), 9),
        ),
    )


def build_attention_center(
    *,
    conversation_updates: Iterable[dict[str, Any]] | None = None,
    include_read_notifications: bool = False,
    limit: int = MAX_ATTENTION_ITEMS,
) -> dict[str, Any]:
    """Build one read-only, redacted operator-attention snapshot.

    The builder does not acknowledge notifications, approve work, change tasks,
    select projects, execute actions, or persist a secondary private index.
    """
    bounded_limit = max(1, min(int(limit or MAX_ATTENTION_ITEMS), MAX_ATTENTION_ITEMS))
    notifications = _notification_items(include_read_notifications)
    approvals = _approval_items()
    tasks = _task_items()
    projects = _project_items()
    action_attention, recent_results = _action_items()
    conversations = _conversation_items(conversation_updates)
    provider_recovery = _provider_recovery_items()

    combined = _sort_items(approvals + tasks + conversations + provider_recovery + action_attention + notifications + projects)
    counts = {
        "total_attention": sum(1 for row in combined if row.get("requires_operator")),
        "unread_notifications": sum(1 for row in notifications if row.get("status") == "unread"),
        "pending_approvals": len(approvals),
        "open_tasks": len(tasks),
        "blocked_tasks": sum(1 for row in tasks if row.get("status") == "blocked"),
        "conversation_updates": len(conversations),
        "provider_recovery": len(provider_recovery),
        "action_attention": len(action_attention),
        "recent_action_results": len(recent_results),
        "project_items": len(projects),
    }
    return {
        "version": ATTENTION_CENTER_VERSION,
        "generated_at": _now(),
        "ok": True,
        "read_only": True,
        "redacted": True,
        "mutations_performed": False,
        "counts": counts,
        "items": combined[:bounded_limit],
        "recent_action_results": recent_results,
        "limits": {"items": bounded_limit, "recent_action_results": MAX_RECENT_RESULTS},
        "privacy": {
            "raw_command_output_included": False,
            "commands_included": False,
            "provider_payloads_included": False,
            "credentials_included": False,
            "runtime_receipts_included": False,
        },
    }


def attention_center_text(report: dict[str, Any] | None = None, *, full: bool = False) -> str:
    report = report or build_attention_center()
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    lines = [
        f"# Eidolon Attention Center {report.get('version', ATTENTION_CENTER_VERSION)}",
        "Mode: READ-ONLY, REDACTED",
        f"Needs operator attention: {counts.get('total_attention', 0)}",
        f"Unread notifications: {counts.get('unread_notifications', 0)}",
        f"Pending approvals: {counts.get('pending_approvals', 0)}",
        f"Open tasks: {counts.get('open_tasks', 0)}",
        f"Conversation updates: {counts.get('conversation_updates', 0)}",
        f"Provider recovery items: {counts.get('provider_recovery', 0)}",
        f"Action issues: {counts.get('action_attention', 0)}",
    ]
    items = report.get("items") if isinstance(report.get("items"), list) else []
    if not items:
        lines.append("No current attention items.")
    else:
        lines.append("Items:")
        for row in items[: MAX_ATTENTION_ITEMS if full else 12]:
            marker = "!" if row.get("requires_operator") else "-"
            lines.append(
                f"{marker} [{str(row.get('kind') or '').upper()} / {str(row.get('status') or '').upper()}] "
                f"{row.get('title')}: {row.get('summary')}"
            )
    lines.append("No notification, approval, task, project, conversation, or action state was changed.")
    return "\n".join(lines)


def print_attention_center(*, full: bool = False, json_output: bool = False) -> None:
    import json

    report = build_attention_center()
    if json_output:
        print(json.dumps(report, indent=2))
    else:
        print(attention_center_text(report, full=full))
