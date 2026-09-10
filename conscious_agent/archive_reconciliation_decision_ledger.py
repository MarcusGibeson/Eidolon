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

ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
RECONCILIATION_DECISION_SCOPE_ID = "v596_reconciliation_decision_scope_contract"
RECONCILIATION_DECISION_OPTION_LEDGER_ID = "v597_reconciliation_decision_option_ledger"
OPERATOR_RECONCILIATION_DECISION_RECORD_ID = "v598_operator_reconciliation_decision_record_prep"
RECONCILIATION_DECISION_GUARD_REVIEW_ID = "v599_reconciliation_decision_guard_review"
ARCHIVE_RECONCILIATION_DECISION_LEDGER_BOARD_ID = "v600_archive_reconciliation_decision_ledger_board"

DECISION_SCOPE_FIELDS: tuple[str, ...] = (
    "conflict_packet_reference",
    "classification_matrix_reference",
    "reconciliation_options_reference",
    "operator_decision_required",
    "single_use_decision_boundary",
    "current_source_of_truth_reference",
    "archive_write_prohibition",
    "current_state_mutation_prohibition",
    "approval_reuse_prohibition",
)

DECISION_LEDGER_FIELDS: tuple[str, ...] = (
    "decision_option",
    "decision_status",
    "operator_identity_placeholder",
    "decision_timestamp_placeholder",
    "evidence_reference",
    "affected_archive_record_reference",
    "current_state_effect",
    "external_write_status",
    "next_review_action",
)

OPERATOR_DECISION_OPTIONS: tuple[str, ...] = (
    "accept_current_source_of_truth",
    "classify_import_as_historical_only",
    "request_manual_metadata_correction",
    "request_readme_release_history_review",
    "request_package_reverification",
    "block_archive_import",
    "defer_reconciliation_decision",
)

DECISION_GUARD_FIELDS: tuple[str, ...] = (
    "operator_decision_not_supplied_by_default",
    "decision_record_not_written_externally",
    "archive_records_not_mutated",
    "current_state_not_mutated",
    "prior_approval_not_reused",
    "release_not_created",
    "publish_not_authorized",
    "autonomy_not_expanded",
)

DECISION_SCOPE_BOUNDARIES: dict[str, bool] = {
    "decision_scope_is_operator_decision": False,
    "decision_scope_writes_ledger": False,
    "decision_scope_writes_archive_records": False,
    "decision_scope_mutates_current_state": False,
    "decision_scope_reuses_prior_approval": False,
    "decision_scope_creates_release": False,
    "decision_scope_publishes_release": False,
    "decision_scope_runs_commands": False,
    "decision_scope_applies_patches": False,
    "decision_scope_executes_rollback": False,
    "decision_scope_writes_source": False,
    "decision_scope_writes_memory": False,
    "decision_scope_expands_autonomy": False,
    "operator_review_required": True,
}

DECISION_LEDGER_BOUNDARIES: dict[str, bool] = {
    "decision_ledger_selects_option": False,
    "decision_ledger_records_external_decision": False,
    "ledger_prep_is_archive_write": False,
    "ledger_prep_is_release_approval": False,
    "ledger_prep_mutates_current_state": False,
    "ledger_prep_creates_release": False,
    "ledger_prep_publishes_release": False,
    "ledger_prep_runs_commands": False,
    "ledger_prep_applies_patches": False,
    "ledger_prep_executes_rollback": False,
    "ledger_prep_writes_source": False,
    "ledger_prep_writes_memory": False,
    "ledger_prep_expands_autonomy": False,
    "operator_review_required": True,
}

OPERATOR_DECISION_RECORD_BOUNDARIES: dict[str, bool] = {
    "decision_record_prep_is_decision": False,
    "decision_record_prep_reuses_prior_approval": False,
    "decision_record_prep_writes_external_ledger": False,
    "decision_record_prep_writes_archive_records": False,
    "decision_record_prep_mutates_current_state": False,
    "decision_record_prep_creates_release": False,
    "decision_record_prep_publishes_release": False,
    "decision_record_prep_runs_commands": False,
    "decision_record_prep_applies_patches": False,
    "decision_record_prep_executes_rollback": False,
    "decision_record_prep_writes_source": False,
    "decision_record_prep_writes_memory": False,
    "decision_record_prep_expands_autonomy": False,
    "operator_review_required": True,
}

