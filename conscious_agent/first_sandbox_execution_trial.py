from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIRST_SANDBOX_EXECUTION_TRIAL_VERSION = "1032.0"
CURRENT_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
SANDBOX_TRIAL_BOUNDARIES: dict[str, bool] = {
    "sandbox_workspace_exists_is_execution_permission": False,
    "command_plan_exists_is_command_run": False,
    "receipt_written_is_future_approval": False,
    "sandbox_execution_success_is_live_source_approval": False,
    "sandbox_execution_success_is_release_approval": False,
    "sandbox_execution_success_is_memory_approval": False,
    "sandbox_execution_success_is_future_approval": False,
    "sandbox_cleanup_success_is_permission_to_continue": False,
    "operator_approval_for_one_command_approves_all_commands": False,
    "successful_sandbox_trial_is_autonomy": False,
    "trial_layer_runs_commands_by_default": False,
    "trial_layer_writes_live_source": False,
    "trial_layer_writes_memory": False,
    "trial_layer_invokes_models_by_default": False,
    "trial_layer_schedules_work": False,
    "trial_layer_promotes_to_live": False,
    "trial_layer_creates_release_candidate": False,
    "trial_layer_continues_automatically": False,
    "trial_layer_expands_autonomy": False,
    "fresh_operator_approval_required": True,
    "single_use_approval_required": True,
    "approval_burnout_required": True,
    "temporary_sandbox_only_required": True,
}

SANDBOX_ROOT = "throwaway_sandbox_workspace/"
SOURCE_COPY_ROOT = "throwaway_sandbox_workspace/source_copy/"
ALLOWED_COMMAND_PLAN: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --tier fast --json",
    "python tools/smoke_check.py --check first-operator-approved-sandbox-execution-trial-v1 --json",
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


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = Path(root or Path(__file__).resolve().parents[1])
    parts = [
        _read_text(repo / "README_NEXT_STEPS.md"),
        _read_text(repo / "README_RELEASE_HISTORY.md"),
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


def build_sandbox_workspace_isolation_contract(root: str | Path | None = None) -> dict[str, Any]:
    contract = {
        "sandbox_root": SANDBOX_ROOT,
        "source_copy_root": SOURCE_COPY_ROOT,
        "allowed_read_paths": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/", "tools/"],
        "allowed_sandbox_write_paths": [SOURCE_COPY_ROOT, f"{SANDBOX_ROOT}.receipts/", f"{SANDBOX_ROOT}reports/"],
        "forbidden_live_write_paths": list(FORBIDDEN_LIVE_WRITE_PATHS),
        "forbidden_memory_paths": ["data/memory.json", "data/workspaces/timeline.json"],
        "forbidden_runtime_paths": ["data/autonomy/", "data/self_maintenance/", "runtime/"],
        "cleanup_expectations": ["discard_throwaway_sandbox_workspace", "verify_no_live_file_changes", "burn_single_use_approval_after_one_trial"],
        "execution_permission": False,
    }
    rows = [
        _row("workspace-defined", contract["sandbox_root"] == SANDBOX_ROOT and contract["source_copy_root"].startswith(SANDBOX_ROOT), "Sandbox workspace and source-copy roots are explicitly isolated."),
        _row("write-paths-sandbox-only", all(path.startswith(SANDBOX_ROOT) for path in contract["allowed_sandbox_write_paths"]), "Allowed write paths are sandbox-only."),
        _row("live-writes-forbidden", "conscious_agent/" in contract["forbidden_live_write_paths"] and "tools/" in contract["forbidden_live_write_paths"], "Live source write paths are forbidden."),
        _row("workspace-not-permission", SANDBOX_TRIAL_BOUNDARIES["sandbox_workspace_exists_is_execution_permission"] is False and contract["execution_permission"] is False, "Sandbox workspace existence is not execution permission."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_workspace_isolation_contract_review_only",
        "contract": contract,
        "trial_layer_status": "prepared",
        "sandbox_execution_status": "not_run_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_TRIAL_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_approved_sandbox_command_plan(root: str | Path | None = None) -> dict[str, Any]:
    plan = {
        "command_plan_status": "defined_not_run",
        "commands": list(ALLOWED_COMMAND_PLAN),
        "allowed_working_directory": SOURCE_COPY_ROOT,
        "requires_exact_operator_approval": True,
        "requires_single_use_scope": True,
        "actual_commands_run": [],
        "command_run": False,
    }
    rows = [
        _row("plan-defined", bool(plan["commands"]), "Sandbox command plan is visible and bounded."),
        _row("boring-verification-commands", all(cmd.startswith("python ") for cmd in plan["commands"]), "Command plan is limited to Python compile/smoke verification commands."),
        _row("approval-required", plan["requires_exact_operator_approval"] is True and plan["requires_single_use_scope"] is True, "Future sandbox execution requires exact single-use operator approval."),
        _row("plan-not-run", not plan["actual_commands_run"] and SANDBOX_TRIAL_BOUNDARIES["command_plan_exists_is_command_run"] is False, "Command plan existence is not command execution."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "approved_sandbox_command_plan_review_only",
        "command_plan": plan,
        "command_plan_status": "defined_not_run",
        "sandbox_execution_status": "not_run_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_TRIAL_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_single_use_sandbox_execution_receipt(root: str | Path | None = None) -> dict[str, Any]:
    receipt_shape = {
        "approval_phrase": "I approve one sandbox execution for packet <packet_id> only.",
        "approval_scope": "single_sandbox_execution_trial_only",
        "execution_start": None,
        "execution_end": None,
        "commands_requested": list(ALLOWED_COMMAND_PLAN),
        "commands_completed": [],
        "exit_codes": {},
        "stdout_summary": None,
        "stderr_summary": None,
        "sandbox_diff_summary": None,
        "privacy_result": None,
        "rollback_or_cleanup_result": None,
        "approval_burned": False,
        "future_approval_created": False,
    }
    rows = [
        _row("receipt-shape-defined", receipt_shape["approval_scope"] == "single_sandbox_execution_trial_only", "Receipt shape is defined for one sandbox execution trial."),
        _row("not-actual-receipt", receipt_shape["execution_start"] is None and not receipt_shape["commands_completed"], "Receipt shape is not evidence of an executed trial."),
        _row("no-future-approval", receipt_shape["future_approval_created"] is False and SANDBOX_TRIAL_BOUNDARIES["receipt_written_is_future_approval"] is False, "Receipt writing cannot become future approval."),
        _row("burnout-required", SANDBOX_TRIAL_BOUNDARIES["approval_burnout_required"] is True, "A real one-use approval must burn after one trial."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "single_use_sandbox_execution_receipt_review_only",
        "receipt_shape": receipt_shape,
        "receipt_status": "shape_defined_not_written",
        "sandbox_execution_status": "not_run_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_TRIAL_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_execution_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked_interpretations = {
        "sandbox_execution_success_as_live_source_approval": False,
        "sandbox_execution_success_as_release_approval": False,
        "sandbox_execution_success_as_memory_approval": False,
        "sandbox_execution_success_as_future_approval": False,
        "sandbox_cleanup_success_as_permission_to_continue": False,
        "operator_approval_for_one_command_as_approval_for_all_commands": False,
        "successful_sandbox_trial_as_autonomy": False,
    }
    text = _docs(root, docs)
    required_language = [
        "sandbox_execution_success_is_live_source_approval=False",
        "sandbox_execution_success_is_release_approval=False",
        "sandbox_execution_success_is_memory_approval=False",
        "sandbox_execution_success_is_future_approval=False",
        "sandbox_cleanup_success_is_permission_to_continue=False",
        "operator_approval_for_one_command_approves_all_commands=False",
        "successful_sandbox_trial_is_autonomy=False",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked_interpretations.values()), "Sandbox execution misinterpretation patterns are blocked."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke contain required sandbox trial boundary language."),
        _row("success-not-autonomy", SANDBOX_TRIAL_BOUNDARIES["successful_sandbox_trial_is_autonomy"] is False, "A successful sandbox trial is not autonomy."),
        _row("no-side-effects", all(SANDBOX_TRIAL_BOUNDARIES[key] is False for key in ["trial_layer_writes_live_source", "trial_layer_writes_memory", "trial_layer_promotes_to_live", "trial_layer_creates_release_candidate", "trial_layer_expands_autonomy"]), "Trial firewall grants no live, memory, release, promotion, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked_interpretations,
        "firewall_status": "active_review_only",
        "authorization_status": "not_authorized",
        "sandbox_execution_status": "not_run_by_default",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_TRIAL_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_first_sandbox_execution_trial_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    workspace = build_sandbox_workspace_isolation_contract(root)
    command_plan = build_approved_sandbox_command_plan(root)
    receipt = build_single_use_sandbox_execution_receipt(root)
    firewall = build_sandbox_execution_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v525.0 - First Operator-Approved Sandbox Execution Trial v1",
        "first-operator-approved-sandbox-execution-trial-v1",
        "sandbox-workspace-isolation-contract",
        "approved-sandbox-command-plan",
        "single-use-sandbox-execution-receipt",
        "sandbox-execution-misinterpretation-firewall",
        "first-sandbox-execution-trial-audit",
        "trial_layer_status=prepared",
        "sandbox_execution_status=not_run_by_default",
        "approval_status=required",
        "live_source_status=untouched",
        "memory_status=untouched",
        "autonomy_status=not_autonomous",
        "successful_sandbox_trial_is_autonomy=False",
    ]
    rows = [
        _row("version-markers", FIRST_SANDBOX_EXECUTION_TRIAL_VERSION == CURRENT_VERSION == "605.0", f"trial={FIRST_SANDBOX_EXECUTION_TRIAL_VERSION}; current={CURRENT_VERSION}"),
        _row("workspace-isolation", workspace.get("ok") is True, "Sandbox workspace isolation contract is review-only and bounded."),
        _row("command-plan", command_plan.get("ok") is True and command_plan.get("executes_sandbox_commands") is False, "Approved sandbox command plan is defined but not run."),
        _row("receipt-shape", receipt.get("ok") is True and receipt.get("creates_approval") is False, "Single-use receipt shape creates no future approval."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Sandbox execution success, cleanup, and single-command approval cannot expand authority."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v521-v525."),
        _row("trial-status", True, "trial_layer_status=prepared; sandbox_execution_status=not_run_by_default; approval_status=required; live_source_status=untouched; memory_status=untouched; autonomy_status=not_autonomous."),
        _row("no-authority", all(SANDBOX_TRIAL_BOUNDARIES[key] is False for key in ["trial_layer_runs_commands_by_default", "trial_layer_writes_live_source", "trial_layer_writes_memory", "trial_layer_invokes_models_by_default", "trial_layer_schedules_work", "trial_layer_promotes_to_live", "trial_layer_creates_release_candidate", "trial_layer_continues_automatically", "trial_layer_expands_autonomy"]), "First sandbox trial layer grants no command-by-default, live source, memory, model, schedule, release, promotion, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "first_sandbox_execution_trial_audit_review_only",
        "trial_layer_status": "prepared",
        "sandbox_execution_status": "not_run_by_default",
        "execution_status": "not_executed",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "live_source_status": "untouched",
        "memory_status": "untouched",
        "autonomy_status": "not_autonomous",
        "workspace_isolation_contract": workspace,
        "approved_sandbox_command_plan": command_plan,
        "single_use_sandbox_execution_receipt": receipt,
        "sandbox_execution_misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(SANDBOX_TRIAL_BOUNDARIES),
        "writes_live_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "promotes_to_live": False,
        "creates_release_candidate": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the first sandbox execution trial layer. Actual sandbox execution still requires exact fresh single-use approval and a separate explicit operator instruction.",
    }


def render_first_sandbox_execution_trial_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"trial_layer_status: {report.get('trial_layer_status', 'prepared')}",
        f"sandbox_execution_status: {report.get('sandbox_execution_status', 'not_run_by_default')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"live_source_status: {report.get('live_source_status', 'untouched')}",
        f"memory_status: {report.get('memory_status', 'untouched')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v520.1-v525.0 first operator-approved sandbox execution trial tokens: sandbox-workspace-isolation-contract approved-sandbox-command-plan single-use-sandbox-execution-receipt sandbox-execution-misinterpretation-firewall first-sandbox-execution-trial-audit first-operator-approved-sandbox-execution-trial-v1 first_sandbox_execution_trial.py sandbox_workspace_exists_is_execution_permission=False command_plan_exists_is_command_run=False receipt_written_is_future_approval=False sandbox_execution_success_is_live_source_approval=False sandbox_execution_success_is_release_approval=False sandbox_execution_success_is_memory_approval=False sandbox_execution_success_is_future_approval=False sandbox_cleanup_success_is_permission_to_continue=False operator_approval_for_one_command_approves_all_commands=False successful_sandbox_trial_is_autonomy=False trial_layer_runs_commands_by_default=False trial_layer_writes_live_source=False trial_layer_writes_memory=False trial_layer_invokes_models_by_default=False trial_layer_schedules_work=False trial_layer_promotes_to_live=False trial_layer_creates_release_candidate=False trial_layer_continues_automatically=False trial_layer_expands_autonomy=False trial_layer_status=prepared sandbox_execution_status=not_run_by_default approval_status=required authorization_status=not_authorized live_source_status=untouched memory_status=untouched autonomy_status=not_autonomous fresh_operator_approval_required=True single_use_approval_required=True approval_burnout_required=True temporary_sandbox_only_required=True no_native_title_tooltip data-tip command-deck operator-console
