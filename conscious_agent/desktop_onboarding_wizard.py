from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from desktop_setup_helper import create_setup_report, list_setup_reports, load_setup_report, setup_report_text
from paths import DATA_DIR
from settings_manager import load_settings


ONBOARDING_VERSION = "4.5"
ONBOARDING_RUNS_DIR = DATA_DIR / "onboarding_runs"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _run_id() -> str:
    return "onboarding_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_onboarding_dir() -> None:
    ONBOARDING_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    readme = ONBOARDING_RUNS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Onboarding Runs\n\nSaved desktop guided onboarding wizard runs.\n",
            encoding="utf-8",
        )


def _step(
    step_id: str,
    title: str,
    status: str,
    description: str,
    *,
    priority: str = "normal",
    commands: list[str] | None = None,
    links: list[dict[str, str]] | None = None,
    suggestions: list[str] | None = None,
    check_ids: list[str] | None = None,
    safe_to_auto_run: bool = False,
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "status": status,
        "priority": priority,
        "description": description,
        "commands": commands or [],
        "links": links or [],
        "suggestions": suggestions or [],
        "related_check_ids": check_ids or [],
        "safe_to_auto_run": safe_to_auto_run,
    }


def _latest_setup_or_new() -> dict[str, Any]:
    reports = list_setup_reports()
    if reports:
        return reports[0]
    return create_setup_report(save=True)


def _check_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = report.get("checks") or []
    return {str(check.get("id")): check for check in checks if isinstance(check, dict)}


def _is_attention(check: dict[str, Any] | None) -> bool:
    return bool(check and check.get("status") in {"warning", "error"})


