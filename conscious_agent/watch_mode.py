from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from approval_manager import list_approvals
from diagnostics import build_diagnostic_report, save_diagnostic_report
from local_brain import local_generate
from maintenance_advisor import list_maintenance_scans, run_maintenance_scan
from memory import load_memories, store_memory
from notification_manager import create_notifications_from_watch_report
from patch_suggester import list_patch_proposals
from paths import DATA_DIR
from session_planner import create_session_plan, list_session_plans
from settings_manager import get_setting
from task_queue import list_tasks
from test_report_reviewer import list_test_reviews
from test_runner import list_test_reports


WATCH_REPORTS_DIR = DATA_DIR / "watch_reports"
PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


@dataclass
class WatchRunResult:
    ok: bool
    report_id: str = ""
    status: str = ""
    recommendation_count: int = 0
    text: str = ""
    error: str = ""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_report_id() -> str:
    return f"watch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _ensure_storage() -> None:
    WATCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    readme = WATCH_REPORTS_DIR / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Watch Reports\n\n"
            "Saved background watch-mode reports. Watch mode inspects Eidolon's state and creates recommendations. "
            "It does not apply patches, rollback files, run destructive commands, or bypass approval gates.\n",
            encoding="utf-8",
        )


def _report_path(report_id: str) -> Path:
    _ensure_storage()
    return WATCH_REPORTS_DIR / f"{report_id}.json"


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_watch_report(report: dict[str, Any]) -> Path:
    _ensure_storage()
    path = _report_path(str(report.get("id") or _new_report_id()))
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    return path


def list_watch_reports() -> list[dict[str, Any]]:
    _ensure_storage()
    reports: list[dict[str, Any]] = []
    for path in WATCH_REPORTS_DIR.glob("*.json"):
        data = _load_json_file(path)
        if data:
            reports.append(data)
    return sorted(reports, key=lambda item: str(item.get("created_at", "")), reverse=True)


def resolve_watch_report_id(report_id: str) -> str:
    token = (report_id or "latest").strip()
    lowered = token.lower()
    reports = list_watch_reports()

    if lowered in {"latest", "last"}:
        return reports[0].get("id", "") if reports else ""

    if lowered.startswith("latest-"):
        desired = lowered.replace("latest-", "", 1)
        for report in reports:
            if str(report.get("status", "")).lower() == desired:
                return str(report.get("id", ""))
        return ""

    for report in reports:
        if report.get("id") == token:
            return token
    return token


def load_watch_report(report_id: str) -> dict[str, Any] | None:
    resolved = resolve_watch_report_id(report_id)
    if not resolved:
        return None
    return _load_json_file(_report_path(resolved))


def _latest_by_id(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return items[0] if items else None


def _recommendation(
    priority: str,
    category: str,
    title: str,
    reason: str,
    command: str = "",
    risk: str = "low",
) -> dict[str, Any]:
    return {
        "priority": priority,
        "category": category,
        "title": title,
        "reason": reason,
        "recommended_command": command,
        "risk": risk,
    }


def _patch_ids_with_reports(reports: list[dict[str, Any]]) -> set[str]:
    return {str(report.get("patch_id", "")) for report in reports if report.get("patch_id")}


def _report_ids_with_reviews(reviews: list[dict[str, Any]]) -> set[str]:
    return {str(review.get("report_id", "")) for review in reviews if review.get("report_id")}


def _build_recommendations(
    diagnostics_report: dict[str, Any],
    approvals: list[dict[str, Any]],
    patches: list[dict[str, Any]],
    test_reports: list[dict[str, Any]],
    test_reviews: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    memory_count: int,
    created_maintenance_scan: dict[str, Any] | None,
    created_session_plan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []

    diag_status = str(diagnostics_report.get("overall_status", "info")).lower()
    if diag_status == "fail":
        recommendations.append(_recommendation(
            "critical",
            "diagnostics",
            "Fix failing diagnostics before continuing",
            diagnostics_report.get("recommendation", "Diagnostics reported failures."),
            "python conscious_agent/main.py --show-diagnostic-report latest --diagnostics-full",
            "low",
        ))
    elif diag_status == "warn":
        recommendations.append(_recommendation(
            "medium",
            "diagnostics",
            "Review diagnostic warnings",
            diagnostics_report.get("recommendation", "Diagnostics reported warnings."),
            "python conscious_agent/main.py --show-diagnostic-report latest --diagnostics-full",
            "low",
        ))

    pending_approvals = [approval for approval in approvals if approval.get("status") == "pending"]
    if pending_approvals:
        recommendations.append(_recommendation(
            "high",
            "approvals",
            "Review pending approvals",
            f"There are {len(pending_approvals)} pending approval request(s).",
            "python conscious_agent/main.py --approval-inbox",
            "medium",
        ))

    proposed_patches = [patch for patch in patches if patch.get("status") == "proposed"]
    if proposed_patches:
        recommendations.append(_recommendation(
            "high",
            "patches",
            "Inspect latest proposed patch",
            f"There are {len(proposed_patches)} proposed patch(es) waiting for review.",
            "python conscious_agent/main.py --show-patch latest-proposed",
            proposed_patches[0].get("risk_level", "medium"),
        ))

    report_patch_ids = _patch_ids_with_reports(test_reports)
    applied_without_reports = [
        patch for patch in patches
        if patch.get("status") == "applied" and patch.get("id") not in report_patch_ids
    ]
    if applied_without_reports:
        patch_id = applied_without_reports[0].get("id", "latest-applied")
        recommendations.append(_recommendation(
            "high",
            "testing",
            "Run tests for an applied patch",
            f"Applied patch {patch_id} has no saved test report.",
            f"python conscious_agent/main.py --run-test-workflow {patch_id} --auto-review",
            "low",
        ))

    reviewed_report_ids = _report_ids_with_reviews(test_reviews)
    unreviewed_reports = [
        report for report in test_reports
        if report.get("id") and report.get("id") not in reviewed_report_ids
    ]
    if unreviewed_reports:
        report_id = unreviewed_reports[0].get("id")
        recommendations.append(_recommendation(
            "medium",
            "test_reviews",
            "Review latest unreviewed test report",
            f"Test report {report_id} has no saved review.",
            f"python conscious_agent/main.py --review-test-report {report_id}",
            "low",
        ))

    blocked_tasks = [task for task in tasks if task.get("status") == "blocked"]
    if blocked_tasks:
        recommendations.append(_recommendation(
            "medium",
            "tasks",
            "Review blocked tasks",
            f"There are {len(blocked_tasks)} blocked task(s).",
            "python conscious_agent/main.py --list-tasks --task-filter-status blocked",
            "low",
        ))

    ready_tasks = [task for task in tasks if task.get("status") == "ready"]
    active_tasks = [task for task in tasks if task.get("status") == "active"]
    if ready_tasks:
        recommendations.append(_recommendation(
            "medium",
            "tasks",
            "Continue the next ready task",
            f"There are {len(ready_tasks)} ready task(s).",
            "python conscious_agent/main.py --guided-work-session latest-ready",
            "low",
        ))
    elif active_tasks:
        recommendations.append(_recommendation(
            "medium",
            "tasks",
            "Continue the active task",
            f"There are {len(active_tasks)} active task(s).",
            "python conscious_agent/main.py --guided-work-session latest-active",
            "low",
        ))
    else:
        recommendations.append(_recommendation(
            "medium",
            "planning",
            "Create or queue a next task",
            "No ready or active task was found.",
            "python conscious_agent/main.py --plan-session --no-ai-session",
            "low",
        ))

    min_memories = int(get_setting("memory_min_count", 80))
    if memory_count >= min_memories:
        recommendations.append(_recommendation(
            "medium",
            "memory",
            "Preview memory compaction",
            f"Active memory count is {memory_count}, meeting or exceeding threshold {min_memories}.",
            "python conscious_agent/main.py --compact-memory --dry-run",
            "low",
        ))

    if created_maintenance_scan:
        suggestion_count = len(created_maintenance_scan.get("suggestions", []) or [])
        if suggestion_count:
            recommendations.append(_recommendation(
                "low",
                "maintenance",
                "Review latest maintenance scan",
                f"Watch mode created maintenance scan {created_maintenance_scan.get('id')} with {suggestion_count} suggestion(s).",
                "python conscious_agent/main.py --show-maintenance-scan latest --show-maintenance-full",
                "low",
            ))

    if created_session_plan:
        primary = created_session_plan.get("primary_recommendation") or {}
        if primary:
            recommendations.append(_recommendation(
                "low",
                "session_plan",
                "Review latest session plan",
                f"Watch mode created session plan {created_session_plan.get('id')}.",
                "python conscious_agent/main.py --show-session-plan latest --show-session-plan-full",
                "low",
            ))

    return sorted(recommendations, key=lambda item: PRIORITY_RANK.get(str(item.get("priority", "low")), 3))


def _watch_ai_summary(report: dict[str, Any]) -> str:
    safe_context = {
        "status": report.get("status"),
        "summary_counts": report.get("summary_counts"),
        "top_recommendations": report.get("recommendations", [])[:8],
        "safe_next_command": report.get("safe_next_command"),
    }
    prompt = f"""
You are Eidolon, summarizing a background watch-mode report for Marcus.

WATCH REPORT JSON:
{json.dumps(safe_context, indent=2)}

Write a concise status note under 160 words.
Include:
1. whether attention is needed
2. the safest next command
3. what not to do automatically
Do not sign off like an email.
""".strip()
    output = local_generate(prompt=prompt, temperature=0.25, max_tokens=230)
    if output.startswith("I tried to use my local brain") or output.startswith("My local brain"):
        return output
    return output.strip()


def _report_status(diagnostic_status: str, recommendations: list[dict[str, Any]]) -> str:
    if diagnostic_status == "fail":
        return "error"
    if any(item.get("priority") in {"critical", "high"} for item in recommendations):
        return "attention_needed"
    if recommendations:
        return "watching"
    return "healthy"


def run_watch_once(
    use_ai: bool = True,
    create_maintenance: bool = True,
    create_session: bool = True,
) -> WatchRunResult:
    """
    Runs one read-mostly background watch cycle.

    Watch mode may create safe report artifacts: diagnostics, maintenance scans, and
    session plans. It does not apply patches, rollback files, execute approvals, or
    bypass command/file safety gates.
    """
    _ensure_storage()
    created_at = _now()

    diagnostics_report = build_diagnostic_report(include_full=True)
    save_diagnostic_report(diagnostics_report)

    approvals = list_approvals(include_closed=True)
    patches = list_patch_proposals()
    test_reports = list_test_reports()
    test_reviews = list_test_reviews()
    tasks = list_tasks(include_cancelled=False)
    memories = load_memories()

    maintenance_result = None
    created_maintenance_scan = None
    if create_maintenance:
        maintenance_result = run_maintenance_scan(use_ai=False)
        if maintenance_result.ok:
            scans = list_maintenance_scans()
            created_maintenance_scan = scans[0] if scans else None

    session_result = None
    created_session_plan = None
    no_ready_or_active_tasks = not any(task.get("status") in {"ready", "active"} for task in tasks)
    if create_session and no_ready_or_active_tasks:
        session_result = create_session_plan(use_ai=False)
        if session_result.ok:
            plans = list_session_plans()
            created_session_plan = plans[0] if plans else None

    recommendations = _build_recommendations(
        diagnostics_report=diagnostics_report,
        approvals=approvals,
        patches=patches,
        test_reports=test_reports,
        test_reviews=test_reviews,
        tasks=tasks,
        memory_count=len(memories),
        created_maintenance_scan=created_maintenance_scan,
        created_session_plan=created_session_plan,
    )

    status = _report_status(str(diagnostics_report.get("overall_status", "info")), recommendations)
    safe_next_command = recommendations[0].get("recommended_command", "") if recommendations else "python conscious_agent/main.py --dev-loop --dry-run --no-ai-dev-loop"

    report = {
        "id": _new_report_id(),
        "type": "background_watch_report",
        "created_at": created_at,
        "status": status,
        "use_ai": use_ai,
        "diagnostic_report_id": diagnostics_report.get("id"),
        "diagnostic_status": diagnostics_report.get("overall_status"),
        "created_maintenance_scan_id": created_maintenance_scan.get("id") if created_maintenance_scan else "",
        "created_session_plan_id": created_session_plan.get("id") if created_session_plan else "",
        "summary_counts": {
            "pending_approvals": len([a for a in approvals if a.get("status") == "pending"]),
            "total_approvals": len(approvals),
            "proposed_patches": len([p for p in patches if p.get("status") == "proposed"]),
            "applied_patches": len([p for p in patches if p.get("status") == "applied"]),
            "test_reports": len(test_reports),
            "test_reviews": len(test_reviews),
            "ready_tasks": len([t for t in tasks if t.get("status") == "ready"]),
            "active_tasks": len([t for t in tasks if t.get("status") == "active"]),
            "blocked_tasks": len([t for t in tasks if t.get("status") == "blocked"]),
            "active_memories": len(memories),
        },
        "recommendations": recommendations,
        "safe_next_command": safe_next_command,
        "notes": [
            "Watch mode is advisory. It does not apply patches, rollback files, or approve actions automatically.",
            "Use approval commands or dev-loop commands explicitly when you want Eidolon to act.",
        ],
        "created_artifacts": {
            "diagnostic_report_id": diagnostics_report.get("id"),
            "maintenance_scan_result": getattr(maintenance_result, "__dict__", None) if maintenance_result else None,
            "session_plan_result": getattr(session_result, "__dict__", None) if session_result else None,
        },
    }

    if use_ai:
        report["ai_summary"] = _watch_ai_summary(report)
    else:
        report["ai_summary"] = ""

    path = save_watch_report(report)

    notifications = create_notifications_from_watch_report(report)
    report["created_notification_ids"] = [note.get("id") for note in notifications]
    if notifications:
        save_watch_report(report)

    store_memory({
        "type": "watch_report_event",
        "content": (
            f"Created watch report {report['id']} with status {status} and "
            f"{len(recommendations)} recommendation(s)."
        ),
        "source": "watch_mode",
        "watch_report_id": report["id"],
        "status": status,
        "recommendation_count": len(recommendations),
        "notification_count": len(notifications),
    })

    return WatchRunResult(
        ok=True,
        report_id=report["id"],
        status=status,
        recommendation_count=len(recommendations),
        text=watch_report_text(report),
    )


def run_watch_loop(
    cycles: int = 3,
    interval_seconds: int = 300,
    use_ai: bool = True,
    create_maintenance: bool = True,
    create_session: bool = True,
) -> dict[str, Any]:
    max_cycles = int(get_setting("watch_max_cycles", 10))
    cycles = max(1, min(int(cycles), max_cycles))
    interval_seconds = max(1, int(interval_seconds))

    loop = {
        "id": f"watchloop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "background_watch_loop",
        "created_at": _now(),
        "cycles_requested": cycles,
        "interval_seconds": interval_seconds,
        "use_ai": use_ai,
        "reports": [],
        "stopped_reason": "completed",
    }

    for index in range(cycles):
        result = run_watch_once(
            use_ai=use_ai,
            create_maintenance=create_maintenance,
            create_session=create_session,
        )
        loop["reports"].append({
            "cycle": index + 1,
            "ok": result.ok,
            "report_id": result.report_id,
            "status": result.status,
            "recommendation_count": result.recommendation_count,
        })

        # Keep loops bounded and non-annoying. If attention is needed, stop instead of
        # repeatedly generating the same report and pretending that is agency.
        if result.status in {"error", "attention_needed"}:
            loop["stopped_reason"] = "attention_needed"
            break

        if index < cycles - 1:
            time.sleep(interval_seconds)

    loop["finished_at"] = _now()
    loop["cycle_count"] = len(loop["reports"])
    path = save_watch_report(loop)
    loop["saved_path"] = str(path)

    store_memory({
        "type": "watch_loop_event",
        "content": f"Ran watch loop {loop['id']} for {loop['cycle_count']} cycle(s). Stopped: {loop['stopped_reason']}.",
        "source": "watch_mode",
        "watch_loop_id": loop["id"],
        "stopped_reason": loop["stopped_reason"],
    })
    return loop


def watch_report_text(report: dict[str, Any], full: bool = False, include_ai: bool = True) -> str:
    if not report:
        return "Watch report not found."

    if report.get("type") == "background_watch_loop":
        lines = [
            f"# Watch Loop: {report.get('id')}",
            f"Created: {report.get('created_at')}",
            f"Finished: {report.get('finished_at', '')}",
            f"Cycles: {report.get('cycle_count', len(report.get('reports', [])))} / {report.get('cycles_requested')}",
            f"Interval seconds: {report.get('interval_seconds')}",
            f"Stopped reason: {report.get('stopped_reason')}",
            "",
            "Reports:",
        ]
        for item in report.get("reports", []):
            lines.append(
                f"- cycle {item.get('cycle')}: {item.get('report_id')} | "
                f"status={item.get('status')} | recommendations={item.get('recommendation_count')}"
            )
        if full:
            lines.extend(["", "## Raw watch loop", json.dumps(report, indent=2)])
        return "\n".join(lines)

    lines = [
        f"# Watch Report: {report.get('id')}",
        f"Created: {report.get('created_at')}",
        f"Status: {str(report.get('status', '')).upper()}",
        f"Diagnostic status: {report.get('diagnostic_status')}",
        f"Diagnostic report: {report.get('diagnostic_report_id')}",
    ]

    if report.get("created_maintenance_scan_id"):
        lines.append(f"Maintenance scan: {report.get('created_maintenance_scan_id')}")
    if report.get("created_session_plan_id"):
        lines.append(f"Session plan: {report.get('created_session_plan_id')}")
    if report.get("created_notification_ids"):
        lines.append(f"Notifications: {len(report.get('created_notification_ids') or [])}")

    lines.extend(["", "Summary counts:"])
    for key, value in (report.get("summary_counts") or {}).items():
        lines.append(f"- {key}: {value}")

    recommendations = report.get("recommendations", []) or []
    lines.extend(["", f"Recommendations: {len(recommendations)}"])
    if recommendations:
        for index, item in enumerate(recommendations[:12], start=1):
            lines.append(f"{index}. [{str(item.get('priority')).upper()}] {item.get('title')}")
            lines.append(f"   Reason: {item.get('reason')}")
            if item.get("recommended_command"):
                lines.append(f"   Command: {item.get('recommended_command')}")
    else:
        lines.append("- No attention-needed recommendations found.")

    if report.get("safe_next_command"):
        lines.extend(["", f"Safe next command: {report.get('safe_next_command')}"])

    if include_ai and report.get("ai_summary"):
        lines.extend(["", "## Local AI summary", report.get("ai_summary")])

    if full:
        lines.extend(["", "## Raw watch report", json.dumps(report, indent=2)])

    return "\n".join(lines)


def print_watch_once(use_ai: bool = True, full: bool = False) -> None:
    result = run_watch_once(use_ai=use_ai)
    print(result.text if not full else watch_report_text(load_watch_report(result.report_id) or {}, full=True))


def print_watch_loop(cycles: int, interval_seconds: int, use_ai: bool = True, full: bool = False) -> None:
    loop = run_watch_loop(cycles=cycles, interval_seconds=interval_seconds, use_ai=use_ai)
    print(watch_report_text(loop, full=full))


def print_watch_reports() -> None:
    reports = list_watch_reports()
    if not reports:
        print("No watch reports found.")
        return
    for report in reports:
        if report.get("type") == "background_watch_loop":
            print(
                f"{report.get('id')} | loop | {report.get('created_at')} | "
                f"cycles={report.get('cycle_count', len(report.get('reports', [])))} | stopped={report.get('stopped_reason')}"
            )
        else:
            print(
                f"{report.get('id')} | {report.get('created_at')} | "
                f"status={report.get('status')} | recommendations={len(report.get('recommendations', []) or [])}"
            )


def print_saved_watch_report(report_id: str = "latest", full: bool = False, include_ai: bool = True) -> None:
    report = load_watch_report(report_id)
    if not report:
        print(f"Watch report not found: {report_id}")
        return
    print(watch_report_text(report, full=full, include_ai=include_ai))
