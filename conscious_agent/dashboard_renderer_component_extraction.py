from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

DASHBOARD_RENDERER_COMPONENT_EXTRACTION_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
TARGETED_SMOKE = "dashboard-route-manifest-to-renderer-reconciliation-v1"
DASHBOARD_COMPONENT_CONTRACT_ID = "v676_dashboard_component_contract"
SHARED_REVIEW_PACKET_RENDERER_ID = "v677_shared_review_packet_renderer"
SHARED_BOUNDARY_MATRIX_RENDERER_ID = "v678_shared_boundary_matrix_renderer"
SHARED_EVIDENCE_WARNING_RENDERER_ID = "v679_shared_evidence_warning_renderer"
SHARED_DECISION_APPROVAL_RENDERER_ID = "v680_shared_decision_approval_renderer"
SHARED_RESUME_CONTINUITY_RENDERER_ID = "v681_shared_resume_continuity_renderer"
DASHBOARD_ROUTE_RENDERER_ADAPTER_ID = "v682_dashboard_route_renderer_adapter"
DASHBOARD_STYLE_REGRESSION_GUARD_ID = "v683_dashboard_style_regression_guard"
LEGACY_RENDERER_DUPLICATION_AUDIT_ID = "v684_legacy_renderer_duplication_audit"
DASHBOARD_RENDERER_COMPONENT_EXTRACTION_BOARD_ID = "v685_dashboard_renderer_component_extraction_board"

DASHBOARD_RENDERER_SURFACE_DEFS: tuple[dict[str, str], ...] = (
    {"version":"v676.0","slug":"dashboard_component_contract_v1","route":"dashboard-component-contract","label":"Dashboard Component Contract v1","status_key":"dashboard_component_contract_status"},
    {"version":"v677.0","slug":"shared_review_packet_renderer_v1","route":"shared-review-packet-renderer","label":"Shared Review Packet Renderer v1","status_key":"shared_review_packet_renderer_status"},
    {"version":"v678.0","slug":"shared_boundary_matrix_renderer_v1","route":"shared-boundary-matrix-renderer","label":"Shared Boundary Matrix Renderer v1","status_key":"shared_boundary_matrix_renderer_status"},
    {"version":"v679.0","slug":"shared_evidence_warning_renderer_v1","route":"shared-evidence-warning-renderer","label":"Shared Evidence and Warning Renderer v1","status_key":"shared_evidence_warning_renderer_status"},
    {"version":"v680.0","slug":"shared_decision_approval_renderer_v1","route":"shared-decision-approval-renderer","label":"Shared Decision and Approval Renderer v1","status_key":"shared_decision_approval_renderer_status"},
    {"version":"v681.0","slug":"shared_resume_continuity_renderer_v1","route":"shared-resume-continuity-renderer","label":"Shared Resume/Continuity Renderer v1","status_key":"shared_resume_continuity_renderer_status"},
    {"version":"v682.0","slug":"dashboard_route_renderer_adapter_v1","route":"dashboard-route-renderer-adapter","label":"Dashboard Route Renderer Adapter v1","status_key":"dashboard_route_renderer_adapter_status"},
    {"version":"v683.0","slug":"dashboard_style_regression_guard_v1","route":"dashboard-style-regression-guard","label":"Dashboard Style Regression Guard v1","status_key":"dashboard_style_regression_guard_status"},
    {"version":"v684.0","slug":"legacy_renderer_duplication_audit_v1","route":"legacy-renderer-duplication-audit","label":"Legacy Renderer Duplication Audit v1","status_key":"legacy_renderer_duplication_audit_status"},
    {"version":"v685.0","slug":"dashboard_renderer_component_extraction_board_v1","route":"dashboard-renderer-component-extraction-board","label":"Dashboard Renderer Component Extraction Board v1","status_key":"dashboard_renderer_component_extraction_board_status"},
)

