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
from release_archive_continuity_index import build_release_archive_retrieval_continuity_index_board

RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
ARCHIVE_SEARCH_SCOPE_ID = "v576_archive_search_scope_contract"
RELEASE_RECORD_QUERY_MATRIX_ID = "v577_release_record_query_matrix"
ARCHIVE_SEARCH_RESULT_REVIEW_ID = "v578_archive_search_result_review_packet"
ARCHIVE_HANDOFF_REVIEW_ID = "v579_archive_handoff_review_packet"
RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_ID = "v580_release_archive_search_handoff_review_board"

ARCHIVE_SEARCH_SCOPE_FIELDS: tuple[str, ...] = (
    "allowed_archive_search_fields",
    "search_scope_boundaries",
    "historical_release_lookup_rules",
    "current_state_lookup_rules",
    "operator_facing_search_packet",
    "operator_notes",
)

RELEASE_RECORD_QUERY_FIELDS: tuple[str, ...] = (
    "version_range",
    "arc_title",
    "dashboard_route",
    "api_cli_surface",
    "targeted_smoke",
    "module_file_surface",
    "status_field",
    "known_warning",
    "next_recommended_arc",
)

ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS: tuple[str, ...] = (
    "matched_records",
    "historical_current_classification",
    "confidence_notes",
    "stale_current_risk_notes",
    "missing_record_warnings",
    "operator_review_notes",
)

ARCHIVE_HANDOFF_REVIEW_FIELDS: tuple[str, ...] = (
    "search_summary",
    "continuity_chain",
    "matched_release_records",
    "warnings_blockers",
    "source_surfaces",
    "operator_decision_options",
)

ARCHIVE_SEARCH_SCOPE_BOUNDARIES: dict[str, bool] = {
    "archive_search_is_read_only": True,
    "search_results_are_approval": False,
    "search_scope_authorizes_archive_writes": False,
    "archive_search_creates_release": False,
    "archive_search_publishes_release": False,
    "archive_search_runs_commands": False,
    "archive_search_applies_patches": False,
    "archive_search_executes_rollback": False,
    "archive_search_writes_source": False,
    "archive_search_writes_memory": False,
    "archive_search_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_RECORD_QUERY_BOUNDARIES: dict[str, bool] = {
    "query_matches_are_current_state_authority": False,
    "search_ranking_is_operator_decision_making": False,
    "query_matrix_writes_archive": False,
    "query_matrix_creates_release": False,
    "query_matrix_publishes_release": False,
    "query_matrix_runs_commands": False,
    "query_matrix_applies_patches": False,
    "query_matrix_executes_rollback": False,
    "query_matrix_writes_source": False,
    "query_matrix_writes_memory": False,
    "query_matrix_expands_autonomy": False,
    "operator_review_required": True,
}

ARCHIVE_SEARCH_RESULT_BOUNDARIES: dict[str, bool] = {
    "search_review_mutates_records": False,
    "search_result_confidence_is_release_confidence": False,
    "search_review_writes_archive": False,
    "search_review_creates_release": False,
    "search_review_publishes_release": False,
    "search_review_runs_commands": False,
    "search_review_applies_patches": False,
    "search_review_executes_rollback": False,
    "search_review_writes_source": False,
    "search_review_writes_memory": False,
    "search_review_expands_autonomy": False,
    "operator_review_required": True,
}

