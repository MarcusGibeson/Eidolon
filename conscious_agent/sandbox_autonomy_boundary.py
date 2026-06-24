from __future__ import annotations

from pathlib import Path
from typing import Any
import json

SANDBOX_AUTONOMY_BOUNDARY_VERSION = "500.0"
CURRENT_VERSION = "500.0"
CURRENT_VERSION_TAG = "v500.0"
CURRENT_MILESTONE = "v500.0 Operator-Governed Autonomy Readiness Review Board v1"
NEXT_RECOMMENDED_ARC = "v501.0-v505.0 Manual Observation-to-Sandbox Packet Bridge v1"

SANDBOX_BOUNDARY_FLAGS: dict[str, bool] = {
    "sandbox_scope_is_authorization": False,
    "sandbox_readiness_is_approval": False,
    "sandbox_target_description_is_permission_to_execute": False,
    "sandbox_success_is_live_authorization": False,
    "sandbox_verification_is_approval": False,
    "sandbox_output_is_patch_execution_packet": False,
    "sandbox_trial_completion_permits_source_mutation": False,
    "promotion_requires_fresh_single_use_operator_approval": True,
    "live_source_writes_allowed": False,
    "memory_writes_allowed": False,
    "real_patch_application_allowed": False,
    "release_candidate_creation_allowed": False,
    "automatic_scheduling_allowed": False,
    "local_model_invocation_by_default_allowed": False,
    "approval_creation_allowed": False,
    "sandbox_execution_allowed": False,
    "source_mutation_allowed": False,
    "memory_mutation_allowed": False,
    "schedule_creation_allowed": False,
    "model_invocation_by_default_allowed": False,
    "automatic_continuation_allowed": False,
    "operator_review_required": True,
    "fresh_operator_approval_required": True,
    "review_only": True,
}

ALLOWED_PREP_ITEMS = [
    "read-only observation packet review",
    "proposal candidate selection for discussion",
    "sandbox target description",
    "allowed sandbox operations list",
    "forbidden live operations list",
    "operator review checklist",
]

FORBIDDEN_OPERATIONS = [
    "live source writes",
    "memory writes",
    "real patch application",
    "release candidate creation",
    "automatic scheduling",
    "local model invocation by default",
    "approval creation",
]


def _repo_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "blocked", "ok": bool(ok), "message": message}


def _boundary_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_keys = {"promotion_requires_fresh_single_use_operator_approval", "operator_review_required", "fresh_operator_approval_required", "review_only"}
    for key, value in SANDBOX_BOUNDARY_FLAGS.items():
        expected = key in true_keys
        rows.append(_row(f"boundary:{key}", value is expected, f"{key}={value}; expected {expected}."))
    return rows


def build_sandbox_only_autonomy_scope_definition(root: str | Path | None = None) -> dict[str, Any]:
    scope = {
        "allowed_prep_only": list(ALLOWED_PREP_ITEMS),
        "forbidden_operations": list(FORBIDDEN_OPERATIONS),
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "review_only": True,
    }
    rows = [_row(f"allowed:{item}", item in scope["allowed_prep_only"], f"Allowed prep-only item is defined: {item}.") for item in ALLOWED_PREP_ITEMS]
    rows.extend(_row(f"forbidden:{item}", item in scope["forbidden_operations"], f"Forbidden operation is defined: {item}.") for item in FORBIDDEN_OPERATIONS)
    rows.extend([
        _row("sandbox-scope-not-authorization", SANDBOX_BOUNDARY_FLAGS["sandbox_scope_is_authorization"] is False, "Sandbox scope is not authorization."),
        _row("sandbox-readiness-not-approval", SANDBOX_BOUNDARY_FLAGS["sandbox_readiness_is_approval"] is False, "Sandbox readiness is not approval."),
        _row("target-description-not-execution-permission", SANDBOX_BOUNDARY_FLAGS["sandbox_target_description_is_permission_to_execute"] is False, "A sandbox target description is not permission to execute."),
    ])
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": SANDBOX_AUTONOMY_BOUNDARY_VERSION,
        "state": "sandbox_only_autonomy_scope_definition_review_only",
        "scope": scope,
        "allowed_prep_only": list(ALLOWED_PREP_ITEMS),
        "forbidden_operations": list(FORBIDDEN_OPERATIONS),
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "review_only": True,
        "boundaries": dict(SANDBOX_BOUNDARY_FLAGS),
    }


def build_sandbox_autonomy_trial_packet_builder(root: str | Path | None = None) -> dict[str, Any]:
    packet = {
        "trial_id": "sandbox-autonomy-trial-prep-example",
        "source_proposal_id": "proposal-example",
        "sandbox_target": "isolated_sandbox_target_description_only",
        "allowed_operations": list(ALLOWED_PREP_ITEMS),
        "forbidden_operations": list(FORBIDDEN_OPERATIONS),
        "required_operator_approval": True,
        "fresh_approval_required": True,
        "rollback_requirement": "rollback packet required before any future approved sandbox execution harness exists",
        "verification_plan": ["compile", "targeted smoke", "operator review"],
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
    }
    required_fields = ["trial_id", "source_proposal_id", "sandbox_target", "allowed_operations", "forbidden_operations", "required_operator_approval", "fresh_approval_required", "rollback_requirement", "verification_plan", "authorization_status"]
    rows = [_row(f"field:{field}", field in packet, f"Sandbox autonomy trial packet includes {field}.") for field in required_fields]
    rows.extend([
        _row("authorization-not-authorized", packet["authorization_status"] == "not_authorized", "Packet creates no authorization."),
        _row("execution-not-executed", packet["execution_status"] == "not_executed", "Packet executes nothing."),
        _row("fresh-approval-required", packet["fresh_approval_required"] is True, "Fresh operator approval remains required."),
    ])
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": SANDBOX_AUTONOMY_BOUNDARY_VERSION,
        "state": "sandbox_autonomy_trial_packet_builder_review_only",
        "packet": packet,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "creates_execution_packet": False,
        "executes_sandbox_commands": False,
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_sandbox_to_live_boundary_hardening(root: str | Path | None = None) -> dict[str, Any]:
    boundary_statements = [
        "Sandbox success is not live authorization.",
        "Sandbox verification is not approval.",
        "Sandbox output is not a patch execution packet.",
        "Sandbox trial completion does not permit source mutation.",
        "Promotion requires fresh single-use operator approval.",
    ]
    rows = [
        _row("sandbox-success-not-live-auth", SANDBOX_BOUNDARY_FLAGS["sandbox_success_is_live_authorization"] is False, "Sandbox success is not live authorization."),
        _row("sandbox-verification-not-approval", SANDBOX_BOUNDARY_FLAGS["sandbox_verification_is_approval"] is False, "Sandbox verification is not approval."),
        _row("sandbox-output-not-execution-packet", SANDBOX_BOUNDARY_FLAGS["sandbox_output_is_patch_execution_packet"] is False, "Sandbox output is not a patch execution packet."),
        _row("trial-completion-no-source-mutation", SANDBOX_BOUNDARY_FLAGS["sandbox_trial_completion_permits_source_mutation"] is False, "Sandbox trial completion does not permit source mutation."),
        _row("fresh-single-use-promotion-approval", SANDBOX_BOUNDARY_FLAGS["promotion_requires_fresh_single_use_operator_approval"] is True, "Promotion requires fresh single-use operator approval."),
    ]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": SANDBOX_AUTONOMY_BOUNDARY_VERSION,
        "state": "sandbox_to_live_boundary_hardening_review_only",
        "boundary_statements": boundary_statements,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "sandbox_success_is_live_authorization": False,
        "sandbox_verification_is_approval": False,
        "sandbox_output_is_patch_execution_packet": False,
        "sandbox_trial_completion_permits_source_mutation": False,
        "promotion_requires_fresh_single_use_operator_approval": True,
        "authorization_status": "not_authorized",
        "review_only": True,
    }


def build_no_execution_sandbox_autonomy_audit(root: str | Path | None = None) -> dict[str, Any]:
    checks = {
        "sandbox_execution_allowed": False,
        "executes_sandbox_commands": False,
        "live_source_mutation_allowed": False,
        "memory_mutation_allowed": False,
        "schedule_creation_allowed": False,
        "model_invocation_by_default_allowed": False,
        "approval_creation_allowed": False,
        "proposal_approval_allowed": False,
        "release_candidate_creation_allowed": False,
        "sandbox_output_promotion_allowed": False,
        "automatic_continuation_allowed": False,
    }
    rows = [_row(name, value is False, f"Audit confirms {name}=false.") for name, value in checks.items()]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": SANDBOX_AUTONOMY_BOUNDARY_VERSION,
        "state": "no_execution_sandbox_autonomy_audit_review_only",
        "checks": checks,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "authorization_status": "not_authorized",
        "sandbox_execution_allowed": False,
        "live_source_mutation_allowed": False,
        "memory_mutation_allowed": False,
        "schedule_creation_allowed": False,
        "model_invocation_by_default_allowed": False,
        "approval_creation_allowed": False,
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "executes_actions": False,
        "expands_autonomy": False,
        "review_only": True,
    }


