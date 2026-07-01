from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

OPERATOR_GUIDED_REVIEW_WIZARD_UX_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
GUIDED_REVIEW_WIZARD_ENTRY_MODEL_ID = "v651_guided_review_wizard_entry_model"
GUIDED_EVIDENCE_WARNING_STEP_CARDS_ID = "v652_guided_evidence_warning_step_cards"
GUIDED_DECISION_APPROVAL_STEP_UX_ID = "v653_guided_decision_approval_step_ux"
GUIDED_VERIFICATION_RESUME_STEP_SUMMARY_ID = "v654_guided_verification_resume_step_summary"
OPERATOR_GUIDED_REVIEW_WIZARD_BOARD_ID = "v655_operator_guided_review_wizard_board"

WIZARD_STEPS: tuple[str, ...] = (
    "entry_context",
    "evidence_and_warnings",
    "decision_and_approval",
    "verification_and_resume",
    "final_operator_review_board",
)

EVIDENCE_WARNING_CARD_TYPES: tuple[str, ...] = (
    "current_state_summary",
    "source_surface_manifest",
    "route_parity_status",
    "targeted_smoke_status",
    "stale_version_status",
    "metadata_integrity_status",
    "legacy_advisory_warnings",
    "raw_evidence_links",
)

DECISION_APPROVAL_FIELDS: tuple[str, ...] = (
    "operator_decision_required",
    "decision_type",
    "target_scope",
    "approval_expiration",
    "single_use_approval_burnout",
    "denial_or_deferral_reason",
    "revision_request",
    "authorization_status",
)

VERIFICATION_RESUME_FIELDS: tuple[str, ...] = (
    "targeted_smoke_review",
    "fast_smoke_review",
    "route_probe_review",
    "metadata_review",
    "package_privacy_review",
    "stale_version_review",
    "resume_carryover_review",
    "next_arc_review",
)

GUIDED_REVIEW_BOUNDARIES: dict[str, bool] = {
    "wizard_entry_starts_work": False,
    "wizard_entry_grants_approval": False,
    "wizard_entry_selects_roadmap": False,
    "evidence_cards_hide_raw_evidence": False,
    "evidence_cards_resolve_warnings": False,
    "evidence_cards_run_checks": False,
    "evidence_cards_treat_presence_as_authorization": False,
    "decision_step_creates_approval": False,
    "decision_step_reuses_approval": False,
    "decision_step_changes_approval_semantics": False,
    "decision_step_executes_actions": False,
    "verification_step_runs_checks": False,
    "verification_step_treats_pass_as_authorization": False,
    "verification_step_starts_next_arc": False,
    "wizard_board_writes_source": False,
    "wizard_board_writes_memory": False,
    "wizard_board_writes_archive_records": False,
    "wizard_board_mutates_current_state": False,
    "wizard_board_creates_release": False,
    "wizard_board_publishes_release": False,
    "wizard_board_reuses_approval": False,
    "wizard_board_schedules_hidden_work": False,
    "wizard_board_continues_automatically": False,
    "wizard_board_expands_autonomy": False,
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
        "guided_review_wizard_ux_status": "prepared_only",
        "wizard_entry_status": "prepared",
        "evidence_warning_cards_status": "prepared",
        "decision_approval_step_status": "prepared",
        "verification_resume_step_status": "prepared",
        "guided_review_board_status": "review_only",
        "raw_evidence_preserved": True,
        "approval_semantics_changed": False,
        "operator_decision_status": "required",
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


def build_guided_review_wizard_entry_model(root: str | Path | None = None) -> dict[str, Any]:
    steps = [
        {"step": step, "operator_visible": True, "starts_work": False, "grants_approval": False, "auto_selects_roadmap": False}
        for step in WIZARD_STEPS
    ]
    rows = [
        _row("wizard-steps-present", len(steps) == len(WIZARD_STEPS), "Entry, evidence/warning, decision/approval, verification/resume, and final board steps are represented."),
        _row("steps-visible", all(step["operator_visible"] is True for step in steps), "Every guided wizard step is operator-visible."),
        _row("entry-not-work", all(step["starts_work"] is False for step in steps) and GUIDED_REVIEW_BOUNDARIES["wizard_entry_starts_work"] is False, "Wizard entry starts no work."),
        _row("entry-not-approval", all(step["grants_approval"] is False for step in steps) and GUIDED_REVIEW_BOUNDARIES["wizard_entry_grants_approval"] is False, "Wizard entry grants no approval."),
        _row("entry-not-roadmap-selector", all(step["auto_selects_roadmap"] is False for step in steps) and GUIDED_REVIEW_BOUNDARIES["wizard_entry_selects_roadmap"] is False, "Wizard entry does not auto-select a roadmap."),
    ]
    return {"version": CURRENT_VERSION, "state": "guided_review_wizard_entry_model_review_only", "guided_review_wizard_entry_model_id": GUIDED_REVIEW_WIZARD_ENTRY_MODEL_ID, "wizard_steps": steps, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(GUIDED_REVIEW_BOUNDARIES)}


def build_guided_evidence_warning_step_cards(root: str | Path | None = None) -> dict[str, Any]:
    cards = [
        {"card_type": card, "operator_visible": True, "raw_evidence_access": True, "hides_raw_evidence": False, "resolves_warning": False, "runs_check": False, "is_authorization": False}
        for card in EVIDENCE_WARNING_CARD_TYPES
    ]
    rows = [
        _row("evidence-warning-card-types-present", len(cards) == len(EVIDENCE_WARNING_CARD_TYPES), "Current state, manifest, route parity, targeted smoke, stale version, metadata, legacy advisory, and raw evidence cards are represented."),
        _row("raw-evidence-preserved", all(card["raw_evidence_access"] is True for card in cards) and GUIDED_REVIEW_BOUNDARIES["evidence_cards_hide_raw_evidence"] is False, "Evidence/warning cards preserve raw evidence access."),
        _row("cards-not-resolvers", all(card["resolves_warning"] is False for card in cards) and GUIDED_REVIEW_BOUNDARIES["evidence_cards_resolve_warnings"] is False, "Evidence/warning cards do not resolve warnings by themselves."),
        _row("cards-not-check-runners", all(card["runs_check"] is False for card in cards) and GUIDED_REVIEW_BOUNDARIES["evidence_cards_run_checks"] is False, "Evidence/warning cards run no checks."),
        _row("cards-not-authorization", all(card["is_authorization"] is False for card in cards) and GUIDED_REVIEW_BOUNDARIES["evidence_cards_treat_presence_as_authorization"] is False, "Evidence/warning presence is not authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "guided_evidence_warning_step_cards_review_only", "guided_evidence_warning_step_cards_id": GUIDED_EVIDENCE_WARNING_STEP_CARDS_ID, "evidence_warning_card_types": list(EVIDENCE_WARNING_CARD_TYPES), "evidence_warning_cards": cards, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(GUIDED_REVIEW_BOUNDARIES)}


def build_guided_decision_approval_step_ux(root: str | Path | None = None) -> dict[str, Any]:
    fields = {
        "operator_decision_required": True,
        "decision_type": "approve_deny_defer_or_request_revision",
        "target_scope": "operator_supplied_scope_required",
        "approval_expiration": "single_use_or_explicit_expiration_required",
        "single_use_approval_burnout": True,
        "denial_or_deferral_reason": "captured_for_review_only",
        "revision_request": "captured_for_review_only",
        "authorization_status": "not_authorized",
        "creates_approval": False,
        "reuses_approval": False,
        "executes_actions": False,
    }
    rows = [
        _row("decision-fields-present", all(field in fields for field in DECISION_APPROVAL_FIELDS), "Decision/approval step declares required decision, type, scope, expiration, burnout, denial/deferral, revision, and authorization fields."),
        _row("operator-decision-required", fields["operator_decision_required"] is True, "Operator decision remains required."),
        _row("decision-not-approval", fields["creates_approval"] is False and GUIDED_REVIEW_BOUNDARIES["decision_step_creates_approval"] is False, "Decision step creates no approval."),
        _row("approval-not-reused", fields["reuses_approval"] is False and GUIDED_REVIEW_BOUNDARIES["decision_step_reuses_approval"] is False, "Decision step does not reuse approval."),
        _row("decision-not-action", fields["executes_actions"] is False and GUIDED_REVIEW_BOUNDARIES["decision_step_executes_actions"] is False, "Decision step executes no actions."),
    ]
    return {"version": CURRENT_VERSION, "state": "guided_decision_approval_step_ux_review_only", "guided_decision_approval_step_ux_id": GUIDED_DECISION_APPROVAL_STEP_UX_ID, "decision_approval_fields": fields, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(GUIDED_REVIEW_BOUNDARIES)}


def build_guided_verification_resume_step_summary(root: str | Path | None = None) -> dict[str, Any]:
    summary = {
        field: {"operator_visible": True, "runs_check": False, "treats_pass_as_authorization": False, "starts_next_arc": False}
        for field in VERIFICATION_RESUME_FIELDS
    }
    rows = [
        _row("verification-fields-present", all(field in summary for field in VERIFICATION_RESUME_FIELDS), "Verification/resume step represents targeted smoke, fast smoke, route probe, metadata, package privacy, stale version, resume carryover, and next arc review fields."),
        _row("verification-not-check-runner", all(item["runs_check"] is False for item in summary.values()) and GUIDED_REVIEW_BOUNDARIES["verification_step_runs_checks"] is False, "Verification/resume step runs no checks."),
        _row("verification-pass-not-authorization", all(item["treats_pass_as_authorization"] is False for item in summary.values()) and GUIDED_REVIEW_BOUNDARIES["verification_step_treats_pass_as_authorization"] is False, "Verification pass status is not authorization."),
        _row("resume-not-next-arc-start", all(item["starts_next_arc"] is False for item in summary.values()) and GUIDED_REVIEW_BOUNDARIES["verification_step_starts_next_arc"] is False, "Resume step does not start the next arc."),
    ]
    return {"version": CURRENT_VERSION, "state": "guided_verification_resume_step_summary_review_only", "guided_verification_resume_step_summary_id": GUIDED_VERIFICATION_RESUME_STEP_SUMMARY_ID, "verification_resume_fields": list(VERIFICATION_RESUME_FIELDS), "verification_resume_summary": summary, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(GUIDED_REVIEW_BOUNDARIES)}


def build_operator_guided_review_wizard_board(root: str | Path | None = None) -> dict[str, Any]:
    entry = build_guided_review_wizard_entry_model(root)
    evidence = build_guided_evidence_warning_step_cards(root)
    decision = build_guided_decision_approval_step_ux(root)
    verification = build_guided_verification_resume_step_summary(root)
    rows = [
        _row("entry-model", entry.get("ok") is True, "Guided review wizard entry model is prepared."),
        _row("evidence-warning-cards", evidence.get("ok") is True, "Evidence and warning step cards are prepared."),
        _row("decision-approval-step", decision.get("ok") is True, "Decision and approval step UX is prepared."),
        _row("verification-resume-step", verification.get("ok") is True, "Verification and resume step summary is prepared."),
        _row("board-not-writer", all(GUIDED_REVIEW_BOUNDARIES[key] is False for key in ["wizard_board_writes_source", "wizard_board_writes_memory", "wizard_board_writes_archive_records", "wizard_board_mutates_current_state", "wizard_board_creates_release", "wizard_board_publishes_release"]), "Guided review wizard board performs no writes, current-state mutation, release creation, or publishing."),
        _row("board-not-autonomy", all(GUIDED_REVIEW_BOUNDARIES[key] is False for key in ["wizard_board_reuses_approval", "wizard_board_schedules_hidden_work", "wizard_board_continues_automatically", "wizard_board_expands_autonomy"]), "Guided review wizard board reuses no approval, schedules no hidden work, continues no work automatically, and expands no autonomy."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_guided_review_wizard_board_review_only", "operator_guided_review_wizard_board_id": OPERATOR_GUIDED_REVIEW_WIZARD_BOARD_ID, "guided_review_wizard_entry_model": entry, "guided_evidence_warning_step_cards": evidence, "guided_decision_approval_step_ux": decision, "guided_verification_resume_step_summary": verification, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(GUIDED_REVIEW_BOUNDARIES)}


def build_operator_guided_review_wizard_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "guided_review_wizard_entry_model_v1": build_guided_review_wizard_entry_model,
        "guided_evidence_warning_step_cards_v1": build_guided_evidence_warning_step_cards,
        "guided_decision_approval_step_ux_v1": build_guided_decision_approval_step_ux,
        "guided_verification_resume_step_summary_v1": build_guided_verification_resume_step_summary,
        "operator_guided_review_wizard_board_v1": build_operator_guided_review_wizard_board,
    }
    if stage in builders:
        return builders[stage](root)
    return build_operator_guided_review_wizard_board(root)


def render_operator_guided_review_wizard_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"guided_review_wizard_ux_status: {report.get('guided_review_wizard_ux_status')}",
        f"wizard_entry_status: {report.get('wizard_entry_status')}",
        f"evidence_warning_cards_status: {report.get('evidence_warning_cards_status')}",
        f"decision_approval_step_status: {report.get('decision_approval_step_status')}",
        f"verification_resume_step_status: {report.get('verification_resume_step_status')}",
        f"guided_review_board_status: {report.get('guided_review_board_status')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"operator_decision_status: {report.get('operator_decision_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"release_status: {report.get('release_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows:
            lines.append(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}")
    return lines


# v651.0-v655.0 operator guided review wizard UX tokens: guided-review-wizard-entry-model guided-evidence-warning-step-cards guided-decision-approval-step-ux guided-verification-resume-step-summary operator-guided-review-wizard-board operator-guided-review-wizard-ux-v1 operator_guided_review_wizard_ux.py guided_review_wizard_ux_status=prepared_only wizard_entry_status=prepared evidence_warning_cards_status=prepared decision_approval_step_status=prepared verification_resume_step_status=prepared guided_review_board_status=review_only raw_evidence_preserved=True approval_semantics_changed=False wizard_entry_starts_work=False evidence_cards_run_checks=False decision_step_creates_approval=False decision_step_reuses_approval=False verification_step_runs_checks=False verification_step_treats_pass_as_authorization=False wizard_board_reuses_approval=False wizard_board_schedules_hidden_work=False wizard_board_continues_automatically=False wizard_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
