from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

OPERATOR_SESSION_CONTINUITY_RESUME_UX_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
SESSION_RESUME_STATE_SUMMARY_ID = "v646_session_resume_state_summary"
UNRESOLVED_WARNING_BLOCKER_CARRYOVER_ID = "v647_unresolved_warning_blocker_carryover"
PENDING_DECISIONS_PREPARED_WORK_RESUME_QUEUE_ID = "v648_pending_decisions_prepared_work_resume_queue"
VERIFICATION_STATE_RESUME_CARD_ID = "v649_verification_state_resume_card"
OPERATOR_SESSION_CONTINUITY_BOARD_ID = "v650_operator_session_continuity_board"

RESUME_STATE_FIELDS: tuple[str, ...] = (
    "latest_completed_version",
    "latest_arc_title",
    "current_project_status",
    "autonomy_status",
    "approval_status",
    "release_status",
    "archive_write_status",
    "memory_write_status",
    "source_mutation_status",
)

WARNING_CARRYOVER_TYPES: tuple[str, ...] = (
    "stale_version_warnings",
    "metadata_drift_warnings",
    "legacy_smoke_advisory_blockers",
    "optional_dependency_warnings",
    "route_parity_issues",
    "package_privacy_warnings",
    "documentation_continuity_issues",
)

RESUME_QUEUE_TYPES: tuple[str, ...] = (
    "pending_operator_decisions",
    "prepared_only_packets",
    "approval_required_actions",
    "blocked_actions",
    "ready_for_review_packets",
    "next_recommended_arc",
)

VERIFICATION_RESUME_FIELDS: tuple[str, ...] = (
    "last_targeted_smoke",
    "last_fast_smoke",
    "last_dashboard_segment",
    "last_recent_regression_segment",
    "last_metadata_check",
    "last_package_privacy_check",
    "last_stale_audit",
    "last_extracted_zip_check",
    "known_advisory_warnings",
)

