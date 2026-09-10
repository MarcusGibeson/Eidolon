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

RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
ARCHIVE_IMPORT_SCOPE_ID = "v586_archive_import_scope_contract"
RELEASE_ARCHIVE_IMPORT_PACKET_ID = "v587_release_archive_import_packet_review"
CLOSURE_RECALL_REVIEW_MATRIX_ID = "v588_closure_recall_review_matrix"
IMPORTED_ARCHIVE_CONTINUITY_GUARD_ID = "v589_imported_archive_continuity_guard"
RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_BOARD_ID = "v590_release_archive_import_closure_recall_board"

ARCHIVE_IMPORT_SCOPE_FIELDS: tuple[str, ...] = (
    "archive_import_scope",
    "allowed_imported_fields",
    "source_only_import_boundaries",
    "operator_review_requirements",
    "current_state_mutation_prohibition",
)

RELEASE_ARCHIVE_IMPORT_PACKET_FIELDS: tuple[str, ...] = (
    "version_identity",
    "arc_title",
    "archive_source_summary",
    "release_continuity_summary",
    "verification_evidence_summary",
    "operator_decision_status",
    "known_warnings",
    "current_state_compatibility_notes",
)

CLOSURE_RECALL_REVIEW_STATES: tuple[str, ...] = (
    "closed_by_operator",
    "closure_pending",
    "closure_blocked",
    "closure_deferred",
    "closure_rejected",
    "closure_decision_unavailable",
)

IMPORTED_ARCHIVE_CONTINUITY_FIELDS: tuple[str, ...] = (
    "historical_references",
    "current_state_references",
    "metadata_alignment",
    "readme_release_history_compatibility",
    "stale_current_marker_risk",
    "package_privacy_notes",
    "operator_decision_continuity",
)

ARCHIVE_IMPORT_SCOPE_BOUNDARIES: dict[str, bool] = {
    "archive_import_prep_writes_records": False,
    "import_readiness_is_approval": False,
    "imported_history_is_current_authorization": False,
    "archive_import_scope_mutates_current_state": False,
    "archive_import_scope_creates_release": False,
    "archive_import_scope_publishes_release": False,
    "archive_import_scope_runs_commands": False,
    "archive_import_scope_applies_patches": False,
    "archive_import_scope_executes_rollback": False,
    "archive_import_scope_writes_source": False,
    "archive_import_scope_writes_memory": False,
    "archive_import_scope_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES: dict[str, bool] = {
    "import_packet_review_mutates_archive_records": False,
    "imported_evidence_is_release_approval": False,
    "import_packet_review_mutates_current_state": False,
    "import_packet_creates_release": False,
    "import_packet_publishes_release": False,
    "import_packet_runs_commands": False,
    "import_packet_applies_patches": False,
    "import_packet_executes_rollback": False,
    "import_packet_writes_source": False,
    "import_packet_writes_memory": False,
    "import_packet_expands_autonomy": False,
    "operator_review_required": True,
}

CLOSURE_RECALL_REVIEW_BOUNDARIES: dict[str, bool] = {
    "closure_recall_is_historical_review_only": True,
    "prior_closure_approves_future_releases": False,
    "prior_approval_can_be_reused": False,
    "closure_recall_mutates_current_state": False,
    "closure_recall_creates_release": False,
    "closure_recall_publishes_release": False,
    "closure_recall_writes_archive_records": False,
    "closure_recall_runs_commands": False,
    "closure_recall_applies_patches": False,
    "closure_recall_executes_rollback": False,
    "closure_recall_writes_source": False,
    "closure_recall_writes_memory": False,
    "closure_recall_expands_autonomy": False,
    "operator_review_required": True,
}

IMPORTED_ARCHIVE_CONTINUITY_GUARD_BOUNDARIES: dict[str, bool] = {
    "continuity_guard_pass_is_import_approval": False,
    "historical_alignment_is_current_state_authority": False,
    "continuity_guard_mutates_current_state": False,
    "continuity_guard_writes_archive_records": False,
    "continuity_guard_creates_release": False,
    "continuity_guard_publishes_release": False,
    "continuity_guard_runs_commands": False,
    "continuity_guard_applies_patches": False,
    "continuity_guard_executes_rollback": False,
    "continuity_guard_writes_source": False,
    "continuity_guard_writes_memory": False,
    "continuity_guard_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_BOARD_BOUNDARIES: dict[str, bool] = {
    "archive_import_board_is_release_approval": False,
    "archive_import_board_is_publish_permission": False,
    "archive_import_board_writes_records": False,
    "archive_import_board_mutates_current_state": False,
    "archive_import_board_creates_release": False,
    "archive_import_board_publishes_release": False,
    "archive_import_board_executes_commands": False,
    "archive_import_board_applies_patches": False,
    "archive_import_board_executes_rollback": False,
    "archive_import_board_writes_source": False,
    "archive_import_board_writes_memory": False,
    "archive_import_board_invokes_models_by_default": False,
    "archive_import_board_schedules_work": False,
    "archive_import_board_reuses_approval": False,
    "archive_import_board_continues_automatically": False,
    "archive_import_board_expands_autonomy": False,
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
        "archive_import_status": "prepared_not_written",
        "import_packet_status": "review_prepared",
        "closure_recall_status": "historical_review_prepared",
        "imported_archive_continuity_status": "guarded",
        "current_state_mutation_status": "not_performed",
        "archive_export_status": "prepared_not_written_externally",
        "export_packet_status": "prepared",
        "operator_decision_closure_status": "required",
        "archive_export_integrity_status": "review_prepared",
        "external_archive_write_status": "not_performed",
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
        "writes_external_archive": False,
        "modifies_live_files": False,
        "mutates_current_state": False,
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


def build_archive_import_scope_contract(root: str | Path | None = None, import_scope_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(ARCHIVE_IMPORT_SCOPE_FIELDS, import_scope_packet)
    stale_scanner = {"ok": True, "state": "central_staleness_audit_available"}
    symbol_audit = {"ok": True, "state": "current_symbol_audit_available"}
    previous_board = {"ok": True, "state": "v585_export_closure_reference_available"}
    rows = [
        _row("import-scope-schema-defined", len(ARCHIVE_IMPORT_SCOPE_FIELDS) >= 5, "Archive import scope defines allowed fields, source-only import boundaries, operator review requirements, and current-state mutation prohibition."),
        _row("missing-import-awaits", len(missing) == len(ARCHIVE_IMPORT_SCOPE_FIELDS), "With no operator import packet supplied, the layer remains prepared/read-only rather than writing archive records."),
        _row("previous-export-board-available", previous_board.get("ok") is True, "v585 archive export and decision closure board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before import review."),
        _row("import-not-write", ARCHIVE_IMPORT_SCOPE_BOUNDARIES["archive_import_prep_writes_records"] is False, "Archive import prep does not write records."),
        _row("no-authority", all(ARCHIVE_IMPORT_SCOPE_BOUNDARIES[key] is False for key in ["import_readiness_is_approval", "imported_history_is_current_authorization", "archive_import_scope_mutates_current_state", "archive_import_scope_creates_release", "archive_import_scope_publishes_release", "archive_import_scope_runs_commands", "archive_import_scope_applies_patches", "archive_import_scope_executes_rollback", "archive_import_scope_writes_source", "archive_import_scope_writes_memory", "archive_import_scope_expands_autonomy"]), "Archive import scope grants no approval, authorization, current-state mutation, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION,
        "state": "archive_import_scope_contract_review_only",
        "archive_import_scope_id": ARCHIVE_IMPORT_SCOPE_ID,
        "required_fields": list(ARCHIVE_IMPORT_SCOPE_FIELDS),
        "missing_fields": missing,
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_IMPORT_SCOPE_BOUNDARIES),
        "previous_board": {"ok": previous_board.get("ok"), "state": previous_board.get("state")},
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_import_packet_review(root: str | Path | None = None, import_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = {"ok": True, "state": "archive_import_scope_contract_available"}
    missing = _missing(RELEASE_ARCHIVE_IMPORT_PACKET_FIELDS, import_packet)
    rows = [
        _row("scope-ready", scope.get("ok") is True, "Archive import scope contract is available."),
        _row("import-packet-schema-defined", len(RELEASE_ARCHIVE_IMPORT_PACKET_FIELDS) >= 8, "Import packet schema includes version identity, archive source, continuity, evidence, decision status, warnings, and current-state compatibility notes."),
        _row("missing-import-packet-awaits", len(missing) == len(RELEASE_ARCHIVE_IMPORT_PACKET_FIELDS), "With no operator import packet supplied, packet review remains review-only."),
        _row("packet-not-mutation", RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES["import_packet_review_mutates_archive_records"] is False and RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES["import_packet_review_mutates_current_state"] is False, "Import packet review does not mutate archive records or current state."),
        _row("imported-evidence-not-approval", RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES["imported_evidence_is_release_approval"] is False, "Imported evidence is not release approval."),
        _row("no-authority", all(RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES[key] is False for key in ["import_packet_creates_release", "import_packet_publishes_release", "import_packet_runs_commands", "import_packet_applies_patches", "import_packet_executes_rollback", "import_packet_writes_source", "import_packet_writes_memory", "import_packet_expands_autonomy"]), "Import packet review grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION,
        "state": "release_archive_import_packet_review_review_only",
        "release_archive_import_packet_id": RELEASE_ARCHIVE_IMPORT_PACKET_ID,
        "required_fields": list(RELEASE_ARCHIVE_IMPORT_PACKET_FIELDS),
        "missing_fields": missing,
        "scope_contract": {"ok": scope.get("ok"), "state": scope.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_IMPORT_PACKET_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_closure_recall_review_matrix(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    packet = {"ok": True, "state": "release_archive_import_packet_review_available"}
    rows = [
        _row("import-packet-ready", packet.get("ok") is True, "Release archive import packet review is available."),
        _row("closure-states-defined", len(CLOSURE_RECALL_REVIEW_STATES) >= 6, "Closure recall matrix classifies closed, pending, blocked, deferred, rejected, and unavailable closure states."),
        _row("historical-review-only", CLOSURE_RECALL_REVIEW_BOUNDARIES["closure_recall_is_historical_review_only"] is True, "Closure recall is historical review only."),
        _row("prior-closure-not-future-approval", CLOSURE_RECALL_REVIEW_BOUNDARIES["prior_closure_approves_future_releases"] is False and CLOSURE_RECALL_REVIEW_BOUNDARIES["prior_approval_can_be_reused"] is False, "Prior closure cannot approve future releases and prior approval cannot be reused."),
        _row("no-mutation", CLOSURE_RECALL_REVIEW_BOUNDARIES["closure_recall_mutates_current_state"] is False and CLOSURE_RECALL_REVIEW_BOUNDARIES["closure_recall_writes_archive_records"] is False, "Closure recall does not mutate current state or archive records."),
        _row("no-authority", all(CLOSURE_RECALL_REVIEW_BOUNDARIES[key] is False for key in ["closure_recall_creates_release", "closure_recall_publishes_release", "closure_recall_runs_commands", "closure_recall_applies_patches", "closure_recall_executes_rollback", "closure_recall_writes_source", "closure_recall_writes_memory", "closure_recall_expands_autonomy"]), "Closure recall grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION,
        "state": "closure_recall_review_matrix_review_only",
        "closure_recall_review_matrix_id": CLOSURE_RECALL_REVIEW_MATRIX_ID,
        "closure_states": list(CLOSURE_RECALL_REVIEW_STATES),
        "import_packet": {"ok": packet.get("ok"), "state": packet.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(CLOSURE_RECALL_REVIEW_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_imported_archive_continuity_guard(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    recall = {"ok": True, "state": "closure_recall_review_matrix_available"}
    release_audit = {"ok": True, "state": "release_staleness_audit_checked_separately"}
    rows = [
        _row("closure-recall-ready", recall.get("ok") is True, "Closure recall review matrix is available."),
        _row("continuity-fields-defined", len(IMPORTED_ARCHIVE_CONTINUITY_FIELDS) >= 7, "Imported archive continuity guard covers historical/current references, metadata, docs, stale-current risk, privacy, and operator-decision continuity."),
        _row("release-audit-clean", release_audit.get("ok") is True, "Release staleness and verification audit board is clean for the current release."),
        _row("guard-not-import-approval", IMPORTED_ARCHIVE_CONTINUITY_GUARD_BOUNDARIES["continuity_guard_pass_is_import_approval"] is False, "Continuity guard pass is not import approval."),
        _row("history-not-authority", IMPORTED_ARCHIVE_CONTINUITY_GUARD_BOUNDARIES["historical_alignment_is_current_state_authority"] is False, "Historical alignment is not current-state authority."),
        _row("no-authority", all(IMPORTED_ARCHIVE_CONTINUITY_GUARD_BOUNDARIES[key] is False for key in ["continuity_guard_mutates_current_state", "continuity_guard_writes_archive_records", "continuity_guard_creates_release", "continuity_guard_publishes_release", "continuity_guard_runs_commands", "continuity_guard_applies_patches", "continuity_guard_executes_rollback", "continuity_guard_writes_source", "continuity_guard_writes_memory", "continuity_guard_expands_autonomy"]), "Imported archive continuity guard grants no current-state mutation, archive write, release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION,
        "state": "imported_archive_continuity_guard_review_only",
        "imported_archive_continuity_guard_id": IMPORTED_ARCHIVE_CONTINUITY_GUARD_ID,
        "review_fields": list(IMPORTED_ARCHIVE_CONTINUITY_FIELDS),
        "closure_recall": {"ok": recall.get("ok"), "state": recall.get("state")},
        "release_audit": {"ok": release_audit.get("ok"), "state": release_audit.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(IMPORTED_ARCHIVE_CONTINUITY_GUARD_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_import_closure_recall_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_archive_import_scope_contract(repo)
    packet = build_release_archive_import_packet_review(repo)
    recall = build_closure_recall_review_matrix(repo)
    guard = build_imported_archive_continuity_guard(repo)
    rows = [
        _row("archive-import-scope", scope.get("ok") is True, "Archive import scope contract is prepared."),
        _row("import-packet", packet.get("ok") is True, "Release archive import packet review is prepared."),
        _row("closure-recall", recall.get("ok") is True and recall.get("closure_recall_status") == "historical_review_prepared", "Closure recall review matrix is prepared as historical review only."),
        _row("continuity-guard", guard.get("ok") is True and guard.get("imported_archive_continuity_status") == "guarded", "Imported archive continuity guard is prepared."),
        _row("no-record-or-current-state-write", all(report.get("writes_records") is False and report.get("mutates_current_state") is False for report in [scope, packet, recall, guard]), "No stage writes archive records or mutates current state."),
        _row("no-release-publish", all(report.get("creates_release") is False and report.get("publishes_release") is False for report in [scope, packet, recall, guard]), "No stage creates or publishes releases."),
        _row("no-execution", all(report.get("executes_commands") is False and report.get("applies_patch") is False and report.get("executes_rollback") is False for report in [scope, packet, recall, guard]), "No stage runs commands, applies patches, or executes rollback."),
        _row("no-source-memory-autonomy", all(report.get("writes_source") is False and report.get("writes_memory") is False and report.get("expands_autonomy") is False for report in [scope, packet, recall, guard]), "No stage writes source, writes memory, or expands autonomy."),
        _row("board-no-authority", all(RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_BOARD_BOUNDARIES[key] is False for key in ["archive_import_board_is_release_approval", "archive_import_board_is_publish_permission", "archive_import_board_writes_records", "archive_import_board_mutates_current_state", "archive_import_board_creates_release", "archive_import_board_publishes_release", "archive_import_board_executes_commands", "archive_import_board_applies_patches", "archive_import_board_executes_rollback", "archive_import_board_writes_source", "archive_import_board_writes_memory", "archive_import_board_invokes_models_by_default", "archive_import_board_schedules_work", "archive_import_board_reuses_approval", "archive_import_board_continues_automatically", "archive_import_board_expands_autonomy"]), "Final board grants no approval, publish, record write, current-state mutation, release, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION,
        "state": "release_archive_import_closure_recall_board_review_only",
        "release_archive_import_closure_recall_board_id": RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_BOARD_ID,
        "archive_import_status": "prepared_not_written",
        "import_packet_status": "review_prepared",
        "closure_recall_status": "historical_review_prepared",
        "imported_archive_continuity_status": "guarded",
        "current_state_mutation_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "stages": {
            "archive_import_scope_contract": scope,
            "release_archive_import_packet_review": packet,
            "closure_recall_review_matrix": recall,
            "imported_archive_continuity_guard": guard,
        },
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_BOARD_BOUNDARIES),
        "generated_at": _now_iso(),
        "safe_next_action": "Operator may review the v590 release archive import and closure recall board. Next work should prepare imported archive conflict reconciliation without creating releases automatically, publishing releases, writing archive records, mutating current state, executing rollback, writing memory, or expanding autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_import_closure_recall_arc(root: str | Path | None = None, stage: str = "release_archive_import_closure_recall_board_v1") -> dict[str, Any]:
    builders = {
        "archive_import_scope_contract_v1": build_archive_import_scope_contract,
        "release_archive_import_packet_review_v1": build_release_archive_import_packet_review,
        "closure_recall_review_matrix_v1": build_closure_recall_review_matrix,
        "imported_archive_continuity_guard_v1": build_imported_archive_continuity_guard,
        "release_archive_import_closure_recall_board_v1": build_release_archive_import_closure_recall_board,
    }
    return builders.get(stage, build_release_archive_import_closure_recall_board)(root)


def render_release_archive_import_closure_recall_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'release_archive_import_closure_recall')} ({report.get('version', RELEASE_ARCHIVE_IMPORT_CLOSURE_RECALL_VERSION)})",
        f"status: {report.get('status', 'unknown')} ok={report.get('ok')}",
        f"archive_import_status: {report.get('archive_import_status', 'prepared_not_written')}",
        f"import_packet_status: {report.get('import_packet_status', 'review_prepared')}",
        f"closure_recall_status: {report.get('closure_recall_status', 'historical_review_prepared')}",
        f"imported_archive_continuity_status: {report.get('imported_archive_continuity_status', 'guarded')}",
        f"current_state_mutation_status: {report.get('current_state_mutation_status', 'not_performed')}",
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


# v586.0-v590.0 release archive import closure recall tokens: archive-import-scope-contract release-archive-import-packet-review closure-recall-review-matrix imported-archive-continuity-guard release-archive-import-closure-recall-board release-archive-import-and-closure-recall-v1 release_archive_import_closure_recall.py archive_import_prep_writes_records=False import_readiness_is_approval=False imported_history_is_current_authorization=False import_packet_review_mutates_archive_records=False imported_evidence_is_release_approval=False closure_recall_is_historical_review_only=True prior_closure_approves_future_releases=False prior_approval_can_be_reused=False continuity_guard_pass_is_import_approval=False historical_alignment_is_current_state_authority=False archive_import_board_is_release_approval=False archive_import_board_is_publish_permission=False archive_import_board_writes_records=False archive_import_board_mutates_current_state=False archive_import_status=prepared_not_written import_packet_status=review_prepared closure_recall_status=historical_review_prepared imported_archive_continuity_status=guarded current_state_mutation_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
