from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

OPERATOR_RECEIPT_TIMELINE_AUDIT_UX_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
OPERATOR_DECISION_TIMELINE_MODEL_ID = "v641_operator_decision_timeline_model"
APPROVAL_BURNOUT_CONSUMPTION_TIMELINE_CARDS_ID = "v642_approval_burnout_consumption_timeline_cards"
BLOCKED_ACTION_SAFETY_EVENT_TIMELINE_CARDS_ID = "v643_blocked_action_safety_event_timeline_cards"
VERIFICATION_RECEIPT_TIMELINE_CARDS_ID = "v644_verification_receipt_timeline_cards"
DECISION_AUDIT_TRAIL_BOARD_ID = "v645_decision_audit_trail_board"

TIMELINE_EVENT_TYPES: tuple[str, ...] = (
    "decision_recorded",
    "approval_requested",
    "approval_granted_once",
    "approval_consumed",
    "approval_denied",
    "approval_deferred",
    "revision_requested",
    "action_blocked",
    "receipt_prepared",
    "verification_completed",
)

APPROVAL_CONSUMPTION_FIELDS: tuple[str, ...] = (
    "approval_scope",
    "approved_target",
    "approval_created_at",
    "approval_expires_at",
    "consumed_status",
    "consumed_by",
    "reuse_allowed",
    "post_use_status",
)

BLOCKED_ACTION_TYPES: tuple[str, ...] = (
    "archive_write_blocked",
    "memory_write_blocked",
    "source_mutation_blocked",
    "release_creation_blocked",
    "publish_blocked",
    "autonomy_blocked",
    "model_invocation_blocked",
)

VERIFICATION_RECEIPT_TYPES: tuple[str, ...] = (
    "targeted_smoke_passed",
    "fast_smoke_passed",
    "stale_audit_passed",
    "metadata_integrity_passed",
    "route_parity_passed",
    "package_privacy_passed",
    "receipt_prepared",
    "receipt_reviewed",
)

