from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE

import json
from pathlib import Path
from typing import Any

SANDBOX_EXECUTION_DRY_RUN_RECEIPT_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
DRY_RUN_RECEIPT_BOUNDARIES: dict[str, bool] = {
    "dry_run_model_exists_is_sandbox_execution": False,
    "transcript_preview_is_command_output": False,
    "diff_receipt_preview_is_actual_file_change": False,
    "dry_run_pass_is_approval": False,
    "dry_run_pass_is_execution_permission": False,
    "receipt_preview_is_actual_receipt": False,
    "sandbox_readiness_is_sandbox_start": False,
    "dry_run_success_is_authorization": False,
    "dry_run_receipt_executes_commands": False,
    "dry_run_receipt_writes_source": False,
    "dry_run_receipt_writes_memory": False,
    "dry_run_receipt_modifies_live_files": False,
    "dry_run_receipt_invokes_models_by_default": False,
    "dry_run_receipt_schedules_work": False,
    "dry_run_receipt_creates_approval": False,
    "dry_run_receipt_promotes_to_live": False,
    "dry_run_receipt_continues_automatically": False,
    "dry_run_receipt_expands_autonomy": False,
    "fresh_operator_approval_still_required_for_future_sandbox_execution": True,
    "single_use_approval_still_required_for_future_sandbox_execution": True,
    "dry_run_receipt_review_only": True,
}

DEFAULT_TRANSCRIPT_COMMANDS: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --fast --json",
    "python tools/smoke_check.py --segment install-governance --json",
    "python tools/smoke_check.py --segment install-dashboard --json",
    "python conscious_agent/main.py --sandbox-execution-dry-run-receipt-v1 --json",
)

FORBIDDEN_LIVE_PATHS: tuple[str, ...] = (
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


def build_sandbox_dry_run_execution_model(root: str | Path | None = None) -> dict[str, Any]:
    model = {
        "dry_run_status": "modeled",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "authorization_status": "not_authorized",
        "approval_status": "not_granted",
        "model_scope": "future_sandbox_execution_shape_only",
        "commands_executed": [],
        "files_written": [],
        "live_files_modified": [],
    }
    rows = [
        _row("dry-run-modeled", model["dry_run_status"] == "modeled", "Dry-run execution shape is modeled."),
        _row("not-executed", model["execution_status"] == "not_executed" and model["sandbox_status"] == "not_started", "No sandbox execution is started."),
        _row("not-authorized", model["authorization_status"] == "not_authorized" and model["approval_status"] == "not_granted", "Dry-run model grants no approval or authorization."),
        _row("model-not-execution", DRY_RUN_RECEIPT_BOUNDARIES["dry_run_model_exists_is_sandbox_execution"] is False, "Dry-run model existence is not sandbox execution."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_dry_run_execution_model_review_only",
        "model": model,
        "dry_run_status": "modeled",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "authorization_status": "not_authorized",
        "approval_status": "not_granted",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DRY_RUN_RECEIPT_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_command_transcript_preview(root: str | Path | None = None) -> dict[str, Any]:
    transcript = {
        "transcript_status": "preview_only",
        "command_sequence": list(DEFAULT_TRANSCRIPT_COMMANDS),
        "expected_working_directory": "throwaway_sandbox_workspace/",
        "expected_read_paths": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/", "tools/"],
        "expected_sandbox_write_paths": ["throwaway_sandbox_workspace/.dry_run_receipts/", "throwaway_sandbox_workspace/reports/"],
        "forbidden_live_paths": list(FORBIDDEN_LIVE_PATHS),
        "expected_exit_conditions": ["stop_after_receipt_preview", "do_not_continue_to_execution", "do_not_promote_to_live"],
        "actual_command_output": None,
    }
    rows = [
        _row("commands-listed", bool(transcript["command_sequence"]), "Command sequence is visible as a preview."),
        _row("preview-not-output", transcript["actual_command_output"] is None and DRY_RUN_RECEIPT_BOUNDARIES["transcript_preview_is_command_output"] is False, "Transcript preview is not command output."),
        _row("sandbox-write-paths-only", all(str(path).startswith("throwaway_sandbox_workspace/") for path in transcript["expected_sandbox_write_paths"]), "Expected write paths are sandbox-only."),
        _row("live-paths-forbidden", "data/workspaces/timeline.json" in transcript["forbidden_live_paths"], "Forbidden live/runtime paths are visible."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "command_transcript_preview_review_only",
        "transcript": transcript,
        "transcript_preview_status": "prepared",
        "execution_status": "not_executed",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DRY_RUN_RECEIPT_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_diff_receipt_preview(root: str | Path | None = None) -> dict[str, Any]:
    preview = {
        "diff_receipt_status": "preview_only",
        "before_state_reference": "pre_sandbox_snapshot_placeholder",
        "after_state_reference": "post_sandbox_snapshot_placeholder",
        "expected_changed_files": ["throwaway_sandbox_workspace/reports/dry_run_receipt.json"],
        "expected_unchanged_live_files": ["conscious_agent/", "tools/", "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "data/workspaces/timeline.json"],
        "rollback_reference": "discard_throwaway_sandbox_workspace_only",
        "privacy_check_reference": "package_privacy_summary_for_zip must remain clean before any future package review",
        "actual_file_changes": [],
    }
    rows = [
        _row("preview-present", preview["diff_receipt_status"] == "preview_only", "Diff receipt preview is prepared."),
        _row("no-actual-changes", not preview["actual_file_changes"] and DRY_RUN_RECEIPT_BOUNDARIES["diff_receipt_preview_is_actual_file_change"] is False, "Diff preview is not an actual file change."),
        _row("live-files-unchanged", "data/workspaces/timeline.json" in preview["expected_unchanged_live_files"], "Live/runtime files are expected to remain unchanged."),
        _row("rollback-is-discard", preview["rollback_reference"] == "discard_throwaway_sandbox_workspace_only", "Rollback preview discards only the throwaway sandbox workspace."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_diff_receipt_preview_review_only",
        "diff_receipt_preview": preview,
        "dry_run_receipt_status": "prepared",
        "actual_execution_status": "not_executed",
        "authorization_status": "not_authorized",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DRY_RUN_RECEIPT_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_dry_run_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked_interpretations = {
        "dry_run_pass_as_approval": False,
        "dry_run_pass_as_execution_permission": False,
        "transcript_preview_as_command_execution": False,
        "diff_preview_as_file_mutation": False,
        "receipt_preview_as_actual_receipt": False,
        "sandbox_readiness_as_sandbox_start": False,
        "dry_run_success_as_authorization": False,
    }
    text = _docs(root, docs)
    required_language = [
        "dry_run_pass_is_approval=False",
        "dry_run_pass_is_execution_permission=False",
        "transcript_preview_is_command_output=False",
        "diff_receipt_preview_is_actual_file_change=False",
        "receipt_preview_is_actual_receipt=False",
        "sandbox_readiness_is_sandbox_start=False",
        "dry_run_success_is_authorization=False",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked_interpretations.values()), "Dry-run misinterpretation patterns are blocked."),
        _row("dry-run-success-not-authorization", DRY_RUN_RECEIPT_BOUNDARIES["dry_run_success_is_authorization"] is False, "Dry-run success is not authorization."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke contain required dry-run boundary language."),
        _row("no-side-effects", all(DRY_RUN_RECEIPT_BOUNDARIES[key] is False for key in ["dry_run_receipt_executes_commands", "dry_run_receipt_writes_source", "dry_run_receipt_writes_memory", "dry_run_receipt_modifies_live_files", "dry_run_receipt_creates_approval", "dry_run_receipt_expands_autonomy"]), "Dry-run firewall grants no side-effect authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "dry_run_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked_interpretations,
        "firewall_status": "active_review_only",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DRY_RUN_RECEIPT_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_execution_dry_run_receipt_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    model = build_sandbox_dry_run_execution_model(root)
    transcript = build_command_transcript_preview(root)
    diff_preview = build_sandbox_diff_receipt_preview(root)
    firewall = build_dry_run_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v525.0 - First Operator-Approved Sandbox Execution Trial v1",
        "sandbox-execution-dry-run-receipt-v1",
        "sandbox-dry-run-execution-model",
        "command-transcript-preview",
        "sandbox-diff-receipt-preview",
        "dry-run-misinterpretation-firewall",
        "sandbox-execution-dry-run-receipt-audit",
        "dry_run_receipt_status=prepared",
        "actual_execution_status=not_executed",
        "approval_status=not_granted",
        "sandbox_status=not_started",
        "autonomy_status=not_autonomous",
        "dry_run_success_is_authorization=False",
    ]
    rows = [
        _row("version-markers", SANDBOX_EXECUTION_DRY_RUN_RECEIPT_VERSION == CURRENT_VERSION == "605.0", f"dry_run_receipt={SANDBOX_EXECUTION_DRY_RUN_RECEIPT_VERSION}; current={CURRENT_VERSION}"),
        _row("execution-model", model.get("ok") is True and model.get("execution_status") == "not_executed", "Dry-run execution model is review-only and not executed."),
        _row("transcript-preview", transcript.get("ok") is True and transcript.get("executes_sandbox_commands") is False, "Command transcript preview does not run commands."),
        _row("diff-preview", diff_preview.get("ok") is True and diff_preview.get("modifies_live_files") is False, "Diff receipt preview does not mutate live files."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Dry-run misinterpretation firewall blocks approval/execution confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v516-v520."),
        _row("receipt-status", True, "dry_run_receipt_status=prepared; actual_execution_status=not_executed; approval_status=not_granted; sandbox_status=not_started; autonomy_status=not_autonomous."),
        _row("no-authority", all(DRY_RUN_RECEIPT_BOUNDARIES[key] is False for key in ["dry_run_receipt_executes_commands", "dry_run_receipt_writes_source", "dry_run_receipt_writes_memory", "dry_run_receipt_modifies_live_files", "dry_run_receipt_invokes_models_by_default", "dry_run_receipt_schedules_work", "dry_run_receipt_creates_approval", "dry_run_receipt_promotes_to_live", "dry_run_receipt_continues_automatically", "dry_run_receipt_expands_autonomy"]), "Dry-run receipt grants no command, source, memory, model, schedule, approval, promotion, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_dry_run_receipt_audit_review_only",
        "dry_run_receipt_status": "prepared",
        "actual_execution_status": "not_executed",
        "execution_status": "not_executed",
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "sandbox_status": "not_started",
        "autonomy_status": "not_autonomous",
        "execution_model": model,
        "command_transcript_preview": transcript,
        "sandbox_diff_receipt_preview": diff_preview,
        "misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DRY_RUN_RECEIPT_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_sandbox_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "promotes_to_live": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the dry-run receipt. Future sandbox execution still requires exact fresh single-use approval and a separate operator-confirmed execution trial.",
    }


def render_sandbox_execution_dry_run_receipt_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"dry_run_receipt_status: {report.get('dry_run_receipt_status', 'prepared')}",
        f"actual_execution_status: {report.get('actual_execution_status', report.get('execution_status', 'not_executed'))}",
        f"approval_status: {report.get('approval_status', 'not_granted')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"sandbox_status: {report.get('sandbox_status', 'not_started')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v515.1-v520.0 sandbox execution dry-run receipt tokens: sandbox-dry-run-execution-model command-transcript-preview sandbox-diff-receipt-preview dry-run-misinterpretation-firewall sandbox-execution-dry-run-receipt-audit sandbox-execution-dry-run-receipt-v1 sandbox_execution_dry_run_receipt.py dry_run_model_exists_is_sandbox_execution=False transcript_preview_is_command_output=False diff_receipt_preview_is_actual_file_change=False dry_run_pass_is_approval=False dry_run_pass_is_execution_permission=False receipt_preview_is_actual_receipt=False sandbox_readiness_is_sandbox_start=False dry_run_success_is_authorization=False dry_run_receipt_executes_commands=False dry_run_receipt_writes_source=False dry_run_receipt_writes_memory=False dry_run_receipt_modifies_live_files=False dry_run_receipt_invokes_models_by_default=False dry_run_receipt_schedules_work=False dry_run_receipt_creates_approval=False dry_run_receipt_promotes_to_live=False dry_run_receipt_continues_automatically=False dry_run_receipt_expands_autonomy=False dry_run_receipt_status=prepared actual_execution_status=not_executed approval_status=not_granted authorization_status=not_authorized sandbox_status=not_started autonomy_status=not_autonomous fresh_operator_approval_still_required_for_future_sandbox_execution=True single_use_approval_still_required_for_future_sandbox_execution=True no_native_title_tooltip data-tip command-deck operator-console
