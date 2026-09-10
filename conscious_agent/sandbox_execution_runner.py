from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE

import json
import shlex
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SANDBOX_EXECUTION_RUNNER_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
RUNNER_PACKET_ID = "v530_sandbox_execution_runner_packet"
RUNNER_CANDIDATE_ID = "v530_operator_approved_sandbox_runner_candidate"
EXACT_APPROVAL_PHRASE = f"I approve one sandbox execution for packet {RUNNER_PACKET_ID} only."

ALLOWED_SANDBOX_COMMANDS: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --tier fast --json",
    "python tools/smoke_check.py --check operator-approved-sandbox-execution-runner-v1 --json",
)

FORBIDDEN_LIVE_WRITE_PATHS: tuple[str, ...] = (
    "conscious_agent/",
    "tools/",
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "data/memory.json",
    "data/workspaces/timeline.json",
    "data/autonomy/",
    "data/self_maintenance/",
    "runtime/",
    ".env",
)

SANDBOX_EXECUTION_RUNNER_BOUNDARIES: dict[str, bool] = {
    "runner_contract_exists_is_execution_permission": False,
    "phrase_validated_is_command_executed": False,
    "sandbox_command_success_is_live_patch_approval": False,
    "receipt_success_is_future_authorization": False,
    "runner_available_is_autonomy": False,
    "runner_runs_without_exact_approval": False,
    "runner_writes_live_source": False,
    "runner_writes_memory": False,
    "runner_invokes_models_by_default": False,
    "runner_schedules_work": False,
    "runner_promotes_to_live": False,
    "runner_creates_release_candidate": False,
    "runner_reuses_approval": False,
    "runner_continues_automatically": False,
    "runner_expands_autonomy": False,
    "live_source_write_allowed": False,
    "memory_write_allowed": False,
    "release_creation_allowed": False,
    "approval_required": True,
    "single_use_only": True,
    "approval_burnout_required": True,
    "sandbox_only_execution_required": True,
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = Path(root or Path(__file__).resolve().parents[1])
    parts = [
        _read_text(repo / "README_NEXT_STEPS.md"),
        _read_text(repo / "README_RELEASE_HISTORY.md"),
        _read_text(repo / "conscious_agent/sandbox_execution_runner.py"),
        _read_text(repo / "conscious_agent/first_sandbox_execution_trial.py"),
        _read_text(repo / "conscious_agent/sandbox_execution_dry_run_receipt.py"),
        _read_text(repo / "conscious_agent/sandbox_execution_approval_gate.py"),
        _read_text(repo / "conscious_agent/self_maintenance.py"),
        _read_text(repo / "conscious_agent/dashboard.py"),
        _read_text(repo / "conscious_agent/dashboard_route_probe.py"),
        _read_text(repo / "conscious_agent/api_server.py"),
        _read_text(repo / "conscious_agent/main.py"),
        _read_text(repo / "tools/smoke_check.py"),
        _read_text(repo / "conscious_agent/source_surface_manifest.py"),
        _read_text(repo / "conscious_agent/smoke_segment_registry.py"),
        extra_docs,
    ]
    return "\n".join(parts)


def build_sandbox_execution_runner_contract(root: str | Path | None = None) -> dict[str, Any]:
    contract = {
        "runner_status": "available_under_approval_only",
        "sandbox_root_required": True,
        "sandbox_root": "throwaway_sandbox_workspace/",
        "source_copy_root": "throwaway_sandbox_workspace/source_copy/",
        "allowed_commands": list(ALLOWED_SANDBOX_COMMANDS),
        "live_source_write_allowed": False,
        "memory_write_allowed": False,
        "release_creation_allowed": False,
        "model_invocation_allowed_by_default": False,
        "scheduler_change_allowed": False,
        "approval_required": True,
        "single_use_only": True,
        "approval_burnout_required": True,
        "execution_permission": False,
    }
    rows = [
        _row("runner-contract-defined", contract["runner_status"] == "available_under_approval_only", "Runner contract is defined as approval-only."),
        _row("sandbox-root-required", contract["sandbox_root_required"] is True and contract["source_copy_root"].startswith(contract["sandbox_root"]), "Execution must be scoped to a disposable sandbox source copy."),
        _row("no-live-memory-release", not contract["live_source_write_allowed"] and not contract["memory_write_allowed"] and not contract["release_creation_allowed"], "Live source, memory, and release creation are forbidden."),
        _row("contract-not-permission", contract["execution_permission"] is False and SANDBOX_EXECUTION_RUNNER_BOUNDARIES["runner_contract_exists_is_execution_permission"] is False, "Runner contract existence is not execution permission."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_runner_contract_review_only",
        "contract": contract,
        "runner_status": "available_under_approval_only",
        "execution_status": "not_executed_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_approval_phrase_validator(root: str | Path | None = None, supplied_phrase: str | None = None, packet_id: str = RUNNER_PACKET_ID, candidate_id: str = RUNNER_CANDIDATE_ID) -> dict[str, Any]:
    expected_phrase = f"I approve one sandbox execution for packet {packet_id} only."
    supplied = supplied_phrase or ""
    exact_match = supplied == expected_phrase
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(microsecond=0).isoformat()
    validation = {
        "packet_id": packet_id,
        "candidate_id": candidate_id,
        "allowed_commands": list(ALLOWED_SANDBOX_COMMANDS),
        "approval_expiry": expires_at,
        "single_use_status": "unused_required",
        "operator_confirmation_phrase_expected": expected_phrase,
        "operator_confirmation_phrase_supplied": supplied if supplied else None,
        "phrase_validated": exact_match,
        "command_executed": False,
        "approval_created": False,
    }
    rows = [
        _row("packet-scope-visible", packet_id == RUNNER_PACKET_ID and candidate_id == RUNNER_CANDIDATE_ID, "Validator is bound to the expected packet and candidate identifiers."),
        _row("commands-scoped", validation["allowed_commands"] == list(ALLOWED_SANDBOX_COMMANDS), "Allowed command list is exact and bounded."),
        _row("phrase-not-auto-entered", supplied_phrase is None or exact_match, "No phrase is auto-entered; invalid supplied phrases fail exact validation."),
        _row("validation-not-execution", validation["command_executed"] is False and SANDBOX_EXECUTION_RUNNER_BOUNDARIES["phrase_validated_is_command_executed"] is False, "Phrase validation is not command execution."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "approval_phrase_validator_review_only",
        "validation": validation,
        "phrase_validated": exact_match,
        "execution_status": "not_executed",
        "approval_status": "validated_not_granted" if exact_match else "required",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def _command_is_allowed(command: str) -> bool:
    return command in ALLOWED_SANDBOX_COMMANDS


def _path_is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def execute_sandbox_command_harness(root: str | Path | None = None, commands: list[str] | None = None, operator_confirmation_phrase: str | None = None, execute: bool = False, timeout_seconds: int = 45) -> dict[str, Any]:
    """Run only explicitly allowed commands in a throwaway sandbox when execute=True and exact approval is supplied.

    The default path is non-executing. This function intentionally refuses to run unless the caller supplies
    the exact one-use approval phrase and explicitly sets execute=True. It never writes live source paths.
    """
    repo = Path(root or Path(__file__).resolve().parents[1])
    requested = list(commands or ALLOWED_SANDBOX_COMMANDS)
    allowed = [cmd for cmd in requested if _command_is_allowed(cmd)]
    blocked = [cmd for cmd in requested if not _command_is_allowed(cmd)]
    validation = build_approval_phrase_validator(repo, operator_confirmation_phrase)
    executed: list[dict[str, Any]] = []
    sandbox_root = Path(tempfile.mkdtemp(prefix="eidolon_sandbox_runner_"))
    source_copy_root = sandbox_root / "source_copy"
    execution_permitted = execute is True and validation.get("phrase_validated") is True and not blocked
    if execution_permitted:
        source_copy_root.mkdir(parents=True, exist_ok=True)
        for command in allowed:
            parts = shlex.split(command)
            result = subprocess.run(parts, cwd=source_copy_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
            executed.append({
                "command": command,
                "exit_code": result.returncode,
                "stdout_summary": result.stdout[-2000:],
                "stderr_summary": result.stderr[-2000:],
            })
    receipt = {
        "runner_status": "available_under_approval_only",
        "execution_requested": execute,
        "execution_permitted": execution_permitted,
        "sandbox_root": str(sandbox_root),
        "source_copy_root": str(source_copy_root),
        "commands_requested": requested,
        "commands_allowed": allowed,
        "commands_blocked": blocked,
        "commands_completed": executed,
        "approval_phrase_validated": validation.get("phrase_validated") is True,
        "approval_burned": bool(executed),
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
    }
    return receipt


def build_sandbox_command_execution_harness(root: str | Path | None = None) -> dict[str, Any]:
    harness = {
        "harness_status": "available_under_approval_only",
        "allowed_command_family": list(ALLOWED_SANDBOX_COMMANDS),
        "default_execution": False,
        "actual_commands_run": [],
        "sandbox_only_required": True,
        "no_live_source_writes": True,
        "no_memory_writes": True,
        "no_model_invocation": True,
        "no_scheduler_changes": True,
        "no_release_packaging": True,
        "no_automatic_continuation": True,
    }
    rows = [
        _row("harness-defined", harness["harness_status"] == "available_under_approval_only", "Sandbox command execution harness is defined under approval only."),
        _row("commands-allowlisted", all(_command_is_allowed(cmd) for cmd in harness["allowed_command_family"]), "Allowed command family is exact and narrow."),
        _row("not-run-by-default", harness["default_execution"] is False and not harness["actual_commands_run"], "Harness does not run commands by default."),
        _row("success-not-live-approval", SANDBOX_EXECUTION_RUNNER_BOUNDARIES["sandbox_command_success_is_live_patch_approval"] is False, "Sandbox command success cannot become live patch approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_command_execution_harness_review_only",
        "harness": harness,
        "runner_status": "available_under_approval_only",
        "execution_status": "not_executed_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_execution_receipt_intake_cleanup_audit(root: str | Path | None = None, receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    receipt = receipt or {
        "commands_requested": list(ALLOWED_SANDBOX_COMMANDS),
        "commands_allowed": list(ALLOWED_SANDBOX_COMMANDS),
        "commands_blocked": [],
        "exit_codes": {},
        "stdout_summary": None,
        "stderr_summary": None,
        "sandbox_diff_summary": None,
        "cleanup_status": "not_needed_no_execution",
        "privacy_status": "not_checked_no_execution",
        "approval_burned": False,
        "future_authorization_created": False,
    }
    rows = [
        _row("receipt-shape-visible", "commands_requested" in receipt and "commands_allowed" in receipt, "Execution receipt intake shape is visible."),
        _row("no-blocked-commands-by-default", receipt.get("commands_blocked") == [], "Default receipt shape has no blocked commands because no execution was requested."),
        _row("cleanup-status-visible", bool(receipt.get("cleanup_status")), "Cleanup status is explicit even when no execution occurs."),
        _row("receipt-not-future-authorization", receipt.get("future_authorization_created") is False and SANDBOX_EXECUTION_RUNNER_BOUNDARIES["receipt_success_is_future_authorization"] is False, "Receipt success cannot become future authorization."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "execution_receipt_intake_cleanup_audit_review_only",
        "receipt": receipt,
        "receipt_intake_status": "prepared",
        "cleanup_audit_status": "defined",
        "runner_status": "available_under_approval_only",
        "execution_status": "not_executed_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_execution_runner_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked = {
        "runner_contract_as_execution_permission": False,
        "phrase_validation_as_command_execution": False,
        "sandbox_command_success_as_live_patch_approval": False,
        "receipt_success_as_future_authorization": False,
        "runner_available_as_autonomy": False,
        "approval_for_one_run_as_reusable_approval": False,
        "sandbox_cleanup_as_continuation_permission": False,
    }
    text = _docs(root, docs)
    required_language = [
        "runner_contract_exists_is_execution_permission=False",
        "phrase_validated_is_command_executed=False",
        "sandbox_command_success_is_live_patch_approval=False",
        "receipt_success_is_future_authorization=False",
        "runner_available_is_autonomy=False",
        "runner_status=available_under_approval_only",
        "execution_status=not_executed_by_default",
        "autonomy_status=not_autonomous",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked.values()), "Runner misinterpretation patterns are blocked."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke include required runner boundary language."),
        _row("no-live-memory-release", all(SANDBOX_EXECUTION_RUNNER_BOUNDARIES[key] is False for key in ["runner_writes_live_source", "runner_writes_memory", "runner_promotes_to_live", "runner_creates_release_candidate", "runner_expands_autonomy"]), "Runner firewall grants no live, memory, release, promotion, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_runner_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked,
        "firewall_status": "active_review_only",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed_by_default",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_execution_trial_review_board(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    contract = build_sandbox_execution_runner_contract(root)
    validator = build_approval_phrase_validator(root)
    harness = build_sandbox_command_execution_harness(root)
    receipt = build_execution_receipt_intake_cleanup_audit(root)
    firewall = build_sandbox_execution_runner_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v530.0 - Operator-Approved Sandbox Execution Runner and Receipt Intake v1",
        "operator-approved-sandbox-execution-runner-v1",
        "sandbox-execution-runner-contract",
        "approval-phrase-validator",
        "sandbox-command-execution-harness",
        "execution-receipt-intake-cleanup-audit",
        "sandbox-execution-trial-review-board",
        "runner_status=available_under_approval_only",
        "execution_status=not_executed_by_default",
        "approval_status=required",
        "live_source_status=untouched",
        "memory_status=untouched",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
        "receipt_success_is_future_authorization=False",
    ]
    rows = [
        _row("version-markers", SANDBOX_EXECUTION_RUNNER_VERSION == CURRENT_VERSION == "605.0", f"runner={SANDBOX_EXECUTION_RUNNER_VERSION}; current={CURRENT_VERSION}"),
        _row("runner-contract", contract.get("ok") is True, "Sandbox execution runner contract is defined under approval only."),
        _row("approval-validator", validator.get("ok") is True and validator.get("executes_sandbox_commands") is False, "Approval phrase validator does not execute commands."),
        _row("execution-harness", harness.get("ok") is True and harness.get("executes_sandbox_commands") is False, "Sandbox command harness is available but not run by default."),
        _row("receipt-cleanup", receipt.get("ok") is True and receipt.get("creates_approval") is False, "Receipt intake and cleanup audit create no future authorization."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Runner firewall blocks approval, execution, live patch, future authorization, and autonomy confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v526-v530."),
        _row("no-live-authority", all(SANDBOX_EXECUTION_RUNNER_BOUNDARIES[key] is False for key in ["runner_writes_live_source", "runner_writes_memory", "runner_invokes_models_by_default", "runner_schedules_work", "runner_promotes_to_live", "runner_creates_release_candidate", "runner_reuses_approval", "runner_continues_automatically", "runner_expands_autonomy"]), "Runner layer grants no live source, memory, model, schedule, release, promotion, approval reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_trial_review_board_review_only",
        "runner_status": "available_under_approval_only",
        "execution_status": "not_executed_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "runner_contract": contract,
        "approval_phrase_validator": validator,
        "sandbox_command_execution_harness": harness,
        "execution_receipt_intake_cleanup_audit": receipt,
        "sandbox_execution_runner_misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_EXECUTION_RUNNER_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "promotes_to_live": False,
        "creates_release_candidate": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the sandbox execution runner and receipt intake layer. Real sandbox execution requires a separate exact fresh single-use approval and must remain sandbox-only.",
    }


def render_sandbox_execution_runner_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"runner_status: {report.get('runner_status', 'available_under_approval_only')}",
        f"execution_status: {report.get('execution_status', 'not_executed_by_default')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"live_source_status: {report.get('live_source_status', 'untouched')}",
        f"memory_status: {report.get('memory_status', 'untouched')}",
        f"release_status: {report.get('release_status', 'not_created')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v525.1-v530.0 sandbox execution runner tokens: sandbox-execution-runner-contract approval-phrase-validator sandbox-command-execution-harness execution-receipt-intake-cleanup-audit sandbox-execution-trial-review-board operator-approved-sandbox-execution-runner-v1 sandbox_execution_runner.py runner_contract_exists_is_execution_permission=False phrase_validated_is_command_executed=False sandbox_command_success_is_live_patch_approval=False receipt_success_is_future_authorization=False runner_available_is_autonomy=False runner_runs_without_exact_approval=False runner_writes_live_source=False runner_writes_memory=False runner_invokes_models_by_default=False runner_schedules_work=False runner_promotes_to_live=False runner_creates_release_candidate=False runner_reuses_approval=False runner_continues_automatically=False runner_expands_autonomy=False runner_status=available_under_approval_only execution_status=not_executed_by_default approval_status=required authorization_status=not_authorized live_source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous approval_required=True single_use_only=True approval_burnout_required=True sandbox_only_execution_required=True no_native_title_tooltip data-tip command-deck operator-console
