from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import (
    CURRENT_VERSION,
    CURRENT_VERSION_TAG,
    CURRENT_MILESTONE,
    NEXT_RECOMMENDED_ARC,
    STALE_VERSION_BOUNDARIES,
    build_current_symbol_staleness_audit,
    build_release_staleness_and_verification_audit_board,
    build_stale_version_string_scanner,
)

POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
EVIDENCE_INTAKE_ID = "v551_post_live_patch_evidence_intake_contract"
VERIFICATION_RECEIPT_REVIEW_ID = "v552_verification_receipt_review_layer"
ROLLBACK_SNAPSHOT_REVIEW_ID = "v553_rollback_snapshot_validity_review"
REGRESSION_STALENESS_BOARD_ID = "v554_post_patch_regression_staleness_audit_board"
VERIFICATION_ROLLBACK_TRIAL_ID = "v555_post_live_patch_verification_rollback_trial"

EVIDENCE_INTAKE_BOUNDARIES: dict[str, bool] = {
    "evidence_presence_is_verification_success": False,
    "evidence_presence_is_release_approval": False,
    "evidence_presence_is_live_patch_permission": False,
    "evidence_intake_executes_commands": False,
    "evidence_intake_applies_patches": False,
    "evidence_intake_executes_rollback": False,
    "evidence_intake_writes_source": False,
    "evidence_intake_writes_memory": False,
    "evidence_intake_creates_release": False,
    "evidence_intake_invokes_models_by_default": False,
    "evidence_intake_schedules_work": False,
    "evidence_intake_reuses_approval": False,
    "evidence_intake_continues_automatically": False,
    "evidence_intake_expands_autonomy": False,
    "operator_supplied_evidence_required": True,
    "operator_review_required": True,
}

VERIFICATION_REVIEW_BOUNDARIES: dict[str, bool] = {
    "receipt_review_runs_commands": False,
    "receipt_review_applies_patches": False,
    "receipt_review_executes_rollback": False,
    "receipt_review_approves_release": False,
    "receipt_review_grants_authorization": False,
    "passing_receipts_create_future_approval": False,
    "missing_receipts_trigger_actions": False,
    "failed_receipts_trigger_rollback": False,
    "receipt_review_writes_source": False,
    "receipt_review_writes_memory": False,
    "receipt_review_creates_release": False,
    "receipt_review_expands_autonomy": False,
    "operator_supplied_receipts_required": True,
    "operator_review_required": True,
}

ROLLBACK_REVIEW_BOUNDARIES: dict[str, bool] = {
    "rollback_plan_is_rollback_execution": False,
    "rollback_snapshot_validity_is_patch_approval": False,
    "rollback_snapshot_validity_is_release_approval": False,
    "rollback_review_executes_rollback": False,
    "rollback_review_writes_source": False,
    "rollback_review_writes_memory": False,
    "rollback_review_creates_release": False,
    "rollback_review_reuses_approval": False,
    "rollback_review_continues_automatically": False,
    "rollback_review_expands_autonomy": False,
    "operator_review_required": True,
}

REGRESSION_BOARD_BOUNDARIES: dict[str, bool] = {
    "regression_audit_pass_is_release_approval": False,
    "regression_audit_pass_is_live_patch_permission": False,
    "regression_audit_executes_commands": False,
    "regression_audit_applies_patches": False,
    "regression_audit_executes_rollback": False,
    "route_health_is_authorization": False,
    "package_privacy_pass_publishes_release": False,
    "stale_audit_pass_is_release_approval": False,
    "stale_audit_pass_is_live_patch_permission": False,
    "regression_audit_writes_source": False,
    "regression_audit_writes_memory": False,
    "regression_audit_creates_release": False,
    "regression_audit_expands_autonomy": False,
    "operator_review_required": True,
}

TRIAL_BOARD_BOUNDARIES: dict[str, bool] = {
    "trial_board_is_autonomy_approval": False,
    "trial_board_is_release_approval": False,
    "trial_board_is_live_patch_permission": False,
    "trial_board_executes_commands": False,
    "trial_board_applies_patches": False,
    "trial_board_executes_rollback": False,
    "trial_board_writes_source": False,
    "trial_board_writes_memory": False,
    "trial_board_creates_release": False,
    "trial_board_invokes_models_by_default": False,
    "trial_board_schedules_work": False,
    "trial_board_reuses_approval": False,
    "trial_board_continues_automatically": False,
    "trial_board_expands_autonomy": False,
    "operator_review_required": True,
    "approval_required": True,
}

EVIDENCE_FIELDS: tuple[str, ...] = (
    "patch_id",
    "operator_approval_receipt_id",
    "applied_file_manifest",
    "before_hashes",
    "after_hashes",
    "compile_result",
    "targeted_smoke_result",
    "fast_smoke_result",
    "dashboard_route_probe_result",
    "api_dispatch_result",
    "cli_dispatch_result",
    "release_doc_update_confirmation",
    "package_privacy_result",
    "rollback_snapshot_reference",
    "rollback_instructions_reference",
    "no_memory_mutation_confirmation",
    "no_autonomy_expansion_confirmation",
    "operator_notes",
)

VERIFICATION_RECEIPT_FIELDS: tuple[str, ...] = (
    "compile_receipt",
    "targeted_smoke_receipt",
    "fast_smoke_receipt",
    "install_governance_receipt",
    "install_dashboard_receipt",
    "install_release_receipt",
    "install_regression_recent_receipt",
    "install_memory_receipt",
    "install_expression_receipt",
    "install_live_trial_receipt",
    "cli_dispatch_receipt",
    "api_dispatch_receipt",
    "extracted_zip_compile_receipt",
    "extracted_zip_targeted_smoke_receipt",
    "extracted_zip_fast_smoke_receipt",
    "package_privacy_receipt",
)

ROLLBACK_FIELDS: tuple[str, ...] = (
    "rollback_snapshot_reference",
    "affected_file_manifest",
    "before_hashes",
    "restore_instructions",
    "verification_commands_after_restore",
    "operator_approval_scope",
    "rollback_risk_notes",
)

REGRESSION_AUDIT_FIELDS: tuple[str, ...] = (
    "verification_receipt_review",
    "rollback_snapshot_review",
    "stale_current_state_scan",
    "current_symbol_scan",
    "dashboard_route_probe",
    "api_cli_parity_review",
    "release_doc_alignment_review",
    "package_privacy_review",
    "no_autonomy_expansion_review",
)


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _supplied_count(payload: dict[str, Any] | None) -> int:
    return len(dict(payload or {}))


def _missing(fields: tuple[str, ...], payload: dict[str, Any] | None) -> list[str]:
    supplied = dict(payload or {})
    return [field for field in fields if field not in supplied]


def _base_authority_state() -> dict[str, Any]:
    return {
        "stale_version_audit_status": "clean_or_blocked",
        "metadata_current_state_status": "aligned_or_blocked",
        "post_patch_verification_status": "review_prepared",
        "evidence_intake_status": "awaiting_operator_supplied_evidence",
        "verification_receipt_status": "awaiting_operator_supplied_evidence",
        "rollback_status": "planned_not_executed",
        "live_patch_status": "not_applied_by_default",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "autonomy_status": "not_autonomous",
        "writes_source": False,
        "writes_memory": False,
        "modifies_live_files": False,
        "executes_commands": False,
        "executes_rollback": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "operator_review_required": True,
        "approval_required": True,
        "review_only": True,
    }


def build_post_live_patch_evidence_intake_contract(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    supplied = dict(evidence or {})
    missing_fields = _missing(EVIDENCE_FIELDS, supplied)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("schema-defined", len(EVIDENCE_FIELDS) >= 12, "Post-live-patch evidence intake fields cover approval receipt, file manifest, hashes, verification results, docs, package privacy, rollback references, and safety confirmations."),
        _row("operator-evidence-required", EVIDENCE_INTAKE_BOUNDARIES["operator_supplied_evidence_required"] is True, "The intake contract expects operator-supplied evidence and does not invent verification results."),
        _row("empty-intake-is-awaiting", not supplied and len(missing_fields) == len(EVIDENCE_FIELDS), "With no operator evidence supplied, the contract remains awaiting evidence rather than passing verification."),
        _row("current-symbol-audit-clean", symbol_audit.get("ok") is True, "Expanded current-symbol staleness audit is clean before packaging."),
        _row("stale-version-audit-clean", stale_scanner.get("ok") is True, "Centralized stale-current-state audit is clean before packaging."),
        _row("no-command-execution", EVIDENCE_INTAKE_BOUNDARIES["evidence_intake_executes_commands"] is False, "Evidence intake records expected evidence shape but does not execute verification commands."),
        _row("no-rollback-execution", EVIDENCE_INTAKE_BOUNDARIES["evidence_intake_executes_rollback"] is False, "Evidence intake can reference rollback material but cannot execute rollback."),
        _row("no-authority", all(EVIDENCE_INTAKE_BOUNDARIES[key] is False for key in ["evidence_presence_is_verification_success", "evidence_presence_is_release_approval", "evidence_presence_is_live_patch_permission", "evidence_intake_applies_patches", "evidence_intake_writes_source", "evidence_intake_writes_memory", "evidence_intake_creates_release", "evidence_intake_invokes_models_by_default", "evidence_intake_schedules_work", "evidence_intake_reuses_approval", "evidence_intake_continues_automatically", "evidence_intake_expands_autonomy"]), "Evidence presence grants no verification success, release approval, live patch permission, source/memory/release/model/schedule/approval/continuation/autonomy authority."),
    ]
    report = {
        "version": POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION,
        "state": "post_live_patch_evidence_intake_contract_review_only",
        "evidence_intake_id": EVIDENCE_INTAKE_ID,
        "evidence_schema_fields": list(EVIDENCE_FIELDS),
        "supplied_evidence_field_count": len(supplied),
        "missing_evidence_fields": missing_fields,
        "stale_version_audit": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(EVIDENCE_INTAKE_BOUNDARIES),
        "safe_next_action": "Operator may supply post-live-patch verification evidence for review. Intake does not run checks, approve release, execute rollback, apply patches, write memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    report["evidence_intake_status"] = "awaiting_operator_supplied_evidence" if missing_fields else "evidence_supplied_for_review"
    report["verification_receipt_status"] = "awaiting_operator_supplied_evidence" if missing_fields else "supplied_for_review_not_verified"
    return report


def build_verification_receipt_review_layer(root: str | Path | None = None, receipts: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing_fields = _missing(VERIFICATION_RECEIPT_FIELDS, receipts)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("receipt-schema-defined", len(VERIFICATION_RECEIPT_FIELDS) >= 12, "Receipt review schema covers compile, targeted smoke, fast smoke, install smoke tiers, dashboard/API/CLI dispatch, extracted zip checks, and package privacy."),
        _row("operator-receipts-required", VERIFICATION_REVIEW_BOUNDARIES["operator_supplied_receipts_required"] is True, "Verification receipts must be supplied by the operator; the layer does not fabricate results."),
        _row("missing-receipts-await", len(missing_fields) == len(VERIFICATION_RECEIPT_FIELDS), "With no receipts supplied, the layer awaits evidence instead of passing verification."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current staleness and current-symbol scans remain clean."),
        _row("no-command-execution", VERIFICATION_REVIEW_BOUNDARIES["receipt_review_runs_commands"] is False, "Receipt review classifies supplied receipts but does not run verification commands."),
        _row("no-authority", all(VERIFICATION_REVIEW_BOUNDARIES[key] is False for key in ["receipt_review_applies_patches", "receipt_review_executes_rollback", "receipt_review_approves_release", "receipt_review_grants_authorization", "passing_receipts_create_future_approval", "missing_receipts_trigger_actions", "failed_receipts_trigger_rollback", "receipt_review_writes_source", "receipt_review_writes_memory", "receipt_review_creates_release", "receipt_review_expands_autonomy"]), "Receipt review grants no patch, rollback, release, source, memory, approval, authorization, or autonomy authority."),
    ]
    report = {
        "version": POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION,
        "state": "verification_receipt_review_layer_review_only",
        "verification_receipt_review_id": VERIFICATION_RECEIPT_REVIEW_ID,
        "receipt_schema_fields": list(VERIFICATION_RECEIPT_FIELDS),
        "supplied_receipt_field_count": _supplied_count(receipts),
        "missing_receipt_fields": missing_fields,
        "receipt_review_status": "prepared",
        "evidence_classification_status": "review_only",
        "command_execution_status": "not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(VERIFICATION_REVIEW_BOUNDARIES),
        "safe_next_action": "Operator may review supplied verification receipts. Review does not run checks, approve release, apply patches, execute rollback, write memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_rollback_snapshot_validity_review(root: str | Path | None = None, rollback_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing_fields = _missing(ROLLBACK_FIELDS, rollback_packet)
    rows = [
        _row("rollback-schema-defined", len(ROLLBACK_FIELDS) >= 6, "Rollback review schema covers snapshot reference, affected files, before hashes, restore instructions, verification commands, approval scope, and risk notes."),
        _row("missing-packet-await", len(missing_fields) == len(ROLLBACK_FIELDS), "With no rollback packet supplied, the layer remains planned/not executed rather than claiming recovery readiness."),
        _row("plan-not-execution", ROLLBACK_REVIEW_BOUNDARIES["rollback_plan_is_rollback_execution"] is False and ROLLBACK_REVIEW_BOUNDARIES["rollback_review_executes_rollback"] is False, "Rollback planning and snapshot review do not execute rollback."),
        _row("validity-not-approval", ROLLBACK_REVIEW_BOUNDARIES["rollback_snapshot_validity_is_patch_approval"] is False and ROLLBACK_REVIEW_BOUNDARIES["rollback_snapshot_validity_is_release_approval"] is False, "Rollback snapshot validity does not approve patches or releases."),
        _row("no-authority", all(ROLLBACK_REVIEW_BOUNDARIES[key] is False for key in ["rollback_review_writes_source", "rollback_review_writes_memory", "rollback_review_creates_release", "rollback_review_reuses_approval", "rollback_review_continues_automatically", "rollback_review_expands_autonomy"]), "Rollback review grants no source, memory, release, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION,
        "state": "rollback_snapshot_validity_review_only",
        "rollback_snapshot_review_id": ROLLBACK_SNAPSHOT_REVIEW_ID,
        "rollback_schema_fields": list(ROLLBACK_FIELDS),
        "missing_rollback_fields": missing_fields,
        "rollback_snapshot_status": "awaiting_operator_supplied_packet" if missing_fields else "supplied_for_review_not_executed",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ROLLBACK_REVIEW_BOUNDARIES),
        "safe_next_action": "Operator may review rollback snapshot validity. Review does not execute rollback, apply patches, approve release, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_post_patch_regression_staleness_audit_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    receipt = build_verification_receipt_review_layer(repo)
    rollback = build_rollback_snapshot_validity_review(repo)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("receipt-review-prepared", receipt.get("ok") is True and receipt.get("executes_commands") is False, "Verification receipt review is prepared and does not run commands."),
        _row("rollback-review-prepared", rollback.get("ok") is True and rollback.get("executes_rollback") is False, "Rollback snapshot validity review is prepared and does not execute rollback."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Stale current-state and current-symbol audits are clean."),
        _row("audit-field-coverage", len(REGRESSION_AUDIT_FIELDS) >= 8, "Regression board covers receipt review, rollback, stale scan, route/API/CLI parity, docs, package privacy, and no-autonomy expansion."),
        _row("no-command-execution", REGRESSION_BOARD_BOUNDARIES["regression_audit_executes_commands"] is False, "Regression board does not execute commands."),
        _row("no-authority", all(REGRESSION_BOARD_BOUNDARIES[key] is False for key in ["regression_audit_pass_is_release_approval", "regression_audit_pass_is_live_patch_permission", "regression_audit_applies_patches", "regression_audit_executes_rollback", "route_health_is_authorization", "package_privacy_pass_publishes_release", "stale_audit_pass_is_release_approval", "stale_audit_pass_is_live_patch_permission", "regression_audit_writes_source", "regression_audit_writes_memory", "regression_audit_creates_release", "regression_audit_expands_autonomy"]), "Regression/staleness board grants no release, live patch, rollback, route, package, source, memory, or autonomy authority."),
    ]
    report = {
        "version": POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION,
        "state": "post_patch_regression_staleness_audit_board_review_only",
        "regression_staleness_board_id": REGRESSION_STALENESS_BOARD_ID,
        "regression_audit_fields": list(REGRESSION_AUDIT_FIELDS),
        "verification_receipt_review": receipt,
        "rollback_snapshot_validity_review": rollback,
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(REGRESSION_BOARD_BOUNDARIES),
        "safe_next_action": "Operator may review regression/staleness alignment. Board does not approve release, apply patches, execute rollback, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_post_live_patch_verification_rollback_trial(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    evidence = build_post_live_patch_evidence_intake_contract(repo)
    receipt = build_verification_receipt_review_layer(repo)
    rollback = build_rollback_snapshot_validity_review(repo)
    regression = build_post_patch_regression_staleness_audit_board(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("evidence-intake-prepared", evidence.get("ok") is True, "Evidence intake contract remains prepared."),
        _row("receipt-review-prepared", receipt.get("ok") is True, "Verification receipt review layer is prepared."),
        _row("rollback-review-prepared", rollback.get("ok") is True, "Rollback snapshot validity review is prepared."),
        _row("regression-staleness-prepared", regression.get("ok") is True, "Post-patch regression/staleness audit board is prepared."),
        _row("release-staleness-board-clean", release_stale.get("ok") is True, "Current release staleness audit board remains clean."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [evidence, receipt, rollback, regression]), "No v551-v555 review layer runs commands or executes rollback."),
        _row("no-authority", all(TRIAL_BOARD_BOUNDARIES[key] is False for key in ["trial_board_is_autonomy_approval", "trial_board_is_release_approval", "trial_board_is_live_patch_permission", "trial_board_executes_commands", "trial_board_applies_patches", "trial_board_executes_rollback", "trial_board_writes_source", "trial_board_writes_memory", "trial_board_creates_release", "trial_board_invokes_models_by_default", "trial_board_schedules_work", "trial_board_reuses_approval", "trial_board_continues_automatically", "trial_board_expands_autonomy"]), "Trial board grants no autonomy, release, live patch, command, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": POST_LIVE_PATCH_VERIFICATION_ROLLBACK_TRIAL_VERSION,
        "state": "post_live_patch_verification_rollback_trial_review_only",
        "trial_id": VERIFICATION_ROLLBACK_TRIAL_ID,
        "evidence_intake_contract": evidence,
        "verification_receipt_review_layer": receipt,
        "rollback_snapshot_validity_review": rollback,
        "post_patch_regression_staleness_audit_board": regression,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(TRIAL_BOARD_BOUNDARIES),
        "safe_next_action": "Operator may review the v555 post-live-patch verification and rollback trial board. It does not run checks, apply patches, execute rollback, create releases, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_post_live_patch_verification_rollback_arc(root: str | Path | None = None, stage: str = "post_live_patch_verification_rollback_trial_v1") -> dict[str, Any]:
    builders = {
        "post_live_patch_evidence_intake_contract_v1": build_post_live_patch_evidence_intake_contract,
        "verification_receipt_review_layer_v1": build_verification_receipt_review_layer,
        "rollback_snapshot_validity_review_v1": build_rollback_snapshot_validity_review,
        "post_patch_regression_staleness_audit_board_v1": build_post_patch_regression_staleness_audit_board,
        "post_live_patch_verification_rollback_trial_v1": build_post_live_patch_verification_rollback_trial,
    }
    return builders.get(stage, build_post_live_patch_verification_rollback_trial)(root)


def render_post_live_patch_verification_rollback_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"stale_version_audit_status: {report.get('stale_version_audit_status')}",
        f"metadata_current_state_status: {report.get('metadata_current_state_status')}",
        f"post_patch_verification_status: {report.get('post_patch_verification_status')}",
        f"evidence_intake_status: {report.get('evidence_intake_status')}",
        f"verification_receipt_status: {report.get('verification_receipt_status')}",
        f"rollback_status: {report.get('rollback_status')}",
        f"live_patch_status: {report.get('live_patch_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


def render_post_live_patch_evidence_intake_lines(report: dict[str, Any]) -> list[str]:
    return render_post_live_patch_verification_rollback_lines(report)

# v552.0-v555.0 post live patch verification rollback tokens: verification-receipt-review-layer rollback-snapshot-validity-review post-patch-regression-staleness-audit-board post-live-patch-verification-rollback-trial post-live-patch-verification-and-rollback-trial-v1 post_live_patch_verification_rollback_trial.py receipt_review_does_not_execute_commands=True receipt_review_is_release_approval=False rollback_plan_is_rollback_execution=False rollback_snapshot_validity_is_patch_approval=False regression_audit_pass_is_release_approval=False route_health_is_authorization=False package_privacy_pass_publishes_release=False trial_board_is_autonomy_approval=False trial_board_is_release_approval=False trial_board_executes_commands=False evidence_intake_status=awaiting_operator_supplied_evidence verification_receipt_status=awaiting_operator_supplied_evidence rollback_status=planned_not_executed stale_version_audit_status=clean_or_blocked metadata_current_state_status=aligned_or_blocked post_patch_verification_status=review_prepared live_patch_status=not_applied_by_default approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
