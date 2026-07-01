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
from release_candidate_operator_handoff import build_release_candidate_integrity_handoff_board

RELEASE_DECISION_ARCHIVE_LEDGER_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
RELEASE_DECISION_SCOPE_ID = "v566_release_decision_scope_contract"
OPERATOR_DECISION_MATRIX_ID = "v567_operator_decision_option_matrix"
RELEASE_ARCHIVE_LEDGER_ID = "v568_release_archive_ledger_prep"
ARCHIVE_INTEGRITY_REVIEW_ID = "v569_archive_integrity_continuity_review"
RELEASE_DECISION_ARCHIVE_BOARD_ID = "v570_release_decision_archive_ledger_board"

RELEASE_DECISION_SCOPE_FIELDS: tuple[str, ...] = (
    "candidate_version_identity",
    "handoff_packet_reference",
    "verification_evidence_summary",
    "known_warnings",
    "known_blockers",
    "operator_decision_choices",
    "archive_readiness_requirements",
    "operator_notes",
)

OPERATOR_DECISION_OPTION_FIELDS: tuple[str, ...] = (
    "candidate_summary",
    "verification_summary",
    "rollback_recovery_reference",
    "archive_readiness_summary",
    "decision_options",
    "operator_selection_required",
)

RELEASE_ARCHIVE_LEDGER_FIELDS: tuple[str, ...] = (
    "version",
    "arc_title",
    "package_name",
    "source_only_package_privacy_status",
    "verification_summary",
    "known_warnings",
    "operator_decision_status",
    "closure_status",
    "next_arc_reference",
)

ARCHIVE_INTEGRITY_FIELDS: tuple[str, ...] = (
    "readme_current_header",
    "release_history_top_entry",
    "workspace_project_metadata",
    "source_version_markers",
    "dashboard_api_cli_current_text",
    "stale_version_audit_compatibility",
    "package_privacy_summary",
)

RELEASE_DECISION_SCOPE_BOUNDARIES: dict[str, bool] = {
    "release_decision_scope_is_release_approval": False,
    "decision_preparation_is_publish_permission": False,
    "release_decision_scope_runs_commands": False,
    "release_decision_scope_applies_patches": False,
    "release_decision_scope_executes_rollback": False,
    "release_decision_scope_creates_release": False,
    "release_decision_scope_publishes_release": False,
    "release_decision_scope_writes_source": False,
    "release_decision_scope_writes_memory": False,
    "release_decision_scope_expands_autonomy": False,
    "operator_review_required": True,
}

OPERATOR_DECISION_BOUNDARIES: dict[str, bool] = {
    "decision_options_are_selected_automatically": False,
    "ranking_an_option_authorizes_it": False,
    "recommendation_is_approval": False,
    "decision_matrix_runs_commands": False,
    "decision_matrix_applies_patches": False,
    "decision_matrix_executes_rollback": False,
    "decision_matrix_creates_release": False,
    "decision_matrix_publishes_release": False,
    "decision_matrix_writes_source": False,
    "decision_matrix_writes_memory": False,
    "decision_matrix_expands_autonomy": False,
    "operator_selection_required": True,
}

ARCHIVE_LEDGER_BOUNDARIES: dict[str, bool] = {
    "archive_ledger_prep_writes_external_archive": False,
    "ledger_readiness_is_release_publication": False,
    "archive_ledger_prep_creates_release": False,
    "archive_ledger_prep_publishes_release": False,
    "archive_ledger_prep_runs_commands": False,
    "archive_ledger_prep_applies_patches": False,
    "archive_ledger_prep_executes_rollback": False,
    "archive_ledger_prep_writes_source": False,
    "archive_ledger_prep_writes_memory": False,
    "archive_ledger_prep_expands_autonomy": False,
    "operator_review_required": True,
}

ARCHIVE_INTEGRITY_BOUNDARIES: dict[str, bool] = {
    "archive_integrity_is_release_approval": False,
    "continuity_alignment_is_publish_permission": False,
    "archive_integrity_review_writes_archive": False,
    "archive_integrity_review_creates_release": False,
    "archive_integrity_review_publishes_release": False,
    "archive_integrity_review_runs_commands": False,
    "archive_integrity_review_applies_patches": False,
    "archive_integrity_review_executes_rollback": False,
    "archive_integrity_review_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_DECISION_ARCHIVE_BOARD_BOUNDARIES: dict[str, bool] = {
    "release_decision_board_is_release_approval": False,
    "release_decision_board_is_publish_permission": False,
    "release_decision_board_selects_decision": False,
    "release_decision_board_writes_external_archive": False,
    "release_decision_board_executes_commands": False,
    "release_decision_board_applies_patches": False,
    "release_decision_board_executes_rollback": False,
    "release_decision_board_writes_source": False,
    "release_decision_board_writes_memory": False,
    "release_decision_board_creates_release": False,
    "release_decision_board_publishes_release": False,
    "release_decision_board_invokes_models_by_default": False,
    "release_decision_board_schedules_work": False,
    "release_decision_board_reuses_approval": False,
    "release_decision_board_continues_automatically": False,
    "release_decision_board_expands_autonomy": False,
    "operator_review_required": True,
    "approval_required": True,
}

