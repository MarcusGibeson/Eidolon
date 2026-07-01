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
from release_archive_search_handoff import build_release_archive_search_handoff_review_board

RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
ARCHIVE_EXPORT_SCOPE_ID = "v581_archive_export_scope_contract"
RELEASE_ARCHIVE_EXPORT_PACKET_ID = "v582_release_archive_export_packet_prep"
OPERATOR_DECISION_CLOSURE_CHECKLIST_ID = "v583_operator_decision_closure_checklist"
ARCHIVE_EXPORT_INTEGRITY_REVIEW_ID = "v584_archive_export_integrity_review"
RELEASE_ARCHIVE_EXPORT_DECISION_CLOSURE_BOARD_ID = "v585_release_archive_export_decision_closure_board"

ARCHIVE_EXPORT_SCOPE_FIELDS: tuple[str, ...] = (
    "archive_export_scope",
    "allowed_export_fields",
    "source_only_export_boundaries",
    "operator_review_requirements",
    "external_write_prohibition",
)

RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS: tuple[str, ...] = (
    "version_identity",
    "arc_title",
    "release_continuity_summary",
    "verification_evidence_summary",
    "package_privacy_status",
    "known_warnings",
    "operator_decision_status",
    "next_arc_pointer",
)

OPERATOR_DECISION_CLOSURE_FIELDS: tuple[str, ...] = (
    "candidate_version_confirmation",
    "evidence_packet_review",
    "archive_packet_review",
    "known_blocker_review",
    "exact_operator_closure_decision",
    "single_use_closure_boundary",
)

ARCHIVE_EXPORT_INTEGRITY_FIELDS: tuple[str, ...] = (
    "readme_current_header",
    "release_history_top_entry",
    "workspace_project_metadata",
    "source_version_markers",
    "dashboard_api_cli_current_text",
    "stale_current_reference_blocking",
    "package_privacy_status",
    "historical_reference_classification",
)

ARCHIVE_EXPORT_SCOPE_BOUNDARIES: dict[str, bool] = {
    "archive_export_prep_writes_external_files": False,
    "export_readiness_is_publish_permission": False,
    "export_scope_is_release_approval": False,
    "archive_export_scope_creates_release": False,
    "archive_export_scope_publishes_release": False,
    "archive_export_scope_runs_commands": False,
    "archive_export_scope_applies_patches": False,
    "archive_export_scope_executes_rollback": False,
    "archive_export_scope_writes_source": False,
    "archive_export_scope_writes_memory": False,
    "archive_export_scope_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES: dict[str, bool] = {
    "export_packet_prep_writes_external_archive": False,
    "prepared_packet_is_approval": False,
    "export_packet_creates_release": False,
    "export_packet_publishes_release": False,
    "export_packet_runs_commands": False,
    "export_packet_applies_patches": False,
    "export_packet_executes_rollback": False,
    "export_packet_writes_source": False,
    "export_packet_writes_memory": False,
    "export_packet_expands_autonomy": False,
    "operator_review_required": True,
}