def build_onboarding_run(*, save: bool = True, refresh_setup: bool = True) -> dict[str, Any]:
    """Create a guided onboarding run from the current setup state.

    This is advisory. It saves a runbook and recommends commands, but it does
    not install packages, change settings, start services, or approve anything.
    Apparently the machine is not allowed to press every shiny button. Tragic.
    """
    settings = load_settings()
    setup_report = create_setup_report(save=True) if refresh_setup else _latest_setup_or_new()
    checks = _check_map(setup_report)
    steps: list[dict[str, Any]] = []

    project_layout = checks.get("project_layout")
    data_writable = checks.get("data_writable")
    required_packages = checks.get("required_packages")
    desktop_packages = checks.get("desktop_packages")
    local_only = checks.get("local_only_settings")
    ollama = checks.get("ollama")
    dashboard_service = checks.get("dashboard_service")
    api_service = checks.get("api_service")

    if _is_attention(project_layout):
        steps.append(_step(
            "fix_project_layout",
            "Fix project folder layout",
            "blocked",
            "Required files are missing. Re-extract the latest zip into a clean Eidolon folder, then run commands from that outer folder.",
            priority="critical",
            suggestions=project_layout.get("suggestions", []),
            check_ids=["project_layout"],
        ))
    else:
        steps.append(_step(
            "confirm_project_layout",
            "Project folder looks usable",
            "done",
            "The expected Eidolon files are present.",
            priority="low",
            check_ids=["project_layout"],
        ))

    if _is_attention(data_writable):
        steps.append(_step(
            "fix_data_folder",
            "Move Eidolon to a writable folder",
            "blocked",
            "Eidolon cannot write to its data folder. Move it somewhere your user account can write, like your normal Documents or project folder.",
            priority="critical",
            suggestions=data_writable.get("suggestions", []),
            check_ids=["data_writable"],
        ))
    else:
        steps.append(_step(
            "confirm_data_folder",
            "Data folder is writable",
            "done",
            "Eidolon can save memories, reports, notifications, and other local state.",
            priority="low",
            check_ids=["data_writable"],
        ))

    if _is_attention(required_packages):
        steps.append(_step(
            "install_required_packages",
            "Install required Python packages",
            "needs_action",
            "Some required packages are missing. Install from requirements.txt before using semantic memory, local requests, or advanced workflows.",
            priority="high",
            commands=required_packages.get("commands", []),
            suggestions=required_packages.get("suggestions", []),
            check_ids=["required_packages"],
        ))
    else:
        steps.append(_step(
            "confirm_required_packages",
            "Required packages are importable",
            "done",
            "Core Python dependencies are available.",
            priority="low",
            check_ids=["required_packages"],
        ))

    if _is_attention(desktop_packages):
        missing = (desktop_packages.get("details") or {}).get("missing_optional") or []
        tkinter_ok = (desktop_packages.get("details") or {}).get("tkinter", True)
        if not tkinter_ok:
            steps.append(_step(
                "fix_tkinter",
                "Use a Python install with Tkinter",
                "needs_action",
                "The desktop shell needs Tkinter. The normal python.org Windows installer includes it; some stripped-down Python installs do not, because convenience would be too merciful.",
                priority="high",
                suggestions=desktop_packages.get("suggestions", []),
                check_ids=["desktop_packages"],
            ))
        if missing:
            steps.append(_step(
                "install_optional_tray_packages",
                "Install optional tray packages",
                "optional",
                "The desktop shell can run without these, but real system tray mode needs pystray and Pillow. Watcher fallback still works.",
                priority="medium",
                commands=desktop_packages.get("commands", []),
                suggestions=desktop_packages.get("suggestions", []),
                check_ids=["desktop_packages"],
            ))
    else:
        steps.append(_step(
            "confirm_desktop_packages",
            "Desktop and tray packages look ready",
            "done",
            "Tkinter is available, and optional tray packages appear importable.",
            priority="low",
            check_ids=["desktop_packages"],
        ))

    if _is_attention(local_only):
        steps.append(_step(
            "restore_local_only_hosts",
            "Keep dashboard and API local-only",
            "needs_action",
            "One or more service hosts are not loopback-only. Set dashboard_host and api_host back to 127.0.0.1 unless you truly intend to expose a local AI control panel.",
            priority="critical",
            commands=local_only.get("commands", []),
            suggestions=local_only.get("suggestions", []),
            check_ids=["local_only_settings"],
        ))
    else:
        steps.append(_step(
            "confirm_local_only_hosts",
            "Local-only service settings are safe",
            "done",
            "Dashboard and API hosts are configured for loopback/local-only use.",
            priority="low",
            check_ids=["local_only_settings"],
        ))

    if _is_attention(ollama):
        details = ollama.get("details") or {}
        steps.append(_step(
            "start_or_configure_ollama",
            "Start Ollama and pull configured models",
            "needs_action",
            "Local AI features need Ollama responding and the configured chat/embedding models installed. Eidolon can still do non-AI workflows without it, like a haunted calculator with boundaries.",
            priority="high",
            commands=ollama.get("commands", []),
            suggestions=ollama.get("suggestions", []),
            check_ids=["ollama"],
            links=[{"label": "Ollama base URL", "url": str(details.get("base_url") or settings.get("ollama_base_url") or "http://localhost:11434")}],
        ))
    else:
        steps.append(_step(
            "confirm_ollama",
            "Ollama looks ready",
            "done",
            "Ollama is responding and the configured local model settings look usable.",
            priority="low",
            check_ids=["ollama"],
        ))

    if dashboard_service and dashboard_service.get("status") != "ok":
        steps.append(_step(
            "start_dashboard",
            "Start the dashboard",
            "ready",
            "The dashboard is not currently responding. Start it when you want the browser interface, API routes, action center, setup pages, and chat console.",
            priority="medium",
            commands=dashboard_service.get("commands", []),
            suggestions=dashboard_service.get("suggestions", []),
            check_ids=["dashboard_service"],
            links=[{"label": "Dashboard", "url": f"http://{settings.get('dashboard_host')}:{settings.get('dashboard_port')}"}],
            safe_to_auto_run=True,
        ))
    elif dashboard_service:
        steps.append(_step(
            "confirm_dashboard",
            "Dashboard is responding",
            "done",
            "The dashboard-integrated API is already online.",
            priority="low",
            check_ids=["dashboard_service"],
            links=[{"label": "Dashboard", "url": f"http://{settings.get('dashboard_host')}:{settings.get('dashboard_port')}"}],
        ))

    if api_service and api_service.get("status") != "ok":
        steps.append(_step(
            "start_api_if_needed",
            "Start standalone API only if needed",
            "optional",
            "The dashboard already includes API routes. Start the standalone API only for external local tools or when you want the API without the dashboard.",
            priority="low",
            commands=api_service.get("commands", []),
            suggestions=api_service.get("suggestions", []),
            check_ids=["api_service"],
            links=[{"label": "Standalone API", "url": f"http://{settings.get('api_host')}:{settings.get('api_port')}/api"}],
            safe_to_auto_run=True,
        ))
    elif api_service:
        steps.append(_step(
            "confirm_api",
            "Standalone API is responding",
            "done",
            "The standalone API is online.",
            priority="low",
            check_ids=["api_service"],
        ))

    if setup_report.get("status") == "ready":
        steps.append(_step(
            "first_use_flow",
            "Start using Eidolon",
            "ready",
            "Setup looks ready. Start the desktop shell or dashboard, run a watch check, then use Chat Console or Action Center to continue work.",
            priority="medium",
            commands=[
                "python conscious_agent/main.py --desktop",
                "python conscious_agent/main.py --dashboard",
                "python conscious_agent/main.py --watch-once --no-ai-watch",
            ],
            links=[
                {"label": "Dashboard", "url": f"http://{settings.get('dashboard_host')}:{settings.get('dashboard_port')}"},
                {"label": "Chat Console", "url": f"http://{settings.get('dashboard_host')}:{settings.get('dashboard_port')}/chat-console"},
                {"label": "Action Center", "url": f"http://{settings.get('dashboard_host')}:{settings.get('dashboard_port')}/actions"},
            ],
        ))
    else:
        steps.append(_step(
            "rerun_after_fixes",
            "Re-run onboarding after fixes",
            "ready",
            "After handling the highest-priority steps, run the onboarding wizard again so it can stop complaining with evidence.",
            priority="medium",
            commands=["python conscious_agent/main.py --onboarding"],
        ))

    status_rank = {"critical": 0, "high": 1, "medium": 2, "normal": 3, "low": 4}
    actionable = [step for step in steps if step.get("status") in {"blocked", "needs_action", "ready"}]
    actionable_sorted = sorted(actionable, key=lambda item: status_rank.get(str(item.get("priority")), 3))
    next_step = actionable_sorted[0] if actionable_sorted else None

    counts = {
        "done": sum(1 for step in steps if step.get("status") == "done"),
        "needs_action": sum(1 for step in steps if step.get("status") == "needs_action"),
        "blocked": sum(1 for step in steps if step.get("status") == "blocked"),
        "optional": sum(1 for step in steps if step.get("status") == "optional"),
        "ready": sum(1 for step in steps if step.get("status") == "ready"),
    }
    if counts["blocked"]:
        overall = "blocked"
    elif counts["needs_action"]:
        overall = "needs_action"
    elif setup_report.get("status") == "ready":
        overall = "ready"
    else:
        overall = "attention_needed"

    run = {
        "id": _run_id(),
        "version": ONBOARDING_VERSION,
        "created_at": _now(),
        "status": overall,
        "setup_report_id": setup_report.get("id"),
        "setup_status": setup_report.get("status"),
        "summary": _summary(overall, counts, next_step),
        "counts": counts,
        "next_step": next_step,
        "steps": steps,
        "settings_snapshot": {
            "dashboard_host": settings.get("dashboard_host"),
            "dashboard_port": settings.get("dashboard_port"),
            "api_host": settings.get("api_host"),
            "api_port": settings.get("api_port"),
            "local_model": settings.get("local_model"),
            "embed_model": settings.get("embed_model"),
            "desktop_real_tray_enabled": settings.get("desktop_real_tray_enabled"),
            "desktop_launch_dashboard_on_start": settings.get("desktop_launch_dashboard_on_start"),
        },
        "safety": "Onboarding is advisory. It saves this runbook and setup report but does not install packages, change settings, start services, approve actions, apply patches, rollback files, or edit project files.",
    }
    if save:
        save_onboarding_run(run)
    return run


