from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path
from typing import Any, Iterator

from desktop_notifier import (
    build_desktop_alert,
    desktop_notification_status_text,
)
from desktop_tray import (
    DesktopTrayController,
    desktop_tray_status_text,
)
from desktop_setup_helper import create_setup_report, setup_report_text
from desktop_onboarding_wizard import build_onboarding_run, onboarding_run_text
from settings_manager import get_setting, load_settings
from release_metadata import RUNTIME_VERSION
from release_candidate_identity import runtime_data_root
from desktop_daily_use import acquire_single_instance_lease
from desktop_chat_usability_contract import composer_key_action, should_focus_composer
from chat_time_labels import day_label, time_label


DESKTOP_VERSION = RUNTIME_VERSION
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = PROJECT_ROOT / "conscious_agent" / "main.py"


def _chat_timestamp(now=None) -> str:
    now = time.localtime() if now is None else now
    return time_label(now.tm_hour, now.tm_min)


class DesktopApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


class DesktopChatStreamTracker:
    """Content-free client timing and exactly-once stream identity tracker."""

    def __init__(self, started_clock: float | None = None) -> None:
        self.started_clock = time.monotonic() if started_clock is None else float(started_clock)
        self.accepted_clock: float | None = None
        self.first_visible_clock: float | None = None
        self.response_complete_clock: float | None = None
        self.completion_clock: float | None = None
        self.operation_id = ""
        self.session_id = ""
        self.done = False

    def observe(self, event: dict[str, Any], now: float | None = None) -> None:
        clock = time.monotonic() if now is None else float(now)
        event_name = str(event.get("event") or "")
        operation_id = str(event.get("operation_id") or "").strip()
        session_id = str(event.get("session_id") or "").strip()
        if operation_id:
            self.operation_id = operation_id
        if session_id:
            self.session_id = session_id
        if event_name in {"transport_accepted", "accepted"} and self.accepted_clock is None:
            self.accepted_clock = clock
        if event_name in {"response_complete", "conversation_complete"} and self.response_complete_clock is None:
            self.response_complete_clock = clock
        if event_name == "done":
            self.done = True
            if self.response_complete_clock is None:
                self.response_complete_clock = clock
            if self.completion_clock is None:
                self.completion_clock = clock

    def mark_visible(self, now: float | None = None) -> None:
        if self.first_visible_clock is None:
            self.first_visible_clock = time.monotonic() if now is None else float(now)

    def mark_complete(self, now: float | None = None) -> None:
        clock = time.monotonic() if now is None else float(now)
        if self.response_complete_clock is None:
            self.response_complete_clock = clock
        if self.completion_clock is None:
            self.completion_clock = clock
        self.done = True

    def timing_metrics(self) -> dict[str, int | bool | None]:
        def elapsed(clock: float | None) -> int | None:
            return None if clock is None else max(0, int((clock - self.started_clock) * 1000))

        return {
            "send_to_acceptance_ms": elapsed(self.accepted_clock),
            "send_to_first_visible_text_ms": elapsed(self.first_visible_clock),
            "send_to_response_complete_ms": elapsed(self.response_complete_clock),
            "total_completion_ms": elapsed(self.completion_clock),
            "content_free": True,
        }


def _host_port(setting_host: str, setting_port: str, default_host: str, default_port: int) -> tuple[str, int]:
    host = str(get_setting(setting_host, default_host))
    port = int(get_setting(setting_port, default_port))
    return host, port


def desktop_urls() -> dict[str, str]:
    dashboard_host, dashboard_port = _host_port("dashboard_host", "dashboard_port", "127.0.0.1", 8765)
    api_host, api_port = _host_port("api_host", "api_port", "127.0.0.1", 8766)
    # The native desktop container is intentionally loopback-only even when a
    # broader dashboard/API host is configured elsewhere. Remote/mobile input
    # remains a separate, explicit operator surface rather than an accidental
    # consequence of launching the desktop shell.
    if dashboard_host not in {"127.0.0.1", "localhost", "::1"}:
        dashboard_host = "127.0.0.1"
    if api_host not in {"127.0.0.1", "localhost", "::1"}:
        api_host = "127.0.0.1"
    dashboard_url_host = f"[{dashboard_host}]" if ":" in dashboard_host else dashboard_host
    api_url_host = f"[{api_host}]" if ":" in api_host else api_host
    return {
        "dashboard": f"http://{dashboard_url_host}:{dashboard_port}",
        "dashboard_api": f"http://{dashboard_url_host}:{dashboard_port}/api",
        "standalone_api": f"http://{api_url_host}:{api_port}/api",
        "chat_console": f"http://{dashboard_url_host}:{dashboard_port}/chat-console",
        "actions": f"http://{dashboard_url_host}:{dashboard_port}/actions",
        "notifications": f"http://{dashboard_url_host}:{dashboard_port}/notifications",
        "approvals": f"http://{dashboard_url_host}:{dashboard_port}/approvals",
        "api_info": f"http://{dashboard_url_host}:{dashboard_port}/api-info",
        "desktop": f"http://{dashboard_url_host}:{dashboard_port}/desktop",
        "setup": f"http://{dashboard_url_host}:{dashboard_port}/setup",
        "latest_setup": f"http://{dashboard_url_host}:{dashboard_port}/detail?kind=setup&id=latest",
        "onboarding": f"http://{dashboard_url_host}:{dashboard_port}/onboarding",
        "latest_onboarding": f"http://{dashboard_url_host}:{dashboard_port}/detail?kind=onboarding&id=latest",
        "latest_notification": f"http://{dashboard_url_host}:{dashboard_port}/detail?kind=notification&id=latest-unread",
        "latest_approval": f"http://{dashboard_url_host}:{dashboard_port}/detail?kind=approval&id=latest-pending",
    }


def desktop_status_text() -> str:
    settings = load_settings()
    urls = desktop_urls()
    lines = [
        f"# Eidolon Desktop Companion Shell v{DESKTOP_VERSION}",
        "",
        "Launch command:",
        "  python conscious_agent/main.py --desktop",
        "",
        "Useful local URLs:",
        f"  Dashboard:      {urls['dashboard']}",
        f"  Dashboard API:  {urls['dashboard_api']}",
        f"  Standalone API: {urls['standalone_api']}",
        f"  Chat Console:   {urls['chat_console']}",
        "",
        "Desktop settings:",
        f"  desktop_refresh_seconds: {settings.get('desktop_refresh_seconds')}",
        f"  desktop_prefer_dashboard_api: {settings.get('desktop_prefer_dashboard_api')}",
        f"  desktop_launch_dashboard_on_start: {settings.get('desktop_launch_dashboard_on_start')}",
        f"  desktop_notifications_enabled: {settings.get('desktop_notifications_enabled')}",
        f"  desktop_close_to_watcher: {settings.get('desktop_close_to_watcher')}",
        f"  desktop_quick_actions_enabled: {settings.get('desktop_quick_actions_enabled')}",
        f"  desktop_confirm_notification_dismiss: {settings.get('desktop_confirm_notification_dismiss')}",
        f"  desktop_confirm_clear_dismissed: {settings.get('desktop_confirm_clear_dismissed')}",
        f"  desktop_tray_enabled: {settings.get('desktop_tray_enabled')}",
        f"  desktop_real_tray_enabled: {settings.get('desktop_real_tray_enabled')}",
        f"  desktop_tray_show_on_start: {settings.get('desktop_tray_show_on_start')}",
        f"  desktop_tray_minimize_on_close: {settings.get('desktop_tray_minimize_on_close')}",
        f"  desktop_setup_check_on_start: {settings.get('desktop_setup_check_on_start')}",
        f"  desktop_setup_warn_if_attention: {settings.get('desktop_setup_warn_if_attention')}",
        f"  desktop_onboarding_check_on_start: {settings.get('desktop_onboarding_check_on_start')}",
        "",
        desktop_notification_status_text(),
        "",
        desktop_tray_status_text(),
        "",
        "Safety:",
        "  The desktop shell calls the local API and existing safety gates.",
        "  It does not apply patches, rollback files, or approve actions by itself.",
        "  Real tray actions are optional UI shortcuts; they use the same API gates as the desktop shell.",
        "  Onboarding is advisory and does not install packages or change settings by itself.",
    ]
    return "\n".join(lines)