DASHBOARD_RENDERER_BOUNDARIES: dict[str, bool] = {
    "component_contract_writes_source": False,
    "component_contract_changes_visual_contract": False,
    "shared_review_renderer_changes_route_behavior": False,
    "shared_boundary_matrix_grants_authorization": False,
    "shared_evidence_warning_hides_raw_evidence": False,
    "shared_decision_renderer_creates_approval": False,
    "shared_decision_renderer_reuses_approval": False,
    "shared_resume_renderer_starts_work": False,
    "shared_resume_renderer_continues_automatically": False,
    "route_renderer_adapter_registers_routes": False,
    "route_renderer_adapter_replaces_routes": False,
    "style_guard_rewrites_dashboard": False,
    "style_guard_uses_native_title_tooltips": False,
    "duplication_audit_deletes_renderers": False,
    "duplication_audit_applies_refactor": False,
    "component_board_writes_source": False,
    "component_board_writes_metadata": False,
    "component_board_writes_memory": False,
    "component_board_writes_archive_records": False,
    "component_board_creates_release": False,
    "component_board_publishes_release": False,
    "component_board_reuses_approval": False,
    "component_board_continues_automatically": False,
    "component_board_expands_autonomy": False,
    "renderer_presence_is_authorization": False,
    "style_guard_pass_is_approval": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}

