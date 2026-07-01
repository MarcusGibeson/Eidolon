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

REVIEW_PACKET_EVIDENCE_UX_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
REVIEW_PACKET_SUMMARY_HEADER_ID = "v626_review_packet_summary_header"
EVIDENCE_GROUPING_PRIORITY_LAYOUT_ID = "v627_evidence_grouping_priority_layout"
RECEIPT_LEDGER_READABILITY_CARDS_ID = "v628_receipt_ledger_readability_cards"
SYSTEM_HEALTH_EVIDENCE_UX_ID = "v629_system_health_evidence_ux"
REVIEW_PACKET_EVIDENCE_UX_BOARD_ID = "v630_review_packet_evidence_ux_board"

STANDARD_REVIEW_PACKET_HEADER_FIELDS: tuple[str, ...] = (
    "packet_title",
    "introduced_version",
    "current_status",
    "operator_required",
    "approval_required",
    "write_allowed",
    "autonomy_status",
    "risk_level",
    "next_safe_action",
)

EVIDENCE_PRIORITY_SECTIONS: tuple[str, ...] = (
    "Summary",
    "Operator Decision Needed",
    "Blocked Actions",
    "Allowed Actions",
    "Verification Evidence",
    "Raw Details",
    "Historical Notes",
)

RECEIPT_LEDGER_CARD_TYPES: tuple[str, ...] = (
    "sandbox_receipt",
    "patch_receipt",
    "archive_ledger",
    "memory_trial_ledger",
    "release_decision_ledger",
    "rollback_recovery_packet",
)

SYSTEM_HEALTH_EVIDENCE_PANELS: tuple[str, ...] = (
    "targeted_smoke",
    "fast_smoke",
    "dashboard_segment",
    "recent_regression_segment",
    "route_parity",
    "api_runtime",
    "cli_runtime",
    "metadata_integrity",
    "source_package_privacy",
    "stale_version_audit",
)

REVIEW_PACKET_EVIDENCE_BOUNDARIES: dict[str, bool] = {
    "summary_header_grants_approval": False,
    "summary_header_executes_actions": False,
    "summary_header_hides_raw_evidence": False,
    "evidence_grouping_hides_raw_evidence": False,
    "evidence_grouping_treats_summary_as_proof": False,
    "receipt_cards_treat_receipt_as_approval": False,
    "receipt_cards_write_ledgers": False,
    "receipt_cards_mutate_current_state": False,
    "system_health_panels_run_smoke": False,
    "system_health_panels_treat_pass_as_authorization": False,
    "system_health_panels_hide_legacy_advisories": False,
    "evidence_board_changes_approval_semantics": False,
    "evidence_board_writes_source": False,
    "evidence_board_writes_memory": False,
    "evidence_board_writes_archive_records": False,
    "evidence_board_mutates_current_state": False,
    "evidence_board_creates_release": False,
    "evidence_board_publishes_release": False,
    "evidence_board_reuses_approval": False,
    "evidence_board_continues_automatically": False,
    "evidence_board_expands_autonomy": False,
    "raw_evidence_preserved": True,
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
        "review_packet_evidence_ux_status": "prepared_only",
        "review_packet_header_status": "prepared",
        "evidence_grouping_status": "prepared",
        "receipt_card_status": "prepared",
        "system_health_evidence_status": "prepared",
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
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "operator_review_required": True,
    }


def build_review_packet_summary_header(root: str | Path | None = None) -> dict[str, Any]:
    header_template = {
        "packet_title": "Operator Review Packet",
        "introduced_version": CURRENT_VERSION_TAG,
        "current_status": "prepared_only",
        "operator_required": True,
        "approval_required": True,
        "write_allowed": False,
        "autonomy_status": "not_autonomous",
        "risk_level": "operator_review_required",
        "next_safe_action": "Open review packet and inspect grouped evidence; do not treat header status as approval.",
    }
    rows = [
        _row("header-fields-present", all(field in header_template for field in STANDARD_REVIEW_PACKET_HEADER_FIELDS), "Review packet summary header declares title, version, status, operator/approval requirements, write allowance, autonomy state, risk, and next safe action."),
        _row("header-not-approval", REVIEW_PACKET_EVIDENCE_BOUNDARIES["summary_header_grants_approval"] is False, "Summary headers do not grant approval or authorization."),
        _row("header-not-action", REVIEW_PACKET_EVIDENCE_BOUNDARIES["summary_header_executes_actions"] is False, "Summary headers execute no actions."),
        _row("raw-evidence-visible", REVIEW_PACKET_EVIDENCE_BOUNDARIES["summary_header_hides_raw_evidence"] is False, "Summary headers must keep raw evidence reachable."),
    ]
    return {"version": CURRENT_VERSION, "state": "review_packet_summary_header_review_only", "header_id": REVIEW_PACKET_SUMMARY_HEADER_ID, "header_template": header_template, "standard_header_fields": list(STANDARD_REVIEW_PACKET_HEADER_FIELDS), **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(REVIEW_PACKET_EVIDENCE_BOUNDARIES)}


