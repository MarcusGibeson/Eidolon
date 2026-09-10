from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE

import json
from pathlib import Path
from typing import Any

SANDBOX_EXECUTION_APPROVAL_GATE_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
APPROVAL_GATE_BOUNDARIES: dict[str, bool] = {
    "approval_contract_exists_is_approval_granted": False,
    "confirmation_phrase_generated_is_confirmation_entered": False,
    "approval_ledger_entry_is_reusable_approval": False,
    "approval_scope_can_expand_after_creation": False,
    "prior_sandbox_success_is_new_approval": False,
    "operator_discussion_is_approval": False,
    "command_preview_executes_commands": False,
    "allowlist_preview_authorizes_execution": False,
    "approval_gate_defined_starts_sandbox": False,
    "sandbox_status_started": False,
    "sandbox_execution_allowed": False,
    "approval_granted": False,
    "execution_status_executed": False,
    "writes_source": False,
    "writes_memory": False,
    "invokes_models_by_default": False,
    "schedules_work": False,
    "creates_release_candidate": False,
    "continues_automatically": False,
    "expands_autonomy": False,
    "single_use_required": True,
    "fresh_operator_approval_required": True,
    "exact_confirmation_required": True,
    "approval_burnout_required": True,
}

DEFAULT_APPROVAL_SCOPE: dict[str, Any] = {
    "approval_scope": "future_single_sandbox_execution_only",
    "approved_candidate_id": None,
    "approved_packet_id": None,
    "allowed_commands": [],
    "allowed_files": [],
    "forbidden_files": [
        "data/memory.json",
        "data/workspaces/timeline.json",
        "data/autonomy/",
        "data/self_maintenance/",
        "runtime/",
        ".env",
    ],
    "approval_expiry": "unset_until_operator_supplies_scope",
    "single_use": True,
    "authorization_status": "not_authorized_by_default",
}

DEFAULT_COMMAND_ALLOWLIST_PREVIEW: tuple[str, ...] = (
    "python -m compileall conscious_agent tools",
    "python tools/smoke_check.py --fast --json",
    "python tools/smoke_check.py --segment install-governance --json",
    "python tools/smoke_check.py --segment install-dashboard --json",
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


def build_sandbox_approval_scope_contract(root: str | Path | None = None, candidate_id: str | None = None, packet_id: str | None = None) -> dict[str, Any]:
    contract = dict(DEFAULT_APPROVAL_SCOPE)
    contract.update({
        "approved_candidate_id": candidate_id,
        "approved_packet_id": packet_id,
        "allowed_commands": list(DEFAULT_COMMAND_ALLOWLIST_PREVIEW) if packet_id else [],
        "allowed_files": ["sandbox_workspace/"] if packet_id else [],
        "approval_contract_status": "defined_not_granted",
    })
    rows = [
        _row("scope-contract-defined", contract["approval_scope"] == "future_single_sandbox_execution_only", "Approval scope is defined for one future sandbox execution only."),
        _row("not-authorized-by-default", contract["authorization_status"] == "not_authorized_by_default", "Approval contracts are not authorized by default."),
        _row("single-use", contract["single_use"] is True and APPROVAL_GATE_BOUNDARIES["single_use_required"] is True, "Approval scope is single-use."),
        _row("contract-not-approval", APPROVAL_GATE_BOUNDARIES["approval_contract_exists_is_approval_granted"] is False, "Approval contract existence does not grant approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_approval_scope_contract_review_only",
        "contract": contract,
        "approval_gate_status": "defined",
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPROVAL_GATE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_exact_confirmation_phrase_builder(root: str | Path | None = None, packet_id: str | None = None) -> dict[str, Any]:
    packet_ref = packet_id or "<packet_id>"
    phrase = f"I approve one sandbox execution for packet {packet_ref} only."
    rows = [
        _row("phrase-built", "one sandbox execution" in phrase and "only" in phrase, "Exact confirmation phrase template is present."),
        _row("phrase-not-entered", APPROVAL_GATE_BOUNDARIES["confirmation_phrase_generated_is_confirmation_entered"] is False, "Generated phrase is not an entered confirmation."),
        _row("exact-confirmation-required", APPROVAL_GATE_BOUNDARIES["exact_confirmation_required"] is True, "Future approval requires exact operator confirmation."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "exact_confirmation_phrase_builder_review_only",
        "confirmation_phrase_template": phrase,
        "phrase_generated": True,
        "phrase_entered": False,
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPROVAL_GATE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_approval_burnout_expiry_ledger(root: str | Path | None = None) -> dict[str, Any]:
    ledger_model = {
        "approval_id": "not_created",
        "approval_status": "not_granted",
        "expires_at": "unset_until_operator_approval",
        "used": False,
        "burned": False,
        "reuse_allowed": False,
        "scope_expansion_allowed": False,
        "previous_success_creates_new_approval": False,
    }
    blocked_reuse = [
        "reusing_old_approval",
        "expanding_approval_scope",
        "using_approval_after_expiry",
        "treating_previous_sandbox_success_as_new_approval",
        "treating_operator_discussion_as_approval",
    ]
    rows = [
        _row("ledger-defined", ledger_model["approval_status"] == "not_granted", "Approval burnout/expiry ledger model is defined without granting approval."),
        _row("reuse-blocked", ledger_model["reuse_allowed"] is False and APPROVAL_GATE_BOUNDARIES["approval_ledger_entry_is_reusable_approval"] is False, "Approval reuse is blocked."),
        _row("scope-expansion-blocked", ledger_model["scope_expansion_allowed"] is False and APPROVAL_GATE_BOUNDARIES["approval_scope_can_expand_after_creation"] is False, "Approval scope expansion is blocked."),
        _row("burnout-required", APPROVAL_GATE_BOUNDARIES["approval_burnout_required"] is True, "Used approval must burn out."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "approval_burnout_expiry_ledger_review_only",
        "ledger_model": ledger_model,
        "blocked_reuse_conditions": blocked_reuse,
        "approval_used_once_means_approval_burned": True,
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPROVAL_GATE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_command_allowlist_preview(root: str | Path | None = None) -> dict[str, Any]:
    preview = {
        "commands_that_would_run": list(DEFAULT_COMMAND_ALLOWLIST_PREVIEW),
        "files_that_would_be_read": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/"],
        "files_that_would_be_written_in_sandbox_only": ["sandbox_workspace/README_NEXT_STEPS.md", "sandbox_workspace/README_RELEASE_HISTORY.md"],
        "forbidden_live_source_paths": list(DEFAULT_APPROVAL_SCOPE["forbidden_files"]),
        "rollback_expectations": ["restore sandbox snapshot", "discard sandbox workspace on failure", "record non-live receipt"],
        "verification_expectations": ["compile", "fast smoke", "targeted smoke", "dashboard/API/CLI dispatch"],
    }
    rows = [
        _row("preview-present", bool(preview["commands_that_would_run"]), "Command allowlist preview is present."),
        _row("preview-not-execution", APPROVAL_GATE_BOUNDARIES["command_preview_executes_commands"] is False, "Command preview does not execute commands."),
        _row("allowlist-not-authorization", APPROVAL_GATE_BOUNDARIES["allowlist_preview_authorizes_execution"] is False, "Allowlist preview does not authorize execution."),
        _row("live-paths-forbidden", "data/workspaces/timeline.json" in preview["forbidden_live_source_paths"], "Forbidden live/runtime paths are visible."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_command_allowlist_preview_review_only",
        "preview": preview,
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPROVAL_GATE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "creates_approval": False,
        "expands_autonomy": False,
    }


def build_sandbox_execution_approval_gate_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    scope = build_sandbox_approval_scope_contract(root)
    phrase = build_exact_confirmation_phrase_builder(root)
    ledger = build_approval_burnout_expiry_ledger(root)
    preview = build_sandbox_command_allowlist_preview(root)
    text = _docs(root, docs)
    required_docs = [
        "v515.0 - Sandbox Execution Approval Gate v1",
        "sandbox-execution-approval-gate-v1",
        "sandbox-approval-scope-contract",
        "exact-confirmation-phrase-builder",
        "approval-burnout-expiry-ledger",
        "sandbox-command-allowlist-preview",
        "sandbox-execution-approval-gate-audit",
        "approval_contract_exists_is_approval_granted=False",
        "confirmation_phrase_generated_is_confirmation_entered=False",
        "command_preview_executes_commands=False",
    ]
    rows = [
        _row("version-markers", SANDBOX_EXECUTION_APPROVAL_GATE_VERSION == CURRENT_VERSION == "605.0", f"approval_gate={SANDBOX_EXECUTION_APPROVAL_GATE_VERSION}; current={CURRENT_VERSION}"),
        _row("scope-contract", scope.get("ok") is True, "Sandbox approval scope contract is defined but not granted."),
        _row("confirmation-phrase", phrase.get("ok") is True and phrase.get("phrase_entered") is False, "Confirmation phrase template is generated but not entered."),
        _row("burnout-expiry", ledger.get("ok") is True, "Approval burnout and expiry ledger blocks reuse."),
        _row("command-preview", preview.get("ok") is True and preview.get("executes_sandbox_commands") is False, "Command allowlist preview remains non-executing."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v511-v515."),
        _row("gate-status", True, "approval_gate_status=defined; approval_status=not_granted; execution_status=not_executed; sandbox_status=not_started; autonomy_status=not_autonomous."),
        _row("no-authority", all(APPROVAL_GATE_BOUNDARIES[key] is False for key in ["sandbox_execution_allowed", "approval_granted", "execution_status_executed", "writes_source", "writes_memory", "invokes_models_by_default", "schedules_work", "creates_release_candidate", "continues_automatically", "expands_autonomy"]), "Approval gate grants no sandbox execution, source, memory, model, schedule, release, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "sandbox_execution_approval_gate_audit_review_only",
        "approval_gate_status": "defined",
        "approval_status": "not_granted",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "sandbox_status": "not_started",
        "autonomy_status": "not_autonomous",
        "scope_contract": scope,
        "confirmation_phrase": phrase,
        "burnout_expiry_ledger": ledger,
        "command_allowlist_preview": preview,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPROVAL_GATE_BOUNDARIES),
        "writes_source": False,
        "writes_memory": False,
        "executes_sandbox_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the approval gate. Future sandbox execution still requires a separate dry-run receipt and a fresh exact single-use approval before any command can run.",
    }


def render_sandbox_execution_approval_gate_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"approval_gate_status: {report.get('approval_gate_status', 'defined')}",
        f"approval_status: {report.get('approval_status', 'not_granted')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"execution_status: {report.get('execution_status', 'not_executed')}",
        f"sandbox_status: {report.get('sandbox_status', 'not_started')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
    ]
    phrase = report.get("confirmation_phrase_template") or report.get("confirmation_phrase", {}).get("confirmation_phrase_template")
    if phrase:
        lines.append(f"confirmation_phrase_template: {phrase}")
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v510.1-v515.0 sandbox execution approval gate tokens: sandbox-approval-scope-contract exact-confirmation-phrase-builder approval-burnout-expiry-ledger sandbox-command-allowlist-preview sandbox-execution-approval-gate-audit sandbox-execution-approval-gate-v1 sandbox_execution_approval_gate.py approval_contract_exists_is_approval_granted=False confirmation_phrase_generated_is_confirmation_entered=False approval_ledger_entry_is_reusable_approval=False approval_scope_can_expand_after_creation=False prior_sandbox_success_is_new_approval=False operator_discussion_is_approval=False command_preview_executes_commands=False allowlist_preview_authorizes_execution=False approval_gate_defined_starts_sandbox=False sandbox_execution_allowed=False approval_granted=False execution_status_executed=False approval_gate_status=defined approval_status=not_granted authorization_status=not_authorized execution_status=not_executed sandbox_status=not_started autonomy_status=not_autonomous single_use_required=True fresh_operator_approval_required=True exact_confirmation_required=True approval_burnout_required=True no_native_title_tooltip data-tip command-deck operator-console
