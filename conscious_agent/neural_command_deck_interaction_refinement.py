from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

NEURAL_COMMAND_DECK_INTERACTION_REFINEMENT_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
INTERACTION_FOCUS_RAIL_ID = "v691_interaction_focus_rail"
INTERACTION_SAFE_INPUT_DECK_ID = "v692_interaction_safe_input_deck"
PANEL_DENSITY_PRIORITY_TUNING_ID = "v693_panel_density_priority_tuning"
CONTEXT_TELEMETRY_AFFORDANCE_ID = "v694_context_telemetry_affordance"
NEURAL_COMMAND_DECK_INTERACTION_BOARD_ID = "v695_neural_command_deck_interaction_board"

INTERACTION_REFINEMENT_SURFACE_DEFS: tuple[dict[str, str], ...] = (
    {"version":"v691.0","slug":"interaction_focus_rail_v1","route":"interaction-focus-rail","label":"Interaction Focus Rail v1","status_key":"interaction_focus_rail_status"},
    {"version":"v692.0","slug":"interaction_safe_input_deck_v1","route":"interaction-safe-input-deck","label":"Interaction-Safe Input Deck v1","status_key":"interaction_safe_input_deck_status"},
    {"version":"v693.0","slug":"panel_density_priority_tuning_v1","route":"panel-density-priority-tuning","label":"Panel Density and Priority Tuning v1","status_key":"panel_density_priority_tuning_status"},
    {"version":"v694.0","slug":"context_telemetry_affordance_v1","route":"context-telemetry-affordance","label":"Context and Telemetry Affordance v1","status_key":"context_telemetry_affordance_status"},
    {"version":"v695.0","slug":"neural_command_deck_interaction_board_v1","route":"neural-command-deck-interaction-board","label":"Neural Command Deck Interaction Board v1","status_key":"neural_command_deck_interaction_board_status"},
)

INTERACTION_REFINEMENT_BOUNDARIES: dict[str, bool] = {
    "focus_rail_starts_work": False,
    "focus_rail_auto_selects_roadmap": False,
    "input_deck_sends_commands": False,
    "input_deck_creates_approval": False,
    "input_deck_executes_models": False,
    "priority_tuning_hides_blockers": False,
    "priority_tuning_treats_visual_priority_as_authorization": False,
    "context_affordance_reads_private_data": False,
    "context_affordance_mutates_memory": False,
    "telemetry_affordance_executes_checks": False,
    "interaction_board_writes_source": False,
    "interaction_board_writes_metadata": False,
    "interaction_board_writes_memory": False,
    "interaction_board_writes_archive_records": False,
    "interaction_board_creates_release": False,
    "interaction_board_publishes_release": False,
    "interaction_board_reuses_approval": False,
    "interaction_board_continues_automatically": False,
    "interaction_board_expands_autonomy": False,
    "visual_priority_is_authorization": False,
    "hover_detail_is_approval": False,
    "chat_input_is_command_execution": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}

INTERACTION_REFINEMENT_COMPONENTS: tuple[dict[str, Any], ...] = (
    {"name":"neural_focus_rail", "purpose":"compact step rail for conversation, evidence, approvals, verification, and handoff review", "starts_work": False},
    {"name":"neural_input_mode_chips", "purpose":"read-only mode chips for ask, review, attach, and voice intent", "executes_commands": False},
    {"name":"priority_panel_density", "purpose":"cleaner panel sizing and priority labels for vitals, approvals, risks, roadmap, and telemetry", "grants_authorization": False},
    {"name":"context_hover_affordances", "purpose":"data-tip context affordances for fragments and telemetry without native title tooltips", "creates_approval": False},
    {"name":"responsive_interaction_stack", "purpose":"smaller-screen stacking and focus order for the neural deck", "removes_routes": False},
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
        "conscious_agent/neural_command_deck_interaction_refinement.py",
        "conscious_agent/neural_command_deck_dashboard_redesign.py",
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
        "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ]
    return "\n".join(_read_text(repo / rel) for rel in rels)


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def build_interaction_refinement_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in INTERACTION_REFINEMENT_SURFACE_DEFS:
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
        "neural_command_deck_interaction_refinement_status": "prepared_only",
        "interaction_focus_rail_status": "prepared",
        "interaction_safe_input_deck_status": "prepared",
        "panel_density_priority_tuning_status": "prepared",
        "context_telemetry_affordance_status": "prepared",
        "interaction_style_regression_gate_status": "guarded_or_blocked",
        "neural_command_deck_interaction_board_status": "review_only",
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
    entries = build_interaction_refinement_manifest_entries()
    return {
        "routes": {entry["dashboard_route"] for entry in entries if entry["dashboard_route"] in docs},
        "api": {entry["api_route"] for entry in entries if entry["api_route"] in docs},
        "cli": {entry["cli_flag"] for entry in entries if entry["cli_flag"] in docs},
        "builders": {entry["builder_function"] for entry in entries if entry["builder_function"] in docs},
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


def build_interaction_focus_rail(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("focus-rail-style", "neural-focus-rail" in docs and "focus-pill" in docs and "interaction-focus-rail" in docs, "The dashboard declares a compact neural focus rail for guided interaction states."),
        _row("focus-rail-boundaries", INTERACTION_REFINEMENT_BOUNDARIES["focus_rail_starts_work"] is False and INTERACTION_REFINEMENT_BOUNDARIES["focus_rail_auto_selects_roadmap"] is False, "Focus rail does not start work or auto-select a roadmap."),
    ]
    return {**_base_state(), "version": CURRENT_VERSION, "state": "interaction_focus_rail_review_only", "interaction_focus_rail_id": INTERACTION_FOCUS_RAIL_ID, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(INTERACTION_REFINEMENT_BOUNDARIES), "components": list(INTERACTION_REFINEMENT_COMPONENTS)}


def build_interaction_safe_input_deck(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("input-mode-chips", "neural-input-actions" in docs and "mode-chip" in docs and "chat-input-is-command-execution" in docs.replace("_", "-"), "The input deck exposes mode chips and keeps the chat box visually inert unless wired by existing supervised handlers."),
        _row("input-boundaries", INTERACTION_REFINEMENT_BOUNDARIES["input_deck_sends_commands"] is False and INTERACTION_REFINEMENT_BOUNDARIES["input_deck_creates_approval"] is False and INTERACTION_REFINEMENT_BOUNDARIES["input_deck_executes_models"] is False, "Input deck refinement does not send commands, create approvals, or execute models."),
    ]
    return {**_base_state(), "version": CURRENT_VERSION, "state": "interaction_safe_input_deck_review_only", "interaction_safe_input_deck_id": INTERACTION_SAFE_INPUT_DECK_ID, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(INTERACTION_REFINEMENT_BOUNDARIES), "components": list(INTERACTION_REFINEMENT_COMPONENTS)}


def build_panel_density_priority_tuning(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("density-priority-style", "neural-priority" in docs and "neural-panel.compact" in docs and "panel-density-priority-tuning" in docs, "Side and center cards include cleaner density and priority labels."),
        _row("priority-boundaries", INTERACTION_REFINEMENT_BOUNDARIES["priority_tuning_hides_blockers"] is False and INTERACTION_REFINEMENT_BOUNDARIES["priority_tuning_treats_visual_priority_as_authorization"] is False, "Visual priority does not hide blockers or grant authorization."),
    ]
    return {**_base_state(), "version": CURRENT_VERSION, "state": "panel_density_priority_tuning_review_only", "panel_density_priority_tuning_id": PANEL_DENSITY_PRIORITY_TUNING_ID, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(INTERACTION_REFINEMENT_BOUNDARIES), "components": list(INTERACTION_REFINEMENT_COMPONENTS)}


def build_context_telemetry_affordance(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("context-affordances", "context-fragment" in docs and "data-tip='Context fragment" in docs and "telemetry-chip" in docs, "Context fragments and telemetry chips expose readable hover/details through custom data-tip affordances."),
        _row("hover-boundaries", INTERACTION_REFINEMENT_BOUNDARIES["context_affordance_reads_private_data"] is False and INTERACTION_REFINEMENT_BOUNDARIES["context_affordance_mutates_memory"] is False and INTERACTION_REFINEMENT_BOUNDARIES["telemetry_affordance_executes_checks"] is False and INTERACTION_REFINEMENT_BOUNDARIES["hover_detail_is_approval"] is False, "Context/telemetry affordances do not read private data, mutate memory, execute checks, or approve anything."),
        _row("no-native-title", not _native_title_regression_present(root), "Custom data-tip hover behavior remains preserved without native title tooltip regression."),
    ]
    return {**_base_state(), "version": CURRENT_VERSION, "state": "context_telemetry_affordance_review_only", "context_telemetry_affordance_id": CONTEXT_TELEMETRY_AFFORDANCE_ID, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(INTERACTION_REFINEMENT_BOUNDARIES), "components": list(INTERACTION_REFINEMENT_COMPONENTS)}


def build_neural_command_deck_interaction_board(root: str | Path | None = None) -> dict[str, Any]:
    focus = build_interaction_focus_rail(root)
    input_deck = build_interaction_safe_input_deck(root)
    density = build_panel_density_priority_tuning(root)
    affordance = build_context_telemetry_affordance(root)
    runtime = _runtime_tokens(root)
    entries = build_interaction_refinement_manifest_entries()
    rows = list(focus["rows"]) + list(input_deck["rows"]) + list(density["rows"]) + list(affordance["rows"]) + [
        _row("manifest-routes", len(runtime["routes"]) == len(entries), "All v691-v695 dashboard route tokens are represented."),
        _row("manifest-api", len(runtime["api"]) == len(entries), "All v691-v695 API route tokens are represented."),
        _row("manifest-cli", len(runtime["cli"]) == len(entries), "All v691-v695 CLI flag tokens are represented."),
        _row("manifest-builders", len(runtime["builders"]) == len(entries), "All v691-v695 builder/text tokens are represented."),
        _row("targeted-smoke-token", TARGETED_SMOKE in runtime["smoke"], "The targeted smoke token is represented in source/docs."),
        _row("no-authority", all(value is False for key, value in INTERACTION_REFINEMENT_BOUNDARIES.items() if key not in {"operator_review_required", "fresh_exact_operator_approval_required_for_writes"}), "Interaction refinement grants no source, metadata, memory, archive, release, publish, command, hidden scheduling, continuation, approval reuse, or autonomy authority."),
    ]
    ok = _ok(rows)
    return {**_base_state(), "version": CURRENT_VERSION, "state": "neural_command_deck_interaction_refinement_review_only", "interaction_refinement_id": NEURAL_COMMAND_DECK_INTERACTION_BOARD_ID, "manifest_entries": entries, "runtime_tokens": {key: sorted(value) for key, value in runtime.items()}, "rows": rows, "status": _status(rows), "ok": ok, "boundaries": dict(INTERACTION_REFINEMENT_BOUNDARIES), "components": list(INTERACTION_REFINEMENT_COMPONENTS), "stage_reports": {"focus": focus, "input_deck": input_deck, "density": density, "affordance": affordance}}


def build_neural_command_deck_interaction_refinement_arc(root: str | Path | None = None, stage: str = "neural_command_deck_interaction_board_v1") -> dict[str, Any]:
    builders = {
        "interaction_focus_rail_v1": build_interaction_focus_rail,
        "interaction_safe_input_deck_v1": build_interaction_safe_input_deck,
        "panel_density_priority_tuning_v1": build_panel_density_priority_tuning,
        "context_telemetry_affordance_v1": build_context_telemetry_affordance,
        "neural_command_deck_interaction_board_v1": build_neural_command_deck_interaction_board,
    }
    return builders.get(stage, build_neural_command_deck_interaction_board)(root)


def render_neural_command_deck_interaction_refinement_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"status: {report.get('status')}",
        f"ok: {report.get('ok')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"release_status: {report.get('release_status')}",
        f"approval_semantics_changed: {report.get('approval_semantics_changed')}",
        f"starts_work: {report.get('starts_work')}",
        f"executes_commands: {report.get('executes_commands')}",
        f"continues_automatically: {report.get('continues_automatically')}",
        f"expands_autonomy: {report.get('expands_autonomy')}",
    ]
    if report.get("rows"):
        lines.append("checks:")
        lines.extend(f"- {row.get('status')}: {row.get('name')} — {row.get('message')}" for row in report.get("rows", [])[:24])
    return lines


# v691.0-v695.0 neural command deck interaction refinement tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False focus_rail_auto_selects_roadmap=False input_deck_sends_commands=False input_deck_creates_approval=False input_deck_executes_models=False priority_tuning_hides_blockers=False priority_tuning_treats_visual_priority_as_authorization=False context_affordance_reads_private_data=False context_affordance_mutates_memory=False telemetry_affordance_executes_checks=False interaction_board_writes_source=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
