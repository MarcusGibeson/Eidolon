from __future__ import annotations

import importlib.util
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from settings_manager import load_settings, settings_health


DIAGNOSTICS_DIR = DATA_DIR / "diagnostics"


@dataclass
class DiagnosticCheck:
    name: str
    status: str
    summary: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details or {},
        }


def _now_id(prefix: str = "diag") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _ensure_diagnostics_dir() -> None:
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    readme = DIAGNOSTICS_DIR / "README.md"
    if not readme.exists():
        readme.write_text("Saved diagnostic reports for Eidolon.\n", encoding="utf-8")


def _load_json_file(path: Path) -> tuple[bool, Any, str]:
    if not path.exists():
        return False, None, "missing"
    try:
        with path.open("r", encoding="utf-8") as file:
            return True, json.load(file), "ok"
    except json.JSONDecodeError as error:
        return False, None, f"invalid json: {error}"
    except OSError as error:
        return False, None, f"read error: {error}"


def _status_rank(status: str) -> int:
    return {"pass": 0, "info": 1, "warn": 2, "fail": 3}.get(status, 2)


def _check_python_environment() -> DiagnosticCheck:
    version = sys.version.split()[0]
    details = {
        "python_version": version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": str(Path.cwd()),
        "root_dir": str(ROOT_DIR),
        "data_dir": str(DATA_DIR),
    }
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        return DiagnosticCheck(
            "python_environment",
            "warn",
            f"Python {version} detected. Eidolon is happiest on Python 3.10+.",
            details,
        )
    return DiagnosticCheck("python_environment", "pass", f"Python {version} is usable.", details)


def _check_dependencies() -> DiagnosticCheck:
    packages = {
        "requests": importlib.util.find_spec("requests") is not None,
        "chromadb": importlib.util.find_spec("chromadb") is not None,
    }
    missing = [name for name, present in packages.items() if not present]
    details = {"packages": packages, "missing": missing}
    if missing:
        return DiagnosticCheck(
            "dependencies",
            "fail",
            "Missing Python packages: " + ", ".join(missing),
            details,
        )
    return DiagnosticCheck("dependencies", "pass", "Required Python packages are importable.", details)


def _check_settings() -> DiagnosticCheck:
    try:
        settings = load_settings()
    except Exception as error:
        return DiagnosticCheck("settings", "fail", f"Could not load settings: {error}", {})

    required = [
        "local_model",
        "embed_model",
        "ollama_base_url",
        "command_timeout_seconds",
        "max_capture_chars",
        "default_dev_loop_steps",
        "safe_mode",
    ]
    missing = [key for key in required if key not in settings]
    details = {
        "settings_file": str(DATA_DIR / "settings.json"),
        "missing_required_keys": missing,
        "selected": {key: settings.get(key) for key in required},
    }
    if missing:
        return DiagnosticCheck("settings", "warn", "Settings loaded, but some required keys were missing and defaulted.", details)
    return DiagnosticCheck("settings", "pass", "Settings loaded successfully.", details)


def _check_ollama() -> DiagnosticCheck:
    try:
        health = settings_health()
    except Exception as error:
        return DiagnosticCheck("ollama", "fail", f"Ollama health check crashed: {error}", {})

    details = health
    if not health.get("ollama_ok"):
        return DiagnosticCheck(
            "ollama",
            "warn",
            "Ollama is not reachable. Local AI features will fail until it is running.",
            details,
        )

    missing = []
    if not health.get("local_model_installed"):
        missing.append(str(health.get("local_model")))
    if not health.get("embed_model_installed"):
        missing.append(str(health.get("embed_model")))

    if missing:
        return DiagnosticCheck(
            "ollama",
            "warn",
            "Ollama is reachable, but configured model(s) are missing: " + ", ".join(missing),
            details,
        )

    return DiagnosticCheck("ollama", "pass", "Ollama is reachable and configured models are installed.", details)


def _check_data_files() -> DiagnosticCheck:
    expected = [
        "settings.json",
        "self_model.json",
        "desires.json",
        "opinions.json",
        "memories.json",
        "projects.json",
        "goals.json",
        "tasks.json",
        "action_log.json",
    ]
    file_results: dict[str, Any] = {}
    failures = []
    warnings = []

    for name in expected:
        path = DATA_DIR / name
        ok, data, message = _load_json_file(path)
        file_results[name] = {
            "exists": path.exists(),
            "status": message,
            "type": type(data).__name__ if ok else None,
            "count": len(data) if ok and hasattr(data, "__len__") else None,
        }
        if not ok:
            if message == "missing":
                warnings.append(name)
            else:
                failures.append(f"{name}: {message}")

    details = {"files": file_results, "missing": warnings, "failures": failures}
    if failures:
        return DiagnosticCheck("data_files", "fail", "Some data JSON files are invalid or unreadable.", details)
    if warnings:
        return DiagnosticCheck("data_files", "warn", "Some data JSON files are missing; Eidolon may recreate defaults.", details)
    return DiagnosticCheck("data_files", "pass", "Core data JSON files exist and parse correctly.", details)


def _check_project_state() -> DiagnosticCheck:
    try:
        from project_manager import get_active_project
    except Exception as error:
        return DiagnosticCheck("project_state", "fail", f"Could not import project manager: {error}", {})

    project = get_active_project()
    if not project:
        return DiagnosticCheck("project_state", "warn", "No active project is set.", {})

    path = Path(str(project.get("path", ""))).expanduser()
    details = {
        "active_project": project,
        "path_exists": path.exists(),
        "is_dir": path.is_dir(),
    }
    if not path.exists() or not path.is_dir():
        return DiagnosticCheck("project_state", "fail", f"Active project path is not a folder: {path}", details)
    return DiagnosticCheck("project_state", "pass", f"Active project path exists: {path}", details)


def _check_project_index() -> DiagnosticCheck:
    index_file = DATA_DIR / "project_index.json"
    ok, index, message = _load_json_file(index_file)
    if not ok:
        return DiagnosticCheck("project_index", "warn", f"Project index unavailable: {message}", {"index_file": str(index_file)})

    files = index.get("files", []) if isinstance(index, dict) else []
    parse_errors = []
    for file_info in files:
        summary = file_info.get("summary", {}) if isinstance(file_info, dict) else {}
        if summary.get("parse_error"):
            parse_errors.append({
                "path": file_info.get("path"),
                "parse_error": summary.get("parse_error"),
            })

    details = {
        "index_file": str(index_file),
        "indexed_at": index.get("indexed_at") if isinstance(index, dict) else None,
        "active_project": index.get("active_project") if isinstance(index, dict) else None,
        "files_indexed": len(files),
        "parse_errors": parse_errors,
    }
    if not files:
        return DiagnosticCheck("project_index", "warn", "Project index exists but has no files. Run --index-project conscious_agent.", details)
    if parse_errors:
        return DiagnosticCheck("project_index", "warn", f"Project index has {len(parse_errors)} Python parse error(s).", details)
    return DiagnosticCheck("project_index", "pass", f"Project index contains {len(files)} files.", details)


def _check_memory_and_vectors() -> DiagnosticCheck:
    memories_ok, memories, memories_message = _load_json_file(DATA_DIR / "memories.json")
    memory_count = len(memories) if memories_ok and isinstance(memories, list) else 0

    details: dict[str, Any] = {
        "memories_json_status": memories_message,
        "active_memory_count": memory_count,
        "chroma_dir_exists": (DATA_DIR / "chroma").exists(),
        "chromadb_importable": importlib.util.find_spec("chromadb") is not None,
        "vector_collection_count": None,
        "vector_error": None,
    }

    if details["chromadb_importable"]:
        try:
            from vector_memory import get_collection
            collection = get_collection()
            details["vector_collection_count"] = collection.count()
        except Exception as error:
            details["vector_error"] = str(error)

    if not memories_ok:
        return DiagnosticCheck("memory", "fail", f"memories.json problem: {memories_message}", details)

    if details["vector_error"]:
        return DiagnosticCheck("memory", "warn", "JSON memory is readable, but semantic memory check failed.", details)

    if details["chromadb_importable"] and details["vector_collection_count"] is not None:
        if memory_count > 0 and int(details["vector_collection_count"] or 0) == 0:
            return DiagnosticCheck("memory", "warn", "Memories exist, but vector memory has no entries. Run --rebuild-semantic-memory.", details)

    return DiagnosticCheck("memory", "pass", f"Memory is readable with {memory_count} active memories.", details)


def _check_counts_and_backlog() -> DiagnosticCheck:
    def load_list(name: str) -> list[Any]:
        ok, data, _ = _load_json_file(DATA_DIR / name)
        return data if ok and isinstance(data, list) else []

    patches = []
    patch_dir = DATA_DIR / "patches"
    if patch_dir.exists():
        for path in patch_dir.glob("*.json"):
            ok, data, _ = _load_json_file(path)
            if ok and isinstance(data, dict):
                patches.append(data)

    approvals = []
    approval_dir = DATA_DIR / "approvals"
    if approval_dir.exists():
        for path in approval_dir.glob("*.json"):
            ok, data, _ = _load_json_file(path)
            if ok and isinstance(data, dict):
                approvals.append(data)

    tasks = load_list("tasks.json")
    goals = load_list("goals.json")
    action_log = load_list("action_log.json")

    pending_approvals = [a for a in approvals if a.get("status") == "pending"]
    proposed_patches = [p for p in patches if p.get("status") == "proposed"]
    applied_patches = [p for p in patches if p.get("status") == "applied"]
    failed_actions = [entry for entry in action_log if str(entry.get("status", "")).lower() in {"failed", "error", "blocked"}]

    details = {
        "patches": {
            "total": len(patches),
            "proposed": len(proposed_patches),
            "applied": len(applied_patches),
        },
        "approvals": {
            "total": len(approvals),
            "pending": len(pending_approvals),
        },
        "tasks": {
            "total": len(tasks),
            "ready": len([t for t in tasks if t.get("status") == "ready"]),
            "active": len([t for t in tasks if t.get("status") == "active"]),
            "blocked": len([t for t in tasks if t.get("status") == "blocked"]),
        },
        "goals": {
            "total": len(goals),
            "active": len([g for g in goals if g.get("status") == "active"]),
            "blocked": len([g for g in goals if g.get("status") == "blocked"]),
        },
        "action_log": {
            "total": len(action_log),
            "recent_failures": failed_actions[-5:],
            "failure_count": len(failed_actions),
        },
    }

    warnings = []
    if pending_approvals:
        warnings.append(f"{len(pending_approvals)} pending approval(s)")
    if proposed_patches:
        warnings.append(f"{len(proposed_patches)} proposed patch(es)")
    if failed_actions:
        warnings.append(f"{len(failed_actions)} failed/blocked action log entrie(s)")

    if warnings:
        return DiagnosticCheck("workflow_backlog", "warn", "; ".join(warnings), details)
    return DiagnosticCheck("workflow_backlog", "pass", "No obvious workflow backlog found.", details)


def _check_command_runner() -> DiagnosticCheck:
    try:
        from command_runner import validate_command
        validation = validate_command("python conscious_agent/main.py --status")
    except Exception as error:
        return DiagnosticCheck("command_runner", "fail", f"Command runner check crashed: {error}", {})

    details = {
        "status_command_allowed": validation.ok,
        "reason": validation.reason,
        "args": validation.args,
    }
    if not validation.ok:
        return DiagnosticCheck("command_runner", "fail", "Approved status command is not allowed by command runner.", details)
    return DiagnosticCheck("command_runner", "pass", "Command runner allows the baseline status command.", details)


def _check_storage_dirs() -> DiagnosticCheck:
    dirs = [
        "patches",
        "backups",
        "test_reports",
        "test_reviews",
        "self_improvements",
        "maintenance_suggestions",
        "memory_summaries",
        "memory_archive",
        "session_plans",
        "task_evaluations",
        "guided_sessions",
        "dev_cycles",
        "dev_loops",
        "approvals",
        "diagnostics",
    ]
    results = {}
    missing = []
    for name in dirs:
        path = DATA_DIR / name
        results[name] = {"exists": path.exists(), "is_dir": path.is_dir()}
        if not path.exists():
            missing.append(name)

    details = {"directories": results, "missing": missing}
    if missing:
        return DiagnosticCheck("storage_dirs", "warn", "Some optional storage directories are missing; they will be created as needed.", details)
    return DiagnosticCheck("storage_dirs", "pass", "Expected storage directories exist.", details)


def build_diagnostic_report(include_full: bool = False) -> dict[str, Any]:
    checks = [
        _check_python_environment(),
        _check_dependencies(),
        _check_settings(),
        _check_ollama(),
        _check_data_files(),
        _check_storage_dirs(),
        _check_project_state(),
        _check_project_index(),
        _check_memory_and_vectors(),
        _check_command_runner(),
        _check_counts_and_backlog(),
    ]

    counts: dict[str, int] = {"pass": 0, "info": 0, "warn": 0, "fail": 0}
    for check in checks:
        counts[check.status] = counts.get(check.status, 0) + 1

    worst = max(checks, key=lambda check: _status_rank(check.status)).status if checks else "info"
    if counts.get("fail", 0):
        recommendation = "Fix failing diagnostics before running dev loops or applying patches."
    elif counts.get("warn", 0):
        recommendation = "System is usable, but review warnings before depending on autonomous workflows."
    else:
        recommendation = "Diagnostics look healthy. Eidolon is ready for normal supervised workflows."

    report = {
        "id": _now_id(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "overall_status": worst,
        "counts": counts,
        "recommendation": recommendation,
        "checks": [check.to_dict() for check in checks],
    }

    if not include_full:
        # Full details are still saved; display functions decide how much to show.
        pass

    return report


def save_diagnostic_report(report: dict[str, Any]) -> Path:
    _ensure_diagnostics_dir()
    report_id = str(report.get("id") or _now_id())
    path = DIAGNOSTICS_DIR / f"{report_id}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    return path


def list_diagnostic_reports() -> list[dict[str, Any]]:
    _ensure_diagnostics_dir()
    reports: list[dict[str, Any]] = []
    for path in DIAGNOSTICS_DIR.glob("diag_*.json"):
        ok, data, _ = _load_json_file(path)
        if ok and isinstance(data, dict):
            reports.append(data)
    return sorted(reports, key=lambda report: str(report.get("created_at", "")), reverse=True)


def resolve_diagnostic_report_id(report_id_or_alias: str) -> str | None:
    reports = list_diagnostic_reports()
    if not reports:
        return None
    alias = (report_id_or_alias or "latest").strip().lower()
    if alias == "latest":
        return str(reports[0].get("id"))
    if alias == "latest-pass":
        for report in reports:
            if report.get("overall_status") == "pass":
                return str(report.get("id"))
    if alias == "latest-warn":
        for report in reports:
            if report.get("overall_status") == "warn":
                return str(report.get("id"))
    if alias == "latest-fail":
        for report in reports:
            if report.get("overall_status") == "fail":
                return str(report.get("id"))
    for report in reports:
        if report.get("id") == report_id_or_alias:
            return str(report.get("id"))
    return None


def load_diagnostic_report(report_id_or_alias: str) -> dict[str, Any] | None:
    resolved = resolve_diagnostic_report_id(report_id_or_alias)
    if not resolved:
        return None
    ok, data, _ = _load_json_file(DIAGNOSTICS_DIR / f"{resolved}.json")
    return data if ok and isinstance(data, dict) else None


def diagnostic_report_text(report: dict[str, Any], include_full: bool = False) -> str:
    lines = [
        f"# Diagnostic report: {report.get('id')}",
        "",
        f"Created at: {report.get('created_at')}",
        f"Overall status: {str(report.get('overall_status')).upper()}",
        f"Counts: {report.get('counts')}",
        f"Recommendation: {report.get('recommendation')}",
        "",
        "Checks:",
    ]

    for check in report.get("checks", []):
        lines.append(f"- [{str(check.get('status')).upper()}] {check.get('name')}: {check.get('summary')}")
        if include_full:
            details = check.get("details", {})
            if details:
                rendered = json.dumps(details, indent=2)
                for line in rendered.splitlines():
                    lines.append(f"    {line}")
    return "\n".join(lines)


def print_diagnostics(include_full: bool = False) -> None:
    report = build_diagnostic_report(include_full=True)
    path = save_diagnostic_report(report)
    print(diagnostic_report_text(report, include_full=include_full))
    print()
    print(f"Saved diagnostic report: {path}")


def print_diagnostic_reports() -> None:
    reports = list_diagnostic_reports()
    if not reports:
        print("No diagnostic reports found.")
        return
    for report in reports:
        counts = report.get("counts", {})
        print(
            f"{report.get('id')} | "
            f"{report.get('created_at')} | "
            f"status={report.get('overall_status')} | "
            f"pass={counts.get('pass', 0)} warn={counts.get('warn', 0)} fail={counts.get('fail', 0)}"
        )


def print_saved_diagnostic_report(report_id_or_alias: str, include_full: bool = False) -> None:
    report = load_diagnostic_report(report_id_or_alias)
    if not report:
        print(f"Diagnostic report not found: {report_id_or_alias}")
        return
    print(diagnostic_report_text(report, include_full=include_full))
