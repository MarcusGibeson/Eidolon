from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from settings_manager import get_setting, load_settings


DESKTOP_NOTIFIER_VERSION = "1032.0"
@dataclass
class DesktopAlert:
    title: str
    message: str
    severity: str
    signature: str
    related_notification_id: str = ""
    related_approval_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def desktop_notification_settings() -> dict[str, Any]:
    settings = load_settings()
    keys = [
        "desktop_notifications_enabled",
        "desktop_notify_on_unread",
        "desktop_notify_on_pending_approvals",
        "desktop_notify_on_startup",
        "desktop_popup_seconds",
        "desktop_bell_enabled",
        "desktop_close_to_watcher",
        "desktop_watcher_topmost",
        "desktop_api_poll_when_hidden",
    ]
    return {key: settings.get(key) for key in keys}


def desktop_notification_status_text() -> str:
    settings = desktop_notification_settings()
    lines = [
        "# Desktop Notifications + Watcher",
        "",
        "Desktop alerts are local Tkinter popups driven by /api/status counts.",
        "They do not approve actions, apply patches, rollback files, or run arbitrary commands.",
        "",
        "Settings:",
    ]
    for key, value in settings.items():
        lines.append(f"  {key}: {value}")
    lines.extend([
        "",
        "Watcher behavior:",
        "  The watcher window is the dependency-free fallback when optional real tray support is unavailable.",
        "  Real tray support lives in desktop_tray.py and requires pystray + Pillow.",
    ])
    return "\n".join(lines)


def build_desktop_alert(status: dict[str, Any], *, startup: bool = False) -> DesktopAlert | None:
    """
    Build a local desktop alert from an /api/status payload.

    This is intentionally advisory. It only inspects counts and latest IDs.
    The desktop shell decides whether to display the alert and how often.
    """
    if not bool(get_setting("desktop_notifications_enabled", True)):
        return None
    if startup and not bool(get_setting("desktop_notify_on_startup", True)):
        return None

    counts = status.get("counts") or {}
    latest = status.get("latest") or {}
    pending = _int(counts.get("pending_approvals"))
    unread = _int(counts.get("unread_notifications"))

    parts: list[str] = []
    severity = "info"

    approval_id = str(latest.get("pending_approval_id") or "")
    notification_id = str(latest.get("unread_notification_id") or "")

    if bool(get_setting("desktop_notify_on_pending_approvals", True)) and pending > 0:
        severity = "warning"
        noun = "approval" if pending == 1 else "approvals"
        parts.append(f"{pending} pending {noun}")

    if bool(get_setting("desktop_notify_on_unread", True)) and unread > 0:
        if severity == "info":
            severity = "info"
        noun = "notification" if unread == 1 else "notifications"
        parts.append(f"{unread} unread {noun}")

    if not parts:
        return None

    title = "Eidolon needs attention" if severity != "info" else "Eidolon update"
    message = "; ".join(parts) + "."
    signature = f"pending={pending}:{approval_id}|unread={unread}:{notification_id}"
    return DesktopAlert(
        title=title,
        message=message,
        severity=severity,
        signature=signature,
        related_notification_id=notification_id,
        related_approval_id=approval_id,
    )