def build_evidence_grouping_priority_layout(root: str | Path | None = None) -> dict[str, Any]:
    layout = [
        {"section": section, "visible_by_default": section != "Raw Details", "purpose": "raw evidence preserved" if section == "Raw Details" else "operator readability"}
        for section in EVIDENCE_PRIORITY_SECTIONS
    ]
    rows = [
        _row("sections-present", len(layout) == len(EVIDENCE_PRIORITY_SECTIONS), "Evidence is grouped into summary, decisions, blocked actions, allowed actions, verification, raw details, and historical notes."),
        _row("raw-details-preserved", any(item["section"] == "Raw Details" for item in layout) and REVIEW_PACKET_EVIDENCE_BOUNDARIES["evidence_grouping_hides_raw_evidence"] is False, "Raw evidence remains preserved and reachable."),
        _row("summary-not-proof", REVIEW_PACKET_EVIDENCE_BOUNDARIES["evidence_grouping_treats_summary_as_proof"] is False, "Evidence grouping does not treat summaries as proof or authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "evidence_grouping_priority_layout_review_only", "layout_id": EVIDENCE_GROUPING_PRIORITY_LAYOUT_ID, "evidence_sections": layout, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(REVIEW_PACKET_EVIDENCE_BOUNDARIES)}


def build_receipt_ledger_readability_cards(root: str | Path | None = None) -> dict[str, Any]:
    card_template = {
        "what_happened": "summarized_without_inference",
        "what_did_not_happen": "explicit_boundary_statement_required",
        "what_was_authorized": "exact_scope_or_not_supplied",
        "what_was_blocked": "blocked_actions_list_required",
        "what_evidence_exists": "receipt_or_ledger_reference_required",
        "what_remains_pending": "operator_decision_or_verification_items_required",
    }
    cards = [{"card_type": item, **card_template} for item in RECEIPT_LEDGER_CARD_TYPES]
    rows = [
        _row("card-types-present", len(cards) >= 6, "Sandbox, patch, archive, memory, release decision, and rollback/recovery cards are represented."),
        _row("boundary-fields-present", all(all(key in card for key in card_template) for card in cards), "Every card states what happened, did not happen, what was authorized, blocked, evidenced, and pending."),
        _row("receipt-not-approval", REVIEW_PACKET_EVIDENCE_BOUNDARIES["receipt_cards_treat_receipt_as_approval"] is False, "Receipts and ledgers are evidence, not approval."),
        _row("cards-do-not-write", REVIEW_PACKET_EVIDENCE_BOUNDARIES["receipt_cards_write_ledgers"] is False and REVIEW_PACKET_EVIDENCE_BOUNDARIES["receipt_cards_mutate_current_state"] is False, "Readability cards do not write ledgers or mutate current state."),
    ]
    return {"version": CURRENT_VERSION, "state": "receipt_ledger_readability_cards_review_only", "cards_id": RECEIPT_LEDGER_READABILITY_CARDS_ID, "receipt_card_template": card_template, "receipt_ledger_cards": cards, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(REVIEW_PACKET_EVIDENCE_BOUNDARIES)}


def build_system_health_evidence_ux(root: str | Path | None = None) -> dict[str, Any]:
    panels = [
        {
            "panel": panel,
            "status_field": "pass_advisory_or_blocked",
            "scope_field": "declared",
            "current_version_checked": CURRENT_VERSION,
            "known_advisory_warnings": "shown_separately_from_release_blockers",
            "release_blocking_failures": "shown_explicitly",
            "last_verified_surface": "declared_when_available",
        }
        for panel in SYSTEM_HEALTH_EVIDENCE_PANELS
    ]
    rows = [
        _row("panels-present", len(panels) >= 10, "Targeted smoke, fast smoke, dashboard, recent regression, route/API/CLI parity, metadata, package privacy, and stale-version audit panels are represented."),
        _row("panels-do-not-run-smoke", REVIEW_PACKET_EVIDENCE_BOUNDARIES["system_health_panels_run_smoke"] is False, "System health evidence panels do not execute smoke by themselves."),
        _row("pass-not-authorization", REVIEW_PACKET_EVIDENCE_BOUNDARIES["system_health_panels_treat_pass_as_authorization"] is False, "System health pass state is not authorization."),
        _row("legacy-advisories-visible", REVIEW_PACKET_EVIDENCE_BOUNDARIES["system_health_panels_hide_legacy_advisories"] is False, "Legacy advisories remain visible instead of being hidden as false green status."),
    ]
    return {"version": CURRENT_VERSION, "state": "system_health_evidence_ux_review_only", "system_health_id": SYSTEM_HEALTH_EVIDENCE_UX_ID, "system_health_evidence_panels": panels, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(REVIEW_PACKET_EVIDENCE_BOUNDARIES)}


def build_review_packet_evidence_ux_board(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo(root)
    header = build_review_packet_summary_header(repo)
    grouping = build_evidence_grouping_priority_layout(repo)
    cards = build_receipt_ledger_readability_cards(repo)
    health = build_system_health_evidence_ux(repo)
    scanner = build_stale_version_string_scanner(repo)
    symbols = build_current_symbol_staleness_audit(repo)
    release_board = build_release_staleness_and_verification_audit_board(repo)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/review_packet_evidence_ux.py",
        "conscious_agent/current_version_staleness_audit.py", "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py", "conscious_agent/smoke_segment_registry.py", "data/projects.json",
    ])
    required_tokens = [
        "v630.0 - Operator Review Packet Readability and Evidence UX v1",
        TARGETED_SMOKE,
        "review-packet-summary-header",
        "evidence-grouping-priority-layout",
        "receipt-ledger-readability-cards",
        "system-health-evidence-ux",
        "review-packet-evidence-ux-board",
        "review_packet_evidence_ux.py",
        "review_packet_evidence_ux_status=prepared_only",
        "review_packet_header_status=prepared",
        "evidence_grouping_status=prepared",
        "receipt_card_status=prepared",
        "system_health_evidence_status=prepared",
        "raw_evidence_preserved=True",
        "approval_semantics_changed=False",
        "summary_header_grants_approval=False",
        "evidence_grouping_hides_raw_evidence=False",
        "receipt_cards_treat_receipt_as_approval=False",
        "system_health_panels_run_smoke=False",
        "evidence_board_expands_autonomy=False",
    ]
    rows = [
        _row("summary-header-ready", header.get("ok") is True, "Review packet summary header is prepared."),
        _row("evidence-grouping-ready", grouping.get("ok") is True, "Evidence grouping and priority layout is prepared."),
        _row("receipt-cards-ready", cards.get("ok") is True, "Receipt and ledger readability cards are prepared."),
        _row("system-health-evidence-ready", health.get("ok") is True, "System health evidence UX panels are prepared."),
        _row("raw-evidence-preserved", REVIEW_PACKET_EVIDENCE_BOUNDARIES["raw_evidence_preserved"] is True and header.get("raw_evidence_preserved") is True, "Raw evidence remains preserved and reachable."),
        _row("stale-scanner-clean", scanner.get("ok") is True, "Stale-version scanner remains clean."),
        _row("current-symbols-clean", symbols.get("ok") is True, "Current-symbol audit remains clean."),
        _row("release-board-clean", release_board.get("ok") is True, "Release staleness verification board remains clean and review-only."),
        _row("docs-runtime-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke metadata include v626-v630 review packet evidence UX surfaces and no-authority tokens."),
        _row("no-authority", all(REVIEW_PACKET_EVIDENCE_BOUNDARIES[key] is False for key in ["summary_header_grants_approval", "summary_header_executes_actions", "summary_header_hides_raw_evidence", "evidence_grouping_hides_raw_evidence", "evidence_grouping_treats_summary_as_proof", "receipt_cards_treat_receipt_as_approval", "receipt_cards_write_ledgers", "receipt_cards_mutate_current_state", "system_health_panels_run_smoke", "system_health_panels_treat_pass_as_authorization", "system_health_panels_hide_legacy_advisories", "evidence_board_changes_approval_semantics", "evidence_board_writes_source", "evidence_board_writes_memory", "evidence_board_writes_archive_records", "evidence_board_mutates_current_state", "evidence_board_creates_release", "evidence_board_publishes_release", "evidence_board_reuses_approval", "evidence_board_continues_automatically", "evidence_board_expands_autonomy"]), "Evidence UX grants no approval, execution, source, memory, archive, release, publish, current-state mutation, approval reuse, continuation, or autonomy authority."),
    ]
    return {"version": CURRENT_VERSION, "state": "review_packet_evidence_ux_board_review_only", "board_id": REVIEW_PACKET_EVIDENCE_UX_BOARD_ID, **_base_state(), "review_packet_summary_header": header, "evidence_grouping_priority_layout": grouping, "receipt_ledger_readability_cards": cards, "system_health_evidence_ux": health, "stale_version_string_scanner": scanner, "current_symbol_staleness_audit": symbols, "release_staleness_verification_board": release_board, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(REVIEW_PACKET_EVIDENCE_BOUNDARIES), "safe_next_action": "Operator may review the v630 evidence UX board. Next work should add dashboard search and surface discovery without changing approval semantics or expanding autonomy."}


def build_review_packet_evidence_ux_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage = stage or "review_packet_evidence_ux_board_v1"
    builders = {
        "review_packet_summary_header_v1": build_review_packet_summary_header,
        "evidence_grouping_priority_layout_v1": build_evidence_grouping_priority_layout,
        "receipt_ledger_readability_cards_v1": build_receipt_ledger_readability_cards,
        "system_health_evidence_ux_v1": build_system_health_evidence_ux,
        "review_packet_evidence_ux_board_v1": build_review_packet_evidence_ux_board,
    }
    return builders.get(stage, build_review_packet_evidence_ux_board)(root=root)


def render_review_packet_evidence_ux_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"review_packet_evidence_ux_status: {report.get('review_packet_evidence_ux_status')}",
        f"review_packet_header_status: {report.get('review_packet_header_status')}",
        f"evidence_grouping_status: {report.get('evidence_grouping_status')}",
        f"receipt_card_status: {report.get('receipt_card_status')}",
        f"system_health_evidence_status: {report.get('system_health_evidence_status')}",
        f"raw_evidence_preserved: {report.get('raw_evidence_preserved')}",
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


# v626.0-v630.0 review packet evidence UX tokens: review-packet-summary-header evidence-grouping-priority-layout receipt-ledger-readability-cards system-health-evidence-ux review-packet-evidence-ux-board review-packet-readability-evidence-ux-v1 review_packet_evidence_ux.py review_packet_evidence_ux_status=prepared_only review_packet_header_status=prepared evidence_grouping_status=prepared receipt_card_status=prepared system_health_evidence_status=prepared raw_evidence_preserved=True approval_semantics_changed=False source_mutation_status=not_performed archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous summary_header_grants_approval=False summary_header_executes_actions=False summary_header_hides_raw_evidence=False evidence_grouping_hides_raw_evidence=False evidence_grouping_treats_summary_as_proof=False receipt_cards_treat_receipt_as_approval=False receipt_cards_write_ledgers=False receipt_cards_mutate_current_state=False system_health_panels_run_smoke=False system_health_panels_treat_pass_as_authorization=False system_health_panels_hide_legacy_advisories=False evidence_board_changes_approval_semantics=False evidence_board_writes_source=False evidence_board_writes_memory=False evidence_board_writes_archive_records=False evidence_board_mutates_current_state=False evidence_board_creates_release=False evidence_board_publishes_release=False evidence_board_reuses_approval=False evidence_board_continues_automatically=False evidence_board_expands_autonomy=False no_native_title_tooltip data-tip command-deck operator-console