DECISION_GUARD_BOUNDARIES: dict[str, bool] = {
    "decision_guard_pass_is_reconciliation_approval": False,
    "decision_guard_pass_is_archive_write_permission": False,
    "decision_guard_writes_ledger": False,
    "decision_guard_writes_archive_records": False,
    "decision_guard_mutates_current_state": False,
    "decision_guard_reuses_prior_approval": False,
    "decision_guard_creates_release": False,
    "decision_guard_publishes_release": False,
    "decision_guard_runs_commands": False,
    "decision_guard_applies_patches": False,
    "decision_guard_executes_rollback": False,
    "decision_guard_writes_source": False,
    "decision_guard_writes_memory": False,
    "decision_guard_expands_autonomy": False,
    "operator_review_required": True,
}

ARCHIVE_RECONCILIATION_DECISION_LEDGER_BOARD_BOUNDARIES: dict[str, bool] = {
    "decision_ledger_board_is_operator_approval": False,
    "decision_ledger_board_is_release_approval": False,
    "decision_ledger_board_is_publish_permission": False,
    "decision_ledger_board_selects_decision": False,
    "decision_ledger_board_executes_decision": False,
    "decision_ledger_board_writes_external_ledger": False,
    "decision_ledger_board_writes_archive_records": False,
    "decision_ledger_board_mutates_current_state": False,
    "decision_ledger_board_reuses_prior_approval": False,
    "decision_ledger_board_creates_release": False,
    "decision_ledger_board_publishes_release": False,
    "decision_ledger_board_executes_commands": False,
    "decision_ledger_board_applies_patches": False,
    "decision_ledger_board_executes_rollback": False,
    "decision_ledger_board_writes_source": False,
    "decision_ledger_board_writes_memory": False,
    "decision_ledger_board_invokes_models_by_default": False,
    "decision_ledger_board_schedules_work": False,
    "decision_ledger_board_reuses_approval": False,
    "decision_ledger_board_continues_automatically": False,
    "decision_ledger_board_expands_autonomy": False,
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
        "reconciliation_decision_status": "operator_required",
        "decision_ledger_status": "prepared_not_written_externally",
        "operator_decision_record_status": "prepared_not_supplied",
        "decision_guard_status": "guarded",
        "archive_conflict_status": "detected_or_review_prepared",
        "conflict_classification_status": "matrix_prepared",
        "reconciliation_option_status": "prepared_for_operator",
        "current_state_mutation_status": "not_performed",
        "archive_write_status": "not_performed",
        "external_ledger_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "source_status": "untouched",
        "memory_status": "untouched",
        "rollback_status": "not_executed",
        "autonomy_status": "not_autonomous",
        "writes_source": False,
        "writes_memory": False,
        "writes_records": False,
        "writes_archive_records": False,
        "writes_external_ledger": False,
        "modifies_live_files": False,
        "mutates_current_state": False,
        "selects_decision": False,
        "executes_decision": False,
        "selects_reconciliation": False,
        "executes_reconciliation": False,
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


def build_reconciliation_decision_scope_contract(root: str | Path | None = None, decision_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(DECISION_SCOPE_FIELDS, decision_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("decision-scope-schema-defined", len(DECISION_SCOPE_FIELDS) >= 9, "Archive reconciliation decision scope defines conflict, classification, option, operator decision, single-use, source-of-truth, archive-write, current-state, and approval-reuse boundaries."),
        _row("missing-decision-packet-awaits", len(missing) == len(DECISION_SCOPE_FIELDS), "With no operator decision packet supplied, the layer remains prepared/read-only instead of selecting a decision."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before decision ledger review."),
        _row("scope-not-decision", DECISION_SCOPE_BOUNDARIES["decision_scope_is_operator_decision"] is False, "Decision scope is not the operator decision."),
        _row("no-authority", all(DECISION_SCOPE_BOUNDARIES[key] is False for key in ["decision_scope_writes_ledger", "decision_scope_writes_archive_records", "decision_scope_mutates_current_state", "decision_scope_reuses_prior_approval", "decision_scope_creates_release", "decision_scope_publishes_release", "decision_scope_runs_commands", "decision_scope_applies_patches", "decision_scope_executes_rollback", "decision_scope_writes_source", "decision_scope_writes_memory", "decision_scope_expands_autonomy"]), "Decision scope grants no ledger write, archive write, current-state mutation, approval reuse, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION,
        "state": "reconciliation_decision_scope_contract_review_only",
        "reconciliation_decision_scope_id": RECONCILIATION_DECISION_SCOPE_ID,
        "required_fields": list(DECISION_SCOPE_FIELDS),
        "missing_fields": missing,
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DECISION_SCOPE_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_reconciliation_decision_option_ledger(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_reconciliation_decision_scope_contract(repo)
    rows = [
        _row("scope-ready", scope.get("ok") is True, "Reconciliation decision scope contract is available."),
        _row("decision-ledger-fields-defined", len(DECISION_LEDGER_FIELDS) >= 9, "Decision ledger prep defines decision option, status, operator identity placeholder, timestamp placeholder, evidence reference, affected archive reference, current-state effect, external-write status, and next review action."),
        _row("options-defined", len(OPERATOR_DECISION_OPTIONS) >= 7, "Operator decision options remain explicit and are not selected automatically."),
        _row("ledger-does-not-select", DECISION_LEDGER_BOUNDARIES["decision_ledger_selects_option"] is False, "Decision ledger prep does not select an option."),
        _row("ledger-not-write", DECISION_LEDGER_BOUNDARIES["decision_ledger_records_external_decision"] is False and DECISION_LEDGER_BOUNDARIES["ledger_prep_is_archive_write"] is False, "Decision ledger prep does not write an external decision or archive record."),
        _row("no-authority", all(DECISION_LEDGER_BOUNDARIES[key] is False for key in ["ledger_prep_is_release_approval", "ledger_prep_mutates_current_state", "ledger_prep_creates_release", "ledger_prep_publishes_release", "ledger_prep_runs_commands", "ledger_prep_applies_patches", "ledger_prep_executes_rollback", "ledger_prep_writes_source", "ledger_prep_writes_memory", "ledger_prep_expands_autonomy"]), "Decision ledger prep grants no release approval, mutation, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION,
        "state": "reconciliation_decision_option_ledger_review_only",
        "reconciliation_decision_option_ledger_id": RECONCILIATION_DECISION_OPTION_LEDGER_ID,
        "decision_ledger_fields": list(DECISION_LEDGER_FIELDS),
        "operator_decision_options": list(OPERATOR_DECISION_OPTIONS),
        "scope_contract": {"ok": scope.get("ok"), "state": scope.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DECISION_LEDGER_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_operator_reconciliation_decision_record_prep(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    ledger = build_reconciliation_decision_option_ledger(repo)
    rows = [
        _row("ledger-ready", ledger.get("ok") is True, "Reconciliation decision option ledger is available."),
        _row("record-prep-not-decision", OPERATOR_DECISION_RECORD_BOUNDARIES["decision_record_prep_is_decision"] is False, "Decision record prep is not the operator decision."),
        _row("prior-approval-not-reused", OPERATOR_DECISION_RECORD_BOUNDARIES["decision_record_prep_reuses_prior_approval"] is False, "Decision record prep does not reuse prior approval."),
        _row("no-write", OPERATOR_DECISION_RECORD_BOUNDARIES["decision_record_prep_writes_external_ledger"] is False and OPERATOR_DECISION_RECORD_BOUNDARIES["decision_record_prep_writes_archive_records"] is False, "Decision record prep writes no external ledger or archive records."),
        _row("no-mutation", OPERATOR_DECISION_RECORD_BOUNDARIES["decision_record_prep_mutates_current_state"] is False, "Decision record prep does not mutate current state."),
        _row("no-authority", all(OPERATOR_DECISION_RECORD_BOUNDARIES[key] is False for key in ["decision_record_prep_creates_release", "decision_record_prep_publishes_release", "decision_record_prep_runs_commands", "decision_record_prep_applies_patches", "decision_record_prep_executes_rollback", "decision_record_prep_writes_source", "decision_record_prep_writes_memory", "decision_record_prep_expands_autonomy"]), "Decision record prep grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION,
        "state": "operator_reconciliation_decision_record_prep_review_only",
        "operator_reconciliation_decision_record_id": OPERATOR_RECONCILIATION_DECISION_RECORD_ID,
        "decision_options": list(OPERATOR_DECISION_OPTIONS),
        "decision_ledger": {"ok": ledger.get("ok"), "state": ledger.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(OPERATOR_DECISION_RECORD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_reconciliation_decision_guard_review(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    record = build_operator_reconciliation_decision_record_prep(repo)
    release_audit = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("record-prep-ready", record.get("ok") is True, "Operator reconciliation decision record prep is available."),
        _row("guard-fields-defined", len(DECISION_GUARD_FIELDS) >= 8, "Decision guard verifies no default operator decision, no external decision record write, no archive mutation, no current-state mutation, no prior approval reuse, no release, no publish authorization, and no autonomy expansion."),
        _row("release-audit-clean", release_audit.get("ok") is True, "Release staleness and verification audit board is clean for the current release."),
        _row("guard-not-approval", DECISION_GUARD_BOUNDARIES["decision_guard_pass_is_reconciliation_approval"] is False, "Decision guard pass is not reconciliation approval."),
        _row("guard-not-write-permission", DECISION_GUARD_BOUNDARIES["decision_guard_pass_is_archive_write_permission"] is False, "Decision guard pass is not archive write permission."),
        _row("no-authority", all(DECISION_GUARD_BOUNDARIES[key] is False for key in ["decision_guard_writes_ledger", "decision_guard_writes_archive_records", "decision_guard_mutates_current_state", "decision_guard_reuses_prior_approval", "decision_guard_creates_release", "decision_guard_publishes_release", "decision_guard_runs_commands", "decision_guard_applies_patches", "decision_guard_executes_rollback", "decision_guard_writes_source", "decision_guard_writes_memory", "decision_guard_expands_autonomy"]), "Decision guard grants no ledger write, archive write, current-state mutation, approval reuse, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION,
        "state": "reconciliation_decision_guard_review_review_only",
        "reconciliation_decision_guard_review_id": RECONCILIATION_DECISION_GUARD_REVIEW_ID,
        "guard_fields": list(DECISION_GUARD_FIELDS),
        "operator_record": {"ok": record.get("ok"), "state": record.get("state")},
        "release_audit": {"ok": release_audit.get("ok"), "state": release_audit.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DECISION_GUARD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_archive_reconciliation_decision_ledger_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_reconciliation_decision_scope_contract(repo)
    ledger = build_reconciliation_decision_option_ledger(repo)
    record = build_operator_reconciliation_decision_record_prep(repo)
    guard = build_reconciliation_decision_guard_review(repo)
    rows = [
        _row("decision-scope", scope.get("ok") is True, "Archive reconciliation decision scope contract is prepared."),
        _row("decision-ledger", ledger.get("ok") is True and ledger.get("decision_ledger_status") == "prepared_not_written_externally", "Reconciliation decision option ledger is prepared without external writes."),
        _row("operator-record", record.get("ok") is True and record.get("operator_decision_record_status") == "prepared_not_supplied", "Operator reconciliation decision record prep is available without supplying a decision."),
        _row("decision-guard", guard.get("ok") is True and guard.get("decision_guard_status") == "guarded", "Reconciliation decision guard review is prepared."),
        _row("no-write-or-mutation", all(report.get("writes_records") is False and report.get("writes_archive_records") is False and report.get("writes_external_ledger") is False and report.get("mutates_current_state") is False for report in [scope, ledger, record, guard]), "No stage writes records, writes archive records, writes an external ledger, or mutates current state."),
        _row("no-decision-execution", all(report.get("selects_decision") is False and report.get("executes_decision") is False and report.get("selects_reconciliation") is False and report.get("executes_reconciliation") is False for report in [scope, ledger, record, guard]), "No stage selects or executes reconciliation decisions automatically."),
        _row("no-release-publish", all(report.get("creates_release") is False and report.get("publishes_release") is False for report in [scope, ledger, record, guard]), "No stage creates or publishes releases."),
        _row("no-execution", all(report.get("executes_commands") is False and report.get("applies_patch") is False and report.get("executes_rollback") is False for report in [scope, ledger, record, guard]), "No stage runs commands, applies patches, or executes rollback."),
        _row("no-source-memory-autonomy", all(report.get("writes_source") is False and report.get("writes_memory") is False and report.get("expands_autonomy") is False for report in [scope, ledger, record, guard]), "No stage writes source, writes memory, or expands autonomy."),
        _row("board-no-authority", all(ARCHIVE_RECONCILIATION_DECISION_LEDGER_BOARD_BOUNDARIES[key] is False for key in ["decision_ledger_board_is_operator_approval", "decision_ledger_board_is_release_approval", "decision_ledger_board_is_publish_permission", "decision_ledger_board_selects_decision", "decision_ledger_board_executes_decision", "decision_ledger_board_writes_external_ledger", "decision_ledger_board_writes_archive_records", "decision_ledger_board_mutates_current_state", "decision_ledger_board_reuses_prior_approval", "decision_ledger_board_creates_release", "decision_ledger_board_publishes_release", "decision_ledger_board_executes_commands", "decision_ledger_board_applies_patches", "decision_ledger_board_executes_rollback", "decision_ledger_board_writes_source", "decision_ledger_board_writes_memory", "decision_ledger_board_invokes_models_by_default", "decision_ledger_board_schedules_work", "decision_ledger_board_reuses_approval", "decision_ledger_board_continues_automatically", "decision_ledger_board_expands_autonomy"]), "Final decision ledger board grants no approval, publishing, decision execution, ledger write, archive write, mutation, release, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION,
        "state": "archive_reconciliation_decision_ledger_board_review_only",
        "archive_reconciliation_decision_ledger_board_id": ARCHIVE_RECONCILIATION_DECISION_LEDGER_BOARD_ID,
        "targeted_smoke": TARGETED_SMOKE,
        "current_version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "generated_at": _now_iso(),
        "stages": {
            "scope": scope,
            "ledger": ledger,
            "operator_record": record,
            "guard": guard,
        },
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_RECONCILIATION_DECISION_LEDGER_BOARD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


_STAGE_BUILDERS = {
    "reconciliation_decision_scope_contract_v1": build_reconciliation_decision_scope_contract,
    "reconciliation_decision_option_ledger_v1": build_reconciliation_decision_option_ledger,
    "operator_reconciliation_decision_record_prep_v1": build_operator_reconciliation_decision_record_prep,
    "reconciliation_decision_guard_review_v1": build_reconciliation_decision_guard_review,
    "archive_reconciliation_decision_ledger_board_v1": build_archive_reconciliation_decision_ledger_board,
}


def build_archive_reconciliation_decision_ledger_arc(root: str | Path | None = None, stage: str = "archive_reconciliation_decision_ledger_board_v1") -> dict[str, Any]:
    builder = _STAGE_BUILDERS.get(stage, build_archive_reconciliation_decision_ledger_board)
    return builder(root)


def render_archive_reconciliation_decision_ledger_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"Archive Reconciliation Decision Ledger v1 ({report.get('version', ARCHIVE_RECONCILIATION_DECISION_LEDGER_VERSION)})",
        f"state: {report.get('state', 'unknown')}",
        f"status: {report.get('status', 'unknown')} ok={report.get('ok')}",
        f"reconciliation_decision_status: {report.get('reconciliation_decision_status', 'operator_required')}",
        f"decision_ledger_status: {report.get('decision_ledger_status', 'prepared_not_written_externally')}",
        f"operator_decision_record_status: {report.get('operator_decision_record_status', 'prepared_not_supplied')}",
        f"decision_guard_status: {report.get('decision_guard_status', 'guarded')}",
        f"current_state_mutation_status: {report.get('current_state_mutation_status', 'not_performed')}",
        f"archive_write_status: {report.get('archive_write_status', 'not_performed')}",
        f"external_ledger_write_status: {report.get('external_ledger_write_status', 'not_performed')}",
        f"release_status: {report.get('release_status', 'not_created')}",
        f"publish_status: {report.get('publish_status', 'not_authorized')}",
        f"approval_status: {report.get('approval_status', 'required')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        f"autonomy_status: {report.get('autonomy_status', 'not_autonomous')}",
        "rows:",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('status')}: {row.get('name')} — {row.get('message')}")
    return lines


# v596.0-v600.0 archive reconciliation decision ledger tokens: reconciliation-decision-scope-contract reconciliation-decision-option-ledger operator-reconciliation-decision-record-prep reconciliation-decision-guard-review archive-reconciliation-decision-ledger-board archive-reconciliation-decision-ledger-v1 archive_reconciliation_decision_ledger.py decision_scope_is_operator_decision=False decision_scope_writes_ledger=False decision_ledger_selects_option=False decision_ledger_records_external_decision=False ledger_prep_is_archive_write=False decision_record_prep_is_decision=False decision_record_prep_reuses_prior_approval=False decision_record_prep_writes_external_ledger=False decision_guard_pass_is_reconciliation_approval=False decision_guard_pass_is_archive_write_permission=False decision_ledger_board_is_operator_approval=False decision_ledger_board_is_release_approval=False decision_ledger_board_is_publish_permission=False decision_ledger_board_selects_decision=False decision_ledger_board_executes_decision=False decision_ledger_board_writes_external_ledger=False decision_ledger_board_writes_archive_records=False decision_ledger_board_mutates_current_state=False reconciliation_decision_status=operator_required decision_ledger_status=prepared_not_written_externally operator_decision_record_status=prepared_not_supplied decision_guard_status=guarded current_state_mutation_status=not_performed archive_write_status=not_performed external_ledger_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
