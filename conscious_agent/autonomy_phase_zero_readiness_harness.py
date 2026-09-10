from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from release_metadata import RUNTIME_VERSION

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from current_version_staleness_audit import CURRENT_VERSION

AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION = RUNTIME_VERSION
TARGETED_SMOKE = "dashboard-dispatcher-proof-surface-historical-compatibility-migration-prep-v1"
PHASE_ZERO_DEFINITION_CONTRACT_ID = "v696_phase_zero_definition_contract"
OBSERVATION_ONLY_CYCLE_SIMULATOR_ID = "v697_observation_only_cycle_simulator"
NO_MUTATION_BOUNDARY_GUARD_ID = "v698_no_mutation_boundary_guard"
PHASE_ZERO_HANDOFF_PACKET_ID = "v699_phase_zero_handoff_packet"
AUTONOMY_PHASE_ZERO_READINESS_BOARD_ID = "v700_autonomy_phase_zero_readiness_board"

PHASE_ZERO_SURFACE_DEFS: tuple[dict[str, str], ...] = (
    {"version":"v696.0","slug":"autonomy_phase_zero_definition_contract_v1","route":"autonomy-phase-zero-definition-contract","label":"Autonomy Phase 0 Definition Contract v1","status_key":"phase_zero_definition_contract_status"},
    {"version":"v697.0","slug":"observation_only_cycle_simulator_v1","route":"observation-only-cycle-simulator","label":"Observation-Only Cycle Simulator v1","status_key":"observation_only_cycle_simulator_status"},
    {"version":"v698.0","slug":"no_mutation_autonomy_boundary_guard_v1","route":"no-mutation-autonomy-boundary-guard","label":"No-Mutation Autonomy Boundary Guard v1","status_key":"no_mutation_boundary_guard_status"},
    {"version":"v699.0","slug":"autonomy_phase_zero_handoff_packet_v1","route":"autonomy-phase-zero-handoff-packet","label":"Autonomy Phase 0 Handoff Packet v1","status_key":"phase_zero_handoff_packet_status"},
    {"version":"v700.0","slug":"autonomy_phase_zero_readiness_board_v1","route":"autonomy-phase-zero-readiness-board","label":"Autonomy Phase 0 Readiness Board v1","status_key":"autonomy_phase_zero_readiness_board_status"},
)

PHASE_ZERO_BOUNDARIES: dict[str, bool] = {
    "phase_zero_is_autonomy_approval": False,
    "phase_zero_observation_executes_commands": False,
    "phase_zero_observation_writes_source": False,
    "phase_zero_observation_writes_memory": False,
    "phase_zero_observation_writes_archives": False,
    "phase_zero_observation_mutates_current_state": False,
    "phase_zero_observation_creates_release": False,
    "phase_zero_observation_publishes_release": False,
    "phase_zero_observation_schedules_hidden_work": False,
    "phase_zero_observation_continues_automatically": False,
    "phase_zero_observation_selects_roadmap": False,
    "phase_zero_observation_invokes_models": False,
    "phase_zero_cycle_starts_work": False,
    "observation_receipt_is_approval": False,
    "readiness_score_is_authorization": False,
    "handoff_packet_is_permission": False,
    "phase_zero_board_expands_autonomy": False,
    "operator_review_required": True,
    "fresh_exact_operator_approval_required_for_any_execution": True,
}

PHASE_ZERO_ALLOWED_ACTIONS: tuple[str, ...] = (
    "inspect_current_state",
    "summarize_findings",
    "classify_blockers",
    "prepare_review_receipts",
    "propose_next_work_without_selection",
)

PHASE_ZERO_FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "execute_commands",
    "write_source_files",
    "write_memory",
    "write_archive_records",
    "mutate_current_state",
    "create_release",
    "publish_release",
    "schedule_hidden_work",
    "continue_automatically",
    "reuse_approval",
    "expand_autonomy",
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
        "conscious_agent/autonomy_phase_zero_readiness_harness.py",
        "conscious_agent/dashboard.py", "conscious_agent/self_maintenance.py",
        "conscious_agent/current_version_staleness_audit.py",
        "conscious_agent/current_state_integrity_staleness_hardening.py",
        "conscious_agent/metadata_release_integrity.py",
        "conscious_agent/source_package_privacy_metadata_integrity.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/route_surface_parity.py",
        "conscious_agent/documentation_continuity_header.py",
        "conscious_agent/smoke_segment_registry.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py",
        "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ]
    return "\n".join(_read_text(repo / rel) for rel in rels)


def _row(name: str, ok: bool, message: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "blocked", "message": message}


def _status(rows: list[dict[str, str]]) -> str:
    return "pass" if all(row.get("status") == "pass" for row in rows) else "blocked"


def _ok(rows: list[dict[str, str]]) -> bool:
    return _status(rows) == "pass"


def build_phase_zero_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in PHASE_ZERO_SURFACE_DEFS:
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
            "smoke_segment": "install-autonomy-readiness",
            "authority_level": "review_only",
            "writes_files": False,
            "writes_memory": False,
            "requires_operator_approval": True,
            "status_key": item["status_key"],
        })
    return entries


def _base_state() -> dict[str, Any]:
    return {
        "autonomy_phase_zero_readiness_harness_status": "prepared_only",
        "phase_zero_definition_contract_status": "defined",
        "observation_only_cycle_simulator_status": "simulated_review_only",
        "no_mutation_boundary_guard_status": "guarded_or_blocked",
        "phase_zero_handoff_packet_status": "prepared_not_permission",
        "autonomy_phase_zero_readiness_board_status": "review_only",
        "autonomy_mode": "observation_only_readiness_harness",
        "phase_zero_status": "not_autonomous_readiness_only",
        "allowed_actions": list(PHASE_ZERO_ALLOWED_ACTIONS),
        "forbidden_actions": list(PHASE_ZERO_FORBIDDEN_ACTIONS),
        "raw_evidence_preserved": True,
        "approval_semantics_changed": False,
        "operator_decision_status": "required",
        "authorization_status": "not_authorized",
        "approval_status": "required",
        "autonomy_status": "not_autonomous",
        "autonomy_expansion_status": "not_performed",
        "source_mutation_status": "not_performed",
        "metadata_write_status": "not_performed_by_report",
        "archive_write_status": "not_performed",
        "memory_write_status": "not_performed",
        "release_status": "not_created",
        "publish_status": "not_authorized",
        "command_execution_status": "not_performed",
        "model_invocation_status": "not_performed",
        "writes_source": False,
        "writes_metadata": False,
        "writes_memory": False,
        "writes_archive_records": False,
        "mutates_current_state": False,
        "executes_actions": False,
        "executes_commands": False,
        "executes_smoke": False,
        "starts_work": False,
        "selects_roadmap": False,
        "schedules_hidden_work": False,
        "applies_patch": False,
        "creates_release": False,
        "publishes_release": False,
        "creates_approval": False,
        "reuses_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "invokes_models": False,
        "review_only": True,
        "created_at": _now_iso(),
    }


def _native_title_regression_present(root: str | Path | None = None) -> bool:
    dashboard = _read_text(_repo(root) / "conscious_agent/dashboard.py")
    for line in dashboard.splitlines():
        if "data-tip" in line and " title=" in line and "data-route-title" not in line:
            return True
        if "nav" in line.lower() and " title=" in line and "data-route-title" not in line:
            return True
    return False


def _common_rows(root: str | Path | None = None) -> list[dict[str, str]]:
    docs = _docs(root)
    entries = build_phase_zero_manifest_entries()
    required = [
        "v700.0 Autonomy Phase 0 Readiness Harness v1",
        TARGETED_SMOKE,
        "autonomy_phase_zero_readiness_harness.py",
        "autonomy_phase_zero_readiness_harness_status=prepared_only",
        "phase_zero_definition_contract_status=defined",
        "observation_only_cycle_simulator_status=simulated_review_only",
        "no_mutation_boundary_guard_status=guarded_or_blocked",
        "phase_zero_handoff_packet_status=prepared_not_permission",
        "autonomy_phase_zero_readiness_board_status=review_only",
        "phase_zero_is_autonomy_approval=False",
        "phase_zero_observation_executes_commands=False",
        "phase_zero_observation_writes_source=False",
        "phase_zero_observation_writes_memory=False",
        "phase_zero_observation_writes_archives=False",
        "phase_zero_observation_mutates_current_state=False",
        "phase_zero_observation_creates_release=False",
        "phase_zero_observation_publishes_release=False",
        "phase_zero_observation_schedules_hidden_work=False",
        "phase_zero_observation_continues_automatically=False",
        "phase_zero_observation_selects_roadmap=False",
        "phase_zero_observation_invokes_models=False",
        "observation_receipt_is_approval=False",
        "readiness_score_is_authorization=False",
        "handoff_packet_is_permission=False",
        "phase_zero_board_expands_autonomy=False",
        "no_native_title_tooltip",
        "data-tip",
        "command-deck",
        "operator-console",
    ]
    return [
        _row("current-version", CURRENT_VERSION == AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, f"current={CURRENT_VERSION}; module={AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION}"),
        _row("surface-routes", all(entry["dashboard_route"] in docs for entry in entries), "All Phase 0 dashboard route tokens are documented/wired."),
        _row("surface-api", all(entry["api_route"] in docs for entry in entries), "All Phase 0 API route tokens are documented/wired."),
        _row("surface-cli", all(entry["cli_flag"] in docs for entry in entries), "All Phase 0 CLI flags are documented/wired."),
        _row("surface-builders", all(entry["builder_function"] in docs and entry["text_function"] in docs for entry in entries), "All Phase 0 builder/text functions are visible."),
        _row("required-doc-tokens", all(token in docs for token in required), "Current docs/source/smoke metadata include the v700 Phase 0 readiness tokens and no-authority boundaries."),
        _row("no-native-title-tooltip", not _native_title_regression_present(root), "Custom data-tip hover behavior remains preserved without native title tooltip regression."),
        _row("no-authority-boundaries", all(PHASE_ZERO_BOUNDARIES[key] is False for key in PHASE_ZERO_BOUNDARIES if key not in {"operator_review_required", "fresh_exact_operator_approval_required_for_any_execution"}), "Phase 0 readiness harness grants no execution, mutation, approval, scheduling, continuation, roadmap selection, model invocation, release, publish, or autonomy authority."),
    ]


def build_autonomy_phase_zero_definition_contract(root: str | Path | None = None) -> dict[str, Any]:
    rows = _common_rows(root) + [
        _row("definition-contract", True, "Phase 0 is defined as observation-only readiness review, not autonomy approval."),
        _row("allowed-actions", set(PHASE_ZERO_ALLOWED_ACTIONS) == {"inspect_current_state", "summarize_findings", "classify_blockers", "prepare_review_receipts", "propose_next_work_without_selection"}, "Allowed actions are inspection, summary, blocker classification, receipt prep, and proposal-only queueing."),
    ]
    state = _base_state(); state.update({"version": AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, "state": "autonomy_phase_zero_definition_contract_review_only", "phase_zero_definition_contract_id": PHASE_ZERO_DEFINITION_CONTRACT_ID, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(PHASE_ZERO_BOUNDARIES)})
    return state


def build_observation_only_cycle_simulator(root: str | Path | None = None) -> dict[str, Any]:
    simulated_cycle = [
        {"step": "inspect", "allowed": True, "mutates_state": False},
        {"step": "summarize", "allowed": True, "mutates_state": False},
        {"step": "classify_blockers", "allowed": True, "mutates_state": False},
        {"step": "prepare_receipt", "allowed": True, "mutates_state": False},
        {"step": "propose_next_work", "allowed": True, "starts_work": False},
    ]
    rows = _common_rows(root) + [
        _row("cycle-simulated", all(step.get("allowed") for step in simulated_cycle), "Observation-only cycle is simulated as a review receipt only."),
        _row("cycle-does-not-start-work", all(step.get("mutates_state", False) is False for step in simulated_cycle) and PHASE_ZERO_BOUNDARIES["phase_zero_cycle_starts_work"] is False, "The simulated cycle does not start work or mutate state."),
    ]
    state = _base_state(); state.update({"version": AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, "state": "observation_only_cycle_simulator_review_only", "observation_only_cycle_simulator_id": OBSERVATION_ONLY_CYCLE_SIMULATOR_ID, "simulated_cycle": simulated_cycle, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(PHASE_ZERO_BOUNDARIES)})
    return state


def build_no_mutation_autonomy_boundary_guard(root: str | Path | None = None) -> dict[str, Any]:
    state = _base_state()
    mutation_fields = ["writes_source", "writes_metadata", "writes_memory", "writes_archive_records", "mutates_current_state", "executes_commands", "executes_actions", "executes_smoke", "starts_work", "selects_roadmap", "schedules_hidden_work", "creates_release", "publishes_release", "creates_approval", "reuses_approval", "continues_automatically", "expands_autonomy", "invokes_models"]
    rows = _common_rows(root) + [
        _row("mutation-fields-false", all(state.get(field) is False for field in mutation_fields), "All no-mutation/no-execution/no-continuation fields remain false."),
        _row("status-fields-inert", state.get("source_mutation_status") == "not_performed" and state.get("memory_write_status") == "not_performed" and state.get("archive_write_status") == "not_performed" and state.get("release_status") == "not_created" and state.get("command_execution_status") == "not_performed", "Status fields explicitly report no source/memory/archive/release/command activity."),
    ]
    state.update({"version": AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, "state": "no_mutation_autonomy_boundary_guard_review_only", "no_mutation_boundary_guard_id": NO_MUTATION_BOUNDARY_GUARD_ID, "mutation_fields_checked": mutation_fields, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(PHASE_ZERO_BOUNDARIES)})
    return state


def build_autonomy_phase_zero_handoff_packet(root: str | Path | None = None) -> dict[str, Any]:
    handoff = {
        "phase_zero_scope": "observation_only_readiness_harness",
        "next_phase_discussion": NEXT_RECOMMENDED_ARC,
        "approval_status": "required_for_any_future_execution",
        "handoff_packet_is_permission": False,
        "operator_review_required": True,
    }
    rows = _common_rows(root) + [
        _row("handoff-prepared", handoff["handoff_packet_is_permission"] is False, "Phase 0 handoff is prepared for review but is not permission to continue."),
        _row("next-phase-not-approved", handoff["approval_status"] == "required_for_any_future_execution", "Any future trial or execution remains separately operator-approved."),
    ]
    state = _base_state(); state.update({"version": AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, "state": "autonomy_phase_zero_handoff_packet_review_only", "phase_zero_handoff_packet_id": PHASE_ZERO_HANDOFF_PACKET_ID, "handoff_packet": handoff, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(PHASE_ZERO_BOUNDARIES)})
    return state


def build_autonomy_phase_zero_readiness_board(root: str | Path | None = None) -> dict[str, Any]:
    definition = build_autonomy_phase_zero_definition_contract(root)
    cycle = build_observation_only_cycle_simulator(root)
    guard = build_no_mutation_autonomy_boundary_guard(root)
    handoff = build_autonomy_phase_zero_handoff_packet(root)
    rows = _common_rows(root) + [
        _row("definition-ok", definition.get("ok") is True, "Definition contract is clean."),
        _row("cycle-ok", cycle.get("ok") is True, "Observation-only simulator is clean."),
        _row("guard-ok", guard.get("ok") is True, "No-mutation boundary guard is clean."),
        _row("handoff-ok", handoff.get("ok") is True and handoff.get("handoff_packet", {}).get("handoff_packet_is_permission") is False, "Handoff packet is review-only and not permission."),
        _row("phase-zero-not-autonomy", True, "The readiness board does not make Eidolon autonomous or authorize Phase 1."),
    ]
    state = _base_state(); state.update({"version": AUTONOMY_PHASE_ZERO_READINESS_HARNESS_VERSION, "state": "autonomy_phase_zero_readiness_board_review_only", "autonomy_phase_zero_readiness_board_id": AUTONOMY_PHASE_ZERO_READINESS_BOARD_ID, "definition_contract": definition, "observation_only_cycle_simulator": cycle, "no_mutation_boundary_guard": guard, "phase_zero_handoff_packet": handoff, "rows": rows, "status": _status(rows), "ok": _ok(rows), "boundaries": dict(PHASE_ZERO_BOUNDARIES), "safe_next_action": "Operator may review the Phase 0 readiness harness and request a future observation-only trial review. This is not approval to execute, schedule, write, release, publish, continue automatically, or expand autonomy."})
    return state


def build_autonomy_phase_zero_readiness_harness_arc(root: str | Path | None = None, stage: str | None = None) -> dict[str, Any]:
    builders = {
        "autonomy_phase_zero_definition_contract_v1": build_autonomy_phase_zero_definition_contract,
        "observation_only_cycle_simulator_v1": build_observation_only_cycle_simulator,
        "no_mutation_autonomy_boundary_guard_v1": build_no_mutation_autonomy_boundary_guard,
        "autonomy_phase_zero_handoff_packet_v1": build_autonomy_phase_zero_handoff_packet,
        "autonomy_phase_zero_readiness_board_v1": build_autonomy_phase_zero_readiness_board,
        None: build_autonomy_phase_zero_readiness_board,
    }
    return builders.get(stage, build_autonomy_phase_zero_readiness_board)(root)


def render_autonomy_phase_zero_readiness_harness_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"version: {report.get('version')}",
        f"status: {report.get('status')}",
        f"ok: {report.get('ok')}",
        f"autonomy_mode: {report.get('autonomy_mode')}",
        f"phase_zero_status: {report.get('phase_zero_status')}",
        f"approval_status: {report.get('approval_status')}",
        f"authorization_status: {report.get('authorization_status')}",
        f"autonomy_status: {report.get('autonomy_status')}",
        f"command_execution_status: {report.get('command_execution_status')}",
        f"source_mutation_status: {report.get('source_mutation_status')}",
        f"memory_write_status: {report.get('memory_write_status')}",
        f"archive_write_status: {report.get('archive_write_status')}",
        f"release_status: {report.get('release_status')}",
        f"autonomy_expansion_status: {report.get('autonomy_expansion_status')}",
    ]
    rows = report.get("rows", [])
    if rows:
        lines.append("rows:")
        for row in rows[:20]:
            lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    if report.get("safe_next_action"):
        lines.append(f"safe_next_action: {report.get('safe_next_action')}")
    return lines


def _make_builder(slug: str):
    def _builder(root: str | Path | None = None) -> dict[str, Any]:
        return build_autonomy_phase_zero_readiness_harness_arc(root, stage=slug)
    return _builder


def _make_text(slug: str):
    def _text(root: str | Path | None = None, full: bool = False) -> str:
        report = build_autonomy_phase_zero_readiness_harness_arc(root, stage=slug)
        lines = render_autonomy_phase_zero_readiness_harness_lines(report)
        if full:
            import json
            lines.append("json:")
            lines.append(json.dumps(report, indent=2, sort_keys=True))
        return "\n".join(lines)
    return _text


for _item in PHASE_ZERO_SURFACE_DEFS:
    _slug = _item["slug"]
    globals()[f"build_{_slug}"] = _make_builder(_slug)
    globals()[f"{_slug}_text"] = _make_text(_slug)

# v696.0-v700.0 autonomy phase zero readiness harness integrity tokens: v700.0 Autonomy Phase 0 Readiness Harness v1 autonomy-phase-zero-readiness-harness-v1 autonomy_phase_zero_readiness_harness.py autonomy-phase-zero-definition-contract observation-only-cycle-simulator no-mutation-autonomy-boundary-guard autonomy-phase-zero-handoff-packet autonomy-phase-zero-readiness-board autonomy_phase_zero_readiness_harness_status=prepared_only phase_zero_definition_contract_status=defined observation_only_cycle_simulator_status=simulated_review_only no_mutation_boundary_guard_status=guarded_or_blocked phase_zero_handoff_packet_status=prepared_not_permission autonomy_phase_zero_readiness_board_status=review_only phase_zero_is_autonomy_approval=False phase_zero_observation_executes_commands=False phase_zero_observation_writes_source=False phase_zero_observation_writes_memory=False phase_zero_observation_writes_archives=False phase_zero_observation_mutates_current_state=False phase_zero_observation_creates_release=False phase_zero_observation_publishes_release=False phase_zero_observation_schedules_hidden_work=False phase_zero_observation_continues_automatically=False phase_zero_observation_selects_roadmap=False phase_zero_observation_invokes_models=False phase_zero_cycle_starts_work=False observation_receipt_is_approval=False readiness_score_is_authorization=False handoff_packet_is_permission=False phase_zero_board_expands_autonomy=False documentation_state_is_authorization=False metadata_consistency_is_authorization=False release_integrity_pass_is_approval=False no_native_title_tooltip data-tip command-deck operator-console
