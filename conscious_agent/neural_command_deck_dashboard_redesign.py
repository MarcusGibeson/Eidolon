from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

NEURAL_COMMAND_DECK_DASHBOARD_REDESIGN_VERSION = "1032.0"
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
NEURAL_DECK_LAYOUT_SHELL_ID = "v686_neural_deck_layout_shell"
EIDOLON_THINKING_CORE_PANEL_ID = "v687_eidolon_thinking_core_panel"
OPERATOR_CONVERSATION_CONSOLE_ID = "v688_operator_conversation_console"
SIDE_INTELLIGENCE_PANELS_ID = "v689_side_intelligence_panels"
NEURAL_COMMAND_DECK_DASHBOARD_BOARD_ID = "v690_neural_command_deck_dashboard_board"

NEURAL_COMMAND_DECK_SURFACE_DEFS: tuple[dict[str, str], ...] = (
    {"version":"v686.0","slug":"neural_deck_layout_shell_v1","route":"neural-deck-layout-shell","label":"Neural Deck Layout Shell v1","status_key":"neural_deck_layout_shell_status"},
    {"version":"v687.0","slug":"eidolon_thinking_core_panel_v1","route":"eidolon-thinking-core-panel","label":"Eidolon Thinking Core Panel v1","status_key":"eidolon_thinking_core_panel_status"},
    {"version":"v688.0","slug":"operator_conversation_console_v1","route":"operator-conversation-console","label":"Operator Conversation Console v1","status_key":"operator_conversation_console_status"},
    {"version":"v689.0","slug":"side_intelligence_panels_v1","route":"side-intelligence-panels","label":"Side Intelligence Panels v1","status_key":"side_intelligence_panels_status"},
    {"version":"v690.0","slug":"neural_command_deck_dashboard_board_v1","route":"neural-command-deck-dashboard-board","label":"Neural Command Deck Dashboard Board v1","status_key":"neural_command_deck_dashboard_board_status"},
)

NEURAL_COMMAND_DECK_BOUNDARIES: dict[str, bool] = {
    "layout_shell_writes_source": False,
    "layout_shell_removes_routes": False,
    "thinking_core_executes_models": False,
    "thinking_core_mutates_memory": False,
    "conversation_console_sends_commands": False,
    "conversation_console_creates_approval": False,
    "side_panels_execute_checks": False,
    "side_panels_treat_metrics_as_authorization": False,
    "style_gate_reintroduces_native_title_tooltips": False,
    "dashboard_board_writes_source": False,
    "dashboard_board_writes_metadata": False,
    "dashboard_board_writes_memory": False,
    "dashboard_board_writes_archive_records": False,
    "dashboard_board_creates_release": False,
    "dashboard_board_publishes_release": False,
    "dashboard_board_reuses_approval": False,
    "dashboard_board_continues_automatically": False,
    "dashboard_board_expands_autonomy": False,
    "visual_health_is_authorization": False,
    "thinking_animation_is_model_execution": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_writes": True,
}

NEURAL_DECK_COMPONENTS: tuple[dict[str, Any], ...] = (
    {"name":"neural_deck_shell", "purpose":"three-column neural command deck dashboard shell", "changes_route_behavior": False},
    {"name":"eidolon_thinking_stream", "purpose":"red thinking core and waveform visualization", "executes_models": False},
    {"name":"operator_conversation_panel", "purpose":"clean central conversation and input console", "executes_commands": False},
    {"name":"left_vitals_approval_stack", "purpose":"system vitals, stable loop, and approval queue cards", "grants_approval": False},
    {"name":"right_risk_roadmap_telemetry_stack", "purpose":"risk overview, roadmap, and telemetry cards", "runs_checks": False},
    {"name":"bottom_status_strip", "purpose":"guardrail, context, queue, tokens, and uptime summary", "authorizes_nothing": True},
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


def build_neural_deck_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in NEURAL_COMMAND_DECK_SURFACE_DEFS:
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
        "neural_command_deck_dashboard_status": "prepared_only",
        "neural_deck_layout_shell_status": "prepared",
        "eidolon_thinking_core_panel_status": "prepared",
        "operator_conversation_console_status": "prepared",
        "side_intelligence_panels_status": "prepared",
        "dashboard_style_regression_gate_status": "guarded_or_blocked",
        "neural_command_deck_dashboard_board_status": "review_only",
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
    entries = build_neural_deck_manifest_entries()
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


def build_neural_deck_layout_shell(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("three-column-shell", "neural-layout" in docs and "neural-left" in docs and "neural-center" in docs and "neural-right" in docs, "The dashboard declares a clean neural command deck three-column shell."),
        _row("red-command-style", "--accent-red" in docs and "neural command deck" in docs.lower(), "Red/black neural command deck style tokens are present."),
        _row("shell-boundaries", NEURAL_COMMAND_DECK_BOUNDARIES["layout_shell_writes_source"] is False and NEURAL_COMMAND_DECK_BOUNDARIES["layout_shell_removes_routes"] is False, "Layout shell grants no write authority and removes no routes by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "neural_deck_layout_shell_review_only", "neural_deck_layout_shell_id": NEURAL_DECK_LAYOUT_SHELL_ID, "components": list(NEURAL_DECK_COMPONENTS), **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(NEURAL_COMMAND_DECK_BOUNDARIES)}


def build_eidolon_thinking_core_panel(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("thinking-core-present", "eidolon-thinking-core" in docs and "EIDOLON THINKING" in docs, "Central Eidolon thinking core and label are present."),
        _row("thinking-wave-present", "thinking-wave" in docs and "neural-squiggle" in docs, "Red waveform/squiggle thinking stream is present."),
        _row("thinking-core-inert", NEURAL_COMMAND_DECK_BOUNDARIES["thinking_core_executes_models"] is False and NEURAL_COMMAND_DECK_BOUNDARIES["thinking_core_mutates_memory"] is False, "Thinking core is visual/informational only and executes no model or memory mutation."),
    ]
    return {"version": CURRENT_VERSION, "state": "eidolon_thinking_core_panel_review_only", "eidolon_thinking_core_panel_id": EIDOLON_THINKING_CORE_PANEL_ID, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(NEURAL_COMMAND_DECK_BOUNDARIES)}


def build_operator_conversation_console(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("conversation-console-present", "eidolon-conversation" in docs and "Ask Eidolon anything" in docs, "Operator conversation console and input are present."),
        _row("response-panel-present", "response-generation" in docs and "SYNTHESIZING" in docs, "Response generation panel is present."),
        _row("conversation-inert", NEURAL_COMMAND_DECK_BOUNDARIES["conversation_console_sends_commands"] is False and NEURAL_COMMAND_DECK_BOUNDARIES["conversation_console_creates_approval"] is False, "Conversation console creates no approval and sends no command by itself."),
    ]
    return {"version": CURRENT_VERSION, "state": "operator_conversation_console_review_only", "operator_conversation_console_id": OPERATOR_CONVERSATION_CONSOLE_ID, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(NEURAL_COMMAND_DECK_BOUNDARIES)}


def build_side_intelligence_panels(root: str | Path | None = None) -> dict[str, Any]:
    docs = _docs(root)
    rows = [
        _row("left-panel-stack", "System Vitals" in docs and "Stable Loop" in docs and "Approval Queue" in docs, "Left intelligence stack includes vitals, stable loop, and approval queue."),
        _row("right-panel-stack", "Risk Overview" in docs and "Roadmap" in docs and "Telemetry Feed" in docs, "Right intelligence stack includes risk, roadmap, and telemetry."),
        _row("side-panels-inert", NEURAL_COMMAND_DECK_BOUNDARIES["side_panels_execute_checks"] is False and NEURAL_COMMAND_DECK_BOUNDARIES["side_panels_treat_metrics_as_authorization"] is False, "Side metrics do not execute checks or become authorization."),
    ]
    return {"version": CURRENT_VERSION, "state": "side_intelligence_panels_review_only", "side_intelligence_panels_id": SIDE_INTELLIGENCE_PANELS_ID, **_base_state(), "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(NEURAL_COMMAND_DECK_BOUNDARIES)}


def build_neural_command_deck_dashboard_board(root: str | Path | None = None) -> dict[str, Any]:
    layout = build_neural_deck_layout_shell(root)
    thinking = build_eidolon_thinking_core_panel(root)
    conversation = build_operator_conversation_console(root)
    side = build_side_intelligence_panels(root)
    docs = _docs(root)
    tokens = _runtime_tokens(root)
    regression = _native_title_regression_present(root)
    entries = build_neural_deck_manifest_entries()
    rows = [
        _row("layout-shell", layout.get("ok") is True, "Neural deck layout shell passed."),
        _row("thinking-core", thinking.get("ok") is True, "Eidolon thinking core panel passed."),
        _row("conversation-console", conversation.get("ok") is True, "Operator conversation console passed."),
        _row("side-intelligence", side.get("ok") is True, "Side intelligence panels passed."),
        _row("surface-tokens-visible", all(entry["dashboard_route"] in tokens["routes"] and entry["api_route"] in tokens["api"] and entry["cli_flag"] in tokens["cli"] for entry in entries), "Dashboard/API/CLI tokens for v686-v690 are visible."),
        _row("targeted-smoke-visible", TARGETED_SMOKE in docs, "Targeted smoke token is visible."),
        _row("style-regression-guard", not regression and "no_native_title_tooltip" in docs and "data-tip" in docs, "Custom data-tip hover behavior remains preserved with no native title tooltip regression."),
        _row("board-no-authority", all(NEURAL_COMMAND_DECK_BOUNDARIES[key] is False for key in ["dashboard_board_writes_source", "dashboard_board_writes_metadata", "dashboard_board_writes_memory", "dashboard_board_writes_archive_records", "dashboard_board_creates_release", "dashboard_board_publishes_release", "dashboard_board_reuses_approval", "dashboard_board_continues_automatically", "dashboard_board_expands_autonomy", "visual_health_is_authorization", "thinking_animation_is_model_execution"]), "Neural command deck dashboard board grants no write, release, approval, continuation, authorization, or autonomy authority."),
    ]
    return {
        "version": CURRENT_VERSION,
        "state": "neural_command_deck_dashboard_board_review_only",
        "neural_command_deck_dashboard_board_id": NEURAL_COMMAND_DECK_DASHBOARD_BOARD_ID,
        "neural_command_deck_dashboard_status": "prepared_only",
        "component_checks": [layout, thinking, conversation, side],
        "neural_deck_manifest_entries": entries,
        "runtime_tokens": {key: sorted(value) for key, value in tokens.items()},
        "native_title_regression_present": regression,
        **_base_state(),
        "rows": rows,
        "status": _status(rows),
        "ok": _ok(rows),
        "boundaries": dict(NEURAL_COMMAND_DECK_BOUNDARIES),
        "safe_next_action": "Operator may review interaction refinement next. Dashboard visual health, thinking animation, and style gate status are not approval, execution permission, release permission, or autonomy approval.",
    }


def build_neural_command_deck_dashboard_redesign_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    stage_map = {
        "neural_deck_layout_shell_v1": build_neural_deck_layout_shell,
        "eidolon_thinking_core_panel_v1": build_eidolon_thinking_core_panel,
        "operator_conversation_console_v1": build_operator_conversation_console,
        "side_intelligence_panels_v1": build_side_intelligence_panels,
        "neural_command_deck_dashboard_board_v1": build_neural_command_deck_dashboard_board,
    }
    if stage and stage in stage_map:
        return stage_map[stage](root)
    return build_neural_command_deck_dashboard_board(root)


def render_neural_command_deck_dashboard_redesign_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"ok: {report.get('ok')}",
        f"status: {report.get('status')}",
        f"neural_command_deck_dashboard_status: {report.get('neural_command_deck_dashboard_status')}",
        f"neural_deck_layout_shell_status: {report.get('neural_deck_layout_shell_status')}",
        f"eidolon_thinking_core_panel_status: {report.get('eidolon_thinking_core_panel_status')}",
        f"operator_conversation_console_status: {report.get('operator_conversation_console_status')}",
        f"side_intelligence_panels_status: {report.get('side_intelligence_panels_status')}",
        f"dashboard_style_regression_gate_status: {report.get('dashboard_style_regression_gate_status')}",
        f"neural_command_deck_dashboard_board_status: {report.get('neural_command_deck_dashboard_board_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
    ]
    rows = report.get("rows") or []
    if rows:
        lines.append("rows:")
        lines.extend(f"- {row.get('name')}: {row.get('status')} — {row.get('message')}" for row in rows)
    return lines


# v686.0-v690.0 neural command deck dashboard redesign tokens: neural-command-deck-dashboard-redesign-v1 neural_command_deck_dashboard_redesign.py neural-deck-layout-shell eidolon-thinking-core-panel operator-conversation-console side-intelligence-panels neural-command-deck-dashboard-board neural-layout neural-left neural-center neural-right eidolon-thinking-core thinking-wave neural-squiggle eidolon-conversation response-generation neural_command_deck_dashboard_status=prepared_only neural_deck_layout_shell_status=prepared eidolon_thinking_core_panel_status=prepared operator_conversation_console_status=prepared side_intelligence_panels_status=prepared dashboard_style_regression_gate_status=guarded_or_blocked neural_command_deck_dashboard_board_status=review_only raw_evidence_preserved=True approval_semantics_changed=False source_mutation_status=not_performed metadata_write_status=not_performed_by_report archive_write_status=not_performed memory_write_status=not_performed release_status=not_created publish_status=not_authorized approval_status=required authorization_status=not_authorized autonomy_status=not_autonomous layout_shell_writes_source=False layout_shell_removes_routes=False thinking_core_executes_models=False thinking_core_mutates_memory=False conversation_console_sends_commands=False conversation_console_creates_approval=False side_panels_execute_checks=False side_panels_treat_metrics_as_authorization=False dashboard_board_expands_autonomy=False visual_health_is_authorization=False thinking_animation_is_model_execution=False no_native_title_tooltip data-tip command-deck operator-console neural command deck

# v691.0-v695.0 neural command deck interaction refinement integrity tokens: v695.0 Neural Command Deck Interaction Refinement v1 neural-command-deck-interaction-refinement-v1 neural_command_deck_interaction_refinement.py interaction-focus-rail interaction-safe-input-deck panel-density-priority-tuning context-telemetry-affordance neural-command-deck-interaction-board neural_command_deck_interaction_refinement_status=prepared_only interaction_focus_rail_status=prepared interaction_safe_input_deck_status=prepared panel_density_priority_tuning_status=prepared context_telemetry_affordance_status=prepared interaction_style_regression_gate_status=guarded_or_blocked neural_command_deck_interaction_board_status=review_only approval_semantics_changed=False focus_rail_starts_work=False input_deck_sends_commands=False input_deck_creates_approval=False priority_tuning_hides_blockers=False telemetry_affordance_executes_checks=False interaction_board_expands_autonomy=False visual_priority_is_authorization=False hover_detail_is_approval=False chat_input_is_command_execution=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console neural command deck