OPERATOR_DECISION_CLOSURE_BOUNDARIES: dict[str, bool] = {
    "closure_checklist_completion_is_automatic_approval": False,
    "closure_decision_reusable_for_future_releases": False,
    "closure_checklist_creates_release": False,
    "closure_checklist_publishes_release": False,
    "closure_checklist_writes_external_archive": False,
    "closure_checklist_runs_commands": False,
    "closure_checklist_applies_patches": False,
    "closure_checklist_executes_rollback": False,
    "closure_checklist_writes_source": False,
    "closure_checklist_writes_memory": False,
    "closure_checklist_expands_autonomy": False,
    "operator_review_required": True,
}

ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES: dict[str, bool] = {
    "export_integrity_review_writes_external_archive": False,
    "integrity_pass_is_publish_approval": False,
    "export_integrity_creates_release": False,
    "export_integrity_publishes_release": False,
    "export_integrity_runs_commands": False,
    "export_integrity_applies_patches": False,
    "export_integrity_executes_rollback": False,
    "export_integrity_writes_source": False,
    "export_integrity_writes_memory": False,
    "export_integrity_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_ARCHIVE_EXPORT_CLOSURE_BOARD_BOUNDARIES: dict[str, bool] = {
    "archive_export_board_is_release_approval": False,
    "archive_export_board_is_publish_permission": False,
    "archive_export_board_writes_external_archive": False,
    "archive_export_board_creates_release": False,
    "archive_export_board_publishes_release": False,
    "archive_export_board_executes_commands": False,
    "archive_export_board_applies_patches": False,
    "archive_export_board_executes_rollback": False,
    "archive_export_board_writes_source": False,
    "archive_export_board_writes_memory": False,
    "archive_export_board_invokes_models_by_default": False,
    "archive_export_board_schedules_work": False,
    "archive_export_board_reuses_approval": False,
    "archive_export_board_continues_automatically": False,
    "archive_export_board_expands_autonomy": False,
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
        "archive_export_status": "prepared_not_written_externally",
        "export_packet_status": "prepared",
        "operator_decision_closure_status": "required",
        "archive_export_integrity_status": "review_prepared",
        "external_archive_write_status": "not_performed",
        "archive_search_status": "prepared_read_only",
        "release_record_query_status": "matrix_prepared",
        "search_result_review_status": "prepared",
        "archive_handoff_status": "prepared",
        "archive_write_status": "not_performed",
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


def build_archive_export_scope_contract(root: str | Path | None = None, export_scope_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(ARCHIVE_EXPORT_SCOPE_FIELDS, export_scope_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    previous_board = build_release_archive_search_handoff_review_board(repo)
    rows = [
        _row("export-scope-schema-defined", len(ARCHIVE_EXPORT_SCOPE_FIELDS) >= 5, "Archive export scope defines allowed fields, source-only boundaries, operator review requirements, and external-write prohibition."),
        _row("missing-export-awaits", len(missing) == len(ARCHIVE_EXPORT_SCOPE_FIELDS), "With no operator export packet supplied, the layer remains prepared/read-only rather than writing external archives."),
        _row("previous-search-board-available", previous_board.get("ok") is True, "v580 archive search and handoff review board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits remain clean before export prep."),
        _row("export-not-external-write", ARCHIVE_EXPORT_SCOPE_BOUNDARIES["archive_export_prep_writes_external_files"] is False, "Archive export prep does not write external files."),
        _row("no-authority", all(ARCHIVE_EXPORT_SCOPE_BOUNDARIES[key] is False for key in ["export_readiness_is_publish_permission", "export_scope_is_release_approval", "archive_export_scope_creates_release", "archive_export_scope_publishes_release", "archive_export_scope_runs_commands", "archive_export_scope_applies_patches", "archive_export_scope_executes_rollback", "archive_export_scope_writes_source", "archive_export_scope_writes_memory", "archive_export_scope_expands_autonomy"]), "Archive export scope grants no publish, approval, release, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION,
        "state": "archive_export_scope_contract_review_only",
        "archive_export_scope_id": ARCHIVE_EXPORT_SCOPE_ID,
        "required_fields": list(ARCHIVE_EXPORT_SCOPE_FIELDS),
        "missing_fields": missing,
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_EXPORT_SCOPE_BOUNDARIES),
        "previous_board": {"ok": previous_board.get("ok"), "state": previous_board.get("state")},
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_export_packet_prep(root: str | Path | None = None, export_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_archive_export_scope_contract(repo)
    missing = _missing(RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS, export_packet)
    rows = [
        _row("scope-ready", scope.get("ok") is True, "Archive export scope contract is available."),
        _row("export-packet-schema-defined", len(RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS) >= 8, "Export packet schema includes version identity, arc title, continuity, evidence, privacy, warnings, operator decision, and next arc."),
        _row("missing-export-packet-awaits", len(missing) == len(RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS), "With no operator export packet supplied, packet prep remains review-only."),
        _row("packet-not-approval", RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES["prepared_packet_is_approval"] is False, "Prepared export packet is not approval."),
        _row("no-external-write", RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES["export_packet_prep_writes_external_archive"] is False, "Export packet prep does not write external archives."),
        _row("no-authority", all(RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES[key] is False for key in ["export_packet_creates_release", "export_packet_publishes_release", "export_packet_runs_commands", "export_packet_applies_patches", "export_packet_executes_rollback", "export_packet_writes_source", "export_packet_writes_memory", "export_packet_expands_autonomy"]), "Export packet prep grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION,
        "state": "release_archive_export_packet_prep_review_only",
        "release_archive_export_packet_id": RELEASE_ARCHIVE_EXPORT_PACKET_ID,
        "required_fields": list(RELEASE_ARCHIVE_EXPORT_PACKET_FIELDS),
        "missing_fields": missing,
        "scope_contract": {"ok": scope.get("ok"), "state": scope.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_EXPORT_PACKET_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_operator_decision_closure_checklist(root: str | Path | None = None, closure_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    export_packet = build_release_archive_export_packet_prep(repo)
    missing = _missing(OPERATOR_DECISION_CLOSURE_FIELDS, closure_packet)
    rows = [
        _row("export-packet-ready", export_packet.get("ok") is True, "Release archive export packet prep is available."),
        _row("closure-schema-defined", len(OPERATOR_DECISION_CLOSURE_FIELDS) >= 6, "Operator closure checklist requires candidate confirmation, evidence review, archive packet review, blocker review, exact decision, and single-use boundary."),
        _row("missing-closure-awaits", len(missing) == len(OPERATOR_DECISION_CLOSURE_FIELDS), "With no exact operator closure decision supplied, closure remains required."),
        _row("checklist-not-automatic-approval", OPERATOR_DECISION_CLOSURE_BOUNDARIES["closure_checklist_completion_is_automatic_approval"] is False, "Closure checklist completion is not automatic approval."),
        _row("decision-not-reusable", OPERATOR_DECISION_CLOSURE_BOUNDARIES["closure_decision_reusable_for_future_releases"] is False, "Closure decision cannot be reused for future releases."),
        _row("no-authority", all(OPERATOR_DECISION_CLOSURE_BOUNDARIES[key] is False for key in ["closure_checklist_creates_release", "closure_checklist_publishes_release", "closure_checklist_writes_external_archive", "closure_checklist_runs_commands", "closure_checklist_applies_patches", "closure_checklist_executes_rollback", "closure_checklist_writes_source", "closure_checklist_writes_memory", "closure_checklist_expands_autonomy"]), "Closure checklist grants no release, publish, external archive write, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION,
        "state": "operator_decision_closure_checklist_review_only",
        "operator_decision_closure_checklist_id": OPERATOR_DECISION_CLOSURE_CHECKLIST_ID,
        "required_fields": list(OPERATOR_DECISION_CLOSURE_FIELDS),
        "missing_fields": missing,
        "export_packet": {"ok": export_packet.get("ok"), "state": export_packet.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(OPERATOR_DECISION_CLOSURE_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_archive_export_integrity_review(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    closure = build_operator_decision_closure_checklist(repo)
    release_audit = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("closure-checklist-ready", closure.get("ok") is True, "Operator decision closure checklist is available."),
        _row("integrity-schema-defined", len(ARCHIVE_EXPORT_INTEGRITY_FIELDS) >= 8, "Archive export integrity review covers README, release history, metadata, version markers, dashboard/API/CLI text, stale blocking, privacy, and historical classification."),
        _row("release-audit-clean", release_audit.get("ok") is True, "Release staleness and verification audit board is clean for the current release."),
        _row("integrity-not-external-write", ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES["export_integrity_review_writes_external_archive"] is False, "Export integrity review does not write external archives."),
        _row("integrity-not-publish-approval", ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES["integrity_pass_is_publish_approval"] is False, "Integrity pass is not publish approval."),
        _row("no-authority", all(ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES[key] is False for key in ["export_integrity_creates_release", "export_integrity_publishes_release", "export_integrity_runs_commands", "export_integrity_applies_patches", "export_integrity_executes_rollback", "export_integrity_writes_source", "export_integrity_writes_memory", "export_integrity_expands_autonomy"]), "Archive export integrity review grants no release, publish, command, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION,
        "state": "archive_export_integrity_review_review_only",
        "archive_export_integrity_review_id": ARCHIVE_EXPORT_INTEGRITY_REVIEW_ID,
        "review_fields": list(ARCHIVE_EXPORT_INTEGRITY_FIELDS),
        "closure_checklist": {"ok": closure.get("ok"), "state": closure.get("state")},
        "release_audit": {"ok": release_audit.get("ok"), "state": release_audit.get("state")},
        "generated_at": _now_iso(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(ARCHIVE_EXPORT_INTEGRITY_BOUNDARIES),
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_export_decision_closure_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_archive_export_scope_contract(repo)
    packet = build_release_archive_export_packet_prep(repo)
    closure = build_operator_decision_closure_checklist(repo)
    integrity = build_archive_export_integrity_review(repo)
    rows = [
        _row("archive-export-scope", scope.get("ok") is True, "Archive export scope contract is prepared."),
        _row("export-packet", packet.get("ok") is True, "Release archive export packet prep is prepared."),
        _row("operator-decision-closure", closure.get("ok") is True and closure.get("operator_decision_closure_status") == "required", "Operator decision closure checklist is prepared and still requires exact operator decision."),
        _row("archive-export-integrity", integrity.get("ok") is True, "Archive export integrity review is prepared."),
        _row("no-external-archive-write", all(report.get("writes_external_archive") is False for report in [scope, packet, closure, integrity]), "No stage writes external archive records."),
        _row("no-release-publish", all(report.get("creates_release") is False and report.get("publishes_release") is False for report in [scope, packet, closure, integrity]), "No stage creates or publishes releases."),
        _row("no-execution", all(report.get("executes_commands") is False and report.get("applies_patch") is False and report.get("executes_rollback") is False for report in [scope, packet, closure, integrity]), "No stage runs commands, applies patches, or executes rollback."),
        _row("no-source-memory-autonomy", all(report.get("writes_source") is False and report.get("writes_memory") is False and report.get("expands_autonomy") is False for report in [scope, packet, closure, integrity]), "No stage writes source, writes memory, or expands autonomy."),
        _row("board-no-authority", all(RELEASE_ARCHIVE_EXPORT_CLOSURE_BOARD_BOUNDARIES[key] is False for key in ["archive_export_board_is_release_approval", "archive_export_board_is_publish_permission", "archive_export_board_writes_external_archive", "archive_export_board_creates_release", "archive_export_board_publishes_release", "archive_export_board_executes_commands", "archive_export_board_applies_patches", "archive_export_board_executes_rollback", "archive_export_board_writes_source", "archive_export_board_writes_memory", "archive_export_board_invokes_models_by_default", "archive_export_board_schedules_work", "archive_export_board_reuses_approval", "archive_export_board_continues_automatically", "archive_export_board_expands_autonomy"]), "Final board grants no approval, publish, external archive write, release, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION,
        "state": "release_archive_export_decision_closure_board_review_only",
        "release_archive_export_decision_closure_board_id": RELEASE_ARCHIVE_EXPORT_DECISION_CLOSURE_BOARD_ID,
        "archive_export_status": "prepared_not_written_externally",
        "export_packet_status": "prepared",
        "operator_decision_closure_status": "required",
        "archive_export_integrity_status": "review_prepared",
        "external_archive_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "approval_status": "required",
        "authorization_status": "not_authorized",
        "autonomy_status": "not_autonomous",
        "stages": {
            "archive_export_scope_contract": scope,
            "release_archive_export_packet_prep": packet,
            "operator_decision_closure_checklist": closure,
            "archive_export_integrity_review": integrity,
        },
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_ARCHIVE_EXPORT_CLOSURE_BOARD_BOUNDARIES),
        "generated_at": _now_iso(),
        "safe_next_action": "Operator may review the v585 release archive export and decision closure board. Next work should prepare release archive import/closure recall without creating releases automatically, publishing releases, writing external archives without approval, executing rollback, writing memory, or expanding autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_release_archive_export_closure_arc(root: str | Path | None = None, stage: str = "release_archive_export_decision_closure_board_v1") -> dict[str, Any]:
    builders = {
        "archive_export_scope_contract_v1": build_archive_export_scope_contract,
        "release_archive_export_packet_prep_v1": build_release_archive_export_packet_prep,
        "operator_decision_closure_checklist_v1": build_operator_decision_closure_checklist,
        "archive_export_integrity_review_v1": build_archive_export_integrity_review,
        "release_archive_export_decision_closure_board_v1": build_release_archive_export_decision_closure_board,
    }
    return builders.get(stage, build_release_archive_export_decision_closure_board)(root)


def render_release_archive_export_closure_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'release_archive_export_closure')} ({report.get('version', RELEASE_ARCHIVE_EXPORT_CLOSURE_VERSION)})",
        f"status: {report.get('status', 'unknown')} ok={report.get('ok')}",
        f"archive_export_status: {report.get('archive_export_status', 'prepared_not_written_externally')}",
        f"export_packet_status: {report.get('export_packet_status', 'prepared')}",
        f"operator_decision_closure_status: {report.get('operator_decision_closure_status', 'required')}",
        f"archive_export_integrity_status: {report.get('archive_export_integrity_status', 'review_prepared')}",
        f"external_archive_write_status: {report.get('external_archive_write_status', 'not_performed')}",
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


# v581.0-v585.0 release archive export closure tokens: archive-export-scope-contract release-archive-export-packet-prep operator-decision-closure-checklist archive-export-integrity-review release-archive-export-decision-closure-board release-archive-export-and-decision-closure-v1 release_archive_export_closure.py archive_export_prep_writes_external_files=False export_readiness_is_publish_permission=False export_scope_is_release_approval=False export_packet_prep_writes_external_archive=False prepared_packet_is_approval=False closure_checklist_completion_is_automatic_approval=False closure_decision_reusable_for_future_releases=False export_integrity_review_writes_external_archive=False integrity_pass_is_publish_approval=False archive_export_board_is_release_approval=False archive_export_board_is_publish_permission=False archive_export_board_writes_external_archive=False archive_export_board_executes_commands=False archive_export_status=prepared_not_written_externally export_packet_status=prepared operator_decision_closure_status=required archive_export_integrity_status=review_prepared external_archive_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous no_native_title_tooltip data-tip command-deck operator-console
