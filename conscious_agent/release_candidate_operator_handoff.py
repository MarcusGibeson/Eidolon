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
from recovery_drill_release_closure import build_recovery_drill_release_closure_board

RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
RELEASE_CANDIDATE_SCOPE_ID = "v561_release_candidate_scope_contract"
CANDIDATE_PACKAGE_INTEGRITY_ID = "v562_candidate_package_integrity_review"
CANDIDATE_VERIFICATION_MATRIX_ID = "v563_candidate_verification_evidence_matrix"
OPERATOR_HANDOFF_PACKET_ID = "v564_operator_release_handoff_packet"
RELEASE_CANDIDATE_HANDOFF_BOARD_ID = "v565_release_candidate_integrity_handoff_board"

RELEASE_CANDIDATE_SCOPE_FIELDS: tuple[str, ...] = (
    "candidate_version_identity",
    "source_only_package_expectations",
    "verification_evidence_requirements",
    "release_notes_requirements",
    "package_privacy_requirements",
    "known_warnings",
    "known_blockers",
    "operator_notes",
)

PACKAGE_INTEGRITY_FIELDS: tuple[str, ...] = (
    "source_only_package_path",
    "zip_entry_inventory",
    "forbidden_path_scan",
    "compiled_artifact_scan",
    "runtime_memory_autonomy_log_scan",
    "metadata_version_alignment",
    "package_privacy_result",
)

VERIFICATION_EVIDENCE_FIELDS: tuple[str, ...] = (
    "compile_evidence",
    "targeted_smoke_evidence",
    "fast_smoke_evidence",
    "install_governance_evidence",
    "install_dashboard_evidence",
    "install_release_evidence",
    "install_regression_recent_evidence",
    "install_memory_evidence",
    "install_expression_evidence",
    "install_live_trial_evidence",
    "dashboard_route_evidence",
    "api_dispatch_evidence",
    "cli_dispatch_evidence",
    "extracted_zip_evidence",
    "stale_version_audit_evidence",
    "package_privacy_evidence",
)

OPERATOR_HANDOFF_FIELDS: tuple[str, ...] = (
    "candidate_summary",
    "changed_surfaces",
    "verification_checklist",
    "unresolved_warnings",
    "rollback_recovery_reference",
    "release_closure_reference",
    "operator_decision_options",
    "single_use_approval_notice",
)

RELEASE_CANDIDATE_SCOPE_BOUNDARIES: dict[str, bool] = {
    "release_candidate_scope_is_release_creation": False,
    "release_candidate_readiness_is_publish_approval": False,
    "release_candidate_scope_runs_commands": False,
    "release_candidate_scope_applies_patches": False,
    "release_candidate_scope_executes_rollback": False,
    "release_candidate_scope_writes_source": False,
    "release_candidate_scope_writes_memory": False,
    "release_candidate_scope_creates_release": False,
    "release_candidate_scope_publishes_release": False,
    "release_candidate_scope_expands_autonomy": False,
    "operator_review_required": True,
}

PACKAGE_INTEGRITY_BOUNDARIES: dict[str, bool] = {
    "package_integrity_review_is_release_approval": False,
    "package_privacy_pass_is_publish_permission": False,
    "package_integrity_review_creates_release": False,
    "package_integrity_review_publishes_release": False,
    "package_integrity_review_applies_patches": False,
    "package_integrity_review_executes_rollback": False,
    "package_integrity_review_writes_source": False,
    "package_integrity_review_writes_memory": False,
    "package_integrity_review_expands_autonomy": False,
    "operator_review_required": True,
}

VERIFICATION_EVIDENCE_BOUNDARIES: dict[str, bool] = {
    "verification_evidence_is_authorization": False,
    "passing_checks_approve_release": False,
    "verification_matrix_runs_commands": False,
    "verification_matrix_applies_patches": False,
    "verification_matrix_executes_rollback": False,
    "verification_matrix_creates_release": False,
    "verification_matrix_publishes_release": False,
    "verification_matrix_writes_source": False,
    "verification_matrix_writes_memory": False,
    "verification_matrix_expands_autonomy": False,
    "operator_supplied_evidence_required": True,
    "operator_review_required": True,
}

OPERATOR_HANDOFF_BOUNDARIES: dict[str, bool] = {
    "handoff_packet_is_operator_approval": False,
    "handoff_preparation_creates_release": False,
    "handoff_packet_publishes_release": False,
    "handoff_packet_applies_patches": False,
    "handoff_packet_executes_rollback": False,
    "handoff_packet_runs_commands": False,
    "handoff_packet_writes_source": False,
    "handoff_packet_writes_memory": False,
    "handoff_packet_reuses_approval": False,
    "handoff_packet_continues_automatically": False,
    "handoff_packet_expands_autonomy": False,
    "operator_review_required": True,
}

RELEASE_CANDIDATE_HANDOFF_BOUNDARIES: dict[str, bool] = {
    "candidate_board_is_release_creation": False,
    "candidate_board_is_publish_approval": False,
    "candidate_board_is_operator_approval": False,
    "candidate_board_executes_commands": False,
    "candidate_board_applies_patches": False,
    "candidate_board_executes_rollback": False,
    "candidate_board_writes_source": False,
    "candidate_board_writes_memory": False,
    "candidate_board_creates_release": False,
    "candidate_board_publishes_release": False,
    "candidate_board_invokes_models_by_default": False,
    "candidate_board_schedules_work": False,
    "candidate_board_reuses_approval": False,
    "candidate_board_continues_automatically": False,
    "candidate_board_expands_autonomy": False,
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
        "release_candidate_status": "prepared_not_created",
        "package_integrity_status": "review_prepared",
        "verification_evidence_status": "matrix_prepared",
        "operator_handoff_status": "prepared",
        "release_closure_status": "evidence_prepared",
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


def build_release_candidate_scope_contract(root: str | Path | None = None, candidate_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(RELEASE_CANDIDATE_SCOPE_FIELDS, candidate_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    symbol_audit = build_current_symbol_staleness_audit(repo)
    recovery_board = build_recovery_drill_release_closure_board(repo)
    rows = [
        _row("scope-schema-defined", len(RELEASE_CANDIDATE_SCOPE_FIELDS) >= 8, "Release candidate scope covers candidate identity, package expectations, verification evidence, release notes, privacy requirements, warnings, blockers, and operator notes."),
        _row("missing-scope-awaits", len(missing) == len(RELEASE_CANDIDATE_SCOPE_FIELDS), "With no operator candidate packet supplied, the layer remains prepared/not created rather than claiming release candidate creation."),
        _row("previous-closure-board-available", recovery_board.get("ok") is True, "v560 recovery drill and release closure board remains available as input context."),
        _row("staleness-clean", stale_scanner.get("ok") is True and symbol_audit.get("ok") is True, "Current stale-version and current-symbol audits are clean before packaging."),
        _row("scope-not-release", RELEASE_CANDIDATE_SCOPE_BOUNDARIES["release_candidate_scope_is_release_creation"] is False and RELEASE_CANDIDATE_SCOPE_BOUNDARIES["release_candidate_readiness_is_publish_approval"] is False, "Release candidate scope is not release creation and readiness is not publish approval."),
        _row("no-authority", all(RELEASE_CANDIDATE_SCOPE_BOUNDARIES[key] is False for key in ["release_candidate_scope_runs_commands", "release_candidate_scope_applies_patches", "release_candidate_scope_executes_rollback", "release_candidate_scope_writes_source", "release_candidate_scope_writes_memory", "release_candidate_scope_creates_release", "release_candidate_scope_publishes_release", "release_candidate_scope_expands_autonomy"]), "Release candidate scope grants no command, patch, rollback, source, memory, release, publish, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION,
        "state": "release_candidate_scope_contract_review_only",
        "release_candidate_scope_id": RELEASE_CANDIDATE_SCOPE_ID,
        "scope_fields": list(RELEASE_CANDIDATE_SCOPE_FIELDS),
        "missing_scope_fields": missing,
        "previous_closure_summary": {"ok": recovery_board.get("ok"), "state": recovery_board.get("state")},
        "stale_version_string_scanner": stale_scanner,
        "current_symbol_staleness_audit": symbol_audit,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_CANDIDATE_SCOPE_BOUNDARIES),
        "safe_next_action": "Operator may review release candidate scope. It does not create or publish a release, run commands, apply patches, execute rollback, write memory, or expand autonomy.",
    }
    report.update(_base_authority_state())
    return report


def build_candidate_package_integrity_review(root: str | Path | None = None, package_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(PACKAGE_INTEGRITY_FIELDS, package_packet)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("package-schema-defined", len(PACKAGE_INTEGRITY_FIELDS) >= 7, "Package integrity review covers source-only package path, inventory, forbidden path scan, compiled artifacts, runtime logs, metadata alignment, and privacy result."),
        _row("missing-package-awaits", len(missing) == len(PACKAGE_INTEGRITY_FIELDS), "With no operator package packet supplied, package integrity remains review-prepared rather than release-approved."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Central release staleness verification board is clean."),
        _row("privacy-not-publish", PACKAGE_INTEGRITY_BOUNDARIES["package_integrity_review_is_release_approval"] is False and PACKAGE_INTEGRITY_BOUNDARIES["package_privacy_pass_is_publish_permission"] is False, "Package integrity review and privacy pass do not approve or publish release."),
        _row("no-authority", all(PACKAGE_INTEGRITY_BOUNDARIES[key] is False for key in ["package_integrity_review_creates_release", "package_integrity_review_publishes_release", "package_integrity_review_applies_patches", "package_integrity_review_executes_rollback", "package_integrity_review_writes_source", "package_integrity_review_writes_memory", "package_integrity_review_expands_autonomy"]), "Package integrity review grants no release, publish, patch, rollback, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION,
        "state": "candidate_package_integrity_review_only",
        "candidate_package_integrity_id": CANDIDATE_PACKAGE_INTEGRITY_ID,
        "package_fields": list(PACKAGE_INTEGRITY_FIELDS),
        "missing_package_fields": missing,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(PACKAGE_INTEGRITY_BOUNDARIES),
        "safe_next_action": "Operator may review package integrity evidence. Review does not create or publish a release and does not authorize future action.",
    }
    report.update(_base_authority_state())
    return report


def build_candidate_verification_evidence_matrix(root: str | Path | None = None, verification_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = _repo(root)
    missing = _missing(VERIFICATION_EVIDENCE_FIELDS, verification_packet)
    stale_scanner = build_stale_version_string_scanner(repo)
    rows = [
        _row("verification-schema-defined", len(VERIFICATION_EVIDENCE_FIELDS) >= 16, "Verification matrix covers compile, targeted smoke, fast smoke, install tiers, dashboard, API, CLI, extracted zip, stale audit, and package privacy evidence."),
        _row("missing-evidence-awaits", len(missing) == len(VERIFICATION_EVIDENCE_FIELDS), "With no operator evidence supplied, the matrix remains prepared rather than claiming verification completion."),
        _row("stale-scan-clean", stale_scanner.get("ok") is True, "Stale-version scan is clean before packaging."),
        _row("evidence-not-authorization", VERIFICATION_EVIDENCE_BOUNDARIES["verification_evidence_is_authorization"] is False and VERIFICATION_EVIDENCE_BOUNDARIES["passing_checks_approve_release"] is False, "Verification evidence and passing checks do not authorize or approve release."),
        _row("no-authority", all(VERIFICATION_EVIDENCE_BOUNDARIES[key] is False for key in ["verification_matrix_runs_commands", "verification_matrix_applies_patches", "verification_matrix_executes_rollback", "verification_matrix_creates_release", "verification_matrix_publishes_release", "verification_matrix_writes_source", "verification_matrix_writes_memory", "verification_matrix_expands_autonomy"]), "Verification matrix grants no command, patch, rollback, release, publish, source, memory, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION,
        "state": "candidate_verification_evidence_matrix_review_only",
        "candidate_verification_matrix_id": CANDIDATE_VERIFICATION_MATRIX_ID,
        "verification_fields": list(VERIFICATION_EVIDENCE_FIELDS),
        "missing_verification_fields": missing,
        "stale_version_string_scanner": stale_scanner,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(VERIFICATION_EVIDENCE_BOUNDARIES),
        "safe_next_action": "Operator may review verification evidence. Matrix does not run commands, approve release, publish release, or authorize rollback.",
    }
    report.update(_base_authority_state())
    return report


def build_operator_release_handoff_packet(root: str | Path | None = None, handoff_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = _missing(OPERATOR_HANDOFF_FIELDS, handoff_packet)
    rows = [
        _row("handoff-schema-defined", len(OPERATOR_HANDOFF_FIELDS) >= 8, "Handoff packet covers summary, changed surfaces, verification checklist, unresolved warnings, rollback/recovery reference, release closure reference, decision options, and single-use approval notice."),
        _row("missing-handoff-awaits", len(missing) == len(OPERATOR_HANDOFF_FIELDS), "With no operator handoff packet supplied, handoff remains prepared rather than approved."),
        _row("handoff-not-approval", OPERATOR_HANDOFF_BOUNDARIES["handoff_packet_is_operator_approval"] is False and OPERATOR_HANDOFF_BOUNDARIES["handoff_preparation_creates_release"] is False, "Operator handoff packet is not approval and preparation does not create release."),
        _row("no-authority", all(OPERATOR_HANDOFF_BOUNDARIES[key] is False for key in ["handoff_packet_publishes_release", "handoff_packet_applies_patches", "handoff_packet_executes_rollback", "handoff_packet_runs_commands", "handoff_packet_writes_source", "handoff_packet_writes_memory", "handoff_packet_reuses_approval", "handoff_packet_continues_automatically", "handoff_packet_expands_autonomy"]), "Operator handoff packet grants no publish, patch, rollback, command, source, memory, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION,
        "state": "operator_release_handoff_packet_review_only",
        "operator_handoff_packet_id": OPERATOR_HANDOFF_PACKET_ID,
        "handoff_fields": list(OPERATOR_HANDOFF_FIELDS),
        "missing_handoff_fields": missing,
        "decision_options": ["approve closure review only", "request revision", "block release candidate", "request rollback review", "defer decision"],
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(OPERATOR_HANDOFF_BOUNDARIES),
        "safe_next_action": "Operator may review the handoff packet. Packet does not create approval, create or publish release, run commands, apply patches, or continue automatically.",
    }
    report.update(_base_authority_state())
    return report


def build_release_candidate_integrity_handoff_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    scope = build_release_candidate_scope_contract(repo)
    package = build_candidate_package_integrity_review(repo)
    matrix = build_candidate_verification_evidence_matrix(repo)
    handoff = build_operator_release_handoff_packet(repo)
    release_stale = build_release_staleness_and_verification_audit_board(repo)
    rows = [
        _row("scope-prepared", scope.get("ok") is True and scope.get("creates_release") is False, "Release candidate scope contract is prepared and does not create releases."),
        _row("package-review-prepared", package.get("ok") is True and package.get("publishes_release") is False, "Candidate package integrity review is prepared and does not publish releases."),
        _row("verification-matrix-prepared", matrix.get("ok") is True and matrix.get("executes_commands") is False, "Candidate verification evidence matrix is prepared and does not run commands."),
        _row("handoff-prepared", handoff.get("ok") is True and handoff.get("approval_status") == "required", "Operator handoff packet is prepared and still requires operator approval."),
        _row("release-staleness-clean", release_stale.get("ok") is True, "Release staleness audit remains clean for current-state fields."),
        _row("no-execution", all(item.get("executes_commands") is False and item.get("executes_rollback") is False for item in [scope, package, matrix, handoff]), "No v561-v565 release candidate layer runs commands or executes rollback."),
        _row("no-authority", all(RELEASE_CANDIDATE_HANDOFF_BOUNDARIES[key] is False for key in ["candidate_board_is_release_creation", "candidate_board_is_publish_approval", "candidate_board_is_operator_approval", "candidate_board_executes_commands", "candidate_board_applies_patches", "candidate_board_executes_rollback", "candidate_board_writes_source", "candidate_board_writes_memory", "candidate_board_creates_release", "candidate_board_publishes_release", "candidate_board_invokes_models_by_default", "candidate_board_schedules_work", "candidate_board_reuses_approval", "candidate_board_continues_automatically", "candidate_board_expands_autonomy"]), "Release candidate handoff board grants no release, publish, approval, command, patch, rollback, source, memory, model, schedule, approval reuse, continuation, or autonomy authority."),
    ]
    report = {
        "version": RELEASE_CANDIDATE_OPERATOR_HANDOFF_VERSION,
        "state": "release_candidate_integrity_handoff_board_review_only",
        "release_candidate_handoff_board_id": RELEASE_CANDIDATE_HANDOFF_BOARD_ID,
        "release_candidate_scope_contract": scope,
        "candidate_package_integrity_review": package,
        "candidate_verification_evidence_matrix": matrix,
        "operator_release_handoff_packet": handoff,
        "release_staleness_audit_board": release_stale,
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(RELEASE_CANDIDATE_HANDOFF_BOUNDARIES),
        "safe_next_action": "Operator may review v565 release candidate integrity and handoff board. It does not create releases, publish releases, run commands, apply patches, execute rollback, write memory, or make Eidolon autonomous.",
    }
    report.update(_base_authority_state())
    return report


def build_release_candidate_operator_handoff_arc(root: str | Path | None = None, stage: str = "release_candidate_integrity_handoff_board_v1") -> dict[str, Any]:
    builders = {
        "release_candidate_scope_contract_v1": build_release_candidate_scope_contract,
        "candidate_package_integrity_review_v1": build_candidate_package_integrity_review,
        "candidate_verification_evidence_matrix_v1": build_candidate_verification_evidence_matrix,
        "operator_release_handoff_packet_v1": build_operator_release_handoff_packet,
        "release_candidate_integrity_handoff_board_v1": build_release_candidate_integrity_handoff_board,
    }
    return builders.get(stage, build_release_candidate_integrity_handoff_board)(root)


def render_release_candidate_operator_handoff_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"release_candidate_status: {report.get('release_candidate_status')}",
        f"package_integrity_status: {report.get('package_integrity_status')}",
        f"verification_evidence_status: {report.get('verification_evidence_status')}",
        f"operator_handoff_status: {report.get('operator_handoff_status')}",
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

# v561.0-v565.0 release candidate integrity operator handoff tokens: release-candidate-scope-contract candidate-package-integrity-review candidate-verification-evidence-matrix operator-release-handoff-packet release-candidate-integrity-handoff-board release-candidate-integrity-and-operator-handoff-v1 release_candidate_operator_handoff.py release_candidate_scope_is_release_creation=False release_candidate_readiness_is_publish_approval=False package_integrity_review_is_release_approval=False package_privacy_pass_is_publish_permission=False verification_evidence_is_authorization=False passing_checks_approve_release=False handoff_packet_is_operator_approval=False handoff_preparation_creates_release=False candidate_board_is_release_creation=False candidate_board_is_publish_approval=False candidate_board_executes_commands=False candidate_board_creates_release=False candidate_board_publishes_release=False release_candidate_status=prepared_not_created package_integrity_status=review_prepared verification_evidence_status=matrix_prepared operator_handoff_status=prepared release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous
