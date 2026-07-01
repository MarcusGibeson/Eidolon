from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from controlled_build_cycle import (
    latest_apply_report_integrity,
    build_patch_plan,
    stage_controlled_patch,
    preview_staged_diff,
    apply_staged_patch,
    verify_latest_patch,
    readme_gate,
)
from paths import DATA_DIR, ROOT_DIR
from workspace_orchestration import (
    WORKSPACES_DIR,
    PROJECTS_FILE,
    ACTIVE_PROJECT_FILE,
    COMMAND_PROFILES_DIR,
    TIMELINE_FILE,
    active_workspace_project_id,
    build_project_health,
    build_workspace_task_inbox,
    build_project_context,
    build_workspace_dependency_map,
    build_command_profiles,
    load_workspace_projects,
    resolve_project_root,
    _read_json as _workspace_read_json,
    _timeline_event,
)

WORKSPACE_EXECUTION_VERSION = "1032.0"
PATCH_WORKSPACE_DIR = DATA_DIR / "patch_workspace"
CURRENT_PLAN = PATCH_WORKSPACE_DIR / "current_plan.json"
PROPOSED_CHANGES = PATCH_WORKSPACE_DIR / "proposed_changes.json"
VALIDATION_REPORT = PATCH_WORKSPACE_DIR / "validation_report.json"
LATEST_WORKSPACE_APPLY = PATCH_WORKSPACE_DIR / "latest_workspace_apply_report.json"
LATEST_WORKSPACE_VERIFY = PATCH_WORKSPACE_DIR / "latest_workspace_verify_report.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _status_from(rows: list[dict[str, Any]]) -> str:
    counts = Counter(str(row.get("status", "pass")) for row in rows)
    if counts.get("fail") or counts.get("blocked"):
        return "blocked"
    if counts.get("warn"):
        return "warn"
    return "pass"


def _project_by_id(project_id: str) -> dict[str, Any]:
    projects = load_workspace_projects(repair=False)
    return next((p for p in projects if str(p.get("id")) == project_id), projects[0] if projects else {})


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def build_workspace_registry_audit(project_id: str = "eidolon", archive_stale: bool = False) -> dict[str, Any]:
    projects = load_workspace_projects(repair=False)
    active_id = active_workspace_project_id()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_ids: set[str] = set()
    for project in projects:
        pid = str(project.get("id") or "")
        if pid in seen:
            duplicate_ids.add(pid)
        seen.add(pid)
        root = resolve_project_root(project)
        root_text = str(project.get("root") or "")
        readme_path = root / str(project.get("readme_path") or "README_NEXT_STEPS.md")
        profile_id = str(project.get("safe_command_profile") or "default_python")
        profile_path = COMMAND_PROFILES_DIR / f"{profile_id}.json"
        problems = []
        if not pid:
            problems.append("missing project id")
        if "/mnt/data" in root_text.replace("\\", "/"):
            problems.append("stale sandbox root path")
        if not root.exists():
            problems.append(f"root does not exist: {root}")
        if not readme_path.exists():
            problems.append(f"README path missing: {readme_path}")
        if not profile_path.exists():
            problems.append(f"safe command profile missing: {profile_id}")
        rows.append({
            "id": pid,
            "name": project.get("name"),
            "root": root_text,
            "resolved_root": str(root),
            "root_exists": root.exists(),
            "readme_exists": readme_path.exists(),
            "profile": profile_id,
            "profile_exists": profile_path.exists(),
            "active": pid == active_id,
            "status": "fail" if problems else "pass",
            "problems": problems,
        })
    json_rows = []
    for path in [PROJECTS_FILE, ACTIVE_PROJECT_FILE, TIMELINE_FILE]:
        try:
            _read_json(path, {})
            json_rows.append({"path": str(path.relative_to(ROOT_DIR)), "status": "pass", "message": "valid JSON or missing with default"})
        except Exception as error:
            json_rows.append({"path": str(path.relative_to(ROOT_DIR)), "status": "fail", "message": str(error)})
    if duplicate_ids:
        rows.append({"id": "duplicate-project-ids", "status": "fail", "problems": sorted(duplicate_ids)})
    if active_id not in seen:
        rows.append({"id": "active-project-pointer", "status": "fail", "problems": [f"active project {active_id} is not registered"]})
    apply_integrity = latest_apply_report_integrity(archive_stale=archive_stale)
    if not apply_integrity.get("ok", True):
        rows.append({"id": "latest-apply-pointer", "status": "warn", "problems": [apply_integrity.get("message", "latest apply pointer is stale")], "archived_to": apply_integrity.get("archived_to")})
    status = _status_from(rows + json_rows)
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status not in {"blocked"},
        "active_project_id": active_id,
        "project_count": len(projects),
        "rows": rows,
        "json_rows": json_rows,
        "latest_apply_integrity": apply_integrity,
        "archive_stale": archive_stale,
        "message": f"Workspace registry audit checked {len(projects)} project(s) and {len(json_rows)} registry file(s).",
    }


def build_workspace_repair_suggestions(project_id: str = "eidolon") -> dict[str, Any]:
    audit = build_workspace_registry_audit(project_id=project_id, archive_stale=False)
    suggestions: list[dict[str, Any]] = []
    for row in audit.get("rows", []):
        for problem in row.get("problems", []) or []:
            text = str(problem)
            fix = "Review workspace registry metadata."
            if "stale sandbox root" in text or "root does not exist" in text:
                fix = "Set the Eidolon project root to '.' so it resolves from ROOT_DIR, or register the real project root."
            elif "README" in text:
                fix = "Set README path to README_NEXT_STEPS.md or add the configured README file."
            elif "safe command profile" in text:
                fix = "Run the command profile report once or create the missing profile under data/workspaces/command_profiles/."
            elif "latest apply pointer" in text:
                fix = "Archive the stale latest_apply_report.json during registry audit/repair before relying on rollback."
            suggestions.append({"project_id": row.get("id"), "problem": text, "suggested_fix": fix})
    if not suggestions:
        suggestions.append({"project_id": project_id, "problem": "No workspace registry blockers detected.", "suggested_fix": "No repair needed."})
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if audit.get("ok") else "warn",
        "ok": True,
        "audit_status": audit.get("status"),
        "suggestions": suggestions,
        "message": f"Generated {len(suggestions)} workspace repair suggestion(s).",
    }


def build_project_registration_wizard(name: str = "Workspace Project", root: str | None = None, project_id: str | None = None) -> dict[str, Any]:
    raw_root = Path(root or ".")
    resolved = (ROOT_DIR / raw_root).resolve() if not raw_root.is_absolute() else raw_root
    language = "unknown"
    framework = "unknown"
    tests: list[str] = []
    profile = "default_python"
    if (resolved / "requirements.txt").exists() or (resolved / "pyproject.toml").exists():
        language = "Python"
        framework = "python"
        tests = ["python -m pytest", "python -m unittest"]
        profile = "default_python"
    if (resolved / "package.json").exists():
        language = "Node"
        framework = "node"
        tests = ["npm test", "npm run build"]
        profile = "default_node"
    if (resolved / "pom.xml").exists() or (resolved / "build.gradle").exists() or (resolved / "build.gradle.kts").exists():
        language = "Java"
        framework = "java"
        tests = ["mvn test", "gradle test"]
        profile = "default_java"
    readme = "README_NEXT_STEPS.md" if (resolved / "README_NEXT_STEPS.md").exists() else "README.md"
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "status": "pass" if resolved.exists() else "warn",
        "ok": True,
        "preview_only": True,
        "proposed_entry": {
            "id": project_id or "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_") or "project",
            "name": name,
            "root": "." if resolved == ROOT_DIR else str(resolved),
            "language": language,
            "framework_type": framework,
            "readme_path": readme,
            "test_commands": tests,
            "safe_command_profile": profile,
            "safe_to_modify": False,
        },
        "message": "Project registration wizard preview generated. Use --register-project to save it.",
    }


def build_project_boundary_check(project_id: str = "eidolon", explicit_workspace_edit: bool = False, changes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    project = _project_by_id(project_id)
    project_root = resolve_project_root(project)
    if changes is None:
        proposed = _read_json(PROPOSED_CHANGES, {})
        if not isinstance(proposed, dict) or not proposed.get("changes"):
            proposed = stage_controlled_patch(project_id=project_id, save=False)
        changes = proposed.get("changes", []) if isinstance(proposed, dict) else []
    rows: list[dict[str, Any]] = []
    for change in changes:
        rel = str(change.get("path") or "")
        status = "pass"
        problems: list[str] = []
        target = (ROOT_DIR / rel).resolve()
        if not _is_relative_to(target, project_root):
            status = "blocked"
            problems.append("target is outside active project root")
        if rel.replace("\\", "/").startswith("data/workspaces/") and not explicit_workspace_edit:
            status = "blocked"
            problems.append("workspace registry/profile edits require explicit workspace intent")
        if rel in {"conscious_agent/command_runner.py", "conscious_agent/safety.py"} and not explicit_workspace_edit:
            status = "warn"
            problems.append("global safety/command-runner file touched")
        rows.append({"path": rel, "action": change.get("action"), "status": status, "problems": problems})
    status = _status_from(rows) if rows else "warn"
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "active_project_root": str(project_root),
        "status": status,
        "ok": status not in {"blocked"},
        "rows": rows,
        "message": f"Project boundary check reviewed {len(rows)} staged change row(s).",
    }


def build_workspace_patch_plan(project_id: str = "eidolon", target_version: str = "15.0", save: bool = False) -> dict[str, Any]:
    audit = build_workspace_registry_audit(project_id=project_id, archive_stale=False)
    health = build_project_health(project_id=project_id, all_projects=False)
    context = build_project_context(project_id=project_id)
    dependency_map = build_workspace_dependency_map(project_id=project_id)
    inbox = build_workspace_task_inbox(project_id=project_id)
    plan = build_patch_plan(project_id=project_id, target_version=target_version, save=save)
    boundary = build_project_boundary_check(project_id=project_id)
    gate = readme_gate(project_id=project_id)
    parts = [audit, health, context, dependency_map, inbox, plan, boundary, gate]
    blocked = [part.get("message", part.get("status")) for part in parts if part.get("ok") is False or part.get("status") in {"blocked", "fail", "failed"}]
    status = "blocked" if blocked else "warn" if any(part.get("status") == "warn" for part in parts) else "pass"
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "target_version": target_version,
        "status": status,
        "ok": not blocked,
        "selected_project": project_id,
        "selected_task": inbox.get("selected"),
        "patch_plan": plan,
        "boundary": boundary,
        "readme_gate": gate,
        "blocked_reasons": blocked,
        "message": "Workspace patch plan assembled from registry, health, task, dependency, risk, boundary, and README gates.",
    }


def build_workspace_preview_diff(project_id: str = "eidolon", save: bool = False) -> dict[str, Any]:
    staged = stage_controlled_patch(project_id=project_id, create_plan_if_missing=True, save=save)
    diff = preview_staged_diff(project_id=project_id, stage_if_missing=False, save=save)
    boundary = build_project_boundary_check(project_id=project_id, changes=staged.get("changes", []))
    blocked = []
    if staged.get("ok") is False:
        blocked.append(staged.get("message"))
    if diff.get("ok") is False:
        blocked.append(diff.get("message"))
    if boundary.get("ok") is False:
        blocked.append(boundary.get("message"))
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if blocked else "warn" if diff.get("status") == "warn" or boundary.get("status") == "warn" else "pass",
        "ok": not blocked,
        "preview_only": not save,
        "staged": staged,
        "diff": diff,
        "boundary": boundary,
        "blocked_reasons": blocked,
        "message": "Workspace diff preview generated with project-boundary awareness.",
    }


def build_workspace_apply(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    plan = build_workspace_patch_plan(project_id=project_id, save=save)
    diff = build_workspace_preview_diff(project_id=project_id, save=save)
    boundary = diff.get("boundary", {})
    blocked = []
    if plan.get("ok") is False:
        blocked.append("workspace patch plan is blocked")
    if diff.get("ok") is False:
        blocked.append("workspace diff preview is blocked")
    if boundary.get("ok") is False:
        blocked.append("project boundary check is blocked")
    if not dry_run and not approve:
        blocked.append("guarded workspace apply requires --approve-controlled-self-build")
    if blocked:
        report = {
            "version": WORKSPACE_EXECUTION_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "blocked",
            "ok": False,
            "dry_run": dry_run,
            "approved": approve,
            "blocked_reasons": blocked,
            "plan": plan,
            "diff": diff,
            "message": "Workspace apply blocked before source mutation.",
        }
        if save:
            _write_json(LATEST_WORKSPACE_APPLY, report)
        return report
    if not save:
        apply_report = {
            "version": WORKSPACE_EXECUTION_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "preview_only",
            "ok": True,
            "dry_run": dry_run,
            "approved": approve,
            "message": "Workspace apply preview checked gates without writing source or workspace state.",
        }
    else:
        apply_report = apply_staged_patch(project_id=project_id, approve=approve, dry_run=dry_run)
    _timeline_event("workspace_apply_dry_run" if dry_run else "workspace_apply_guarded", {"project_id": project_id, "status": apply_report.get("status")}, save=save)
    report = {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": apply_report.get("status"),
        "ok": apply_report.get("ok", False),
        "dry_run": dry_run,
        "approved": approve,
        "apply_report": apply_report,
        "message": "Workspace apply dry-run completed." if dry_run else "Guarded workspace apply completed.",
    }
    if save:
        _write_json(LATEST_WORKSPACE_APPLY, report)
    return report


def build_workspace_verify_latest(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    if save:
        verification = verify_latest_patch(project_id=project_id)
    else:
        integrity = latest_apply_report_integrity(archive_stale=False)
        verification = {
            "version": WORKSPACE_EXECUTION_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "passed" if integrity.get("ok", True) else "failed",
            "ok": bool(integrity.get("ok", True)),
            "latest_apply_integrity": integrity,
            "preview_only": True,
            "message": "Workspace verification preview checked latest apply integrity without writing validation state.",
        }
    gate = readme_gate(project_id=project_id)
    boundary = build_project_boundary_check(project_id=project_id)
    health = build_project_health(project_id=project_id, all_projects=False)
    parts = [verification, gate, boundary, health]
    blocked = [part.get("message", part.get("status")) for part in parts if part.get("ok") is False or part.get("status") in {"blocked", "fail", "failed"}]
    status = "failed" if blocked else "passed_with_warnings" if any(part.get("status") in {"warn", "passed_with_warnings"} for part in parts) else "passed"
    report = {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "verification": verification,
        "readme_gate": gate,
        "boundary": boundary,
        "health": health,
        "rollback_recommended": status == "failed" and bool(verification.get("rollback_recommended")),
        "blocked_reasons": blocked,
        "message": f"Workspace verification pipeline {status}.",
    }
    if save:
        _write_json(LATEST_WORKSPACE_VERIFY, report)
    return report


def build_guarded_workspace_dev_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    audit = build_workspace_registry_audit(project_id=project_id, archive_stale=save)
    health = build_project_health(project_id=project_id, all_projects=True)
    inbox = build_workspace_task_inbox(project_id=project_id)
    selected_project = str((inbox.get("selected") or {}).get("project_id") or project_id)
    context = build_project_context(project_id=selected_project)
    plan = build_workspace_patch_plan(project_id=selected_project, target_version="15.0", save=save)
    diff = build_workspace_preview_diff(project_id=selected_project, save=save)
    boundary = diff.get("boundary", build_project_boundary_check(project_id=selected_project))
    apply_report = build_workspace_apply(project_id=selected_project, approve=approve, dry_run=True if dry_run or not approve else False, save=save)
    verification = build_workspace_verify_latest(project_id=selected_project, save=save)
    steps = [audit, health, inbox, context, plan, diff, boundary, apply_report, verification]
    blocked = [step.get("message", step.get("status")) for step in steps if step.get("ok") is False or step.get("status") in {"blocked", "fail", "failed"}]
    status = "blocked" if blocked else "dry_run_complete" if dry_run or not approve else "completed"
    _timeline_event("guarded_workspace_dev_loop", {"project_id": selected_project, "status": status, "dry_run": dry_run or not approve}, save=save)
    return {
        "version": WORKSPACE_EXECUTION_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "selected_project_id": selected_project,
        "status": status,
        "ok": not blocked,
        "dry_run": dry_run or not approve,
        "approved": approve,
        "steps": {
            "audit": audit,
            "health": health,
            "task_inbox": inbox,
            "context": context,
            "plan": plan,
            "diff": diff,
            "boundary": boundary,
            "apply": apply_report,
            "verification": verification,
        },
        "blocked_reasons": blocked,
        "message": "Guarded workspace development loop selected one project, prepared one patch lane, verified gates, and stopped.",
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
    for key in ["blocked_reasons", "warnings"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or report.get("suggestions") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:30]:
            if isinstance(row, dict):
                name = row.get("id") or row.get("project_id") or row.get("path") or row.get("problem") or "row"
                status = row.get("status") or row.get("suggested_fix") or "info"
                message = row.get("message") or "; ".join(str(x) for x in row.get("problems", []) or []) or row.get("suggested_fix") or ""
                lines.append(f"- {str(status).upper()} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def workspace_registry_audit_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.1 Workspace Registry Persistence Audit", report or build_workspace_registry_audit(), full)


def workspace_repair_suggestions_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.2 Workspace Repair Suggestions", report or build_workspace_repair_suggestions(), full)


def project_registration_wizard_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.3 Project Registration Wizard", report or build_project_registration_wizard(), full)


def project_boundary_check_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.4 Project Boundary Guard", report or build_project_boundary_check(), full)


def workspace_patch_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.5 Workspace Patch Plan", report or build_workspace_patch_plan(), full)


def workspace_preview_diff_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.6 Workspace Diff Preview", report or build_workspace_preview_diff(), full)


def workspace_apply_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.7-v11.8 Workspace Apply", report or build_workspace_apply(dry_run=True, save=False), full)


def workspace_verify_latest_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v11.9 Workspace Verification Pipeline", report or build_workspace_verify_latest(save=False), full)


def guarded_workspace_dev_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.0 Guarded Workspace Development Loop", report or build_guarded_workspace_dev_loop(save=False), full)


def print_workspace_registry_audit(project_id: str = "eidolon", full: bool = False, json_output: bool = False, archive_stale: bool = True) -> None:
    report = build_workspace_registry_audit(project_id=project_id, archive_stale=archive_stale)
    _json_print(report) if json_output else print(workspace_registry_audit_text(report, full=full))


def print_workspace_repair_suggestions(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_repair_suggestions(project_id=project_id)
    _json_print(report) if json_output else print(workspace_repair_suggestions_text(report, full=full))


def print_project_registration_wizard(name: str = "Workspace Project", root: str | None = None, project_id: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_project_registration_wizard(name=name, root=root, project_id=project_id)
    _json_print(report) if json_output else print(project_registration_wizard_text(report, full=full))


def print_project_boundary_check(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_project_boundary_check(project_id=project_id)
    _json_print(report) if json_output else print(project_boundary_check_text(report, full=full))


def print_workspace_patch_plan(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_patch_plan(project_id=project_id, save=True)
    _json_print(report) if json_output else print(workspace_patch_plan_text(report, full=full))


def print_workspace_preview_diff(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_preview_diff(project_id=project_id, save=True)
    _json_print(report) if json_output else print(workspace_preview_diff_text(report, full=full))


def print_workspace_apply(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_apply(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(workspace_apply_text(report, full=full))


def print_workspace_verify_latest(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_workspace_verify_latest(project_id=project_id, save=True)
    _json_print(report) if json_output else print(workspace_verify_latest_text(report, full=full))


def print_guarded_workspace_dev_loop(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_guarded_workspace_dev_loop(project_id=project_id, approve=approve, dry_run=dry_run, save=bool(approve and not dry_run))
    _json_print(report) if json_output else print(guarded_workspace_dev_loop_text(report, full=full))