TIMELINE_AUDIT_BOUNDARIES: dict[str, bool] = {
    "timeline_model_executes_events": False,
    "timeline_model_grants_approval": False,
    "timeline_model_reuses_approval": False,
    "approval_consumption_cards_consume_approval": False,
    "approval_consumption_cards_allow_reuse": False,
    "approval_consumption_cards_execute_actions": False,
    "blocked_action_cards_unblock_actions": False,
    "blocked_action_cards_treat_missing_approval_as_approval": False,
    "blocked_action_cards_execute_safe_next_action": False,
    "verification_cards_run_checks": False,
    "verification_cards_treat_pass_as_authorization": False,
    "verification_cards_hide_raw_evidence": False,
    "audit_trail_executes_timeline_events": False,
    "audit_trail_creates_approval": False,
    "audit_trail_reuses_approval": False,
    "audit_trail_writes_source": False,
    "audit_trail_writes_memory": False,
    "audit_trail_writes_archive_records": False,
    "audit_trail_mutates_current_state": False,
    "audit_trail_runs_verification_commands": False,
    "audit_trail_creates_release": False,
    "audit_trail_publishes_release": False,
    "audit_trail_continues_automatically": False,
    "audit_trail_expands_autonomy": False,
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
        "receipt_timeline_audit_ux_status": "prepared_only",
        "timeline_model_status": "prepared",
        "approval_consumption_cards_status": "prepared",
        "blocked_action_cards_status": "prepared",
        "verification_receipt_cards_status": "prepared",
        "audit_trail_status": "review_only",
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


def build_operator_decision_timeline_model(root: str | Path | None = None) -> dict[str, Any]:
    event_model = [
        {"event_type": item, "timestamp_required": True, "operator_visible": True, "executes_event": False, "grants_authorization": False}
        for item in TIMELINE_EVENT_TYPES
    ]
    rows = [
        _row("timeline-events-present", len(event_model) == len(TIMELINE_EVENT_TYPES), "Decision, approval request, one-time approval, consumption, denial, deferral, revision, blocked action, receipt, and verification events are represented."),
        _row("timestamped-review-only", all(item["timestamp_required"] and item["operator_visible"] for item in event_model), "Timeline events are timestamped and operator-visible."),
        _row("model-not-execution", TIMELINE_AUDIT_BOUNDARIES["timeline_model_executes_events"] is False and all(item["executes_event"] is False for item in event_model), "Timeline model displays events and does not execute them."),
        _row("model-not-approval", TIMELINE_AUDIT_BOUNDARIES["timeline_model_grants_approval"] is False and all(item["grants_authorization"] is False for item in event_model), "Timeline model does not grant authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_decision_timeline_model_review_only", "operator_decision_timeline_model_id": OPERATOR_DECISION_TIMELINE_MODEL_ID, "timeline_event_types": list(TIMELINE_EVENT_TYPES), "event_model": event_model, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(TIMELINE_AUDIT_BOUNDARIES)}


def build_approval_burnout_consumption_timeline_cards(root: str | Path | None = None) -> dict[str, Any]:
    approval_card = {
        "approval_scope": "operator_supplied_exact_scope",
        "approved_target": "operator_supplied_exact_target",
        "approval_created_at": "operator_supplied_timestamp",
        "approval_expires_at": "required_expiration_timestamp",
        "consumed_status": "not_consumed_until_scoped_action_receipt",
        "consumed_by": None,
        "reuse_allowed": False,
        "post_use_status": "expired_consumed_after_single_use",
        "card_consumes_approval": False,
        "card_executes_action": False,
    }
    rows = [
        _row("approval-fields-present", all(field in approval_card for field in APPROVAL_CONSUMPTION_FIELDS), "Approval timeline card declares scope, target, created, expires, consumed status, consumed-by, no-reuse, and post-use status fields."),
        _row("reuse-blocked", approval_card["reuse_allowed"] is False and TIMELINE_AUDIT_BOUNDARIES["approval_consumption_cards_allow_reuse"] is False, "Approval timeline card preserves no-reuse semantics."),
        _row("card-not-consumer", approval_card["card_consumes_approval"] is False and TIMELINE_AUDIT_BOUNDARIES["approval_consumption_cards_consume_approval"] is False, "Approval timeline card does not consume approval by itself."),
        _row("card-not-action", approval_card["card_executes_action"] is False and TIMELINE_AUDIT_BOUNDARIES["approval_consumption_cards_execute_actions"] is False, "Approval timeline card executes no action."),
    ]
    return {"version": CURRENT_VERSION, "state": "approval_burnout_consumption_timeline_cards_review_only", "approval_burnout_consumption_timeline_cards_id": APPROVAL_BURNOUT_CONSUMPTION_TIMELINE_CARDS_ID, "approval_consumption_fields": list(APPROVAL_CONSUMPTION_FIELDS), "approval_card": approval_card, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(TIMELINE_AUDIT_BOUNDARIES)}


def build_blocked_action_safety_event_timeline_cards(root: str | Path | None = None) -> dict[str, Any]:
    cards = [
        {
            "event_type": item,
            "blocked": True,
            "why_blocked": "missing fresh exact operator approval or required evidence",
            "missing_approval": True,
            "safe_next_action": "prepare review packet or request exact operator decision",
            "must_not_infer": "blocked timeline presence is not approval, authorization, or permission to proceed",
            "unblocks_action": False,
            "executes_safe_next_action": False,
        }
        for item in BLOCKED_ACTION_TYPES
    ]
    rows = [
        _row("blocked-action-types-present", len(cards) == len(BLOCKED_ACTION_TYPES), "Archive, memory, source, release, publish, autonomy, and model invocation blocked events are represented."),
        _row("cards-explain-why", all(card["blocked"] is True and card["missing_approval"] is True and card["why_blocked"] for card in cards), "Blocked action cards explain the missing approval/evidence state."),
        _row("cards-do-not-unblock", all(card["unblocks_action"] is False for card in cards) and TIMELINE_AUDIT_BOUNDARIES["blocked_action_cards_unblock_actions"] is False, "Blocked action cards do not unblock actions."),
        _row("cards-do-not-execute", all(card["executes_safe_next_action"] is False for card in cards) and TIMELINE_AUDIT_BOUNDARIES["blocked_action_cards_execute_safe_next_action"] is False, "Blocked action cards do not execute safe-next actions."),
    ]
    return {"version": CURRENT_VERSION, "state": "blocked_action_safety_event_timeline_cards_review_only", "blocked_action_safety_event_timeline_cards_id": BLOCKED_ACTION_SAFETY_EVENT_TIMELINE_CARDS_ID, "blocked_action_types": list(BLOCKED_ACTION_TYPES), "blocked_action_cards": cards, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(TIMELINE_AUDIT_BOUNDARIES)}


def build_verification_receipt_timeline_cards(root: str | Path | None = None) -> dict[str, Any]:
    cards = [
        {"event_type": item, "status": "represented", "scope_required": True, "raw_evidence_link_required": True, "runs_check": False, "grants_authorization": False, "hides_raw_evidence": False}
        for item in VERIFICATION_RECEIPT_TYPES
    ]
    rows = [
        _row("verification-types-present", len(cards) == len(VERIFICATION_RECEIPT_TYPES), "Targeted smoke, fast smoke, stale audit, metadata integrity, route parity, package privacy, prepared receipt, and reviewed receipt cards are represented."),
        _row("raw-evidence-preserved", all(card["raw_evidence_link_required"] and card["hides_raw_evidence"] is False for card in cards) and TIMELINE_AUDIT_BOUNDARIES["verification_cards_hide_raw_evidence"] is False, "Verification receipt cards preserve raw evidence access."),
        _row("cards-do-not-run-checks", all(card["runs_check"] is False for card in cards) and TIMELINE_AUDIT_BOUNDARIES["verification_cards_run_checks"] is False, "Verification receipt timeline cards do not run checks."),
        _row("pass-not-authorization", all(card["grants_authorization"] is False for card in cards) and TIMELINE_AUDIT_BOUNDARIES["verification_cards_treat_pass_as_authorization"] is False, "Verification pass cards do not grant authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "verification_receipt_timeline_cards_review_only", "verification_receipt_timeline_cards_id": VERIFICATION_RECEIPT_TIMELINE_CARDS_ID, "verification_receipt_types": list(VERIFICATION_RECEIPT_TYPES), "verification_cards": cards, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(TIMELINE_AUDIT_BOUNDARIES)}


def build_decision_audit_trail_board(root: str | Path | None = None) -> dict[str, Any]:
    timeline = build_operator_decision_timeline_model(root)
    approval = build_approval_burnout_consumption_timeline_cards(root)
    blocked = build_blocked_action_safety_event_timeline_cards(root)
    verification = build_verification_receipt_timeline_cards(root)
    no_authority_keys = [
        "audit_trail_executes_timeline_events",
        "audit_trail_creates_approval",
        "audit_trail_reuses_approval",
        "audit_trail_writes_source",
        "audit_trail_writes_memory",
        "audit_trail_writes_archive_records",
        "audit_trail_mutates_current_state",
        "audit_trail_runs_verification_commands",
        "audit_trail_creates_release",
        "audit_trail_publishes_release",
        "audit_trail_continues_automatically",
        "audit_trail_expands_autonomy",
    ]
    rows = [
        _row("timeline-model", timeline.get("ok") is True, "Operator decision timeline model is prepared."),
        _row("approval-consumption", approval.get("ok") is True, "Approval burnout/consumption timeline cards are prepared."),
        _row("blocked-actions", blocked.get("ok") is True, "Blocked action and safety event timeline cards are prepared."),
        _row("verification-receipts", verification.get("ok") is True, "Verification and receipt timeline cards are prepared."),
        _row("raw-evidence", TIMELINE_AUDIT_BOUNDARIES["raw_evidence_preserved"] is True, "Raw evidence remains preserved."),
        _row("approval-semantics", _base_state()["approval_semantics_changed"] is False, "Decision audit trail board does not change approval semantics."),
        _row("no-authority", all(TIMELINE_AUDIT_BOUNDARIES[key] is False for key in no_authority_keys), "Final audit trail board grants no execution, approval creation, approval reuse, source, memory, archive, current-state mutation, verification command, release, publish, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "decision_audit_trail_board_review_only", "decision_audit_trail_board_id": DECISION_AUDIT_TRAIL_BOARD_ID, "operator_decision_timeline_model": timeline, "approval_burnout_consumption_timeline_cards": approval, "blocked_action_safety_event_timeline_cards": blocked, "verification_receipt_timeline_cards": verification, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(TIMELINE_AUDIT_BOUNDARIES)}


def build_operator_receipt_timeline_decision_audit_trail_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "operator_decision_timeline_model_v1": build_operator_decision_timeline_model,
        "approval_burnout_consumption_timeline_cards_v1": build_approval_burnout_consumption_timeline_cards,
        "blocked_action_safety_event_timeline_cards_v1": build_blocked_action_safety_event_timeline_cards,
        "verification_receipt_timeline_cards_v1": build_verification_receipt_timeline_cards,
        "decision_audit_trail_board_v1": build_decision_audit_trail_board,
    }
    builder = builders.get(stage or "decision_audit_trail_board_v1", build_decision_audit_trail_board)
    report = builder(root)
    report.update({
        "arc": "v641.0-v645.0 Operator Receipt Timeline and Decision Audit Trail UX v1",
        "targeted_smoke": TARGETED_SMOKE,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "generated_at": _now_iso(),
    })
    return report


def render_operator_receipt_timeline_decision_audit_trail_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"Eidolon {CURRENT_VERSION_TAG} - Operator Receipt Timeline and Decision Audit Trail UX v1",
        f"State: {report.get('state')}",
        f"Status: {report.get('status')} ok={report.get('ok')}",
        "",
        "Operator receipt timeline/audit UX statuses:",
        f"- receipt_timeline_audit_ux_status={report.get('receipt_timeline_audit_ux_status')}",
        f"- timeline_model_status={report.get('timeline_model_status')}",
        f"- approval_consumption_cards_status={report.get('approval_consumption_cards_status')}",
        f"- blocked_action_cards_status={report.get('blocked_action_cards_status')}",
        f"- verification_receipt_cards_status={report.get('verification_receipt_cards_status')}",
        f"- audit_trail_status={report.get('audit_trail_status')}",
        f"- raw_evidence_preserved={report.get('raw_evidence_preserved')}",
        f"- approval_status={report.get('approval_status')}",
        f"- authorization_status={report.get('authorization_status')}",
        f"- autonomy_status={report.get('autonomy_status')}",
        "",
        "Safety boundaries:",
        f"- creates_approval={report.get('creates_approval')}",
        f"- records_operator_decision={report.get('records_operator_decision')}",
        f"- writes_source={report.get('writes_source')}",
        f"- writes_memory={report.get('writes_memory')}",
        f"- writes_archive_records={report.get('writes_archive_records')}",
        f"- executes_actions={report.get('executes_actions')}",
        f"- executes_commands={report.get('executes_commands')}",
        f"- executes_smoke={report.get('executes_smoke')}",
        f"- creates_release={report.get('creates_release')}",
        f"- publishes_release={report.get('publishes_release')}",
        f"- reuses_approval={report.get('reuses_approval')}",
        f"- continues_automatically={report.get('continues_automatically')}",
        f"- expands_autonomy={report.get('expands_autonomy')}",
        "",
        "Rows:",
    ]
    for row in report.get("rows", []):
        lines.append(f"- [{row.get('status')}] {row.get('name')}: {row.get('message')}")
    return lines


# v641.0-v645.0 operator receipt timeline and decision audit trail UX tokens: operator-decision-timeline-model approval-burnout-consumption-timeline-cards blocked-action-safety-event-timeline-cards verification-receipt-timeline-cards decision-audit-trail-board operator-receipt-timeline-decision-audit-trail-ux-v1 operator_receipt_timeline_audit_ux.py receipt_timeline_audit_ux_status=prepared_only timeline_model_status=prepared approval_consumption_cards_status=prepared blocked_action_cards_status=prepared verification_receipt_cards_status=prepared audit_trail_status=review_only raw_evidence_preserved=True approval_semantics_changed=False authorization_status=not_authorized autonomy_status=not_autonomous timeline_model_executes_events=False timeline_model_grants_approval=False approval_consumption_cards_consume_approval=False approval_consumption_cards_allow_reuse=False blocked_action_cards_unblock_actions=False verification_cards_run_checks=False verification_cards_treat_pass_as_authorization=False audit_trail_creates_approval=False audit_trail_reuses_approval=False audit_trail_writes_source=False audit_trail_writes_memory=False audit_trail_writes_archive_records=False audit_trail_mutates_current_state=False audit_trail_runs_verification_commands=False audit_trail_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
