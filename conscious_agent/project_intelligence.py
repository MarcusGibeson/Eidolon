from __future__ import annotations

import ast
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from settings_manager import load_settings
from task_queue import list_tasks

PROJECT_INTELLIGENCE_VERSION = "15.0"
WORKSPACES_DIR = DATA_DIR / "workspaces"
WORKSPACE_PROJECTS_FILE = WORKSPACES_DIR / "projects.json"
ACTIVE_PROJECT_FILE = WORKSPACES_DIR / "active_project.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"
PATCH_WORKSPACE_DIR = DATA_DIR / "patch_workspace"
CURRENT_PLAN = PATCH_WORKSPACE_DIR / "current_plan.json"
PROPOSED_CHANGES = PATCH_WORKSPACE_DIR / "proposed_changes.json"
LATEST_APPLY_REPORT = PATCH_WORKSPACE_DIR / "latest_apply_report.json"
LATEST_DRY_RUN_APPLY_REPORT = PATCH_WORKSPACE_DIR / "latest_dry_run_apply_report.json"
LATEST_ROLLBACK_REPORT = PATCH_WORKSPACE_DIR / "latest_rollback_report.json"
REPORTS_DIR = DATA_DIR / "controlled_build_reports"

IGNORE_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "chroma"}
CORE_MODULE_HINTS = {
    "main.py": "CLI entrypoint and command dispatch",
    "api_server.py": "Local JSON API routing",
    "dashboard.py": "Local dashboard pages and forms",
    "controlled_build_cycle.py": "Controlled self-build staging, apply, verify, rollback, and supervised loop",
    "project_intelligence.py": "Codebase map, dependency planning, test planning, risk analysis, memory index, and workspace review",
    "operational_readiness.py": "Doctor, repair suggestions, confidence, hardening, and project readiness reports",
    "stabilization_checkpoint.py": "End-to-end stabilization checkpoint",
    "command_runner.py": "Safe command allowlist and command execution history",
    "settings_manager.py": "Settings schema, health checks, and settings display",
    "task_queue.py": "Canonical task queue",
    "task_lifecycle.py": "Task lifecycle derivation",
    "task_recovery.py": "Task recovery and retry reporting",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _status_from(counts: Counter[str]) -> str:
    if counts.get("blocked", 0) or counts.get("fail", 0):
        return "fail"
    if counts.get("warn", 0):
        return "warn"
    return "pass"


def _project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT_DIR)
        if any(part in IGNORE_PARTS for part in rel.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: str(item.relative_to(ROOT_DIR)).lower())


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT_DIR)).replace("\\", "/")


def _python_imports(path: Path) -> list[str]:
    text = _read_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return sorted(imports)


def _cli_flags() -> list[str]:
    text = _read_text(ROOT_DIR / "conscious_agent" / "main.py")
    return sorted(set(re.findall(r'"(--[a-zA-Z0-9][a-zA-Z0-9_-]*)"', text)))


def _api_routes() -> list[str]:
    text = _read_text(ROOT_DIR / "conscious_agent" / "api_server.py")
    routes = set(re.findall(r'"((?:GET|POST|PUT|DELETE) /api[^"\n]+)"', text))
    routes.update(re.findall(r'((?:GET|POST) /api/[a-zA-Z0-9_/?=&{}.-]+)', text))
    return sorted(routes)


def _dashboard_routes() -> list[str]:
    text = _read_text(ROOT_DIR / "conscious_agent" / "dashboard.py")
    routes = set(re.findall(r'"(/[a-zA-Z0-9_-]+)"', text))
    routes.update(re.findall(r"'(/[a-zA-Z0-9_-]+)'", text))
    return sorted(route for route in routes if not route.startswith("/api"))


def build_codebase_map(project_id: str = "eidolon") -> dict[str, Any]:
    files = _project_files()
    extension_counts = Counter(path.suffix or "[none]" for path in files)
    py_files = [path for path in files if path.suffix == ".py"]
    modules: list[dict[str, Any]] = []
    for path in sorted((ROOT_DIR / "conscious_agent").glob("*.py")):
        rel = _relative(path)
        modules.append({
            "path": rel,
            "role": CORE_MODULE_HINTS.get(path.name, "Support module"),
            "imports": _python_imports(path),
            "line_count": len(_read_text(path).splitlines()),
        })
    cli_flags = _cli_flags()
    dashboard_routes = _dashboard_routes()
    api_routes = _api_routes()
    data_files = sorted(_relative(path) for path in files if _relative(path).startswith("data/"))[:200]
    risky_files = [
        "conscious_agent/main.py",
        "conscious_agent/api_server.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/command_runner.py",
        "conscious_agent/settings_manager.py",
        "conscious_agent/controlled_build_cycle.py",
        "conscious_agent/stabilization_checkpoint.py",
        "conscious_agent/operational_readiness.py",
    ]
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass",
        "ok": True,
        "root": str(ROOT_DIR),
        "file_count": len(files),
        "python_file_count": len(py_files),
        "extension_counts": dict(sorted(extension_counts.items())),
        "major_modules": modules,
        "cli_command_count": len(cli_flags),
        "cli_commands": cli_flags,
        "dashboard_route_count": len(dashboard_routes),
        "dashboard_routes": dashboard_routes,
        "api_route_count": len(api_routes),
        "api_routes": api_routes,
        "data_files_sample": data_files,
        "risky_files": risky_files,
        "message": f"Mapped {len(files)} file(s), {len(py_files)} Python file(s), {len(cli_flags)} CLI flag(s), {len(api_routes)} API route hint(s), and {len(dashboard_routes)} dashboard route(s).",
    }


def _infer_files_from_task(task: dict[str, Any]) -> list[str]:
    text = json.dumps(task, default=str).lower()
    files: list[str] = []
    mapping = [
        ("dashboard", "conscious_agent/dashboard.py"),
        ("api", "conscious_agent/api_server.py"),
        ("route", "conscious_agent/api_server.py"),
        ("cli", "conscious_agent/main.py"),
        ("command", "conscious_agent/main.py"),
        ("settings", "conscious_agent/settings_manager.py"),
        ("safe command", "conscious_agent/command_runner.py"),
        ("command runner", "conscious_agent/command_runner.py"),
        ("controlled", "conscious_agent/controlled_build_cycle.py"),
        ("rollback", "conscious_agent/controlled_build_cycle.py"),
        ("readme", "README_NEXT_STEPS.md"),
        ("task", "conscious_agent/task_queue.py"),
        ("lifecycle", "conscious_agent/task_lifecycle.py"),
        ("recovery", "conscious_agent/task_recovery.py"),
    ]
    for term, file_path in mapping:
        if term in text and file_path not in files:
            files.append(file_path)
    if not files:
        files.append("README_NEXT_STEPS.md")
    return files


def build_task_dependencies(project_id: str = "eidolon") -> dict[str, Any]:
    tasks = list_tasks(project=project_id, include_cancelled=False)
    rows: list[dict[str, Any]] = []
    for task in tasks[:50]:
        files = _infer_files_from_task(task)
        requires = ["README_NEXT_STEPS.md"]
        if any(path.startswith("conscious_agent/") for path in files):
            requires.extend(["python -m py_compile", "doctor", "smoke_check"])
        if "conscious_agent/api_server.py" in files:
            requires.append("api route review")
        if "conscious_agent/dashboard.py" in files:
            requires.append("dashboard route review")
        rows.append({
            "task_id": task.get("id"),
            "title": task.get("title", task.get("name", "[untitled]")),
            "status": task.get("status", "unknown"),
            "priority": task.get("priority", "medium"),
            "inferred_files": files,
            "dependency_checks": sorted(set(requires)),
            "readme_update_required": True,
        })
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if not rows else "pass",
        "ok": True,
        "task_count": len(tasks),
        "rows": rows,
        "message": f"Built dependency hints for {len(rows)} task row(s).",
    }


def _current_changed_files() -> list[str]:
    plan = _read_json(CURRENT_PLAN, {})
    proposed = _read_json(PROPOSED_CHANGES, {})
    files: list[str] = []
    if isinstance(plan, dict):
        files.extend(str(item) for item in plan.get("files_to_change", []) if item)
    if isinstance(proposed, dict):
        files.extend(str(row.get("path")) for row in proposed.get("changes", []) if row.get("path"))
    seen: set[str] = set()
    return [item for item in files if not (item in seen or seen.add(item))]


def _tests_for_files(files: list[str]) -> list[str]:
    tests = ["python -m py_compile conscious_agent/*.py tools/smoke_check.py"]
    if not files:
        tests.append("python conscious_agent/main.py --doctor")
    if any(path.endswith("main.py") for path in files):
        tests.extend([
            "python conscious_agent/main.py --status",
            "python conscious_agent/main.py --doctor",
            "python conscious_agent/main.py --stabilization-checkpoint --stabilization-full",
        ])
    if any("api_server.py" in path for path in files):
        tests.extend([
            "python conscious_agent/main.py --doctor",
            "python conscious_agent/main.py --codebase-map",
        ])
    if any("dashboard.py" in path for path in files):
        tests.extend([
            "python conscious_agent/main.py --codebase-map",
            "python conscious_agent/main.py --patch-review",
        ])
    if any("controlled_build_cycle.py" in path for path in files):
        tests.extend([
            "python conscious_agent/main.py --controlled-self-build --select-task",
            "python conscious_agent/main.py --controlled-self-build --plan-patch",
            "python conscious_agent/main.py --controlled-self-build --stage-patch",
            "python conscious_agent/main.py --controlled-self-build --preview-diff",
            "python conscious_agent/main.py --controlled-self-build --apply-staged-patch --dry-run",
            "python conscious_agent/main.py --readme-gate",
        ])
    if any("project_intelligence.py" in path for path in files):
        tests.extend([
            "python conscious_agent/main.py --codebase-map",
            "python conscious_agent/main.py --task-dependencies",
            "python conscious_agent/main.py --test-plan",
            "python conscious_agent/main.py --patch-risk",
            "python conscious_agent/main.py --patch-review",
            "python conscious_agent/main.py --project-memory-index",
            "python conscious_agent/main.py --workspace-status",
            "python conscious_agent/main.py --cross-project-task-review",
            "python conscious_agent/main.py --asymmetric-dev-loop",
        ])
    tests.extend(["python conscious_agent/main.py --readme-gate", "python tools/smoke_check.py"])
    seen: set[str] = set()
    return [item for item in tests if not (item in seen or seen.add(item))]


def build_test_plan(project_id: str = "eidolon", files: list[str] | None = None) -> dict[str, Any]:
    changed_files = files if files is not None else _current_changed_files()
    commands = _tests_for_files(changed_files)
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass",
        "ok": True,
        "files": changed_files,
        "commands": commands,
        "message": f"Generated {len(commands)} verification command(s) for {len(changed_files)} changed file hint(s).",
    }


def build_patch_risk(project_id: str = "eidolon") -> dict[str, Any]:
    files = _current_changed_files()
    proposed = _read_json(PROPOSED_CHANGES, {})
    factors: list[dict[str, Any]] = []
    score = 0
    high_files = {"conscious_agent/command_runner.py", "conscious_agent/settings_manager.py", "conscious_agent/controlled_build_cycle.py"}
    med_files = {"conscious_agent/main.py", "conscious_agent/api_server.py", "conscious_agent/dashboard.py", "conscious_agent/stabilization_checkpoint.py", "conscious_agent/operational_readiness.py"}
    for path in files:
        if path in high_files:
            score += 30
            factors.append({"path": path, "severity": "high", "reason": "guarded build/safety/settings surface"})
        elif path in med_files:
            score += 20
            factors.append({"path": path, "severity": "medium", "reason": "CLI/API/dashboard/readiness surface"})
        elif path == "README_NEXT_STEPS.md":
            score += 5
            factors.append({"path": path, "severity": "low", "reason": "documentation update"})
        else:
            score += 10
            factors.append({"path": path, "severity": "medium", "reason": "uncategorized project file"})
    if isinstance(proposed, dict):
        for row in proposed.get("changes", []):
            if row.get("action") == "delete":
                score += 50
                factors.append({"path": row.get("path"), "severity": "blocked", "reason": "deletion in proposed changes"})
    if len(files) > 5:
        score += 25
        factors.append({"path": "[patch]", "severity": "medium", "reason": "large multi-file change"})
    if files and "README_NEXT_STEPS.md" not in files:
        score += 20
        factors.append({"path": "README_NEXT_STEPS.md", "severity": "medium", "reason": "code/data changes need README update"})
    if any(factor.get("severity") == "blocked" for factor in factors):
        risk = "BLOCKED"
    elif score >= 60:
        risk = "HIGH"
    elif score >= 25:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "fail" if risk == "BLOCKED" else "warn" if risk in {"HIGH", "MEDIUM"} else "pass",
        "ok": risk != "BLOCKED",
        "risk": risk,
        "score": score,
        "files": files,
        "factors": factors,
        "message": f"Patch risk is {risk} with score {score} across {len(files)} file hint(s).",
    }


def build_patch_review(project_id: str = "eidolon") -> dict[str, Any]:
    from controlled_build_cycle import patch_workspace_status, preview_staged_diff, readme_gate

    workspace = patch_workspace_status()
    diff = preview_staged_diff(project_id=project_id, stage_if_missing=False, save=False)
    risk = build_patch_risk(project_id=project_id)
    tests = build_test_plan(project_id=project_id)
    gate = readme_gate(project_id=project_id)
    reports = [workspace, diff, risk, tests, gate]
    counts = Counter(str(report.get("status", "unknown")) for report in reports)
    status = "fail" if any(report.get("ok") is False for report in reports) else "warn" if counts.get("warn") or counts.get("dry_run") else "pass"
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not any(report.get("ok") is False for report in reports),
        "workspace": workspace,
        "diff": diff,
        "risk": risk,
        "test_plan": tests,
        "readme_gate": gate,
        "message": f"Patch review composed workspace, diff, risk, test plan, and README gate with status {status}.",
    }


def _readme_versions() -> list[str]:
    text = _read_text(README_FILE)
    versions = re.findall(r"Eidolon v(\d+\.\d+)", text)
    seen: set[str] = set()
    return [v for v in versions if not (v in seen or seen.add(v))]


def build_project_memory_index(project_id: str = "eidolon") -> dict[str, Any]:
    versions = _readme_versions()
    report_files = sorted(REPORTS_DIR.glob("*.json")) if REPORTS_DIR.exists() else []
    patch_workspace_files = [path for path in [CURRENT_PLAN, PROPOSED_CHANGES, LATEST_APPLY_REPORT, LATEST_DRY_RUN_APPLY_REPORT, LATEST_ROLLBACK_REPORT] if path.exists()]
    warnings: list[str] = []
    if "15.0" not in versions:
        warnings.append("README does not yet contain v15.0.")
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if warnings else "pass",
        "ok": True,
        "readme_versions": versions,
        "readme_version_count": len(versions),
        "controlled_build_report_count": len(report_files),
        "patch_workspace_files": [_relative(path) for path in patch_workspace_files],
        "latest_report_files": [_relative(path) for path in report_files[-10:]],
        "warnings": warnings,
        "message": f"Indexed {len(versions)} README version marker(s) and {len(report_files)} controlled build report(s).",
    }


def _workspace_projects() -> list[dict[str, Any]]:
    projects = _read_json(WORKSPACE_PROJECTS_FILE, [])
    if isinstance(projects, dict):
        projects = projects.get("projects", [])
    if not isinstance(projects, list) or not projects:
        projects = [{"id": "eidolon", "name": "Eidolon", "root": ".", "version": load_settings().get("settings_version", "unknown"), "priority": "high"}]
    normalized: list[dict[str, Any]] = []
    for item in projects:
        if not isinstance(item, dict):
            continue
        if str(item.get("id", "")).lower() == "eidolon" and str(item.get("root", "")) in {"", ".", "$ROOT_DIR", "{ROOT_DIR}", "ROOT_DIR"}:
            item = {**item, "root": ".", "root_resolves_from": "ROOT_DIR"}
        normalized.append(item)
    return normalized


def _resolve_workspace_root(project: dict[str, Any]) -> Path:
    raw = str(project.get("root") or project.get("path") or ".")
    if raw in {"", ".", "$ROOT_DIR", "{ROOT_DIR}", "ROOT_DIR"}:
        return ROOT_DIR
    path = Path(raw)
    if not path.is_absolute():
        return (ROOT_DIR / path).resolve()
    return path


def build_workspace_status(project_id: str = "eidolon") -> dict[str, Any]:
    projects = _workspace_projects()
    active = _read_json(ACTIVE_PROJECT_FILE, {"active_project_id": project_id})
    active_id = active.get("active_project_id", project_id) if isinstance(active, dict) else project_id
    rows: list[dict[str, Any]] = []
    for project in projects:
        root = _resolve_workspace_root(project)
        rows.append({
            "id": project.get("id", "unknown"),
            "name": project.get("name", project.get("id", "unknown")),
            "root": str(root),
            "version": project.get("version", "unknown"),
            "priority": project.get("priority", "medium"),
            "active": project.get("id") == active_id,
            "root_exists": root.exists(),
            "safe_to_modify": project.get("id") == "eidolon" and root.exists(),
        })
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if rows else "warn",
        "ok": True,
        "workspace_dir": str(WORKSPACES_DIR.relative_to(ROOT_DIR)),
        "active_project_id": active_id,
        "project_count": len(rows),
        "rows": rows,
        "message": f"Workspace foundation knows {len(rows)} project(s); active project is {active_id}.",
    }


def build_cross_project_task_review(project_id: str = "eidolon") -> dict[str, Any]:
    workspace = build_workspace_status(project_id=project_id)
    rows: list[dict[str, Any]] = []
    priority_value = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    for project in workspace.get("rows", []):
        pid = str(project.get("id") or project_id)
        tasks = list_tasks(project=pid, include_cancelled=False)
        available = [task for task in tasks if str(task.get("status", "planned")).lower() not in {"done", "completed", "cancelled", "blocked", "failed"}]
        top = sorted(available, key=lambda task: -priority_value.get(str(task.get("priority", "medium")).lower(), 20))[:3]
        rows.append({
            "project_id": pid,
            "project_priority": project.get("priority", "medium"),
            "safe_to_modify": project.get("safe_to_modify", False),
            "available_task_count": len(available),
            "top_tasks": [{"id": task.get("id"), "title": task.get("title", task.get("name", "[untitled]")), "priority": task.get("priority", "medium")} for task in top],
        })
    selected = next((row for row in rows if row.get("safe_to_modify") and row.get("available_task_count", 0) > 0), rows[0] if rows else {})
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if not rows else "pass",
        "ok": True,
        "rows": rows,
        "selected_project": selected,
        "message": f"Reviewed task availability across {len(rows)} project workspace row(s).",
    }


def build_asymmetric_dev_loop(project_id: str = "eidolon") -> dict[str, Any]:
    workspace = build_workspace_status(project_id=project_id)
    cross_review = build_cross_project_task_review(project_id=project_id)
    selected_project = cross_review.get("selected_project") or {}
    codebase = build_codebase_map(project_id=project_id)
    dependencies = build_task_dependencies(project_id=str(selected_project.get("project_id") or project_id))
    tests = build_test_plan(project_id=project_id)
    risk = build_patch_risk(project_id=project_id)
    blocked: list[str] = []
    if not selected_project:
        blocked.append("No project is available in the workspace foundation.")
    if selected_project and not selected_project.get("safe_to_modify"):
        blocked.append("Selected project is not marked safe to modify.")
    return {
        "version": PROJECT_INTELLIGENCE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if blocked else "preview_complete",
        "ok": not blocked,
        "live": False,
        "modifies_files": False,
        "workspace": workspace,
        "cross_project_review": cross_review,
        "selected_project": selected_project,
        "codebase_map_summary": {
            "file_count": codebase.get("file_count"),
            "python_file_count": codebase.get("python_file_count"),
            "cli_command_count": codebase.get("cli_command_count"),
            "api_route_count": codebase.get("api_route_count"),
        },
        "dependency_summary": {"task_count": dependencies.get("task_count"), "row_count": len(dependencies.get("rows", []))},
        "test_plan": tests,
        "patch_risk": risk,
        "blocked_reasons": blocked,
        "message": "Asymmetric development loop preview scanned projects, ranked safe work, mapped the active codebase, planned checks, and stopped before mutation.",
    }


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    for key in ["warnings", "blocked_reasons", "commands"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or report.get("factors") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:30]:
            if isinstance(row, dict):
                name = row.get("id") or row.get("task_id") or row.get("path") or row.get("project_id") or row.get("name") or "row"
                status = row.get("status") or row.get("risk") or row.get("severity") or "info"
                message = row.get("title") or row.get("reason") or row.get("message") or ""
                lines.append(f"- {str(status).upper()} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def codebase_map_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_codebase_map()
    lines = _generic_text("Eidolon v9.1 Codebase Map", report, full=False).splitlines()
    lines.extend([
        "",
        "## Summary",
        f"- Files: {report.get('file_count')}",
        f"- Python files: {report.get('python_file_count')}",
        f"- CLI commands: {report.get('cli_command_count')}",
        f"- API route hints: {report.get('api_route_count')}",
        f"- Dashboard routes: {report.get('dashboard_route_count')}",
        "",
        "## Major modules",
    ])
    for module in report.get("major_modules", [])[:25]:
        lines.append(f"- {module.get('path')}: {module.get('role')} ({module.get('line_count')} lines)")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def task_dependencies_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.2 Dependency-Aware Task Planning", report or build_task_dependencies(), full=full)


def test_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.3 Test Planner", report or build_test_plan(), full=full)


def patch_risk_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.4 Patch Risk Analyzer", report or build_patch_risk(), full=full)


def patch_review_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_patch_review()
    lines = _generic_text("Eidolon v9.5 Dashboard Patch Review", report, full=False).splitlines()
    for key in ["workspace", "diff", "risk", "test_plan", "readme_gate"]:
        item = report.get(key) or {}
        lines.append(f"- {key}: {str(item.get('status', 'unknown')).upper()} - {item.get('message', '')}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def project_memory_index_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.7 Project Memory Index", report or build_project_memory_index(), full=full)


def workspace_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.8 Multi-Project Workspace Foundation", report or build_workspace_status(), full=full)


def cross_project_task_review_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v9.9 Cross-Project Task Scheduler", report or build_cross_project_task_review(), full=full)


def asymmetric_dev_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v10.0 Asymmetric Multi-Project Development Loop", report or build_asymmetric_dev_loop(), full=full)


def print_codebase_map(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_codebase_map(project_id=project_id)
    _json_print(report) if json_output else print(codebase_map_text(report, full=full))


def print_task_dependencies(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_task_dependencies(project_id=project_id)
    _json_print(report) if json_output else print(task_dependencies_text(report, full=full))


def print_test_plan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_test_plan(project_id=project_id)
    _json_print(report) if json_output else print(test_plan_text(report, full=full))


def print_patch_risk(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_risk(project_id=project_id)
    _json_print(report) if json_output else print(patch_risk_text(report, full=full))


def print_patch_review(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_review(project_id=project_id)
    _json_print(report) if json_output else print(patch_review_text(report, full=full))


def print_project_memory_index(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_project_memory_index(project_id=project_id)
    _json_print(report) if json_output else print(project_memory_index_text(report, full=full))


def print_workspace_status(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_status(project_id=project_id)
    _json_print(report) if json_output else print(workspace_status_text(report, full=full))


def print_cross_project_task_review(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_cross_project_task_review(project_id=project_id)
    _json_print(report) if json_output else print(cross_project_task_review_text(report, full=full))


def print_asymmetric_dev_loop(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_asymmetric_dev_loop(project_id=project_id)
    _json_print(report) if json_output else print(asymmetric_dev_loop_text(report, full=full))
