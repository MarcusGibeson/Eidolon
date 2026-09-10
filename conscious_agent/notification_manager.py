from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from memory import store_memory
from paths import DATA_DIR
from settings_manager import get_setting


NOTIFICATIONS_DIR = DATA_DIR / "notifications"
SEVERITY_RANK = {"critical": 0, "error": 1, "warning": 2, "info": 3}
STATUS_ORDER = {"unread": 0, "read": 1, "dismissed": 2}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_notification_id() -> str:
    return f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"


def _ensure_storage() -> None:
    NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    readme = NOTIFICATIONS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Notifications\n\n"
            "Saved Eidolon notifications. Notifications are advisory. They do not apply patches, "
            "approve actions, run commands, or bypass safety gates.\n",
            encoding="utf-8",
        )


def _notification_path(notification_id: str) -> Path:
    _ensure_storage()
    return NOTIFICATIONS_DIR / f"{notification_id}.json"


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_notification(notification: dict[str, Any]) -> Path:
    _ensure_storage()
    if not notification.get("id"):
        notification["id"] = _new_notification_id()
    path = _notification_path(str(notification["id"]))
    with path.open("w", encoding="utf-8") as file:
        json.dump(notification, file, indent=2)
    return path


def list_notifications(
    status: str = "",
    severity: str = "",
    include_dismissed: bool = True,
    *,
    create_if_missing: bool = True,
) -> list[dict[str, Any]]:
    if create_if_missing:
        _ensure_storage()
    elif not NOTIFICATIONS_DIR.exists():
        return []
    notifications: list[dict[str, Any]] = []
    for path in NOTIFICATIONS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if not data:
            continue
        if status and str(data.get("status", "")).lower() != status.lower():
            continue
        if severity and str(data.get("severity", "")).lower() != severity.lower():
            continue
        if not include_dismissed and data.get("status") == "dismissed":
            continue
        notifications.append(data)

    return sorted(
        notifications,
        key=lambda item: (
            STATUS_ORDER.get(str(item.get("status", "unread")), 9),
            SEVERITY_RANK.get(str(item.get("severity", "info")), 9),
            str(item.get("created_at", "")),
        ),
    )


def resolve_notification_id(notification_id: str) -> str:
    token = (notification_id or "latest-unread").strip()
    lowered = token.lower()
    notifications = list_notifications(include_dismissed=True)

    if lowered in {"latest", "last"}:
        by_time = sorted(notifications, key=lambda item: str(item.get("created_at", "")), reverse=True)
        return str(by_time[0].get("id", "")) if by_time else ""

    if lowered in {"latest-unread", "unread"}:
        unread = [note for note in notifications if note.get("status") == "unread"]
        unread = sorted(unread, key=lambda item: str(item.get("created_at", "")), reverse=True)
        return str(unread[0].get("id", "")) if unread else ""

    if lowered.startswith("latest-"):
        desired = lowered.replace("latest-", "", 1)
        matching = [
            note for note in notifications
            if str(note.get("status", "")).lower() == desired
            or str(note.get("severity", "")).lower() == desired
            or str(note.get("type", "")).lower() == desired
        ]
        matching = sorted(matching, key=lambda item: str(item.get("created_at", "")), reverse=True)
        return str(matching[0].get("id", "")) if matching else ""

    for note in notifications:
        if note.get("id") == token:
            return token
    return token


def load_notification(notification_id: str) -> dict[str, Any] | None:
    resolved = resolve_notification_id(notification_id)
    if not resolved:
        return None
    return _load_json_file(_notification_path(resolved))


def _find_existing_unread_by_dedupe(dedupe_key: str) -> dict[str, Any] | None:
    if not dedupe_key:
        return None
    for note in list_notifications(status="unread", include_dismissed=False):
        if note.get("dedupe_key") == dedupe_key:
            return note
    return None


def create_notification(
    type_: str,
    severity: str,
    title: str,
    message: str,
    recommended_command: str = "",
    source: str = "",
    related_id: str = "",
    metadata: dict[str, Any] | None = None,
    dedupe_key: str = "",
) -> dict[str, Any]:
    """
    Creates or updates an unread notification.

    If an unread notification has the same dedupe key, it is updated instead of
    creating another duplicate. This keeps watch mode from becoming a tiny JSON
    woodpecker pecking the same alert forever.
    """
    _ensure_storage()
    now = _now()
    severity = severity.lower().strip() or "info"
    type_ = type_.lower().strip() or "general"
    dedupe_key = dedupe_key or f"{source}:{type_}:{related_id}:{title}"

    existing = _find_existing_unread_by_dedupe(dedupe_key)
    if existing:
        existing["last_seen_at"] = now
        existing["seen_count"] = int(existing.get("seen_count", 1)) + 1
        existing["message"] = message
        existing["recommended_command"] = recommended_command
        existing["metadata"] = metadata or existing.get("metadata", {})
        save_notification(existing)
        return existing

    notification = {
        "id": _new_notification_id(),
        "type": type_,
        "severity": severity,
        "title": title,
        "message": message,
        "recommended_command": recommended_command,
        "status": "unread",
        "created_at": now,
        "last_seen_at": now,
        "seen_count": 1,
        "source": source,
        "related_id": related_id,
        "dedupe_key": dedupe_key,
        "metadata": metadata or {},
    }
    save_notification(notification)

    store_memory({
        "type": "notification_event",
        "content": f"Created notification {notification['id']}: {title}",
        "source": "notification_manager",
        "notification_id": notification["id"],
        "severity": severity,
        "notification_type": type_,
    })
    return notification