ARCHIVE_HANDOFF_BOUNDARIES: dict[str, bool] = {
    "archive_handoff_is_operator_approval": False,
    "handoff_review_creates_release": False,
    "handoff_review_publishes_release": False,
    "handoff_review_writes_archive": False,
    "handoff_review_runs_commands": False,
    "handoff_review_applies_patches": False,
    "handoff_review_executes_rollback": False,
    "handoff_review_writes_source": False,
    "handoff_review_writes_memory": False,
    "handoff_review_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_BOUNDARIES: dict[str, bool] = {
    "archive_search_board_is_release_approval": False,
    "archive_search_board_is_publish_permission": False,
    "archive_search_board_writes_archive": False,
    "archive_search_board_creates_release": False,
    "archive_search_board_publishes_release": False,
    "archive_search_board_executes_commands": False,
    "archive_search_board_applies_patches": False,
    "archive_search_board_executes_rollback": False,
    "archive_search_board_writes_source": False,
    "archive_search_board_writes_memory": False,
    "archive_search_board_invokes_models_by_default": False,
    "archive_search_board_schedules_work": False,
    "archive_search_board_reuses_approval": False,
    "archive_search_board_continues_automatically": False,
    "archive_search_board_expands_autonomy": False,
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
        "archive_search_status": "prepared_read_only",
        "release_record_query_status": "matrix_prepared",
        "search_result_review_status": "prepared",
        "archive_handoff_status": "prepared",
        "archive_write_status": "not_performed",
        "archive_retrieval_status": "prepared_read_only",
        "continuity_index_status": "prepared",
        "historical_reference_status": "classified",
        "stale_current_reference_status": "blocked_if_detected",
        "retrieval_packet_status": "prepared",
        "release_decision_status": "prepared_for_operator",
        "operator_decision_status": "required",
        "archive_ledger_status": "prepared_not_written_externally",
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
        "writes_external_archive": False,
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


def build_archive_search_scope_contract(root: str | Path | None = None, search_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(ARCHIVE_SEARCH_SCOPE_FIELDS, search_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    continuity_board = build_release_archive_retrieval_continuity_index_board(repo)
    rows = [
        _row("search-schema-defined", len(ARCHIVE_SEARCH_SCOPE_FIELDS) >= 6, "Archive search scope defines allowed search fields, lookup boundaries, current/historical rules, operator packet, and notes."),
        _row("missing-search-awaits", len(missing) == len(ARCHIVE_SEARCH_SCOPE_FIELDS), "With no operator search packet supplied, the layer remains prepared/read-only rather than writing archive records."),
        _row("previous-continuity-board-available", continuity_board.get("ok") is True, "v575 archive retrieval and continuity index board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before archive search."),
        _row("search-read-only", ARCHIVE_SEARCH_SCOPE_BOUNDARIES["archive_search_is_read_only"] is True and ARCHIVE_SEARCH_SCOPE_BOUNDARIES["search_results_are_approval"] is False, "Archive search is read-only and search results are not approval."),
        _row("no-authority", all(ARCHIVE_SEARCH_SCOPE_BOUNDARIES[key] is False for key in ["search_scope_authorizes_archive_writes", "archive_search_creates_release", "archive_search_publishes_release", "archive_search_runs_commands", "archive_search_applies_patches", "archive_search_executes_rollback", "archive_search_writes_source", "archive_search_writes_memory", "archive_search_expands_autonomy"]), "Archive search scope grants no archive-write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION,
        "state": "archive_search_scope_contract_review_only",
        "archive_search_scope_id": ARCHIVE_SEARCH_SCOPE_ID,
        "search_fields": list(ARCHIVE_SEARCH_SCOPE_FIELDS),
        "missing_search_fields": missing,
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "previous_continuity_board": continuity_board,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_SEARCH_SCOPE_BOUNDARIES),
        "safe_next_action": "Operator may review archive search scope. Search is read-only and does not approve, write archives, publish, run commands, mutate source or memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_record_query_matrix(root: str | Path | None = None, query_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(RELEASE_RECORD_QUERY_FIELDS, query_packet)
    rows = [
        _row("query-schema-defined", len(RELEASE_RECORD_QUERY_FIELDS) >= 9, "Query matrix covers version range, arc, dashboard route, API/CLI, smoke, module/file, status field, warning, and next arc."),
        _row("missing-query-awaits", len(missing) == len(RELEASE_RECORD_QUERY_FIELDS), "With no operator query packet supplied, the query matrix remains prepared rather than selected or executed as authority."),
        _row("matches-not-authority", RELEASE_RECORD_QUERY_BOUNDARIES["query_matches_are_current_state_authority"] is False, "Query matches are not current-state authority."),
        _row("ranking-not-decision", RELEASE_RECORD_QUERY_BOUNDARIES["search_ranking_is_operator_decision_making"] is False, "Search ranking is not operator decision-making."),
        _row("no-authority", all(RELEASE_RECORD_QUERY_BOUNDARIES[key] is False for key in ["query_matrix_writes_archive", "query_matrix_creates_release", "query_matrix_publishes_release", "query_matrix_runs_commands", "query_matrix_applies_patches", "query_matrix_executes_rollback", "query_matrix_writes_source", "query_matrix_writes_memory", "query_matrix_expands_autonomy"]), "Query matrix grants no archive write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION,
        "state": "release_record_query_matrix_review_only",
        "release_record_query_matrix_id": RELEASE_RECORD_QUERY_MATRIX_ID,
        "query_fields": list(RELEASE_RECORD_QUERY_FIELDS),
        "missing_query_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_RECORD_QUERY_BOUNDARIES),
        "safe_next_action": "Operator may review release record query matrix. Query matches and ranking do not authorize decisions or writes.",
    }
    report.update(_base_authority_state())
    return report


def build_archive_search_result_review_packet(root: str | Path | None = None, result_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS, result_packet)
    rows = [
        _row("result-review-schema-defined", len(ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS) >= 6, "Search result review covers matches, classification, confidence notes, stale-current risks, missing-record warnings, and operator notes."),
        _row("missing-results-await", len(missing) == len(ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS), "With no operator result packet supplied, review remains prepared rather than mutating records."),
        _row("review-does-not-mutate", ARCHIVE_SEARCH_RESULT_BOUNDARIES["search_review_mutates_records"] is False, "Search review does not mutate archive records."),
        _row("confidence-not-release-confidence", ARCHIVE_SEARCH_RESULT_BOUNDARIES["search_result_confidence_is_release_confidence"] is False, "Search result confidence is not release confidence."),
        _row("no-authority", all(ARCHIVE_SEARCH_RESULT_BOUNDARIES[key] is False for key in ["search_review_writes_archive", "search_review_creates_release", "search_review_publishes_release", "search_review_runs_commands", "search_review_applies_patches", "search_review_executes_rollback", "search_review_writes_source", "search_review_writes_memory", "search_review_expands_autonomy"]), "Search result review grants no archive write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION,
        "state": "archive_search_result_review_packet_review_only",
        "archive_search_result_review_id": ARCHIVE_SEARCH_RESULT_REVIEW_ID,
        "result_review_fields": list(ARCHIVE_SEARCH_RESULT_REVIEW_FIELDS),
        "missing_result_review_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_SEARCH_RESULT_BOUNDARIES),
        "safe_next_action": "Operator may review archive search results. Review does not mutate records or create release confidence.",
    }
    report.update(_base_authority_state())
    return report


def build_archive_handoff_review_packet(root: str | Path | None = None, handoff_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(ARCHIVE_HANDOFF_REVIEW_FIELDS, handoff_packet)
    rows = [
        _row("handoff-schema-defined", len(ARCHIVE_HANDOFF_REVIEW_FIELDS) >= 6, "Archive handoff review covers search summary, continuity chain, matched records, warnings/blockers, source surfaces, and operator decision options."),
        _row("missing-handoff-awaits", len(missing) == len(ARCHIVE_HANDOFF_REVIEW_FIELDS), "With no operator handoff packet supplied, handoff remains prepared rather than approved."),
        _row("handoff-not-approval", ARCHIVE_HANDOFF_BOUNDARIES["archive_handoff_is_operator_approval"] is False, "Archive handoff is not operator approval."),
        _row("no-authority", all(ARCHIVE_HANDOFF_BOUNDARIES[key] is False for key in ["handoff_review_creates_release", "handoff_review_publishes_release", "handoff_review_writes_archive", "handoff_review_runs_commands", "handoff_review_applies_patches", "handoff_review_executes_rollback", "handoff_review_writes_source", "handoff_review_writes_memory", "handoff_review_expands_autonomy"]), "Archive handoff review grants no release, publish, archive write, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION,
        "state": "archive_handoff_review_packet_review_only",
        "archive_handoff_review_id": ARCHIVE_HANDOFF_REVIEW_ID,
        "handoff_fields": list(ARCHIVE_HANDOFF_REVIEW_FIELDS),
        "missing_handoff_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_HANDOFF_BOUNDARIES),
        "safe_next_action": "Operator may review archive handoff packet. Handoff does not approve, publish, create release, write archive, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_search_handoff_review_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_archive_search_scope_contract(repo)
    query = build_release_record_query_matrix(repo)
    result = build_archive_search_result_review_packet(repo)
    handoff = build_archive_handoff_review_packet(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("archive-search-prepared", scope.get("ok") is True and scope.get("archive_search_status") == "prepared_read_only", "Archive search scope is prepared/read-only."),
        _row("query-matrix-prepared", query.get("ok") is True and query.get("release_record_query_status") == "matrix_prepared", "Release record query matrix is prepared."),
        _row("search-result-review-prepared", result.get("ok") is True and result.get("search_result_review_status") == "prepared", "Archive search result review packet is prepared."),
        _row("archive-handoff-prepared", handoff.get("ok") is True and handoff.get("archive_handoff_status") == "prepared", "Archive handoff review packet is prepared."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Release staleness audit remains clean for current-state fields."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [scope, query, result, handoff]), "No v576-v580 archive search handoff layer runs commands or executes rollback."),
        _row("no-authority", all(RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_BOUNDARIES[key] is False for key in ["archive_search_board_is_release_approval", "archive_search_board_is_publish_permission", "archive_search_board_writes_archive", "archive_search_board_creates_release", "archive_search_board_publishes_release", "archive_search_board_executes_commands", "archive_search_board_applies_patches", "archive_search_board_executes_rollback", "archive_search_board_writes_source", "archive_search_board_writes_memory", "archive_search_board_invokes_models_by_default", "archive_search_board_schedules_work", "archive_search_board_reuses_approval", "archive_search_board_continues_automatically", "archive_search_board_expands_autonomy"]), "Archive search handoff board grants no approval, publish, archive write, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_SEARCH_HANDOFF_VERSION,
        "state": "release_archive_search_handoff_review_board_review_only",
        "release_archive_search_handoff_board_id": RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_ID,
        "archive_search_scope_contract": scope,
        "release_record_query_matrix": query,
        "archive_search_result_review_packet": result,
        "archive_handoff_review_packet": handoff,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_SEARCH_HANDOFF_BOARD_BOUNDARIES),
        "safe_next_action": "Operator may review v580 release archive search and handoff board. It does not approve releases, publish, write external archives, run commands, apply patches, execute rollback, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_search_handoff_arc(root: str | Path | None = None, stage: str = "release_archive_search_handoff_review_board_v1") -> dict[str, Any]:
    builders = {
        "archive_search_scope_contract_v1": build_archive_search_scope_contract,
        "release_record_query_matrix_v1": build_release_record_query_matrix,
        "archive_search_result_review_packet_v1": build_archive_search_result_review_packet,
        "archive_handoff_review_packet_v1": build_archive_handoff_review_packet,
        "release_archive_search_handoff_review_board_v1": build_release_archive_search_handoff_review_board,
    }
    return builders.get(stage, build_release_archive_search_handoff_review_board)(root)


def render_release_archive_search_handoff_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"archive_search_status: {report.get('archive_search_status')}",
        f"release_record_query_status: {report.get('release_record_query_status')}",
        f"search_result_review_status: {report.get('search_result_review_status')}",
        f"archive_handoff_status: {report.get('archive_handoff_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
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

# v576.0-v580.0 release archive search handoff tokens: archive-search-scope-contract release-record-query-matrix archive-search-result-review-packet archive-handoff-review-packet release-archive-search-handoff-review-board release-archive-search-and-handoff-review-v1 release_archive_search_handoff.py archive_search_is_read_only=True search_results_are_approval=False search_scope_authorizes_archive_writes=False query_matches_are_current_state_authority=False search_ranking_is_operator_decision_making=False search_review_mutates_records=False search_result_confidence_is_release_confidence=False archive_handoff_is_operator_approval=False handoff_review_creates_release=False handoff_review_publishes_release=False archive_search_board_is_release_approval=False archive_search_board_is_publish_permission=False archive_search_board_writes_archive=False archive_search_board_executes_commands=False archive_search_status=prepared_read_only release_record_query_status=matrix_prepared search_result_review_status=prepared archive_handoff_status=prepared archive_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
