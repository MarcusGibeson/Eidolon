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
from release_decision_archive_ledger import build_release_decision_archive_ledger_board

RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
RELEASE_ARCHIVE_RETRIEVAL_SCOPE_ID = "v571_release_archive_retrieval_scope_contract"
RELEASE_CONTINUITY_INDEX_ID = "v572_release_continuity_index_prep"
HISTORICAL_REFERENCE_CLASSIFICATION_ID = "v573_historical_reference_classification_review"
CONTINUITY_RETRIEVAL_PACKET_ID = "v574_continuity_retrieval_packet"
RELEASE_ARCHIVE_CONTINUITY_BOARD_ID = "v575_release_archive_retrieval_continuity_index_board"

ARCHIVE_RETRIEVAL_SCOPE_FIELDS: tuple[str, ...] = (
    "archive_retrieval_scope",
    "allowed_archive_fields",
    "historical_release_lookup_boundaries",
    "current_state_vs_historical_reference_distinction",
    "operator_facing_retrieval_packet",
    "operator_notes",
)

CONTINUITY_INDEX_FIELDS: tuple[str, ...] = (
    "version_range",
    "arc_title",
    "primary_module",
    "dashboard_routes",
    "api_cli_surfaces",
    "targeted_smoke_name",
    "readme_release_history_references",
    "next_arc_pointer",
)

HISTORICAL_REFERENCE_CLASSES: tuple[str, ...] = (
    "allowed_historical_release_history_reference",
    "allowed_prior_arc_route_smoke_reference",
    "allowed_regression_smoke_reference",
    "blocked_stale_current_state_marker",
    "blocked_stale_metadata_current_header",
    "blocked_stale_dashboard_api_cli_current_text",
)

CONTINUITY_RETRIEVAL_PACKET_FIELDS: tuple[str, ...] = (
    "current_version_identity",
    "recent_arc_chain",
    "historical_references",
    "blocked_stale_references",
    "archive_ledger_continuity_summary",
    "operator_review_notes",
    "next_recommended_arc",
)

ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES: dict[str, bool] = {
    "archive_retrieval_is_release_approval": False,
    "historical_continuity_authorizes_future_patches": False,
    "archive_lookup_writes_archive_records": False,
    "archive_retrieval_creates_release": False,
    "archive_retrieval_publishes_release": False,
    "archive_retrieval_runs_commands": False,
    "archive_retrieval_applies_patches": False,
    "archive_retrieval_executes_rollback": False,
    "archive_retrieval_writes_source": False,
    "archive_retrieval_writes_memory": False,
    "archive_retrieval_expands_autonomy": False,
    "operator_review_required": True,
}

CONTINUITY_INDEX_BOUNDARIES: dict[str, bool] = {
    "continuity_indexing_is_approval": False,
    "index_completeness_is_publish_permission": False,
    "continuity_index_writes_archive": False,
    "continuity_index_creates_release": False,
    "continuity_index_publishes_release": False,
    "continuity_index_runs_commands": False,
    "continuity_index_applies_patches": False,
    "continuity_index_executes_rollback": False,
    "continuity_index_writes_source": False,
    "continuity_index_writes_memory": False,
    "continuity_index_expands_autonomy": False,
    "operator_review_required": True,
}

HISTORICAL_REFERENCE_BOUNDARIES: dict[str, bool] = {
    "historical_classification_weakens_stale_current_blocking": False,
    "regression_references_are_current_state_authority": False,
    "historical_classification_creates_release": False,
    "historical_classification_publishes_release": False,
    "historical_classification_runs_commands": False,
    "historical_classification_applies_patches": False,
    "historical_classification_executes_rollback": False,
    "historical_classification_writes_source": False,
    "historical_classification_writes_memory": False,
    "historical_classification_expands_autonomy": False,
    "operator_review_required": True,
}

CONTINUITY_RETRIEVAL_BOUNDARIES: dict[str, bool] = {
    "retrieval_packet_is_operator_approval": False,
    "continuity_summary_is_release_closure": False,
    "retrieval_packet_creates_release": False,
    "retrieval_packet_publishes_release": False,
    "retrieval_packet_runs_commands": False,
    "retrieval_packet_applies_patches": False,
    "retrieval_packet_executes_rollback": False,
    "retrieval_packet_writes_source": False,
    "retrieval_packet_writes_memory": False,
    "retrieval_packet_writes_external_archive": False,
    "retrieval_packet_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_CONTINUITY_BOARD_BOUNDARIES: dict[str, bool] = {
    "archive_continuity_board_is_release_approval": False,
    "archive_continuity_board_is_publish_permission": False,
    "archive_continuity_board_writes_archive": False,
    "archive_continuity_board_creates_release": False,
    "archive_continuity_board_publishes_release": False,
    "archive_continuity_board_executes_commands": False,
    "archive_continuity_board_applies_patches": False,
    "archive_continuity_board_executes_rollback": False,
    "archive_continuity_board_writes_source": False,
    "archive_continuity_board_writes_memory": False,
    "archive_continuity_board_invokes_models_by_default": False,
    "archive_continuity_board_schedules_work": False,
    "archive_continuity_board_reuses_approval": False,
    "archive_continuity_board_continues_automatically": False,
    "archive_continuity_board_expands_autonomy": False,
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


def build_release_archive_retrieval_scope_contract(root: str | Path | None = None, retrieval_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(ARCHIVE_RETRIEVAL_SCOPE_FIELDS, retrieval_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    decision_board = build_release_decision_archive_ledger_board(repo)
    rows = [
        _row("scope-schema-defined", len(ARCHIVE_RETRIEVAL_SCOPE_FIELDS) >= 6, "Archive retrieval scope covers allowed fields, historical lookup boundaries, current-vs-historical distinctions, operator packeting, and notes."),
        _row("missing-retrieval-awaits", len(missing) == len(ARCHIVE_RETRIEVAL_SCOPE_FIELDS), "With no operator retrieval packet supplied, the layer remains prepared/read-only rather than writing or approving anything."),
        _row("previous-decision-board-available", decision_board.get("ok") is True, "v570 release decision and archive ledger board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before archive retrieval."),
        _row("retrieval-not-approval", ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES["archive_retrieval_is_release_approval"] is False and ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES["historical_continuity_authorizes_future_patches"] is False, "Archive retrieval is not release approval and historical continuity does not authorize future patches."),
        _row("no-authority", all(ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES[key] is False for key in ["archive_lookup_writes_archive_records", "archive_retrieval_creates_release", "archive_retrieval_publishes_release", "archive_retrieval_runs_commands", "archive_retrieval_applies_patches", "archive_retrieval_executes_rollback", "archive_retrieval_writes_source", "archive_retrieval_writes_memory", "archive_retrieval_expands_autonomy"]), "Archive retrieval grants no archive write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION,
        "state": "release_archive_retrieval_scope_contract_read_only",
        "release_archive_retrieval_scope_id": RELEASE_ARCHIVE_RETRIEVAL_SCOPE_ID,
        "scope_fields": list(ARCHIVE_RETRIEVAL_SCOPE_FIELDS),
        "missing_scope_fields": missing,
        "previous_decision_summary": {"ok": decision_board.get("ok"), "state": decision_board.get("state")},
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_RETRIEVAL_SCOPE_BOUNDARIES),
        "safe_next_action": "Operator may review archive retrieval scope. Retrieval does not approve releases, write archives, publish, run commands, mutate source or memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_continuity_index_prep(root: str | Path | None = None, index_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(CONTINUITY_INDEX_FIELDS, index_packet)
    rows = [
        _row("index-schema-defined", len(CONTINUITY_INDEX_FIELDS) >= 8, "Continuity index covers version range, arc title, module, routes, API/CLI surfaces, smoke, README/history references, and next arc pointer."),
        _row("missing-index-awaits", len(missing) == len(CONTINUITY_INDEX_FIELDS), "With no operator index packet supplied, the index remains prepared rather than becoming an archive write."),
        _row("index-not-approval", CONTINUITY_INDEX_BOUNDARIES["continuity_indexing_is_approval"] is False and CONTINUITY_INDEX_BOUNDARIES["index_completeness_is_publish_permission"] is False, "Continuity indexing is not approval and index completeness is not publish permission."),
        _row("no-authority", all(CONTINUITY_INDEX_BOUNDARIES[key] is False for key in ["continuity_index_writes_archive", "continuity_index_creates_release", "continuity_index_publishes_release", "continuity_index_runs_commands", "continuity_index_applies_patches", "continuity_index_executes_rollback", "continuity_index_writes_source", "continuity_index_writes_memory", "continuity_index_expands_autonomy"]), "Continuity index prep grants no archive write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION,
        "state": "release_continuity_index_prep_review_only",
        "release_continuity_index_id": RELEASE_CONTINUITY_INDEX_ID,
        "index_fields": list(CONTINUITY_INDEX_FIELDS),
        "missing_index_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CONTINUITY_INDEX_BOUNDARIES),
        "safe_next_action": "Operator may review continuity index prep. Indexing does not approve, publish, write archives, run commands, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_historical_reference_classification_review(root: str | Path | None = None, reference_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    rows = [
        _row("classification-schema-defined", len(HISTORICAL_REFERENCE_CLASSES) == 6, "Historical reference classification separates allowed historical release/regression references from blocked stale current-state markers."),
        _row("stale-current-blocking-preserved", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Historical classification does not weaken stale-current blocking."),
        _row("regression-not-authority", HISTORICAL_REFERENCE_BOUNDARIES["regression_references_are_current_state_authority"] is False, "Regression references are not current-state authority."),
        _row("no-authority", all(HISTORICAL_REFERENCE_BOUNDARIES[key] is False for key in ["historical_classification_weakens_stale_current_blocking", "historical_classification_creates_release", "historical_classification_publishes_release", "historical_classification_runs_commands", "historical_classification_applies_patches", "historical_classification_executes_rollback", "historical_classification_writes_source", "historical_classification_writes_memory", "historical_classification_expands_autonomy"]), "Historical classification grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION,
        "state": "historical_reference_classification_review_only",
        "historical_reference_classification_id": HISTORICAL_REFERENCE_CLASSIFICATION_ID,
        "reference_classes": list(HISTORICAL_REFERENCE_CLASSES),
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(HISTORICAL_REFERENCE_BOUNDARIES),
        "safe_next_action": "Operator may review historical classification. It does not weaken stale-current blocking or grant authority.",
    }
    report.update(_base_authority_state())
    return report


def build_continuity_retrieval_packet(root: str | Path | None = None, continuity_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(CONTINUITY_RETRIEVAL_PACKET_FIELDS, continuity_packet)
    rows = [
        _row("retrieval-packet-schema-defined", len(CONTINUITY_RETRIEVAL_PACKET_FIELDS) >= 7, "Continuity retrieval packet covers current version, recent arc chain, historical references, blocked stale references, archive ledger summary, operator notes, and next arc."),
        _row("missing-packet-awaits", len(missing) == len(CONTINUITY_RETRIEVAL_PACKET_FIELDS), "With no operator continuity packet supplied, retrieval remains prepared rather than approval or closure."),
        _row("packet-not-approval", CONTINUITY_RETRIEVAL_BOUNDARIES["retrieval_packet_is_operator_approval"] is False and CONTINUITY_RETRIEVAL_BOUNDARIES["continuity_summary_is_release_closure"] is False, "Retrieval packet is not operator approval and continuity summary is not release closure."),
        _row("no-authority", all(CONTINUITY_RETRIEVAL_BOUNDARIES[key] is False for key in ["retrieval_packet_creates_release", "retrieval_packet_publishes_release", "retrieval_packet_runs_commands", "retrieval_packet_applies_patches", "retrieval_packet_executes_rollback", "retrieval_packet_writes_source", "retrieval_packet_writes_memory", "retrieval_packet_writes_external_archive", "retrieval_packet_expands_autonomy"]), "Continuity retrieval packet grants no release, publish, command, patch, rollback, source, memory, archive write, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION,
        "state": "continuity_retrieval_packet_review_only",
        "continuity_retrieval_packet_id": CONTINUITY_RETRIEVAL_PACKET_ID,
        "retrieval_packet_fields": list(CONTINUITY_RETRIEVAL_PACKET_FIELDS),
        "missing_retrieval_packet_fields": missing,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CONTINUITY_RETRIEVAL_BOUNDARIES),
        "safe_next_action": "Operator may review continuity retrieval packet. Packet does not approve, close releases, write archives, run commands, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_retrieval_continuity_index_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_release_archive_retrieval_scope_contract(repo)
    index = build_release_continuity_index_prep(repo)
    classification = build_historical_reference_classification_review(repo)
    packet = build_continuity_retrieval_packet(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("archive-retrieval-prepared", scope.get("ok") is True and scope.get("archive_retrieval_status") == "prepared_read_only", "Archive retrieval scope is prepared/read-only."),
        _row("continuity-index-prepared", index.get("ok") is True and index.get("continuity_index_status") == "prepared", "Continuity index prep is prepared."),
        _row("historical-references-classified", classification.get("ok") is True and classification.get("historical_reference_status") == "classified", "Historical references are classified while stale current references remain blocked."),
        _row("retrieval-packet-prepared", packet.get("ok") is True and packet.get("retrieval_packet_status") == "prepared", "Continuity retrieval packet is prepared."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Release staleness audit remains clean for current-state fields."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [scope, index, classification, packet]), "No v571-v575 archive continuity layer runs commands or executes rollback."),
        _row("no-authority", all(RELEASE_ARCHIVE_CONTINUITY_BOARD_BOUNDARIES[key] is False for key in ["archive_continuity_board_is_release_approval", "archive_continuity_board_is_publish_permission", "archive_continuity_board_writes_archive", "archive_continuity_board_creates_release", "archive_continuity_board_publishes_release", "archive_continuity_board_executes_commands", "archive_continuity_board_applies_patches", "archive_continuity_board_executes_rollback", "archive_continuity_board_writes_source", "archive_continuity_board_writes_memory", "archive_continuity_board_invokes_models_by_default", "archive_continuity_board_schedules_work", "archive_continuity_board_reuses_approval", "archive_continuity_board_continues_automatically", "archive_continuity_board_expands_autonomy"]), "Archive continuity board grants no approval, publish, archive write, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_CONTINUITY_INDEX_VERSION,
        "state": "release_archive_retrieval_continuity_index_board_review_only",
        "release_archive_continuity_board_id": RELEASE_ARCHIVE_CONTINUITY_BOARD_ID,
        "release_archive_retrieval_scope_contract": scope,
        "release_continuity_index_prep": index,
        "historical_reference_classification_review": classification,
        "continuity_retrieval_packet": packet,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_CONTINUITY_BOARD_BOUNDARIES),
        "safe_next_action": "Operator may review v575 release archive retrieval and continuity index board. It does not approve releases, publish, write external archives, run commands, apply patches, execute rollback, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_continuity_index_arc(root: str | Path | None = None, stage: str = "release_archive_retrieval_continuity_index_board_v1") -> dict[str, Any]:
    builders = {
        "release_archive_retrieval_scope_contract_v1": build_release_archive_retrieval_scope_contract,
        "release_continuity_index_prep_v1": build_release_continuity_index_prep,
        "historical_reference_classification_review_v1": build_historical_reference_classification_review,
        "continuity_retrieval_packet_v1": build_continuity_retrieval_packet,
        "release_archive_retrieval_continuity_index_board_v1": build_release_archive_retrieval_continuity_index_board,
    }
    return builders.get(stage, build_release_archive_retrieval_continuity_index_board)(root)


def render_release_archive_continuity_index_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"archive_retrieval_status: {report.get('archive_retrieval_status')}",
        f"continuity_index_status: {report.get('continuity_index_status')}",
        f"historical_reference_status: {report.get('historical_reference_status')}",
        f"stale_current_reference_status: {report.get('stale_current_reference_status')}",
        f"retrieval_packet_status: {report.get('retrieval_packet_status')}",
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

# v571.0-v575.0 release archive continuity index tokens: release-archive-retrieval-scope-contract release-continuity-index-prep historical-reference-classification-review continuity-retrieval-packet release-archive-retrieval-continuity-index-board release-archive-retrieval-and-continuity-index-v1 release_archive_continuity_index.py archive_retrieval_is_release_approval=False historical_continuity_authorizes_future_patches=False archive_lookup_writes_archive_records=False continuity_indexing_is_approval=False index_completeness_is_publish_permission=False historical_classification_weakens_stale_current_blocking=False regression_references_are_current_state_authority=False retrieval_packet_is_operator_approval=False continuity_summary_is_release_closure=False archive_continuity_board_is_release_approval=False archive_continuity_board_is_publish_permission=False archive_continuity_board_writes_archive=False archive_continuity_board_executes_commands=False archive_retrieval_status=prepared_read_only continuity_index_status=prepared historical_reference_status=classified stale_current_reference_status=blocked_if_detected retrieval_packet_status=prepared release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
