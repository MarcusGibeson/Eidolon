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

IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
IMPORTED_ARCHIVE_CONFLICT_SCOPE_ID = "v591_imported_archive_conflict_scope_contract"
ARCHIVE_CONFLICT_CLASSIFICATION_MATRIX_ID = "v592_archive_conflict_classification_matrix"
CONFLICT_RECONCILIATION_OPTION_PACKET_ID = "v593_conflict_reconciliation_option_packet"
IMPORTED_ARCHIVE_CONFLICT_GUARD_REVIEW_ID = "v594_imported_archive_conflict_guard_review"
IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_BOARD_ID = "v595_imported_archive_conflict_reconciliation_board"

CONFLICT_SCOPE_FIELDS: tuple[str, ...] = (
    "version_identity",
    "arc_title",
    "release_history_entry",
    "readme_current_state_header",
    "workspace_project_metadata",
    "source_version_markers",
    "operator_closure_status",
    "verification_evidence_status",
    "package_privacy_status",
)

CONFLICT_CLASSIFICATIONS: tuple[str, ...] = (
    "historical_reference_allowed",
    "current_state_mismatch_blocked",
    "metadata_conflict",
    "release_history_conflict",
    "documentation_conflict",
    "operator_decision_conflict",
    "verification_evidence_conflict",
    "package_integrity_conflict",
    "unresolved_requires_operator_review",
)

RECONCILIATION_OPTIONS: tuple[str, ...] = (
    "accept_current_source_of_truth",
    "accept_imported_archive_as_historical_only",
    "request_manual_metadata_correction",
    "request_readme_release_history_review",
    "request_package_reverification",
    "block_import",
    "defer_reconciliation",
)

CONFLICT_GUARD_FIELDS: tuple[str, ...] = (
    "no_current_state_mutation_occurred",
    "no_archive_records_written",
    "no_release_decision_inferred",
    "no_prior_approval_reused",
    "no_stale_current_reference_accepted",
    "operator_review_remains_required",
)

CONFLICT_SCOPE_BOUNDARIES: dict[str, bool] = {
    "conflict_detection_is_correction": False,
    "imported_archive_data_is_current_state_authority": False,
    "conflict_scope_authorizes_source_edits": False,
    "conflict_scope_writes_archive_records": False,
    "conflict_scope_mutates_current_state": False,
    "conflict_scope_creates_release": False,
    "conflict_scope_publishes_release": False,
    "conflict_scope_runs_commands": False,
    "conflict_scope_applies_patches": False,
    "conflict_scope_executes_rollback": False,
    "conflict_scope_writes_source": False,
    "conflict_scope_writes_memory": False,
    "conflict_scope_expands_autonomy": False,
    "operator_review_required": True,
}

CONFLICT_CLASSIFICATION_BOUNDARIES: dict[str, bool] = {
    "conflict_classification_selects_fix": False,
    "severity_ranking_is_approval": False,
    "classification_writes_archive_records": False,
    "classification_mutates_current_state": False,
    "classification_creates_release": False,
    "classification_publishes_release": False,
    "classification_runs_commands": False,
    "classification_applies_patches": False,
    "classification_executes_rollback": False,
    "classification_writes_source": False,
    "classification_writes_memory": False,
    "classification_expands_autonomy": False,
    "operator_review_required": True,
}

RECONCILIATION_OPTION_BOUNDARIES: dict[str, bool] = {
    "reconciliation_options_execute_automatically": False,
    "recommended_option_is_operator_approval": False,
    "option_packet_writes_archive_records": False,
    "option_packet_mutates_current_state": False,
    "option_packet_creates_release": False,
    "option_packet_publishes_release": False,
    "option_packet_runs_commands": False,
    "option_packet_applies_patches": False,
    "option_packet_executes_rollback": False,
    "option_packet_writes_source": False,
    "option_packet_writes_memory": False,
    "option_packet_expands_autonomy": False,
    "operator_review_required": True,
}

