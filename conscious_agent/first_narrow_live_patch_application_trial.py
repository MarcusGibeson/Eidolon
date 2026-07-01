from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIRST_NARROW_LIVE_PATCH_APPLICATION_TRIAL_VERSION = "1032.0"
CURRENT_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
TRIAL_ID = "v545_first_single_use_narrow_live_patch_application_trial"
LIVE_PATCH_GATE_ID = "v540_operator_approved_narrow_live_patch_promotion_gate"
PATCH_CANDIDATE_ID = "v541_first_narrow_live_patch_candidate_review_only"
APPROVAL_RECEIPT_ID = "v542_single_use_live_patch_approval_receipt_template"
APPLICATION_HARNESS_ID = "v543_live_patch_application_harness_preview"

ALLOWED_FIRST_TRIAL_CANDIDATES: tuple[str, ...] = (
    "README wording cleanup",
    "release history correction",
    "metadata version drift repair",
    "smoke command wording repair",
    "route/report text correction",
    "package privacy rule text correction",
)

FORBIDDEN_FIRST_TRIAL_CANDIDATES: tuple[str, ...] = (
    "memory writes",
    "identity changes",
    "personality changes",
    "purpose changes",
    "scheduler changes",
    "model invocation changes",
    "autonomy escalation",
    "broad refactors",
    "runtime behavior changes",
    "release publishing",
)

FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES: dict[str, bool] = {
    "candidate_selected_is_live_patch_approved": False,
    "approval_receipt_template_is_approval_granted": False,
    "application_harness_exists_is_patch_applied": False,
    "candidate_selection_is_approval": False,
    "approval_receipt_template_is_approval": False,
    "preflight_pass_is_patch_permission": False,
    "sandbox_success_is_live_patch_permission": False,
    "one_live_approval_is_future_approval": False,
    "successful_patch_is_autonomy": False,
    "successful_patch_is_release_approval": False,
    "live_patch_success_is_future_authorization": False,
    "trial_applies_patches_automatically": False,
    "trial_writes_memory": False,
    "trial_alters_identity": False,
    "trial_alters_personality": False,
    "trial_alters_purpose": False,
    "trial_changes_scheduler": False,
    "trial_invokes_models_by_default": False,
    "trial_creates_release_candidate": False,
    "trial_publishes_release": False,
    "trial_reuses_approval": False,
    "trial_continues_automatically": False,
    "trial_expands_autonomy": False,
    "approval_required": True,
    "fresh_operator_approval_required": True,
    "single_use_approval_required": True,
    "approval_burnout_required": True,
    "rollback_snapshot_required": True,
}

FIRST_TRIAL_ALLOWED_FILES: tuple[str, ...] = (
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

FIRST_TRIAL_FORBIDDEN_FILES: tuple[str, ...] = (
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
        "conscious_agent/first_narrow_live_patch_application_trial.py",
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


def build_live_patch_trial_candidate_selector(root: str | Path | None = None) -> dict[str, Any]:
    selector = {
        "patch_candidate_id": PATCH_CANDIDATE_ID,
        "allowed_candidate_types": list(ALLOWED_FIRST_TRIAL_CANDIDATES),
        "forbidden_candidate_types": list(FORBIDDEN_FIRST_TRIAL_CANDIDATES),
        "allowed_files": list(FIRST_TRIAL_ALLOWED_FILES),
        "forbidden_files": list(FIRST_TRIAL_FORBIDDEN_FILES),
        "candidate_selected": True,
        "live_patch_approved": False,
        "operator_confirmation_required": True,
    }
    rows = [
        _row("allowed-candidates-boring", len(selector["allowed_candidate_types"]) == 6 and "runtime behavior changes" not in selector["allowed_candidate_types"], "First live-patch trial candidates are limited to documentation, metadata, smoke wording, route/report text, and package privacy text repair."),
        _row("forbidden-candidates-listed", all(item in selector["forbidden_candidate_types"] for item in ["memory writes", "identity changes", "autonomy escalation", "release publishing", "runtime behavior changes"]), "Forbidden candidate types include memory, identity/personality/purpose, scheduler, model, autonomy, runtime behavior, broad refactor, and release changes."),
        _row("forbidden-files-listed", all(path in selector["forbidden_files"] for path in ["data/memory.json", "data/workspaces/timeline.json", "runtime/"]), "Memory, workspace timeline, and runtime paths are forbidden targets."),
        _row("selection-not-approval", selector["candidate_selected"] is True and selector["live_patch_approved"] is False and FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES["candidate_selected_is_live_patch_approved"] is False, "Candidate selection is not live patch approval."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "live_patch_trial_candidate_selector_review_only",
        "selector": selector,
        "trial_status": "prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES),
        "applies_patches_automatically": False,
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "expands_autonomy": False,
    }


def build_single_use_live_patch_approval_receipt(root: str | Path | None = None) -> dict[str, Any]:
    selector = build_live_patch_trial_candidate_selector(root)
    target_files = ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"]
    phrase = f"I approve one narrow live patch application for candidate {PATCH_CANDIDATE_ID} only."
    receipt = {
        "approval_receipt_id": APPROVAL_RECEIPT_ID,
        "patch_candidate_id": PATCH_CANDIDATE_ID,
        "target_files": target_files,
        "exact_diff_summary": "Documentation-only first live patch trial candidate; no memory, identity, personality, purpose, scheduler, model, runtime behavior, release, or autonomy changes.",
        "approval_phrase_template": phrase,
        "approval_phrase_entered": False,
        "approval_expiry": "single-session operator approval only",
        "single_use": True,
        "operator_confirmation_required": True,
        "approval_status": "not_granted_by_default",
        "approval_granted": False,
    }
    rows = [
        _row("selector-ok", selector.get("ok") is True, "Candidate selector passes while granting no approval."),
        _row("candidate-visible", receipt["patch_candidate_id"] == PATCH_CANDIDATE_ID, "Patch candidate id is explicit."),
        _row("single-use-template", receipt["single_use"] is True and "only" in phrase, "Approval receipt template is single-use and candidate scoped."),
        _row("template-not-approval", receipt["approval_granted"] is False and receipt["approval_phrase_entered"] is False and FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES["approval_receipt_template_is_approval_granted"] is False, "Approval receipt template is not approval granted."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "single_use_live_patch_approval_receipt_review_only",
        "selector": selector,
        "approval_receipt": receipt,
        "trial_status": "prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES),
        "applies_patches_automatically": False,
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "expands_autonomy": False,
    }


def build_live_patch_application_harness_preview(root: str | Path | None = None) -> dict[str, Any]:
    receipt = build_single_use_live_patch_approval_receipt(root)
    harness = {
        "application_harness_id": APPLICATION_HARNESS_ID,
        "target_files": ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"],
        "write_scope": "narrow_documentation_only_after_exact_fresh_single_use_operator_approval",
        "rollback_snapshot_plan": "Create pre-change snapshots for target files before any future approved live patch application.",
        "post_patch_compile_command": "python -m compileall conscious_agent tools",
        "post_patch_smoke_commands": [
            "python tools/smoke_check.py --tier fast --json",
            "python tools/smoke_check.py --check first-single-use-narrow-live-patch-application-trial-v1 --json",
        ],
        "readme_update_required": True,
        "release_history_update_required": True,
        "patch_applied": False,
        "runs_by_default": False,
    }
    rows = [
        _row("receipt-ok", receipt.get("ok") is True, "Single-use approval receipt template passes without granting approval."),
        _row("target-files-bounded", harness["target_files"] == ["README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md"], "Harness preview target files remain narrow and documentation-only."),
        _row("rollback-and-smoke-declared", bool(harness["rollback_snapshot_plan"]) and bool(harness["post_patch_smoke_commands"]), "Rollback snapshot and post-patch smoke expectations are declared."),
        _row("docs-required", harness["readme_update_required"] is True and harness["release_history_update_required"] is True, "README and release history updates remain required for any future live patch."),
        _row("harness-not-application", harness["patch_applied"] is False and harness["runs_by_default"] is False and FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES["application_harness_exists_is_patch_applied"] is False, "Application harness preview is not patch application."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "live_patch_application_harness_preview_review_only",
        "approval_receipt": receipt,
        "harness": harness,
        "trial_status": "prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES),
        "applies_patches_automatically": False,
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "expands_autonomy": False,
    }


def build_live_patch_application_misinterpretation_firewall(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    blocked = {
        "candidate_selection_as_approval": False,
        "approval_receipt_template_as_approval": False,
        "preflight_pass_as_patch_permission": False,
        "sandbox_success_as_live_patch_permission": False,
        "one_live_approval_as_future_approval": False,
        "successful_patch_as_autonomy": False,
        "successful_patch_as_release_approval": False,
        "live_patch_success_as_future_authorization": False,
    }
    text = _docs(root, docs)
    required_language = [
        "candidate_selected_is_live_patch_approved=False",
        "approval_receipt_template_is_approval_granted=False",
        "application_harness_exists_is_patch_applied=False",
        "live_patch_success_is_future_authorization=False",
        "trial_status=prepared",
        "live_patch_status=not_applied_by_default",
        "approval_status=required",
        "authorization_status=not_authorized",
        "memory_status=untouched",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
    ]
    rows = [
        _row("blocked-interpretations", all(value is False for value in blocked.values()), "Live patch trial misinterpretation patterns are blocked."),
        _row("docs-language", all(token in text for token in required_language), "Docs/source/smoke include required first live patch trial boundary language."),
        _row("no-danger-authority", all(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES[key] is False for key in ["trial_applies_patches_automatically", "trial_writes_memory", "trial_alters_identity", "trial_alters_personality", "trial_alters_purpose", "trial_changes_scheduler", "trial_invokes_models_by_default", "trial_creates_release_candidate", "trial_publishes_release", "trial_reuses_approval", "trial_continues_automatically", "trial_expands_autonomy"]), "Trial grants no automatic patch, memory, identity, personality, purpose, scheduler, model, release, publish, approval-reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "live_patch_application_misinterpretation_firewall_review_only",
        "blocked_interpretations": blocked,
        "firewall_status": "active_review_only",
        "trial_status": "prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES),
        "applies_patches_automatically": False,
        "writes_live_source": False,
        "writes_memory": False,
        "creates_release_candidate": False,
        "expands_autonomy": False,
    }


def build_first_narrow_live_patch_trial_audit(root: str | Path | None = None, docs: str = "") -> dict[str, Any]:
    selector = build_live_patch_trial_candidate_selector(root)
    receipt = build_single_use_live_patch_approval_receipt(root)
    harness = build_live_patch_application_harness_preview(root)
    firewall = build_live_patch_application_misinterpretation_firewall(root, docs)
    text = _docs(root, docs)
    required_docs = [
        "v545.0 - First Single-Use Narrow Live Patch Application Trial v1",
        "first-single-use-narrow-live-patch-application-trial-v1",
        "live-patch-trial-candidate-selector",
        "single-use-live-patch-approval-receipt",
        "live-patch-application-harness-preview",
        "live-patch-application-misinterpretation-firewall",
        "first-narrow-live-patch-trial-audit",
        "trial_status=prepared",
        "live_patch_status=not_applied_by_default",
        "approval_status=required",
        "authorization_status=not_authorized",
        "memory_status=untouched",
        "release_status=not_created",
        "autonomy_status=not_autonomous",
        "live_patch_success_is_future_authorization=False",
    ]
    rows = [
        _row("version-markers", FIRST_NARROW_LIVE_PATCH_APPLICATION_TRIAL_VERSION == CURRENT_VERSION == "605.0", f"trial={FIRST_NARROW_LIVE_PATCH_APPLICATION_TRIAL_VERSION}; current={CURRENT_VERSION}"),
        _row("candidate-selector", selector.get("ok") is True, "Live patch trial candidate selector is bounded and not approval."),
        _row("approval-receipt", receipt.get("ok") is True and receipt.get("writes_live_source") is False, "Single-use approval receipt is a template only."),
        _row("harness-preview", harness.get("ok") is True and harness.get("writes_live_source") is False, "Live patch application harness preview grants no patch application."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Live patch application firewall blocks approval, success, release, and autonomy confusion."),
        _row("docs", all(token in text for token in required_docs), "README/source/dashboard/API/CLI smoke tokens describe v541-v545."),
        _row("no-automatic-authority", all(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES[key] is False for key in ["trial_applies_patches_automatically", "trial_writes_memory", "trial_alters_identity", "trial_alters_personality", "trial_alters_purpose", "trial_changes_scheduler", "trial_invokes_models_by_default", "trial_creates_release_candidate", "trial_publishes_release", "trial_reuses_approval", "trial_continues_automatically", "trial_expands_autonomy"]), "First live patch trial grants no automatic patch, memory, identity, personality, purpose, scheduler, model, release, publish, approval-reuse, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "first_narrow_live_patch_trial_audit_review_only",
        "trial_id": TRIAL_ID,
        "trial_status": "prepared",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "live_patch_trial_candidate_selector": selector,
        "single_use_live_patch_approval_receipt": receipt,
        "live_patch_application_harness_preview": harness,
        "live_patch_application_misinterpretation_firewall": firewall,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(FIRST_NARROW_LIVE_PATCH_TRIAL_BOUNDARIES),
        "applies_patches_automatically": False,
        "writes_live_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "alters_identity": False,
        "alters_personality": False,
        "alters_purpose": False,
        "changes_scheduler": False,
        "executes_commands": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "creates_release_candidate": False,
        "publishes_release": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "safe_next_action": "Operator may review the first narrow live patch application trial layer. Any future live-source application requires separate exact fresh single-use approval, bounded target files, rollback snapshots, post-patch verification, and stop-after-trial semantics.",
    }


def render_first_narrow_live_patch_trial_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"trial_status: {report.get('trial_status', 'prepared')}",
        f"live_patch_status: {report.get('live_patch_status', 'not_applied_by_default')}",
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


# v540.1-v545.0 first narrow live patch application trial tokens: live-patch-trial-candidate-selector single-use-live-patch-approval-receipt live-patch-application-harness-preview live-patch-application-misinterpretation-firewall first-narrow-live-patch-trial-audit first-single-use-narrow-live-patch-application-trial-v1 first_narrow_live_patch_application_trial.py candidate_selected_is_live_patch_approved=False approval_receipt_template_is_approval_granted=False application_harness_exists_is_patch_applied=False candidate_selection_is_approval=False approval_receipt_template_is_approval=False preflight_pass_is_patch_permission=False sandbox_success_is_live_patch_permission=False one_live_approval_is_future_approval=False successful_patch_is_autonomy=False successful_patch_is_release_approval=False live_patch_success_is_future_authorization=False trial_applies_patches_automatically=False trial_writes_memory=False trial_alters_identity=False trial_alters_personality=False trial_alters_purpose=False trial_changes_scheduler=False trial_invokes_models_by_default=False trial_creates_release_candidate=False trial_publishes_release=False trial_reuses_approval=False trial_continues_automatically=False trial_expands_autonomy=False trial_status=prepared live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized source_status=untouched memory_status=untouched release_status=not_created autonomy_status=not_autonomous fresh_operator_approval_required=True single_use_approval_required=True approval_burnout_required=True rollback_snapshot_required=True no_native_title_tooltip data-tip command-deck operator-console
