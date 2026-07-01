from __future__ import annotations

"""v7.0 stabilization checkpoint helpers.

This module performs a read-only checkpoint across the current Eidolon loop:
settings, files, JSON storage, task lifecycle, recovery, cycle policy, stable-loop
preflight, closure guardrails, API/dashboard surface checks, and smoke-test
readiness. It intentionally does not apply patches, run live loops, approve
anything, archive anything, or start local servers. Groundbreaking restraint.
"""

import importlib
import importlib.util
import json
import py_compile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from paths import ROOT_DIR, DATA_DIR

STABILIZATION_CHECKPOINT_VERSION = "1032.0"
DEFAULT_PROJECT_ID = "eidolon"

PASS = "pass"
WARN = "warn"
FAIL = "fail"

REQUIRED_FILES = [
    "README_NEXT_STEPS.md",
    "requirements.txt",
    "conscious_agent/main.py",
    "conscious_agent/dashboard.py",
    "conscious_agent/api_server.py",
    "conscious_agent/settings_manager.py",
    "conscious_agent/task_queue.py",
    "conscious_agent/task_lifecycle.py",
    "conscious_agent/task_recovery.py",
    "conscious_agent/task_cycle_policy.py",
    "conscious_agent/work_cycle.py",
    "conscious_agent/stable_supervised_loop.py",
    "conscious_agent/stable_loop_guardrails.py",
    "conscious_agent/stable_loop_followup_completion.py",
    "conscious_agent/operational_readiness.py",
    "conscious_agent/controlled_build_cycle.py",
    "conscious_agent/project_intelligence.py",
    "conscious_agent/workspace_orchestration.py",
        "conscious_agent/workspace_execution.py",
    "tools/smoke_check.py",
    "data/settings.json",
    "data/projects.json",
    "data/tasks.json",
]

JSON_FILES = [
    "data/settings.json",
    "data/projects.json",
    "data/tasks.json",
    "data/goals.json",
    "data/memories.json",
    "data/action_log.json",
]

CORE_IMPORTS = [
    "settings_manager",
    "task_queue",
    "task_lifecycle",
    "task_recovery",
    "task_cycle_policy",
    "work_cycle",
    "stable_supervised_loop",
    "stable_loop_review",
    "stable_loop_decision_report",
    "stable_loop_followup_tasks",
    "stable_loop_followup_lifecycle",
    "stable_loop_followup_completion",
    "stable_loop_guardrails",
    "api_server",
    "dashboard",
    "controlled_build_cycle",
    "project_intelligence",
    "workspace_orchestration",
]

ENVIRONMENT_IMPORTS = ["requests", "chromadb"]

EXPECTED_CLI_FLAGS = [
    "--stabilization-checkpoint",
    "--stabilization-full",
    "--stabilization-json",
    "--doctor",
    "--repair-suggestions",
    "--patch-integrity",
    "--project-snapshot",
    "--task-review",
    "--recovery-drill",
    "--stable-loop-confidence",
    "--hardening-report",
    "--controlled-self-build",
    "--select-task",
    "--plan-patch",
    "--patch-workspace-status",
    "--stage-patch",
    "--preview-diff",
    "--apply-staged-patch",
    "--verify-latest-patch",
    "--rollback-latest-patch",
    "--readme-gate",
    "--controlled-self-build-cycle",
    "--supervised-dev-loop",
    "--codebase-map",
    "--patch-generation-context-builder",
    "--pre-v72-patch-context-gate",
    "--task-dependencies",
    "--test-plan",
    "--patch-risk",
    "--patch-review",
    "--project-memory-index",
    "--workspace-status",
    "--cross-project-task-review",
    "--asymmetric-dev-loop",
    "--project-registry",
    "--register-project",
    "--set-active-workspace-project",
    "--project-health",
    "--project-health-all",
    "--command-profiles",
    "--workspace-dependency-map",
    "--workspace-task-inbox",
    "--switch-project",
    "--project-context",
    "--workspace-timeline",
    "--workspace-dev-loop",
]

EXPECTED_API_ENDPOINTS = [
    "GET /api/stabilization-checkpoint",
    "GET /api/doctor",
    "GET /api/repair-suggestions",
    "GET /api/patch-integrity",
    "GET /api/project-snapshot",
    "GET /api/tasks/review",
    "GET /api/recovery-drill",
    "GET /api/stable-loops/confidence",
    "GET /api/hardening-report",
    "GET /api/controlled-self-build",
    "GET /api/controlled-build/select-task",
    "GET /api/controlled-build/plan-patch",
    "GET /api/controlled-build/workspace",
    "GET /api/controlled-build/preview-diff",
    "GET /api/controlled-build/readme-gate",
    "POST /api/supervised-dev-loop",
    "GET /api/codebase-map",
    "GET /api/patch-context/layer",
    "GET /api/patch-context/gate",
    "GET /api/task-dependencies",
    "GET /api/test-plan",
    "GET /api/patch-risk",
    "GET /api/patch-review",
    "GET /api/project-memory-index",
    "GET /api/workspace-status",
    "GET /api/cross-project-task-review",
    "GET /api/asymmetric-dev-loop",
    "GET /api/project-registry",
    "POST /api/projects/register",
    "POST /api/projects/active",
    "GET /api/project-health",
    "GET /api/command-profiles",
    "GET /api/workspace-dependency-map",
    "GET /api/workspace-task-inbox",
    "POST /api/workspace/switch-project",
    "GET /api/project-context",
    "GET /api/workspace-timeline",
    "GET /api/workspace-dev-loop",
    "GET /api/stable-loops/preflight",
    "GET /api/stable-loops/guardrails",
    "GET /api/tasks/lifecycle",
    "GET /api/tasks/recovery/summary",
]

EXPECTED_DASHBOARD_ROUTES = [
    "/stabilization",
    "/doctor",
    "/build-cycle",
    "/patch-review",
    "/intelligence",
    "/workspace",
    "/stable-loop",
    "/work-cycle",
    "/api-info",
]

RECOMMENDED_COMMANDS = [
    "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
    "python conscious_agent/main.py --status",
    "python conscious_agent/main.py --settings-health",
    "python conscious_agent/main.py --stabilization-checkpoint --stabilization-full",
    "python conscious_agent/main.py --doctor --doctor-full",
    "python conscious_agent/main.py --repair-suggestions",
    "python conscious_agent/main.py --stable-loop-confidence",
    "python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop",
    "python conscious_agent/main.py --controlled-self-build --select-task",
    "python conscious_agent/main.py --controlled-self-build --plan-patch",
    "python conscious_agent/main.py --controlled-self-build --preview-diff",
    "python conscious_agent/main.py --readme-gate",
    "python conscious_agent/main.py --supervised-dev-loop",
    "python conscious_agent/main.py --codebase-map",
    "python conscious_agent/main.py --task-dependencies",
    "python conscious_agent/main.py --test-plan",
    "python conscious_agent/main.py --patch-risk",
    "python conscious_agent/main.py --patch-review",
    "python conscious_agent/main.py --project-memory-index",
    "python conscious_agent/main.py --workspace-status",
    "python conscious_agent/main.py --cross-project-task-review",
    "python conscious_agent/main.py --asymmetric-dev-loop",
    "python conscious_agent/main.py --project-registry",
    "python conscious_agent/main.py --project-health --project-health-all",
    "python conscious_agent/main.py --command-profiles",
    "python conscious_agent/main.py --workspace-dependency-map",
    "python conscious_agent/main.py --workspace-task-inbox",
    "python conscious_agent/main.py --project-context",
    "python conscious_agent/main.py --workspace-timeline",
    "python conscious_agent/main.py --workspace-dev-loop",
    "python conscious_agent/main.py --guarded-workspace-dev-loop",
    "python conscious_agent/main.py --stable-loop-guardrails",
    "python conscious_agent/main.py --stable-loop-preflight --no-ai-stable-loop",
    "python conscious_agent/main.py --stable-loop-followup-completion-report unresolved",
    "python tools/smoke_check.py",
]


@dataclass
class CheckpointItem:
    name: str
    status: str
    message: str
    category: str = "general"
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root_path(relative: str | Path) -> Path:
    return ROOT_DIR / Path(relative)


def _item(name: str, status: str, message: str, category: str = "general", details: dict[str, Any] | None = None) -> CheckpointItem:
    return CheckpointItem(name=name, status=status, message=message, category=category, details=details or {})


def _run_check(items: list[CheckpointItem], name: str, category: str, callback: Callable[[], CheckpointItem | list[CheckpointItem]]) -> None:
    try:
        result = callback()
        if isinstance(result, list):
            items.extend(result)
        else:
            items.append(result)
    except Exception as error:
        items.append(_item(name, FAIL, f"Checkpoint check crashed: {error}", category, {"error": repr(error)}))


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _check_required_files() -> list[CheckpointItem]:
    rows: list[CheckpointItem] = []
    missing: list[str] = []
    for relative in REQUIRED_FILES:
        path = _root_path(relative)
        if path.exists():
            rows.append(_item(f"file:{relative}", PASS, "Required file exists.", "files"))
        else:
            missing.append(relative)
            rows.append(_item(f"file:{relative}", FAIL, "Required file is missing.", "files"))
    rows.append(_item(
        "required-file-surface",
        FAIL if missing else PASS,
        f"{len(missing)} required file(s) missing." if missing else "All required checkpoint files are present.",
        "files",
        {"missing": missing},
    ))
    return rows


def _check_json_files() -> list[CheckpointItem]:
    rows: list[CheckpointItem] = []
    for relative in JSON_FILES:
        path = _root_path(relative)
        if not path.exists():
            rows.append(_item(f"json:{relative}", WARN, "JSON file is missing; it may be optional or generated later.", "json"))
            continue
        try:
            data = _load_json_file(path)
        except Exception as error:
            rows.append(_item(f"json:{relative}", FAIL, f"JSON parse failed: {error}", "json"))
            continue
        shape = "list" if isinstance(data, list) else "dict" if isinstance(data, dict) else type(data).__name__
        count = len(data) if isinstance(data, (dict, list)) else 0
        rows.append(_item(f"json:{relative}", PASS, f"JSON parsed as {shape} with {count} top-level item(s).", "json", {"shape": shape, "count": count}))
    return rows


def _check_python_compile() -> CheckpointItem:
    failures: list[str] = []
    paths = sorted((ROOT_DIR / "conscious_agent").glob("*.py")) + [ROOT_DIR / "tools" / "smoke_check.py"]
    for path in paths:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(f"{path.relative_to(ROOT_DIR)}: {error.msg}")
    if failures:
        return _item("python-compile", FAIL, f"{len(failures)} Python file(s) failed to compile.", "code", {"failures": failures})
    return _item("python-compile", PASS, f"Compiled {len(paths)} Python file(s).", "code", {"compiled_count": len(paths)})


def _check_core_imports() -> list[CheckpointItem]:
    rows: list[CheckpointItem] = []
    for module in CORE_IMPORTS:
        try:
            importlib.import_module(module)
        except Exception as error:
            rows.append(_item(f"import:{module}", FAIL, f"Core import failed: {error}", "imports", {"error": repr(error)}))
        else:
            rows.append(_item(f"import:{module}", PASS, "Core module imports cleanly.", "imports"))
    return rows


def _check_environment_imports() -> list[CheckpointItem]:
    rows: list[CheckpointItem] = []
    requirements_text = ""
    requirements = ROOT_DIR / "requirements.txt"
    if requirements.exists():
        requirements_text = requirements.read_text(encoding="utf-8", errors="replace").lower()
    for module in ENVIRONMENT_IMPORTS:
        listed = module.lower() in requirements_text
        try:
            importlib.import_module(module)
        except Exception as error:
            rows.append(_item(
                f"environment:{module}",
                WARN,
                f"Environment package import failed: {error}. {'It is listed in requirements.txt.' if listed else 'It is not listed in requirements.txt.'}",
                "environment",
                {"listed_in_requirements": listed, "error": repr(error)},
            ))
        else:
            rows.append(_item(
                f"environment:{module}",
                PASS,
                "Environment package imports cleanly.",
                "environment",
                {"listed_in_requirements": listed},
            ))
    return rows


def _check_settings() -> list[CheckpointItem]:
    from settings_manager import DEFAULT_SETTINGS, load_settings

    settings = load_settings()
    rows: list[CheckpointItem] = []
    rows.append(_item(
        "settings-load",
        PASS,
        f"Loaded settings schema {settings.get('settings_version')}.",
        "settings",
        {"settings_version": settings.get("settings_version")},
    ))
    safe_mode = str(settings.get("safe_mode") or "")
    rows.append(_item(
        "settings-safe-mode",
        PASS if safe_mode == "strict" else FAIL,
        "safe_mode is strict." if safe_mode == "strict" else f"safe_mode should be strict, found {safe_mode!r}.",
        "settings",
        {"safe_mode": safe_mode},
    ))
    missing_defaults = [key for key in DEFAULT_SETTINGS if key not in settings]
    rows.append(_item(
        "settings-default-coverage",
        FAIL if missing_defaults else PASS,
        f"Missing {len(missing_defaults)} default setting(s)." if missing_defaults else "All default settings are represented.",
        "settings",
        {"missing_defaults": missing_defaults},
    ))
    return rows


def _check_command_whitelist() -> list[CheckpointItem]:
    from command_runner import ALLOWED_MAIN_FLAGS

    missing = [flag for flag in EXPECTED_CLI_FLAGS if flag not in ALLOWED_MAIN_FLAGS]
    return [_item(
        "command-whitelist-stabilization-flags",
        FAIL if missing else PASS,
        f"Missing stabilization flag(s) from command whitelist: {', '.join(missing)}" if missing else "Stabilization CLI flags are whitelisted for safe command-runner inspection.",
        "safety",
        {"missing_flags": missing},
    )]


def _check_task_loop(project_id: str) -> list[CheckpointItem]:
    from task_cycle_policy import choose_next_cycle_decision, list_cycle_candidates
    from task_lifecycle import task_lifecycle_summary
    from task_queue import list_tasks, task_status_counts
    from task_recovery import task_recovery_summary

    rows: list[CheckpointItem] = []
    tasks = list_tasks(project=project_id, include_cancelled=True)
    counts = task_status_counts()
    lifecycle = task_lifecycle_summary(project=project_id, stage_filter="all")
    recovery = task_recovery_summary(project=project_id)
    decision = choose_next_cycle_decision(project=project_id)
    candidates = list_cycle_candidates(project=project_id)

    rows.append(_item("task-queue-load", PASS, f"Loaded {len(tasks)} task(s).", "tasks", {"status_counts": counts}))
    rows.append(_item(
        "task-lifecycle-summary",
        PASS if "counts" in lifecycle and "filtered_total" in lifecycle else FAIL,
        "Task lifecycle summary is available." if "counts" in lifecycle and "filtered_total" in lifecycle else "Task lifecycle summary shape is incomplete.",
        "tasks",
        {"summary_keys": sorted(lifecycle.keys())},
    ))
    rows.append(_item(
        "task-recovery-summary",
        PASS if "recoverable" in recovery and "categories" in recovery else FAIL,
        "Task recovery summary is available." if "recoverable" in recovery and "categories" in recovery else "Task recovery summary shape is incomplete.",
        "tasks",
        {"recoverable": recovery.get("recoverable"), "categories": recovery.get("categories")},
    ))
    rows.append(_item(
        "cycle-policy-decision",
        PASS if getattr(decision, "action", "") else FAIL,
        f"Cycle policy selected action: {getattr(decision, 'action', '[none]')}.",
        "tasks",
        {"decision": decision.to_dict() if hasattr(decision, "to_dict") else str(decision), "candidate_count": len(candidates)},
    ))
    return rows


def _check_stable_loop(project_id: str, max_steps: int) -> list[CheckpointItem]:
    from stable_loop_decision_report import stable_loop_decision_summary
    from stable_loop_followup_completion import stable_loop_followup_completion_summary
    from stable_loop_followup_lifecycle import stable_loop_followup_lifecycle_summary
    from stable_loop_guardrails import stable_loop_guardrail_summary
    from stable_loop_review import stable_loop_review_summary
    from stable_supervised_loop import build_stable_loop_preflight

    rows: list[CheckpointItem] = []
    preflight = build_stable_loop_preflight(project_id=project_id, max_steps=max_steps)
    guardrails = stable_loop_guardrail_summary(project_id=project_id)
    reviews = stable_loop_review_summary()
    decisions = stable_loop_decision_summary(decision_filter="all")
    followup_lifecycle = stable_loop_followup_lifecycle_summary(decision_filter="all")
    completion = stable_loop_followup_completion_summary(completion_filter="all")

    rows.append(_item(
        "stable-loop-preflight",
        PASS if "next_decision" in preflight and "lifecycle_summary" in preflight else FAIL,
        "Stable-loop preflight returns next decision and lifecycle summary." if "next_decision" in preflight and "lifecycle_summary" in preflight else "Stable-loop preflight shape is incomplete.",
        "stable-loop",
        {"ok": preflight.get("ok"), "next_action": (preflight.get("next_decision") or {}).get("action")},
    ))
    rows.append(_item(
        "stable-loop-closure-guardrails",
        PASS if guardrails.get("ok_for_live") else WARN,
        guardrails.get("message", "Stable-loop guardrails checked."),
        "stable-loop",
        {
            "ok_for_preview": guardrails.get("ok_for_preview"),
            "ok_for_live": guardrails.get("ok_for_live"),
            "unresolved_count": guardrails.get("unresolved_count"),
            "warnings": guardrails.get("warnings"),
        },
    ))
    rows.append(_item(
        "stable-loop-review-summary",
        PASS if "counts" in reviews else FAIL,
        "Stable-loop review summary is available." if "counts" in reviews else "Stable-loop review summary shape is incomplete.",
        "stable-loop",
        {"counts": reviews.get("counts")},
    ))
    rows.append(_item(
        "stable-loop-decision-summary",
        PASS if "counts" in decisions else FAIL,
        "Stable-loop decision report is available." if "counts" in decisions else "Stable-loop decision report shape is incomplete.",
        "stable-loop",
        {"counts": decisions.get("counts")},
    ))
    rows.append(_item(
        "stable-loop-followup-lifecycle",
        PASS if "ready_to_resolve_loop_count" in followup_lifecycle else FAIL,
        "Stable-loop follow-up lifecycle summary is available." if "ready_to_resolve_loop_count" in followup_lifecycle else "Stable-loop follow-up lifecycle shape is incomplete.",
        "stable-loop",
        {"ready_to_resolve_loop_count": followup_lifecycle.get("ready_to_resolve_loop_count")},
    ))
    rows.append(_item(
        "stable-loop-followup-completion",
        PASS if "cleanup_candidate_count" in completion else FAIL,
        "Stable-loop follow-up completion report is available." if "cleanup_candidate_count" in completion else "Stable-loop follow-up completion shape is incomplete.",
        "stable-loop",
        {
            "unresolved_count": completion.get("unresolved_count"),
            "cleanup_candidate_count": completion.get("cleanup_candidate_count"),
        },
    ))
    return rows


def _check_api_dashboard_surface() -> list[CheckpointItem]:
    rows: list[CheckpointItem] = []
    api_source = (ROOT_DIR / "conscious_agent" / "api_server.py").read_text(encoding="utf-8", errors="replace")
    dashboard_source = (ROOT_DIR / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8", errors="replace")
    main_source = (ROOT_DIR / "conscious_agent" / "main.py").read_text(encoding="utf-8", errors="replace")

    missing_flags = [flag for flag in EXPECTED_CLI_FLAGS if flag not in main_source]
    rows.append(_item(
        "cli-stabilization-surface",
        FAIL if missing_flags else PASS,
        f"Missing CLI flag(s): {', '.join(missing_flags)}" if missing_flags else "Stabilization checkpoint CLI flags are present.",
        "surface",
        {"missing_flags": missing_flags},
    ))

    missing_api = [endpoint for endpoint in EXPECTED_API_ENDPOINTS if endpoint not in api_source]
    rows.append(_item(
        "api-stabilization-surface",
        FAIL if missing_api else PASS,
        f"Missing API endpoint documentation/surface: {', '.join(missing_api)}" if missing_api else "Checkpoint API route and related loop endpoints are documented.",
        "surface",
        {"missing_endpoints": missing_api},
    ))

    missing_routes = [route for route in EXPECTED_DASHBOARD_ROUTES if route not in dashboard_source]
    rows.append(_item(
        "dashboard-stabilization-surface",
        FAIL if missing_routes else PASS,
        f"Missing dashboard route(s): {', '.join(missing_routes)}" if missing_routes else "Checkpoint dashboard route and core dashboard routes are present.",
        "surface",
        {"missing_routes": missing_routes},
    ))

    api_prefix_fixed = "path == \"/api\" or path.startswith(\"/api/\")" in dashboard_source
    rows.append(_item(
        "dashboard-api-prefix-routing",
        PASS if api_prefix_fixed else FAIL,
        "Dashboard API routing uses exact /api or /api/... matching, so /api-info stays human-readable." if api_prefix_fixed else "Dashboard API routing may still swallow /api-info.",
        "surface",
    ))
    return rows


def _check_smoke_readiness() -> list[CheckpointItem]:
    smoke = ROOT_DIR / "tools" / "smoke_check.py"
    if not smoke.exists():
        return [_item("smoke-check-script", FAIL, "tools/smoke_check.py is missing.", "smoke")]
    text = smoke.read_text(encoding="utf-8", errors="replace")
    checks = {
        "stabilization command": "--stabilization-checkpoint" in text,
        "stable loop guardrails": "check_stable_loop_guardrails" in text,
        "stable loop preflight": "--stable-loop-preflight" in text,
        "project intelligence": "check_project_intelligence" in text,
        "workspace orchestration": "check_workspace_orchestration" in text,
        "environment warning helper": "check_environment_import" in text,
    }
    missing = [name for name, ok in checks.items() if not ok]
    return [_item(
        "smoke-check-readiness",
        FAIL if missing else PASS,
        f"Smoke check is missing: {', '.join(missing)}" if missing else "Smoke check covers stabilization, guardrails, preflight, and environment warnings.",
        "smoke",
        {"checks": checks},
    )]


def _count_statuses(items: list[CheckpointItem]) -> dict[str, int]:
    counts = {PASS: 0, WARN: 0, FAIL: 0}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts


def _overall_status(counts: dict[str, int]) -> str:
    if counts.get(FAIL, 0):
        return FAIL
    if counts.get(WARN, 0):
        return WARN
    return PASS


def build_stabilization_checkpoint(project_id: str = DEFAULT_PROJECT_ID, full: bool = False) -> dict[str, Any]:
    """Build a read-only v7.0 stabilization checkpoint report."""
    project = (project_id or DEFAULT_PROJECT_ID).strip() or DEFAULT_PROJECT_ID
    items: list[CheckpointItem] = []

    _run_check(items, "required files", "files", _check_required_files)
    _run_check(items, "json files", "json", _check_json_files)
    _run_check(items, "python compile", "code", _check_python_compile)
    _run_check(items, "environment imports", "environment", _check_environment_imports)
    _run_check(items, "core imports", "imports", _check_core_imports)
    _run_check(items, "settings", "settings", _check_settings)
    _run_check(items, "command whitelist", "safety", _check_command_whitelist)
    _run_check(items, "task loop", "tasks", lambda: _check_task_loop(project))
    _run_check(items, "stable loop", "stable-loop", lambda: _check_stable_loop(project, max_steps=1))
    _run_check(items, "api/dashboard surface", "surface", _check_api_dashboard_surface)
    _run_check(items, "smoke readiness", "smoke", _check_smoke_readiness)

    counts = _count_statuses(items)
    overall = _overall_status(counts)
    blockers = [item.to_dict() for item in items if item.status == FAIL]
    warnings = [item.to_dict() for item in items if item.status == WARN]

    report: dict[str, Any] = {
        "ok": overall != FAIL,
        "status": overall,
        "version": STABILIZATION_CHECKPOINT_VERSION,
        "checked_at": _now(),
        "project_id": project,
        "counts": counts,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "recommended_commands": RECOMMENDED_COMMANDS,
        "message": _message_for_status(overall, counts),
    }
    report["items"] = [item.to_dict() for item in items] if full else [
        item.to_dict() for item in items if item.status in {WARN, FAIL}
    ]
    return report


def _message_for_status(status: str, counts: dict[str, int]) -> str:
    if status == FAIL:
        return f"Stabilization checkpoint failed with {counts.get(FAIL, 0)} blocker(s) and {counts.get(WARN, 0)} warning(s)."
    if status == WARN:
        return f"Stabilization checkpoint passed code checks with {counts.get(WARN, 0)} warning(s)."
    return "Stabilization checkpoint passed. No blockers or warnings found. Suspiciously competent."


def stabilization_checkpoint_text(data: dict[str, Any] | None = None, full: bool = False) -> str:
    report = data or build_stabilization_checkpoint(full=full)
    counts = report.get("counts") or {}
    lines = [
        "# Eidolon v15.0 Stabilization Checkpoint",
        "",
        f"Version: {report.get('version', STABILIZATION_CHECKPOINT_VERSION)}",
        f"Project: {report.get('project_id', DEFAULT_PROJECT_ID)}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status', '')).upper()}",
        f"Pass: {counts.get(PASS, 0)} | Warn: {counts.get(WARN, 0)} | Fail: {counts.get(FAIL, 0)}",
        f"Message: {report.get('message', '')}",
    ]

    blockers = report.get("blockers") or []
    warnings = report.get("warnings") or []
    if blockers:
        lines.extend(["", "## Blockers"])
        for item in blockers:
            lines.append(f"- [{str(item.get('category', 'general')).upper()}] {item.get('name')}: {item.get('message')}")
    if warnings:
        lines.extend(["", "## Warnings"])
        for item in warnings:
            lines.append(f"- [{str(item.get('category', 'general')).upper()}] {item.get('name')}: {item.get('message')}")

    commands = report.get("recommended_commands") or []
    if commands:
        lines.extend(["", "## Recommended verification commands"])
        lines.extend(f"- {command}" for command in commands)

    if full:
        items = report.get("items") or []
        lines.extend(["", "## Full check items"])
        for item in items:
            lines.append(f"- {str(item.get('status', '')).upper()} [{item.get('category')}] {item.get('name')}: {item.get('message')}")
        lines.extend(["", "## Raw checkpoint", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_stabilization_checkpoint(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_stabilization_checkpoint(project_id=project_id, full=full or json_output)
    if json_output:
        print(json.dumps(report, indent=2, default=str))
        return
    print(stabilization_checkpoint_text(report, full=full))
