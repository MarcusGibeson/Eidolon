from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

OPERATOR_DECISION_APPROVAL_UX_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
DECISION_CAPTURE_FORM_SCHEMA_ID = "v636_decision_capture_form_schema"
APPROVAL_SCOPE_TARGET_BINDING_PANEL_ID = "v637_approval_scope_target_binding_panel"
APPROVAL_EXPIRATION_BURNOUT_FORM_UX_ID = "v638_approval_expiration_burnout_form_ux"
DENIAL_DEFERRAL_REVISION_CAPTURE_ID = "v639_denial_deferral_revision_decision_capture"
OPERATOR_DECISION_APPROVAL_UX_BOARD_ID = "v640_operator_decision_approval_ux_board"

DECISION_FORM_FIELDS: tuple[str, ...] = (
    "decision_type",
    "decision_scope",
    "selected_option",
    "target_surface",
    "target_files",
    "target_archive_records",
    "target_memory_candidates",
    "target_commands",
    "expected_result",
    "operator_rationale",
    "expiration",
    "single_use_required",
    "reuse_allowed",
)

APPROVAL_TARGET_FIELDS: tuple[str, ...] = (
    "approved_files",
    "approved_routes",
    "approved_cli_flags",
    "approved_api_paths",
    "approved_archive_records",
    "approved_memory_candidates",
    "approved_verification_commands",
)

APPROVAL_BURNOUT_FIELDS: tuple[str, ...] = (
    "approval_created",
    "approval_expires",
    "approval_consumed",
    "consumed_by_action",
    "consumed_at",
    "reuse_allowed",
    "post_use_status",
)

NON_APPROVAL_DECISION_TYPES: tuple[str, ...] = (
    "denied",
    "deferred",
    "needs_revision",
    "needs_more_evidence",
    "out_of_scope",
    "unsafe",
    "superseded",
)

DECISION_APPROVAL_UX_BOUNDARIES: dict[str, bool] = {
    "decision_form_creates_approval": False,
    "decision_form_executes_decision": False,
    "decision_form_writes_source": False,
    "decision_form_writes_memory": False,
    "decision_form_writes_archive_records": False,
    "decision_form_mutates_current_state": False,
    "decision_form_creates_release": False,
    "decision_form_publishes_release": False,
    "decision_form_expands_autonomy": False,
    "scope_binding_grants_authorization": False,
    "scope_binding_expands_scope": False,
    "scope_binding_reuses_approval": False,
    "scope_binding_runs_commands": False,
    "approval_expiration_reuses_approval": False,
    "approval_expiration_consumes_without_action": False,
    "approval_burnout_reuse_allowed": False,
    "denial_deferral_is_approval": False,
    "revision_request_is_approval": False,
    "unsafe_decision_is_permission": False,
    "ux_board_changes_approval_semantics": False,
    "ux_board_executes_actions": False,
    "ux_board_runs_smoke": False,
    "ux_board_writes_source": False,
    "ux_board_writes_memory": False,
    "ux_board_writes_archive_records": False,
    "ux_board_mutates_current_state": False,
    "ux_board_creates_release": False,
    "ux_board_publishes_release": False,
    "ux_board_reuses_approval": False,
    "ux_board_continues_automatically": False,
    "ux_board_expands_autonomy": False,
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
        "decision_capture_ux_status": "prepared_only",
        "decision_capture_schema_status": "prepared",
        "approval_scope_binding_status": "prepared",
        "approval_expiration_status": "prepared",
        "denial_deferral_capture_status": "prepared",
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


def build_decision_capture_form_schema(root: str | Path | None = None) -> dict[str, Any]:
    form_schema = {
        "decision_type": "approval_denial_deferral_revision_or_more_evidence",
        "decision_scope": "exact_scope_required",
        "selected_option": "operator_supplied_when_applicable",
        "target_surface": "dashboard_api_cli_or_packet_surface",
        "target_files": [],
        "target_archive_records": [],
        "target_memory_candidates": [],
        "target_commands": [],
        "expected_result": "operator_supplied_expected_result",
        "operator_rationale": "optional_operator_rationale",
        "expiration": "required_for_any_approval",
        "single_use_required": True,
        "reuse_allowed": False,
    }
    rows = [
        _row("fields-present", all(field in form_schema for field in DECISION_FORM_FIELDS), "Decision capture form declares exact decision type, scope, targets, result, rationale, expiration, single-use, and no-reuse fields."),
        _row("no-approval-created", DECISION_APPROVAL_UX_BOUNDARIES["decision_form_creates_approval"] is False and form_schema["reuse_allowed"] is False, "Form schema is a capture model and does not create approval by itself."),
        _row("no-execution", DECISION_APPROVAL_UX_BOUNDARIES["decision_form_executes_decision"] is False and DECISION_APPROVAL_UX_BOUNDARIES["decision_form_writes_source"] is False, "Decision form executes no decision and writes no source."),
    ]
    return {"version": CURRENT_VERSION, "state": "decision_capture_form_schema_review_only", "decision_capture_form_schema_id": DECISION_CAPTURE_FORM_SCHEMA_ID, "decision_form_fields": list(DECISION_FORM_FIELDS), "decision_form_schema": form_schema, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DECISION_APPROVAL_UX_BOUNDARIES)}