class LocalApiClient:
    def __init__(self) -> None:
        self.urls = desktop_urls()
        self.active_base = ""
        self.last_error = ""

    def refresh_urls(self) -> None:
        self.urls = desktop_urls()

    def candidate_api_bases(self) -> list[str]:
        self.refresh_urls()
        prefer_dashboard = bool(get_setting("desktop_prefer_dashboard_api", True))
        dashboard_api = self.urls["dashboard_api"]
        standalone_api = self.urls["standalone_api"]
        if prefer_dashboard:
            return [dashboard_api, standalone_api]
        return [standalone_api, dashboard_api]

    def request(self, method: str, endpoint: str, data: dict[str, Any] | None = None, timeout: int = 5, base_url: str = "") -> dict[str, Any]:
        endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        bases = [base_url] if base_url else ([self.active_base] if self.active_base else []) + self.candidate_api_bases()
        seen: set[str] = set()
        errors: list[str] = []

        for base in bases:
            if not base or base in seen:
                continue
            seen.add(base)
            url = base.rstrip("/") + endpoint
            raw_body = None
            headers = {"Accept": "application/json"}
            if data is not None:
                raw_body = json.dumps(data).encode("utf-8")
                headers["Content-Type"] = "application/json"
            request = urllib.request.Request(url, data=raw_body, headers=headers, method=method.upper())
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    self.active_base = base.rstrip("/")
                    self.last_error = ""
                    return payload
            except urllib.error.HTTPError as error:
                try:
                    payload = json.loads(error.read().decode("utf-8"))
                except Exception:
                    payload = {"error": str(error)}
                self.active_base = base.rstrip("/")
                message = str(payload.get("error") or payload.get("message") or error)
                raise DesktopApiError(message, status=error.code, payload=payload) from error
            except Exception as error:
                errors.append(f"{base}: {error}")

        self.active_base = ""
        self.last_error = "; ".join(errors[-2:]) if errors else "API unavailable."
        raise DesktopApiError(self.last_error or "API unavailable.")

    def get(self, endpoint: str, timeout: int = 5) -> dict[str, Any]:
        return self.request("GET", endpoint, timeout=timeout)

    def post(self, endpoint: str, data: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
        return self.request("POST", endpoint, data=data or {}, timeout=timeout)

    def dashboard_request(self, method: str, endpoint: str, data: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
        """Call the dashboard API without failover.

        Conversation acceptance/reconciliation must stay on one authoritative
        endpoint. Falling through to a second server after a transport failure
        could turn uncertainty into a duplicate mutation.
        """
        self.refresh_urls()
        return self.request(method, endpoint, data=data, timeout=timeout, base_url=self.urls["dashboard_api"])

    def stream_dashboard_chat(self, data: dict[str, Any], timeout: int = 180) -> Iterator[dict[str, Any]]:
        """Yield one governed dashboard-chat SSE request with no automatic retry."""
        self.refresh_urls()
        base = self.urls["dashboard_api"].rstrip("/")
        url = base + "/dashboard-chat/stream"
        raw_body = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=raw_body,
            headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
            method="POST",
        )
        response = None
        operation_id = ""
        session_id = ""
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
            self.active_base = base
            self.last_error = ""
            operation_id = str(response.headers.get("X-Eidolon-Operation-Id") or "").strip()
            session_id = str(response.headers.get("X-Eidolon-Session-Id") or "").strip()
            yield {
                "event": "transport_accepted",
                "operation_id": operation_id,
                "session_id": session_id,
                "content_free": True,
            }

            event_name = "message"
            data_lines: list[str] = []
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    if data_lines:
                        payload_text = "\n".join(data_lines)
                        try:
                            payload = json.loads(payload_text)
                        except json.JSONDecodeError:
                            payload = {"message": "Malformed local stream event.", "raw_length": len(payload_text)}
                        if not isinstance(payload, dict):
                            payload = {"data": payload}
                        payload.setdefault("event", event_name or "message")
                        yield payload
                    event_name = "message"
                    data_lines = []
                    continue
                if line.startswith(":"):
                    continue
                field, _, value = line.partition(":")
                value = value[1:] if value.startswith(" ") else value
                if field == "event":
                    event_name = value.strip() or "message"
                elif field == "data":
                    data_lines.append(value)
            if data_lines:
                payload_text = "\n".join(data_lines)
                payload = json.loads(payload_text)
                if not isinstance(payload, dict):
                    payload = {"data": payload}
                payload.setdefault("event", event_name or "message")
                yield payload
        except urllib.error.HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8"))
            except Exception:
                payload = {"error": str(error)}
            message = str(payload.get("error") or payload.get("message") or error)
            raise DesktopApiError(message, status=error.code, payload=payload) from error
        except DesktopApiError:
            raise
        except Exception as error:
            raise DesktopApiError(
                f"Desktop chat stream ended: {error}",
                payload={
                    "operation_id": operation_id,
                    "session_id": session_id,
                    "accepted_transport": bool(operation_id),
                    "automatic_retry": False,
                },
            ) from error
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def dashboard_chat_operation_status(self, operation_id: str, timeout: int = 10) -> dict[str, Any]:
        query = urllib.parse.urlencode({"operation_id": str(operation_id or "")})
        return self.dashboard_request("GET", f"/dashboard-chat/operation?{query}", timeout=timeout)

    def cancel_dashboard_chat_operation(self, operation_id: str, timeout: int = 20) -> dict[str, Any]:
        return self.dashboard_request("POST", "/dashboard-chat/cancel", {"operation_id": str(operation_id or "")}, timeout=timeout)


def _desktop_chat_response(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    response = (
        data.get("eidolon_response")
        or data.get("response")
        or data.get("assistant_response")
        or payload.get("message")
        or "Chat turn saved."
    )
    return str(response)


def _desktop_stream_text(event: dict[str, Any]) -> tuple[str, str]:
    """Return (mode, text) for visible stream events without inventing content."""
    event_name = str(event.get("event") or "")
    if event_name == "delta":
        return "append", str(event.get("text") or "")
    if event_name == "replace":
        return "replace", str(event.get("text") or "")
    if event_name == "done":
        turn = event.get("turn") if isinstance(event.get("turn"), dict) else {}
        if turn.get("eidolon_response"):
            return "replace", str(turn.get("eidolon_response") or "")
        result = event.get("result") if isinstance(event.get("result"), dict) else {}
        final = result.get("display_message") or result.get("response")
        if final:
            return "replace", str(final)
    return "", ""


def _format_status_line(status: dict[str, Any]) -> str:
    project = status.get("active_project") or {}
    counts = status.get("counts") or {}
    return (
        f"Project: {project.get('name', '[none]')} | "
        f"Tasks: {counts.get('tasks', 0)} | "
        f"Approvals pending: {counts.get('pending_approvals', 0)} | "
        f"Unread notes: {counts.get('unread_notifications', 0)} | "
        f"Patches: {counts.get('patches', 0)} | "
        f"Watch reports: {counts.get('watch_reports', 0)} | "
        f"Session plans: {counts.get('session_plans', 0)}"
    )


def _attention_line(status: dict[str, Any]) -> str:
    counts = status.get("counts") or {}
    pending = counts.get("pending_approvals", 0)
    unread = counts.get("unread_notifications", 0)
    if pending or unread:
        return f"Attention: {pending} pending approvals, {unread} unread notifications."
    return "Attention: clear. The goblin is quiet for now."


def _spawn_main(args: list[str]) -> subprocess.Popen[Any]:
    command = [sys.executable, str(MAIN_FILE), *args]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _desktop_restart_command() -> list[str]:
    return [sys.executable, str(MAIN_FILE), "--desktop"]


def _desktop_window_state_path() -> Path:
    return runtime_data_root() / "desktop" / "window_state.json"


def _valid_desktop_geometry(value: object) -> str:
    geometry = str(value or "").strip()
    return geometry if re.fullmatch(r"\d+x\d+[+-]\d+[+-]\d+", geometry) else ""


def _load_desktop_geometry(path: Path | None = None) -> str:
    state_path = path or _desktop_window_state_path()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    return _valid_desktop_geometry(payload.get("geometry")) if isinstance(payload, dict) else ""


def _save_desktop_geometry(geometry: str, path: Path | None = None) -> bool:
    value = _valid_desktop_geometry(geometry)
    if not value:
        return False
    state_path = path or _desktop_window_state_path()
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = state_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps({"geometry": value}, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(state_path)
    except OSError:
        return False
    return True


def _spawn_desktop_replacement() -> subprocess.Popen[Any]:
    creationflags = 0
    if os.name == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    return subprocess.Popen(
        _desktop_restart_command(),
        cwd=str(PROJECT_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _stop_spawned_process(process: subprocess.Popen[Any], timeout_seconds: float = 5.0) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout_seconds)
    except Exception:
        pass


def run_desktop_shell() -> None:
    instance_lock = runtime_data_root() / "desktop" / "desktop_shell.pid"
    lease = acquire_single_instance_lease(instance_lock)
    if not lease.get("ok"):
        print("Eidolon Desktop is already running for this runtime profile.")
        print(f"Existing PID: {lease.get('existing_pid', 'unknown')}")
        return
    try:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext
    except Exception as error:
        print("Desktop shell unavailable: tkinter could not be imported.")
        print(f"Error: {error}")
        print()
        print(desktop_status_text())
        try: instance_lock.unlink()
        except FileNotFoundError: pass
        return

    client = LocalApiClient()
    spawned_processes: list[subprocess.Popen[Any]] = []
    desktop_closing = threading.Event()
    active_chat_lock = threading.Lock()
    active_chat: dict[str, Any] = {
        "operation_id": "",
        "session_id": "",
        "acceptance_key": "",
        "cancel_requested": False,
        "cancel_dispatched": False,
        "tracker": None,
    }
    last_status: dict[str, Any] = {}
    last_alert_signature = ""
    startup_alert_pending = True
    watcher_window: Any = None
    tray_controller = DesktopTrayController()

    try:
        root = tk.Tk()
    except Exception as error:
        print("Desktop shell unavailable: a desktop display could not be opened.")
        print(f"Error: {error}")
        print()
        print(desktop_status_text())
        try: instance_lock.unlink()
        except FileNotFoundError: pass
        return

    root.title(f"Eidolon Desktop v{DESKTOP_VERSION}")
    root.geometry(_load_desktop_geometry() or "1180x820")
    root.minsize(760, 600)

    colors = {
        "background": "#090d10",
        "surface": "#10171b",
        "surface_raised": "#172126",
        "border": "#26343b",
        "text": "#e7eef1",
        "muted": "#7f9098",
        "cyan": "#35c4d8",
        "amber": "#f2ae49",
        "green": "#58c77b",
        "warning": "#cf655f",
    }
    root.configure(background=colors["background"])

    status_var = tk.StringVar(value="API: checking...")
    api_var = tk.StringVar(value="Active API: [unknown]")
    counts_var = tk.StringVar(value="No status loaded yet.")
    attention_var = tk.StringVar(value="Attention: unknown.")
    chat_var = tk.StringVar(value="")

    def themed_button(parent, text: str, command, *, accent: str | None = None, width: int | None = None, compact: bool = False):
        active = accent or colors["cyan"]
        button = tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            background=colors["surface"],
            foreground=colors["muted"],
            activebackground=colors["surface_raised"],
            activeforeground=active,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=active,
            cursor="hand2",
            font=("Segoe UI", 10),
            padx=8 if compact else 10,
            pady=4 if compact else 7,
        )
        button.bind("<Enter>", lambda _event: button.configure(foreground=active, background=colors["surface_raised"]))
        button.bind("<Leave>", lambda _event: button.configure(foreground=colors["muted"], background=colors["surface"]))
        return button

    def theme_scrollbar(widget) -> None:
        scrollbar = getattr(widget, "vbar", None)
        if scrollbar is None:
            return
        try:
            scrollbar.configure(
                background=colors["surface_raised"],
                activebackground=colors["cyan"],
                troughcolor=colors["background"],
                highlightthickness=0,
                borderwidth=0,
                relief="flat",
            )
        except tk.TclError:
            pass

    header = tk.Frame(root, background=colors["background"], padx=18, pady=12)
    header.pack(fill="x")

    menu_button = themed_button(header, "\u2630", lambda: toggle_drawer("navigation"), width=3)
    menu_button.pack(side="left")

    identity = tk.Frame(header, background=colors["background"])
    identity.pack(side="left", padx=(18, 0))
    core = tk.Canvas(identity, width=34, height=34, background=colors["background"], highlightthickness=0)
    core.pack(side="left", padx=(0, 10))
    core.create_oval(3, 3, 31, 31, outline=colors["border"], width=2)
    core.create_oval(8, 8, 26, 26, outline=colors["cyan"], width=2)
    core.create_oval(13, 13, 21, 21, fill=colors["cyan"], outline=colors["cyan"])
    title_stack = tk.Frame(identity, background=colors["background"])
    title_stack.pack(side="left")
    tk.Label(title_stack, text="EIDOLON", background=colors["background"], foreground=colors["text"], font=("Segoe UI", 15, "bold")).pack(anchor="w")
    tk.Label(title_stack, text="Present", background=colors["background"], foreground=colors["green"], font=("Segoe UI", 9)).pack(anchor="w")

    settings_button = themed_button(header, "Settings", lambda: open_url("setup"), width=9)
    settings_button.pack(side="right", padx=(8, 0))
    activity_button = themed_button(header, "Activity", lambda: activity_panel.open(), accent=colors["amber"], width=9)
    activity_button.pack(side="right", padx=(8, 0))
    system_button = themed_button(header, "System", lambda: toggle_drawer("activity"), width=8)
    system_button.pack(side="right", padx=(8, 0))
    restart_button = themed_button(header, "Restart", lambda: restart_desktop(), accent=colors["cyan"], width=9)
    restart_button.pack(side="right")

    status_strip = tk.Frame(root, background=colors["surface"], highlightthickness=1, highlightbackground=colors["border"])
    status_strip.pack(fill="x", padx=18, pady=(0, 8))
    tk.Label(status_strip, textvariable=attention_var, background=colors["surface"], foreground=colors["muted"], font=("Segoe UI", 9), padx=12, pady=7, anchor="w").pack(side="left", fill="x", expand=True)
    tk.Label(status_strip, textvariable=status_var, background=colors["surface"], foreground=colors["cyan"], font=("Segoe UI", 9, "bold"), padx=12).pack(side="right")

    composer_host = tk.Frame(root, background=colors["background"])
    composer_host.pack(side="bottom", fill="x")
    workspace = tk.Frame(root, background=colors["background"])
    workspace.pack(fill="both", expand=True)
    from desktop_activity import ActivityPanel
    activity_panel = ActivityPanel(root, workspace, client, colors)

    navigation_drawer = tk.Frame(root, background=colors["surface"], highlightthickness=1, highlightbackground=colors["border"])
    tk.Label(navigation_drawer, text="Navigation", background=colors["surface"], foreground=colors["text"], font=("Segoe UI", 14, "bold"), padx=16, pady=14, anchor="w").pack(fill="x")
    button_frame = tk.Frame(navigation_drawer, background=colors["surface"], padx=12, pady=8)
    button_frame.pack(fill="both", expand=True)

    activity_drawer = tk.Frame(root, background=colors["surface"], highlightthickness=1, highlightbackground=colors["border"])
    tk.Label(activity_drawer, text="Activity and system", background=colors["surface"], foreground=colors["text"], font=("Segoe UI", 14, "bold"), padx=16, pady=14, anchor="w").pack(fill="x")
    status_frame = tk.Frame(activity_drawer, background=colors["surface"], padx=16, pady=10)
    status_frame.pack(fill="x")
    tk.Label(status_frame, textvariable=api_var, background=colors["surface"], foreground=colors["cyan"], anchor="w").pack(fill="x")
    tk.Label(status_frame, textvariable=counts_var, background=colors["surface"], foreground=colors["muted"], wraplength=350, justify="left", anchor="w").pack(fill="x", pady=(6, 0))
    tk.Label(activity_drawer, text="Recent output", background=colors["surface"], foreground=colors["text"], font=("Segoe UI", 10, "bold"), padx=16, pady=8, anchor="w").pack(fill="x")
    activity_output = scrolledtext.ScrolledText(
        activity_drawer,
        height=10,
        wrap="word",
        background=colors["background"],
        foreground=colors["muted"],
        insertbackground=colors["cyan"],
        relief="flat",
        borderwidth=0,
        font=("Consolas", 9),
        padx=10,
        pady=10,
    )
    activity_output.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    activity_output.configure(state="disabled")
    theme_scrollbar(activity_output)

    if bool(get_setting("desktop_quick_actions_enabled", True)):
        quick_frame = tk.Frame(activity_drawer, background=colors["surface"], padx=12, pady=8)
        quick_frame.pack(fill="x")

        notification_frame = tk.Frame(activity_drawer, background=colors["surface"], padx=12, pady=8)
        notification_frame.pack(fill="x")
    else:
        quick_frame = tk.Frame(activity_drawer, background=colors["surface"])
        notification_frame = tk.Frame(activity_drawer, background=colors["surface"])

    log_frame = tk.Frame(workspace, background=colors["background"], padx=48, pady=18)
    log_frame.pack(fill="both", expand=True)

    output = scrolledtext.ScrolledText(
        log_frame,
        height=13,
        wrap="word",
        background=colors["background"],
        foreground=colors["text"],
        insertbackground=colors["cyan"],
        selectbackground="#17444d",
        relief="flat",
        borderwidth=0,
        font=("Segoe UI", 11),
        padx=18,
        pady=18,
        spacing1=4,
        spacing3=12,
    )
    output.pack(fill="both", expand=True)
    output.tag_configure("eidolon", foreground=colors["text"], lmargin1=18, lmargin2=18, rmargin=90)
    output.tag_configure("marcus", foreground="#d5f5fa", lmargin1=110, lmargin2=110, rmargin=18, justify="right")
    output.tag_configure("system", foreground=colors["muted"], font=("Consolas", 9))
    output.tag_configure("date-divider", foreground=colors["muted"], justify="center", spacing1=12, spacing3=12)
    output.configure(state="disabled")
    theme_scrollbar(output)

    open_drawer: str | None = None

    def close_drawers() -> None:
        nonlocal open_drawer
        navigation_drawer.place_forget()
        activity_drawer.place_forget()
        open_drawer = None

    def toggle_drawer(name: str) -> None:
        nonlocal open_drawer
        if open_drawer == name:
            close_drawers()
            return
        close_drawers()
        if name == "navigation":
            navigation_drawer.place(x=0, y=64, width=330, relheight=1, height=-64)
            navigation_drawer.lift()
        else:
            activity_drawer.place(relx=1, x=-390, y=64, width=390, relheight=1, height=-64)
            activity_drawer.lift()
        open_drawer = name

    root.bind("<Escape>", lambda _event: close_drawers())

    last_chat_date = None

    def ensure_chat_date(now) -> None:
        nonlocal last_chat_date
        key = (now.tm_year, now.tm_mon, now.tm_mday)
        if key != last_chat_date:
            output.insert("end-1c", day_label(*key) + "\n", "date-divider")
            last_chat_date = key

    def log(message: str) -> None:
        now = time.localtime()
        timestamp = _chat_timestamp(now)
        tag = "eidolon" if message.startswith("Eidolon:") else "marcus" if message.startswith("Marcus:") else "system"
        if tag in {"eidolon", "marcus"}:
            output.configure(state="normal")
            ensure_chat_date(now)
            output.insert("end", f"{timestamp} {message}\n", tag)
            output.see("end")
            output.configure(state="disabled")
        else:
            activity_output.configure(state="normal")
            activity_output.insert("end", f"{timestamp} {message}\n")
            activity_output.see("end")
            activity_output.configure(state="disabled")

    stream_reply_open = False

    def begin_stream_reply() -> None:
        nonlocal stream_reply_open
        output.configure(state="normal")
        now = time.localtime()
        ensure_chat_date(now)
        output.insert("end-1c", f"{_chat_timestamp(now)} Eidolon: ", "eidolon")
        output.mark_set("desktop_stream_reply_start", "end-1c")
        output.mark_gravity("desktop_stream_reply_start", "left")
        output.see("end")
        output.configure(state="disabled")
        stream_reply_open = True

    def render_stream_reply(mode: str, text: str, tracker: DesktopChatStreamTracker) -> None:
        if not stream_reply_open or not text:
            return
        output.configure(state="normal")
        if mode == "replace":
            output.delete("desktop_stream_reply_start", "end-1c")
        output.insert("end-1c", text, "eidolon")
        output.see("end")
        output.configure(state="disabled")
        if text.strip():
            tracker.mark_visible()

    def finish_stream_reply() -> None:
        nonlocal stream_reply_open
        if not stream_reply_open:
            return
        output.configure(state="normal")
        output.insert("end-1c", "\n", "eidolon")
        output.see("end")
        output.configure(state="disabled")
        stream_reply_open = False

    def safe_ui(callback) -> None:
        if desktop_closing.is_set():
            return
        try:
            root.after(0, callback)
        except Exception:
            pass

    def pretty_payload(payload: dict[str, Any]) -> str:
        message = payload.get("message") or ""
        if message:
            return str(message)
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("id", "plan_id", "report_id", "scan_id", "loop_id"):
                if data.get(key):
                    return f"Saved: {data.get(key)}"
        return json.dumps(payload, indent=2, default=str)[:1600]

    def show_desktop_popup(title_text: str, message_text: str, *, severity: str = "info") -> None:
        if not bool(get_setting("desktop_notifications_enabled", True)):
            return
        try:
            if bool(get_setting("desktop_bell_enabled", True)):
                root.bell()
        except Exception:
            pass

        popup = tk.Toplevel(root)
        popup.title(title_text)
        popup.attributes("-topmost", True)
        popup.resizable(False, False)

        container = tk.Frame(popup, padx=14, pady=12)
        container.pack(fill="both", expand=True)
        tk.Label(container, text=title_text, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(container, text=message_text, wraplength=330, justify="left").pack(anchor="w", pady=(6, 10))

        button_row = tk.Frame(container)
        button_row.pack(fill="x")
        tk.Button(button_row, text="Open Notifications", command=lambda: open_url("notifications")).pack(side="left", padx=(0, 6))
        tk.Button(button_row, text="Open Approvals", command=lambda: open_url("approvals")).pack(side="left", padx=(0, 6))
        tk.Button(button_row, text="Mark Read", command=mark_latest_notification_read).pack(side="left", padx=(0, 6))
        tk.Button(button_row, text="Dismiss", command=dismiss_latest_notification).pack(side="left", padx=(0, 6))
        tk.Button(button_row, text="Close", command=popup.destroy).pack(side="right")

        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        x = max(20, screen_w - width - 30)
        y = max(20, screen_h - height - 70)
        popup.geometry(f"+{x}+{y}")

        seconds = int(get_setting("desktop_popup_seconds", 8) or 8)
        popup.after(max(2, seconds) * 1000, popup.destroy)
        log(f"Desktop alert: {title_text} - {message_text}")

    def maybe_show_status_alert(status: dict[str, Any]) -> None:
        nonlocal last_alert_signature, startup_alert_pending
        alert = build_desktop_alert(status, startup=startup_alert_pending)
        startup_alert_pending = False
        if not alert:
            return
        if alert.signature == last_alert_signature:
            return
        last_alert_signature = alert.signature
        show_desktop_popup(alert.title, alert.message, severity=alert.severity)

    def update_watcher() -> None:
        if watcher_window is None:
            return
        try:
            watcher_window.status_label.configure(text=counts_var.get())
            watcher_window.attention_label.configure(text=attention_var.get())
        except Exception:
            pass

    def refresh_status(background: bool = False) -> None:
        if background and root.state() == "withdrawn" and not bool(get_setting("desktop_api_poll_when_hidden", True)):
            return

        def work() -> None:
            nonlocal last_status
            try:
                payload = client.get("/status", timeout=4)
                data = payload.get("data") or {}
                last_status = data
                line = _format_status_line(data)
                attention = _attention_line(data)
                active_api = client.active_base or "[unknown]"
                root.after(0, lambda: status_var.set("API: online"))
                root.after(0, lambda: api_var.set(f"Active API: {active_api}"))
                root.after(0, lambda: counts_var.set(line))
                root.after(0, lambda: attention_var.set(attention))
                root.after(0, update_watcher)
                root.after(0, lambda: tray_controller.update_status(data))
                root.after(0, lambda: maybe_show_status_alert(data))
            except DesktopApiError as error:
                error_text = str(error)
                root.after(0, lambda: status_var.set("API: offline"))
                root.after(0, lambda: api_var.set("Active API: [none]"))
                root.after(0, lambda value=error_text: counts_var.set(value))
                root.after(0, lambda: attention_var.set("Attention: unknown because the API is offline."))
                root.after(0, update_watcher)
                if not background:
                    root.after(0, lambda value=error_text: log(f"Status check failed: {value}"))

        threading.Thread(target=work, daemon=True).start()

    def api_action(label: str, endpoint: str, body: dict[str, Any] | None = None, timeout: int = 45) -> None:
        def work() -> None:
            try:
                payload = client.post(endpoint, body or {}, timeout=timeout)
                root.after(0, lambda: log(f"{label}: {pretty_payload(payload)}"))
                root.after(0, refresh_status)
            except DesktopApiError as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"{label} failed: {value}"))

        log(f"Starting: {label}")
        threading.Thread(target=work, daemon=True).start()

    def api_get_action(label: str, endpoint: str, timeout: int = 15) -> None:
        def work() -> None:
            try:
                payload = client.get(endpoint, timeout=timeout)
                root.after(0, lambda: log(f"{label}: {pretty_payload(payload)}"))
                root.after(0, refresh_status)
            except DesktopApiError as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"{label} failed: {value}"))

        log(f"Fetching: {label}")
        threading.Thread(target=work, daemon=True).start()

    def log_unread_notifications() -> None:
        def work() -> None:
            try:
                payload = client.get("/notifications?status=unread&include_dismissed=false", timeout=10)
                notes = payload.get("data") or []
                if not notes:
                    root.after(0, lambda: log("Unread notifications: none. The tiny alarm bell is unemployed."))
                    return
                lines = [f"Unread notifications ({len(notes)}):"]
                for note in notes[:8]:
                    lines.append(
                        f"- {note.get('id')} | {note.get('severity')} | {note.get('title')}"
                    )
                    if note.get("recommended_command"):
                        lines.append(f"  command: {note.get('recommended_command')}")
                root.after(0, lambda: log("\n".join(lines)))
            except DesktopApiError as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"Unread notification fetch failed: {value}"))

        threading.Thread(target=work, daemon=True).start()

    def log_pending_approvals() -> None:
        def work() -> None:
            try:
                payload = client.get("/approvals?status=pending&include_closed=false", timeout=10)
                approvals = payload.get("data") or []
                if not approvals:
                    root.after(0, lambda: log("Pending approvals: none. The permission-slip desk is empty."))
                    return
                lines = [f"Pending approvals ({len(approvals)}):"]
                for approval in approvals[:8]:
                    lines.append(
                        f"- {approval.get('id')} | {approval.get('action_type') or approval.get('type')} | {approval.get('title') or approval.get('summary') or approval.get('reason', '')}"
                    )
                root.after(0, lambda: log("\n".join(lines)))
            except DesktopApiError as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"Pending approval fetch failed: {value}"))

        threading.Thread(target=work, daemon=True).start()

    def mark_latest_notification_read() -> None:
        api_action(
            "Mark latest unread notification read",
            "/notifications/latest-unread/read",
            {"note": "Marked read from desktop quick action."},
            timeout=20,
        )

    def dismiss_latest_notification() -> None:
        if bool(get_setting("desktop_confirm_notification_dismiss", True)):
            if not messagebox.askyesno("Dismiss notification", "Dismiss the latest unread notification?"):
                return
        api_action(
            "Dismiss latest unread notification",
            "/notifications/latest-unread/dismiss",
            {"note": "Dismissed from desktop quick action."},
            timeout=20,
        )

    def clear_dismissed_notifications_action() -> None:
        if bool(get_setting("desktop_confirm_clear_dismissed", True)):
            if not messagebox.askyesno("Clear dismissed notifications", "Delete all dismissed notification records?"):
                return
        api_action("Clear dismissed notifications", "/notifications/clear-dismissed", {}, timeout=20)

    def dry_run_latest_approval() -> None:
        api_action(
            "Dry-run latest pending approval",
            "/approvals/latest-pending/approve",
            {"dry_run": True},
            timeout=90,
        )

    def run_setup_check_action(show_full: bool = False) -> None:
        def work() -> None:
            try:
                report = create_setup_report(save=True)
                text = setup_report_text(report, full=show_full)
                root.after(0, lambda: log(text))
                root.after(0, refresh_status)
                if bool(get_setting("desktop_setup_warn_if_attention", True)) and report.get("status") != "ready":
                    root.after(0, lambda: show_desktop_popup("Setup needs attention", report.get("summary", "Setup check found issues."), severity="warning"))
            except Exception as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"Setup check failed: {value}"))

        log("Starting: setup check")
        threading.Thread(target=work, daemon=True).start()

    def run_onboarding_action(show_full: bool = False, refresh_setup: bool = True) -> None:
        def work() -> None:
            try:
                run = build_onboarding_run(save=True, refresh_setup=refresh_setup)
                text = onboarding_run_text(run, full=show_full)
                root.after(0, lambda: log(text))
                root.after(0, refresh_status)
                if run.get("status") in {"blocked", "needs_action"}:
                    root.after(0, lambda: show_desktop_popup("Onboarding needs action", run.get("summary", "Onboarding found setup steps."), severity="warning"))
            except Exception as error:
                error_text = str(error)
                root.after(0, lambda value=error_text: log(f"Onboarding wizard failed: {value}"))

        log("Starting: onboarding wizard")
        threading.Thread(target=work, daemon=True).start()

    def run_desktop_quick_action(action_id: str) -> None:
        if action_id == "diagnostics":
            api_action("Diagnostics", "/diagnostics/run", {"include_full": False}, timeout=60)
        elif action_id == "watch_once":
            api_action("Watch once", "/watch/run-once", {"use_ai": False}, timeout=90)
        elif action_id == "maintenance_scan":
            api_action("Maintenance scan", "/maintenance/run", {"use_ai": False}, timeout=90)
        elif action_id == "session_plan":
            api_action("Session plan", "/session-plans/run", {"use_ai": False}, timeout=90)
        elif action_id == "dev_loop_dry":
            api_action(
                "Dry-run dev loop",
                "/dev-loops/run",
                {"task_id": "latest-ready", "max_steps": 3, "dry_run": True, "use_ai": False},
                timeout=120,
            )
        elif action_id == "attention_summary":
            api_get_action("Desktop attention summary", "/desktop/attention", timeout=15)
        elif action_id == "setup_check":
            run_setup_check_action(show_full=False)
        elif action_id == "onboarding":
            run_onboarding_action(show_full=False, refresh_setup=True)

    def open_url(key: str) -> None:
        urls = desktop_urls()
        url = urls[key]
        webbrowser.open(url)
        log(f"Opened {url}")

    def start_dashboard() -> None:
        host = str(get_setting("dashboard_host", "127.0.0.1"))
        port = str(get_setting("dashboard_port", 8765))
        process = _spawn_main(["--dashboard", "--dashboard-host", host, "--dashboard-port", port])
        spawned_processes.append(process)
        log(f"Started dashboard process on http://{host}:{port} (pid {process.pid})")
        root.after(1200, refresh_status)

    def start_api_server() -> None:
        host = str(get_setting("api_host", "127.0.0.1"))
        port = str(get_setting("api_port", 8766))
        process = _spawn_main(["--api-server", "--api-host", host, "--api-port", port])
        spawned_processes.append(process)
        log(f"Started standalone API process on http://{host}:{port}/api (pid {process.pid})")
        root.after(1200, refresh_status)

    def set_chat_busy(busy: bool) -> None:
        try:
            send_button.configure(state="disabled" if busy else "normal")
            cancel_button.configure(state="normal" if busy else "disabled")
            restart_button.configure(state="disabled" if busy else "normal")
        except Exception:
            pass

    def reset_active_chat() -> None:
        with active_chat_lock:
            active_chat.update({
                "operation_id": "",
                "session_id": "",
                "acceptance_key": "",
                "cancel_requested": False,
                "cancel_dispatched": False,
                "tracker": None,
            })

    def finish_chat_ui(tracker: DesktopChatStreamTracker, *, status_note: str = "") -> None:
        if tracker.completion_clock is None:
            tracker.mark_complete()
        finish_stream_reply()
        metrics = tracker.timing_metrics()
        log(
            "Chat timing (content-free): "
            f"acceptance={metrics.get('send_to_acceptance_ms')} ms | "
            f"first visible={metrics.get('send_to_first_visible_text_ms')} ms | "
            f"response complete={metrics.get('send_to_response_complete_ms')} ms | "
            f"total={metrics.get('total_completion_ms')} ms"
        )
        if status_note:
            log(status_note)
        reset_active_chat()
        set_chat_busy(False)
        refresh_status(background=True)

    def reconcile_accepted_chat(operation_id: str, tracker: DesktopChatStreamTracker, *, timeout_seconds: float = 180.0) -> tuple[str, str]:
        """Read-only reconciliation after a viewer transport loss; never resubmit."""
        deadline = time.monotonic() + max(1.0, float(timeout_seconds))
        last_state = "running"
        while not desktop_closing.is_set() and time.monotonic() < deadline:
            try:
                payload = client.dashboard_chat_operation_status(operation_id, timeout=10)
            except DesktopApiError:
                time.sleep(0.75)
                continue
            marker = payload.get("operation") if isinstance(payload.get("operation"), dict) else {}
            last_state = str(marker.get("public_state") or last_state or "uncertain")
            turn = payload.get("session_turn") if isinstance(payload.get("session_turn"), dict) else {}
            response = str(turn.get("eidolon_response") or "").strip()
            if response:
                return last_state, response
            if last_state in {"completed", "failed", "cancelled", "uncertain"}:
                return last_state, ""
            time.sleep(0.75)
        return last_state if last_state != "running" else "uncertain", ""

    def dispatch_chat_cancellation(operation_id: str) -> None:
        try:
            payload = client.cancel_dashboard_chat_operation(operation_id, timeout=20)
            status = str(payload.get("status") or "cancellation_requested")
            safe_ui(lambda: log(f"Conversation cancellation: {status}."))
        except DesktopApiError as error:
            error_text = str(error)
            safe_ui(lambda value=error_text: log(f"Conversation cancellation failed safely: {value}"))

    def cancel_chat() -> None:
        operation_id = ""
        dispatch = False
        with active_chat_lock:
            if not active_chat.get("acceptance_key"):
                return
            active_chat["cancel_requested"] = True
            operation_id = str(active_chat.get("operation_id") or "")
            if operation_id and not active_chat.get("cancel_dispatched"):
                active_chat["cancel_dispatched"] = True
                dispatch = True
        log("Cancellation requested. The accepted turn will not be resubmitted.")
        if dispatch:
            threading.Thread(target=dispatch_chat_cancellation, args=(operation_id,), daemon=True).start()

    def send_chat() -> None:
        message = composer.get("1.0", "end-1c").strip()
        if not message or message == placeholder:
            return
        with active_chat_lock:
            if active_chat.get("acceptance_key"):
                log("One desktop conversation turn is already in progress.")
                return
        composer.delete("1.0", "end")
        log(f"Marcus: {message}")
        acceptance_key = f"desktop-{uuid.uuid4().hex}"
        tracker = DesktopChatStreamTracker()
        with active_chat_lock:
            active_chat.update({
                "operation_id": "",
                "session_id": "",
                "acceptance_key": acceptance_key,
                "cancel_requested": False,
                "cancel_dispatched": False,
                "tracker": tracker,
            })
        begin_stream_reply()
        set_chat_busy(True)

        def work() -> None:
            stream: Iterator[dict[str, Any]] | None = None
            completed = False
            failure_note = ""
            visible_text_received = False
            try:
                stream = client.stream_dashboard_chat(
                    {
                        "message": message,
                        "use_ai": bool(get_setting("ai_chat_enabled", True)),
                        "acceptance_key": acceptance_key,
                    },
                    timeout=180,
                )
                for event in stream:
                    if desktop_closing.is_set():
                        break
                    tracker.observe(event)
                    operation_id = tracker.operation_id
                    session_id = tracker.session_id
                    dispatch_cancel = False
                    with active_chat_lock:
                        if operation_id:
                            active_chat["operation_id"] = operation_id
                        if session_id:
                            active_chat["session_id"] = session_id
                        if operation_id and active_chat.get("cancel_requested") and not active_chat.get("cancel_dispatched"):
                            active_chat["cancel_dispatched"] = True
                            dispatch_cancel = True
                    if dispatch_cancel:
                        threading.Thread(target=dispatch_chat_cancellation, args=(operation_id,), daemon=True).start()

                    mode, text = _desktop_stream_text(event)
                    if mode and text:
                        visible_text_received = visible_text_received or bool(text.strip())
                        safe_ui(lambda mode=mode, text=text: render_stream_reply(mode, text, tracker))

                    event_name = str(event.get("event") or "")
                    if event_name == "error":
                        failure_note = str(event.get("message") or "The accepted conversation operation reported an error.")
                    if event_name == "done":
                        completed = True
                        turn = event.get("turn") if isinstance(event.get("turn"), dict) else {}
                        action = turn.get("action") if isinstance(turn.get("action"), dict) else {}
                        if action.get("command"):
                            safe_ui(lambda command=str(action.get("command")): log(f"Proposed action: {command}"))
                        break
            except DesktopApiError as error:
                payload = error.payload if isinstance(error.payload, dict) else {}
                if not tracker.operation_id:
                    tracker.operation_id = str(payload.get("operation_id") or "")
                if not tracker.session_id:
                    tracker.session_id = str(payload.get("session_id") or "")
                failure_note = str(error)
            finally:
                if stream is not None:
                    try:
                        stream.close()  # Viewer detaches; accepted provider work is not cancelled.
                    except Exception:
                        pass

            if desktop_closing.is_set():
                return

            if not completed and tracker.operation_id:
                state, reconciled_response = reconcile_accepted_chat(tracker.operation_id, tracker)
                if reconciled_response:
                    visible_text_received = True
                    safe_ui(lambda text=reconciled_response: render_stream_reply("replace", text, tracker))
                tracker.mark_complete()
                failure_note = (
                    f"Stream viewer detached; accepted operation reconciled as {state}. No duplicate request was sent."
                )
                completed = state in {"completed", "failed", "cancelled", "uncertain"}
            elif not completed:
                tracker.mark_complete()
                failure_note = (
                    "Chat transport ended before acceptance could be confirmed. It was not retried automatically. "
                    + failure_note
                ).strip()

            if failure_note and not visible_text_received:
                safe_ui(lambda: render_stream_reply(
                    "replace",
                    "The local conversation service is unavailable. Open Activity for details, then retry after the service is online.",
                    tracker,
                ))

            safe_ui(lambda: finish_chat_ui(tracker, status_note=failure_note))

        threading.Thread(target=work, daemon=True).start()

    def restore_from_watcher() -> None:
        root.deiconify()
        root.lift()
        if watcher_window is not None:
            try:
                watcher_window.withdraw()
            except Exception:
                pass
        refresh_status(background=False)

    def hide_to_tray() -> None:
        if tray_controller.running:
            root.withdraw()
            log("Main window hidden to real system tray. Tiny icon, same safety gates.")
            return
        message = "Real tray support is unavailable."
        if tray_controller.available.reason:
            message += f" {tray_controller.available.reason}"
        log(message)
        if bool(get_setting("desktop_tray_fallback_to_watcher", True)):
            hide_to_watcher()
        else:
            log("Tray fallback to watcher is disabled; leaving the main window open.")

    def hide_to_watcher() -> None:
        nonlocal watcher_window
        if watcher_window is None or not watcher_window.winfo_exists():
            watcher_window = tk.Toplevel(root)
            watcher_window.title("Eidolon Watcher")
            watcher_window.geometry("650x250")
            watcher_window.resizable(False, False)
            if bool(get_setting("desktop_watcher_topmost", True)):
                watcher_window.attributes("-topmost", True)
            watcher_window.protocol("WM_DELETE_WINDOW", lambda: watcher_window.withdraw())

            frame = tk.Frame(watcher_window, padx=12, pady=10)
            frame.pack(fill="both", expand=True)
            tk.Label(frame, text="Eidolon Watcher", font=("Segoe UI", 13, "bold")).pack(anchor="w")
            watcher_window.status_label = tk.Label(frame, text=counts_var.get(), wraplength=610, justify="left")
            watcher_window.status_label.pack(anchor="w", pady=(8, 0))
            watcher_window.attention_label = tk.Label(frame, text=attention_var.get(), wraplength=610, justify="left", font=("Segoe UI", 10, "bold"))
            watcher_window.attention_label.pack(anchor="w", pady=(4, 8))

            row = tk.Frame(frame)
            row.pack(fill="x")
            tk.Button(row, text="Restore", command=restore_from_watcher, width=10).pack(side="left", padx=(0, 5))
            tk.Button(row, text="Refresh", command=lambda: refresh_status(False), width=10).pack(side="left", padx=(0, 5))
            tk.Button(row, text="Mark Read", command=mark_latest_notification_read, width=10).pack(side="left", padx=(0, 5))
            tk.Button(row, text="Dismiss", command=dismiss_latest_notification, width=10).pack(side="left", padx=(0, 5))
            tk.Button(row, text="Approvals", command=lambda: open_url("approvals"), width=10).pack(side="left", padx=(0, 5))
            tk.Button(row, text="Exit", command=exit_desktop, width=8).pack(side="right")
        else:
            watcher_window.deiconify()
            watcher_window.lift()

        update_watcher()
        root.withdraw()
        log("Main window hidden to watcher mode. Real tray was unavailable or not requested, because dependencies are humanity's tiny obstacle course.")

    def restart_desktop() -> None:
        with active_chat_lock:
            if active_chat.get("acceptance_key"):
                log("Restart is unavailable while a conversation turn is active. Wait for it to finish or cancel it first.")
                return

        restart_button.configure(state="disabled")
        log("Restarting Eidolon Desktop...")
        root.update_idletasks()
        _save_desktop_geometry(root.geometry())
        desktop_closing.set()
        for process in list(spawned_processes):
            _stop_spawned_process(process)
        tray_controller.stop()
        try:
            instance_lock.unlink()
        except FileNotFoundError:
            pass
        try:
            _spawn_desktop_replacement()
        except Exception as error:
            desktop_closing.clear()
            restart_button.configure(state="normal")
            log(f"Desktop restart failed safely: {error}")
            return
        root.destroy()

    def exit_desktop() -> None:
        # Closing the viewer is not cancellation. The independent accepted
        # operation may finish and reconcile on the next launch without replay.
        root.update_idletasks()
        _save_desktop_geometry(root.geometry())
        desktop_closing.set()
        living = [process for process in spawned_processes if process.poll() is None]
        if living:
            if messagebox.askyesno("Close Eidolon Desktop", "Stop dashboard/API processes started from this window?"):
                for process in living:
                    try:
                        process.terminate()
                    except Exception:
                        pass
        tray_controller.stop()
        try: instance_lock.unlink()
        except FileNotFoundError: pass
        root.destroy()

    def on_close() -> None:
        if bool(get_setting("desktop_tray_minimize_on_close", True)) and tray_controller.running:
            hide_to_tray()
            return
        if bool(get_setting("desktop_close_to_watcher", False)):
            hide_to_watcher()
            return
        exit_desktop()

    controls = [
        ("Start Dashboard", start_dashboard),
        ("Start API", start_api_server),
        ("Open Dashboard", lambda: open_url("dashboard")),
        ("Open Chat", lambda: open_url("chat_console")),
        ("Open Actions", lambda: open_url("actions")),
        ("Open Notifications", lambda: open_url("notifications")),
        ("Open Approvals", lambda: open_url("approvals")),
        ("Open Setup", lambda: open_url("setup")),
        ("Open Onboarding", lambda: open_url("onboarding")),
        ("Refresh", lambda: refresh_status(False)),
        ("Hide to Tray", hide_to_tray),
        ("Hide to Watcher", hide_to_watcher),
    ]

    for index, (text, command) in enumerate(controls):
        button = themed_button(button_frame, text, command, width=24)
        button.grid(row=index, column=0, padx=4, pady=3, sticky="ew")

    button_frame.columnconfigure(0, weight=1)

    quick_actions = [
        ("Run Diagnostics", lambda: run_desktop_quick_action("diagnostics")),
        ("Watch Once", lambda: run_desktop_quick_action("watch_once")),
        ("Maintenance Scan", lambda: run_desktop_quick_action("maintenance_scan")),
        ("Plan Session", lambda: run_desktop_quick_action("session_plan")),
        ("Dry-run Dev Loop", lambda: run_desktop_quick_action("dev_loop_dry")),
        ("Attention Summary", lambda: run_desktop_quick_action("attention_summary")),
        ("Setup Check", lambda: run_desktop_quick_action("setup_check")),
        ("Onboarding", lambda: run_desktop_quick_action("onboarding")),
    ]

    for index, (text, command) in enumerate(quick_actions):
        button = themed_button(quick_frame, text, command, accent=colors["amber"], width=18, compact=True)
        button.grid(row=index // 2, column=index % 2, padx=4, pady=1, sticky="ew")

    for column in range(2):
        quick_frame.columnconfigure(column, weight=1)

    notification_actions = [
        ("Show Unread", log_unread_notifications),
        ("Open Latest Note", lambda: open_url("latest_notification")),
        ("Mark Latest Read", mark_latest_notification_read),
        ("Dismiss Latest", dismiss_latest_notification),
        ("Clear Dismissed", clear_dismissed_notifications_action),
        ("Show Approvals", log_pending_approvals),
        ("Open Latest Approval", lambda: open_url("latest_approval")),
        ("Dry-run Approval", dry_run_latest_approval),
    ]

    for index, (text, command) in enumerate(notification_actions):
        button = themed_button(notification_frame, text, command, accent=colors["green"], width=18, compact=True)
        button.grid(row=index // 2, column=index % 2, padx=4, pady=1, sticky="ew")

    for column in range(2):
        notification_frame.columnconfigure(column, weight=1)

    chat_frame = tk.Frame(
        composer_host,
        background=colors["surface"],
        highlightthickness=1,
        highlightbackground=colors["border"],
        padx=12,
        pady=10,
    )
    chat_frame.pack(fill="x", padx=48, pady=(6, 18))

    composer = tk.Text(
        chat_frame,
        height=3,
        wrap="word",
        background=colors["surface"],
        foreground=colors["text"],
        insertbackground=colors["cyan"],
        selectbackground="#17444d",
        relief="flat",
        borderwidth=0,
        font=("Segoe UI", 11),
        padx=6,
        pady=6,
    )
    composer.pack(side="left", fill="x", expand=True, padx=(0, 10))
    placeholder = "Message Eidolon..."
    composer.insert("1.0", placeholder)
    composer.configure(foreground=colors["muted"])

    def composer_focus_in(_event=None):
        if composer.get("1.0", "end-1c") == placeholder:
            composer.delete("1.0", "end")
            composer.configure(foreground=colors["text"])

    def composer_focus_out(_event=None):
        if not composer.get("1.0", "end-1c").strip():
            composer.insert("1.0", placeholder)
            composer.configure(foreground=colors["muted"])

    composer.bind("<FocusIn>", composer_focus_in)
    composer.bind("<FocusOut>", composer_focus_out)

    def composer_key(event):
        action = composer_key_action(
            keysym=getattr(event, "keysym", ""),
            shift=bool(getattr(event, "state", 0) & 0x0001),
            ime_composing=bool(getattr(event, "is_composing", False)),
        )
        if action == "send":
            send_chat()
            return "break"
        if action == "newline":
            return None
        return "break" if bool(getattr(event, "is_composing", False)) else None

    def focus_composer_from_host(event=None):
        target = "composer_frame" if event is not None else "composer_host"
        if should_focus_composer(target=target, disabled=str(composer.cget("state")) == "disabled"):
            composer.focus_set()

    composer.bind("<Return>", composer_key)
    chat_frame.bind("<Button-1>", focus_composer_from_host)
    composer_host.bind("<Button-1>", focus_composer_from_host)

    edit_menu = tk.Menu(
        root,
        tearoff=False,
        background=colors["surface"],
        foreground=colors["text"],
        activebackground=colors["surface_raised"],
        activeforeground=colors["cyan"],
        relief="flat",
        borderwidth=1,
    )
    edit_target: dict[str, Any] = {"widget": composer}

    def selected_text(widget) -> str:
        try:
            return str(widget.get("sel.first", "sel.last"))
        except tk.TclError:
            return ""

    def copy_selection() -> None:
        text = selected_text(edit_target["widget"])
        if not text:
            return
        root.clipboard_clear()
        root.clipboard_append(text)

    def delete_selection(widget) -> None:
        try:
            widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def cut_selection() -> None:
        widget = edit_target["widget"]
        if widget is not composer or str(widget.cget("state")) == "disabled":
            return
        copy_selection()
        delete_selection(widget)

    def paste_clipboard() -> None:
        widget = edit_target["widget"]
        if widget is not composer or str(widget.cget("state")) == "disabled":
            return
        try:
            text = str(root.clipboard_get())
        except tk.TclError:
            return
        if widget.get("1.0", "end-1c") == placeholder:
            widget.delete("1.0", "end")
            widget.configure(foreground=colors["text"])
        delete_selection(widget)
        widget.insert("insert", text)
        widget.focus_set()

    def select_all_text() -> None:
        widget = edit_target["widget"]
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "end-1c")
        widget.see("insert")

    edit_menu.add_command(label="Cut", command=cut_selection)
    edit_menu.add_command(label="Copy", command=copy_selection)
    edit_menu.add_command(label="Paste", command=paste_clipboard)
    edit_menu.add_separator()
    edit_menu.add_command(label="Select all", command=select_all_text)

    def show_edit_menu(event) -> str:
        widget = event.widget
        edit_target["widget"] = widget
        has_selection = bool(selected_text(widget))
        editable = widget is composer and str(widget.cget("state")) != "disabled"
        try:
            clipboard_available = bool(str(root.clipboard_get()))
        except tk.TclError:
            clipboard_available = False
        edit_menu.entryconfigure("Cut", state="normal" if editable and has_selection else "disabled")
        edit_menu.entryconfigure("Copy", state="normal" if has_selection else "disabled")
        edit_menu.entryconfigure("Paste", state="normal" if editable and clipboard_available else "disabled")
        edit_menu.entryconfigure("Select all", state="normal")
        try:
            edit_menu.tk_popup(event.x_root, event.y_root)
        finally:
            edit_menu.grab_release()
        return "break"

    for text_widget in (composer, output, activity_output):
        text_widget.bind("<Button-3>", show_edit_menu)
        text_widget.bind("<Shift-F10>", show_edit_menu)
    cancel_button = themed_button(chat_frame, "Cancel", cancel_chat, accent=colors["warning"], width=9)
    cancel_button.configure(state="disabled")
    cancel_button.pack(side="right", fill="y", padx=(0, 8))
    send_button = themed_button(chat_frame, "Send", send_chat, accent=colors["cyan"], width=10)
    send_button.configure(foreground=colors["cyan"], highlightbackground=colors["cyan"])
    send_button.pack(side="right", fill="y")

    def tray_safe(callback) -> None:
        root.after(0, callback)

    tray_controller.set_callbacks({
        "restore": lambda: tray_safe(restore_from_watcher),
        "hide": lambda: tray_safe(hide_to_tray),
        "open_dashboard": lambda: tray_safe(lambda: open_url("dashboard")),
        "open_chat": lambda: tray_safe(lambda: open_url("chat_console")),
        "open_notifications": lambda: tray_safe(lambda: open_url("notifications")),
        "open_approvals": lambda: tray_safe(lambda: open_url("approvals")),
        "open_onboarding": lambda: tray_safe(lambda: open_url("onboarding")),
        "diagnostics": lambda: tray_safe(lambda: run_desktop_quick_action("diagnostics")),
        "watch_once": lambda: tray_safe(lambda: run_desktop_quick_action("watch_once")),
        "session_plan": lambda: tray_safe(lambda: run_desktop_quick_action("session_plan")),
        "mark_read": lambda: tray_safe(mark_latest_notification_read),
        "dismiss": lambda: tray_safe(dismiss_latest_notification),
        "exit": lambda: tray_safe(exit_desktop),
    })

    def start_real_tray_if_enabled() -> None:
        if not bool(get_setting("desktop_tray_show_on_start", True)):
            log("Real tray auto-start is disabled.")
            return
        ok, message = tray_controller.start()
        log(f"Tray: {message}")
        if not ok and bool(get_setting("desktop_tray_fallback_to_watcher", True)):
            log("Tray fallback remains available through Hide to Watcher.")

    def schedule_refresh() -> None:
        refresh_status(background=True)
        seconds = int(get_setting("desktop_refresh_seconds", 8) or 8)
        root.after(max(2, seconds) * 1000, schedule_refresh)

    root.protocol("WM_DELETE_WINDOW", on_close)

    log("Eidolon is present.")
    log("Open Activity for system status and development controls.")
    refresh_status(background=False)

    if bool(get_setting("desktop_setup_check_on_start", False)):
        run_setup_check_action(show_full=False)

    if bool(get_setting("desktop_onboarding_check_on_start", False)):
        run_onboarding_action(show_full=False, refresh_setup=True)

    if bool(get_setting("desktop_launch_dashboard_on_start", False)):
        start_dashboard()

    start_real_tray_if_enabled()

    root.after(1500, schedule_refresh)
    root.mainloop()


def print_desktop_status() -> None:
    print(desktop_status_text())


if __name__ == "__main__":
    run_desktop_shell()


def print_desktop_tray_status() -> None:
    print(desktop_tray_status_text())