def build_sandbox_autonomy_boundary_prep_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/sandbox_autonomy_boundary.py",
        "conscious_agent/observation_proposal_queue.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
        "conscious_agent/smoke_segment_registry.py",
        "data/settings.json",
        "data/projects.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
    ])
    scope = build_sandbox_only_autonomy_scope_definition(repo)
    packet = build_sandbox_autonomy_trial_packet_builder(repo)
    boundary = build_sandbox_to_live_boundary_hardening(repo)
    no_exec = build_no_execution_sandbox_autonomy_audit(repo)
    required_tokens = [
        "sandbox-only-autonomy-scope-definition",
        "sandbox-autonomy-trial-packet-builder",
        "sandbox-to-live-boundary-hardening",
        "no-execution-sandbox-autonomy-audit",
        "sandbox-autonomy-boundary-prep-audit",
        "operator-governed-sandbox-autonomy-boundary-prep-v1",
        "sandbox_autonomy_boundary.py",
        "sandbox_scope_is_authorization=False",
        "sandbox_readiness_is_approval=False",
        "sandbox_target_description_is_permission_to_execute=False",
        "sandbox_success_is_live_authorization=False",
        "sandbox_verification_is_approval=False",
        "sandbox_output_is_patch_execution_packet=False",
        "sandbox_trial_completion_permits_source_mutation=False",
        "promotion_requires_fresh_single_use_operator_approval=True",
        "live_source_writes_allowed=False",
        "memory_writes_allowed=False",
        "real_patch_application_allowed=False",
        "release_candidate_creation_allowed=False",
        "automatic_scheduling_allowed=False",
        "local_model_invocation_by_default_allowed=False",
        "approval_creation_allowed=False",
        "sandbox_execution_allowed=False",
        "authorization_status=not_authorized",
    ]
    token_rows = [_row(f"token:{token}", token in docs, f"Required token present: {token}.") for token in required_tokens]
    rows = [
        _row("scope", scope.get("ok") is True, "Sandbox-only autonomy scope is defined as prep-only and non-authorizing."),
        _row("packet", packet.get("ok") is True, "Sandbox autonomy trial packet builder creates no execution or authorization."),
        _row("sandbox-to-live-boundary", boundary.get("ok") is True, "Sandbox-to-live promotion remains blocked without fresh single-use approval."),
        _row("no-execution", no_exec.get("ok") is True, "Sandbox boundary prep executes nothing and mutates nothing."),
    ] + token_rows
    ok = all(row["ok"] for row in rows)
    return {
        "version": SANDBOX_AUTONOMY_BOUNDARY_VERSION,
        "state": "sandbox_autonomy_boundary_prep_audit_review_only",
        "scope": scope,
        "packet": packet,
        "sandbox_to_live_boundary": boundary,
        "no_execution_audit": no_exec,
        "required_tokens": required_tokens,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_execution_packet": False,
        "executes_sandbox_commands": False,
        "applies_patches": False,
        "publishes_releases": False,
        "creates_release_candidate": False,
        "approves_proposals": False,
        "continues_automatically": False,
        "creates_approval": False,
        "expands_autonomy": False,
        "authorization_status": "not_authorized",
        "execution_status": "not_executed",
        "operator_review_required": True,
        "fresh_operator_approval_required": True,
        "review_only": True,
        "boundaries": dict(SANDBOX_BOUNDARY_FLAGS),
    }


def render_sandbox_autonomy_boundary_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'sandbox_autonomy_boundary')} :: {report.get('status', 'unknown')}",
        f"version: {report.get('version', SANDBOX_AUTONOMY_BOUNDARY_VERSION)}",
        "boundary: sandbox scope is not authorization; sandbox readiness is not approval; sandbox target descriptions are not permission to execute.",
        "sandbox-to-live: sandbox success is not live authorization; sandbox verification is not approval; sandbox output is not an execution packet; promotion requires fresh single-use operator approval.",
        "non-execution: no sandbox commands, no live source writes, no memory writes, no schedules, no default models, no approval creation, no release candidates, no promotion, no automatic continuation.",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines
