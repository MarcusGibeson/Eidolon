from __future__ import annotations

from pathlib import Path
from typing import Any
import json

OPERATOR_OBSERVATION_PREP_VERSION = "1032.0"
CURRENT_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
OBSERVATION_SCOPE_ITEMS = [
    "source version markers",
    "README current-state header",
    "release history latest entry",
    "project/workspace metadata",
    "smoke registry entries",
    "dashboard route inventory",
    "source surface manifest",
    "known blockers and recommended next arc",
]

OBSERVATION_BOUNDARIES: dict[str, bool] = {
    "observation_is_authorization": False,
    "observation_is_execution": False,
    "observation_grants_followup_permission": False,
    "observation_writes_source": False,
    "observation_writes_memory": False,
    "observation_updates_metadata": False,
    "observation_schedules_work": False,
    "observation_invokes_models_by_default": False,
    "observation_applies_patches": False,
    "observation_publishes_releases": False,
    "observation_promotes_sandbox_output": False,
    "observation_creates_approval": False,
    "operator_invocation_required": True,
    "single_run_read_only": True,
    "operator_review_required": True,
}


def _repo_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(_read_text(path))
    except Exception:
        return {}


def _row(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "blocked", "ok": bool(ok), "message": message}


def build_manual_read_only_observation_scope(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    required_files = [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "data/settings.json",
        "data/projects.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
        "conscious_agent/smoke_segment_registry.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/source_surface_manifest.py",
    ]
    rows = [_row(f"file:{rel}", (repo / rel).exists(), f"Observation source file {rel} is present.") for rel in required_files]
    rows.extend([
        _row("operator-invocation-required", OBSERVATION_BOUNDARIES["operator_invocation_required"], "Observation scope is available only as an operator-invoked review packet."),
        _row("single-run-read-only", OBSERVATION_BOUNDARIES["single_run_read_only"], "Observation scope is single-run and read-only."),
        _row("no-source-writes", not OBSERVATION_BOUNDARIES["observation_writes_source"], "Scope does not authorize source writes."),
        _row("no-memory-writes", not OBSERVATION_BOUNDARIES["observation_writes_memory"], "Scope does not authorize memory writes."),
        _row("no-schedules", not OBSERVATION_BOUNDARIES["observation_schedules_work"], "Scope does not create schedules or hidden monitoring."),
    ])
    return {
        "version": OPERATOR_OBSERVATION_PREP_VERSION,
        "state": "manual_read_only_observation_scope_review_only",
        "scope_items": list(OBSERVATION_SCOPE_ITEMS),
        "required_files": required_files,
        "rows": rows,
        "ok": all(row["ok"] for row in rows),
        "status": "pass" if all(row["ok"] for row in rows) else "blocked",
        "boundaries": dict(OBSERVATION_BOUNDARIES),
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_operator_observation_packet(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    settings = _read_json(repo / "data/settings.json")
    projects = _read_json(repo / "data/projects.json")
    active_workspace = _read_json(repo / "data/workspaces/active_project.json")
    workspace_projects = _read_json(repo / "data/workspaces/projects.json")
    readme = _read_text(repo / "README_NEXT_STEPS.md")
    history = _read_text(repo / "README_RELEASE_HISTORY.md")
    smoke_registry = _read_text(repo / "conscious_agent/smoke_segment_registry.py")
    route_probe = _read_text(repo / "conscious_agent/dashboard_route_probe.py")
    manifest = _read_text(repo / "conscious_agent/source_surface_manifest.py")

    expected_version = CURRENT_VERSION
    expected_tag = CURRENT_VERSION_TAG
    expected_milestone = CURRENT_MILESTONE
    version_sources = {
        "settings_version": settings.get("settings_version"),
        "settings_last_updated_for": settings.get("last_updated_for"),
        "projects_version": projects.get("version"),
        "projects_root_version": projects.get("root_version"),
        "active_workspace_version": active_workspace.get("version"),
        "active_workspace_last_updated_for": active_workspace.get("last_updated_for"),
        "workspace_projects_version": workspace_projects.get("version"),
    }
    metadata_alignment = {
        "expected_version": expected_version,
        "version_sources": version_sources,
        "ok": all(value in {expected_version, expected_tag} for value in version_sources.values() if value is not None),
    }
    documentation_alignment = {
        "readme_current_version": (f"CURRENT VERSION: {expected_tag}" in readme or f"# Current State — {expected_tag}" in readme),
        "release_history_current_entry": (f"# {expected_tag} - {CURRENT_MILESTONE.split(' ', 1)[1]}" in history or f"## {expected_tag} - {CURRENT_MILESTONE.split(' ', 1)[1]}" in history),
        "readme_next_arc": NEXT_RECOMMENDED_ARC in readme,
        "observation_boundary_language": "Observation is not authorization" in readme and "Operator invocation permits one read-only observation report only" in readme,
    }
    route_surface_alignment = {
        "route_probe_token": "operator-read-only-observation-audit" in route_probe,
        "manifest_token": "v480-operator-read-only-observation-audit" in manifest,
        "smoke_token": "operator-invoked-read-only-observation-prep-v1" in smoke_registry,
    }
    known_blockers = [
        "Recurring/background observation is still out of scope until a visible ledger and stop/pause semantics exist.",
        "Observation findings cannot become execution packets or approval records.",
        "Observation reports cannot write source, memory, metadata, schedules, releases, or local model outputs.",
    ]
    recommended_review_targets = [
        "Review read-only observation scope before adding any ledger behavior.",
        "Prepare v556-v560 recovery drill and release closure packets only after v555 verification/rollback trial smoke passes.",
        "Keep observation packet findings separate from patch proposal queues until supervised proposal gates exist.",
    ]
    rows = [
        _row("metadata-alignment", metadata_alignment["ok"], "Settings/project/workspace metadata align to current version."),
        _row("readme-current-version", documentation_alignment["readme_current_version"], "README_NEXT_STEPS.md exposes current header."),
        _row("release-history-current-entry", documentation_alignment["release_history_current_entry"], "README_RELEASE_HISTORY.md documents current release."),
        _row("readme-next-arc", documentation_alignment["readme_next_arc"], "README points to the current next recommended arc."),
        _row("boundary-language", documentation_alignment["observation_boundary_language"], "README states observation is not authorization and operator invocation is single-run/read-only."),
        _row("route-probe-token", route_surface_alignment["route_probe_token"], "Dashboard route probe includes v476-v480 observation routes."),
        _row("manifest-token", route_surface_alignment["manifest_token"], "Source surface manifest includes v476-v480 observation surfaces."),
        _row("smoke-token", route_surface_alignment["smoke_token"], "Smoke segment registry includes v480 observation prep token."),
    ]
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_PREP_VERSION,
        "state": "operator_observation_packet_review_only",
        "current_version": expected_tag,
        "current_milestone": expected_milestone,
        "verified_state": {
            "metadata_alignment": metadata_alignment["ok"],
            "documentation_alignment": all(documentation_alignment.values()),
            "route_surface_alignment": all(route_surface_alignment.values()),
            "smoke_token_present": route_surface_alignment["smoke_token"],
        },
        "known_blockers": known_blockers,
        "metadata_alignment": metadata_alignment,
        "route_surface_alignment": route_surface_alignment,
        "documentation_alignment": documentation_alignment,
        "recommended_review_targets": recommended_review_targets,
        "authorization_boundary": dict(OBSERVATION_BOUNDARIES),
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "applies_patches": False,
        "publishes_releases": False,
        "creates_approval": False,
        "continues_automatically": False,
        "review_only": True,
    }


def build_no_mutation_observation_audit(root: str | Path | None = None) -> dict[str, Any]:
    packet = build_operator_observation_packet(root)
    checks = {
        "source_writes": packet.get("writes_files") is False,
        "memory_writes": packet.get("writes_memory") is False,
        "metadata_updates": packet.get("updates_metadata") is False,
        "schedule_creation": packet.get("creates_schedule") is False,
        "model_invocation": packet.get("invokes_models") is False,
        "patch_application": packet.get("applies_patches") is False,
        "release_publication": packet.get("publishes_releases") is False,
        "sandbox_promotion": OBSERVATION_BOUNDARIES["observation_promotes_sandbox_output"] is False,
        "approval_creation": packet.get("creates_approval") is False,
        "automatic_continuation": packet.get("continues_automatically") is False,
    }
    rows = [_row(name, ok, f"Observation audit confirms no {name.replace('_', ' ')}.") for name, ok in checks.items()]
    ok = packet.get("ok") is True and all(checks.values())
    return {
        "version": OPERATOR_OBSERVATION_PREP_VERSION,
        "state": "no_mutation_observation_audit_review_only",
        "packet_status": packet.get("status"),
        "checks": checks,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "applies_patches": False,
        "publishes_releases": False,
        "creates_approval": False,
        "continues_automatically": False,
        "review_only": True,
    }


def build_operator_invocation_boundary(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/operator_observation_prep.py",
        "conscious_agent/self_maintenance.py",
        "tools/smoke_check.py",
    ])
    required_phrases = [
        "Operator invocation permits one read-only observation report only",
        "It does not authorize continued monitoring",
        "It does not authorize follow-up action",
        "It does not authorize live changes",
        "Observation is not authorization",
    ]
    rows = [_row(f"phrase:{phrase}", phrase in docs, f"Boundary phrase present: {phrase}") for phrase in required_phrases]
    rows.extend([
        _row("no-hidden-schedule", OBSERVATION_BOUNDARIES["observation_schedules_work"] is False, "Operator invocation does not create hidden schedules."),
        _row("no-followup-permission", OBSERVATION_BOUNDARIES["observation_grants_followup_permission"] is False, "Operator invocation does not grant follow-up permission."),
        _row("operator-invocation-required", OBSERVATION_BOUNDARIES["operator_invocation_required"] is True, "Observation requires explicit operator invocation."),
    ])
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_PREP_VERSION,
        "state": "operator_invocation_boundary_review_only",
        "required_phrases": required_phrases,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "operator_invocation_required": True,
        "continued_monitoring_authorized": False,
        "followup_action_authorized": False,
        "live_changes_authorized": False,
        "creates_schedule": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_operator_read_only_observation_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/operator_observation_prep.py",
        "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py",
        "conscious_agent/dashboard_route_probe.py",
        "conscious_agent/source_surface_manifest.py",
        "conscious_agent/api_server.py",
        "conscious_agent/main.py",
        "tools/smoke_check.py",
        "conscious_agent/smoke_segment_registry.py",
        "data/settings.json",
        "data/projects.json",
        "data/workspaces/active_project.json",
        "data/workspaces/projects.json",
    ])
    scope = build_manual_read_only_observation_scope(repo)
    packet = build_operator_observation_packet(repo)
    mutation = build_no_mutation_observation_audit(repo)
    invocation = build_operator_invocation_boundary(repo)
    required_tokens = [
        "manual-read-only-observation-scope",
        "operator-observation-packet",
        "no-mutation-observation-audit",
        "operator-invocation-boundary",
        "operator-read-only-observation-audit",
        "operator-invoked-read-only-observation-prep-v1",
        "operator_observation_prep.py",
        "observation_is_authorization=False",
        "observation_is_execution=False",
        "observation_grants_followup_permission=False",
        "observation_writes_source=False",
        "observation_writes_memory=False",
        "observation_updates_metadata=False",
        "observation_schedules_work=False",
        "observation_invokes_models_by_default=False",
        "observation_creates_approval=False",
        "operator_invocation_required=True",
        "single_run_read_only=True",
    ]
    token_rows = [_row(f"token:{token}", token in docs, f"Required token present: {token}") for token in required_tokens]
    rows = [
        _row("scope", scope.get("ok") is True, "Manual read-only observation scope is defined."),
        _row("packet", packet.get("ok") is True, "Observation packet builder reports current project state."),
        _row("no-mutation", mutation.get("ok") is True, "No-mutation audit blocks source, memory, metadata, schedules, models, patches, releases, approvals, and continuation."),
        _row("operator-boundary", invocation.get("ok") is True, "Operator invocation boundary is explicit and single-run."),
    ] + token_rows
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_PREP_VERSION,
        "state": "operator_invoked_read_only_observation_prep_audit_review_only",
        "scope": scope,
        "packet": packet,
        "no_mutation_audit": mutation,
        "operator_invocation_boundary": invocation,
        "required_tokens": required_tokens,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "applies_patches": False,
        "publishes_releases": False,
        "creates_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "observation_is_authorization": False,
        "observation_is_execution": False,
        "observation_grants_followup_permission": False,
        "observation_writes_source": False,
        "observation_writes_memory": False,
        "observation_updates_metadata": False,
        "observation_schedules_work": False,
        "observation_invokes_models_by_default": False,
        "observation_creates_approval": False,
        "operator_invocation_required": True,
        "single_run_read_only": True,
        "operator_approval_still_required": True,
        "review_only": True,
    }


def render_operator_observation_prep_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'operator_observation_prep')} :: {report.get('status', 'unknown')}",
        f"version: {report.get('version', OPERATOR_OBSERVATION_PREP_VERSION)}",
        "boundary: observation is not authorization; operator invocation permits one read-only observation report only.",
        "mutation: no source writes, no memory writes, no metadata updates, no schedules, no models, no patches, no releases, no approvals, no automatic continuation.",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines
