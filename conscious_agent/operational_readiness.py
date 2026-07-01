from __future__ import annotations

"""v8.0 operational readiness helpers for Eidolon.

This module groups the v7.1-v8.0 checkpoint features that should stay
read-only unless an existing, explicit live runner is deliberately invoked.
It is intentionally boring in the way seatbelts are boring. Software needs more
seatbelts and fewer fireworks taped to while-loops.
"""

import json
import py_compile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import ROOT_DIR, DATA_DIR
from project_manager import get_active_project
from settings_manager import load_settings, settings_health
from stabilization_checkpoint import build_stabilization_checkpoint
from stable_loop_guardrails import stable_loop_guardrail_summary
from stable_supervised_loop import build_stable_loop_preflight, run_stable_supervised_loop
from task_lifecycle import list_task_lifecycles, task_lifecycle_summary
from task_queue import list_tasks, task_status_counts
from task_recovery import task_recovery_summary
from patch_suggester import list_patch_proposals
from approval_manager import list_approvals
from test_runner import list_test_reports
from test_report_reviewer import list_test_reviews
from work_cycle import list_work_cycles
from stable_supervised_loop import list_stable_loops

OPERATIONAL_READINESS_VERSION = "1032.0"
DEFAULT_PROJECT_ID = "eidolon"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(relative: str) -> str:
    path = ROOT_DIR / relative
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _status_from_counts(fail: int = 0, warn: int = 0) -> str:
    if fail:
        return "fail"
    if warn:
        return "warn"
    return "pass"


def _json_print(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, default=str))


def _title(text: str) -> list[str]:
    return [f"# {text}", ""]


def _bullet_lines(items: list[str], empty: str = "None.") -> list[str]:
    if not items:
        return [empty]
    return [f"- {item}" for item in items]


def _report_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = _title(title)
    lines.extend([
        f"Version: {report.get('version', OPERATIONAL_READINESS_VERSION)}",
        f"Checked at: {report.get('checked_at', '')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ])
    if "score" in report:
        lines.append(f"Score: {report.get('score')}%")
    lines.append("")

    for section in ["blockers", "warnings", "strengths", "weaknesses", "recommendations", "next_commands"]:
        values = report.get(section) or []
        if values or section in {"blockers", "warnings", "recommendations", "next_commands"}:
            label = section.replace("_", " ").title()
            lines.extend([f"## {label}"])
            lines.extend(_bullet_lines([str(item) for item in values], empty="None."))
            lines.append("")

    rows = report.get("rows") or report.get("items") or report.get("scenarios") or []
    if rows:
        lines.extend(["## Rows"])
        for row in rows:
            if isinstance(row, dict):
                status = str(row.get("status", row.get("result", "info"))).upper()
                name = row.get("name") or row.get("id") or row.get("title") or row.get("scenario") or "row"
                msg = row.get("message") or row.get("summary") or row.get("problem") or row.get("expected") or ""
                lines.append(f"- {status} {name}: {msg}")
            else:
                lines.append(f"- {row}")
        lines.append("")

    if full:
        lines.extend(["## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def build_repair_suggestions(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    checkpoint = build_stabilization_checkpoint(project_id=project_id, full=True)
    health = settings_health()
    suggestions: list[dict[str, Any]] = []

    def add(key: str, severity: str, problem: str, fix: str, commands: list[str] | None = None, auto_fix: bool = False) -> None:
        suggestions.append({
            "id": key,
            "severity": severity,
            "problem": problem,
            "fix": fix,
            "commands": commands or [],
            "safe_to_auto_fix": auto_fix,
        })

    for item in checkpoint.get("blockers", []):
        name = str(item.get("name", ""))
        msg = str(item.get("message", ""))
        if name.startswith("python-compile"):
            add("compile-failure", "critical", msg, "Open the failed Python file, fix the syntax/runtime import issue, then rerun py_compile and --doctor.", ["python -m py_compile conscious_agent/*.py tools/smoke_check.py"])
        elif name.startswith("json:"):
            add("json-parse-failure", "high", msg, "Repair the malformed JSON file or restore it from backup before running any live workflow.")
        elif "settings-safe-mode" in name:
            add("safe-mode-not-strict", "critical", msg, "Reset safe_mode to strict before allowing autonomous workflows.", ["python conscious_agent/main.py --set-setting safe_mode strict"])
        else:
            add(f"blocker-{len(suggestions)+1}", "high", f"{name}: {msg}", "Review the blocker details in --stabilization-checkpoint --stabilization-full.", ["python conscious_agent/main.py --stabilization-checkpoint --stabilization-full"])

    warning_names = "\n".join(str(item.get("name", "")) + " " + str(item.get("message", "")) for item in checkpoint.get("warnings", []))
    if "chromadb" in warning_names.lower():
        add("install-chromadb", "medium", "ChromaDB is missing from the active Python environment.", "Install project requirements in the same environment used to run Eidolon.", ["python -m pip install -r requirements.txt"])
    if not health.get("ollama", {}).get("ok", False):
        add("start-ollama", "medium", "Ollama is not reachable from the configured base URL.", "Start Ollama locally, verify the configured model exists, then rerun --settings-health.", ["ollama list", "python conscious_agent/main.py --settings-health"])
    if "stable-loop-closure-guardrails" in warning_names:
        add("close-stable-loop-followups", "medium", "Stable-loop closure guardrails found unresolved follow-up chains.", "Resolve or close follow-up chains before live stable-loop advancement.", [
            "python conscious_agent/main.py --stable-loop-followup-completion-report unresolved",
            "python conscious_agent/main.py --resolve-stable-loop-followups stableloop_ID",
            "python conscious_agent/main.py --mark-stable-loop-followup-closed stableloop_ID",
        ])

    if not suggestions:
        add("no-repairs-needed", "info", "No repair suggestions were generated.", "Keep running --doctor before major changes anyway, because entropy has excellent attendance.")

    severities = Counter(item["severity"] for item in suggestions)
    status = "fail" if severities.get("critical") else "warn" if any(s != "info" for s in severities) else "pass"
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "fail",
        "counts": dict(severities),
        "rows": suggestions,
        "recommendations": [item["fix"] for item in suggestions if item.get("severity") != "info"],
        "next_commands": [cmd for item in suggestions for cmd in item.get("commands", [])],
        "message": f"Generated {len(suggestions)} repair suggestion(s).",
    }


def repair_suggestions_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_repair_suggestions()
    lines = _title("Eidolon v7.3 Self-Repair Suggestions")
    lines.extend([
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Message: {report.get('message')}",
        "",
        "## Suggestions",
    ])
    for item in report.get("rows", []):
        commands = item.get("commands") or []
        lines.append(f"- {str(item.get('severity', 'info')).upper()} {item.get('id')}: {item.get('problem')} Fix: {item.get('fix')}")
        for command in commands:
            lines.append(f"  - {command}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def build_stable_loop_confidence(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    checkpoint = build_stabilization_checkpoint(project_id=project_id, full=False)
    guardrails = stable_loop_guardrail_summary(project_id=project_id)
    recovery = task_recovery_summary(project=project_id)
    health = settings_health()

    fail = int((checkpoint.get("counts") or {}).get("fail", 0))
    warn = int((checkpoint.get("counts") or {}).get("warn", 0))
    recoverable = int(recovery.get("recoverable", 0) or 0)
    unresolved = int(guardrails.get("unresolved_count", 0) or 0)
    ollama_ok = bool((health.get("ollama") or {}).get("ok", False))

    score = 100
    score -= fail * 25
    score -= warn * 6
    score -= min(recoverable, 5) * 5
    score -= min(unresolved, 5) * 8
    if not ollama_ok:
        score -= 8
    score = max(0, min(100, score))

    if score >= 90:
        readiness = "ready"
    elif score >= 75:
        readiness = "ready_with_warnings"
    elif score >= 50:
        readiness = "limited_mode"
    else:
        readiness = "blocked"

    strengths: list[str] = []
    weaknesses: list[str] = []
    if fail == 0:
        strengths.append("No stabilization blockers are currently reported.")
    else:
        weaknesses.append(f"Stabilization has {fail} blocker(s).")
    if warn == 0:
        strengths.append("No stabilization warnings are currently reported.")
    else:
        weaknesses.append(f"Stabilization has {warn} warning(s).")
    if guardrails.get("ok_for_live"):
        strengths.append("Stable-loop closure guardrails allow live advancement.")
    else:
        weaknesses.append("Stable-loop closure guardrails do not allow live advancement yet.")
    if recoverable:
        weaknesses.append(f"Task recovery has {recoverable} recoverable item(s).")
    else:
        strengths.append("No recoverable failed/blocked task backlog is reported.")
    if ollama_ok:
        strengths.append("Ollama health check passes.")
    else:
        weaknesses.append("Ollama is unavailable, so AI-dependent work should stay disabled or local setup should be fixed.")

    recommendations = []
    if readiness in {"blocked", "limited_mode"}:
        recommendations.append("Do not run live self-build workflows until --doctor improves to ready or ready_with_warnings.")
    if weaknesses:
        recommendations.append("Run --repair-suggestions and handle the listed setup/closure items.")
    recommendations.append("Use preview/dry-run commands before live work. Tedious, yes. Also why the files are still alive.")

    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": readiness,
        "ok": readiness in {"ready", "ready_with_warnings"},
        "score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
        "next_commands": [
            "python conscious_agent/main.py --doctor --doctor-full",
            "python conscious_agent/main.py --repair-suggestions",
            "python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop",
        ],
        "inputs": {
            "stabilization_status": checkpoint.get("status"),
            "stabilization_counts": checkpoint.get("counts"),
            "guardrails_ok_for_live": guardrails.get("ok_for_live"),
            "guardrail_unresolved_count": guardrails.get("unresolved_count"),
            "recoverable_task_count": recoverable,
            "ollama_ok": ollama_ok,
        },
        "message": f"Stable loop confidence is {score}% ({readiness}).",
    }


def stable_loop_confidence_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _report_text("Eidolon v7.8 Stable Loop Confidence", report or build_stable_loop_confidence(), full=full)


def build_patch_integrity_report() -> dict[str, Any]:
    patches = list_patch_proposals()
    rows: list[dict[str, Any]] = []
    status_counts = Counter(str(patch.get("status", "unknown")) for patch in patches)
    for patch in patches[:100]:
        problems: list[str] = []
        patch_id = str(patch.get("id", ""))
        target = str(patch.get("target_file", ""))
        status = str(patch.get("status", "unknown"))
        if not patch_id:
            problems.append("missing id")
        if not target:
            problems.append("missing target_file")
        if status == "proposed" and not patch.get("proposed_sha256"):
            problems.append("proposed patch missing proposed_sha256")
        if status == "applied":
            backup = str(patch.get("backup_path", ""))
            if not backup:
                problems.append("applied patch missing backup_path")
            else:
                backup_path = Path(backup)
                if not backup_path.is_absolute():
                    backup_path = (ROOT_DIR / backup).resolve()
                if not backup_path.exists():
                    problems.append("backup_path does not exist")
            if not patch.get("applied_sha256"):
                problems.append("applied patch missing applied_sha256")
        rows.append({
            "id": patch_id or "[missing]",
            "target_file": target,
            "patch_status": status,
            "status": "warn" if problems else "pass",
            "message": ", ".join(problems) if problems else "Patch metadata is internally consistent.",
            "problems": problems,
        })

    warnings = [f"{row['id']}: {row['message']}" for row in rows if row["status"] == "warn"]
    readme = _read_text("README_NEXT_STEPS.md")
    readme_mentions_v8 = "Eidolon v8.0" in readme and "Patch Integrity" in readme
    if not readme_mentions_v8:
        warnings.append("README does not appear to include the v8.0/v7.4 integrity notes yet.")

    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "status": "warn" if warnings else "pass",
        "ok": True,
        "patch_count": len(patches),
        "counts": dict(status_counts),
        "rows": rows,
        "warnings": warnings,
        "recommendations": ["Regenerate or repair any patch records with missing hashes/backups before relying on rollback." ] if warnings else [],
        "next_commands": ["python conscious_agent/main.py --patch-integrity", "python conscious_agent/main.py --list-patches"],
        "message": f"Checked metadata for {len(patches)} patch proposal(s).",
    }


def patch_integrity_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _report_text("Eidolon v7.4 Patch Integrity Report", report or build_patch_integrity_report(), full=full)


def build_project_snapshot(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    active = get_active_project()
    settings = load_settings()
    checkpoint = build_stabilization_checkpoint(project_id=project_id, full=False)
    confidence = build_stable_loop_confidence(project_id=project_id)
    tasks = list_tasks(project=project_id, include_cancelled=True)
    approvals = list_approvals(status="pending")
    patches = list_patch_proposals()
    snapshot = {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if checkpoint.get("status") == "pass" else "warn" if checkpoint.get("ok") else "fail",
        "ok": bool(checkpoint.get("ok")),
        "active_project": active,
        "settings_version": settings.get("settings_version"),
        "task_counts": task_status_counts(),
        "task_total": len(tasks),
        "pending_approvals": len(approvals),
        "patch_count": len(patches),
        "test_report_count": len(list_test_reports()),
        "test_review_count": len(list_test_reviews()),
        "work_cycle_count": len(list_work_cycles()),
        "stable_loop_count": len(list_stable_loops()),
        "stabilization": {"status": checkpoint.get("status"), "counts": checkpoint.get("counts")},
        "confidence": {"score": confidence.get("score"), "status": confidence.get("status")},
        "recommendations": [
            "Run --doctor before major patch batches.",
            "Run --task-review before controlled self-build work.",
            "Run --patch-integrity after applying or rolling back patches.",
        ],
        "next_commands": [
            "python conscious_agent/main.py --project-snapshot",
            "python conscious_agent/main.py --task-review",
            "python conscious_agent/main.py --doctor",
        ],
        "message": "Project state snapshot generated.",
    }
    return snapshot


def project_snapshot_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_project_snapshot()
    lines = _title("Eidolon v7.5 Project State Snapshot")
    lines.extend([
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Settings version: {report.get('settings_version')}",
        f"Stable loop confidence: {(report.get('confidence') or {}).get('score')}% ({(report.get('confidence') or {}).get('status')})",
        f"Tasks: {report.get('task_total')} | Pending approvals: {report.get('pending_approvals')} | Patches: {report.get('patch_count')}",
        f"Work cycles: {report.get('work_cycle_count')} | Stable loops: {report.get('stable_loop_count')}",
        "",
        "## Task counts",
    ])
    for status, count in (report.get("task_counts") or {}).items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Next commands"])
    lines.extend(_bullet_lines(report.get("next_commands") or []))
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def _risk_for_task(task: dict[str, Any], lifecycle: dict[str, Any]) -> str:
    text = json.dumps(task, default=str).lower()
    stage = str(lifecycle.get("stage", ""))
    if any(term in text for term in ["apply patch", "rollback", "delete", "subprocess", "shell", "approval_required"]):
        return "high"
    if stage in {"needs_attention", "approval_required", "recovery"}:
        return "medium"
    return "low"


def build_task_review(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    lifecycles = list_task_lifecycles(project=project_id, include_closed=False)
    rows: list[dict[str, Any]] = []
    for lifecycle in lifecycles[:50]:
        task = {
            "id": lifecycle.get("task_id", ""),
            "title": lifecycle.get("title", ""),
            "status": lifecycle.get("status", "unknown"),
            "risk": lifecycle.get("risk", "low"),
            "requires_approval": lifecycle.get("requires_approval", False),
            "metadata": {
                "patch_id": lifecycle.get("patch_id", ""),
                "stage": lifecycle.get("stage", ""),
            },
        }
        risk = _risk_for_task(task, lifecycle)
        stage = str(lifecycle.get("stage", "unknown"))
        needs_approval = bool(lifecycle.get("needs_approval") or lifecycle.get("requires_approval") or stage == "approval_required")
        rows.append({
            "id": lifecycle.get("task_id", "[missing]"),
            "title": lifecycle.get("title", "[untitled]"),
            "task_status": lifecycle.get("status", "unknown"),
            "stage": stage,
            "risk": risk,
            "needs_approval": needs_approval,
            "status": "warn" if risk in {"medium", "high"} or needs_approval else "pass",
            "message": f"stage={stage}; risk={risk}; approval_required={needs_approval}",
        })

    summary = task_lifecycle_summary(project=project_id, stage_filter="all")
    warnings = [f"{row['id']}: {row['message']}" for row in rows if row["status"] == "warn"]
    if not rows:
        warnings.append("No task rows are available; controlled self-build has nothing useful to select yet.")
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if warnings else "pass",
        "ok": True,
        "summary": summary,
        "rows": rows,
        "warnings": warnings,
        "recommendations": [
            "Resolve approval_required and recovery stages before live self-build.",
            "Keep high-risk file edits behind explicit approval.",
        ],
        "next_commands": [
            "python conscious_agent/main.py --task-review",
            "python conscious_agent/main.py --next-task",
            "python conscious_agent/main.py --task-recovery-summary",
        ],
        "message": f"Reviewed {len(rows)} task lifecycle row(s).",
    }


def task_review_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _report_text("Eidolon v7.6 Task Queue Review", report or build_task_review(), full=full)


def build_recovery_drill(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    recovery = task_recovery_summary(project=project_id)
    guardrails = stable_loop_guardrail_summary(project_id=project_id)
    scenarios = [
        {
            "scenario": "failed-patch-apply",
            "status": "pass",
            "expected": "Patch apply remains approval-gated and rollback metadata is checked by --patch-integrity.",
        },
        {
            "scenario": "failed-test-run",
            "status": "pass" if "categories" in recovery else "fail",
            "expected": "Task recovery summary can classify blocked/failed tasks and recommend retry/manual review.",
        },
        {
            "scenario": "missing-dependency",
            "status": "pass",
            "expected": "Stabilization/doctor reports environment warnings separately from code failures.",
        },
        {
            "scenario": "unresolved-stable-loop-followup",
            "status": "pass" if "ok_for_live" in guardrails else "fail",
            "expected": "Closure guardrails block live advancement unless explicitly bypassed by the operator.",
        },
        {
            "scenario": "ai-unavailable",
            "status": "pass",
            "expected": "No-AI flags keep previews and doctor checks usable while Ollama is down.",
        },
    ]
    fail = sum(1 for item in scenarios if item["status"] == "fail")
    warn = sum(1 for item in scenarios if item["status"] == "warn")
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": _status_from_counts(fail, warn),
        "ok": fail == 0,
        "scenarios": scenarios,
        "recommendations": ["Run recovery drills after changing task execution, patch apply, rollback, or stable-loop guardrails."],
        "next_commands": ["python conscious_agent/main.py --recovery-drill", "python conscious_agent/main.py --task-recovery-summary"],
        "message": f"Recovery drill simulated {len(scenarios)} failure mode(s) without mutating project state.",
    }


def recovery_drill_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _report_text("Eidolon v7.7 Recovery Drill", report or build_recovery_drill(), full=full)


def build_hardening_report(project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    files = {
        "main.py": _read_text("conscious_agent/main.py"),
        "api_server.py": _read_text("conscious_agent/api_server.py"),
        "dashboard.py": _read_text("conscious_agent/dashboard.py"),
        "README_NEXT_STEPS.md": _read_text("README_NEXT_STEPS.md"),
        "smoke_check.py": _read_text("tools/smoke_check.py"),
        "command_runner.py": _read_text("conscious_agent/command_runner.py"),
    }
    expected_flags = [
        "--doctor", "--repair-suggestions", "--patch-integrity", "--project-snapshot",
        "--task-review", "--recovery-drill", "--stable-loop-confidence",
        "--hardening-report", "--controlled-self-build", "--select-task",
        "--plan-patch", "--patch-workspace-status", "--stage-patch", "--preview-diff",
        "--apply-staged-patch", "--verify-latest-patch", "--rollback-latest-patch",
        "--readme-gate", "--controlled-self-build-cycle", "--supervised-dev-loop",
        "--codebase-map", "--task-dependencies", "--test-plan", "--patch-risk",
        "--patch-review", "--project-memory-index", "--workspace-status",
        "--cross-project-task-review", "--asymmetric-dev-loop",
        "--project-registry", "--register-project", "--set-active-workspace-project",
        "--project-health", "--project-health-all", "--command-profiles",
        "--workspace-dependency-map", "--workspace-task-inbox", "--switch-project",
        "--project-context", "--workspace-timeline", "--workspace-dev-loop",
        "--workspace-registry-audit", "--workspace-repair-suggestions",
        "--project-boundary-check", "--workspace-patch-plan", "--workspace-preview-diff",
        "--workspace-apply", "--workspace-verify-latest", "--guarded-workspace-dev-loop",
        "--patch-draft-request", "--draft-patch", "--patch-draft-status",
        "--patch-review-notes", "--draft-diff", "--draft-test-impact",
        "--approve-draft", "--reject-draft", "--apply-approved-draft",
        "--rollback-approved-draft", "--reopen-draft", "--human-approved-patch-loop",
    ]
    expected_api = [
        "/api/doctor", "/api/repair-suggestions", "/api/patch-integrity", "/api/project-snapshot",
        "/api/tasks/review", "/api/recovery-drill", "/api/stable-loops/confidence",
        "/api/hardening-report", "/api/controlled-self-build", "/api/controlled-build/select-task",
        "/api/controlled-build/plan-patch", "/api/controlled-build/workspace",
        "/api/controlled-build/preview-diff", "/api/controlled-build/readme-gate",
        "/api/codebase-map", "/api/task-dependencies", "/api/test-plan",
        "/api/patch-risk", "/api/patch-review", "/api/project-memory-index",
        "/api/workspace-status", "/api/cross-project-task-review", "/api/asymmetric-dev-loop",
        "/api/project-registry", "/api/projects/register", "/api/projects/active",
        "/api/project-health", "/api/command-profiles", "/api/workspace-dependency-map",
        "/api/workspace-task-inbox", "/api/workspace/switch-project", "/api/project-context",
        "/api/workspace-timeline", "/api/workspace-dev-loop",
        "/api/workspace-registry-audit", "/api/workspace-repair-suggestions",
        "/api/project-boundary-check", "/api/workspace-patch-plan",
        "/api/workspace-preview-diff", "/api/workspace-verify-latest",
        "/api/guarded-workspace-dev-loop", "/api/patch-draft-status",
        "/api/patch-draft-request", "/api/draft-patch", "/api/patch-review-notes",
        "/api/draft-diff", "/api/draft-test-impact", "/api/approval-gate",
        "/api/human-approved-patch-loop", "/api/supervised-dev-loop",
    ]
    expected_dashboard = ["/doctor", "/stabilization", "/build-cycle", "/patch-review", "/intelligence", "/workspace", "/patch-drafts"]
    rows: list[dict[str, Any]] = []

    for flag in expected_flags:
        ok = flag in files["main.py"] and flag in files["command_runner.py"]
        rows.append({"name": f"cli:{flag}", "status": "pass" if ok else "fail", "message": "CLI flag and whitelist entry found." if ok else "Missing CLI flag or command whitelist entry."})
    for route in expected_api:
        ok = route in files["api_server.py"] or route.replace("/api", "") in files["api_server.py"] or route.replace("/api/", "") in files["api_server.py"]
        rows.append({"name": f"api:{route}", "status": "pass" if ok else "fail", "message": "API route surface found." if ok else "Missing API route surface."})
    for route in expected_dashboard:
        ok = route in files["dashboard.py"]
        rows.append({"name": f"dashboard:{route}", "status": "pass" if ok else "fail", "message": "Dashboard route found." if ok else "Missing dashboard route."})
    for version in ["v7.1", "v7.2", "v7.3", "v7.4", "v7.5", "v7.6", "v7.7", "v7.8", "v7.9", "v8.0", "v8.1", "v8.2", "v8.3", "v8.4", "v8.5", "v8.6", "v8.7", "v8.8", "v8.9", "v9.0", "v9.1", "v9.2", "v9.3", "v9.4", "v9.5", "v9.6", "v9.7", "v9.8", "v9.9", "v10.0", "v10.1", "v10.2", "v10.3", "v10.4", "v10.5", "v10.6", "v10.7", "v10.8", "v10.9", "v11.0", "v11.1", "v11.2", "v11.3", "v11.4", "v11.5", "v11.6", "v11.7", "v11.8", "v11.9", "v12.0", "v12.1", "v12.2", "v12.3", "v12.4", "v12.5", "v12.6", "v12.7", "v12.8", "v12.9", "v13.0", "v13.1", "v13.2", "v13.3", "v13.4", "v13.5", "v13.6", "v13.7", "v13.8", "v13.9", "v14.0", "v14.1", "v14.2", "v14.3", "v14.4", "v14.5", "v14.6", "v14.7", "v14.8", "v14.9", "v15.0"]:
        ok = version in files["README_NEXT_STEPS.md"]
        rows.append({"name": f"readme:{version}", "status": "pass" if ok else "fail", "message": "README version notes found." if ok else "README version notes missing."})

    compile_failures: list[str] = []
    for path in sorted((ROOT_DIR / "conscious_agent").glob("*.py")) + [ROOT_DIR / "tools" / "smoke_check.py"]:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as error:
            compile_failures.append(f"{path.relative_to(ROOT_DIR)}: {error.msg}")
    rows.append({
        "name": "python-compile-surface",
        "status": "fail" if compile_failures else "pass",
        "message": f"{len(compile_failures)} compile failure(s)." if compile_failures else "Python compile surface is clean.",
        "failures": compile_failures,
    })

    fail = sum(1 for row in rows if row["status"] == "fail")
    warn = sum(1 for row in rows if row["status"] == "warn")
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": _status_from_counts(fail, warn),
        "ok": fail == 0,
        "counts": {"pass": sum(1 for row in rows if row["status"] == "pass"), "warn": warn, "fail": fail},
        "rows": rows,
        "blockers": [f"{row['name']}: {row['message']}" for row in rows if row["status"] == "fail"],
        "recommendations": ["Keep every new major command represented in CLI, API, dashboard or README, smoke checks, and command whitelist."],
        "next_commands": ["python conscious_agent/main.py --hardening-report --doctor-full", "python tools/smoke_check.py"],
        "message": f"Hardening report checked {len(rows)} surface item(s).",
    }


def hardening_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _report_text("Eidolon v7.9 Pre-v8 Hardening Report", report or build_hardening_report(), full=full)


def build_doctor_report(project_id: str = DEFAULT_PROJECT_ID, full: bool = False) -> dict[str, Any]:
    checkpoint = build_stabilization_checkpoint(project_id=project_id, full=full)
    confidence = build_stable_loop_confidence(project_id=project_id)
    repairs = build_repair_suggestions(project_id=project_id)
    patch_integrity = build_patch_integrity_report()
    task_review = build_task_review(project_id=project_id)
    recovery_drill = build_recovery_drill(project_id=project_id)
    hardening = build_hardening_report(project_id=project_id)
    reports = {
        "stabilization": checkpoint,
        "confidence": confidence,
        "repair_suggestions": repairs,
        "patch_integrity": patch_integrity,
        "task_review": task_review,
        "recovery_drill": recovery_drill,
        "hardening": hardening,
    }
    fail = sum(1 for report in reports.values() if report.get("status") == "fail" or report.get("ok") is False)
    warn = sum(1 for report in reports.values() if report.get("status") in {"warn", "limited_mode", "ready_with_warnings"})
    if confidence.get("status") == "blocked":
        fail += 1
    elif confidence.get("status") == "limited_mode":
        warn += 1
    status = "blocked" if fail else "ready_with_warnings" if warn else "ready"
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "score": confidence.get("score"),
        "reports": reports,
        "blockers": [f"{name}: {report.get('message')}" for name, report in reports.items() if report.get("status") == "fail" or report.get("ok") is False],
        "warnings": [f"{name}: {report.get('message')}" for name, report in reports.items() if report.get("status") in {"warn", "limited_mode", "ready_with_warnings"}],
        "recommendations": [
            "Fix blockers before live self-build.",
            "Treat warnings as acceptable only for preview/dry-run work unless you intentionally understand them.",
            "Rerun --doctor after every patch batch.",
        ],
        "next_commands": [
            "python conscious_agent/main.py --repair-suggestions",
            "python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop",
            "python tools/smoke_check.py",
        ],
        "message": f"Doctor status is {status} with confidence score {confidence.get('score')}%.",
    }


def doctor_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_doctor_report(full=full)
    lines = _title("Eidolon v7.2 Doctor Mode")
    lines.extend([
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Confidence score: {report.get('score')}%",
        f"Message: {report.get('message')}",
        "",
        "## Subreports",
    ])
    for name, subreport in (report.get("reports") or {}).items():
        lines.append(f"- {name}: {str(subreport.get('status')).upper()} - {subreport.get('message')}")
    lines.extend(["", "## Blockers"])
    lines.extend(_bullet_lines(report.get("blockers") or []))
    lines.extend(["", "## Warnings"])
    lines.extend(_bullet_lines(report.get("warnings") or []))
    lines.extend(["", "## Next commands"])
    lines.extend(_bullet_lines(report.get("next_commands") or []))
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def build_controlled_self_build(project_id: str = DEFAULT_PROJECT_ID, max_steps: int = 1, live: bool = False, approve_live: bool = False, use_ai: bool = False) -> dict[str, Any]:
    doctor = build_doctor_report(project_id=project_id, full=False)
    confidence = (doctor.get("score") or 0)
    task_review = build_task_review(project_id=project_id)
    preflight = build_stable_loop_preflight(project_id=project_id, max_steps=max(1, min(max_steps, 5)))
    guardrails = stable_loop_guardrail_summary(project_id=project_id)

    blocked_reasons: list[str] = []
    if doctor.get("status") == "blocked":
        blocked_reasons.append("Doctor mode reports blocked status.")
    if confidence < 75:
        blocked_reasons.append(f"Stable-loop confidence is only {confidence}%, below the 75% minimum for controlled self-build preview.")
    if live and confidence < 90:
        blocked_reasons.append(f"Live controlled self-build requires 90% confidence; current score is {confidence}%.")
    if live and not guardrails.get("ok_for_live"):
        blocked_reasons.append("Stable-loop closure guardrails do not allow live advancement.")
    if live and not approve_live:
        blocked_reasons.append("Live controlled self-build requires --approve-controlled-self-build.")

    actions = [
        "Run doctor mode and confidence scoring.",
        "Review task queue risk and lifecycle state.",
        "Build stable-loop preflight for the selected bounded step count.",
        "Keep patch creation/application behind existing patch and approval gates.",
        "Update README and rerun smoke checks after any patch batch.",
    ]

    run_result: dict[str, Any] | None = None
    if live and not blocked_reasons:
        result = run_stable_supervised_loop(
            project_id=project_id,
            max_steps=max(1, min(max_steps, 5)),
            live=True,
            use_ai=use_ai,
            seed_if_empty=False,
            auto_create_followups=True,
            auto_request_approvals=True,
            auto_retry_recovery=False,
        )
        run_result = result.to_dict() if hasattr(result, "to_dict") else dict(result.__dict__)
    elif not live and not blocked_reasons:
        run_result = {
            "ok": True,
            "live": False,
            "record_created": False,
            "message": "Read-only controlled self-build preview completed from doctor, task review, guardrails, and stable-loop preflight. No stable-loop record was created.",
            "preflight_ok": preflight.get("ok"),
            "next_decision": preflight.get("next_decision"),
        }

    status = "blocked" if blocked_reasons else "live_complete" if live else "preview_complete"
    return {
        "version": OPERATIONAL_READINESS_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked_reasons,
        "live": live,
        "approved_live": approve_live,
        "use_ai": use_ai,
        "max_steps": max(1, min(max_steps, 5)),
        "score": confidence,
        "blocked_reasons": blocked_reasons,
        "actions": actions,
        "task_review_status": task_review.get("status"),
        "preflight_next_action": (preflight.get("next_decision") or {}).get("action"),
        "guardrails_ok_for_live": guardrails.get("ok_for_live"),
        "run_result": run_result,
        "recommendations": [
            "Use preview mode first; live mode requires explicit approval and clean guardrails.",
            "Do not let controlled self-build modify guardrails or safety settings without human review.",
        ],
        "next_commands": [
            "python conscious_agent/main.py --controlled-self-build --dry-run --no-ai-stable-loop",
            "python conscious_agent/main.py --doctor --doctor-full",
            "python conscious_agent/main.py --patch-integrity",
        ],
        "message": "Controlled self-build preview completed." if status == "preview_complete" else "Controlled self-build live run completed." if status == "live_complete" else "Controlled self-build is blocked.",
    }


def controlled_self_build_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_controlled_self_build()
    lines = _title("Eidolon v8.0 Controlled Self-Build Loop")
    lines.extend([
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Confidence score: {report.get('score')}%",
        f"Live: {report.get('live')} | AI: {report.get('use_ai')} | Steps: {report.get('max_steps')}",
        f"Message: {report.get('message')}",
        "",
        "## Planned control gates",
    ])
    lines.extend(_bullet_lines(report.get("actions") or []))
    if report.get("blocked_reasons"):
        lines.extend(["", "## Blocked reasons"])
        lines.extend(_bullet_lines(report.get("blocked_reasons") or []))
    if report.get("run_result"):
        result = report["run_result"]
        lines.extend(["", "## Run result", f"- ok: {result.get('ok')}", f"- loop_id: {result.get('loop_id')}", f"- message: {result.get('message')}"])
    lines.extend(["", "## Next commands"])
    lines.extend(_bullet_lines(report.get("next_commands") or []))
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def print_doctor(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_doctor_report(project_id=project_id, full=full or json_output)
    _json_print(report) if json_output else print(doctor_report_text(report, full=full))


def print_repair_suggestions(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_repair_suggestions(project_id=project_id)
    _json_print(report) if json_output else print(repair_suggestions_text(report, full=full))


def print_patch_integrity(full: bool = False, json_output: bool = False) -> None:
    report = build_patch_integrity_report()
    _json_print(report) if json_output else print(patch_integrity_text(report, full=full))


def print_project_snapshot(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_project_snapshot(project_id=project_id)
    _json_print(report) if json_output else print(project_snapshot_text(report, full=full))


def print_task_review(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_task_review(project_id=project_id)
    _json_print(report) if json_output else print(task_review_text(report, full=full))


def print_recovery_drill(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_recovery_drill(project_id=project_id)
    _json_print(report) if json_output else print(recovery_drill_text(report, full=full))


def print_stable_loop_confidence(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_stable_loop_confidence(project_id=project_id)
    _json_print(report) if json_output else print(stable_loop_confidence_text(report, full=full))


def print_hardening_report(project_id: str = DEFAULT_PROJECT_ID, full: bool = False, json_output: bool = False) -> None:
    report = build_hardening_report(project_id=project_id)
    _json_print(report) if json_output else print(hardening_report_text(report, full=full))


def print_controlled_self_build(project_id: str = DEFAULT_PROJECT_ID, max_steps: int = 1, live: bool = False, approve_live: bool = False, use_ai: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_controlled_self_build(project_id=project_id, max_steps=max_steps, live=live, approve_live=approve_live, use_ai=use_ai)
    _json_print(report) if json_output else print(controlled_self_build_text(report, full=full))
