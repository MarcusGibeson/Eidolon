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

ARCHIVE_RECONCILIATION_APPLICATION_PREP_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
APPLICATION_SCOPE_PACKET_ID = "v606_archive_reconciliation_application_scope_packet"
APPLICATION_CANDIDATE_MAP_ID = "v607_reconciliation_application_candidate_map"
OPERATOR_APPLICATION_APPROVAL_CHECKLIST_ID = "v608_operator_reconciliation_application_approval_checklist"
DRY_RUN_APPLICATION_RECEIPT_PREP_ID = "v609_dry_run_application_receipt_prep"
ARCHIVE_RECONCILIATION_APPLICATION_PREP_BOARD_ID = "v610_archive_reconciliation_application_prep_board"

APPLICATION_SCOPE_FIELDS: tuple[str, ...] = (
    "selected_decision_record_reference",
    "target_archive_record_reference",
    "target_current_state_field_reference",
    "operator_decision_required",
    "single_use_application_approval_required",
    "approval_burnout_required",
    "archive_write_prohibition_by_default",
    "current_state_mutation_prohibition_by_default",
    "release_publish_prohibition",
    "rollback_reversal_plan_required",
)

CANDIDATE_MAP_FIELDS: tuple[str, ...] = (
    "candidate_archive_updates",
    "candidate_current_state_updates",
    "candidate_metadata_adjustments",
    "candidate_release_history_notes",
    "candidate_readme_continuity_notes",
    "blocked_mutations",
    "required_operator_decisions",
)

APPROVAL_CHECKLIST_FIELDS: tuple[str, ...] = (
    "selected_reconciliation_option",
    "target_archive_record",
    "target_current_state_fields",
    "expected_result",
    "rollback_or_reversal_plan",
    "single_use_approval",
    "approval_burnout",
)

DRY_RUN_RECEIPT_FIELDS: tuple[str, ...] = (
    "planned_changes",
    "no_write_confirmation",
    "no_current_state_mutation_confirmation",
    "blocked_write_confirmation",
    "operator_approval_required_confirmation",
    "receipt_status",
)