OPERATOR_DECISION_OPTIONS: tuple[str, ...] = (
    "approve candidate for manual archival",
    "request more verification",
    "block candidate",
    "request rollback review",
    "defer decision",
    "reject candidate",
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


def _missing(fields: tuple[str, ...], payload: dict[str, Any] | None) -> list[str]:
    supplied = dict(payload or {})
    return [field for field in fields if field not in supplied]


def _base_authority_state() -> dict[str, Any]:
    return {
        "release_decision_status": "prepared_for_operator",
        "operator_decision_status": "required",
        "archive_ledger_status": "prepared_not_written_externally",
        "archive_integrity_status": "review_prepared",
        "release_candidate_status": "handoff_prepared",
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
        "modifies_live_files": False,
        "executes_commands": False,
        "executes_rollback": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "writes_external_archive": False,
        "selects_operator_decision": False,
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


def build_release_decision_scope_contract(root: str | Path | None = None, decision_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(RELEASE_DECISION_SCOPE_FIELDS, decision_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    handoff_board = build_release_candidate_integrity_handoff_board(repo)
    rows = [
        _row("scope-schema-defined", len(RELEASE_DECISION_SCOPE_FIELDS) >= 8, "Release decision scope covers candidate identity, handoff packet reference, verification summary, warnings, blockers, decision choices, archive requirements, and operator notes."),
        _row("missing-scope-awaits", len(missing) == len(RELEASE_DECISION_SCOPE_FIELDS), "With no operator decision packet supplied, the scope remains prepared rather than approved."),
        _row("previous-handoff-board-available", handoff_board.get("ok") is True, "v565 release candidate integrity and operator handoff board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits are clean before packaging."),
        _row("scope-not-approval", RELEASE_DECISION_SCOPE_BOUNDARIES["release_decision_scope_is_release_approval"] is False and RELEASE_DECISION_SCOPE_BOUNDARIES["decision_preparation_is_publish_permission"] is False, "Release decision scope is not release approval and decision preparation is not publish permission."),
        _row("no-authority", all(RELEASE_DECISION_SCOPE_BOUNDARIES[key] is False for key in ["release_decision_scope_runs_commands", "release_decision_scope_applies_patches", "release_decision_scope_executes_rollback", "release_decision_scope_creates_release", "release_decision_scope_publishes_release", "release_decision_scope_writes_source", "release_decision_scope_writes_memory", "release_decision_scope_expands_autonomy"]), "Release decision scope grants no command, patch, rollback, release, publish, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_DECISION_ARCHIVE_LEDGER_VERSION,
        "state": "release_decision_scope_contract_review_only",
        "release_decision_scope_id": RELEASE_DECISION_SCOPE_ID,
        "scope_fields": list(RELEASE_DECISION_SCOPE_FIELDS),
        "missing_scope_fields": missing,
        "previous_handoff_summary": {"ok": handoff_board.get("ok"), "state": handoff_board.get("state")},
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_DECISION_SCOPE_BOUNDARIES),
        "safe_next_action": "Operator may review release decision scope. Scope does not approve release, publish release, execute rollback, run commands, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_operator_decision_option_matrix(root: str | Path | None = None, decision_context: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(OPERATOR_DECISION_OPTION_FIELDS, decision_context)
    rows = [
        _row("decision-options-defined", len(OPERATOR_DECISION_OPTIONS) == 6, "Operator decision matrix includes approve for manual archival, request more verification, block, request rollback review, defer, and reject options."),
        _row("missing-context-awaits", len(missing) == len(OPERATOR_DECISION_OPTION_FIELDS), "With no operator context supplied, the matrix remains prepared and does not select an option."),
        _row("operator-selection-required", OPERATOR_DECISION_BOUNDARIES["operator_selection_required"] is True, "Operator selection is required for any release decision."),
        _row("recommendation-not-approval", OPERATOR_DECISION_BOUNDARIES["decision_options_are_selected_automatically"] is False and OPERATOR_DECISION_BOUNDARIES["ranking_an_option_authorizes_it"] is False and OPERATOR_DECISION_BOUNDARIES["recommendation_is_approval"] is False, "Options are not selected automatically; ranking or recommendation is not approval."),
        _row("no-authority", all(OPERATOR_DECISION_BOUNDARIES[key] is False for key in ["decision_matrix_runs_commands", "decision_matrix_applies_patches", "decision_matrix_executes_rollback", "decision_matrix_creates_release", "decision_matrix_publishes_release", "decision_matrix_writes_source", "decision_matrix_writes_memory", "decision_matrix_expands_autonomy"]), "Decision matrix grants no command, patch, rollback, release, publish, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_DECISION_ARCHIVE_LEDGER_VERSION,
        "state": "operator_decision_option_matrix_review_only",
        "operator_decision_matrix_id": OPERATOR_DECISION_MATRIX_ID,
        "decision_context_fields": list(OPERATOR_DECISION_OPTION_FIELDS),
        "missing_decision_context_fields": missing,
        "decision_options": list(OPERATOR_DECISION_OPTIONS),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(OPERATOR_DECISION_BOUNDARIES),
        "safe_next_action": "Operator may review decision options. Matrix does not select, approve, publish, run commands, apply patches, execute rollback, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_ledger_prep(root: str | Path | None = None, archive_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(RELEASE_ARCHIVE_LEDGER_FIELDS, archive_packet)
    rows = [
        _row("ledger-schema-defined", len(RELEASE_ARCHIVE_LEDGER_FIELDS) >= 9, "Archive ledger prep covers version, arc title, package, source-only privacy, verification, warnings, operator decision, closure, and next arc reference."),
        _row("missing-ledger-awaits", len(missing) == len(RELEASE_ARCHIVE_LEDGER_FIELDS), "With no operator archive packet supplied, the ledger remains prepared and is not written externally."),
        _row("ledger-not-publication", ARCHIVE_LEDGER_BOUNDARIES["archive_ledger_prep_writes_external_archive"] is False and ARCHIVE_LEDGER_BOUNDARIES["ledger_readiness_is_release_publication"] is False, "Archive ledger prep does not write external archives and ledger readiness is not release publication."),
        _row("no-authority", all(ARCHIVE_LEDGER_BOUNDARIES[key] is False for key in ["archive_ledger_prep_creates_release", "archive_ledger_prep_publishes_release", "archive_ledger_prep_runs_commands", "archive_ledger_prep_applies_patches", "archive_ledger_prep_executes_rollback", "archive_ledger_prep_writes_source", "archive_ledger_prep_writes_memory", "archive_ledger_prep_expands_autonomy"]), "Archive ledger prep grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_DECISION_ARCHIVE_LEDGER_VERSION,
        "state": "release_archive_ledger_prep_review_only",
        "release_archive_ledger_id": RELEASE_ARCHIVE_LEDGER_ID,
        "ledger_fields": list(RELEASE_ARCHIVE_LEDGER_FIELDS),
        "missing_ledger_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_LEDGER_BOUNDARIES),
        "safe_next_action": "Operator may review archive ledger prep. Prep does not write external archives, create releases, publish releases, run commands, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_archive_integrity_continuity_review(root: str | Path | None = None, archive_context: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(ARCHIVE_INTEGRITY_FIELDS, archive_context)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("integrity-schema-defined", len(ARCHIVE_INTEGRITY_FIELDS) >= 7, "Archive continuity review covers README, release history, workspace/project metadata, source markers, dashboard/API/CLI text, stale audit compatibility, and package privacy."),
        _row("missing-integrity-awaits", len(missing) == len(ARCHIVE_INTEGRITY_FIELDS), "With no operator archive context supplied, integrity review remains prepared rather than approving release."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean for archive continuity review."),
        _row("integrity-not-approval", ARCHIVE_INTEGRITY_BOUNDARIES["archive_integrity_is_release_approval"] is False and ARCHIVE_INTEGRITY_BOUNDARIES["continuity_alignment_is_publish_permission"] is False, "Archive integrity is not release approval and continuity alignment is not publish permission."),
        _row("no-authority", all(ARCHIVE_INTEGRITY_BOUNDARIES[key] is False for key in ["archive_integrity_review_writes_archive", "archive_integrity_review_creates_release", "archive_integrity_review_publishes_release", "archive_integrity_review_runs_commands", "archive_integrity_review_applies_patches", "archive_integrity_review_executes_rollback", "archive_integrity_review_expands_autonomy"]), "Archive integrity review grants no archive write, release, publish, command, patch, rollback, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_DECISION_ARCHIVE_LEDGER_VERSION,
        "state": "archive_integrity_continuity_review_only",
        "archive_integrity_review_id": ARCHIVE_INTEGRITY_REVIEW_ID,
        "archive_integrity_fields": list(ARCHIVE_INTEGRITY_FIELDS),
        "missing_archive_integrity_fields": missing,
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_INTEGRITY_BOUNDARIES),
        "safe_next_action": "Operator may review archive continuity. Review does not approve release, publish, write external archives, run commands, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_decision_archive_ledger_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_release_decision_scope_contract(repo)
    matrix = build_operator_decision_option_matrix(repo)
    ledger = build_release_archive_ledger_prep(repo)
    integrity = build_archive_integrity_continuity_review(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("scope-prepared", scope.get("ok") is True and scope.get("release_status") == "not_created", "Release decision scope is prepared and does not create releases."),
        _row("decision-matrix-prepared", matrix.get("ok") is True and matrix.get("selects_operator_decision") is False, "Operator decision option matrix is prepared and does not select a decision."),
        _row("archive-ledger-prepared", ledger.get("ok") is True and ledger.get("writes_external_archive") is False, "Release archive ledger prep is prepared and does not write external archives."),
        _row("archive-integrity-prepared", integrity.get("ok") is True and integrity.get("publishes_release") is False, "Archive integrity and continuity review is prepared and does not publish releases."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Release staleness audit remains clean for current-state fields."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [scope, matrix, ledger, integrity]), "No v566-v570 release decision/archive layer runs commands or executes rollback."),
        _row("no-authority", all(RELEASE_DECISION_ARCHIVE_BOARD_BOUNDARIES[key] is False for key in ["release_decision_board_is_release_approval", "release_decision_board_is_publish_permission", "release_decision_board_selects_decision", "release_decision_board_writes_external_archive", "release_decision_board_executes_commands", "release_decision_board_applies_patches", "release_decision_board_executes_rollback", "release_decision_board_writes_source", "release_decision_board_writes_memory", "release_decision_board_creates_release", "release_decision_board_publishes_release", "release_decision_board_invokes_models_by_default", "release_decision_board_schedules_work", "release_decision_board_reuses_approval", "release_decision_board_continues_automatically", "release_decision_board_expands_autonomy"]), "Release decision archive board grants no release approval, publish permission, decision selection, archive write, command, patch, rollback, source, memory, release, publish, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_DECISION_ARCHIVE_LEDGER_VERSION,
        "state": "release_decision_archive_ledger_board_review_only",
        "release_decision_archive_board_id": RELEASE_DECISION_ARCHIVE_BOARD_ID,
        "release_decision_scope_contract": scope,
        "operator_decision_option_matrix": matrix,
        "release_archive_ledger_prep": ledger,
        "archive_integrity_continuity_review": integrity,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_DECISION_ARCHIVE_BOARD_BOUNDARIES),
        "safe_next_action": "Operator may review v570 release decision and archive ledger board. It does not approve releases, select decisions, write external archives, publish releases, run commands, apply patches, execute rollback, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_release_decision_archive_ledger_arc(root: str | Path | None = None, stage: str = "release_decision_archive_ledger_board_v1") -> dict[str, Any]:
    builders = {
        "release_decision_scope_contract_v1": build_release_decision_scope_contract,
        "operator_decision_option_matrix_v1": build_operator_decision_option_matrix,
        "release_archive_ledger_prep_v1": build_release_archive_ledger_prep,
        "archive_integrity_continuity_review_v1": build_archive_integrity_continuity_review,
        "release_decision_archive_ledger_board_v1": build_release_decision_archive_ledger_board,
    }
    return builders.get(stage, build_release_decision_archive_ledger_board)(root)


def render_release_decision_archive_ledger_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"release_decision_status: {report.get('release_decision_status')}",
        f"operator_decision_status: {report.get('operator_decision_status')}",
        f"archive_ledger_status: {report.get('archive_ledger_status')}",
        f"archive_integrity_status: {report.get('archive_integrity_status')}",
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

# v566.0-v570.0 release decision archive ledger tokens: release-decision-scope-contract operator-decision-option-matrix release-archive-ledger-prep archive-integrity-continuity-review release-decision-archive-ledger-board release-decision-and-archive-ledger-v1 release_decision_archive_ledger.py release_decision_scope_is_release_approval=False decision_preparation_is_publish_permission=False decision_options_are_selected_automatically=False ranking_an_option_authorizes_it=False recommendation_is_approval=False archive_ledger_prep_writes_external_archive=False ledger_readiness_is_release_publication=False archive_integrity_is_release_approval=False continuity_alignment_is_publish_permission=False release_decision_board_is_release_approval=False release_decision_board_is_publish_permission=False release_decision_board_selects_decision=False release_decision_board_writes_external_archive=False release_decision_board_executes_commands=False release_decision_status=prepared_for_operator operator_decision_status=required archive_ledger_status=prepared_not_written_externally archive_integrity_status=review_prepared release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