CONFLICT_GUARD_BOUNDARIES: dict[str, bool] = {
    "conflict_guard_pass_is_reconciliation_approval": False,
    "guard_review_authorizes_import": False,
    "guard_review_writes_archive_records": False,
    "guard_review_mutates_current_state": False,
    "guard_review_creates_release": False,
    "guard_review_publishes_release": False,
    "guard_review_runs_commands": False,
    "guard_review_applies_patches": False,
    "guard_review_executes_rollback": False,
    "guard_review_writes_source": False,
    "guard_review_writes_memory": False,
    "guard_review_expands_autonomy": False,
    "operator_review_required": True,
}

IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_BOARD_BOUNDARIES: dict[str, bool] = {
    "conflict_board_is_release_approval": False,
    "conflict_board_is_publish_permission": False,
    "conflict_board_writes_archive_records": False,
    "conflict_board_mutates_current_state": False,
    "conflict_board_selects_reconciliation": False,
    "conflict_board_executes_reconciliation": False,
    "conflict_board_creates_release": False,
    "conflict_board_publishes_release": False,
    "conflict_board_executes_commands": False,
    "conflict_board_applies_patches": False,
    "conflict_board_executes_rollback": False,
    "conflict_board_writes_source": False,
    "conflict_board_writes_memory": False,
    "conflict_board_invokes_models_by_default": False,
    "conflict_board_schedules_work": False,
    "conflict_board_reuses_approval": False,
    "conflict_board_continues_automatically": False,
    "conflict_board_expands_autonomy": False,
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
        "archive_conflict_status": "detected_or_review_prepared",
        "conflict_classification_status": "matrix_prepared",
        "reconciliation_option_status": "prepared_for_operator",
        "conflict_guard_status": "guarded",
        "current_state_mutation_status": "not_performed",
        "archive_write_status": "not_performed",
        "archive_import_status": "prepared_not_written",
        "import_packet_status": "review_prepared",
        "closure_recall_status": "historical_review_prepared",
        "imported_archive_continuity_status": "guarded",
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
        "writes_external_archive": False,
        "modifies_live_files": False,
        "mutates_current_state": False,
        "executes_commands": False,
        "executes_rollback": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "selects_reconciliation": False,
        "executes_reconciliation": False,
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


def build_imported_archive_conflict_scope_contract(root: str | Path | None = None, conflict_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(CONFLICT_SCOPE_FIELDS, conflict_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("conflict-scope-schema-defined", len(CONFLICT_SCOPE_FIELDS) >= 9, "Imported archive conflict scope defines version, arc, release-history, README, metadata, source-marker, closure, evidence, and package-privacy conflict surfaces."),
        _row("missing-conflict-packet-awaits", len(missing) == len(CONFLICT_SCOPE_FIELDS), "With no operator conflict packet supplied, the layer remains prepared/read-only instead of correcting anything."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before conflict reconciliation review."),
        _row("detection-not-correction", CONFLICT_SCOPE_BOUNDARIES["conflict_detection_is_correction"] is False, "Conflict detection is not correction."),
        _row("imported-data-not-authority", CONFLICT_SCOPE_BOUNDARIES["imported_archive_data_is_current_state_authority"] is False, "Imported archive data is not current-state authority."),
        _row("no-authority", all(CONFLICT_SCOPE_BOUNDARIES[key] is False for key in ["conflict_scope_authorizes_source_edits", "conflict_scope_writes_archive_records", "conflict_scope_mutates_current_state", "conflict_scope_creates_release", "conflict_scope_publishes_release", "conflict_scope_runs_commands", "conflict_scope_applies_patches", "conflict_scope_executes_rollback", "conflict_scope_writes_source", "conflict_scope_writes_memory", "conflict_scope_expands_autonomy"]), "Conflict scope grants no source edit, archive write, current-state mutation, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION,
        "state": "imported_archive_conflict_scope_contract_review_only",
        "imported_archive_conflict_scope_id": IMPORTED_ARCHIVE_CONFLICT_SCOPE_ID,
        "required_fields": list(CONFLICT_SCOPE_FIELDS),
        "missing_fields": missing,
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CONFLICT_SCOPE_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_archive_conflict_classification_matrix(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_imported_archive_conflict_scope_contract(repo)
    rows = [
        _row("scope-ready", scope.get("ok") is True, "Imported archive conflict scope contract is available."),
        _row("classification-matrix-defined", len(CONFLICT_CLASSIFICATIONS) >= 9, "Conflict classification matrix covers historical references, stale-current blockers, metadata, release history, documentation, operator decision, verification evidence, package integrity, and unresolved operator review."),
        _row("classification-not-fix", CONFLICT_CLASSIFICATION_BOUNDARIES["conflict_classification_selects_fix"] is False, "Conflict classification does not select a fix."),
        _row("severity-not-approval", CONFLICT_CLASSIFICATION_BOUNDARIES["severity_ranking_is_approval"] is False, "Severity ranking is not approval."),
        _row("no-mutation", CONFLICT_CLASSIFICATION_BOUNDARIES["classification_writes_archive_records"] is False and CONFLICT_CLASSIFICATION_BOUNDARIES["classification_mutates_current_state"] is False, "Classification does not write archive records or mutate current state."),
        _row("no-authority", all(CONFLICT_CLASSIFICATION_BOUNDARIES[key] is False for key in ["classification_creates_release", "classification_publishes_release", "classification_runs_commands", "classification_applies_patches", "classification_executes_rollback", "classification_writes_source", "classification_writes_memory", "classification_expands_autonomy"]), "Classification grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION,
        "state": "archive_conflict_classification_matrix_review_only",
        "archive_conflict_classification_matrix_id": ARCHIVE_CONFLICT_CLASSIFICATION_MATRIX_ID,
        "classifications": list(CONFLICT_CLASSIFICATIONS),
        "scope_contract": {"ok": scope.get("ok"), "state": scope.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CONFLICT_CLASSIFICATION_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_conflict_reconciliation_option_packet(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    matrix = build_archive_conflict_classification_matrix(repo)
    rows = [
        _row("classification-ready", matrix.get("ok") is True, "Archive conflict classification matrix is available."),
        _row("options-defined", len(RECONCILIATION_OPTIONS) >= 7, "Reconciliation options include accepting current source of truth, treating imports as historical-only, requesting manual correction/review/reverification, blocking import, or deferring."),
        _row("options-not-execution", RECONCILIATION_OPTION_BOUNDARIES["reconciliation_options_execute_automatically"] is False, "Reconciliation options are not executed automatically."),
        _row("recommendation-not-approval", RECONCILIATION_OPTION_BOUNDARIES["recommended_option_is_operator_approval"] is False, "Recommended option is not operator approval."),
        _row("no-write", RECONCILIATION_OPTION_BOUNDARIES["option_packet_writes_archive_records"] is False and RECONCILIATION_OPTION_BOUNDARIES["option_packet_mutates_current_state"] is False, "Option packet does not write archive records or mutate current state."),
        _row("no-authority", all(RECONCILIATION_OPTION_BOUNDARIES[key] is False for key in ["option_packet_creates_release", "option_packet_publishes_release", "option_packet_runs_commands", "option_packet_applies_patches", "option_packet_executes_rollback", "option_packet_writes_source", "option_packet_writes_memory", "option_packet_expands_autonomy"]), "Option packet grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION,
        "state": "conflict_reconciliation_option_packet_review_only",
        "conflict_reconciliation_option_packet_id": CONFLICT_RECONCILIATION_OPTION_PACKET_ID,
        "options": list(RECONCILIATION_OPTIONS),
        "classification_matrix": {"ok": matrix.get("ok"), "state": matrix.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RECONCILIATION_OPTION_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_imported_archive_conflict_guard_review(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    options = build_conflict_reconciliation_option_packet(repo)
    release_audit = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("options-ready", options.get("ok") is True, "Conflict reconciliation option packet is available."),
        _row("guard-fields-defined", len(CONFLICT_GUARD_FIELDS) >= 6, "Conflict guard verifies no current-state mutation, archive write, release decision inference, approval reuse, stale-current acceptance, and continued operator review."),
        _row("release-audit-clean", release_audit.get("ok") is True, "Release staleness and verification audit board is clean for the current release."),
        _row("guard-not-approval", CONFLICT_GUARD_BOUNDARIES["conflict_guard_pass_is_reconciliation_approval"] is False, "Conflict guard pass is not reconciliation approval."),
        _row("guard-not-import", CONFLICT_GUARD_BOUNDARIES["guard_review_authorizes_import"] is False, "Guard review does not authorize import."),
        _row("no-authority", all(CONFLICT_GUARD_BOUNDARIES[key] is False for key in ["guard_review_writes_archive_records", "guard_review_mutates_current_state", "guard_review_creates_release", "guard_review_publishes_release", "guard_review_runs_commands", "guard_review_applies_patches", "guard_review_executes_rollback", "guard_review_writes_source", "guard_review_writes_memory", "guard_review_expands_autonomy"]), "Conflict guard grants no archive write, current-state mutation, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION,
        "state": "imported_archive_conflict_guard_review_review_only",
        "imported_archive_conflict_guard_review_id": IMPORTED_ARCHIVE_CONFLICT_GUARD_REVIEW_ID,
        "guard_fields": list(CONFLICT_GUARD_FIELDS),
        "option_packet": {"ok": options.get("ok"), "state": options.get("state")},
        "release_audit": {"ok": release_audit.get("ok"), "state": release_audit.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CONFLICT_GUARD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_imported_archive_conflict_reconciliation_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_imported_archive_conflict_scope_contract(repo)
    matrix = build_archive_conflict_classification_matrix(repo)
    options = build_conflict_reconciliation_option_packet(repo)
    guard = build_imported_archive_conflict_guard_review(repo)
    rows = [
        _row("conflict-scope", scope.get("ok") is True, "Imported archive conflict scope contract is prepared."),
        _row("classification-matrix", matrix.get("ok") is True and matrix.get("conflict_classification_status") == "matrix_prepared", "Archive conflict classification matrix is prepared."),
        _row("reconciliation-options", options.get("ok") is True and options.get("reconciliation_option_status") == "prepared_for_operator", "Conflict reconciliation options are prepared for operator review."),
        _row("conflict-guard", guard.get("ok") is True and guard.get("conflict_guard_status") == "guarded", "Imported archive conflict guard review is prepared."),
        _row("no-write-or-mutation", all(report.get("writes_records") is False and report.get("writes_archive_records") is False and report.get("mutates_current_state") is False for report in [scope, matrix, options, guard]), "No stage writes archive records or mutates current state."),
        _row("no-reconciliation-execution", all(report.get("selects_reconciliation") is False and report.get("executes_reconciliation") is False for report in [scope, matrix, options, guard]), "No stage selects or executes reconciliation automatically."),
        _row("no-release-publish", all(report.get("creates_release") is False and report.get("publishes_release") is False for report in [scope, matrix, options, guard]), "No stage creates or publishes releases."),
        _row("no-execution", all(report.get("executes_commands") is False and report.get("applies_patch") is False and report.get("executes_rollback") is False for report in [scope, matrix, options, guard]), "No stage runs commands, applies patches, or executes rollback."),
        _row("no-source-memory-autonomy", all(report.get("writes_source") is False and report.get("writes_memory") is False and report.get("expands_autonomy") is False for report in [scope, matrix, options, guard]), "No stage writes source, writes memory, or expands autonomy."),
        _row("board-no-authority", all(IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_BOARD_BOUNDARIES[key] is False for key in ["conflict_board_is_release_approval", "conflict_board_is_publish_permission", "conflict_board_writes_archive_records", "conflict_board_mutates_current_state", "conflict_board_selects_reconciliation", "conflict_board_executes_reconciliation", "conflict_board_creates_release", "conflict_board_publishes_release", "conflict_board_executes_commands", "conflict_board_applies_patches", "conflict_board_executes_rollback", "conflict_board_writes_source", "conflict_board_writes_memory", "conflict_board_invokes_models_by_default", "conflict_board_schedules_work", "conflict_board_reuses_approval", "conflict_board_continues_automatically", "conflict_board_expands_autonomy"]), "Final conflict reconciliation board grants no approval, publishing, archive write, mutation, reconciliation execution, release, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION,
        "state": "imported_archive_conflict_reconciliation_board_review_only",
        "imported_archive_conflict_reconciliation_board_id": IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_BOARD_ID,
        "targeted_smoke": TARGETED_SMOKE,
        "current_version": CURRENT_VERSION,
        "current_version_tag": CURRENT_VERSION_TAG,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "generated_at": _now_iso(),
        "stages": {
            "scope": scope,
            "classification": matrix,
            "options": options,
            "guard": guard,
        },
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_BOARD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


_STAGE_BUILDERS = {
    "imported_archive_conflict_scope_contract_v1": build_imported_archive_conflict_scope_contract,
    "archive_conflict_classification_matrix_v1": build_archive_conflict_classification_matrix,
    "conflict_reconciliation_option_packet_v1": build_conflict_reconciliation_option_packet,
    "imported_archive_conflict_guard_review_v1": build_imported_archive_conflict_guard_review,
    "imported_archive_conflict_reconciliation_board_v1": build_imported_archive_conflict_reconciliation_board,
}


def build_imported_archive_conflict_reconciliation_arc(root: str | Path | None = None, stage: str = "imported_archive_conflict_reconciliation_board_v1") -> dict[str, Any]:
    builder = _STAGE_BUILDERS.get(stage, build_imported_archive_conflict_reconciliation_board)
    return builder(root)


def render_imported_archive_conflict_reconciliation_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"Imported Archive Conflict Reconciliation v1 ({report.get('version', IMPORTED_ARCHIVE_CONFLICT_RECONCILIATION_VERSION)})",
        f"state: {report.get('state', 'unknown')}",
        f"status: {report.get('status', 'unknown')} ok={report.get('ok')}",
        f"archive_conflict_status: {report.get('archive_conflict_status', 'detected_or_review_prepared')}",
        f"conflict_classification_status: {report.get('conflict_classification_status', 'matrix_prepared')}",
        f"reconciliation_option_status: {report.get('reconciliation_option_status', 'prepared_for_operator')}",
        f"conflict_guard_status: {report.get('conflict_guard_status', 'guarded')}",
        f"current_state_mutation_status: {report.get('current_state_mutation_status', 'not_performed')}",
        f"archive_write_status: {report.get('archive_write_status', 'not_performed')}",
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


# v591.0-v595.0 imported archive conflict reconciliation tokens: imported-archive-conflict-scope-contract archive-conflict-classification-matrix conflict-reconciliation-option-packet imported-archive-conflict-guard-review imported-archive-conflict-reconciliation-board imported-archive-conflict-reconciliation-v1 imported_archive_conflict_reconciliation.py conflict_detection_is_correction=False imported_archive_data_is_current_state_authority=False conflict_scope_authorizes_source_edits=False conflict_classification_selects_fix=False severity_ranking_is_approval=False reconciliation_options_execute_automatically=False recommended_option_is_operator_approval=False conflict_guard_pass_is_reconciliation_approval=False guard_review_authorizes_import=False conflict_board_is_release_approval=False conflict_board_is_publish_permission=False conflict_board_writes_archive_records=False conflict_board_mutates_current_state=False conflict_board_selects_reconciliation=False conflict_board_executes_reconciliation=False archive_conflict_status=detected_or_review_prepared conflict_classification_status=matrix_prepared reconciliation_option_status=prepared_for_operator conflict_guard_status=guarded current_state_mutation_status=not_performed archive_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