def _summary(status: str, counts: dict[str, int], next_step: dict[str, Any] | None) -> str:
    if status == "ready":
        return "Onboarding looks ready. Start the dashboard or desktop shell and begin using the action center or chat console. Civilization shambles forward."
    if status == "blocked":
        title = next_step.get("title") if next_step else "a blocked setup step"
        return f"Onboarding is blocked by {title}. Fix that first before chasing shinier buttons."
    if status == "needs_action":
        title = next_step.get("title") if next_step else "a setup step"
        return f"Onboarding needs action. Next recommended step: {title}."
    return f"Onboarding needs attention: {counts.get('needs_action', 0)} action step(s), {counts.get('blocked', 0)} blocked step(s), {counts.get('optional', 0)} optional step(s)."


def save_onboarding_run(run: dict[str, Any]) -> None:
    _ensure_onboarding_dir()
    path = ONBOARDING_RUNS_DIR / f"{run.get('id')}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(run, file, indent=2)


def list_onboarding_runs() -> list[dict[str, Any]]:
    _ensure_onboarding_dir()
    runs: list[dict[str, Any]] = []
    for path in ONBOARDING_RUNS_DIR.glob("onboarding_*.json"):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                runs.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(runs, key=lambda item: item.get("created_at", ""), reverse=True)


