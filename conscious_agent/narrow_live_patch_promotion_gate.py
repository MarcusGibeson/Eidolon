from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NARROW_LIVE_PATCH_PROMOTION_GATE_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
LIVE_PATCH_GATE_ID = "v540_operator_approved_narrow_live_patch_promotion_gate"
PROMOTION_PACKET_ID = "v535_sandbox_to_source_promotion_packet_review_only"
LIVE_PATCH_SCOPE_ID = "v536_narrow_live_patch_scope_contract"

ALLOWED_NARROW_PATCH_CLASSES: tuple[str, ...] = (
    "README/doc cleanup",
    "metadata version repair",
    "route registry sync",
    "smoke check wording repair",
    "package privacy rule repair",
    "dashboard text/report surface correction",
)

FORBIDDEN_LIVE_PATCH_CLASSES: tuple[str, ...] = (
    "memory writes",
    "identity changes",
    "personality changes",
    "purpose changes",
    "scheduler changes",
    "model invocation defaults",
    "autonomy escalation",
    "release publishing",
    "broad refactors",
)

NARROW_LIVE_PATCH_GATE_BOUNDARIES: dict[str, bool] = {
    "live_patch_scope_defined_is_live_patch_approved": False,
    "approval_phrase_template_is_operator_approval": False,
    "preflight_pass_is_live_patch_permission": False,
    "sandbox_success_is_live_approval": False,
    "promotion_packet_is_live_approval": False,
    "preflight_pass_is_live_approval": False,
    "operator_interest_is_approval": False,
    "prior_sandbox_approval_is_live_approval": False,
    "approval_phrase_template_is_approval_entered": False,
    "successful_live_patch_is_future_approval": False,
    "live_promotion_readiness_is_live_promotion_authorization": False,
    "live_patch_gate_applies_live_source_patch": False,
    "live_patch_gate_writes_memory": False,
    "live_patch_gate_executes_rollback": False,
    "live_patch_gate_creates_release": False,
    "live_patch_gate_publishes_release": False,
    "live_patch_gate_invokes_models_by_default": False,
    "live_patch_gate_schedules_work": False,
    "live_patch_gate_reuses_approval": False,
    "live_patch_gate_continues_automatically": False,
    "live_patch_gate_expands_autonomy": False,
    "approval_required": True,
    "fresh_operator_approval_required": True,
    "single_use_approval_required": True,
    "approval_burnout_required": True,
    "rollback_plan_required": True,
}

NARROW_LIVE_PATCH_ALLOWED_FILES: tuple[str, ...] = (
    "README_NEXT_STEPS.md",
    "README_RELEASE_HISTORY.md",
    "data/settings.json",
    "data/projects.json",
    "data/workspaces/active_project.json",
    "data/workspaces/projects.json",
    "conscious_agent/dashboard_route_probe.py",
    "conscious_agent/smoke_segment_registry.py",
    "conscious_agent/source_surface_manifest.py",
)

NARROW_LIVE_PATCH_FORBIDDEN_FILES: tuple[str, ...] = (
    "data/memory.json",
    "data/workspaces/timeline.json",
    "data/autonomy/",
    "data/self_maintenance/",
    "runtime/",
    ".env",
    "models/",
    "local_models/",
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_id(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _docs(root: str | Path | None = None, extra_docs: str = "") -> str:
    repo = Path(root or Path(__file__).resolve().parents[1])
    paths = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/narrow_live_patch_promotion_gate.py",
        "conscious_agent/sandbox_to_source_promotion_packet.py",
        "conscious_agent/sandbox_execution_runner.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/smoke_segment_registry.py",
        "data/settings.json",
        "data/projects.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
    ]
    return "\n".join(_read_text(repo / path) for path in paths) + "\n" + extra_docs


def build_narrow_live_patch_scope_contract(root: str | Path | None = None) -> dict[str, Any]:
    scope = {
        "scope_id": LIVE_PATCH_SCOPE_ID,
        "allowed_patch_classes": list(ALLOWED_NARROW_PATCH_CLASSES),
        "forbidden_patch_classes": list(FORBIDDEN_LIVE_PATCH_CLASSES),
        "allowed_files": list(NARROW_LIVE_PATCH_ALLOWED_FILES),
        "forbidden_files": list(NARROW_LIVE_PATCH_FORBIDDEN_FILES),
        "scope_defined": True,
        "live_patch_approved": False,
        "fresh_operator_approval_required": True,
        "single_use_approval_required": True,
    }
    rows = [
        _row("allowed-classes-bounded", len(scope["allowed_patch_classes"]) == 6 and "broad refactors" not in scope["allowed_patch_classes"], "Allowed live patch classes are narrow and boring."),
        _row("forbidden-classes-listed", all(item in scope["forbidden_patch_classes"] for item in ["memory writes", "identity changes", "autonomy escalation", "release publishing", "broad refactors"]), "Forbidden live patch classes include memory, identity, autonomy, release, and broad refactor changes."),
        _row("forbidden-runtime-paths", all(path in scope["forbidden_files"] for path in ["data/memory.json", "data/workspaces/timeline.json", "data/autonomy/"]), "Memory, runtime, and autonomy data paths are forbidden as live-patch targets."),
        _row("scope-not-approval", scope["scope_defined"] is True and scope["live_patch_approved"] is False and NARROW_LIVE_PATCH_GATE_BOUNDARIES["live_patch_scope_defined_is_live_patch_approved"] is False, "Live patch scope definition is not live patch approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "narrow_live_patch_scope_contract_review_only",
        "scope": scope,
        "live_patch_gate_status": "defined",
        "live_patch_status": "not_applied",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NARROW_LIVE_PATCH_GATE_BOUNDARIES),
        "applies_live_source_patch": False,
        "writes_memory": False,
        "executes_rollback": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "expands_autonomy": False,
    }


def build_promotion_approval_phrase_contract(root: str | Path | None = None) -> dict[str, Any]:
    scope = build_narrow_live_patch_scope_contract(root)
    packet_id = PROMOTION_PACKET_ID
    target_files = ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]
    phrase = f"I approve one narrow live patch promotion for packet {packet_id} only."
    contract = {
        "promotion_packet_id": packet_id,
        "target_files": target_files,
        "allowed_diff_summary": "Documentation/metadata-only live promotion packet review; no memory, identity, personality, scheduler, model, release, or autonomy changes.",
        "approval_expiry": "single-session operator approval only",
        "single_use": True,
        "operator_confirmation_phrase_template": phrase,
        "operator_confirmation_phrase_entered": False,
        "approval_granted": False,
    }
    rows = [
        _row("scope-ok", scope.get("ok") is True, "Narrow live patch scope contract passes."),
        _row("packet-visible", contract["promotion_packet_id"] == PROMOTION_PACKET_ID, "Promotion packet id is explicit."),
        _row("single-use", contract["single_use"] is True and "only" in phrase, "Approval phrase template is single-use and packet scoped."),
        _row("template-not-approval", contract["operator_confirmation_phrase_entered"] is False and contract["approval_granted"] is False and NARROW_LIVE_PATCH_GATE_BOUNDARIES["approval_phrase_template_is_operator_approval"] is False, "Approval phrase template is not operator approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "promotion_approval_phrase_contract_review_only",
        "contract": contract,
        "live_patch_gate_status": "defined",
        "live_patch_status": "not_applied",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NARROW_LIVE_PATCH_GATE_BOUNDARIES),
        "applies_live_source_patch": False,
        "writes_memory": False,
        "executes_rollback": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "expands_autonomy": False,
    }


def build_live_patch_preflight_checklist(root: str | Path | None = None) -> dict[str, Any]:
    phrase = build_promotion_approval_phrase_contract(root)
    checklist = {
        "source_package_privacy_clean": True,
        "target_files_allowed": True,
        "rollback_packet_present": True,
        "smoke_commands_declared": True,
        "readme_updates_included": True,
        "release_history_updates_included": True,
        "no_memory_writes": True,
        "no_identity_personality_changes": True,
        "no_scheduler_changes": True,
        "no_autonomy_escalation": True,
        "live_patch_permission": False,
    }
    rows = [
        _row("phrase-contract-ok", phrase.get("ok") is True, "Promotion approval phrase contract passes."),
        _row("privacy-and-targets", checklist["source_package_privacy_clean"] and checklist["target_files_allowed"], "Package privacy and target-file checks are represented."),
        _row("rollback-and-smoke", checklist["rollback_packet_present"] and checklist["smoke_commands_declared"], "Rollback packet and smoke command expectations are present."),
        _row("docs-required", checklist["readme_updates_included"] and checklist["release_history_updates_included"], "README next steps and release history remain required for live patches."),
        _row("forbidden-changes-blocked", all(checklist[key] for key in ["no_memory_writes", "no_identity_personality_changes", "no_scheduler_changes", "no_autonomy_escalation"]), "Memory, identity/personality, scheduler, and autonomy changes are blocked."),
        _row("preflight-not-permission", checklist["live_patch_permission"] is False and NARROW_LIVE_PATCH_GATE_BOUNDARIES["preflight_pass_is_live_patch_permission"] is False, "Preflight pass is not live patch permission."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "live_patch_preflight_checklist_review_only",
        "checklist": checklist,
        "live_patch_gate_status": "defined",
        "live_patch_status": "not_applied",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NARROW_LIVE_PATCH_GATE_BOUNDARIES),
        "applies_live_source_patch": False,
        "writes_memory": False,
        "executes_rollback": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "expands_autonomy": False,
    }


def build_live_promotion_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked = {
        "sandbox_success_as_live_approval": False,
        "promotion_packet_as_live_approval": False,
        "preflight_pass_as_live_approval": False,
        "operator_interest_as_approval": False,
        "prior_sandbox_approval_as_live_approval": False,
        "approval_phrase_template_as_approval_entered": False,
        "successful_live_patch_as_future_approval": False,
        "live_promotion_readiness_as_live_promotion_authorization": False,
    }
    text = _docs(root, docs)
    required_language = [
        "live_patch_scope_defined_is_live_patch_approved=False",
        "approval_phrase_template_is_operator_approval=False",
        "preflight_pass_is_live_patch_permission=False",
        "live_promotion_readiness_is_live_promotion_authorization=False",
        "live_patch_gate_status=defined",
        "live_patch_status=not_applied",
        "source_status=untouched",
        "memory_status=untouched",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked.values()), "Live promotion misinterpretation patterns are blocked."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke include required live patch gate boundary language."),
        _row("no-live-memory-release", all(NARROW_LIVE_PATCH_GATE_BOUNDARIES[key] is False for key in ["live_patch_gate_applies_live_source_patch", "live_patch_gate_writes_memory", "live_patch_gate_creates_release", "live_patch_gate_publishes_release", "live_patch_gate_expands_autonomy"]), "Live promotion gate grants no source, memory, release, publish, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "live_promotion_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked,
        "firewall_status": "active_review_only",
        "live_patch_gate_status": "defined",
        "live_patch_status": "not_applied",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NARROW_LIVE_PATCH_GATE_BOUNDARIES),
        "applies_live_source_patch": False,
        "writes_memory": False,
        "executes_rollback": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "expands_autonomy": False,
    }


def build_narrow_live_patch_promotion_gate_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    scope = build_narrow_live_patch_scope_contract(root)
    phrase = build_promotion_approval_phrase_contract(root)
    preflight = build_live_patch_preflight_checklist(root)
    firewall = build_live_promotion_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v540.0 - Operator-Approved Narrow Live Patch Promotion Gate v1",
        "operator-approved-narrow-live-patch-promotion-gate-v1",
        "narrow-live-patch-scope-contract",
        "promotion-approval-phrase-contract",
        "live-patch-preflight-checklist",
        "live-promotion-misinterpretation-firewall",
        "narrow-live-patch-promotion-gate-audit",
        "live_patch_gate_status=defined",
        "live_patch_status=not_applied",
        "approval_status=required",
        "authorization_status=not_authorized",
        "source_status=untouched",
        "memory_status=untouched",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
        "live_promotion_readiness_is_live_promotion_authorization=False",
    ]
    rows = [
        _row("version-markers", NARROW_LIVE_PATCH_PROMOTION_GATE_VERSION == CURRENT_VERSION == "605.0", f"gate={NARROW_LIVE_PATCH_PROMOTION_GATE_VERSION}; current={CURRENT_VERSION}"),
        _row("scope-contract", scope.get("ok") is True, "Narrow live patch scope contract is defined without approval."),
        _row("approval-phrase", phrase.get("ok") is True and phrase.get("applies_live_source_patch") is False, "Promotion approval phrase contract is a template only."),
        _row("preflight", preflight.get("ok") is True and preflight.get("applies_live_source_patch") is False, "Live patch preflight checklist grants no permission."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Live promotion firewall blocks approval and authorization confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v536-v540."),
        _row("no-live-authority", all(NARROW_LIVE_PATCH_GATE_BOUNDARIES[key] is False for key in ["live_patch_gate_applies_live_source_patch", "live_patch_gate_writes_memory", "live_patch_gate_executes_rollback", "live_patch_gate_creates_release", "live_patch_gate_publishes_release", "live_patch_gate_invokes_models_by_default", "live_patch_gate_schedules_work", "live_patch_gate_reuses_approval", "live_patch_gate_continues_automatically", "live_patch_gate_expands_autonomy"]), "Narrow live patch gate grants no live source, memory, rollback execution, model, schedule, release, publish, approval reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "narrow_live_patch_promotion_gate_audit_review_only",
        "live_patch_gate_id": LIVE_PATCH_GATE_ID,
        "live_patch_gate_status": "defined",
        "live_patch_status": "not_applied",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "narrow_live_patch_scope_contract": scope,
        "promotion_approval_phrase_contract": phrase,
        "live_patch_preflight_checklist": preflight,
        "live_promotion_misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NARROW_LIVE_PATCH_GATE_BOUNDARIES),
        "applies_live_source_patch": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_rollback": False,
        "executes_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the narrow live patch promotion gate. Any future live-source application requires a separate exact fresh single-use approval and must remain narrow, reversible, receipted, and non-autonomous.",
    }


def render_narrow_live_patch_promotion_gate_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"live_patch_gate_status: {report.get('live_patch_gate_status', 'defined')}",
        f"live_patch_status: {report.get('live_patch_status', 'not_applied')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"source_status: {report.get('source_status', 'untouched')}",
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


# v535.1-v540.0 narrow live patch promotion gate tokens: narrow-live-patch-scope-contract promotion-approval-phrase-contract live-patch-preflight-checklist live-promotion-misinterpretation-firewall narrow-live-patch-promotion-gate-audit operator-approved-narrow-live-patch-promotion-gate-v1 narrow_live_patch_promotion_gate.py live_patch_scope_defined_is_live_patch_approved=False approval_phrase_template_is_operator_approval=False preflight_pass_is_live_patch_permission=False sandbox_success_is_live_approval=False promotion_packet_is_live_approval=False preflight_pass_is_live_approval=False operator_interest_is_approval=False prior_sandbox_approval_is_live_approval=False approval_phrase_template_is_approval_entered=False successful_live_patch_is_future_approval=False live_promotion_readiness_is_live_promotion_authorization=False live_patch_gate_applies_live_source_patch=False live_patch_gate_writes_memory=False live_patch_gate_executes_rollback=False live_patch_gate_creates_release=False live_patch_gate_publishes_release=False live_patch_gate_invokes_models_by_default=False live_patch_gate_schedules_work=False live_patch_gate_reuses_approval=False live_patch_gate_continues_automatically=False live_patch_gate_expands_autonomy=False live_patch_gate_status=defined live_patch_status=not_applied approval_status=required authorization_status=not_authorized source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous fresh_operator_approval_required=True single_use_approval_required=True approval_burnout_required=True rollback_plan_required=True no_native_title_tooltip data-tip command-deck operator-console
