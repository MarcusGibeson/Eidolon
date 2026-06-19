from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from command_runner import run_approved_command, validate_command
from memory import store_memory
from patch_suggester import load_patch_proposal, resolve_patch_id
from paths import DATA_DIR


TEST_REPORTS_DIR = DATA_DIR / "test_reports"
ACTION_LOG_FILE = DATA_DIR / "action_log.json"

DEFAULT_TEST_COMMANDS = [
    "python conscious_agent/main.py --status",
    "python conscious_agent/main.py --project-index-summary",
]


@dataclass
class TestWorkflowResult:
    ok: bool
    report_id: str = ""
    status: str = ""
    recommendation: str = ""
    error: str = ""
    dry_run: bool = False


def _ensure_storage() -> None:
    TEST_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ACTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not ACTION_LOG_FILE.exists():
        with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
            json.dump([], file, indent=2)


def _load_action_log() -> list[dict[str, Any]]:
    _ensure_storage()
    try:
        with ACTION_LOG_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save_action_log(log: list[dict[str, Any]]) -> None:
    _ensure_storage()
    with ACTION_LOG_FILE.open("w", encoding="utf-8") as file:
        json.dump(log, file, indent=2)


def _append_action_log(entry: dict[str, Any]) -> None:
    log = _load_action_log()
    log.append(entry)
    _save_action_log(log)


def _new_report_id(patch_id: str = "") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = patch_id.strip() or "general"
    safe_suffix = "".join(char if char.isalnum() or char in {"_", "-"} else "-" for char in suffix)
    return f"test_{timestamp}_{safe_suffix[:80]}"


def _report_path(report_id: str) -> Path:
    return TEST_REPORTS_DIR / f"{report_id}.json"


def save_test_report(report: dict[str, Any]) -> None:
    _ensure_storage()
    with _report_path(report["id"]).open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)



def resolve_test_report_id(report_id: str) -> str:
    """Resolves latest/last into the newest test report id."""
    token = (report_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    reports = list_test_reports()
    if not reports:
        return ""

    return reports[0].get("id", "")


def load_test_report(report_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_test_report_id(report_id)
    if not resolved_id:
        return None

    path = _report_path(resolved_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def list_test_reports() -> list[dict[str, Any]]:
    _ensure_storage()
    reports: list[dict[str, Any]] = []

    for path in sorted(TEST_REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(data, dict):
            reports.append(data)

    return reports


def _patch_context(patch_id: str) -> dict[str, Any]:
    if not patch_id:
        return {
            "patch_id": "",
            "patch_found": False,
            "message": "No patch id supplied. Running a general test workflow.",
        }

    proposal = load_patch_proposal(patch_id)
    if not proposal:
        return {
            "patch_id": patch_id,
            "patch_found": False,
            "message": f"Patch not found: {patch_id}",
        }

    return {
        "patch_id": patch_id,
        "patch_found": True,
        "status": proposal.get("status"),
        "target_file": proposal.get("target_file"),
        "risk_level": proposal.get("risk_level"),
        "request": proposal.get("request"),
    }


def _normalize_commands(commands: list[str] | None) -> list[str]:
    cleaned = [command.strip() for command in (commands or []) if command and command.strip()]
    return cleaned if cleaned else DEFAULT_TEST_COMMANDS.copy()


def _evaluate_results(command_results: list[dict[str, Any]], patch_context: dict[str, Any]) -> tuple[str, str]:
    if not command_results:
        return "failed", "No commands were run. Review the test workflow configuration."

    failed = [result for result in command_results if not result.get("ok")]

    if failed:
        if patch_context.get("patch_found") and patch_context.get("status") == "applied":
            return (
                "failed",
                "One or more checks failed after an applied patch. Review the output and consider rollback if the failure is related to the patch.",
            )
        return "failed", "One or more checks failed. Review the output before applying or keeping changes."

    if patch_context.get("patch_found") and patch_context.get("status") == "proposed":
        return (
            "passed",
            "Checks passed, but the patch is still only proposed. Apply it with --apply-patch, then run this workflow again.",
        )

    if patch_context.get("patch_found") and patch_context.get("status") == "applied":
        return "passed", "All checks passed after the applied patch. Recommendation: keep the patch for now."

    return "passed", "All checks passed. No patch-specific recommendation was needed."


def run_test_workflow(
    patch_id: str = "",
    commands: list[str] | None = None,
    dry_run: bool = False,
) -> TestWorkflowResult:
    """
    Runs a small approved-command test workflow and saves a JSON report.

    This does not bypass command safety. Every command goes through command_runner.py.
    """
    if (patch_id or "").strip().lower() in {"latest", "last"}:
        patch_id = resolve_patch_id(patch_id, status="applied") or resolve_patch_id(patch_id) or patch_id
    else:
        patch_id = resolve_patch_id(patch_id) if patch_id else ""

    normalized_commands = _normalize_commands(commands)
    context = _patch_context(patch_id)

    if patch_id and not context.get("patch_found"):
        return TestWorkflowResult(ok=False, error=context.get("message", "Patch not found."), dry_run=dry_run)

    report_id = _new_report_id(patch_id)
    started_at = datetime.now().isoformat(timespec="seconds")

    command_results: list[dict[str, Any]] = []

    for command in normalized_commands:
        if dry_run:
            validation = validate_command(command)
            command_results.append({
                "command": command,
                "ok": validation.ok,
                "dry_run": True,
                "return_code": None,
                "stdout": "",
                "stderr": "",
                "error": validation.reason,
                "message": "Command is allowed." if validation.ok else "Command is not allowed.",
            })
            continue

        result = run_approved_command(command, dry_run=False)
        command_results.append({
            "command": result.command,
            "ok": result.ok,
            "dry_run": result.dry_run,
            "return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
            "message": result.message,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "cwd": result.cwd,
        })

    status, recommendation = _evaluate_results(command_results, context)
    finished_at = datetime.now().isoformat(timespec="seconds")

    report = {
        "id": report_id,
        "created_at": finished_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "dry_run": dry_run,
        "patch": context,
        "commands": command_results,
        "recommendation": recommendation,
    }

    save_test_report(report)

    _append_action_log({
        "timestamp": finished_at,
        "action": "test_workflow",
        "report_id": report_id,
        "patch_id": patch_id,
        "status": status,
        "dry_run": dry_run,
        "commands": normalized_commands,
        "recommendation": recommendation,
    })

    store_memory({
        "type": "test_workflow_event",
        "content": f"Ran test workflow {report_id}. Status: {status}. Recommendation: {recommendation}",
        "source": "test_runner",
        "report_id": report_id,
        "patch_id": patch_id,
        "status": status,
    })

    return TestWorkflowResult(
        ok=status == "passed",
        report_id=report_id,
        status=status,
        recommendation=recommendation,
        dry_run=dry_run,
    )


def test_report_text(report: dict[str, Any], include_output: bool = False) -> str:
    lines = [
        f"# Test Workflow Report: {report.get('id')}",
        "",
        f"Created: {report.get('created_at')}",
        f"Status: {report.get('status')}",
        f"Dry run: {report.get('dry_run')}",
        "",
        "## Patch context",
    ]

    patch = report.get("patch", {})
    if patch.get("patch_id"):
        lines.extend([
            f"Patch id: {patch.get('patch_id')}",
            f"Patch found: {patch.get('patch_found')}",
            f"Patch status: {patch.get('status')}",
            f"Target file: {patch.get('target_file')}",
            f"Risk level: {patch.get('risk_level')}",
            f"Request: {patch.get('request')}",
        ])
    else:
        lines.append(patch.get("message", "No patch id supplied."))

    lines.extend([
        "",
        "## Commands",
    ])

    for result in report.get("commands", []):
        lines.extend([
            f"- Command: {result.get('command')}",
            f"  OK: {result.get('ok')}",
            f"  Return code: {result.get('return_code')}",
        ])
        if result.get("error"):
            lines.append(f"  Error: {result.get('error')}")

        if include_output:
            if result.get("stdout"):
                lines.extend(["  stdout:", _indent(result.get("stdout", ""), "    ")])
            if result.get("stderr"):
                lines.extend(["  stderr:", _indent(result.get("stderr", ""), "    ")])

    lines.extend([
        "",
        "## Recommendation",
        report.get("recommendation", ""),
    ])

    return "\n".join(lines).strip()


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def print_test_workflow(patch_id: str = "", commands: list[str] | None = None, dry_run: bool = False) -> None:
    result = run_test_workflow(patch_id=patch_id, commands=commands, dry_run=dry_run)

    if not result.report_id:
        print("Test workflow did not run.")
        print(f"Reason: {result.error}")
        return

    report = load_test_report(result.report_id)
    if not report:
        print(f"Test workflow finished, but report could not be loaded: {result.report_id}")
        return

    print(test_report_text(report, include_output=False))
    print()
    print(f"Saved test report: {result.report_id}")
    print("Next suggested step: python conscious_agent/main.py --review-test-report latest")


def print_test_report(report_id: str, include_output: bool = False) -> None:
    report = load_test_report(report_id)
    if not report:
        print(f"Test report not found: {report_id}")
        return
    print(test_report_text(report, include_output=include_output))


def print_test_reports() -> None:
    reports = list_test_reports()

    if not reports:
        print("No test workflow reports found.")
        return

    for report in reports:
        patch = report.get("patch", {})
        print(
            f"{report.get('id')} | "
            f"status={report.get('status')} | "
            f"dry_run={report.get('dry_run')} | "
            f"patch={patch.get('patch_id') or '[none]'}"
        )
        print(f"  Recommendation: {report.get('recommendation')}")