def resolve_onboarding_run_id(run_id: str) -> str | None:
    run_id = (run_id or "latest").strip()
    runs = list_onboarding_runs()
    if not runs:
        return None
    if run_id == "latest":
        return str(runs[0].get("id"))
    if run_id.startswith("latest-"):
        wanted = run_id.replace("latest-", "", 1)
        for run in runs:
            if run.get("status") == wanted:
                return str(run.get("id"))
        return None
    for run in runs:
        if run.get("id") == run_id:
            return run_id
    return None


def load_onboarding_run(run_id: str) -> dict[str, Any] | None:
    resolved = resolve_onboarding_run_id(run_id)
    if not resolved:
        return None
    path = ONBOARDING_RUNS_DIR / f"{resolved}.json"
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def onboarding_run_text(run: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# Onboarding run: {run.get('id')}",
        f"Version: {run.get('version')}",
        f"Created: {run.get('created_at')}",
        f"Status: {run.get('status')}",
        f"Setup report: {run.get('setup_report_id')} ({run.get('setup_status')})",
        f"Summary: {run.get('summary')}",
        "",
        "## Counts",
    ]
    counts = run.get("counts") or {}
    for key in ("blocked", "needs_action", "ready", "optional", "done"):
        lines.append(f"- {key}: {counts.get(key, 0)}")

    next_step = run.get("next_step") or {}
    if next_step:
        lines.extend(["", "## Next recommended step", f"{next_step.get('title')} [{next_step.get('status')} / {next_step.get('priority')}]"])
        lines.append(str(next_step.get("description", "")))
        for command in next_step.get("commands", []):
            lines.append(f"command: {command}")

    lines.extend(["", "## Steps"])
    for step in run.get("steps", []):
        lines.append(f"- [{step.get('status')}] {step.get('title')} ({step.get('priority')})")
        lines.append(f"  {step.get('description')}")
        for suggestion in step.get("suggestions", []):
            lines.append(f"  suggestion: {suggestion}")
        for command in step.get("commands", []):
            lines.append(f"  command: {command}")
        for link in step.get("links", []):
            lines.append(f"  link: {link.get('label')}: {link.get('url')}")

    if full:
        setup_report_id = run.get("setup_report_id")
        setup_report = load_setup_report(str(setup_report_id)) if setup_report_id else None
        if setup_report:
            lines.extend(["", "## Setup report details", setup_report_text(setup_report, full=True)])
        lines.extend(["", "## Settings snapshot", json.dumps(run.get("settings_snapshot", {}), indent=2, default=str)])
        lines.extend(["", "## Raw onboarding run", json.dumps(run, indent=2, default=str)])

    return "\n".join(lines)


def print_onboarding_run(full: bool = False, refresh_setup: bool = True) -> None:
    run = build_onboarding_run(save=True, refresh_setup=refresh_setup)
    print(onboarding_run_text(run, full=full))


def print_onboarding_runs() -> None:
    runs = list_onboarding_runs()
    if not runs:
        print("No onboarding runs saved yet.")
        return
    for run in runs:
        counts = run.get("counts") or {}
        print(
            f"{run.get('id')} | {run.get('status')} | "
            f"blocked={counts.get('blocked', 0)} action={counts.get('needs_action', 0)} optional={counts.get('optional', 0)} | {run.get('created_at')}"
        )


def print_saved_onboarding_run(run_id: str = "latest", full: bool = False) -> None:
    run = load_onboarding_run(run_id)
    if not run:
        print(f"Onboarding run not found: {run_id}")
        return
    print(onboarding_run_text(run, full=full))
