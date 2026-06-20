from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from settings_manager import load_settings
from task_queue import list_tasks

WORKSPACE_ORCHESTRATION_VERSION = "30.0"
WORKSPACES_DIR = DATA_DIR / "workspaces"
PROJECTS_FILE = WORKSPACES_DIR / "projects.json"
ACTIVE_PROJECT_FILE = WORKSPACES_DIR / "active_project.json"
COMMAND_PROFILES_DIR = WORKSPACES_DIR / "command_profiles"
TIMELINE_FILE = WORKSPACES_DIR / "timeline.json"
PATCH_WORKSPACE_DIR = DATA_DIR / "patch_workspace"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"

DEFAULT_TEST_COMMANDS = [
    "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
    "python conscious_agent/main.py --doctor",
    "python conscious_agent/main.py --stabilization-checkpoint --stabilization-full",
    "python tools/smoke_check.py",
]

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "eidolon": {
        "id": "eidolon",
        "language": "Python",
        "allowed_compile_commands": ["python -m py_compile conscious_agent/*.py tools/smoke_check.py"],
        "allowed_test_commands": DEFAULT_TEST_COMMANDS,
        "forbidden_commands": ["rm -rf", "del /s", "format", "git push --force"],
        "package_install_requires_approval": True,
        "destructive_commands_require_approval": True,
        "shell_commands_require_approval": True,
    },
    "default_python": {
        "id": "default_python",
        "language": "Python",
        "allowed_compile_commands": ["python -m py_compile"],
        "allowed_test_commands": ["python -m pytest", "python -m unittest"],
        "forbidden_commands": ["rm -rf", "del /s", "format"],
        "package_install_requires_approval": True,
        "destructive_commands_require_approval": True,
        "shell_commands_require_approval": True,
    },
    "default_node": {
        "id": "default_node",
        "language": "Node",
        "allowed_compile_commands": ["npm run build"],
        "allowed_test_commands": ["npm test", "npm run lint"],
        "forbidden_commands": ["rm -rf", "del /s", "format", "npm publish"],
        "package_install_requires_approval": True,
        "destructive_commands_require_approval": True,
        "shell_commands_require_approval": True,
    },
    "default_java": {
        "id": "default_java",
        "language": "Java",
        "allowed_compile_commands": ["mvn test", "gradle test"],
        "allowed_test_commands": ["mvn test", "gradle test"],
        "forbidden_commands": ["rm -rf", "del /s", "format"],
        "package_install_requires_approval": True,
        "destructive_commands_require_approval": True,
        "shell_commands_require_approval": True,
    },
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _ensure_dirs() -> None:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    COMMAND_PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return cleaned or "project"


def _root_token(path_value: str | None) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return "."
    if raw in {".", "$ROOT_DIR", "{ROOT_DIR}", "ROOT_DIR"}:
        return "."
    try:
        path = Path(raw)
        if path.resolve() == ROOT_DIR.resolve():
            return "."
    except OSError:
        pass
    return raw


def resolve_project_root(project: dict[str, Any] | str | None = None) -> Path:
    if isinstance(project, dict):
        raw = str(project.get("root") or project.get("path") or ".")
    elif project is None:
        raw = "."
    else:
        raw = str(project)
    if raw in {"", ".", "$ROOT_DIR", "{ROOT_DIR}", "ROOT_DIR"}:
        return ROOT_DIR
    path = Path(raw)
    if not path.is_absolute():
        return (ROOT_DIR / path).resolve()
    return path


def _default_project() -> dict[str, Any]:
    settings = load_settings()
    return {
        "id": "eidolon",
        "name": "Eidolon",
        "root": ".",
        "root_resolves_from": "ROOT_DIR",
        "version": str(settings.get("settings_version", "15.0")),
        "language": "Python",
        "framework_type": "local_cli_dashboard_api",
        "readme_path": "README_NEXT_STEPS.md",
        "test_commands": DEFAULT_TEST_COMMANDS,
        "safe_command_profile": "eidolon",
        "last_health_status": "unknown",
        "priority": "high",
        "safe_to_modify": True,
        "last_updated_for": f"v{settings.get('settings_version', WORKSPACE_ORCHESTRATION_VERSION)}",
        "current_milestone": f"v{settings.get('settings_version', WORKSPACE_ORCHESTRATION_VERSION)} Assisted Self-Improvement Release",
        "registered_at": _now(),
        "updated_at": _now(),
    }


def _normalize_project(project: dict[str, Any]) -> dict[str, Any]:
    base = _default_project() if str(project.get("id", "")).lower() == "eidolon" else {}
    merged = {**base, **project}
    name = str(merged.get("name") or merged.get("id") or "Project")
    merged["id"] = str(merged.get("id") or _slug(name))
    merged["name"] = name
    merged["root"] = _root_token(str(merged.get("root") or merged.get("path") or "."))
    if merged["root"] == ".":
        merged["root_resolves_from"] = "ROOT_DIR"
    merged.setdefault("version", "unknown")
    merged.setdefault("language", "unknown")
    merged.setdefault("framework_type", "unknown")
    merged.setdefault("readme_path", "README_NEXT_STEPS.md")
    merged.setdefault("test_commands", DEFAULT_TEST_COMMANDS if merged["id"] == "eidolon" else [])
    merged.setdefault("safe_command_profile", "eidolon" if merged["id"] == "eidolon" else "default_python")
    merged.setdefault("last_health_status", "unknown")
    merged.setdefault("priority", "medium")
    merged.setdefault("safe_to_modify", merged["id"] == "eidolon")
    merged.setdefault("registered_at", _now())
    merged["updated_at"] = _now()
    return merged


def load_workspace_projects(repair: bool = False) -> list[dict[str, Any]]:
    raw = _read_json(PROJECTS_FILE, {})
    projects = raw.get("projects", raw) if isinstance(raw, dict) else raw
    if not isinstance(projects, list) or not projects:
        projects = [_default_project()]
    normalized = [_normalize_project(item) for item in projects if isinstance(item, dict)]
    if not any(item.get("id") == "eidolon" for item in normalized):
        normalized.insert(0, _default_project())
    if repair:
        _write_json(PROJECTS_FILE, {"version": WORKSPACE_ORCHESTRATION_VERSION, "updated_at": _now(), "projects": normalized})
        active = _read_json(ACTIVE_PROJECT_FILE, {})
        active_payload = {"version": f"v{WORKSPACE_ORCHESTRATION_VERSION}", "active_project_id": str(active.get("active_project_id") or "eidolon") if isinstance(active, dict) else "eidolon", "updated_at": _now(), "last_updated_for": f"v{WORKSPACE_ORCHESTRATION_VERSION}", "current_milestone": f"v{WORKSPACE_ORCHESTRATION_VERSION} Assisted Self-Improvement Release"}
        if not isinstance(active, dict) or active.get("version") != f"v{WORKSPACE_ORCHESTRATION_VERSION}" or active.get("last_updated_for") != f"v{WORKSPACE_ORCHESTRATION_VERSION}":
            _write_json(ACTIVE_PROJECT_FILE, active_payload)
    return normalized


def active_workspace_project_id(default: str = "eidolon") -> str:
    active = _read_json(ACTIVE_PROJECT_FILE, {})
    if isinstance(active, dict):
        return str(active.get("active_project_id") or default)
    return default


def _timeline_event(event_type: str, detail: dict[str, Any], save: bool = True) -> dict[str, Any]:
    event = {"timestamp": _now(), "type": event_type, **detail}
    if save:
        current = _read_json(TIMELINE_FILE, [])
        if not isinstance(current, list):
            current = []
        current.append(event)
        _write_json(TIMELINE_FILE, current[-500:])
    return event


def build_command_profiles(save: bool = True) -> dict[str, Any]:
    _ensure_dirs()
    rows: list[dict[str, Any]] = []
    if save:
        for profile_id, profile in DEFAULT_PROFILES.items():
            path = COMMAND_PROFILES_DIR / f"{profile_id}.json"
            existing = _read_json(path, {})
            payload = {**profile, **existing, "id": profile_id, "updated_at": _now()}
            _write_json(path, payload)
    for path in sorted(COMMAND_PROFILES_DIR.glob("*.json")):
        profile = _read_json(path, {})
        if isinstance(profile, dict):
            rows.append({
                "id": profile.get("id", path.stem),
                "path": str(path.relative_to(ROOT_DIR)),
                "language": profile.get("language", "unknown"),
                "allowed_test_count": len(profile.get("allowed_test_commands", [])),
                "requires_approval_for_packages": bool(profile.get("package_install_requires_approval", True)),
                "requires_approval_for_destructive": bool(profile.get("destructive_commands_require_approval", True)),
            })
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "status": "pass" if rows else "warn",
        "ok": True,
        "profile_count": len(rows),
        "rows": rows,
        "message": f"Command profiles ready for {len(rows)} profile(s).",
    }


