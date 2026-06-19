from __future__ import annotations

import importlib.util
import json
import os
import platform
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR
from settings_manager import get_setting, load_settings


SETUP_VERSION = "4.5"
SETUP_REPORTS_DIR = DATA_DIR / "setup_reports"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = PROJECT_ROOT / "conscious_agent" / "main.py"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _report_id() -> str:
    return "setup_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_setup_dir() -> None:
    SETUP_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    readme = SETUP_REPORTS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Setup Reports\n\nSaved first-run setup and desktop startup helper reports.\n",
            encoding="utf-8",
        )


def _check(check_id: str, title: str, status: str, message: str, *, severity: str = "info", details: Any | None = None, suggestions: list[str] | None = None, commands: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {},
        "suggestions": suggestions or [],
        "commands": commands or [],
    }


def _module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _http_json(url: str, timeout: float = 2.5) -> tuple[bool, dict[str, Any] | None, str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return False, None, f"Response was not JSON: {raw[:160]}"
            return True, data, ""
    except urllib.error.HTTPError as error:
        return False, None, f"HTTP {error.code}: {error.reason}"
    except Exception as error:
        return False, None, str(error)


def _port_accepts_connection(host: str, port: int, timeout: float = 1.0) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "connection accepted"
    except Exception as error:
        return False, str(error)


def _port_bindable(host: str, port: int) -> tuple[bool, str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True, "port can be bound"
    except Exception as error:
        return False, str(error)


def _localhost_for_bind(host: str) -> str:
    if host in {"", "localhost"}:
        return "127.0.0.1"
    return host


def _check_python() -> dict[str, Any]:
    version = sys.version_info
    status = "ok" if version >= (3, 10) else "warning"
    severity = "info" if status == "ok" else "warning"
    message = f"Python {platform.python_version()} on {platform.system()} {platform.release()}."
    suggestions: list[str] = []
    if status != "ok":
        suggestions.append("Use Python 3.10 or newer. Eidolon may work on older versions until it decides not to, because software enjoys betrayal.")
    return _check(
        "python_runtime",
        "Python runtime",
        status,
        message,
        severity=severity,
        details={"executable": sys.executable, "version_info": list(version[:3]), "platform": platform.platform()},
        suggestions=suggestions,
    )


def _check_project_layout() -> dict[str, Any]:
    missing = []
    expected = [
        PROJECT_ROOT / "conscious_agent",
        MAIN_FILE,
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "README_NEXT_STEPS.md",
    ]
    for path in expected:
        if not path.exists():
            missing.append(str(path))
    if missing:
        return _check(
            "project_layout",
            "Project layout",
            "error",
            "One or more required project files are missing.",
            severity="critical",
            details={"project_root": str(PROJECT_ROOT), "missing": missing},
            suggestions=["Re-extract the latest Eidolon zip into a clean folder and run commands from the outer Eidolon folder."],
        )
    return _check(
        "project_layout",
        "Project layout",
        "ok",
        "Required project files are present.",
        details={"project_root": str(PROJECT_ROOT), "main_file": str(MAIN_FILE)},
    )


def _check_data_writable() -> dict[str, Any]:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".setup_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return _check("data_writable", "Data directory writable", "ok", "Eidolon can write to its data directory.", details={"data_dir": str(DATA_DIR)})
    except Exception as error:
        return _check(
            "data_writable",
            "Data directory writable",
            "error",
            f"Eidolon cannot write to its data directory: {error}",
            severity="critical",
            details={"data_dir": str(DATA_DIR), "error": str(error)},
            suggestions=["Move Eidolon to a normal user-writable folder, not Program Files or a locked synced folder."],
        )


def _check_required_packages() -> dict[str, Any]:
    packages = {
        "requests": "requests>=2.31.0",
        "chromadb": "chromadb>=0.5.0",
    }
    missing = [requirement for module, requirement in packages.items() if not _module_available(module)]
    if missing:
        return _check(
            "required_packages",
            "Required Python packages",
            "warning",
            "Some required packages are missing.",
            severity="warning",
            details={"missing": missing},
            suggestions=["Install required packages from requirements.txt."],
            commands=["python -m pip install -r requirements.txt"],
        )
    return _check("required_packages", "Required Python packages", "ok", "Required Python packages are importable.", details={"packages": list(packages.values())})


def _check_desktop_packages() -> dict[str, Any]:
    tkinter_ok = _module_available("tkinter")
    pystray_ok = _module_available("pystray")
    pillow_ok = _module_available("PIL")
    missing_optional = []
    if not pystray_ok:
        missing_optional.append("pystray")
    if not pillow_ok:
        missing_optional.append("pillow")

    suggestions = []
    commands = []
    status = "ok"
    severity = "info"
    message = "Desktop support looks ready."

    if not tkinter_ok:
        status = "warning"
        severity = "warning"
        message = "Tkinter is unavailable, so the desktop shell cannot open on this Python install."
        suggestions.append("Install a Python build that includes Tkinter. The python.org Windows installer normally does.")

    if missing_optional:
        if status == "ok":
            status = "warning"
            severity = "warning"
            message = "Desktop shell can run, but real tray support is missing optional packages. Watcher fallback still works."
        suggestions.append("Install optional tray packages if you want a real system tray icon.")
        commands.append("python -m pip install pystray pillow")

    return _check(
        "desktop_packages",
        "Desktop and tray packages",
        status,
        message,
        severity=severity,
        details={"tkinter": tkinter_ok, "pystray": pystray_ok, "pillow": pillow_ok, "missing_optional": missing_optional},
        suggestions=suggestions,
        commands=commands,
    )


def _check_service_port(name: str, host: str, port: int, endpoint: str, start_command: str) -> dict[str, Any]:
    bind_host = _localhost_for_bind(host)
    url = f"http://{host}:{port}{endpoint}"
    ok, payload, error = _http_json(url, timeout=2.0)
    if ok and isinstance(payload, dict) and payload.get("ok") is True and (payload.get("data") or {}).get("name") == "Eidolon":
        return _check(
            f"{name}_service",
            f"{name.title()} service",
            "ok",
            f"{name.title()} API is already responding at {url}.",
            details={"url": url, "api_version": payload.get("api_version"), "active_project": (payload.get("data") or {}).get("active_project")},
        )

    accepts, connect_message = _port_accepts_connection(bind_host, port)
    if accepts:
        return _check(
            f"{name}_service",
            f"{name.title()} service",
            "warning",
            f"Port {port} is open, but Eidolon did not respond correctly at {url}.",
            severity="warning",
            details={"url": url, "http_error": error, "connect": connect_message},
            suggestions=["Another process may be using this port, or an older Eidolon server may be stuck."],
            commands=[start_command],
        )

    bindable, bind_message = _port_bindable(bind_host, port)
    if bindable:
        return _check(
            f"{name}_service",
            f"{name.title()} service",
            "info",
            f"{name.title()} service is not running, and port {port} appears available.",
            details={"url": url, "connect_error": connect_message, "bind": bind_message},
            suggestions=[f"Start the {name} service when needed."],
            commands=[start_command],
        )

    return _check(
        f"{name}_service",
        f"{name.title()} service",
        "warning",
        f"{name.title()} service is not responding, and port {port} could not be bound.",
        severity="warning",
        details={"url": url, "connect_error": connect_message, "bind_error": bind_message},
        suggestions=["Change the configured port or stop the process using it."],
        commands=[f"python conscious_agent/main.py --set-setting {name}_port {port + 1}" if name in {"dashboard", "api"} else start_command],
    )


def _check_services(settings: dict[str, Any]) -> list[dict[str, Any]]:
    dashboard_host = str(settings.get("dashboard_host") or "127.0.0.1")
    dashboard_port = int(settings.get("dashboard_port") or 8765)
    api_host = str(settings.get("api_host") or "127.0.0.1")
    api_port = int(settings.get("api_port") or 8766)
    return [
        _check_service_port(
            "dashboard",
            dashboard_host,
            dashboard_port,
            "/api/status",
            f"python conscious_agent/main.py --dashboard --dashboard-host {dashboard_host} --dashboard-port {dashboard_port}",
        ),
        _check_service_port(
            "api",
            api_host,
            api_port,
            "/api/status",
            f"python conscious_agent/main.py --api-server --api-host {api_host} --api-port {api_port}",
        ),
    ]


def _check_ollama(settings: dict[str, Any]) -> dict[str, Any]:
    base_url = str(settings.get("ollama_base_url") or "http://localhost:11434").rstrip("/")
    local_model = str(settings.get("local_model") or "")
    embed_model = str(settings.get("embed_model") or "")
    ok, payload, error = _http_json(f"{base_url}/api/tags", timeout=3.0)
    if not ok or not isinstance(payload, dict):
        return _check(
            "ollama",
            "Ollama service and models",
            "warning",
            f"Ollama did not respond at {base_url}.",
            severity="warning",
            details={"base_url": base_url, "error": error},
            suggestions=["Start Ollama before using local AI, chat, summaries, embeddings, reviews, or patch suggestions."],
            commands=["ollama serve", f"ollama pull {local_model}", f"ollama pull {embed_model}"],
        )

    models = []
    for item in payload.get("models", []):
        if isinstance(item, dict) and item.get("name"):
            models.append(str(item.get("name")))
    def has_model(model: str) -> bool:
        return any(name == model or name.startswith(model + ":") or model.startswith(name + ":") for name in models)

    missing = []
    if local_model and not has_model(local_model):
        missing.append(local_model)
    if embed_model and not has_model(embed_model):
        missing.append(embed_model)

    if missing:
        return _check(
            "ollama",
            "Ollama service and models",
            "warning",
            "Ollama is running, but one or more configured models are missing.",
            severity="warning",
            details={"base_url": base_url, "configured_local_model": local_model, "configured_embed_model": embed_model, "installed_models": models, "missing": missing},
            suggestions=["Pull the missing models or change Eidolon settings to models you already have."],
            commands=[f"ollama pull {model}" for model in missing],
        )

    return _check(
        "ollama",
        "Ollama service and models",
        "ok",
        "Ollama is responding and configured models appear available.",
        details={"base_url": base_url, "configured_local_model": local_model, "configured_embed_model": embed_model, "installed_models": models},
    )


def _check_settings(settings: dict[str, Any]) -> dict[str, Any]:
    risky_hosts = []
    for key in ("dashboard_host", "api_host"):
        value = str(settings.get(key) or "")
        if value not in {"127.0.0.1", "localhost", "::1"}:
            risky_hosts.append({"setting": key, "value": value})
    if risky_hosts:
        return _check(
            "local_only_settings",
            "Local-only host settings",
            "warning",
            "One or more service hosts are not loopback/local-only.",
            severity="warning",
            details={"risky_hosts": risky_hosts},
            suggestions=["Keep dashboard_host and api_host set to 127.0.0.1 unless you truly know why you are exposing a local AI control panel. Humanity begs you."],
            commands=["python conscious_agent/main.py --set-setting dashboard_host 127.0.0.1", "python conscious_agent/main.py --set-setting api_host 127.0.0.1"],
        )
    return _check(
        "local_only_settings",
        "Local-only host settings",
        "ok",
        "Dashboard and API hosts are local-only.",
        details={"dashboard_host": settings.get("dashboard_host"), "api_host": settings.get("api_host")},
    )


def create_setup_report(save: bool = True) -> dict[str, Any]:
    settings = load_settings()
    checks: list[dict[str, Any]] = [
        _check_python(),
        _check_project_layout(),
        _check_data_writable(),
        _check_required_packages(),
        _check_desktop_packages(),
        _check_settings(settings),
    ]
    if bool(settings.get("setup_check_ollama", True)):
        checks.append(_check_ollama(settings))
    else:
        checks.append(_check("ollama", "Ollama service and models", "info", "Ollama setup check is disabled by settings."))
    if bool(settings.get("setup_check_ports", True)):
        checks.extend(_check_services(settings))
    else:
        checks.append(_check("local_services", "Local service ports", "info", "Dashboard/API port checks are disabled by settings."))

    counts = {
        "ok": sum(1 for check in checks if check.get("status") == "ok"),
        "info": sum(1 for check in checks if check.get("status") == "info"),
        "warning": sum(1 for check in checks if check.get("status") == "warning"),
        "error": sum(1 for check in checks if check.get("status") == "error"),
    }
    if counts["error"]:
        overall = "critical"
    elif counts["warning"]:
        overall = "attention_needed"
    else:
        overall = "ready"

    commands: list[str] = []
    suggestions: list[str] = []
    for check in checks:
        for command in check.get("commands", []):
            if command and command not in commands:
                commands.append(command)
        for suggestion in check.get("suggestions", []):
            if suggestion and suggestion not in suggestions:
                suggestions.append(suggestion)

    report = {
        "id": _report_id(),
        "version": SETUP_VERSION,
        "created_at": _now(),
        "status": overall,
        "counts": counts,
        "summary": _summary_text(overall, counts),
        "checks": checks,
        "suggested_commands": commands,
        "suggestions": suggestions,
        "settings_snapshot": {
            "dashboard_host": settings.get("dashboard_host"),
            "dashboard_port": settings.get("dashboard_port"),
            "api_host": settings.get("api_host"),
            "api_port": settings.get("api_port"),
            "ollama_base_url": settings.get("ollama_base_url"),
            "local_model": settings.get("local_model"),
            "embed_model": settings.get("embed_model"),
            "desktop_real_tray_enabled": settings.get("desktop_real_tray_enabled"),
            "desktop_tray_fallback_to_watcher": settings.get("desktop_tray_fallback_to_watcher"),
        },
        "safety": "Setup helper is read-only except saving this report. It recommends commands but does not install packages, edit files, or expose services.",
    }
    if save:
        save_setup_report(report)
    return report


def _summary_text(status: str, counts: dict[str, int]) -> str:
    if status == "ready":
        return "Setup looks ready. The machine did not find a new way to be annoying."
    if status == "critical":
        return f"Setup has critical issues: {counts.get('error', 0)} error(s), {counts.get('warning', 0)} warning(s)."
    return f"Setup needs attention: {counts.get('warning', 0)} warning(s), {counts.get('error', 0)} error(s)."


def save_setup_report(report: dict[str, Any]) -> None:
    _ensure_setup_dir()
    path = SETUP_REPORTS_DIR / f"{report.get('id')}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


def list_setup_reports() -> list[dict[str, Any]]:
    _ensure_setup_dir()
    reports: list[dict[str, Any]] = []
    for path in SETUP_REPORTS_DIR.glob("setup_*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                reports.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(reports, key=lambda item: item.get("created_at", ""), reverse=True)


def load_setup_report(report_id: str) -> dict[str, Any] | None:
    resolved = resolve_setup_report_id(report_id)
    if not resolved:
        return None
    path = SETUP_REPORTS_DIR / f"{resolved}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def resolve_setup_report_id(report_id: str) -> str | None:
    report_id = (report_id or "latest").strip()
    reports = list_setup_reports()
    if not reports:
        return None
    if report_id == "latest":
        return str(reports[0].get("id"))
    if report_id.startswith("latest-"):
        wanted = report_id.replace("latest-", "", 1)
        for report in reports:
            if report.get("status") == wanted:
                return str(report.get("id"))
        return None
    for report in reports:
        if report.get("id") == report_id:
            return report_id
    return None


def setup_report_text(report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# Setup report: {report.get('id')}",
        f"Version: {report.get('version')}",
        f"Created: {report.get('created_at')}",
        f"Status: {report.get('status')}",
        f"Summary: {report.get('summary')}",
        "",
        "## Counts",
    ]
    counts = report.get("counts") or {}
    for key in ("ok", "info", "warning", "error"):
        lines.append(f"- {key}: {counts.get(key, 0)}")

    lines.extend(["", "## Checks"])
    for check in report.get("checks", []):
        lines.append(f"- [{check.get('status')}] {check.get('title')}: {check.get('message')}")
        for suggestion in check.get("suggestions", []):
            lines.append(f"  suggestion: {suggestion}")
        for command in check.get("commands", []):
            lines.append(f"  command: {command}")
        if full and check.get("details"):
            lines.append("  details:")
            details = json.dumps(check.get("details"), indent=2, default=str).splitlines()
            lines.extend(f"    {line}" for line in details)

    commands = report.get("suggested_commands", [])
    if commands:
        lines.extend(["", "## Suggested commands"])
        lines.extend(f"- {command}" for command in commands)

    if full:
        lines.extend(["", "## Settings snapshot", json.dumps(report.get("settings_snapshot", {}), indent=2, default=str)])
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])

    return "\n".join(lines)


def print_setup_check(full: bool = False) -> None:
    report = create_setup_report(save=True)
    print(setup_report_text(report, full=full))


def print_setup_reports() -> None:
    reports = list_setup_reports()
    if not reports:
        print("No setup reports saved yet.")
        return
    for report in reports:
        counts = report.get("counts") or {}
        print(
            f"{report.get('id')} | {report.get('status')} | "
            f"warnings={counts.get('warning', 0)} errors={counts.get('error', 0)} | {report.get('created_at')}"
        )


def print_saved_setup_report(report_id: str = "latest", full: bool = False) -> None:
    report = load_setup_report(report_id)
    if not report:
        print(f"Setup report not found: {report_id}")
        return
    print(setup_report_text(report, full=full))
