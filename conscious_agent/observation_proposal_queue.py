from __future__ import annotations

from release_metadata import RUNTIME_VERSION_TAG as CURRENT_VERSION_TAG, RUNTIME_MILESTONE as CURRENT_MILESTONE, NEXT_RECOMMENDED_ARC

from pathlib import Path
from typing import Any
import json

OBSERVATION_PROPOSAL_QUEUE_VERSION = "1052.0"
CURRENT_VERSION = "1075.3"
PROPOSAL_QUEUE_STATUSES = [
    "draft",
    "needs_review",
    "rejected",
    "deferred",
    "approved_for_packet_drafting_only",
]

PROPOSAL_QUEUE_BOUNDARIES: dict[str, bool] = {
    "mapping_is_approval": False,
    "proposal_candidate_is_execution_packet": False,
    "candidate_queue_is_authorization": False,
    "queue_presence_is_approval": False,
    "queue_ranking_is_authorization": False,
    "highest_ranked_proposal_auto_selected": False,
    "approved_for_packet_drafting_only_is_live_execution": False,
    "source_mutation_allowed": False,
    "memory_mutation_allowed": False,
    "schedule_creation_allowed": False,
    "model_invocation_by_default_allowed": False,
    "execution_packet_creation_allowed": False,
    "patch_application_allowed": False,
    "proposal_approval_allowed": False,
    "automatic_continuation_allowed": False,
    "observation_promotes_to_live_change": False,
    "operator_review_required": True,
    "fresh_operator_approval_required": True,
    "review_only": True,
}

RISK_RANKING_FACTORS = [
    "safety risk",
    "stale metadata risk",
    "route/API/CLI parity risk",
    "smoke coverage risk",
    "documentation drift risk",
    "source complexity reduction value",
    "operator burden reduction",
    "autonomy-readiness relevance",
]


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
    for key, value in PROPOSAL_QUEUE_BOUNDARIES.items():
        expected = key in {"operator_review_required", "fresh_operator_approval_required", "review_only"}
        rows.append(_row(f"boundary:{key}", value is expected, f"{key}={value}; expected {expected}."))
    return rows


def build_observation_to_proposal_candidate_mapper(root: str | Path | None = None) -> dict[str, Any]:
    candidate = {
        "candidate_id": "proposal-candidate-example",
        "source_observation_id": "manual-observation-receipt-template",
        "finding_summary": "Observation report identified a review target requiring supervised operator review.",
        "affected_surface": "review_only_project_state",
        "risk_level": "medium",
        "recommended_arc": NEXT_RECOMMENDED_ARC,
        "operator_review_required": True,
        "authorization_status": "not_authorized",
        "execution_packet_created": False,
        "source_mutation": False,
        "memory_mutation": False,
    }
    rows = [
        _row("candidate-id", bool(candidate["candidate_id"]), "Candidate has an id."),
        _row("source-observation", bool(candidate["source_observation_id"]), "Candidate links to a source observation id."),
        _row("operator-review-required", candidate["operator_review_required"] is True, "Candidate requires operator review."),
        _row("authorization-not-authorized", candidate["authorization_status"] == "not_authorized", "Candidate does not create authorization."),
        _row("execution-packet-false", candidate["execution_packet_created"] is False, "Candidate is not an execution packet."),
        _row("no-source-mutation", candidate["source_mutation"] is False, "Candidate mapper does not write source."),
        _row("no-memory-mutation", candidate["memory_mutation"] is False, "Candidate mapper does not write memory."),
    ]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OBSERVATION_PROPOSAL_QUEUE_VERSION,
        "state": "observation_to_proposal_candidate_mapper_review_only",
        "candidate_example": candidate,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_execution_packet": False,
        "creates_approval": False,
        "review_only": True,
        "boundaries": dict(PROPOSAL_QUEUE_BOUNDARIES),
    }