def _severity_from_priority(priority: str) -> str:
    priority = str(priority or "info").lower()
    if priority == "critical":
        return "critical"
    if priority == "high":
        return "warning"
    if priority == "medium":
        return "warning"
    return "info"


def create_notifications_from_watch_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Converts a watch report into saved notifications.
    """
    created: list[dict[str, Any]] = []
    if not bool(get_setting("notifications_enabled", True)):
        return created
    if not report or report.get("type") != "background_watch_report":
        return created

    report_id = str(report.get("id", ""))
    status = str(report.get("status", "")).lower()

    if status in {"error", "attention_needed"}:
        severity = "critical" if status == "error" else "warning"
        created.append(create_notification(
            type_="watch_attention",
            severity=severity,
            title="Watch mode needs attention",
            message=(
                f"Watch report {report_id} ended with status {status}. "
                f"Safe next command: {report.get('safe_next_command', '')}"
            ),
            recommended_command=str(report.get("safe_next_command", "")),
            source="watch_mode",
            related_id=report_id,
            metadata={"watch_report_id": report_id, "status": status},
            dedupe_key=f"watch_attention:{status}:{report.get('safe_next_command', '')}",
        ))

    min_priority = str(get_setting("notification_min_priority", "medium")).lower()
    allowed_priorities = {"critical", "high", "medium", "low"}
    min_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(min_priority, 2)

    for recommendation in (report.get("recommendations") or [])[:8]:
        priority = str(recommendation.get("priority", "info")).lower()
        priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 99)
        if priority not in allowed_priorities or priority_rank > min_rank:
            continue
        title = str(recommendation.get("title", "Watch recommendation"))
        command = str(recommendation.get("recommended_command", ""))
        category = str(recommendation.get("category", "watch"))
        created.append(create_notification(
            type_=category,
            severity=_severity_from_priority(priority),
            title=title,
            message=str(recommendation.get("reason", "")),
            recommended_command=command,
            source="watch_mode",
            related_id=report_id,
            metadata={"watch_report_id": report_id, "recommendation": recommendation},
            dedupe_key=f"watch_recommendation:{category}:{title}:{command}",
        ))

    return created


def notification_text(notification: dict[str, Any] | None, full: bool = False) -> str:
    if not notification:
        return "Notification not found."

    lines = [
        f"# Notification: {notification.get('id')}",
        f"Status: {str(notification.get('status', '')).upper()}",
        f"Severity: {str(notification.get('severity', '')).upper()}",
        f"Type: {notification.get('type')}",
        f"Title: {notification.get('title')}",
        f"Created: {notification.get('created_at')}",
        f"Last seen: {notification.get('last_seen_at')}",
        f"Seen count: {notification.get('seen_count', 1)}",
        "",
        str(notification.get("message", "")),
    ]
    if notification.get("recommended_command"):
        lines.extend(["", f"Recommended command: {notification.get('recommended_command')}"])
    if notification.get("source"):
        lines.append(f"Source: {notification.get('source')}")
    if notification.get("related_id"):
        lines.append(f"Related id: {notification.get('related_id')}")
    if full:
        lines.extend(["", "## Raw notification", json.dumps(notification, indent=2)])
    return "\n".join(lines)


def update_notification_status(notification_id: str, status: str, note: str = "") -> dict[str, Any]:
    notification = load_notification(notification_id)
    if not notification:
        return {"ok": False, "error": f"Notification not found: {notification_id}"}

    status = status.lower().strip()
    if status not in {"unread", "read", "dismissed"}:
        return {"ok": False, "error": f"Unsupported notification status: {status}"}

    notification["status"] = status
    notification["updated_at"] = _now()
    if note:
        notes = notification.setdefault("notes", [])
        notes.append({"created_at": _now(), "note": note})
    save_notification(notification)
    return {"ok": True, "notification": notification}


def clear_dismissed_notifications() -> int:
    count = 0
    for note in list_notifications(status="dismissed", include_dismissed=True):
        path = _notification_path(str(note.get("id", "")))
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count


def print_notifications(status: str = "unread", include_dismissed: bool = False) -> None:
    notifications = list_notifications(status=status, include_dismissed=include_dismissed)
    if not notifications:
        label = status or "any"
        print(f"No {label} notifications found.")
        return

    for note in notifications:
        print(
            f"{note.get('id')} | {note.get('status')} | {note.get('severity')} | "
            f"{note.get('type')} | {note.get('title')}"
        )
        if note.get("recommended_command"):
            print(f"  Command: {note.get('recommended_command')}")


def print_notification(notification_id: str, full: bool = False) -> None:
    notification = load_notification(notification_id)
    if not notification:
        print(f"Notification not found: {notification_id}")
        return
    print(notification_text(notification, full=full))


def print_mark_notification_read(notification_id: str, note: str = "") -> None:
    result = update_notification_status(notification_id, "read", note=note)
    if not result.get("ok"):
        print(result.get("error"))
        return
    note_obj = result.get("notification", {})
    print(f"Marked notification read: {note_obj.get('id')}")


def print_dismiss_notification(notification_id: str, note: str = "") -> None:
    result = update_notification_status(notification_id, "dismissed", note=note)
    if not result.get("ok"):
        print(result.get("error"))
        return
    note_obj = result.get("notification", {})
    print(f"Dismissed notification: {note_obj.get('id')}")


def print_clear_dismissed_notifications() -> None:
    count = clear_dismissed_notifications()
    print(f"Cleared {count} dismissed notification(s).")
