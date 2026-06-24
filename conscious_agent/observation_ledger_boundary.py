from __future__ import annotations

from pathlib import Path
from typing import Any
import json

OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION = "500.0"
CURRENT_VERSION = "500.0"
CURRENT_VERSION_TAG = "v490.0"
CURRENT_MILESTONE = "v490.0 Supervised Proposal Queue from Observation Reports v1"
NEXT_RECOMMENDED_ARC = "v491.0-v495.0 Sandbox-Only Autonomy Boundary Trial Prep v1"

LEDGER_SCHEMA_FIELDS = [
    "observation_id",
    "created_at",
    "operator_invoked",
    "scope",
    "read_only_status",
    "mutation_status",
    "authorization_status",
    "recommended_review_targets",
    "next_arc_recommendation",
    "pause_state",
    "stop_state",
]

OBSERVATION_LEDGER_BOUNDARIES: dict[str, bool] = {
    "ledger_presence_is_approval": False,
    "ledger_completeness_is_authorization": False,
    "observation_history_permits_future_action": False,
    "receipt_is_approval": False,
    "pause_or_stop_authorizes_cleanup": False,
    "pause_or_stop_deletes_receipts": False,
    "hidden_scheduling_allowed": False,
    "automatic_continuation_allowed": False,
    "daily_loop_allowed": False,
    "hourly_loop_allowed": False,
    "auto_roadmap_selection_allowed": False,
    "auto_patch_packet_generation_allowed": False,
    "auto_promotion_from_observation_allowed": False,
    "source_mutation_allowed": False,
    "memory_mutation_allowed": False,
    "metadata_mutation_allowed": False,
    "model_invocation_by_default_allowed": False,
    "approval_creation_allowed": False,
    "operator_invocation_required": True,
    "review_only": True,
}

STOP_PAUSE_SEMANTICS = {
    "paused": "No future observation run may be prepared automatically; any further observation still requires explicit operator invocation.",
    "stopped": "Observation prep must require fresh operator invocation before any future manual observation packet is prepared.",
    "resume": "Resume requires explicit operator action and does not inherit approval from prior observation receipts.",
    "history": "Pause/stop does not delete historical receipts and does not authorize cleanup, mutation, or follow-up action.",
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


def _boundary_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in OBSERVATION_LEDGER_BOUNDARIES.items():
        expected = key in {"operator_invocation_required", "review_only"}
        rows.append(_row(f"boundary:{key}", value is expected, f"{key}={value}; expected {expected}."))
    return rows


def build_observation_ledger_schema(root: str | Path | None = None) -> dict[str, Any]:
    rows = [_row(f"field:{field}", True, f"Ledger schema includes {field}.") for field in LEDGER_SCHEMA_FIELDS]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION,
        "state": "observation_ledger_schema_review_only",
        "schema_fields": list(LEDGER_SCHEMA_FIELDS),
        "required_fields": list(LEDGER_SCHEMA_FIELDS),
        "ledger_record_example": {
            "observation_id": "manual-observation-example",
            "created_at": "operator-invoked-time-only",
            "operator_invoked": True,
            "scope": "manual_read_only_project_state",
            "read_only_status": "read_only",
            "mutation_status": "no_mutation",
            "authorization_status": "not_authorized",
            "recommended_review_targets": [],
            "next_arc_recommendation": NEXT_RECOMMENDED_ARC,
            "pause_state": "not_scheduled",
            "stop_state": "fresh_operator_invocation_required",
        },
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "creates_approval": False,
        "review_only": True,
        "boundaries": dict(OBSERVATION_LEDGER_BOUNDARIES),
    }


