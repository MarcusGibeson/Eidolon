from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
import threading
import time
import urllib.error
import urllib.request
import webbrowser


def _browser_host(host: str) -> str:
    token = str(host or "127.0.0.1").strip()
    return "127.0.0.1" if token in {"0.0.0.0", "::", "[::]"} else token


def dashboard_url(host: str, port: int) -> str:
    return f"http://{_browser_host(host)}:{int(port)}/"


def conversation_url(host: str, port: int) -> str:
    return dashboard_url(host, port) + "chat-console"


def probe_existing_dashboard(host: str, port: int, *, timeout_seconds: float = 0.5) -> dict[str, object]:
    url = dashboard_url(host, port) + "api/dashboard-health"
    try:
        request = urllib.request.Request(url, headers={"Cache-Control": "no-store"})
        with urllib.request.urlopen(request, timeout=max(0.1, timeout_seconds)) as response:
            body = response.read().decode("utf-8", "replace")
            payload = json.loads(body)
            service = str(payload.get("service") or "") if isinstance(payload, dict) else ""
            return {
                "reachable": True,
                "eidolon_dashboard": service == "eidolon-dashboard",
                "status_code": int(response.status),
                "service": service,
            }
    except urllib.error.HTTPError as error:
        return {"reachable": True, "eidolon_dashboard": False, "status_code": int(error.code), "service": ""}
    except Exception:
        return {"reachable": False, "eidolon_dashboard": False, "status_code": None, "service": ""}


def _open_browser_when_ready(host: str, port: int, *, timeout_seconds: float = 15.0) -> threading.Thread:
    url = conversation_url(host, port)

    def worker() -> None:
        deadline = time.monotonic() + max(1.0, timeout_seconds)
        while time.monotonic() < deadline:
            status = probe_existing_dashboard(host, port, timeout_seconds=0.35)
            if status.get("eidolon_dashboard"):
                webbrowser.open(url, new=2, autoraise=True)
                return
            time.sleep(0.12)

    thread = threading.Thread(target=worker, name="eidolon-dashboard-browser", daemon=True)
    thread.start()
    return thread


def launch_dashboard_from_argv(argv: Sequence[str]) -> int:
    """Launch only the dashboard without importing the heavyweight general CLI graph."""

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--dashboard-host", default=None)
    parser.add_argument("--dashboard-port", type=int, default=None)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args, _unknown = parser.parse_known_args(list(argv))
    if not args.dashboard:
        raise ValueError("The lightweight dashboard launcher requires --dashboard.")
    host = str(args.dashboard_host or "127.0.0.1")
    port = int(args.dashboard_port or 8765)
    open_browser = bool(args.open_browser and not args.no_browser)
    existing = probe_existing_dashboard(host, port)
    if existing.get("eidolon_dashboard"):
        print(f"Eidolon is already running at {dashboard_url(host, port)}")
        if open_browser:
            webbrowser.open(conversation_url(host, port), new=2, autoraise=True)
        return 0
    if existing.get("reachable"):
        raise RuntimeError(f"Port {port} is already in use by another local service.")
    if open_browser:
        _open_browser_when_ready(host, port)
    print(f"Starting Eidolon at {dashboard_url(host, port)}")
    print("Press Ctrl+C in this window to stop the dashboard.")
    try:
        from dashboard import run_dashboard
    except ImportError:
        from dashboard import run_dashboard
    run_dashboard(host=host, port=port)
    return 0
