from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import (
    CURRENT_VERSION,
    CURRENT_VERSION_TAG,
    CURRENT_MILESTONE,
    NEXT_RECOMMENDED_ARC,
    build_current_symbol_staleness_audit,
    build_release_staleness_and_verification_audit_board,
    build_stale_version_string_scanner,
)
from post_live_patch_verification_rollback_trial import build_post_live_patch_verification_rollback_trial

RECOVERY_DRILL_RELEASE_CLOSURE_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
RECOVERY_DRILL_SCOPE_ID = "v556_recovery_drill_scope_contract"
ROLLBACK_DECISION_ID = "v557_rollback_decision_review_packet"
RELEASE_CLOSURE_EVIDENCE_ID = "v558_release_closure_evidence_board"
OPERATOR_CLOSURE_GATE_ID = "v559_operator_closure_approval_gate"
RECOVERY_RELEASE_CLOSURE_BOARD_ID = "v560_recovery_drill_release_closure_board"

RECOVERY_DRILL_SCOPE_FIELDS: tuple[str, ...] = (
    "drill_id",
    "live_patch_reference",
    "operator_supplied_verification_receipts",
    "affected_file_expectations",
    "rollback_snapshot_reference",
    "rollback_readiness_checklist",
    "release_closure_prerequisites",
    "known_blockers",
    "operator_notes",
)

ROLLBACK_DECISION_FIELDS: tuple[str, ...] = (
    "verification_receipt_review",
    "failure_or_warning_summary",
    "affected_file_manifest",
    "rollback_snapshot_validity",
    "restore_risk_notes",
    "operator_decision_required",
)

RELEASE_CLOSURE_FIELDS: tuple[str, ...] = (
    "source_version_alignment",
    "readme_current_state_alignment",
    "release_history_top_entry",
    "dashboard_api_cli_parity",
    "smoke_results",
    "package_privacy_scan",
    "extracted_zip_verification",
    "no_autonomy_no_authority_confirmation",
)

CLOSURE_APPROVAL_FIELDS: tuple[str, ...] = (
    "exact_operator_closure_phrase",
    "current_version_confirmation",
    "evidence_packet_reference",
    "single_use_scope",
    "approval_burnout_confirmation",
)

RECOVERY_DRILL_BOUNDARIES: dict[str, bool] = {
    "recovery_drill_scope_is_rollback_permission": False,
    "recovery_drill_readiness_is_execution_approval": False,
    "recovery_drill_planning_mutates_source": False,
    "recovery_drill_executes_commands": False,
    "recovery_drill_executes_rollback": False,
    "recovery_drill_creates_release": False,
    "recovery_drill_writes_memory": False,
    "recovery_drill_expands_autonomy": False,
    "operator_review_required": True,
}

ROLLBACK_DECISION_BOUNDARIES: dict[str, bool] = {
    "rollback_recommendation_is_rollback_execution": False,
    "rollback_eligibility_is_rollback_authorization": False,
    "rollback_decision_review_executes_rollback": False,
    "rollback_decision_review_applies_patches": False,
    "rollback_decision_review_writes_source": False,
    "rollback_decision_review_creates_release": False,
    "rollback_decision_review_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_CLOSURE_BOUNDARIES: dict[str, bool] = {
    "release_closure_review_is_release_approval": False,
    "closure_evidence_is_publish_permission": False,
    "release_closure_board_creates_release": False,
    "release_closure_board_publishes_release": False,
    "release_closure_board_applies_patches": False,
    "release_closure_board_executes_rollback": False,
    "release_closure_board_expands_autonomy": False,
    "operator_review_required": True,
}

CLOSURE_APPROVAL_BOUNDARIES: dict[str, bool] = {
    "closure_approval_is_single_use": True,
    "closure_approval_authorizes_future_patches": False,
    "closure_approval_authorizes_future_releases": False,
    "closure_approval_authorizes_autonomy": False,
    "closure_gate_infers_approval_from_receipts": False,
    "closure_gate_reuses_prior_approval": False,
    "closure_gate_creates_release": False,
    "closure_gate_executes_commands": False,
    "fresh_operator_phrase_required": True,
}

RECOVERY_RELEASE_CLOSURE_BOUNDARIES: dict[str, bool] = {
    "recovery_board_is_rollback_permission": False,
    "recovery_board_is_release_approval": False,
    "recovery_board_executes_commands": False,
    "recovery_board_executes_rollback": False,
    "recovery_board_applies_patches": False,
    "recovery_board_creates_release": False,
    "recovery_board_publishes_release": False,
    "recovery_board_writes_source": False,
    "recovery_board_writes_memory": False,
    "recovery_board_invokes_models_by_default": False,
    "recovery_board_schedules_work": False,
    "recovery_board_reuses_approval": False,
    "recovery_board_continues_automatically": False,
    "recovery_board_expands_autonomy": False,
    "operator_review_required": True,
    "approval_required": True,
}


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


def _missing(fields: tuple[str, ...], payload: dict[str, Any] | None) -> list[str]:
    supplied = dict(payload or {})
    return [field for field in fields if field not in supplied]


def _base_authority_state() -> dict[str, Any]:
    return {
        "recovery_drill_status": "prepared_not_executed",
        "rollback_decision_status": "review_prepared",
        "release_closure_status": "evidence_prepared",
        "closure_approval_status": "required",
        "post_patch_verification_status": "review_prepared",
        "verification_receipt_status": "awaiting_operator_supplied_evidence",
        "live_patch_status": "not_applied_by_default",
        "rollback_status": "not_executed",
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


def build_recovery_drill_scope_contract(root: str | Path | None = None, drill_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(RECOVERY_DRILL_SCOPE_FIELDS, drill_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    previous_trial = build_post_live_patch_verification_rollback_trial(repo)
    rows = [
        _row("scope-schema-defined", len(RECOVERY_DRILL_SCOPE_FIELDS) >= 8, "Recovery drill scope covers patch reference, receipts, affected files, rollback snapshot, readiness checklist, closure prerequisites, blockers, and operator notes."),
        _row("missing-scope-awaits", len(missing) == len(RECOVERY_DRILL_SCOPE_FIELDS), "With no operator drill packet supplied, the layer remains prepared/not executed rather than claiming drill completion."),
        _row("previous-trial-available", previous_trial.get("ok") is True, "v555 post-live-patch verification and rollback trial board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits are clean before packaging."),
        _row("no-execution", RECOVERY_DRILL_BOUNDARIES["recovery_drill_executes_commands"] is False and RECOVERY_DRILL_BOUNDARIES["recovery_drill_executes_rollback"] is False, "Recovery drill scope preparation does not run commands or execute rollback."),
        _row("no-authority", all(RECOVERY_DRILL_BOUNDARIES[key] is False for key in ["recovery_drill_scope_is_rollback_permission", "recovery_drill_readiness_is_execution_approval", "recovery_drill_planning_mutates_source", "recovery_drill_creates_release", "recovery_drill_writes_memory", "recovery_drill_expands_autonomy"]), "Recovery drill scope grants no rollback, execution, source, release, memory, or autonomy authority."),
    ]
    report = {
        "version": RECOVERY_DRILL_RELEASE_CLOSURE_VERSION,
        "state": "recovery_drill_scope_contract_review_only",
        "recovery_drill_scope_id": RECOVERY_DRILL_SCOPE_ID,
        "scope_fields": list(RECOVERY_DRILL_SCOPE_FIELDS),
        "missing_scope_fields": missing,
        "previous_trial_summary": {"ok": previous_trial.get("ok"), "state": previous_trial.get("state")},
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RECOVERY_DRILL_BOUNDARIES),
        "safe_next_action": "Operator may review recovery drill scope. The layer does not run commands, execute rollback, apply patches, create releases, write memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_rollback_decision_review_packet(root: str | Path | None = None, decision_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(ROLLBACK_DECISION_FIELDS, decision_packet)
    rows = [
        _row("decision-schema-defined", len(ROLLBACK_DECISION_FIELDS) >= 6, "Rollback decision review covers receipt review, warning/failure summary, affected files, snapshot validity, restore risk notes, and operator decision requirement."),
        _row("missing-decision-awaits", len(missing) == len(ROLLBACK_DECISION_FIELDS), "With no decision packet supplied, the layer prepares review categories without recommending execution."),
        _row("recommendation-not-execution", ROLLBACK_DECISION_BOUNDARIES["rollback_recommendation_is_rollback_execution"] is False and ROLLBACK_DECISION_BOUNDARIES["rollback_decision_review_executes_rollback"] is False, "Rollback recommendation is not rollback execution."),
        _row("eligibility-not-authorization", ROLLBACK_DECISION_BOUNDARIES["rollback_eligibility_is_rollback_authorization"] is False, "Rollback eligibility remains separate from operator authorization."),
        _row("no-authority", all(ROLLBACK_DECISION_BOUNDARIES[key] is False for key in ["rollback_decision_review_applies_patches", "rollback_decision_review_writes_source", "rollback_decision_review_creates_release", "rollback_decision_review_expands_autonomy"]), "Rollback decision review grants no patch, source, release, or autonomy authority."),
    ]
    report = {
        "version": RECOVERY_DRILL_RELEASE_CLOSURE_VERSION,
        "state": "rollback_decision_review_packet_review_only",
        "rollback_decision_id": ROLLBACK_DECISION_ID,
        "decision_fields": list(ROLLBACK_DECISION_FIELDS),
        "decision_categories": ["rollback_not_needed", "rollback_should_be_considered", "rollback_blocked_by_missing_evidence", "rollback_unsafe_incomplete_snapshot", "operator_review_required"],
        "missing_decision_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ROLLBACK_DECISION_BOUNDARIES),
        "safe_next_action": "Operator may review rollback decision categories. Review does not execute rollback, apply patches, create releases, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_closure_evidence_board(root: str | Path | None = None, closure_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(RELEASE_CLOSURE_FIELDS, closure_evidence)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("closure-schema-defined", len(RELEASE_CLOSURE_FIELDS) >= 8, "Release closure evidence covers source version, README, release history, dashboard/API/CLI parity, smoke results, package privacy, extracted zip verification, and no-authority confirmations."),
        _row("missing-evidence-awaits", len(missing) == len(RELEASE_CLOSURE_FIELDS), "With no closure evidence supplied, the board remains evidence-prepared rather than approving release closure."),
        _row("staleness-board-clean", release_stale.get("ok") is True, "Central release staleness and verification audit board is clean."),
        _row("review-not-approval", RELEASE_CLOSURE_BOUNDARIES["release_closure_review_is_release_approval"] is False and RELEASE_CLOSURE_BOUNDARIES["closure_evidence_is_publish_permission"] is False, "Release closure review and closure evidence do not approve or publish release."),
        _row("no-authority", all(RELEASE_CLOSURE_BOUNDARIES[key] is False for key in ["release_closure_board_creates_release", "release_closure_board_publishes_release", "release_closure_board_applies_patches", "release_closure_board_executes_rollback", "release_closure_board_expands_autonomy"]), "Closure evidence board grants no release creation, publish, patch, rollback, or autonomy authority."),
    ]
    report = {
        "version": RECOVERY_DRILL_RELEASE_CLOSURE_VERSION,
        "state": "release_closure_evidence_board_review_only",
        "release_closure_evidence_id": RELEASE_CLOSURE_EVIDENCE_ID,
        "closure_fields": list(RELEASE_CLOSURE_FIELDS),
        "missing_closure_fields": missing,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_CLOSURE_BOUNDARIES),
        "safe_next_action": "Operator may review closure evidence. Board does not approve, create, or publish releases and does not execute rollback or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_operator_closure_approval_gate(root: str | Path | None = None, approval_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(CLOSURE_APPROVAL_FIELDS, approval_packet)
    rows = [
        _row("approval-schema-defined", len(CLOSURE_APPROVAL_FIELDS) >= 5, "Closure gate requires exact phrase, current version confirmation, evidence reference, single-use scope, and approval burnout confirmation."),
        _row("fresh-phrase-required", CLOSURE_APPROVAL_BOUNDARIES["fresh_operator_phrase_required"] is True, "Closure gate requires a fresh operator phrase rather than inferred approval."),
        _row("single-use", CLOSURE_APPROVAL_BOUNDARIES["closure_approval_is_single_use"] is True, "Closure approval is explicitly single-use."),
        _row("missing-approval-awaits", len(missing) == len(CLOSURE_APPROVAL_FIELDS), "With no approval packet supplied, approval remains required."),
        _row("no-authority", all(CLOSURE_APPROVAL_BOUNDARIES[key] is False for key in ["closure_approval_authorizes_future_patches", "closure_approval_authorizes_future_releases", "closure_approval_authorizes_autonomy", "closure_gate_infers_approval_from_receipts", "closure_gate_reuses_prior_approval", "closure_gate_creates_release", "closure_gate_executes_commands"]), "Closure gate grants no future patch, future release, autonomy, receipt-inferred approval, approval reuse, release creation, or command authority."),
    ]
    report = {
        "version": RECOVERY_DRILL_RELEASE_CLOSURE_VERSION,
        "state": "operator_closure_approval_gate_review_only",
        "operator_closure_gate_id": OPERATOR_CLOSURE_GATE_ID,
        "approval_fields": list(CLOSURE_APPROVAL_FIELDS),
        "missing_approval_fields": missing,
        "required_phrase_template": f"I approve closing Eidolon {CURRENT_VERSION_TAG} release evidence review for this single cycle only.",
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CLOSURE_APPROVAL_BOUNDARIES),
        "safe_next_action": "Operator may review the exact closure phrase requirement. Gate does not infer approval, create releases, run commands, or authorize future work.",
    }
    report.update(_base_authority_state())
    return report


def build_recovery_drill_release_closure_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_recovery_drill_scope_contract(repo)
    decision = build_rollback_decision_review_packet(repo)
    closure = build_release_closure_evidence_board(repo)
    gate = build_operator_closure_approval_gate(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("scope-prepared", scope.get("ok") is True and scope.get("executes_commands") is False, "Recovery drill scope contract is prepared and does not execute commands."),
        _row("rollback-decision-prepared", decision.get("ok") is True and decision.get("executes_rollback") is False, "Rollback decision review packet is prepared and does not execute rollback."),
        _row("closure-evidence-prepared", closure.get("ok") is True and closure.get("creates_release") is False, "Release closure evidence board is prepared and does not create releases."),
        _row("approval-gate-prepared", gate.get("ok") is True and gate.get("approval_status") == "required", "Operator closure approval gate is prepared and still requires exact approval."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Release staleness audit remains clean for current-state fields."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [scope, decision, closure, gate]), "No v556-v560 recovery/closure layer runs commands or executes rollback."),
        _row("no-authority", all(RECOVERY_RELEASE_CLOSURE_BOUNDARIES[key] is False for key in ["recovery_board_is_rollback_permission", "recovery_board_is_release_approval", "recovery_board_executes_commands", "recovery_board_executes_rollback", "recovery_board_applies_patches", "recovery_board_creates_release", "recovery_board_publishes_release", "recovery_board_writes_source", "recovery_board_writes_memory", "recovery_board_invokes_models_by_default", "recovery_board_schedules_work", "recovery_board_reuses_approval", "recovery_board_continues_automatically", "recovery_board_expands_autonomy"]), "Recovery/release closure board grants no rollback, release, command, patch, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RECOVERY_DRILL_RELEASE_CLOSURE_VERSION,
        "state": "recovery_drill_release_closure_board_review_only",
        "recovery_release_closure_board_id": RECOVERY_RELEASE_CLOSURE_BOARD_ID,
        "recovery_drill_scope_contract": scope,
        "rollback_decision_review_packet": decision,
        "release_closure_evidence_board": closure,
        "operator_closure_approval_gate": gate,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RECOVERY_RELEASE_CLOSURE_BOUNDARIES),
        "safe_next_action": "Operator may review v560 recovery drill and release closure board. It does not execute rollback, run commands, apply patches, create releases, publish releases, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_recovery_drill_release_closure_arc(root: str | Path | None = None, stage: str = "recovery_drill_release_closure_board_v1") -> dict[str, Any]:
    builders = {
        "recovery_drill_scope_contract_v1": build_recovery_drill_scope_contract,
        "rollback_decision_review_packet_v1": build_rollback_decision_review_packet,
        "release_closure_evidence_board_v1": build_release_closure_evidence_board,
        "operator_closure_approval_gate_v1": build_operator_closure_approval_gate,
        "recovery_drill_release_closure_board_v1": build_recovery_drill_release_closure_board,
    }
    return builders.get(stage, build_recovery_drill_release_closure_board)(root)


def render_recovery_drill_release_closure_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"recovery_drill_status: {report.get('recovery_drill_status')}",
        f"rollback_decision_status: {report.get('rollback_decision_status')}",
        f"release_closure_status: {report.get('release_closure_status')}",
        f"closure_approval_status: {report.get('closure_approval_status')}",
        f"live_patch_status: {report.get('live_patch_status')}",
        f"rollback_status: {report.get('rollback_status')}",
        f"release_status: {report.get('release_status')}",
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

# v556.0-v565.0 recovery drill release closure tokens: recovery-drill-scope-contract rollback-decision-review-packet release-closure-evidence-board operator-closure-approval-gate recovery-drill-release-closure-board recovery-drill-and-release-closure-v1 recovery_drill_release_closure.py recovery_drill_scope_is_rollback_permission=False recovery_drill_readiness_is_execution_approval=False rollback_recommendation_is_rollback_execution=False rollback_eligibility_is_rollback_authorization=False release_closure_review_is_release_approval=False closure_evidence_is_publish_permission=False closure_approval_is_single_use=True closure_approval_authorizes_future_patches=False closure_approval_authorizes_future_releases=False closure_approval_authorizes_autonomy=False recovery_board_is_rollback_permission=False recovery_board_is_release_approval=False recovery_board_executes_commands=False recovery_board_executes_rollback=False recovery_drill_status=prepared_not_executed rollback_decision_status=review_prepared release_closure_status=evidence_prepared closure_approval_status=required live_patch_status=not_applied_by_default rollback_status=not_executed release_status=not_created authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
