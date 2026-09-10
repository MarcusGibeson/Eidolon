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

OPERATOR_ACTION_SEMANTICS_UX_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
UNIVERSAL_ACTION_LABEL_STANDARD_ID = "v621_universal_action_label_standard"
BLOCKED_ACTION_EXPLANATION_CARDS_ID = "v622_blocked_action_explanation_cards"
ONE_TIME_APPROVAL_BURNOUT_UX_ID = "v623_one_time_approval_burnout_ux"
SAFE_PREVIEW_BEFORE_ACTION_SUMMARY_ID = "v624_safe_preview_before_action_summary"
OPERATOR_ACTION_SEMANTICS_BOARD_ID = "v625_operator_action_semantics_board"

ACTION_CLASSES: tuple[str, ...] = (
    "read_only",
    "draft_only",
    "approval_required",
    "blocked",
    "historical",
    "advisory",
)

STANDARD_ACTION_LABELS: tuple[dict[str, str], ...] = (
    {"label": "Open Review Packet", "class": "read_only", "meaning": "Open prepared review evidence without executing commands or granting approval."},
    {"label": "Prepare Draft Only", "class": "draft_only", "meaning": "Prepare a reviewable draft without writing it into live source or current state."},
    {"label": "Run Read-Only Audit", "class": "read_only", "meaning": "Describe or invoke only explicitly approved read-only audit paths; summary cards do not execute audits."},
    {"label": "Prepare Sandbox Packet", "class": "draft_only", "meaning": "Prepare sandbox instructions without executing the sandbox."},
    {"label": "Request Operator Approval", "class": "approval_required", "meaning": "Ask for exact scoped approval; this does not grant approval by itself."},
    {"label": "Record Operator Decision", "class": "approval_required", "meaning": "Prepare a decision record path that still requires exact operator-supplied content and scope."},
    {"label": "Apply Approved Patch", "class": "approval_required", "meaning": "Reserved for a separately approved one-time live patch application packet only."},
    {"label": "Mark Approval Consumed", "class": "approval_required", "meaning": "Mark a single-use approval as burned out after the approved attempt."},
    {"label": "View Raw Evidence", "class": "read_only", "meaning": "Expose raw report details without treating evidence as authorization."},
    {"label": "Open Legacy Surface", "class": "historical", "meaning": "Open a historical route without granting current execution or write permission."},
)

BLOCKED_ACTION_CARD_TEMPLATE: dict[str, str] = {
    "what_is_blocked": "Exact write/execution action remains blocked.",
    "why_blocked": "No fresh single-use operator approval with exact scope has been supplied.",
    "missing_evidence_or_approval": "Operator decision, approved target scope, command/file list, expected result, and burnout rule are required.",
    "still_allowed": "Review packets, prepare drafts, inspect evidence, and prepare approval requests.",
    "must_not_infer": "Do not infer approval from route health, smoke success, readiness, prior approval, UI navigation, or operator interest.",
}

APPROVAL_BURNOUT_TEMPLATE: dict[str, Any] = {
    "approval_scope": "exact single-use scope required",
    "approved_action": "not_supplied",
    "approved_files_or_targets": [],
    "approved_commands": [],
    "expiration": "not_supplied",
    "consumed_status": "not_consumed_because_not_granted",
    "reuse_allowed": False,
    "approval_created_by_ui": False,
}

SAFE_PREVIEW_TEMPLATE: dict[str, Any] = {
    "if_approved_eidolon_would": [
        "perform only the explicitly approved action inside the exact approved scope",
        "produce the expected receipt or failure report",
        "stop at the declared stop condition",
    ],
    "eidolon_would_not": [
        "continue into another patch or workflow",
        "publish a release",
        "write memory",
        "write archive records",
        "mutate current state outside scope",
        "treat success as future approval",
    ],
    "expected_receipt": "receipt_required_after_any_approved_attempt",
    "rollback_or_reversal_notes": "required_before_write_or_execution_scope",
    "stop_condition": "stop_after_single_approved_attempt_or_any_blocker",
}