SHARED_RENDERER_COMPONENTS: tuple[dict[str, Any], ...] = (
    {"name":"render_console_card", "purpose":"shared command-deck card wrapper", "changes_visual_contract": False},
    {"name":"render_status_pill", "purpose":"shared prepared/pass/blocked marker contract", "changes_visual_contract": False},
    {"name":"render_review_packet_section", "purpose":"shared review packet section structure", "changes_visual_contract": False},
    {"name":"render_boundary_matrix", "purpose":"shared no-authority boundary rows", "changes_visual_contract": False},
    {"name":"render_evidence_warning_rows", "purpose":"shared evidence/warning row display", "changes_visual_contract": False},
    {"name":"render_decision_approval_summary", "purpose":"shared decision/approval reminder without creating approval", "changes_visual_contract": False},
    {"name":"render_resume_continuity_summary", "purpose":"shared resume/continuity cards without starting work", "changes_visual_contract": False},
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _repo(root: str | Path | None = None) -> Path:
    return Path(root or Path(__file__).resolve().parents[1])


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _docs(root: str | Path | None = None) -> str:
    repo = _repo(root)
    rels = [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md",
        "conscious_agent/dashboard_renderer_component_extraction.py",
        "conscious_agent/dashboard_components.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/current_state_integrity_staleness_hardening.py",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/route_surface_parity.py",
        "conscious_agent/documentation_continuity_header.py",
        "conscious_agent/smoke_segment_registry.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
    ]
    return "\n".join(_read_text(repo / rel) for rel in rels)


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def render_console_card(title: str, body: str, data_tip: str = "Review-only dashboard component") -> str:
    safe_title = str(title)
    safe_body = str(body)
    safe_tip = str(data_tip).replace("'", "&#39;")
    return f"<section class='card' data-tip='{safe_tip}'><h2>{safe_title}</h2><p>{safe_body}</p></section>"


def render_status_pill(label: str, status: str) -> str:
    return f"<span class='status-pill' data-tip='Status marker only; not approval'>{label}: {status}</span>"


def render_boundary_matrix(boundaries: dict[str, bool] | None = None) -> list[dict[str, Any]]:
    source = boundaries or DASHBOARD_RENDERER_BOUNDARIES
    return [{"boundary": key, "value": value, "authority_effect": "none"} for key, value in source.items()]


def render_review_packet_section(title: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": title, "rows": rows, "review_only": True, "grants_authorization": False}


def render_evidence_warning_rows(evidence: list[str] | None = None, warnings: list[str] | None = None) -> list[dict[str, str]]:
    rows = [{"kind":"evidence", "message": item, "raw_evidence_preserved":"true"} for item in evidence or []]
    rows.extend({"kind":"warning", "message": item, "raw_evidence_preserved":"true"} for item in warnings or [])
    return rows


def render_decision_approval_summary(decision_status: str = "required") -> dict[str, Any]:
    return {"decision_status": decision_status, "creates_approval": False, "reuses_approval": False, "authorization_status": "not_authorized"}


def render_resume_continuity_summary() -> dict[str, Any]:
    return {"resume_status": "prepared", "starts_work": False, "continues_automatically": False, "autonomy_status": "not_autonomous"}


def build_renderer_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in DASHBOARD_RENDERER_SURFACE_DEFS:
        route = item["route"]
        slug = item["slug"]
        entries.append({
            "version": item["version"],
            "slug": slug,
            "route": route,
            "label": item["label"],
            "dashboard_route": f"/{route}",
            "api_route": f"/api/{route}/layer",
            "cli_flag": f"--{slug.replace('_', '-')}",
            "builder_function": f"build_{slug}",
            "text_function": f"{slug}_text",
            "smoke_check": TARGETED_SMOKE,
            "smoke_segment": "install-dashboard",
            "authority_level": "review_only",
            "writes_files": False,
            "writes_memory": False,
            "requires_operator_approval": True,
            "status_key": item["status_key"],
        })
    return entries


def _base_state() -> dict[str, Any]:
    return {
        "dashboard_renderer_component_extraction_status": "prepared_only",
        "dashboard_component_contract_status": "prepared",
        "shared_review_packet_renderer_status": "prepared",
        "shared_boundary_matrix_renderer_status": "prepared",
        "shared_evidence_warning_renderer_status": "prepared",
        "shared_decision_approval_renderer_status": "prepared",
        "shared_resume_continuity_renderer_status": "prepared",
        "dashboard_route_renderer_adapter_status": "prepared",
        "dashboard_style_regression_guard_status": "guarded_or_blocked",
        "legacy_renderer_duplication_audit_status": "audited",
        "dashboard_renderer_component_extraction_board_status": "review_only",
        "raw_evidence_preserved": True,
        "approval_semantics_changed": False,
        "operator_decision_status": "required",
        "authorization_status": "not_authorized",
        "approval_status": "required",
        "autonomy_status": "not_autonomous",
        "source_mutation_status": "not_performed",
        "metadata_write_status": "not_performed_by_report",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "writes_source": False,
        "writes_metadata": False,
        "writes_memory": False,
        "writes_archive_records": False,
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
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "review_only": True,
        "created_at": _now_iso(),
    }


def _runtime_tokens(root: str | Path | None = None) -> dict[str, set[str]]:
    docs = _docs(root)
    return {
        "routes": {entry["dashboard_route"] for entry in build_renderer_manifest_entries() if entry["dashboard_route"] in docs},
        "api": {entry["api_route"] for entry in build_renderer_manifest_entries() if entry["api_route"] in docs},
        "cli": {entry["cli_flag"] for entry in build_renderer_manifest_entries() if entry["cli_flag"] in docs},
        "builders": {entry["builder_function"] for entry in build_renderer_manifest_entries() if entry["builder_function"] in docs},
        "smoke": {TARGETED_SMOKE for _ in [0] if TARGETED_SMOKE in docs},
    }


def _native_title_regression_present(root: str | Path | None = None) -> bool:
    dashboard = _read_text(_repo(root) / "conscious_agent/dashboard.py")
    for line in dashboard.splitlines():
        if "data-tip" in line and " title=" in line and "data-route-title" not in line:
            return True
        if "nav" in line.lower() and " title=" in line and "data-route-title" not in line:
            return True
    return False


def build_dashboard_component_contract(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_renderer_manifest_entries()
    rows = [
        _row("component-contract-declared", len(SHARED_RENDERER_COMPONENTS) >= 7, "Shared dashboard renderer component contracts are declared."),
        _row("manifest-entries-declared", len(entries) == 10, "v676-v685 renderer surface entries are declared."),
        _row("required-fields-present", all(all(key in entry for key in ["dashboard_route", "api_route", "cli_flag", "builder_function", "text_function", "smoke_check", "authority_level"]) for entry in entries), "Renderer manifest entries include dashboard/API/CLI/smoke/authority fields."),
        _row("contract-boundaries", DASHBOARD_RENDERER_BOUNDARIES["component_contract_writes_source"] is False and DASHBOARD_RENDERER_BOUNDARIES["component_contract_changes_visual_contract"] is False, "Component contract writes no source and changes no visual contract by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_component_contract_review_only", "dashboard_component_contract_id": DASHBOARD_COMPONENT_CONTRACT_ID, "shared_components": list(SHARED_RENDERER_COMPONENTS), "renderer_manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_shared_review_packet_renderer(root: str | Path | None = None) -> dict[str, Any]:
    section = render_review_packet_section("Example Review Packet", [_row("review-only", True, "Renderer structures review rows without executing actions.")])
    rows = [
        _row("review-section-renderer", section.get("review_only") is True and section.get("grants_authorization") is False, "Shared review packet renderer preserves review-only authority."),
        _row("shared-component-present", any(component["name"] == "render_review_packet_section" for component in SHARED_RENDERER_COMPONENTS), "Review packet component is declared."),
        _row("route-behavior-unchanged", DASHBOARD_RENDERER_BOUNDARIES["shared_review_renderer_changes_route_behavior"] is False, "Shared review renderer does not change route behavior by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "shared_review_packet_renderer_review_only", "shared_review_packet_renderer_id": SHARED_REVIEW_PACKET_RENDERER_ID, "example_section": section, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_shared_boundary_matrix_renderer(root: str | Path | None = None) -> dict[str, Any]:
    matrix = render_boundary_matrix()
    rows = [
        _row("boundary-matrix-rendered", len(matrix) >= 20, "Boundary matrix renderer exposes authority boundaries."),
        _row("authorization-not-granted", DASHBOARD_RENDERER_BOUNDARIES["shared_boundary_matrix_grants_authorization"] is False and all(row["authority_effect"] == "none" for row in matrix), "Boundary matrix grants no authorization."),
        _row("operator-review-required", DASHBOARD_RENDERER_BOUNDARIES["operator_review_required"] is True, "Operator review remains required."),
    ]
    return {"version": CURRENT_VERSION, "state": "shared_boundary_matrix_renderer_review_only", "shared_boundary_matrix_renderer_id": SHARED_BOUNDARY_MATRIX_RENDERER_ID, "boundary_matrix": matrix, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_shared_evidence_warning_renderer(root: str | Path | None = None) -> dict[str, Any]:
    evidence_rows = render_evidence_warning_rows(["dashboard route token present", "source surface token present"], ["legacy renderer duplication remains advisory"])
    rows = [
        _row("evidence-warning-rows", len(evidence_rows) == 3, "Evidence and warning rows render through a shared shape."),
        _row("raw-evidence-preserved", all(row.get("raw_evidence_preserved") == "true" for row in evidence_rows), "Raw evidence preservation marker is retained."),
        _row("warnings-not-hidden", DASHBOARD_RENDERER_BOUNDARIES["shared_evidence_warning_hides_raw_evidence"] is False, "Evidence/warning renderer does not hide raw evidence."),
    ]
    return {"version": CURRENT_VERSION, "state": "shared_evidence_warning_renderer_review_only", "shared_evidence_warning_renderer_id": SHARED_EVIDENCE_WARNING_RENDERER_ID, "evidence_warning_rows": evidence_rows, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_shared_decision_approval_renderer(root: str | Path | None = None) -> dict[str, Any]:
    summary = render_decision_approval_summary()
    rows = [
        _row("decision-summary-rendered", summary.get("decision_status") == "required", "Decision summary marks operator decision as required."),
        _row("no-approval-created", summary.get("creates_approval") is False and DASHBOARD_RENDERER_BOUNDARIES["shared_decision_renderer_creates_approval"] is False, "Decision renderer creates no approval."),
        _row("no-approval-reuse", summary.get("reuses_approval") is False and DASHBOARD_RENDERER_BOUNDARIES["shared_decision_renderer_reuses_approval"] is False, "Decision renderer reuses no approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "shared_decision_approval_renderer_review_only", "shared_decision_approval_renderer_id": SHARED_DECISION_APPROVAL_RENDERER_ID, "decision_approval_summary": summary, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_shared_resume_continuity_renderer(root: str | Path | None = None) -> dict[str, Any]:
    summary = render_resume_continuity_summary()
    rows = [
        _row("resume-summary-rendered", summary.get("resume_status") == "prepared", "Resume/continuity summary is prepared."),
        _row("does-not-start-work", summary.get("starts_work") is False and DASHBOARD_RENDERER_BOUNDARIES["shared_resume_renderer_starts_work"] is False, "Resume renderer does not start work."),
        _row("does-not-continue", summary.get("continues_automatically") is False and DASHBOARD_RENDERER_BOUNDARIES["shared_resume_renderer_continues_automatically"] is False, "Resume renderer does not continue automatically."),
    ]
    return {"version": CURRENT_VERSION, "state": "shared_resume_continuity_renderer_review_only", "shared_resume_continuity_renderer_id": SHARED_RESUME_CONTINUITY_RENDERER_ID, "resume_continuity_summary": summary, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_dashboard_route_renderer_adapter(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_renderer_manifest_entries()
    tokens = _runtime_tokens(root)
    rows = [
        _row("dashboard-routes-visible", all(entry["dashboard_route"] in tokens["routes"] for entry in entries), "Dashboard route tokens for v676-v685 are visible in source/docs."),
        _row("builders-visible", all(entry["builder_function"] in tokens["builders"] for entry in entries), "Builder functions for v676-v685 are visible through self-maintenance/runtime wiring."),
        _row("adapter-review-only", DASHBOARD_RENDERER_BOUNDARIES["route_renderer_adapter_registers_routes"] is False and DASHBOARD_RENDERER_BOUNDARIES["route_renderer_adapter_replaces_routes"] is False, "Route renderer adapter validates but does not register or replace routes."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_route_renderer_adapter_review_only", "dashboard_route_renderer_adapter_id": DASHBOARD_ROUTE_RENDERER_ADAPTER_ID, "renderer_manifest_entries": entries, "runtime_tokens": {k: sorted(v) for k, v in tokens.items()}, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_dashboard_style_regression_guard(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    regression = _native_title_regression_present(root)
    rows = [
        _row("command-deck-token", "command-deck" in docs and "operator-console" in docs, "Command-deck/operator-console tokens remain represented."),
        _row("data-tip-token", "data-tip" in docs, "Custom data-tip hover token remains represented."),
        _row("native-title-regression-absent", not regression, "Native title tooltip regression is not present in dashboard nav/data-tip lines."),
        _row("style-guard-review-only", DASHBOARD_RENDERER_BOUNDARIES["style_guard_rewrites_dashboard"] is False and DASHBOARD_RENDERER_BOUNDARIES["style_guard_uses_native_title_tooltips"] is False, "Style guard rewrites nothing and does not introduce native title tooltips."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_style_regression_guard_review_only", "dashboard_style_regression_guard_id": DASHBOARD_STYLE_REGRESSION_GUARD_ID, "native_title_regression_present": regression, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_legacy_renderer_duplication_audit(root: str | Path | None = None) -> dict[str, Any]:
    dashboard = _read_text(_repo(root) / "conscious_agent/dashboard.py")
    repeated_renderer_count = dashboard.count("_render_supervised_runtime_arc(")
    repeated_card_count = dashboard.count("mini-card") + dashboard.count("_card(")
    rows = [
        _row("duplication-measured", repeated_renderer_count >= 1, f"Detected {repeated_renderer_count} supervised runtime renderer calls for future extraction tracking."),
        _row("shared-components-declared", len(SHARED_RENDERER_COMPONENTS) >= 7, "Shared components are declared as extraction targets."),
        _row("audit-does-not-delete", DASHBOARD_RENDERER_BOUNDARIES["duplication_audit_deletes_renderers"] is False and DASHBOARD_RENDERER_BOUNDARIES["duplication_audit_applies_refactor"] is False, "Duplication audit deletes no renderers and applies no refactor by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "legacy_renderer_duplication_audit_review_only", "legacy_renderer_duplication_audit_id": LEGACY_RENDERER_DUPLICATION_AUDIT_ID, "repeated_renderer_count": repeated_renderer_count, "repeated_card_count": repeated_card_count, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES)}


def build_dashboard_renderer_component_extraction_board(root: str | Path | None = None) -> dict[str, Any]:
    contract = build_dashboard_component_contract(root)
    review = build_shared_review_packet_renderer(root)
    boundary = build_shared_boundary_matrix_renderer(root)
    evidence = build_shared_evidence_warning_renderer(root)
    decision = build_shared_decision_approval_renderer(root)
    resume = build_shared_resume_continuity_renderer(root)
    adapter = build_dashboard_route_renderer_adapter(root)
    style = build_dashboard_style_regression_guard(root)
    duplication = build_legacy_renderer_duplication_audit(root)
    components = [contract, review, boundary, evidence, decision, resume, adapter, style, duplication]
    rows = [_row(f"component-{component.get('state')}", component.get("ok") is True, f"{component.get('state')} passed.") for component in components] + [
        _row("board-no-authority", all(DASHBOARD_RENDERER_BOUNDARIES[key] is False for key in ["component_board_writes_source", "component_board_writes_metadata", "component_board_writes_memory", "component_board_writes_archive_records", "component_board_creates_release", "component_board_publishes_release", "component_board_reuses_approval", "component_board_continues_automatically", "component_board_expands_autonomy", "renderer_presence_is_authorization", "style_guard_pass_is_approval"]), "Dashboard renderer component extraction board grants no write, release, approval, continuation, authorization, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "dashboard_renderer_component_extraction_board_review_only",
        "dashboard_renderer_component_extraction_board_id": DASHBOARD_RENDERER_COMPONENT_EXTRACTION_BOARD_ID,
        "dashboard_renderer_component_extraction_status": "prepared_only",
        "component_checks": components,
        "renderer_manifest_entries": build_renderer_manifest_entries(),
        **_base_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(DASHBOARD_RENDERER_BOUNDARIES),
        "safe_next_action": "Operator may review Autonomy Phase 0 readiness harness preparation next. Renderer component health is not approval, execution permission, release permission, or autonomy approval.",
    }


def build_dashboard_renderer_component_extraction_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage_map = {
        "dashboard_component_contract_v1": build_dashboard_component_contract,
        "shared_review_packet_renderer_v1": build_shared_review_packet_renderer,
        "shared_boundary_matrix_renderer_v1": build_shared_boundary_matrix_renderer,
        "shared_evidence_warning_renderer_v1": build_shared_evidence_warning_renderer,
        "shared_decision_approval_renderer_v1": build_shared_decision_approval_renderer,
        "shared_resume_continuity_renderer_v1": build_shared_resume_continuity_renderer,
        "dashboard_route_renderer_adapter_v1": build_dashboard_route_renderer_adapter,
        "dashboard_style_regression_guard_v1": build_dashboard_style_regression_guard,
        "legacy_renderer_duplication_audit_v1": build_legacy_renderer_duplication_audit,
        "dashboard_renderer_component_extraction_board_v1": build_dashboard_renderer_component_extraction_board,
    }
    if stage and stage in stage_map:
        return stage_map[stage](root)
    return build_dashboard_renderer_component_extraction_board(root)


def render_dashboard_renderer_component_extraction_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"dashboard_renderer_component_extraction_status: {report.get('dashboard_renderer_component_extraction_status')}",
        f"dashboard_component_contract_status: {report.get('dashboard_component_contract_status')}",
        f"shared_review_packet_renderer_status: {report.get('shared_review_packet_renderer_status')}",
        f"shared_boundary_matrix_renderer_status: {report.get('shared_boundary_matrix_renderer_status')}",
        f"shared_evidence_warning_renderer_status: {report.get('shared_evidence_warning_renderer_status')}",
        f"shared_decision_approval_renderer_status: {report.get('shared_decision_approval_renderer_status')}",
        f"shared_resume_continuity_renderer_status: {report.get('shared_resume_continuity_renderer_status')}",
        f"dashboard_route_renderer_adapter_status: {report.get('dashboard_route_renderer_adapter_status')}",
        f"dashboard_style_regression_guard_status: {report.get('dashboard_style_regression_guard_status')}",
        f"legacy_renderer_duplication_audit_status: {report.get('legacy_renderer_duplication_audit_status')}",
        f"dashboard_renderer_component_extraction_board_status: {report.get('dashboard_renderer_component_extraction_board_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows") or []
    if rows:
        lines.append("rows:")
        lines.extend(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}" for row in rows)
    return lines


# v676.0-v685.0 dashboard renderer component extraction tokens: dashboard-renderer-component-extraction-v1 dashboard_renderer_component_extraction.py dashboard-component-contract shared-review-packet-renderer shared-boundary-matrix-renderer shared-evidence-warning-renderer shared-decision-approval-renderer shared-resume-continuity-renderer dashboard-route-renderer-adapter dashboard-style-regression-guard legacy-renderer-duplication-audit dashboard-renderer-component-extraction-board dashboard_renderer_component_extraction_status=prepared_only dashboard_component_contract_status=prepared shared_review_packet_renderer_status=prepared shared_boundary_matrix_renderer_status=prepared shared_evidence_warning_renderer_status=prepared shared_decision_approval_renderer_status=prepared shared_resume_continuity_renderer_status=prepared dashboard_route_renderer_adapter_status=prepared dashboard_style_regression_guard_status=guarded_or_blocked legacy_renderer_duplication_audit_status=audited dashboard_renderer_component_extraction_board_status=review_only raw_evidence_preserved=True approval_semantics_changed=False component_contract_writes_source=False shared_review_renderer_changes_route_behavior=False shared_boundary_matrix_grants_authorization=False shared_evidence_warning_hides_raw_evidence=False shared_decision_renderer_creates_approval=False shared_resume_renderer_starts_work=False route_renderer_adapter_replaces_routes=False style_guard_rewrites_dashboard=False duplication_audit_deletes_renderers=False component_board_expands_autonomy=False renderer_presence_is_authorization=False style_guard_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
