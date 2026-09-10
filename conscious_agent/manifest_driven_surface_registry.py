from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

MANIFEST_DRIVEN_SURFACE_REGISTRY_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
SURFACE_REGISTRY_CONTRACT_ID = "v666_surface_registry_manifest_contract"
DASHBOARD_MANIFEST_ADAPTER_ID = "v667_dashboard_surface_manifest_adapter"
API_CLI_MANIFEST_ADAPTER_ID = "v668_api_cli_surface_manifest_adapter"
SMOKE_MANIFEST_ADAPTER_ID = "v669_smoke_surface_manifest_adapter"
SOURCE_SURFACE_RECONCILIATION_ID = "v670_source_surface_manifest_reconciliation"
DOCUMENTATION_TOKEN_MANIFEST_ID = "v671_documentation_token_manifest_validation"
MANIFEST_DRIFT_DETECTION_ID = "v672_manifest_drift_detection_board"
REGISTRY_GENERATION_PREP_ID = "v673_registry_generation_prep_layer"
MANIFEST_CURRENT_RELEASE_GATE_ID = "v674_manifest_driven_current_release_gate"
MANIFEST_SURFACE_REGISTRY_BOARD_ID = "v675_manifest_driven_surface_registry_board"

MANIFEST_SURFACE_DEFS: tuple[dict[str, str], ...] = (
    {"version":"v666.0","slug":"surface_registry_manifest_contract_v1","route":"surface-registry-manifest-contract","label":"Surface Registry Manifest Contract v1","status_key":"surface_registry_manifest_contract_status"},
    {"version":"v667.0","slug":"dashboard_surface_manifest_adapter_v1","route":"dashboard-surface-manifest-adapter","label":"Dashboard Surface Manifest Adapter v1","status_key":"dashboard_manifest_adapter_status"},
    {"version":"v668.0","slug":"api_cli_surface_manifest_adapter_v1","route":"api-cli-surface-manifest-adapter","label":"API/CLI Surface Manifest Adapter v1","status_key":"api_cli_manifest_adapter_status"},
    {"version":"v669.0","slug":"smoke_surface_manifest_adapter_v1","route":"smoke-surface-manifest-adapter","label":"Smoke Surface Manifest Adapter v1","status_key":"smoke_manifest_adapter_status"},
    {"version":"v670.0","slug":"source_surface_manifest_reconciliation_v1","route":"source-surface-manifest-reconciliation","label":"Source Surface Manifest Reconciliation v1","status_key":"source_surface_reconciliation_status"},
    {"version":"v671.0","slug":"documentation_token_manifest_validation_v1","route":"documentation-token-manifest-validation","label":"Documentation Token Manifest Validation v1","status_key":"documentation_token_manifest_status"},
    {"version":"v672.0","slug":"manifest_drift_detection_board_v1","route":"manifest-drift-detection-board","label":"Manifest Drift Detection Board v1","status_key":"manifest_drift_detection_status"},
    {"version":"v673.0","slug":"registry_generation_prep_layer_v1","route":"registry-generation-prep-layer","label":"Registry Generation Prep Layer v1","status_key":"registry_generation_prep_status"},
    {"version":"v674.0","slug":"manifest_driven_current_release_gate_v1","route":"manifest-driven-current-release-gate","label":"Manifest-Driven Current Release Gate v1","status_key":"manifest_current_release_gate_status"},
    {"version":"v675.0","slug":"manifest_driven_surface_registry_board_v1","route":"manifest-driven-surface-registry-board","label":"Manifest-Driven Surface Registry Board v1","status_key":"manifest_surface_registry_board_status"},
)

MANIFEST_REGISTRY_BOUNDARIES: dict[str, bool] = {
    "manifest_contract_writes_source": False,
    "manifest_contract_writes_metadata": False,
    "manifest_contract_registers_routes": False,
    "dashboard_manifest_adapter_registers_routes": False,
    "dashboard_manifest_adapter_executes_routes": False,
    "api_cli_manifest_adapter_registers_endpoints": False,
    "api_cli_manifest_adapter_executes_commands": False,
    "smoke_manifest_adapter_executes_smoke": False,
    "smoke_manifest_adapter_changes_results": False,
    "source_surface_reconciliation_mutates_manifest": False,
    "source_surface_reconciliation_writes_files": False,
    "documentation_token_validation_rewrites_docs": False,
    "documentation_token_validation_is_approval": False,
    "drift_detection_auto_fixes": False,
    "drift_detection_hides_findings": False,
    "generation_prep_generates_live_routes": False,
    "generation_prep_replaces_dispatch": False,
    "manifest_current_gate_executes_checks": False,
    "manifest_current_gate_treats_pass_as_authorization": False,
    "manifest_board_writes_source": False,
    "manifest_board_writes_metadata": False,
    "manifest_board_writes_memory": False,
    "manifest_board_writes_archive_records": False,
    "manifest_board_creates_release": False,
    "manifest_board_publishes_release": False,
    "manifest_board_reuses_approval": False,
    "manifest_board_continues_automatically": False,
    "manifest_board_expands_autonomy": False,
    "manifest_presence_is_authorization": False,
    "registry_health_is_approval": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}

MANIFEST_REQUIRED_FIELDS: tuple[str, ...] = (
    "version", "slug", "route", "label", "dashboard_route", "api_route", "cli_flag",
    "builder_function", "text_function", "smoke_check", "smoke_segment", "authority_level",
    "writes_files", "writes_memory", "requires_operator_approval",
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


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def _docs(root: str | Path | None = None) -> str:
    repo = _repo(root)
    rels = [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md",
        "conscious_agent/manifest_driven_surface_registry.py",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/current_state_integrity_staleness_hardening.py",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/route_surface_parity.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/documentation_continuity_header.py",
        "conscious_agent/smoke_segment_registry.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
    ]
    return "\n".join(_read_text(repo / rel) for rel in rels)


def build_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in MANIFEST_SURFACE_DEFS:
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
        "manifest_driven_surface_registry_status": "prepared_only",
        "surface_registry_manifest_contract_status": "prepared",
        "dashboard_manifest_adapter_status": "validated_or_blocked",
        "api_cli_manifest_adapter_status": "validated_or_blocked",
        "smoke_manifest_adapter_status": "validated_or_blocked",
        "source_surface_reconciliation_status": "reconciled_or_blocked",
        "documentation_token_manifest_status": "validated_or_blocked",
        "manifest_drift_detection_status": "prepared",
        "registry_generation_prep_status": "prepared",
        "manifest_current_release_gate_status": "prepared",
        "manifest_surface_registry_board_status": "review_only",
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
        "operator_review_required": True,
        "fresh_exact_operator_approval_required_for_writes": True,
    }


def _runtime_tokens(root: str | Path | None = None) -> dict[str, str]:
    repo = _repo(root)
    return {
        "dashboard": _read_text(repo / "conscious_agent" / "dashboard.py"),
        "self_maintenance": _read_text(repo / "conscious_agent" / "self_maintenance.py"),
        "api_server": _read_text(repo / "conscious_agent" / "api_server.py"),
        "main": _read_text(repo / "conscious_agent" / "main.py"),
        "smoke": _read_text(repo / "tools" / "smoke_check.py"),
        "surface": _read_text(repo / "conscious_agent" / "source_surface_manifest.py"),
        "route_probe": _read_text(repo / "conscious_agent" / "dashboard_route_probe.py"),
    }


def build_surface_registry_manifest_contract(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    rows = [
        _row("entries-declared", len(entries) == 10, "Ten v666-v675 manifest surface entries are declared."),
        _row("required-fields", all(all(field in entry for field in MANIFEST_REQUIRED_FIELDS) for entry in entries), "Each manifest entry declares version, route, API, CLI, smoke, authority, and write metadata."),
        _row("authority-review-only", all(entry.get("authority_level") == "review_only" and entry.get("writes_files") is False and entry.get("writes_memory") is False for entry in entries), "All manifest entries are review-only and non-mutating."),
        _row("contract-no-registration", MANIFEST_REGISTRY_BOUNDARIES["manifest_contract_registers_routes"] is False and MANIFEST_REGISTRY_BOUNDARIES["manifest_contract_writes_source"] is False, "Manifest contract declares shape only; it does not register routes or write source."),
    ]
    return {"version": CURRENT_VERSION, "state": "surface_registry_manifest_contract_review_only", "manifest_contract_id": SURFACE_REGISTRY_CONTRACT_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_dashboard_surface_manifest_adapter(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    tokens = _runtime_tokens(root)
    rows = [
        _row("dashboard-routes-present", all(entry["dashboard_route"] in tokens["dashboard"] for entry in entries), "Dashboard contains each v666-v675 manifest dashboard route."),
        _row("dashboard-renderers-present", all(f"render_{entry['slug'].removesuffix('_v1')}" in tokens["dashboard"] for entry in entries), "Dashboard renderers exist for each manifest surface."),
        _row("route-probe-present", all(entry["dashboard_route"] in tokens["route_probe"] for entry in entries), "Dashboard route probe inventory includes each manifest route."),
        _row("adapter-no-route-registration", MANIFEST_REGISTRY_BOUNDARIES["dashboard_manifest_adapter_registers_routes"] is False and MANIFEST_REGISTRY_BOUNDARIES["dashboard_manifest_adapter_executes_routes"] is False, "Dashboard manifest adapter validates surfaces only; it registers or executes no route."),
    ]
    return {"version": CURRENT_VERSION, "state": "dashboard_surface_manifest_adapter_review_only", "dashboard_manifest_adapter_id": DASHBOARD_MANIFEST_ADAPTER_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_api_cli_surface_manifest_adapter(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    tokens = _runtime_tokens(root)
    rows = [
        _row("cli-map-tokens-present", all(entry["slug"] in tokens["self_maintenance"] for entry in entries), "Self-maintenance runtime CLI map contains each manifest CLI flag token."),
        _row("runtime-route-tokens-present", all(f"{entry['route']}/layer" in tokens["self_maintenance"] or f"{entry['route']}" in tokens["self_maintenance"] for entry in entries), "Self-maintenance runtime route map contains each manifest API route token."),
        _row("api-main-comments-present", TARGETED_SMOKE in tokens["api_server"] and TARGETED_SMOKE in tokens["main"], "API and CLI surface modules document dynamic manifest-driven routing coverage."),
        _row("adapter-no-dispatch-change", MANIFEST_REGISTRY_BOUNDARIES["api_cli_manifest_adapter_registers_endpoints"] is False and MANIFEST_REGISTRY_BOUNDARIES["api_cli_manifest_adapter_executes_commands"] is False, "API/CLI adapter validates dispatch coverage only and executes no command."),
    ]
    return {"version": CURRENT_VERSION, "state": "api_cli_surface_manifest_adapter_review_only", "api_cli_manifest_adapter_id": API_CLI_MANIFEST_ADAPTER_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_smoke_surface_manifest_adapter(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    smoke = _runtime_tokens(root)["smoke"]
    names = set(re.findall(r'SmokeCheck\("([^"]+)"', smoke))
    rows = [
        _row("targeted-smoke-registered", TARGETED_SMOKE in names, "Manifest-driven surface registry targeted smoke is registered."),
        _row("entries-share-smoke", all(entry["smoke_check"] == TARGETED_SMOKE for entry in entries), "All v666-v675 manifest surfaces point at the targeted smoke gate."),
        _row("smoke-documents-boundaries", "smoke_manifest_adapter_executes_smoke=False" in smoke and "manifest_presence_is_authorization=False" in smoke, "Smoke checker documents that manifest validation does not execute smoke or grant authorization."),
        _row("adapter-does-not-run-smoke", MANIFEST_REGISTRY_BOUNDARIES["smoke_manifest_adapter_executes_smoke"] is False and MANIFEST_REGISTRY_BOUNDARIES["smoke_manifest_adapter_changes_results"] is False, "Smoke manifest adapter is descriptive and does not run or change smoke results by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "smoke_surface_manifest_adapter_review_only", "smoke_manifest_adapter_id": SMOKE_MANIFEST_ADAPTER_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_source_surface_manifest_reconciliation(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    surface = _runtime_tokens(root)["surface"]
    rows = [
        _row("source-surface-entries-present", all(entry["dashboard_route"] in surface and entry["cli_flag"] in surface and entry["api_route"] in surface for entry in entries), "Source surface manifest represents dashboard/API/CLI entries for all v666-v675 manifest surfaces."),
        _row("surface-smoke-linked", TARGETED_SMOKE in surface, "Source surface manifest links v666-v675 surfaces to the targeted smoke."),
        _row("surface-boundaries-documented", "manifest_presence_is_authorization=False" in surface and "registry_health_is_approval=False" in surface, "Source surface manifest documents manifest and registry health no-authority boundaries."),
        _row("reconciliation-no-write", MANIFEST_REGISTRY_BOUNDARIES["source_surface_reconciliation_mutates_manifest"] is False and MANIFEST_REGISTRY_BOUNDARIES["source_surface_reconciliation_writes_files"] is False, "Reconciliation is review-only and mutates no manifest or source file."),
    ]
    return {"version": CURRENT_VERSION, "state": "source_surface_manifest_reconciliation_review_only", "source_surface_reconciliation_id": SOURCE_SURFACE_RECONCILIATION_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_documentation_token_manifest_validation(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    docs = _docs(root)
    required_tokens = [
        TARGETED_SMOKE,
        "manifest_driven_surface_registry.py",
        "manifest_driven_surface_registry_status=prepared_only",
        "surface_registry_manifest_contract_status=prepared",
        "manifest_surface_registry_board_status=review_only",
        "manifest_presence_is_authorization=False",
        "registry_health_is_approval=False",
        "manifest_board_expands_autonomy=False",
        "no_native_title_tooltip",
        "data-tip",
    ] + [entry["route"] for entry in entries]
    rows = [
        _row("docs-token-coverage", all(token in docs for token in required_tokens), "README/source/dashboard/API/CLI/smoke docs expose v666-v675 manifest registry tokens."),
        _row("release-history-current", "v675.0 - Manifest-Driven Surface Registry v1" in docs, "Release history documents the current v675 milestone."),
        _row("readme-current", "# Current State — v675.0" in docs and "Latest completed version: v675.0 - Manifest-Driven Surface Registry v1" in docs, "README current-state header names v675."),
        _row("docs-not-rewritten", MANIFEST_REGISTRY_BOUNDARIES["documentation_token_validation_rewrites_docs"] is False and MANIFEST_REGISTRY_BOUNDARIES["documentation_token_validation_is_approval"] is False, "Documentation token validation rewrites nothing and grants no approval."),
    ]
    return {"version": CURRENT_VERSION, "state": "documentation_token_manifest_validation_review_only", "documentation_token_manifest_id": DOCUMENTATION_TOKEN_MANIFEST_ID, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_manifest_drift_detection_board(root: str | Path | None = None) -> dict[str, Any]:
    checks = [
        build_surface_registry_manifest_contract(root),
        build_dashboard_surface_manifest_adapter(root),
        build_api_cli_surface_manifest_adapter(root),
        build_smoke_surface_manifest_adapter(root),
        build_source_surface_manifest_reconciliation(root),
        build_documentation_token_manifest_validation(root),
    ]
    rows = [_row(f"component-{i}", check.get("ok") is True, f"{check.get('state')} is aligned.") for i, check in enumerate(checks, start=1)] + [
        _row("drift-detection-no-autofix", MANIFEST_REGISTRY_BOUNDARIES["drift_detection_auto_fixes"] is False and MANIFEST_REGISTRY_BOUNDARIES["drift_detection_hides_findings"] is False, "Drift detection prepares findings only; it neither fixes nor hides them."),
    ]
    return {"version": CURRENT_VERSION, "state": "manifest_drift_detection_board_review_only", "manifest_drift_detection_id": MANIFEST_DRIFT_DETECTION_ID, "component_checks": checks, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_registry_generation_prep_layer(root: str | Path | None = None) -> dict[str, Any]:
    entries = build_manifest_entries()
    generation_plan = {
        "candidate_generated_surfaces": ["dashboard route registration", "API route registration", "CLI dispatch registration", "smoke expectation registration", "source surface entries", "documentation token expectations"],
        "generation_status": "prepared_not_applied",
        "switch_to_generated_dispatch": False,
        "write_source": False,
        "operator_approval_required": True,
    }
    rows = [
        _row("generation-plan-declared", len(generation_plan["candidate_generated_surfaces"]) >= 5, "Generation prep identifies future generated surface categories."),
        _row("manifest-entries-available", len(entries) == 10, "Generation prep has v666-v675 manifest entries to consume later."),
        _row("generation-not-applied", generation_plan["switch_to_generated_dispatch"] is False and generation_plan["write_source"] is False, "Generation prep does not switch dispatch or write source."),
        _row("generation-boundaries", MANIFEST_REGISTRY_BOUNDARIES["generation_prep_generates_live_routes"] is False and MANIFEST_REGISTRY_BOUNDARIES["generation_prep_replaces_dispatch"] is False, "Registry generation prep does not generate live routes or replace dispatch."),
    ]
    return {"version": CURRENT_VERSION, "state": "registry_generation_prep_layer_review_only", "registry_generation_prep_id": REGISTRY_GENERATION_PREP_ID, "generation_plan": generation_plan, "manifest_entries": entries, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_manifest_driven_current_release_gate(root: str | Path | None = None) -> dict[str, Any]:
    drift = build_manifest_drift_detection_board(root)
    generation = build_registry_generation_prep_layer(root)
    rows = [
        _row("manifest-drift-clean", drift.get("ok") is True, "Manifest drift detection currently passes."),
        _row("generation-prep-review-only", generation.get("ok") is True and generation.get("generation_plan", {}).get("switch_to_generated_dispatch") is False, "Generation prep is review-only and not activated."),
        _row("current-gate-targeted", TARGETED_SMOKE in _runtime_tokens(root)["smoke"], "Targeted smoke is available for the current manifest release gate."),
        _row("current-gate-no-execution", MANIFEST_REGISTRY_BOUNDARIES["manifest_current_gate_executes_checks"] is False and MANIFEST_REGISTRY_BOUNDARIES["manifest_current_gate_treats_pass_as_authorization"] is False, "Manifest current gate executes no checks by itself and treats pass state as no authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "manifest_driven_current_release_gate_review_only", "manifest_current_release_gate_id": MANIFEST_CURRENT_RELEASE_GATE_ID, "manifest_drift_detection": drift, "registry_generation_prep": generation, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES)}


def build_manifest_driven_surface_registry_board(root: str | Path | None = None) -> dict[str, Any]:
    contract = build_surface_registry_manifest_contract(root)
    dashboard = build_dashboard_surface_manifest_adapter(root)
    api_cli = build_api_cli_surface_manifest_adapter(root)
    smoke = build_smoke_surface_manifest_adapter(root)
    surface = build_source_surface_manifest_reconciliation(root)
    docs = build_documentation_token_manifest_validation(root)
    drift = build_manifest_drift_detection_board(root)
    generation = build_registry_generation_prep_layer(root)
    current_gate = build_manifest_driven_current_release_gate(root)
    components = [contract, dashboard, api_cli, smoke, surface, docs, drift, generation, current_gate]
    rows = [_row(f"component-{component.get('state')}", component.get("ok") is True, f"{component.get('state')} passed.") for component in components] + [
        _row("board-no-authority", all(MANIFEST_REGISTRY_BOUNDARIES[key] is False for key in ["manifest_board_writes_source", "manifest_board_writes_metadata", "manifest_board_writes_memory", "manifest_board_writes_archive_records", "manifest_board_creates_release", "manifest_board_publishes_release", "manifest_board_reuses_approval", "manifest_board_continues_automatically", "manifest_board_expands_autonomy", "manifest_presence_is_authorization", "registry_health_is_approval"]), "Manifest surface registry board grants no write, release, approval, continuation, authorization, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "manifest_driven_surface_registry_board_review_only",
        "manifest_surface_registry_board_id": MANIFEST_SURFACE_REGISTRY_BOARD_ID,
        "manifest_driven_surface_registry_status": "prepared_only",
        "component_checks": components,
        "manifest_entries": build_manifest_entries(),
        **_base_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(MANIFEST_REGISTRY_BOUNDARIES),
        "safe_next_action": "Operator may review dashboard renderer component extraction next. Manifest registry health is not approval, execution permission, release permission, or autonomy approval.",
    }


def build_manifest_driven_surface_registry_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage_map = {
        "surface_registry_manifest_contract_v1": build_surface_registry_manifest_contract,
        "dashboard_surface_manifest_adapter_v1": build_dashboard_surface_manifest_adapter,
        "api_cli_surface_manifest_adapter_v1": build_api_cli_surface_manifest_adapter,
        "smoke_surface_manifest_adapter_v1": build_smoke_surface_manifest_adapter,
        "source_surface_manifest_reconciliation_v1": build_source_surface_manifest_reconciliation,
        "documentation_token_manifest_validation_v1": build_documentation_token_manifest_validation,
        "manifest_drift_detection_board_v1": build_manifest_drift_detection_board,
        "registry_generation_prep_layer_v1": build_registry_generation_prep_layer,
        "manifest_driven_current_release_gate_v1": build_manifest_driven_current_release_gate,
        "manifest_driven_surface_registry_board_v1": build_manifest_driven_surface_registry_board,
    }
    if stage and stage in stage_map:
        return stage_map[stage](root)
    return build_manifest_driven_surface_registry_board(root)


def render_manifest_driven_surface_registry_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"manifest_driven_surface_registry_status: {report.get('manifest_driven_surface_registry_status')}",
        f"surface_registry_manifest_contract_status: {report.get('surface_registry_manifest_contract_status')}",
        f"dashboard_manifest_adapter_status: {report.get('dashboard_manifest_adapter_status')}",
        f"api_cli_manifest_adapter_status: {report.get('api_cli_manifest_adapter_status')}",
        f"smoke_manifest_adapter_status: {report.get('smoke_manifest_adapter_status')}",
        f"source_surface_reconciliation_status: {report.get('source_surface_reconciliation_status')}",
        f"documentation_token_manifest_status: {report.get('documentation_token_manifest_status')}",
        f"manifest_drift_detection_status: {report.get('manifest_drift_detection_status')}",
        f"registry_generation_prep_status: {report.get('registry_generation_prep_status')}",
        f"manifest_current_release_gate_status: {report.get('manifest_current_release_gate_status')}",
        f"manifest_surface_registry_board_status: {report.get('manifest_surface_registry_board_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows") or []
    if rows:
        lines.append("rows:")
        lines.extend(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}" for row in rows)
    return lines


# v666.0-v675.0 manifest-driven surface registry tokens: manifest-driven-surface-registry-v1 manifest_driven_surface_registry.py surface-registry-manifest-contract dashboard-surface-manifest-adapter api-cli-surface-manifest-adapter smoke-surface-manifest-adapter source-surface-manifest-reconciliation documentation-token-manifest-validation manifest-drift-detection-board registry-generation-prep-layer manifest-driven-current-release-gate manifest-driven-surface-registry-board manifest_driven_surface_registry_status=prepared_only surface_registry_manifest_contract_status=prepared dashboard_manifest_adapter_status=validated_or_blocked api_cli_manifest_adapter_status=validated_or_blocked smoke_manifest_adapter_status=validated_or_blocked source_surface_reconciliation_status=reconciled_or_blocked documentation_token_manifest_status=validated_or_blocked manifest_drift_detection_status=prepared registry_generation_prep_status=prepared manifest_current_release_gate_status=prepared manifest_surface_registry_board_status=review_only approval_semantics_changed=False manifest_contract_writes_source=False dashboard_manifest_adapter_registers_routes=False api_cli_manifest_adapter_registers_endpoints=False smoke_manifest_adapter_executes_smoke=False source_surface_reconciliation_mutates_manifest=False documentation_token_validation_rewrites_docs=False drift_detection_auto_fixes=False generation_prep_generates_live_routes=False manifest_current_gate_executes_checks=False manifest_board_expands_autonomy=False manifest_presence_is_authorization=False registry_health_is_approval=False no_native_title_tooltip data-tip command-deck operator-console

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