ACTION_SEMANTICS_BOUNDARIES: dict[str, bool] = {
    "action_labels_execute_actions": False,
    "action_labels_grant_approval": False,
    "blocked_cards_unblock_actions": False,
    "blocked_cards_create_approval": False,
    "approval_card_grants_approval": False,
    "approval_card_reuses_approval": False,
    "approval_burnout_reuse_allowed": False,
    "safe_preview_executes_action": False,
    "safe_preview_is_operator_approval": False,
    "safe_preview_runs_commands": False,
    "semantics_board_changes_approval_rules": False,
    "semantics_board_writes_source": False,
    "semantics_board_writes_memory": False,
    "semantics_board_writes_archive_records": False,
    "semantics_board_mutates_current_state": False,
    "semantics_board_creates_release": False,
    "semantics_board_publishes_release": False,
    "semantics_board_reuses_approval": False,
    "semantics_board_continues_automatically": False,
    "semantics_board_expands_autonomy": False,
    "operator_review_required": True,
    "explicit_approval_required_for_writes": True,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _base_state() -> dict[str, Any]:
    return {
        "action_semantics_status": "prepared_only",
        "action_label_standard_status": "prepared",
        "blocked_action_card_status": "prepared",
        "approval_burnout_ux_status": "prepared",
        "safe_preview_status": "prepared",
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
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
    }


def build_universal_action_label_standard(root: str | Path | None = None) -> dict[str, Any]:
    labels = [dict(label) for label in STANDARD_ACTION_LABELS]
    rows = [
        _row("labels-present", len(labels) >= 10, "Universal action labels are declared for review, draft, approval, evidence, and legacy access flows."),
        _row("classes-present", all(item["class"] in ACTION_CLASSES for item in labels), "Every action label maps to a standard action class."),
        _row("labels-do-not-execute", ACTION_SEMANTICS_BOUNDARIES["action_labels_execute_actions"] is False, "Action labels describe intent but execute no actions."),
        _row("labels-do-not-approve", ACTION_SEMANTICS_BOUNDARIES["action_labels_grant_approval"] is False, "Action labels do not grant approval or authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "universal_action_label_standard_review_only", "standard_id": UNIVERSAL_ACTION_LABEL_STANDARD_ID, "action_classes": list(ACTION_CLASSES), "standard_action_labels": labels, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(ACTION_SEMANTICS_BOUNDARIES)}


def build_blocked_action_explanation_cards(root: str | Path | None = None) -> dict[str, Any]:
    examples = [
        {"blocked_action": "Archive write", **BLOCKED_ACTION_CARD_TEMPLATE, "why_blocked": "No exact archive-write approval has been supplied."},
        {"blocked_action": "Memory write", **BLOCKED_ACTION_CARD_TEMPLATE, "why_blocked": "No fresh exact memory-write approval and candidate confirmation have been supplied."},
        {"blocked_action": "Live source patch", **BLOCKED_ACTION_CARD_TEMPLATE, "why_blocked": "No single-use live patch approval packet is active for the exact files and commands."},
    ]
    rows = [
        _row("blocked-card-template-present", all(key in BLOCKED_ACTION_CARD_TEMPLATE for key in ["what_is_blocked", "why_blocked", "missing_evidence_or_approval", "still_allowed", "must_not_infer"]), "Blocked action card template explains what is blocked, why, what is missing, what remains allowed, and what must not be inferred."),
        _row("blocked-examples-present", len(examples) >= 3, "Archive, memory, and live patch blocked examples are prepared."),
        _row("blocked-cards-do-not-unblock", ACTION_SEMANTICS_BOUNDARIES["blocked_cards_unblock_actions"] is False, "Blocked cards do not unblock actions."),
        _row("blocked-cards-do-not-approve", ACTION_SEMANTICS_BOUNDARIES["blocked_cards_create_approval"] is False, "Blocked cards do not create approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "blocked_action_explanation_cards_review_only", "cards_id": BLOCKED_ACTION_EXPLANATION_CARDS_ID, "blocked_action_card_template": dict(BLOCKED_ACTION_CARD_TEMPLATE), "blocked_action_examples": examples, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(ACTION_SEMANTICS_BOUNDARIES)}


def build_one_time_approval_burnout_ux(root: str | Path | None = None) -> dict[str, Any]:
    card = dict(APPROVAL_BURNOUT_TEMPLATE)
    rows = [
        _row("approval-scope-required", card["approval_scope"] == "exact single-use scope required", "Approval card requires exact single-use scope."),
        _row("reuse-blocked", card["reuse_allowed"] is False and ACTION_SEMANTICS_BOUNDARIES["approval_burnout_reuse_allowed"] is False, "Approval reuse remains blocked."),
        _row("card-not-approval", ACTION_SEMANTICS_BOUNDARIES["approval_card_grants_approval"] is False, "Approval UX card does not grant approval by itself."),
        _row("not-created-by-ui", card["approval_created_by_ui"] is False, "Approval card does not create approval from UI presence."),
    ]
    return {"version": CURRENT_VERSION, "state": "one_time_approval_burnout_ux_review_only", "approval_ux_id": ONE_TIME_APPROVAL_BURNOUT_UX_ID, "approval_burnout_template": card, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(ACTION_SEMANTICS_BOUNDARIES)}


def build_safe_preview_before_action_summary(root: str | Path | None = None) -> dict[str, Any]:
    preview = {key: list(value) if isinstance(value, list) else value for key, value in SAFE_PREVIEW_TEMPLATE.items()}
    rows = [
        _row("preview-declares-would", len(preview["if_approved_eidolon_would"]) >= 3, "Safe preview declares what Eidolon would do if explicitly approved."),
        _row("preview-declares-would-not", len(preview["eidolon_would_not"]) >= 6, "Safe preview declares what Eidolon would not do."),
        _row("preview-not-action", ACTION_SEMANTICS_BOUNDARIES["safe_preview_executes_action"] is False, "Safe preview does not execute the action."),
        _row("preview-not-approval", ACTION_SEMANTICS_BOUNDARIES["safe_preview_is_operator_approval"] is False, "Safe preview is not operator approval."),
        _row("preview-no-commands", ACTION_SEMANTICS_BOUNDARIES["safe_preview_runs_commands"] is False, "Safe preview runs no commands."),
    ]
    return {"version": CURRENT_VERSION, "state": "safe_preview_before_action_summary_review_only", "preview_id": SAFE_PREVIEW_BEFORE_ACTION_SUMMARY_ID, "safe_preview_template": preview, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(ACTION_SEMANTICS_BOUNDARIES)}


def build_operator_action_semantics_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    labels = build_universal_action_label_standard(repo)
    blocked = build_blocked_action_explanation_cards(repo)
    approval = build_one_time_approval_burnout_ux(repo)
    preview = build_safe_preview_before_action_summary(repo)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/operator_action_semantics_ux.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v625.0 - Operator Action Semantics and Approval UX Standardization v1",
        TARGETED_SMOKE,
        "universal-action-label-standard",
        "blocked-action-explanation-cards",
        "one-time-approval-burnout-ux",
        "safe-preview-before-action-summary",
        "operator-action-semantics-board",
        "operator_action_semantics_ux.py",
        "action_semantics_status=prepared_only",
        "action_label_standard_status=prepared",
        "blocked_action_card_status=prepared",
        "approval_burnout_ux_status=prepared",
        "safe_preview_status=prepared",
        "approval_semantics_changed=False",
        "action_labels_execute_actions=False",
        "blocked_cards_unblock_actions=False",
        "approval_card_reuses_approval=False",
        "safe_preview_executes_action=False",
        "semantics_board_expands_autonomy=False",
    ]
    rows = [
        _row("label-standard-ready", labels.get("ok") is True, "Universal action label standard is prepared."),
        _row("blocked-cards-ready", blocked.get("ok") is True, "Blocked-action explanation cards are prepared."),
        _row("approval-burnout-ready", approval.get("ok") is True, "One-time approval and burnout UX is prepared."),
        _row("safe-preview-ready", preview.get("ok") is True, "Safe preview before-action summary is prepared."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Stale-version scanner remains clean."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current-symbol audit remains clean."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains clean and review-only."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v621-v625 action semantics surfaces and no-authority tokens."),
        _row("no-authority", all(ACTION_SEMANTICS_BOUNDARIES[key] is False for key in ["action_labels_execute_actions", "action_labels_grant_approval", "blocked_cards_unblock_actions", "blocked_cards_create_approval", "approval_card_grants_approval", "approval_card_reuses_approval", "approval_burnout_reuse_allowed", "safe_preview_executes_action", "safe_preview_is_operator_approval", "safe_preview_runs_commands", "semantics_board_changes_approval_rules", "semantics_board_writes_source", "semantics_board_writes_memory", "semantics_board_writes_archive_records", "semantics_board_mutates_current_state", "semantics_board_creates_release", "semantics_board_publishes_release", "semantics_board_reuses_approval", "semantics_board_continues_automatically", "semantics_board_expands_autonomy"]), "Action semantics UX grants no approval, execution, source, memory, archive, release, publish, current-state mutation, approval reuse, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_action_semantics_board_review_only", "board_id": OPERATOR_ACTION_SEMANTICS_BOARD_ID, **_base_state(), "universal_action_label_standard": labels, "blocked_action_explanation_cards": blocked, "one_time_approval_burnout_ux": approval, "safe_preview_before_action_summary": preview, "stale_version_string_scanner": scanner, "current_symbol_staleness_audit": symbols, "release_staleness_verification_board": release_board, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(ACTION_SEMANTICS_BOUNDARIES), "safe_next_action": "Operator may review the v625 action semantics board. Next work should improve review packet readability and evidence UX without changing approval semantics or expanding autonomy."}


def build_operator_action_semantics_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "operator_action_semantics_board_v1"
    builders = {
        "universal_action_label_standard_v1": build_universal_action_label_standard,
        "blocked_action_explanation_cards_v1": build_blocked_action_explanation_cards,
        "one_time_approval_burnout_ux_v1": build_one_time_approval_burnout_ux,
        "safe_preview_before_action_summary_v1": build_safe_preview_before_action_summary,
        "operator_action_semantics_board_v1": build_operator_action_semantics_board,
    }
    return builders.get(stage, build_operator_action_semantics_board)(root=root)


def render_operator_action_semantics_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"action_semantics_status: {report.get('action_semantics_status')}",
        f"action_label_standard_status: {report.get('action_label_standard_status')}",
        f"blocked_action_card_status: {report.get('blocked_action_card_status')}",
        f"approval_burnout_ux_status: {report.get('approval_burnout_ux_status')}",
        f"safe_preview_status: {report.get('safe_preview_status')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
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


# v621.0-v625.0 operator action semantics UX tokens: universal-action-label-standard blocked-action-explanation-cards one-time-approval-burnout-ux safe-preview-before-action-summary operator-action-semantics-board operator-action-semantics-approval-ux-v1 operator_action_semantics_ux.py action_semantics_status=prepared_only action_label_standard_status=prepared blocked_action_card_status=prepared approval_burnout_ux_status=prepared safe_preview_status=prepared approval_semantics_changed=False source_mutation_status=not_performed archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous action_labels_execute_actions=False action_labels_grant_approval=False blocked_cards_unblock_actions=False blocked_cards_create_approval=False approval_card_grants_approval=False approval_card_reuses_approval=False approval_burnout_reuse_allowed=False safe_preview_executes_action=False safe_preview_is_operator_approval=False safe_preview_runs_commands=False semantics_board_changes_approval_rules=False semantics_board_writes_source=False semantics_board_writes_memory=False semantics_board_writes_archive_records=False semantics_board_mutates_current_state=False semantics_board_creates_release=False semantics_board_publishes_release=False semantics_board_reuses_approval=False semantics_board_continues_automatically=False semantics_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