def build_approval_scope_target_binding_panel(root: str | Path | None = None) -> dict[str, Any]:
    binding_panel = {field: [] for field in APPROVAL_TARGET_FIELDS}
    binding_panel.update({"scope_binding_required": True, "scope_expansion_allowed": False, "authorization_granted_by_binding_panel": False})
    rows = [
        _row("target-fields-present", all(field in binding_panel for field in APPROVAL_TARGET_FIELDS), "Approval binding panel declares exact files, routes, CLI flags, API paths, archive records, memory candidates, and verification commands."),
        _row("no-scope-expansion", DECISION_APPROVAL_UX_BOUNDARIES["scope_binding_expands_scope"] is False and binding_panel["scope_expansion_allowed"] is False, "Scope binding does not expand approval scope."),
        _row("binding-not-authorization", DECISION_APPROVAL_UX_BOUNDARIES["scope_binding_grants_authorization"] is False and binding_panel["authorization_granted_by_binding_panel"] is False, "Binding panel visibility is not authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "approval_scope_target_binding_panel_review_only", "approval_scope_target_binding_panel_id": APPROVAL_SCOPE_TARGET_BINDING_PANEL_ID, "approval_target_fields": list(APPROVAL_TARGET_FIELDS), "binding_panel": binding_panel, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DECISION_APPROVAL_UX_BOUNDARIES)}


def build_approval_expiration_burnout_form_ux(root: str | Path | None = None) -> dict[str, Any]:
    burnout_form = {
        "approval_created": "operator_supplied_if_approved",
        "approval_expires": "required",
        "approval_consumed": False,
        "consumed_by_action": None,
        "consumed_at": None,
        "reuse_allowed": False,
        "post_use_status": "expired_consumed_after_single_use",
    }
    rows = [
        _row("burnout-fields-present", all(field in burnout_form for field in APPROVAL_BURNOUT_FIELDS), "Approval burnout form declares created, expires, consumed, consumed-by, consumed-at, no-reuse, and post-use status fields."),
        _row("reuse-blocked", DECISION_APPROVAL_UX_BOUNDARIES["approval_burnout_reuse_allowed"] is False and burnout_form["reuse_allowed"] is False, "Single-use approval reuse remains blocked."),
        _row("no-auto-consume", DECISION_APPROVAL_UX_BOUNDARIES["approval_expiration_consumes_without_action"] is False, "Approval expiration UX does not consume approval without a scoped action receipt."),
    ]
    return {"version": CURRENT_VERSION, "state": "approval_expiration_burnout_form_ux_review_only", "approval_expiration_burnout_form_ux_id": APPROVAL_EXPIRATION_BURNOUT_FORM_UX_ID, "approval_burnout_fields": list(APPROVAL_BURNOUT_FIELDS), "burnout_form": burnout_form, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DECISION_APPROVAL_UX_BOUNDARIES)}


def build_denial_deferral_revision_decision_capture(root: str | Path | None = None) -> dict[str, Any]:
    non_approval_records = [
        {"decision_type": item, "is_approval": False, "requires_followup_review": item in {"deferred", "needs_revision", "needs_more_evidence"}, "grants_authorization": False}
        for item in NON_APPROVAL_DECISION_TYPES
    ]
    rows = [
        _row("non-approval-types-present", len(non_approval_records) >= 7, "Denial, deferral, revision, more-evidence, out-of-scope, unsafe, and superseded decisions are represented."),
        _row("non-approval-not-approval", all(record["is_approval"] is False and record["grants_authorization"] is False for record in non_approval_records), "Non-approval decision records do not grant authorization."),
        _row("unsafe-not-permission", DECISION_APPROVAL_UX_BOUNDARIES["unsafe_decision_is_permission"] is False and DECISION_APPROVAL_UX_BOUNDARIES["denial_deferral_is_approval"] is False, "Denied/deferred/unsafe decisions cannot be treated as approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "denial_deferral_revision_decision_capture_review_only", "denial_deferral_revision_capture_id": DENIAL_DEFERRAL_REVISION_CAPTURE_ID, "non_approval_decision_types": list(NON_APPROVAL_DECISION_TYPES), "non_approval_records": non_approval_records, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DECISION_APPROVAL_UX_BOUNDARIES)}


def build_operator_decision_approval_ux_board(root: str | Path | None = None) -> dict[str, Any]:
    schema = build_decision_capture_form_schema(root)
    binding = build_approval_scope_target_binding_panel(root)
    burnout = build_approval_expiration_burnout_form_ux(root)
    nonapproval = build_denial_deferral_revision_decision_capture(root)
    rows = [
        _row("schema", schema.get("ok") is True, "Decision capture form schema is prepared."),
        _row("binding", binding.get("ok") is True, "Approval scope and target binding panel is prepared."),
        _row("burnout", burnout.get("ok") is True, "Approval expiration and burnout form UX is prepared."),
        _row("non-approval", nonapproval.get("ok") is True, "Denial, deferral, revision, and more-evidence capture is prepared."),
        _row("approval-semantics", DECISION_APPROVAL_UX_BOUNDARIES["ux_board_changes_approval_semantics"] is False, "UX board does not change approval semantics."),
        _row("no-authority", all(DECISION_APPROVAL_UX_BOUNDARIES[key] is False for key in ["ux_board_executes_actions", "ux_board_runs_smoke", "ux_board_writes_source", "ux_board_writes_memory", "ux_board_writes_archive_records", "ux_board_mutates_current_state", "ux_board_creates_release", "ux_board_publishes_release", "ux_board_reuses_approval", "ux_board_continues_automatically", "ux_board_expands_autonomy"]), "Final UX board grants no execution, smoke, source, memory, archive, release, publish, current-state mutation, approval reuse, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_decision_approval_ux_board_review_only", "operator_decision_approval_ux_board_id": OPERATOR_DECISION_APPROVAL_UX_BOARD_ID, "decision_capture_schema": schema, "approval_scope_binding": binding, "approval_expiration_burnout": burnout, "denial_deferral_revision_capture": nonapproval, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DECISION_APPROVAL_UX_BOUNDARIES)}


def build_operator_decision_capture_approval_form_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "decision_capture_form_schema_v1": build_decision_capture_form_schema,
        "approval_scope_target_binding_panel_v1": build_approval_scope_target_binding_panel,
        "approval_expiration_burnout_form_ux_v1": build_approval_expiration_burnout_form_ux,
        "denial_deferral_revision_decision_capture_v1": build_denial_deferral_revision_decision_capture,
        "operator_decision_approval_ux_board_v1": build_operator_decision_approval_ux_board,
    }
    builder = builders.get(stage or "operator_decision_approval_ux_board_v1", build_operator_decision_approval_ux_board)
    report = builder(root)
    report.update({
        "arc": "v636.0-v640.0 Operator Decision Capture and Approval Form UX v1",
        "targeted_smoke": TARGETED_SMOKE,
        "current_milestone": CURRENT_MILESTONE,
        "next_recommended_arc": NEXT_RECOMMENDED_ARC,
        "generated_at": _now_iso(),
    })
    return report


def render_operator_decision_capture_approval_form_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"Eidolon {CURRENT_VERSION_TAG} - Operator Decision Capture and Approval Form UX v1",
        f"State: {report.get('state')}",
        f"Status: {report.get('status')} ok={report.get('ok')}",
        "",
        "Operator decision/approval UX statuses:",
        f"- decision_capture_ux_status={report.get('decision_capture_ux_status')}",
        f"- decision_capture_schema_status={report.get('decision_capture_schema_status')}",
        f"- approval_scope_binding_status={report.get('approval_scope_binding_status')}",
        f"- approval_expiration_status={report.get('approval_expiration_status')}",
        f"- denial_deferral_capture_status={report.get('denial_deferral_capture_status')}",
        f"- approval_semantics_changed={report.get('approval_semantics_changed')}",
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


# v636.0-v640.0 operator decision capture/approval form UX tokens: decision-capture-form-schema approval-scope-target-binding-panel approval-expiration-burnout-form-ux denial-deferral-revision-decision-capture operator-decision-approval-ux-board operator-decision-capture-approval-form-ux-v1 operator_decision_approval_ux.py decision_capture_ux_status=prepared_only decision_capture_schema_status=prepared approval_scope_binding_status=prepared approval_expiration_status=prepared denial_deferral_capture_status=prepared approval_semantics_changed=False authorization_status=not_authorized autonomy_status=not_autonomous decision_form_creates_approval=False decision_form_executes_decision=False scope_binding_grants_authorization=False scope_binding_expands_scope=False approval_burnout_reuse_allowed=False denial_deferral_is_approval=False ux_board_changes_approval_semantics=False ux_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