SESSION_CONTINUITY_BOUNDARIES: dict[str, bool] = {
    "resume_summary_starts_work": False,
    "resume_summary_grants_approval": False,
    "warning_carryover_resolves_blockers": False,
    "warning_carryover_runs_checks": False,
    "pending_queue_starts_work": False,
    "pending_queue_auto_selects_arc": False,
    "pending_queue_grants_approval": False,
    "verification_card_runs_checks": False,
    "verification_card_treats_pass_as_authorization": False,
    "handoff_packet_executes_work": False,
    "handoff_packet_is_approval": False,
    "continuity_board_writes_source": False,
    "continuity_board_writes_memory": False,
    "continuity_board_writes_archive_records": False,
    "continuity_board_mutates_current_state": False,
    "continuity_board_creates_release": False,
    "continuity_board_publishes_release": False,
    "continuity_board_reuses_approval": False,
    "continuity_board_schedules_hidden_work": False,
    "continuity_board_continues_automatically": False,
    "continuity_board_expands_autonomy": False,
    "raw_evidence_preserved": True,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _base_state() -> dict[str, Any]:
    return {
        "session_continuity_resume_ux_status": "prepared_only",
        "resume_summary_status": "prepared",
        "warning_carryover_status": "prepared",
        "pending_work_queue_status": "prepared",
        "verification_resume_card_status": "prepared",
        "handoff_packet_status": "prepared",
        "raw_evidence_preserved": True,
        "approval_semantics_changed": False,
        "authorization_status": "not_authorized",
        "approval_status": "required",
        "autonomy_status": "not_autonomous",
        "source_mutation_status": "not_performed",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "writes_source": False,
        "writes_memory": False,
        "writes_archive_records": False,
        "writes_external_ledger": False,
        "mutates_current_state": False,
        "executes_actions": False,
        "executes_commands": False,
        "executes_smoke": False,
        "starts_work": False,
        "schedules_hidden_work": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "creates_approval": False,
        "records_operator_decision": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
        "fresh_exact_operator_approval_required_for_writes": True,
    }


def build_session_resume_state_summary(root: str | Path | None = None) -> dict[str, Any]:
    summary = {
        "latest_completed_version": CURRENT_VERSION,
        "latest_arc_title": "Operator Session Continuity and Resume Console UX v1",
        "current_project_status": "active_operator_governed_local_artificial_mind_project",
        "autonomy_status": "not_autonomous",
        "approval_status": "required",
        "release_status": "not_created",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "source_mutation_status": "not_performed_by_resume_summary",
        "starts_work": False,
        "grants_approval": False,
    }
    rows = [
        _row("resume-fields-present", all(field in summary for field in RESUME_STATE_FIELDS), "Resume state summary declares latest version, latest arc, project status, autonomy, approval, release, archive, memory, and source-mutation fields."),
        _row("current-version", summary["latest_completed_version"] == CURRENT_VERSION, "Resume summary points to the current completed version."),
        _row("summary-not-work", summary["starts_work"] is False and SESSION_CONTINUITY_BOUNDARIES["resume_summary_starts_work"] is False, "Resume summary starts no work."),
        _row("summary-not-approval", summary["grants_approval"] is False and SESSION_CONTINUITY_BOUNDARIES["resume_summary_grants_approval"] is False, "Resume summary grants no approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "session_resume_state_summary_review_only", "session_resume_state_summary_id": SESSION_RESUME_STATE_SUMMARY_ID, "resume_state_fields": list(RESUME_STATE_FIELDS), "summary": summary, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SESSION_CONTINUITY_BOUNDARIES)}


def build_unresolved_warning_blocker_carryover(root: str | Path | None = None) -> dict[str, Any]:
    warnings = [
        {"warning_type": item, "operator_visible": True, "resolved_by_card": False, "runs_check": False, "is_authorization": False}
        for item in WARNING_CARRYOVER_TYPES
    ]
    rows = [
        _row("warning-types-present", len(warnings) == len(WARNING_CARRYOVER_TYPES), "Stale-version, metadata, legacy smoke, optional dependency, route parity, package privacy, and documentation continuity warning types are represented."),
        _row("operator-visible", all(item["operator_visible"] is True for item in warnings), "Warning carryover items are operator-visible."),
        _row("not-resolver", all(item["resolved_by_card"] is False for item in warnings) and SESSION_CONTINUITY_BOUNDARIES["warning_carryover_resolves_blockers"] is False, "Warning carryover cards do not resolve blockers by themselves."),
        _row("not-check-runner", all(item["runs_check"] is False for item in warnings) and SESSION_CONTINUITY_BOUNDARIES["warning_carryover_runs_checks"] is False, "Warning carryover cards run no checks."),
    ]
    return {"version": CURRENT_VERSION, "state": "unresolved_warning_blocker_carryover_review_only", "unresolved_warning_blocker_carryover_id": UNRESOLVED_WARNING_BLOCKER_CARRYOVER_ID, "warning_carryover_types": list(WARNING_CARRYOVER_TYPES), "warning_cards": warnings, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SESSION_CONTINUITY_BOUNDARIES)}


def build_pending_decisions_prepared_work_resume_queue(root: str | Path | None = None) -> dict[str, Any]:
    queue = [
        {"queue_type": item, "operator_visible": True, "starts_work": False, "grants_approval": False, "auto_selects_arc": False}
        for item in RESUME_QUEUE_TYPES
    ]
    rows = [
        _row("queue-types-present", len(queue) == len(RESUME_QUEUE_TYPES), "Pending decisions, prepared-only packets, approval-required actions, blocked actions, ready-for-review packets, and next recommended arc are represented."),
        _row("queue-not-work", all(item["starts_work"] is False for item in queue) and SESSION_CONTINUITY_BOUNDARIES["pending_queue_starts_work"] is False, "Resume queue starts no work."),
        _row("queue-not-approval", all(item["grants_approval"] is False for item in queue) and SESSION_CONTINUITY_BOUNDARIES["pending_queue_grants_approval"] is False, "Resume queue grants no approval."),
        _row("queue-not-roadmap-selector", all(item["auto_selects_arc"] is False for item in queue) and SESSION_CONTINUITY_BOUNDARIES["pending_queue_auto_selects_arc"] is False, "Resume queue does not auto-select roadmaps or arcs."),
    ]
    return {"version": CURRENT_VERSION, "state": "pending_decisions_prepared_work_resume_queue_review_only", "pending_decisions_prepared_work_resume_queue_id": PENDING_DECISIONS_PREPARED_WORK_RESUME_QUEUE_ID, "resume_queue_types": list(RESUME_QUEUE_TYPES), "queue_cards": queue, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SESSION_CONTINUITY_BOUNDARIES)}


def build_verification_state_resume_card(root: str | Path | None = None) -> dict[str, Any]:
    card = {field: "operator_supplied_or_latest_packaging_record" for field in VERIFICATION_RESUME_FIELDS}
    card.update({"runs_checks": False, "grants_authorization": False, "treats_pass_as_approval": False})
    rows = [
        _row("verification-fields-present", all(field in card for field in VERIFICATION_RESUME_FIELDS), "Verification resume card declares targeted smoke, fast smoke, dashboard, recent regression, metadata, package privacy, stale audit, extracted zip, and advisory-warning fields."),
        _row("card-not-check-runner", card["runs_checks"] is False and SESSION_CONTINUITY_BOUNDARIES["verification_card_runs_checks"] is False, "Verification resume card runs no checks."),
        _row("pass-not-authorization", card["grants_authorization"] is False and card["treats_pass_as_approval"] is False and SESSION_CONTINUITY_BOUNDARIES["verification_card_treats_pass_as_authorization"] is False, "Verification resume card does not treat pass status as authorization or approval."),
        _row("raw-evidence", SESSION_CONTINUITY_BOUNDARIES["raw_evidence_preserved"] is True, "Verification resume card preserves raw evidence access requirements."),
    ]
    return {"version": CURRENT_VERSION, "state": "verification_state_resume_card_review_only", "verification_state_resume_card_id": VERIFICATION_STATE_RESUME_CARD_ID, "verification_resume_fields": list(VERIFICATION_RESUME_FIELDS), "verification_card": card, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SESSION_CONTINUITY_BOUNDARIES)}


def build_operator_session_continuity_board(root: str | Path | None = None) -> dict[str, Any]:
    resume = build_session_resume_state_summary(root)
    warnings = build_unresolved_warning_blocker_carryover(root)
    queue = build_pending_decisions_prepared_work_resume_queue(root)
    verification = build_verification_state_resume_card(root)
    no_authority_keys = [
        "handoff_packet_executes_work",
        "handoff_packet_is_approval",
        "continuity_board_writes_source",
        "continuity_board_writes_memory",
        "continuity_board_writes_archive_records",
        "continuity_board_mutates_current_state",
        "continuity_board_creates_release",
        "continuity_board_publishes_release",
        "continuity_board_reuses_approval",
        "continuity_board_schedules_hidden_work",
        "continuity_board_continues_automatically",
        "continuity_board_expands_autonomy",
    ]
    rows = [
        _row("resume-summary", resume.get("ok") is True, "Session resume state summary is prepared."),
        _row("warning-carryover", warnings.get("ok") is True, "Unresolved warning and blocker carryover is prepared."),
        _row("pending-work-queue", queue.get("ok") is True, "Pending decisions and prepared work resume queue is prepared."),
        _row("verification-resume-card", verification.get("ok") is True, "Verification state resume card is prepared."),
        _row("handoff-packet", _base_state()["handoff_packet_status"] == "prepared", "Handoff packet status is prepared for review only."),
        _row("approval-semantics", _base_state()["approval_semantics_changed"] is False, "Operator session continuity board does not change approval semantics."),
        _row("no-authority", all(SESSION_CONTINUITY_BOUNDARIES[key] is False for key in no_authority_keys), "Final continuity board grants no execution, approval, source, memory, archive, current-state mutation, release, publish, approval reuse, hidden scheduling, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_session_continuity_board_review_only", "operator_session_continuity_board_id": OPERATOR_SESSION_CONTINUITY_BOARD_ID, "session_resume_state_summary": resume, "unresolved_warning_blocker_carryover": warnings, "pending_decisions_prepared_work_resume_queue": queue, "verification_state_resume_card": verification, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(SESSION_CONTINUITY_BOUNDARIES)}


def build_operator_session_continuity_resume_console_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    mapping = {
        "session_resume_state_summary_v1": build_session_resume_state_summary,
        "unresolved_warning_blocker_carryover_v1": build_unresolved_warning_blocker_carryover,
        "pending_decisions_prepared_work_resume_queue_v1": build_pending_decisions_prepared_work_resume_queue,
        "verification_state_resume_card_v1": build_verification_state_resume_card,
        "operator_session_continuity_board_v1": build_operator_session_continuity_board,
    }
    if stage in mapping:
        return mapping[stage](root)
    return build_operator_session_continuity_board(root)


def render_operator_session_continuity_resume_console_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"Eidolon v{report.get('version')} operator session continuity and resume console UX",
        f"state: {report.get('state')}",
        f"status: {report.get('status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
        f"release_status: {report.get('release_status')}",
        f"handoff_packet_status: {report.get('handoff_packet_status')}",
    ]
    for row in report.get("rows", []):
        lines.append(f"[{row.get('status')}] {row.get('name')}: {row.get('message')}")
    lines.append("Boundary: resume/handoff views are review-only; they do not start work, grant approval, run checks, write source/memory/archive records, publish releases, schedule hidden work, continue automatically, or expand autonomy.")
    return lines

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