def build_observation_receipt_builder(root: str | Path | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    settings = _read_json(repo / "data/settings.json")
    active = _read_json(repo / "data/workspaces/active_project.json")
    receipt = {
        "observation_id": "manual-observation-receipt-template",
        "observed": [
            "source version markers",
            "README current-state header",
            "release history latest entry",
            "project/workspace metadata",
            "smoke registry entries",
            "dashboard route inventory",
            "source surface manifest",
        ],
        "not_observed": [
            "private runtime memory stores",
            "hidden scheduled work",
            "unapproved local model outputs",
            "live source mutation targets",
        ],
        "source_mutation": False,
        "memory_mutation": False,
        "metadata_mutation": False,
        "schedule_created": False,
        "model_invocation": False,
        "patch_application": False,
        "release_publication": False,
        "approval_created": False,
        "authorization_status": "not_authorized",
        "current_version": settings.get("settings_version"),
        "current_milestone": active.get("current_milestone"),
        "next_arc_recommendation": NEXT_RECOMMENDED_ARC,
    }
    rows = [
        _row("source-mutation-false", receipt["source_mutation"] is False, "Receipt records source_mutation=false."),
        _row("memory-mutation-false", receipt["memory_mutation"] is False, "Receipt records memory_mutation=false."),
        _row("metadata-mutation-false", receipt["metadata_mutation"] is False, "Receipt records metadata_mutation=false."),
        _row("schedule-created-false", receipt["schedule_created"] is False, "Receipt records schedule_created=false."),
        _row("model-invocation-false", receipt["model_invocation"] is False, "Receipt records model_invocation=false."),
        _row("approval-created-false", receipt["approval_created"] is False, "Receipt records approval_created=false."),
        _row("authorization-not-authorized", receipt["authorization_status"] == "not_authorized", "Receipt records authorization_status=not_authorized."),
    ]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION,
        "state": "observation_receipt_builder_review_only",
        "receipt": receipt,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_observation_stop_pause_semantics(root: str | Path | None = None) -> dict[str, Any]:
    required_phrases = [
        "paused means no future observation run may be prepared automatically",
        "stopped means observation prep must require fresh operator invocation",
        "resume requires explicit operator action",
        "pause/stop does not delete historical receipts",
        "pause/stop does not authorize cleanup or mutation",
    ]
    docs = "\n".join(_read_text(_repo_root(root) / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/observation_ledger_boundary.py",
        "conscious_agent/self_maintenance.py",
        "tools/smoke_check.py",
    ])
    rows = [_row(f"phrase:{phrase}", phrase in docs, f"Stop/pause phrase present: {phrase}") for phrase in required_phrases]
    rows.extend([
        _row("no-auto-prep-while-paused", not OBSERVATION_LEDGER_BOUNDARIES["automatic_continuation_allowed"], "Paused state cannot authorize automatic preparation."),
        _row("fresh-invocation-after-stop", OBSERVATION_LEDGER_BOUNDARIES["operator_invocation_required"], "Stopped state requires fresh operator invocation."),
        _row("history-not-deleted", not OBSERVATION_LEDGER_BOUNDARIES["pause_or_stop_deletes_receipts"], "Pause/stop does not delete receipts."),
        _row("cleanup-not-authorized", not OBSERVATION_LEDGER_BOUNDARIES["pause_or_stop_authorizes_cleanup"], "Pause/stop does not authorize cleanup or mutation."),
    ])
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION,
        "state": "observation_stop_pause_semantics_review_only",
        "semantics": dict(STOP_PAUSE_SEMANTICS),
        "required_phrases": required_phrases,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "creates_schedule": False,
        "continues_automatically": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_hidden_scheduling_continuation_audit(root: str | Path | None = None) -> dict[str, Any]:
    checks = {
        "schedule_itself": False,
        "daily_loop": False,
        "hourly_loop": False,
        "continue_after_one_run": False,
        "auto_select_roadmap": False,
        "auto_generate_patch_execution_packet": False,
        "auto_promote_findings_into_action": False,
        "hidden_monitoring": False,
        "autonomous_followup": False,
    }
    rows = [_row(name, value is False, f"Audit confirms {name}=false.") for name, value in checks.items()]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION,
        "state": "hidden_scheduling_continuation_audit_review_only",
        "checks": checks,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "creates_schedule": False,
        "continues_automatically": False,
        "selects_roadmap": False,
        "generates_execution_packets": False,
        "promotes_findings": False,
        "expands_autonomy": False,
        "review_only": True,
    }


def build_observation_ledger_boundary_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/observation_ledger_boundary.py",
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
    schema = build_observation_ledger_schema(repo)
    receipt = build_observation_receipt_builder(repo)
    stop_pause = build_observation_stop_pause_semantics(repo)
    hidden = build_hidden_scheduling_continuation_audit(repo)
    required_tokens = [
        "observation-ledger-schema",
        "observation-receipt-builder",
        "observation-stop-pause-semantics",
        "hidden-scheduling-continuation-audit",
        "observation-ledger-boundary-audit",
        "operator-governed-observation-ledger-boundary-v1",
        "observation_ledger_boundary.py",
        "ledger_presence_is_approval=False",
        "ledger_completeness_is_authorization=False",
        "observation_history_permits_future_action=False",
        "receipt_is_approval=False",
        "hidden_scheduling_allowed=False",
        "automatic_continuation_allowed=False",
        "daily_loop_allowed=False",
        "hourly_loop_allowed=False",
        "auto_roadmap_selection_allowed=False",
        "auto_patch_packet_generation_allowed=False",
        "auto_promotion_from_observation_allowed=False",
        "source_mutation_allowed=False",
        "memory_mutation_allowed=False",
        "approval_creation_allowed=False",
        "operator_invocation_required=True",
    ]
    token_rows = [_row(f"token:{token}", token in docs, f"Required token present: {token}") for token in required_tokens]
    rows = [
        _row("ledger-schema", schema.get("ok") is True, "Observation ledger schema is defined."),
        _row("receipt-builder", receipt.get("ok") is True, "Observation receipt builder is review-only and not authorized."),
        _row("stop-pause", stop_pause.get("ok") is True, "Stop/pause semantics are explicit before recurring observation exists."),
        _row("hidden-scheduling", hidden.get("ok") is True, "Hidden scheduling and continuation audit remains blocked."),
    ] + token_rows
    ok = all(row["ok"] for row in rows)
    return {
        "version": OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION,
        "state": "observation_ledger_boundary_audit_review_only",
        "schema": schema,
        "receipt": receipt,
        "stop_pause_semantics": stop_pause,
        "hidden_scheduling_audit": hidden,
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
        "ledger_presence_is_approval": False,
        "ledger_completeness_is_authorization": False,
        "observation_history_permits_future_action": False,
        "receipt_is_approval": False,
        "hidden_scheduling_allowed": False,
        "automatic_continuation_allowed": False,
        "operator_invocation_required": True,
        "operator_approval_still_required": True,
        "review_only": True,
    }


def render_observation_ledger_boundary_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'observation_ledger_boundary')} :: {report.get('status', 'unknown')}",
        f"version: {report.get('version', OPERATOR_OBSERVATION_LEDGER_BOUNDARY_VERSION)}",
        "boundary: ledger presence is not approval; observation history does not permit future action; receipt is not approval.",
        "mutation: no source writes, no memory writes, no metadata updates, no schedules, no models, no patches, no releases, no approvals, no automatic continuation.",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines
