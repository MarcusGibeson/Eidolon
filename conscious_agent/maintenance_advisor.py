from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from local_brain import local_generate
from memory import load_memories, store_memory
from patch_suggester import list_patch_proposals
from paths import DATA_DIR
from project_indexer import load_project_index
from project_manager import get_active_project
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports
from self_improver import list_self_improvement_runs


MAINTENANCE_DIR = DATA_DIR / "maintenance_suggestions"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"
MAX_AI_CONTEXT_CHARS = 14_000


@dataclass
class MaintenanceScanResult:
    ok: bool
    scan_id: str = ""
    suggestion_count: int = 0
    text: str = ""
    error: str = ""


def _ensure_storage() -> None:
    MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    readme = MAINTENANCE_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Maintenance Suggestions\n\n"
            "This folder stores read-only maintenance scan results. "
            "These scans suggest safe next tasks but do not edit files or run commands.\n",
            encoding="utf-8",
        )


def _scan_path(scan_id: str) -> Path:
    return MAINTENANCE_DIR / f"{scan_id}.json"


def _new_scan_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"maint_{timestamp}"


def save_maintenance_scan(scan: dict[str, Any]) -> None:
    _ensure_storage()
    with _scan_path(scan["id"]).open("w", encoding="utf-8") as file:
        json.dump(scan, file, indent=2)


def resolve_maintenance_scan_id(scan_id: str) -> str:
    token = (scan_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    scans = list_maintenance_scans()
    if not scans:
        return ""
    return scans[0].get("id", "")


def load_maintenance_scan(scan_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_maintenance_scan_id(scan_id)
    if not resolved_id:
        return None

    path = _scan_path(resolved_id)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def list_maintenance_scans() -> list[dict[str, Any]]:
    _ensure_storage()
    scans: list[dict[str, Any]] = []

    for path in sorted(MAINTENANCE_DIR.glob("maint_*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            scans.append(data)

    return scans


def _load_action_log() -> list[dict[str, Any]]:
    if not ACTION_LOG_FILE.exists():
        return []
    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _suggestion(
    priority: str,
    category: str,
    title: str,
    evidence: str,
    recommended_command: str = "",
    notes: str = "",
) -> dict[str, Any]:
    return {
        "priority": priority,
        "category": category,
        "title": title,
        "evidence": evidence,
        "recommended_command": recommended_command,
        "notes": notes,
        "status": "suggested",
    }


def _project_index_suggestions(index: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    files = index.get("files", []) if isinstance(index, dict) else []

    if not index.get("indexed_at") or not files:
        suggestions.append(_suggestion(
            priority="high",
            category="project_index",
            title="Build or refresh the project index",
            evidence="No usable project index was found.",
            recommended_command="python conscious_agent/main.py --index-project conscious_agent",
            notes="A fresh index improves code review, patch suggestions, and project awareness.",
        ))
        return suggestions

    parse_error_files = []
    large_files = []
    missing_docstring_files = []

    for file in files:
        path = file.get("path", "")
        summary = file.get("summary", {})
        extension = file.get("extension", "")

        if extension == ".py" and summary.get("parse_error"):
            parse_error_files.append(path)

        line_count = summary.get("line_count") or 0
        if isinstance(line_count, int) and line_count > 350:
            large_files.append((path, line_count))

        if extension == ".py":
            functions = summary.get("functions", []) or []
            classes = summary.get("classes", []) or []
            if (functions or classes) and not summary.get("docstring_checked"):
                # The indexer does not track docstrings directly yet. Suggest code review for dense files.
                if len(functions) + len(classes) >= 8:
                    missing_docstring_files.append(path)

    if parse_error_files:
        suggestions.append(_suggestion(
            priority="high",
            category="code_health",
            title="Fix Python files with parse errors",
            evidence="Files with parse errors: " + ", ".join(parse_error_files[:6]),
            recommended_command=f"python conscious_agent/main.py --review-project-file {parse_error_files[0]} --no-ai-review",
            notes="Parse errors can break indexing, review, and future automation.",
        ))

    if large_files:
        largest = sorted(large_files, key=lambda item: item[1], reverse=True)[0]
        suggestions.append(_suggestion(
            priority="medium",
            category="code_health",
            title="Review large files for possible splitting",
            evidence=f"Largest indexed file: {largest[0]} with {largest[1]} lines.",
            recommended_command=f"python conscious_agent/main.py --review-project-file {largest[0]} --no-ai-review",
            notes="Large files are harder for local models to patch safely and easier for humans to ruin. Humanity adapts by making smaller messes.",
        ))

    if missing_docstring_files:
        target = missing_docstring_files[0]
        suggestions.append(_suggestion(
            priority="low",
            category="maintainability",
            title="Review dense modules for documentation clarity",
            evidence="Dense Python files found: " + ", ".join(missing_docstring_files[:6]),
            recommended_command=f"python conscious_agent/main.py --review-project-file {target} --no-ai-review",
            notes="This is advisory. Do not add docstrings everywhere just to appease the machine goblin.",
        ))

    return suggestions


def _patch_suggestions(patches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    proposed = [patch for patch in patches if patch.get("status") == "proposed"]
    applied = [patch for patch in patches if patch.get("status") == "applied"]
    high_risk = [patch for patch in proposed if patch.get("risk_level") == "high"]

    if proposed:
        suggestions.append(_suggestion(
            priority="medium",
            category="patch_workflow",
            title="Review proposed patches waiting for approval",
            evidence=f"There are {len(proposed)} proposed patch(es). Newest: {proposed[0].get('id')}",
            recommended_command="python conscious_agent/main.py --show-patch latest-proposed",
            notes="Review the diff before applying. Future-you deserves fewer surprises, allegedly.",
        ))

    if high_risk:
        suggestions.append(_suggestion(
            priority="high",
            category="patch_safety",
            title="Manually inspect high-risk patch proposals",
            evidence=f"High-risk proposed patch: {high_risk[0].get('id')} targeting {high_risk[0].get('target_file')}",
            recommended_command=f"python conscious_agent/main.py --show-patch {high_risk[0].get('id')}",
            notes="Do not apply high-risk patches through the comfort of optimism. Optimism has broken enough builds.",
        ))

    if applied:
        suggestions.append(_suggestion(
            priority="medium",
            category="testing",
            title="Run a test workflow for recently applied patches",
            evidence=f"There are {len(applied)} applied patch(es). Latest applied: {applied[0].get('id')}",
            recommended_command="python conscious_agent/main.py --run-test-workflow latest-applied --auto-review",
            notes="An applied patch without a test report is just a guess wearing a helmet.",
        ))

    return suggestions


def _test_suggestions(reports: list[dict[str, Any]], reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []

    if not reports:
        suggestions.append(_suggestion(
            priority="medium",
            category="testing",
            title="Run the default test workflow",
            evidence="No saved test reports were found.",
            recommended_command="python conscious_agent/main.py --run-test-workflow --auto-review",
            notes="This creates a baseline health check for the project.",
        ))
        return suggestions

    latest_report = reports[0]
    if latest_report.get("failed_commands", 0):
        suggestions.append(_suggestion(
            priority="high",
            category="testing",
            title="Investigate failing test workflow report",
            evidence=f"Latest report {latest_report.get('id')} has {latest_report.get('failed_commands')} failing command(s).",
            recommended_command="python conscious_agent/main.py --show-test-report latest --show-test-output",
            notes="Review output before applying more patches. Stacking changes on broken tests is how software becomes folklore.",
        ))

    if not reviews:
        suggestions.append(_suggestion(
            priority="medium",
            category="testing",
            title="Auto-review the latest test report",
            evidence=f"Latest test report {latest_report.get('id')} has not been paired with a saved review yet.",
            recommended_command="python conscious_agent/main.py --review-test-report latest",
            notes="The review summarizes whether to keep, rollback, or inspect manually.",
        ))

    return suggestions


def _memory_suggestions(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    count = len(memories)

    if count > 250:
        suggestions.append(_suggestion(
            priority="medium",
            category="memory",
            title="Summarize or compact long-term memory soon",
            evidence=f"Stored memories count is {count}.",
            recommended_command="",
            notes="A future memory compaction module should summarize older low-importance memories. Not implemented yet.",
        ))
    elif count > 100:
        suggestions.append(_suggestion(
            priority="low",
            category="memory",
            title="Monitor memory growth",
            evidence=f"Stored memories count is {count}.",
            recommended_command="python conscious_agent/main.py --semantic-search \"Eidolon project purpose\"",
            notes="Memory growth is expected, but future compaction will keep prompts smaller and cheaper.",
        ))

    return suggestions


def _action_log_suggestions(action_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    failures = [entry for entry in action_log if entry.get("status") in {"failed", "error"}]

    if failures:
        latest = failures[-1]
        suggestions.append(_suggestion(
            priority="medium",
            category="audit",
            title="Review recent failed actions",
            evidence=f"Found {len(failures)} failed/error action log entries. Latest action: {latest.get('action')}",
            recommended_command="python conscious_agent/main.py --command-history",
            notes="Repeated failures are good candidates for a targeted self-improvement run.",
        ))

    return suggestions


def _ai_maintenance_summary(scan_context: dict[str, Any]) -> str:
    context = json.dumps(scan_context, indent=2)[:MAX_AI_CONTEXT_CHARS]
    prompt = f"""
You are Eidolon, a supervised local AI coding assistant.

You are reviewing a read-only maintenance scan.
Do not claim you edited files or ran commands.
Do not propose destructive actions.
Focus on safe next steps Marcus can approve manually.

Maintenance scan context:
{context}

Write a concise maintenance summary with:
1. highest priority issue
2. safest next command
3. why it matters
4. what not to do yet

Keep it under 180 words.
""".strip()

    response = local_generate(prompt=prompt, temperature=0.25, max_tokens=260)
    if response.startswith("I tried to use my local brain") or response.startswith("My local brain"):
        return response
    return response.strip()


def run_maintenance_scan(use_ai: bool = True) -> MaintenanceScanResult:
    """
    Creates a read-only maintenance scan.

    This does not apply patches, rollback patches, run commands, or edit files.
    It only inspects saved metadata and proposes safe next steps.
    """
    _ensure_storage()

    active_project = get_active_project() or {}
    project_index = load_project_index()
    patches = list_patch_proposals()
    reports = list_test_reports()
    reviews = list_test_reviews()
    runs = list_self_improvement_runs()
    memories = load_memories()
    action_log = _load_action_log()

    suggestions: list[dict[str, Any]] = []
    suggestions.extend(_project_index_suggestions(project_index))
    suggestions.extend(_patch_suggestions(patches))
    suggestions.extend(_test_suggestions(reports, reviews))
    suggestions.extend(_memory_suggestions(memories))
    suggestions.extend(_action_log_suggestions(action_log))

    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda item: priority_order.get(item.get("priority", "low"), 2))

    scan_id = _new_scan_id()
    created_at = datetime.now().isoformat(timespec="seconds")

    scan_context = {
        "active_project": active_project,
        "project_indexed_at": project_index.get("indexed_at"),
        "indexed_file_count": len(project_index.get("files", [])) if isinstance(project_index, dict) else 0,
        "patch_count": len(patches),
        "test_report_count": len(reports),
        "test_review_count": len(reviews),
        "self_improvement_run_count": len(runs),
        "memory_count": len(memories),
        "action_log_count": len(action_log),
        "suggestions": suggestions,
    }

    ai_summary = _ai_maintenance_summary(scan_context) if use_ai else ""

    scan = {
        "id": scan_id,
        "created_at": created_at,
        "active_project": active_project.get("name"),
        "use_ai": use_ai,
        "summary": {
            "indexed_file_count": scan_context["indexed_file_count"],
            "patch_count": len(patches),
            "test_report_count": len(reports),
            "test_review_count": len(reviews),
            "self_improvement_run_count": len(runs),
            "memory_count": len(memories),
            "action_log_count": len(action_log),
        },
        "suggestions": suggestions,
        "ai_summary": ai_summary,
        "status": "suggested",
    }

    save_maintenance_scan(scan)

    store_memory({
        "type": "maintenance_scan_event",
        "content": f"Created maintenance scan {scan_id} with {len(suggestions)} suggestion(s).",
        "source": "maintenance_advisor",
        "scan_id": scan_id,
        "suggestion_count": len(suggestions),
    })

    return MaintenanceScanResult(
        ok=True,
        scan_id=scan_id,
        suggestion_count=len(suggestions),
        text=maintenance_scan_text(scan, include_ai=True),
    )


def maintenance_scan_text(scan: dict[str, Any], include_ai: bool = True, full: bool = False) -> str:
    suggestions = scan.get("suggestions", []) or []
    summary = scan.get("summary", {}) or {}

    lines = [
        f"# Maintenance Scan: {scan.get('id')}",
        "",
        f"Created: {scan.get('created_at')}",
        f"Active project: {scan.get('active_project')}",
        f"Suggestions: {len(suggestions)}",
        "",
        "## Snapshot",
        f"- Indexed files: {summary.get('indexed_file_count', 0)}",
        f"- Patches: {summary.get('patch_count', 0)}",
        f"- Test reports: {summary.get('test_report_count', 0)}",
        f"- Test reviews: {summary.get('test_review_count', 0)}",
        f"- Self-improvement runs: {summary.get('self_improvement_run_count', 0)}",
        f"- Memories: {summary.get('memory_count', 0)}",
        f"- Action log entries: {summary.get('action_log_count', 0)}",
        "",
        "## Suggestions",
    ]

    if not suggestions:
        lines.append("No maintenance suggestions found. Suspiciously tidy. Enjoy it while it lasts.")
    else:
        for index, suggestion in enumerate(suggestions, start=1):
            lines.extend([
                f"{index}. [{suggestion.get('priority', 'low').upper()}] {suggestion.get('title')}",
                f"   Category: {suggestion.get('category')}",
                f"   Evidence: {suggestion.get('evidence')}",
            ])
            command = suggestion.get("recommended_command")
            if command:
                lines.append(f"   Recommended command: {command}")
            if full and suggestion.get("notes"):
                lines.append(f"   Notes: {suggestion.get('notes')}")
            lines.append("")

    ai_summary = scan.get("ai_summary", "")
    if include_ai and ai_summary:
        lines.extend([
            "## Local AI Summary",
            ai_summary,
            "",
        ])

    lines.extend([
        "Shortcut commands:",
        "  python conscious_agent/main.py --show-maintenance-scan latest",
        "  python conscious_agent/main.py --maintenance-scan --no-ai-maintenance",
    ])

    return "\n".join(lines).strip()


def print_maintenance_scan(use_ai: bool = True) -> None:
    result = run_maintenance_scan(use_ai=use_ai)
    if not result.ok:
        print(f"Could not create maintenance scan: {result.error}")
        return
    print(result.text)
    print()
    print(f"Saved maintenance scan: {result.scan_id}")


def print_maintenance_scans() -> None:
    scans = list_maintenance_scans()
    if not scans:
        print("No maintenance scans found.")
        return

    for scan in scans:
        suggestions = scan.get("suggestions", []) or []
        high = len([item for item in suggestions if item.get("priority") == "high"])
        medium = len([item for item in suggestions if item.get("priority") == "medium"])
        low = len([item for item in suggestions if item.get("priority") == "low"])
        print(
            f"{scan.get('id')} | {scan.get('created_at')} | "
            f"suggestions={len(suggestions)} high={high} medium={medium} low={low}"
        )
        if suggestions:
            print(f"  Top: [{suggestions[0].get('priority')}] {suggestions[0].get('title')}")


def print_saved_maintenance_scan(scan_id: str, include_ai: bool = True, full: bool = False) -> None:
    scan = load_maintenance_scan(scan_id)
    if not scan:
        print(f"Maintenance scan not found: {scan_id}")
        return
    print(maintenance_scan_text(scan, include_ai=include_ai, full=full))
