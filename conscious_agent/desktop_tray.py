from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from settings_manager import get_setting, load_settings


DESKTOP_TRAY_VERSION = "1032.0"
@dataclass
class TrayAvailability:
    available: bool
    reason: str = ""
    pystray_version: str = "unknown"
    pillow_available: bool = False


def check_tray_availability() -> TrayAvailability:
    """Return whether optional real system tray support is available."""
    try:
        import pystray  # type: ignore
        pystray_version = str(getattr(pystray, "__version__", "unknown"))
    except Exception as error:
        return TrayAvailability(
            available=False,
            reason=f"pystray is not installed or could not be imported: {error}",
            pillow_available=False,
        )

    try:
        import PIL  # type: ignore
        from PIL import Image, ImageDraw  # noqa: F401  # type: ignore
        pillow_version = str(getattr(PIL, "__version__", "unknown"))
    except Exception as error:
        return TrayAvailability(
            available=False,
            reason=f"Pillow is not installed or could not be imported: {error}",
            pystray_version=pystray_version,
            pillow_available=False,
        )

    return TrayAvailability(
        available=True,
        reason=f"pystray {pystray_version}, Pillow {pillow_version}",
        pystray_version=pystray_version,
        pillow_available=True,
    )


def desktop_tray_settings() -> dict[str, Any]:
    settings = load_settings()
    keys = [
        "desktop_tray_enabled",
        "desktop_real_tray_enabled",
        "desktop_tray_show_on_start",
        "desktop_tray_minimize_on_close",
        "desktop_tray_fallback_to_watcher",
        "desktop_tray_status_in_tooltip",
    ]
    return {key: settings.get(key) for key in keys}


def desktop_tray_status_text() -> str:
    availability = check_tray_availability()
    settings = desktop_tray_settings()
    lines = [
        f"# Desktop Tray Integration v{DESKTOP_TRAY_VERSION}",
        "",
        "Real system tray support is optional. Eidolon uses pystray + Pillow when they are installed.",
        "If they are missing, the desktop shell falls back to the watcher window.",
        "",
        f"Available: {availability.available}",
        f"Details: {availability.reason or 'ready'}",
        "",
        "Settings:",
    ]
    for key, value in settings.items():
        lines.append(f"  {key}: {value}")
    lines.extend([
        "",
        "Install optional tray support:",
        "  python -m pip install pystray pillow",
        "",
        "Safety:",
        "  Tray menu actions call the same local API and desktop callbacks as the main shell.",
        "  They do not bypass approvals, patch gates, rollback checks, or command whitelist rules.",
    ])
    return "\n".join(lines)


def _create_icon_image() -> Any:
    from PIL import Image, ImageDraw  # type: ignore

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # A simple local-only generated icon. No external files, no font nonsense, no dependency confetti.
    draw.ellipse((5, 5, 59, 59), fill=(32, 42, 64, 255), outline=(132, 180, 255, 255), width=3)
    draw.ellipse((20, 18, 44, 42), fill=(105, 150, 235, 255))
    draw.ellipse((27, 25, 37, 35), fill=(235, 245, 255, 255))
    draw.rectangle((30, 42, 34, 55), fill=(132, 180, 255, 255))
    return image


class DesktopTrayController:
    """Optional pystray bridge for the desktop shell.

    The controller is intentionally tiny. Tkinter remains the main UI, and callbacks are
    scheduled back onto Tk by desktop_shell. The tray is just a convenience surface,
    because letting a tray icon bypass safety gates would be how the software gremlin wins.
    """

    def __init__(self, callbacks: dict[str, Callable[[], None]] | None = None) -> None:
        self.callbacks = callbacks or {}
        self.icon: Any | None = None
        self.available = check_tray_availability()
        self.running = False
        self.last_tooltip = "Eidolon Desktop Companion"

    def can_start(self) -> bool:
        return (
            bool(get_setting("desktop_tray_enabled", True))
            and bool(get_setting("desktop_real_tray_enabled", True))
            and self.available.available
        )

    def set_callbacks(self, callbacks: dict[str, Callable[[], None]]) -> None:
        self.callbacks = callbacks

    def _callback(self, name: str) -> None:
        callback = self.callbacks.get(name)
        if callback:
            callback()

    def start(self) -> tuple[bool, str]:
        if self.running:
            return True, "Tray is already running."
        if not self.can_start():
            return False, self.available.reason or "Tray support is disabled."

        try:
            import pystray  # type: ignore
        except Exception as error:
            return False, f"pystray import failed: {error}"

        menu = pystray.Menu(
            pystray.MenuItem("Restore Eidolon", lambda _icon, _item: self._callback("restore")),
            pystray.MenuItem("Open Dashboard", lambda _icon, _item: self._callback("open_dashboard")),
            pystray.MenuItem("Open Chat Console", lambda _icon, _item: self._callback("open_chat")),
            pystray.MenuItem("Open Onboarding", lambda _icon, _item: self._callback("open_onboarding")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run Diagnostics", lambda _icon, _item: self._callback("diagnostics")),
            pystray.MenuItem("Watch Once", lambda _icon, _item: self._callback("watch_once")),
            pystray.MenuItem("Plan Session", lambda _icon, _item: self._callback("session_plan")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Notifications", lambda _icon, _item: self._callback("open_notifications")),
            pystray.MenuItem("Open Approvals", lambda _icon, _item: self._callback("open_approvals")),
            pystray.MenuItem("Mark Latest Read", lambda _icon, _item: self._callback("mark_read")),
            pystray.MenuItem("Dismiss Latest", lambda _icon, _item: self._callback("dismiss")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Hide Window", lambda _icon, _item: self._callback("hide")),
            pystray.MenuItem("Exit", lambda _icon, _item: self._callback("exit")),
        )

        try:
            self.icon = pystray.Icon("Eidolon", _create_icon_image(), self.last_tooltip, menu)
            if hasattr(self.icon, "run_detached"):
                self.icon.run_detached()
            else:
                import threading
                threading.Thread(target=self.icon.run, daemon=True).start()
            self.running = True
            return True, "Real system tray icon started."
        except Exception as error:
            self.icon = None
            self.running = False
            return False, f"Tray start failed: {error}"

    def update_status(self, status: dict[str, Any]) -> None:
        if not self.running or self.icon is None:
            return
        if not bool(get_setting("desktop_tray_status_in_tooltip", True)):
            return
        counts = status.get("counts") or {}
        pending = counts.get("pending_approvals", 0)
        unread = counts.get("unread_notifications", 0)
        tasks = counts.get("tasks", 0)
        tooltip = f"Eidolon | tasks {tasks} | approvals {pending} | notes {unread}"
        self.last_tooltip = tooltip
        try:
            self.icon.title = tooltip
        except Exception:
            pass

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        self.icon = None
        self.running = False