def build_project_registry(repair: bool = False) -> dict[str, Any]:
    projects = load_workspace_projects(repair=repair)
    if repair:
        build_command_profiles(save=True)
        _timeline_event("registry_checked", {"project_count": len(projects)}, save=True)
    active_id = active_workspace_project_id()
    rows = []
    warnings = []
    for project in projects:
        root = resolve_project_root(project)
        if not root.exists():
            warnings.append(f"Project root does not exist for {project.get('id')}: {root}")
        rows.append({**project, "resolved_root": str(root), "root_exists": root.exists(), "active": project.get("id") == active_id})
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "status": "warn" if warnings else "pass",
        "ok": True,
        "workspace_dir": str(WORKSPACES_DIR.relative_to(ROOT_DIR)),
        "active_project_id": active_id,
        "project_count": len(rows),
        "rows": rows,
        "warnings": warnings,
        "message": f"Workspace registry contains {len(rows)} project(s); active project is {active_id}.",
    }


def register_project(name: str, root: str | None = None, version: str = "unknown", language: str = "unknown", framework_type: str = "unknown", readme_path: str = "README_NEXT_STEPS.md", test_commands: list[str] | None = None, safe_command_profile: str = "default_python", project_id: str | None = None) -> dict[str, Any]:
    projects = load_workspace_projects(repair=True)
    pid = project_id or _slug(name)
    new_project = _normalize_project({
        "id": pid,
        "name": name,
        "root": _root_token(root or "."),
        "version": version,
        "language": language,
        "framework_type": framework_type,
        "readme_path": readme_path,
        "test_commands": test_commands or [],
        "safe_command_profile": safe_command_profile,
        "priority": "medium" if pid != "eidolon" else "high",
        "safe_to_modify": pid == "eidolon",
    })
    replaced = False
    for idx, project in enumerate(projects):
        if project.get("id") == pid:
            projects[idx] = {**project, **new_project, "registered_at": project.get("registered_at", new_project["registered_at"]), "updated_at": _now()}
            replaced = True
            break
    if not replaced:
        projects.append(new_project)
    _write_json(PROJECTS_FILE, {"version": WORKSPACE_ORCHESTRATION_VERSION, "updated_at": _now(), "projects": projects})
    _timeline_event("project_registered", {"project_id": pid, "name": name, "replaced": replaced}, save=True)
    return build_project_registry(repair=False)


def set_active_workspace_project(project_id: str) -> dict[str, Any]:
    projects = load_workspace_projects(repair=True)
    if not any(project.get("id") == project_id for project in projects):
        return {"version": WORKSPACE_ORCHESTRATION_VERSION, "checked_at": _now(), "status": "fail", "ok": False, "message": f"Unknown workspace project: {project_id}", "project_id": project_id}
    _write_json(ACTIVE_PROJECT_FILE, {"version": WORKSPACE_ORCHESTRATION_VERSION, "active_project_id": project_id, "updated_at": _now()})
    _timeline_event("active_project_set", {"project_id": project_id}, save=True)
    return build_project_registry(repair=False)


def _readme_exists(project: dict[str, Any]) -> bool:
    return (resolve_project_root(project) / str(project.get("readme_path", "README_NEXT_STEPS.md"))).exists()


def build_project_health(project_id: str = "eidolon", all_projects: bool = False) -> dict[str, Any]:
    registry = build_project_registry(repair=True)
    projects = registry.get("rows", [])
    rows = []
    for project in projects:
        if not all_projects and project.get("id") != project_id:
            continue
        root = resolve_project_root(project)
        readme_ok = _readme_exists(project)
        tests = project.get("test_commands", [])
        profile = COMMAND_PROFILES_DIR / f"{project.get('safe_command_profile', 'default_python')}.json"
        blockers = []
        if not root.exists():
            blockers.append("project root missing")
        if not readme_ok:
            blockers.append("README missing")
        if not profile.exists():
            blockers.append("safe command profile missing")
        status = "blocked" if blockers else "pass" if tests else "warn"
        rows.append({
            "id": project.get("id"),
            "name": project.get("name"),
            "root": str(root),
            "root_exists": root.exists(),
            "readme_exists": readme_ok,
            "test_command_count": len(tests),
            "safe_command_profile": project.get("safe_command_profile"),
            "safe_command_profile_exists": profile.exists(),
            "safe_to_modify": bool(project.get("safe_to_modify")),
            "status": status,
            "blockers": blockers,
        })
    counts = Counter(row["status"] for row in rows)
    overall = "blocked" if counts.get("blocked") else "warn" if counts.get("warn") else "pass"
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": overall if rows else "warn",
        "ok": not counts.get("blocked"),
        "all_projects": all_projects,
        "rows": rows,
        "counts": dict(counts),
        "message": f"Checked health for {len(rows)} project(s).",
    }


def build_workspace_dependency_map(project_id: str = "eidolon") -> dict[str, Any]:
    projects = load_workspace_projects(repair=True)
    rows = []
    for project in projects:
        root = resolve_project_root(project)
        text = ""
        readme = root / str(project.get("readme_path", "README_NEXT_STEPS.md"))
        if readme.exists():
            try:
                text = readme.read_text(encoding="utf-8")[:20000]
            except OSError:
                text = ""
        references = []
        for other in projects:
            if other.get("id") != project.get("id") and str(other.get("name", "")).lower() in text.lower():
                references.append(other.get("id"))
        rows.append({
            "project_id": project.get("id"),
            "root": str(root),
            "shared_root_with": [other.get("id") for other in projects if other is not project and resolve_project_root(other) == root],
            "readme_references": references,
            "configured_dependency_count": len(project.get("dependencies", [])) if isinstance(project.get("dependencies"), list) else 0,
            "risky_coupling": bool(references or project.get("dependencies")),
        })
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if any(row.get("risky_coupling") for row in rows) else "pass",
        "ok": True,
        "rows": rows,
        "message": f"Mapped dependency/coupling hints for {len(rows)} project(s).",
    }


def build_workspace_task_inbox(project_id: str = "eidolon") -> dict[str, Any]:
    projects = load_workspace_projects(repair=False)
    health = build_project_health(project_id=project_id, all_projects=True)
    health_by_id = {row.get("id"): row for row in health.get("rows", [])}
    rows = []
    priority_value = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    for project in projects:
        pid = str(project.get("id"))
        tasks = list_tasks(project=pid, include_cancelled=False)
        usable = [task for task in tasks if str(task.get("status", "planned")).lower() not in {"done", "completed", "cancelled", "failed"}]
        if not usable and pid == "eidolon":
            usable = [{"id": "synthetic_workspace_health_task", "title": "Review workspace health and README state", "priority": "low", "status": "planned", "risk": "low"}]
        for task in usable[:10]:
            blocked = bool(health_by_id.get(pid, {}).get("blockers")) or str(task.get("status", "")).lower() == "blocked"
            priority = str(task.get("priority", "medium")).lower()
            rows.append({
                "project_id": pid,
                "project_name": project.get("name"),
                "task_id": task.get("id"),
                "task_title": task.get("title", task.get("name", "[untitled]")),
                "priority": priority,
                "priority_score": priority_value.get(priority, 20),
                "risk": task.get("risk", task.get("risk_level", "medium")),
                "blocked": blocked,
                "needs_ai": bool(task.get("needs_ai", task.get("requires_ai", False))),
                "can_run_offline": not bool(task.get("requires_ai", False)),
                "recommended_action": "unblock project" if blocked else "prepare context bundle",
            })
    rows.sort(key=lambda row: (row.get("blocked", False), -int(row.get("priority_score", 0)), str(row.get("project_id"))))
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if not rows else "pass",
        "ok": True,
        "rows": rows,
        "selected": next((row for row in rows if not row.get("blocked")), rows[0] if rows else {}),
        "message": f"Workspace task inbox contains {len(rows)} task row(s).",
    }


def _patch_workspace_dirty() -> list[str]:
    dirty = []
    for name in ["current_plan.json", "proposed_changes.json", "validation_report.json"]:
        if (PATCH_WORKSPACE_DIR / name).exists():
            dirty.append(name)
    latest = _read_json(PATCH_WORKSPACE_DIR / "latest_apply_report.json", {})
    if isinstance(latest, dict) and latest.get("status") not in {None, "", "applied"}:
        dirty.append("latest_apply_report_not_applied")
    return dirty


def switch_workspace_project(project_id: str, force: bool = False) -> dict[str, Any]:
    dirty = _patch_workspace_dirty()
    if dirty and not force:
        return {
            "version": WORKSPACE_ORCHESTRATION_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "blocked",
            "ok": False,
            "dirty_workspace_items": dirty,
            "message": "Project switch blocked because patch workspace state exists. Clear, verify, or use force only when you actually mean it.",
        }
    report = set_active_workspace_project(project_id)
    if report.get("ok") is not False:
        _timeline_event("project_switched", {"project_id": project_id, "forced": force}, save=True)
    return report


def build_project_context(project_id: str = "eidolon") -> dict[str, Any]:
    registry = build_project_registry(repair=False)
    project = next((row for row in registry.get("rows", []) if row.get("id") == project_id), registry.get("rows", [{}])[0] if registry.get("rows") else {})
    health = build_project_health(project_id=project_id, all_projects=False)
    dependency_map = build_workspace_dependency_map(project_id=project_id)
    task_inbox = build_workspace_task_inbox(project_id=project_id)
    try:
        from project_intelligence import build_test_plan, build_patch_risk, build_project_memory_index

        test_plan = build_test_plan(project_id=project_id)
        risk = build_patch_risk(project_id=project_id)
        memory = build_project_memory_index(project_id=project_id)
    except Exception as error:
        test_plan = {"status": "warn", "ok": True, "commands": [], "message": f"Test plan unavailable: {error}"}
        risk = {"status": "warn", "ok": True, "message": f"Risk unavailable: {error}"}
        memory = {"status": "warn", "ok": True, "message": f"Memory unavailable: {error}"}
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if health.get("status") == "blocked" else "pass",
        "ok": health.get("ok", True),
        "project": project,
        "health": health,
        "dependency_map": dependency_map,
        "task_inbox_selection": task_inbox.get("selected"),
        "test_plan": test_plan,
        "risk_profile": risk,
        "memory_index": memory,
        "message": f"Built context bundle for {project_id}.",
    }


def build_workspace_timeline(limit: int = 50, save_if_missing: bool = False) -> dict[str, Any]:
    events = _read_json(TIMELINE_FILE, [])
    if not isinstance(events, list):
        events = []
    if not events and save_if_missing:
        _timeline_event("timeline_initialized", {"message": "Workspace timeline initialized."}, save=True)
        events = _read_json(TIMELINE_FILE, [])
    return {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "status": "pass",
        "ok": True,
        "event_count": len(events),
        "rows": events[-limit:],
        "message": f"Workspace timeline contains {len(events)} event(s).",
    }


def build_workspace_dev_loop(project_id: str = "eidolon", live: bool = False, save_timeline: bool = False) -> dict[str, Any]:
    registry = build_project_registry(repair=False)
    health = build_project_health(project_id=project_id, all_projects=True)
    inbox = build_workspace_task_inbox(project_id=project_id)
    selected = inbox.get("selected") or {}
    selected_project_id = str(selected.get("project_id") or active_workspace_project_id(project_id))
    context = build_project_context(project_id=selected_project_id)
    try:
        from controlled_build_cycle import build_patch_plan, stage_controlled_patch, preview_staged_diff

        plan = build_patch_plan(project_id=selected_project_id, target_version="26.0", save=False)
        staged = stage_controlled_patch(project_id=selected_project_id, create_plan_if_missing=True, save=False)
        diff = preview_staged_diff(project_id=selected_project_id, stage_if_missing=False, save=False)
    except Exception as error:
        plan = {"status": "warn", "ok": True, "message": f"Patch plan preview unavailable: {error}"}
        staged = {"status": "warn", "ok": True, "message": f"Stage preview unavailable: {error}"}
        diff = {"status": "warn", "ok": True, "message": f"Diff preview unavailable: {error}"}
    blocked = []
    if live:
        blocked.append("v12.0 workspace dev loop is preview-only; it does not apply patches.")
    if not selected:
        blocked.append("No workspace task was selected.")
    if context.get("status") == "blocked":
        blocked.append("Selected project context is blocked.")
    report = {
        "version": WORKSPACE_ORCHESTRATION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if blocked else "preview_complete",
        "ok": not blocked,
        "live": False,
        "modifies_files": False,
        "registry": registry,
        "health": health,
        "task_inbox": inbox,
        "selected_project_id": selected_project_id,
        "context": context,
        "patch_plan_preview": plan,
        "stage_preview": staged,
        "diff_preview": diff,
        "blocked_reasons": blocked,
        "message": "Workspace dev loop scanned projects, ranked tasks, loaded context, prepared patch previews, and stopped before mutation.",
    }
    _timeline_event("workspace_dev_loop_preview", {"selected_project_id": selected_project_id, "status": report["status"]}, save=save_timeline)
    return report


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    for key in ["warnings", "blocked_reasons", "dirty_workspace_items"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:30]:
            if isinstance(row, dict):
                name = row.get("id") or row.get("project_id") or row.get("task_id") or row.get("type") or row.get("name") or "row"
                status = row.get("status") or row.get("priority") or "info"
                message = row.get("message") or row.get("task_title") or row.get("name") or row.get("root") or ""
                lines.append(f"- {str(status).upper()} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def project_registry_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.1 Project Registry", report or build_project_registry(repair=False), full=full)


def project_health_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.2 Per-Project Health", report or build_project_health(all_projects=True), full=full)


def command_profiles_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.3 Project Command Profiles", report or build_command_profiles(save=False), full=full)


def workspace_dependency_map_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.4 Cross-Project Dependency Map", report or build_workspace_dependency_map(), full=full)


def workspace_task_inbox_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.5 Multi-Project Task Inbox", report or build_workspace_task_inbox(), full=full)


def switch_project_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.6 Safe Project Switching", report or build_project_registry(repair=False), full=full)


def project_context_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.7 Project Context Bundle", report or build_project_context(), full=full)


def workspace_timeline_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.8 Workspace Timeline", report or build_workspace_timeline(), full=full)


def workspace_dev_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_workspace_dev_loop()
    lines = _generic_text("Eidolon v11.0 Workspace-Orchestrated Development Loop", report, full=False).splitlines()
    lines.extend(["", "## Selected", f"- Project: {report.get('selected_project_id')}", f"- Modifies files: {report.get('modifies_files')}"])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_project_registry(full: bool = False, json_output: bool = False) -> None:
    report = build_project_registry(repair=True)
    _json_print(report) if json_output else print(project_registry_text(report, full=full))


def print_register_project(name: str, root: str | None = None, version: str = "unknown", language: str = "unknown", framework_type: str = "unknown", readme_path: str = "README_NEXT_STEPS.md", test_commands: list[str] | None = None, profile: str = "default_python", project_id: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = register_project(name=name, root=root, version=version, language=language, framework_type=framework_type, readme_path=readme_path, test_commands=test_commands, safe_command_profile=profile, project_id=project_id)
    _json_print(report) if json_output else print(project_registry_text(report, full=full))


def print_set_active_workspace_project(project_id: str, full: bool = False, json_output: bool = False) -> None:
    report = set_active_workspace_project(project_id)
    _json_print(report) if json_output else print(project_registry_text(report, full=full))


def print_project_health(project_id: str = "eidolon", all_projects: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_project_health(project_id=project_id, all_projects=all_projects)
    _json_print(report) if json_output else print(project_health_text(report, full=full))


def print_command_profiles(full: bool = False, json_output: bool = False) -> None:
    report = build_command_profiles(save=True)
    _json_print(report) if json_output else print(command_profiles_text(report, full=full))


def print_workspace_dependency_map(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_dependency_map(project_id=project_id)
    _json_print(report) if json_output else print(workspace_dependency_map_text(report, full=full))


def print_workspace_task_inbox(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_task_inbox(project_id=project_id)
    _json_print(report) if json_output else print(workspace_task_inbox_text(report, full=full))


def print_switch_workspace_project(project_id: str, force: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = switch_workspace_project(project_id=project_id, force=force)
    _json_print(report) if json_output else print(switch_project_text(report, full=full))


def print_project_context(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_project_context(project_id=project_id)
    _json_print(report) if json_output else print(project_context_text(report, full=full))


def print_workspace_timeline(full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_timeline()
    _json_print(report) if json_output else print(workspace_timeline_text(report, full=full))


def print_workspace_dev_loop(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_dev_loop(project_id=project_id, live=False)
    _json_print(report) if json_output else print(workspace_dev_loop_text(report, full=full))