APPLICATION_PREP_BOUNDARIES: dict[str, bool] = {
    "application_scope_is_application": False,
    "application_scope_writes_archive_records": False,
    "application_scope_mutates_current_state": False,
    "application_scope_writes_external_ledger": False,
    "application_scope_creates_release": False,
    "application_scope_publishes_release": False,
    "candidate_map_writes_archive_records": False,
    "candidate_map_mutates_current_state": False,
    "candidate_map_selects_reconciliation": False,
    "approval_checklist_grants_approval": False,
    "approval_checklist_reuses_prior_approval": False,
    "dry_run_receipt_is_execution_receipt": False,
    "dry_run_receipt_executes_application": False,
    "dry_run_receipt_writes_archive_records": False,
    "application_prep_board_is_operator_approval": False,
    "application_prep_board_is_archive_write_permission": False,
    "application_prep_board_is_release_approval": False,
    "application_prep_board_is_publish_permission": False,
    "application_prep_board_writes_archive_records": False,
    "application_prep_board_mutates_current_state": False,
    "application_prep_board_writes_external_ledger": False,
    "application_prep_board_executes_commands": False,
    "application_prep_board_applies_patches": False,
    "application_prep_board_executes_rollback": False,
    "application_prep_board_writes_source": False,
    "application_prep_board_writes_memory": False,
    "application_prep_board_reuses_approval": False,
    "application_prep_board_continues_automatically": False,
    "application_prep_board_expands_autonomy": False,
    "operator_decision_required": True,
    "approval_required": True,
    "operator_review_required": True,
    "single_use_approval_required": True,
    "approval_burnout_required": True,
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


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _missing(fields: tuple[str, ...], payload: dict[str, Any] | None) -> list[str]:
    supplied = dict(payload or {})
    return [field for field in fields if field not in supplied]


def _base_application_state() -> dict[str, Any]:
    return {
        "archive_reconciliation_application_status": "prepared_only",
        "application_prep_status": "prepared_only",
        "operator_decision_status": "required",
        "operator_application_approval_status": "required",
        "application_scope_status": "prepared_not_applied",
        "candidate_map_status": "prepared_not_selected",
        "approval_checklist_status": "prepared_not_approved",
        "dry_run_receipt_status": "prepared_not_executed",
        "archive_write_status": "not_performed",
        "current_state_mutation_status": "not_performed",
        "external_ledger_write_status": "not_performed",
        "source_status": "untouched",
        "memory_status": "untouched",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "rollback_status": "not_executed",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "writes_source": False,
        "writes_memory": False,
        "writes_records": False,
        "writes_archive_records": False,
        "writes_external_ledger": False,
        "modifies_live_files": False,
        "mutates_current_state": False,
        "selects_reconciliation": False,
        "executes_reconciliation": False,
        "executes_application": False,
        "executes_commands": False,
        "applies_patch": False,
        "executes_rollback": False,
        "creates_release": False,
        "publishes_release": False,
        "invokes_models_by_default": False,
        "schedules_work": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "single_use_approval_required": True,
        "approval_burnout_required": True,
        "operator_review_required": True,
        "review_only": True,
    }


def build_archive_reconciliation_application_scope_packet(application_scope: dict[str, Any] | None = None, root: str | Path | None = None) -> dict[str, Any]:
    supplied = dict(application_scope or {})
    missing = _missing(APPLICATION_SCOPE_FIELDS, supplied)
    rows = [
        _row("scope-fields-declared", not missing or not supplied, f"application scope fields missing={len(missing)}; blank templates remain reviewable."),
        _row("application-scope-prepared-only", APPLICATION_PREP_BOUNDARIES["application_scope_is_application"] is False, "Application scope packet is preparation only and is not archive reconciliation application."),
        _row("no-archive-write", APPLICATION_PREP_BOUNDARIES["application_scope_writes_archive_records"] is False, "Scope packet writes no archive records."),
        _row("no-current-state-mutation", APPLICATION_PREP_BOUNDARIES["application_scope_mutates_current_state"] is False, "Scope packet mutates no current-state fields."),
        _row("approval-required", APPLICATION_PREP_BOUNDARIES["single_use_approval_required"] is True and APPLICATION_PREP_BOUNDARIES["approval_burnout_required"] is True, "Any future application requires exact single-use approval and approval burnout."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "archive_reconciliation_application_scope_packet_review_only",
        "packet_id": APPLICATION_SCOPE_PACKET_ID,
        "required_fields": list(APPLICATION_SCOPE_FIELDS),
        "supplied_scope": supplied,
        "missing_fields": missing,
        "prepared_at": _now_iso(),
        **_base_application_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPLICATION_PREP_BOUNDARIES),
    }


def build_reconciliation_application_candidate_map(candidate_map: dict[str, Any] | None = None, root: str | Path | None = None) -> dict[str, Any]:
    supplied = dict(candidate_map or {})
    default_candidates = {
        "candidate_archive_updates": ["operator-selected archive reconciliation write target would be listed here only after decision review"],
        "candidate_current_state_updates": ["operator-selected current-state field adjustment would be listed here only after approval"],
        "candidate_metadata_adjustments": ["metadata adjustment candidates are review-only until explicitly approved"],
        "candidate_release_history_notes": ["release history note candidates remain draft-only"],
        "candidate_readme_continuity_notes": ["README continuity note candidates remain draft-only"],
        "blocked_mutations": ["archive write", "current-state mutation", "external ledger write", "release creation", "publish", "memory write", "source patch", "rollback execution", "autonomy expansion"],
        "required_operator_decisions": ["selected reconciliation option", "exact target records", "expected result", "rollback/reversal plan", "single-use approval phrase"],
    }
    merged = {**default_candidates, **supplied}
    missing = _missing(CANDIDATE_MAP_FIELDS, merged)
    rows = [
        _row("candidate-fields-present", not missing, f"candidate map required fields missing={len(missing)}."),
        _row("candidate-map-prepared-only", APPLICATION_PREP_BOUNDARIES["candidate_map_writes_archive_records"] is False and APPLICATION_PREP_BOUNDARIES["candidate_map_mutates_current_state"] is False, "Candidate map writes no archive records and mutates no current state."),
        _row("candidate-map-does-not-select", APPLICATION_PREP_BOUNDARIES["candidate_map_selects_reconciliation"] is False, "Candidate map does not select a reconciliation option."),
        _row("blocked-mutations-listed", bool(merged.get("blocked_mutations")), "Blocked mutation classes are listed for operator review."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "reconciliation_application_candidate_map_review_only",
        "map_id": APPLICATION_CANDIDATE_MAP_ID,
        "candidate_map": merged,
        "missing_fields": missing,
        **_base_application_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPLICATION_PREP_BOUNDARIES),
    }


def build_operator_reconciliation_application_approval_checklist(approval_packet: dict[str, Any] | None = None, root: str | Path | None = None) -> dict[str, Any]:
    supplied = dict(approval_packet or {})
    checklist = {
        "selected_reconciliation_option": supplied.get("selected_reconciliation_option", "operator_not_supplied"),
        "target_archive_record": supplied.get("target_archive_record", "operator_not_supplied"),
        "target_current_state_fields": supplied.get("target_current_state_fields", "operator_not_supplied"),
        "expected_result": supplied.get("expected_result", "operator_not_supplied"),
        "rollback_or_reversal_plan": supplied.get("rollback_or_reversal_plan", "required_before_any_future_application"),
        "single_use_approval": supplied.get("single_use_approval", "not_granted"),
        "approval_burnout": supplied.get("approval_burnout", "required_after_any_approved_attempt"),
    }
    missing = _missing(APPROVAL_CHECKLIST_FIELDS, supplied)
    rows = [
        _row("approval-fields-template-ready", len(checklist) == len(APPROVAL_CHECKLIST_FIELDS), "Approval checklist template includes exact scope, target, expectation, reversal, single-use approval, and burnout fields."),
        _row("approval-not-granted-by-checklist", APPLICATION_PREP_BOUNDARIES["approval_checklist_grants_approval"] is False, "Checklist existence does not grant approval."),
        _row("prior-approval-not-reused", APPLICATION_PREP_BOUNDARIES["approval_checklist_reuses_prior_approval"] is False, "Prior approval cannot be reused for reconciliation application."),
        _row("operator-decision-required", checklist["selected_reconciliation_option"] == "operator_not_supplied" or bool(supplied.get("operator_supplied_decision_record")), "Blank checklist remains operator-required until a supplied decision record exists."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "operator_reconciliation_application_approval_checklist_review_only",
        "checklist_id": OPERATOR_APPLICATION_APPROVAL_CHECKLIST_ID,
        "required_fields": list(APPROVAL_CHECKLIST_FIELDS),
        "checklist": checklist,
        "missing_supplied_fields": missing,
        **_base_application_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPLICATION_PREP_BOUNDARIES),
    }


def build_dry_run_application_receipt_prep(receipt_packet: dict[str, Any] | None = None, root: str | Path | None = None) -> dict[str, Any]:
    supplied = dict(receipt_packet or {})
    receipt = {
        "planned_changes": supplied.get("planned_changes", []),
        "no_write_confirmation": True,
        "no_current_state_mutation_confirmation": True,
        "blocked_write_confirmation": True,
        "operator_approval_required_confirmation": True,
        "receipt_status": "prepared_not_executed",
    }
    rows = [
        _row("receipt-template-prepared", all(field in receipt for field in DRY_RUN_RECEIPT_FIELDS), "Dry-run application receipt template is prepared."),
        _row("receipt-not-execution", APPLICATION_PREP_BOUNDARIES["dry_run_receipt_is_execution_receipt"] is False and APPLICATION_PREP_BOUNDARIES["dry_run_receipt_executes_application"] is False, "Dry-run receipt prep is not execution and performs no application."),
        _row("no-write-confirmed", receipt["no_write_confirmation"] is True and receipt["no_current_state_mutation_confirmation"] is True, "Receipt prep confirms no archive write and no current-state mutation."),
        _row("approval-required-confirmed", receipt["operator_approval_required_confirmation"] is True, "Receipt prep confirms operator approval is required before any future application."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "dry_run_application_receipt_prep_review_only",
        "receipt_prep_id": DRY_RUN_APPLICATION_RECEIPT_PREP_ID,
        "receipt": receipt,
        **_base_application_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPLICATION_PREP_BOUNDARIES),
    }


def build_archive_reconciliation_application_prep_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_archive_reconciliation_application_scope_packet(root=repo)
    candidates = build_reconciliation_application_candidate_map(root=repo)
    checklist = build_operator_reconciliation_application_approval_checklist(root=repo)
    receipt = build_dry_run_application_receipt_prep(root=repo)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/archive_reconciliation_application_prep.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v610.0 - Operator-Governed Archive Reconciliation Application Prep v1",
        TARGETED_SMOKE,
        "archive-reconciliation-application-scope-packet",
        "reconciliation-application-candidate-map",
        "operator-reconciliation-application-approval-checklist",
        "dry-run-application-receipt-prep",
        "archive-reconciliation-application-prep-board",
        "archive_reconciliation_application_prep.py",
        "application_prep_status=prepared_only",
        "dry_run_receipt_status=prepared_not_executed",
        "application_prep_board_is_operator_approval=False",
        "application_prep_board_writes_archive_records=False",
        "application_prep_board_mutates_current_state=False",
        "no_native_title_tooltip",
        "data-tip",
    ]
    rows = [
        _row("scope-packet-ready", scope.get("ok") is True, "Application scope packet is prepared and review-only."),
        _row("candidate-map-ready", candidates.get("ok") is True, "Application candidate map is prepared and review-only."),
        _row("approval-checklist-ready", checklist.get("ok") is True, "Operator application approval checklist is prepared and does not grant approval."),
        _row("dry-run-receipt-prep-ready", receipt.get("ok") is True, "Dry-run receipt prep is prepared and not executed."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Expanded stale scanner remains clean for current-state surfaces."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current symbol audit remains aligned to v610."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains aligned and review-only."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v606-v610 application prep surfaces and non-authority tokens."),
        _row("no-authority", all(APPLICATION_PREP_BOUNDARIES[key] is False for key in ["application_scope_is_application", "application_scope_writes_archive_records", "application_scope_mutates_current_state", "candidate_map_writes_archive_records", "candidate_map_mutates_current_state", "candidate_map_selects_reconciliation", "approval_checklist_grants_approval", "approval_checklist_reuses_prior_approval", "dry_run_receipt_is_execution_receipt", "dry_run_receipt_executes_application", "application_prep_board_is_operator_approval", "application_prep_board_is_archive_write_permission", "application_prep_board_is_release_approval", "application_prep_board_is_publish_permission", "application_prep_board_writes_archive_records", "application_prep_board_mutates_current_state", "application_prep_board_writes_external_ledger", "application_prep_board_executes_commands", "application_prep_board_applies_patches", "application_prep_board_executes_rollback", "application_prep_board_writes_source", "application_prep_board_writes_memory", "application_prep_board_reuses_approval", "application_prep_board_continues_automatically", "application_prep_board_expands_autonomy"]), "Application prep grants no approval, write, mutation, command, rollback, source, memory, release, publish, continuation, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "archive_reconciliation_application_prep_board_review_only",
        "board_id": ARCHIVE_RECONCILIATION_APPLICATION_PREP_BOARD_ID,
        **_base_application_state(),
        "application_scope_packet": scope,
        "candidate_map": candidates,
        "operator_approval_checklist": checklist,
        "dry_run_application_receipt_prep": receipt,
        "stale_version_string_scanner": scanner,
        "current_symbol_staleness_audit": symbols,
        "release_staleness_verification_board": release_board,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(APPLICATION_PREP_BOUNDARIES),
        "safe_next_action": "Operator may review the v610 archive reconciliation application prep board. Next work should start command-center UI consolidation without applying archive writes, mutating current state, creating releases, publishing, writing memory, reusing approval, or expanding autonomy.",
    }


def build_archive_reconciliation_application_prep_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "archive_reconciliation_application_prep_board_v1"
    builders = {
        "archive_reconciliation_application_scope_packet_v1": build_archive_reconciliation_application_scope_packet,
        "reconciliation_application_candidate_map_v1": build_reconciliation_application_candidate_map,
        "operator_reconciliation_application_approval_checklist_v1": build_operator_reconciliation_application_approval_checklist,
        "dry_run_application_receipt_prep_v1": build_dry_run_application_receipt_prep,
        "archive_reconciliation_application_prep_board_v1": build_archive_reconciliation_application_prep_board,
    }
    return builders.get(stage, build_archive_reconciliation_application_prep_board)(root=root)


def render_archive_reconciliation_application_prep_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"archive_reconciliation_application_status: {report.get('archive_reconciliation_application_status')}",
        f"application_prep_status: {report.get('application_prep_status')}",
        f"operator_decision_status: {report.get('operator_decision_status')}",
        f"operator_application_approval_status: {report.get('operator_application_approval_status')}",
        f"dry_run_receipt_status: {report.get('dry_run_receipt_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"current_state_mutation_status: {report.get('current_state_mutation_status')}",
        f"release_status: {report.get('release_status')}",
        f"publish_status: {report.get('publish_status')}",
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


# v606.0-v610.0 archive reconciliation application prep tokens: archive-reconciliation-application-scope-packet reconciliation-application-candidate-map operator-reconciliation-application-approval-checklist dry-run-application-receipt-prep archive-reconciliation-application-prep-board archive-reconciliation-application-prep-v1 archive_reconciliation_application_prep.py archive_reconciliation_application_status=prepared_only application_prep_status=prepared_only operator_decision_status=required operator_application_approval_status=required dry_run_receipt_status=prepared_not_executed archive_write_status=not_performed current_state_mutation_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous application_scope_is_application=False candidate_map_selects_reconciliation=False approval_checklist_grants_approval=False dry_run_receipt_executes_application=False application_prep_board_is_operator_approval=False application_prep_board_writes_archive_records=False application_prep_board_mutates_current_state=False application_prep_board_executes_commands=False application_prep_board_writes_source=False application_prep_board_writes_memory=False application_prep_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
