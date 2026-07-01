from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

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


DESKTOP_VERSION = "1032.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = PROJECT_ROOT / "conscious_agent" / "main.py"


class DesktopApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload or {}


def _host_port(setting_host: str, setting_port: str, default_host: str, default_port: int) -> tuple[str, int]:
    host = str(get_setting(setting_host, default_host))
    port = int(get_setting(setting_port, default_port))
    return host, port


def desktop_urls() -> dict[str, str]:
    dashboard_host, dashboard_port = _host_port("dashboard_host", "dashboard_port", "127.0.0.1", 8765)
    api_host, api_port = _host_port("api_host", "api_port", "127.0.0.1", 8766)
    return {
        "dashboard": f"http://{dashboard_host}:{dashboard_port}",
        "dashboard_api": f"http://{dashboard_host}:{dashboard_port}/api",
        "standalone_api": f"http://{api_host}:{api_port}/api",
        "chat_console": f"http://{dashboard_host}:{dashboard_port}/chat-console",
        "actions": f"http://{dashboard_host}:{dashboard_port}/actions",
        "notifications": f"http://{dashboard_host}:{dashboard_port}/notifications",
        "approvals": f"http://{dashboard_host}:{dashboard_port}/approvals",
        "api_info": f"http://{dashboard_host}:{dashboard_port}/api-info",
        "desktop": f"http://{dashboard_host}:{dashboard_port}/desktop",
        "setup": f"http://{dashboard_host}:{dashboard_port}/setup",
        "latest_setup": f"http://{dashboard_host}:{dashboard_port}/detail?kind=setup&id=latest",
        "onboarding": f"http://{dashboard_host}:{dashboard_port}/onboarding",
        "latest_onboarding": f"http://{dashboard_host}:{dashboard_port}/detail?kind=onboarding&id=latest",
        "latest_notification": f"http://{dashboard_host}:{dashboard_port}/detail?kind=notification&id=latest-unread",
        "latest_approval": f"http://{dashboard_host}:{dashboard_port}/detail?kind=approval&id=latest-pending",
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


def run_desktop_shell() -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox, scrolledtext
    except Exception as error:
        print("Desktop shell unavailable: tkinter could not be imported.")
        print(f"Error: {error}")
        print()
        print(desktop_status_text())
        return

    client = LocalApiClient()
    spawned_processes: list[subprocess.Popen[Any]] = []
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
        return

    root.title(f"Eidolon Desktop Companion v{DESKTOP_VERSION}")
    root.geometry("1040x860")
    root.minsize(840, 680)

    status_var = tk.StringVar(value="API: checking...")
    api_var = tk.StringVar(value="Active API: [unknown]")
    counts_var = tk.StringVar(value="No status loaded yet.")
    attention_var = tk.StringVar(value="Attention: unknown.")
    chat_var = tk.StringVar(value="")

    top = tk.Frame(root, padx=12, pady=10)
    top.pack(fill="x")

    title = tk.Label(top, text="Eidolon Desktop Companion", font=("Segoe UI", 18, "bold"))
    title.pack(anchor="w")

    subtitle = tk.Label(top, text="Local launcher, quick-action desk, notification handler, watcher, and chat/action bridge. Still not allowed to chew files without approval.")
    subtitle.pack(anchor="w")

    status_frame = tk.LabelFrame(root, text="Live Status", padx=12, pady=10)
    status_frame.pack(fill="x", padx=12, pady=6)

    tk.Label(status_frame, textvariable=status_var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
    tk.Label(status_frame, textvariable=api_var).pack(anchor="w")
    tk.Label(status_frame, textvariable=counts_var, wraplength=880, justify="left").pack(anchor="w", pady=(4, 0))
    tk.Label(status_frame, textvariable=attention_var, wraplength=880, justify="left", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(4, 0))

    button_frame = tk.LabelFrame(root, text="Launch / Navigation", padx=12, pady=10)
    button_frame.pack(fill="x", padx=12, pady=6)

    if bool(get_setting("desktop_quick_actions_enabled", True)):
        quick_frame = tk.LabelFrame(root, text="Desktop Quick Actions", padx=12, pady=10)
        quick_frame.pack(fill="x", padx=12, pady=6)

        notification_frame = tk.LabelFrame(root, text="Notification / Approval Actions", padx=12, pady=10)
        notification_frame.pack(fill="x", padx=12, pady=6)
    else:
        quick_frame = tk.Frame(root)
        notification_frame = tk.Frame(root)

    log_frame = tk.LabelFrame(root, text="Output", padx=12, pady=10)
    log_frame.pack(fill="both", expand=True, padx=12, pady=6)

    output = scrolledtext.ScrolledText(log_frame, height=13, wrap="word")
    output.pack(fill="both", expand=True)

    def log(message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        output.insert("end", f"[{timestamp}] {message}\n")
        output.see("end")

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
                root.after(0, lambda: status_var.set("API: offline"))
                root.after(0, lambda: api_var.set("Active API: [none]"))
                root.after(0, lambda: counts_var.set(str(error)))
                root.after(0, lambda: attention_var.set("Attention: unknown because the API is offline."))
                root.after(0, update_watcher)
                if not background:
                    root.after(0, lambda: log(f"Status check failed: {error}"))

        threading.Thread(target=work, daemon=True).start()

    def api_action(label: str, endpoint: str, body: dict[str, Any] | None = None, timeout: int = 45) -> None:
        def work() -> None:
            try:
                payload = client.post(endpoint, body or {}, timeout=timeout)
                root.after(0, lambda: log(f"{label}: {pretty_payload(payload)}"))
                root.after(0, refresh_status)
            except DesktopApiError as error:
                root.after(0, lambda: log(f"{label} failed: {error}"))

        log(f"Starting: {label}")
        threading.Thread(target=work, daemon=True).start()

    def api_get_action(label: str, endpoint: str, timeout: int = 15) -> None:
        def work() -> None:
            try:
                payload = client.get(endpoint, timeout=timeout)
                root.after(0, lambda: log(f"{label}: {pretty_payload(payload)}"))
                root.after(0, refresh_status)
            except DesktopApiError as error:
                root.after(0, lambda: log(f"{label} failed: {error}"))

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
                root.after(0, lambda: log(f"Unread notification fetch failed: {error}"))

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
                root.after(0, lambda: log(f"Pending approval fetch failed: {error}"))

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
                root.after(0, lambda: log(f"Setup check failed: {error}"))

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
                root.after(0, lambda: log(f"Onboarding wizard failed: {error}"))

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

    def send_chat() -> None:
        message = chat_var.get().strip()
        if not message:
            return
        chat_var.set("")
        log(f"Marcus: {message}")

        def work() -> None:
            try:
                payload = client.post("/dashboard-chat", {"message": message}, timeout=90)
                data = payload.get("data") or {}
                response = data.get("response") or data.get("assistant_response") or payload.get("message") or "Chat turn saved."
                action = data.get("chat_action") or data.get("action") or {}
                action_line = ""
                if isinstance(action, dict) and action.get("command"):
                    action_line = f"\nProposed action: {action.get('command')}"
                root.after(0, lambda: log(f"Eidolon: {response}{action_line}"))
                root.after(0, refresh_status)
            except DesktopApiError as error:
                root.after(0, lambda: log(f"Chat failed: {error}"))

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

    def exit_desktop() -> None:
        living = [process for process in spawned_processes if process.poll() is None]
        if living:
            if messagebox.askyesno("Close Eidolon Desktop", "Stop dashboard/API processes started from this window?"):
                for process in living:
                    try:
                        process.terminate()
                    except Exception:
                        pass
        tray_controller.stop()
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
        button = tk.Button(button_frame, text=text, command=command, width=16)
        button.grid(row=index // 5, column=index % 5, padx=4, pady=4, sticky="ew")

    for column in range(5):
        button_frame.columnconfigure(column, weight=1)

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
        button = tk.Button(quick_frame, text=text, command=command, width=18)
        button.grid(row=index // 7, column=index % 7, padx=4, pady=4, sticky="ew")

    for column in range(7):
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
        button = tk.Button(notification_frame, text=text, command=command, width=18)
        button.grid(row=index // 4, column=index % 4, padx=4, pady=4, sticky="ew")

    for column in range(4):
        notification_frame.columnconfigure(column, weight=1)

    chat_frame = tk.LabelFrame(root, text="Chat / Action Request", padx=12, pady=10)
    chat_frame.pack(fill="x", padx=12, pady=6)

    entry = tk.Entry(chat_frame, textvariable=chat_var)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    entry.bind("<Return>", lambda _event: send_chat())
    tk.Button(chat_frame, text="Send", command=send_chat, width=12).pack(side="right")

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

    log("Desktop companion started.")
    log("Use Start Dashboard if the API is offline. Yes, even the local goblin needs a server to talk to.")
    log("v4.5 adds a guided onboarding wizard. Same safety gates, fewer mystery failures wearing a trench coat.")
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