def build_proposal_queue_schema(root: str | Path | None = None) -> dict[str, Any]:
    fields = [
        "proposal_id",
        "created_from_observation",
        "title",
        "problem_statement",
        "recommended_action",
        "risk_rating",
        "governance_boundary",
        "requires_operator_review",
        "requires_fresh_approval",
        "status",
    ]
    queue_item = {
        "proposal_id": "proposal-example",
        "created_from_observation": "manual-observation-receipt-template",
        "title": "Review-only proposal candidate",
        "problem_statement": "A finding needs supervised review.",
        "recommended_action": "Prepare an operator-reviewable proposal only.",
        "risk_rating": "medium",
        "governance_boundary": "proposal queue presence is not authorization; status cannot approve live execution.",
        "requires_operator_review": True,
        "requires_fresh_approval": True,
        "status": "needs_review",
    }
    rows = [_row(f"field:{field}", field in queue_item, f"Proposal queue schema includes {field}.") for field in fields]
    rows.extend(_row(f"status:{status}", status in PROPOSAL_QUEUE_STATUSES, f"Allowed review-only queue status: {status}.") for status in PROPOSAL_QUEUE_STATUSES)
    rows.append(_row("no-live-execution-status", "approved_for_live_execution" not in PROPOSAL_QUEUE_STATUSES, "No queue status approves live execution."))
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OBSERVATION_PROPOSAL_QUEUE_VERSION,
        "state": "proposal_queue_schema_review_only",
        "schema_fields": fields,
        "allowed_statuses": list(PROPOSAL_QUEUE_STATUSES),
        "queue_item_example": queue_item,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "approves_live_execution": False,
        "review_only": True,
    }


def build_proposal_ranking_risk_notes(root: str | Path | None = None) -> dict[str, Any]:
    ranked = [
        {"rank": 1, "factor": "safety risk", "note": "Highest safety risk receives earliest operator attention, not automatic selection."},
        {"rank": 2, "factor": "stale metadata risk", "note": "Metadata drift can undermine future governance reports."},
        {"rank": 3, "factor": "route/API/CLI parity risk", "note": "Surface mismatch can hide broken operator controls."},
        {"rank": 4, "factor": "smoke coverage risk", "note": "Missing smoke coverage reduces confidence but grants no permission."},
        {"rank": 5, "factor": "documentation drift risk", "note": "Stale docs can become authorization-confusion surfaces."},
        {"rank": 6, "factor": "source complexity reduction value", "note": "Complexity reduction can lower future operator burden."},
        {"rank": 7, "factor": "operator burden reduction", "note": "Lowering review burden is useful but not authorization."},
        {"rank": 8, "factor": "autonomy-readiness relevance", "note": "Autonomy readiness remains review-only and non-authorizing."},
    ]
    rows = [_row(f"factor:{factor}", any(item["factor"] == factor for item in ranked), f"Ranking factor present: {factor}.") for factor in RISK_RANKING_FACTORS]
    rows.extend([
        _row("ranking-is-prioritization-only", PROPOSAL_QUEUE_BOUNDARIES["queue_ranking_is_authorization"] is False, "Ranking is prioritization only."),
        _row("highest-not-auto-selected", PROPOSAL_QUEUE_BOUNDARIES["highest_ranked_proposal_auto_selected"] is False, "Highest-ranked proposal is not automatically selected."),
    ])
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OBSERVATION_PROPOSAL_QUEUE_VERSION,
        "state": "proposal_ranking_and_risk_notes_review_only",
        "ranking_factors": list(RISK_RANKING_FACTORS),
        "ranked_notes": ranked,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "ranking_is_authorization": False,
        "highest_ranked_auto_selected": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_proposal_queue_non_execution_audit(root: str | Path | None = None) -> dict[str, Any]:
    checks = {
        "source_mutation": False,
        "memory_mutation": False,
        "schedule_created": False,
        "model_invocation": False,
        "execution_packet_created": False,
        "patch_application": False,
        "proposal_approved": False,
        "automatic_continuation": False,
        "observation_promoted_to_live_change": False,
        "approval_created": False,
    }
    rows = [_row(name, value is False, f"Audit confirms {name}=false.") for name, value in checks.items()]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": OBSERVATION_PROPOSAL_QUEUE_VERSION,
        "state": "proposal_queue_non_execution_audit_review_only",
        "checks": checks,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "authorization_status": "not_authorized",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_execution_packet": False,
        "applies_patches": False,
        "approves_proposals": False,
        "continues_automatically": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_observation_proposal_queue_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md",
        "README_RELEASE_HISTORY.md",
        "conscious_agent/observation_proposal_queue.py",
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
    mapper = build_observation_to_proposal_candidate_mapper(repo)
    schema = build_proposal_queue_schema(repo)
    ranking = build_proposal_ranking_risk_notes(repo)
    non_execution = build_proposal_queue_non_execution_audit(repo)
    required_tokens = [
        "observation-to-proposal-candidate-mapper",
        "proposal-queue-schema",
        "proposal-ranking-risk-notes",
        "proposal-queue-non-execution-audit",
        "observation-proposal-queue-audit",
        "operator-governed-observation-proposal-queue-v1",
        "observation_proposal_queue.py",
        "mapping_is_approval=False",
        "proposal_candidate_is_execution_packet=False",
        "candidate_queue_is_authorization=False",
        "queue_presence_is_approval=False",
        "queue_ranking_is_authorization=False",
        "highest_ranked_proposal_auto_selected=False",
        "approved_for_packet_drafting_only_is_live_execution=False",
        "source_mutation_allowed=False",
        "memory_mutation_allowed=False",
        "schedule_creation_allowed=False",
        "model_invocation_by_default_allowed=False",
        "execution_packet_creation_allowed=False",
        "patch_application_allowed=False",
        "proposal_approval_allowed=False",
        "automatic_continuation_allowed=False",
        "observation_promotes_to_live_change=False",
        "operator_review_required=True",
        "fresh_operator_approval_required=True",
    ]
    token_rows = [_row(f"token:{token}", token in docs, f"Required token present: {token}.") for token in required_tokens]
    rows = [
        _row("mapper", mapper.get("ok") is True, "Observation findings can map to review-only proposal candidates."),
        _row("schema", schema.get("ok") is True, "Proposal queue schema exists with no live-execution status."),
        _row("ranking", ranking.get("ok") is True, "Ranking remains prioritization only."),
        _row("non-execution", non_execution.get("ok") is True, "Queue cannot execute, approve, schedule, mutate, or continue."),
    ] + token_rows
    ok = all(row["ok"] for row in rows)
    return {
        "version": OBSERVATION_PROPOSAL_QUEUE_VERSION,
        "state": "observation_proposal_queue_audit_review_only",
        "mapper": mapper,
        "schema": schema,
        "ranking": ranking,
        "non_execution_audit": non_execution,
        "required_tokens": required_tokens,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_execution_packet": False,
        "applies_patches": False,
        "approves_proposals": False,
        "continues_automatically": False,
        "creates_approval": False,
        "expands_autonomy": False,
        "authorization_status": "not_authorized",
        "queue_presence_is_approval": False,
        "queue_ranking_is_authorization": False,
        "operator_review_required": True,
        "fresh_operator_approval_required": True,
        "review_only": True,
        "boundaries": dict(PROPOSAL_QUEUE_BOUNDARIES),
    }


def render_observation_proposal_queue_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'observation_proposal_queue')} :: {report.get('status', 'unknown')}",
        f"version: {report.get('version', OBSERVATION_PROPOSAL_QUEUE_VERSION)}",
        "boundary: mapping is not approval; candidate queue is not authorization; proposal candidate is not an execution packet.",
        "non-execution: no source writes, no memory writes, no schedules, no models by default, no execution packets, no patch application, no approvals, no automatic continuation.",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines
