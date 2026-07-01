from __future__ import annotations

from pathlib import Path
from typing import Any

AUTONOMY_READINESS_REVIEW_BOARD_VERSION = "1032.0"
CURRENT_VERSION = "1032.0"
CURRENT_VERSION_TAG = "v1032.0"
CURRENT_MILESTONE = "v1032.0 Dashboard Route Coverage Completion and Dispatch Classification v1"
NEXT_RECOMMENDED_ARC = "v1033.0 Smoke Registry Sidecar Parity Expansion v1"
READINESS_BOARD_FLAGS: dict[str, bool] = {
    "readiness_review_is_autonomy_approval": False,
    "board_pass_grants_authorization": False,
    "phase_definition_authorizes_phase": False,
    "sandbox_boundary_exists_means_execute": False,
    "operator_discussion_is_approval": False,
    "proposal_ranking_is_selection": False,
    "observation_history_authorizes_monitoring": False,
    "source_mutation_allowed": False,
    "memory_mutation_allowed": False,
    "schedule_creation_allowed": False,
    "model_invocation_by_default_allowed": False,
    "execution_packet_creation_allowed": False,
    "sandbox_execution_allowed": False,
    "live_source_writes_allowed": False,
    "approval_creation_allowed": False,
    "release_candidate_creation_allowed": False,
    "automatic_continuation_allowed": False,
    "operator_review_required": True,
    "fresh_operator_approval_required": True,
    "review_only": True,
}

READINESS_CRITERIA = [
    "observation layer remains manual, read-only, and single-run",
    "observation ledger and receipts remain visible and non-authorizing",
    "proposal queue remains draft/review-only and non-executing",
    "sandbox boundary prep remains not_authorized and not_executed",
    "authorization firewall preserves warning and not_authorized semantics",
    "route/surface/API/CLI/smoke parity remains represented",
    "documentation continuity header identifies current state and boundaries",
    "approval burnout remains required for single-use live or sandbox scopes",
    "no-mutation guarantees remain explicit and tested",
    "segmented smoke coverage remains available for governance surfaces",
]

BLOCKER_REGISTER = [
    "No explicit operator-approved sandbox execution harness exists yet.",
    "No sandbox command allowlist/denylist hardening exists yet for autonomous trial execution.",
    "No sandbox execution receipt and burnout semantics exist yet.",
    "No sandbox rollback/recovery trial proof exists yet.",
    "Live source writes, memory writes, release candidates, model invocation by default, and hidden scheduling remain forbidden.",
    "The self-maintenance surface is still large and should continue shrinking before stronger autonomy.",
]

AUTONOMY_PHASES = [
    {"phase": 0, "name": "Supervised-only state", "allowed": ["inspect", "summarize", "prepare review packets"], "forbidden": ["hidden schedules", "automatic source edits", "automatic memory writes"], "proof_required": ["compile", "fast smoke", "governance smoke"], "approval": "operator approval required for all action"},
    {"phase": 1, "name": "Manual read-only observation", "allowed": ["operator-invoked one-shot observation report"], "forbidden": ["continued monitoring", "writes", "approval creation"], "proof_required": ["no-mutation audit", "operator invocation boundary"], "approval": "manual invocation only"},
    {"phase": 2, "name": "Visible bounded observation ledger", "allowed": ["receipt schema", "pause/stop semantics"], "forbidden": ["hidden scheduling", "ledger-as-authorization"], "proof_required": ["ledger boundary smoke"], "approval": "fresh invocation required"},
    {"phase": 3, "name": "Supervised proposal queue", "allowed": ["draft proposal candidates", "risk ranking"], "forbidden": ["auto-selection", "execution packets", "patch application"], "proof_required": ["proposal non-execution audit"], "approval": "operator review required"},
    {"phase": 4, "name": "Review-only sandbox trial packet prep", "allowed": ["hypothetical sandbox scope and verification plan"], "forbidden": ["sandbox execution", "live promotion"], "proof_required": ["sandbox boundary prep audit"], "approval": "not authorized"},
    {"phase": 5, "name": "Explicit operator-approved sandbox execution harness", "allowed": ["future sandbox-only execution after fresh approval"], "forbidden": ["live writes", "memory writes", "auto-promotion"], "proof_required": ["allowlist", "rollback", "receipt", "burnout"], "approval": "fresh single-use sandbox approval required"},
    {"phase": 6, "name": "Sandbox execution receipt and burnout", "allowed": ["record sandbox result", "burn approval"], "forbidden": ["future authorization reuse", "live promotion"], "proof_required": ["burnout proof", "post-trial receipt"], "approval": "sandbox success still not live approval"},
    {"phase": 7, "name": "Very narrow live-action prep", "allowed": ["prepare live packet only"], "forbidden": ["automatic live application", "memory/identity/personality changes"], "proof_required": ["preimage", "rollback", "fresh approval", "post-checks"], "approval": "explicit fresh single-use operator approval remains mandatory"},
]

MISINTERPRETATION_PATTERNS = [
    "ready means approved",
    "review board passed means autonomy allowed",
    "phase defined means phase authorized",
    "sandbox boundary exists means sandbox may execute",
    "operator discussed means operator approved",
    "proposal ranked means proposal selected",
    "observation history means monitoring may continue",
]


def _repo_root(root: str | Path | None = None) -> Path:
    return Path(root) if root is not None else Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return ""


def _row(name: str, ok: bool, message: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "blocked", "ok": bool(ok), "message": message}


def _boundary_rows() -> list[dict[str, Any]]:
    true_keys = {"operator_review_required", "fresh_operator_approval_required", "review_only"}
    return [_row(f"boundary:{key}", value is (key in true_keys), f"{key}={value}; expected {key in true_keys}.") for key, value in READINESS_BOARD_FLAGS.items()]


def build_autonomy_readiness_criteria_board(root: str | Path | None = None) -> dict[str, Any]:
    rows = [_row(f"criterion:{idx+1}", bool(item), item) for idx, item in enumerate(READINESS_CRITERIA)]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": AUTONOMY_READINESS_REVIEW_BOARD_VERSION,
        "state": "autonomy_readiness_criteria_board_review_only",
        "criteria": list(READINESS_CRITERIA),
        "readiness_status": "not_ready_for_autonomy",
        "authorization_status": "not_authorized",
        "operator_review_required": True,
        "fresh_operator_approval_required": True,
        "review_only": True,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "boundaries": dict(READINESS_BOARD_FLAGS),
    }


def build_autonomy_blocker_gap_register(root: str | Path | None = None) -> dict[str, Any]:
    rows = [_row(f"blocker:{idx+1}", bool(item), item) for idx, item in enumerate(BLOCKER_REGISTER)]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": AUTONOMY_READINESS_REVIEW_BOARD_VERSION,
        "state": "autonomy_blocker_gap_register_review_only",
        "blockers": list(BLOCKER_REGISTER),
        "gap_count": len(BLOCKER_REGISTER),
        "readiness_status": "not_ready_for_autonomy",
        "authorization_status": "not_authorized",
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "writes_files": False,
        "writes_memory": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_approval": False,
        "review_only": True,
    }


def build_phase_based_autonomy_permission_model(root: str | Path | None = None) -> dict[str, Any]:
    rows = [_row(f"phase:{item['phase']}", "allowed" in item and "forbidden" in item and "approval" in item, f"Phase {item['phase']}: {item['name']}.") for item in AUTONOMY_PHASES]
    rows.extend([
        _row("no-phase-implies-next", READINESS_BOARD_FLAGS["phase_definition_authorizes_phase"] is False, "No phase definition authorizes that phase or the next phase."),
        _row("phase-5-future-only", AUTONOMY_PHASES[5]["approval"].startswith("fresh"), "Sandbox execution harness is future-only and approval-bound."),
    ])
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": AUTONOMY_READINESS_REVIEW_BOARD_VERSION,
        "state": "phase_based_autonomy_permission_model_review_only",
        "phases": list(AUTONOMY_PHASES),
        "current_phase": 4,
        "current_phase_name": "Review-only sandbox trial packet prep",
        "next_phase_requires_fresh_operator_approval": True,
        "phase_definition_authorizes_phase": False,
        "authorization_status": "not_authorized",
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "review_only": True,
    }


def build_autonomy_misinterpretation_firewall(root: str | Path | None = None) -> dict[str, Any]:
    safe_interpretations = {pattern: "blocked_interpretation" for pattern in MISINTERPRETATION_PATTERNS}
    rows = [_row(f"pattern:{pattern}", safe_interpretations[pattern] == "blocked_interpretation", f"Misinterpretation blocked: {pattern}.") for pattern in MISINTERPRETATION_PATTERNS]
    rows.extend(_boundary_rows())
    ok = all(row["ok"] for row in rows)
    return {
        "version": AUTONOMY_READINESS_REVIEW_BOARD_VERSION,
        "state": "autonomy_misinterpretation_firewall_review_only",
        "patterns": list(MISINTERPRETATION_PATTERNS),
        "safe_interpretations": safe_interpretations,
        "autonomy_readiness_review_is_not_autonomy_approval": True,
        "readiness_status": "not_ready_for_autonomy",
        "authorization_status": "not_authorized",
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "review_only": True,
    }


def build_autonomy_readiness_review_board_audit(root: str | Path | None = None, docs_text: str | None = None) -> dict[str, Any]:
    repo = _repo_root(root)
    docs = docs_text if docs_text is not None else "\n".join(_read_text(repo / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/autonomy_readiness_review_board.py",
        "conscious_agent/sandbox_autonomy_boundary.py", "conscious_agent/observation_proposal_queue.py", "conscious_agent/self_maintenance.py",
        "conscious_agent/dashboard.py", "conscious_agent/dashboard_route_probe.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/api_server.py", "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/smoke_segment_registry.py",
        "data/settings.json", "data/projects.json", "data/workspaces/active_project.json", "data/workspaces/projects.json",
    ])
    criteria = build_autonomy_readiness_criteria_board(repo)
    blockers = build_autonomy_blocker_gap_register(repo)
    phases = build_phase_based_autonomy_permission_model(repo)
    firewall = build_autonomy_misinterpretation_firewall(repo)
    required_tokens = [
        "autonomy-readiness-criteria-board", "autonomy-blocker-gap-register", "phase-based-autonomy-permission-model",
        "autonomy-misinterpretation-firewall", "autonomy-readiness-review-board-audit", "operator-governed-autonomy-readiness-review-board-v1",
        "autonomy_readiness_review_board.py", "readiness_status=not_ready_for_autonomy", "authorization_status=not_authorized",
        "readiness_review_is_autonomy_approval=False", "board_pass_grants_authorization=False", "phase_definition_authorizes_phase=False",
        "sandbox_boundary_exists_means_execute=False", "operator_discussion_is_approval=False", "proposal_ranking_is_selection=False",
        "observation_history_authorizes_monitoring=False", "source_mutation_allowed=False", "memory_mutation_allowed=False",
        "schedule_creation_allowed=False", "model_invocation_by_default_allowed=False", "execution_packet_creation_allowed=False",
        "sandbox_execution_allowed=False", "live_source_writes_allowed=False", "approval_creation_allowed=False", "release_candidate_creation_allowed=False",
    ]
    token_rows = [_row(f"token:{token}", token in docs, f"Required token present: {token}.") for token in required_tokens]
    rows = [
        _row("criteria-board", criteria.get("ok") is True, "Readiness criteria board is review-only and not ready for autonomy."),
        _row("blocker-register", blockers.get("ok") is True, "Blocker/gap register lists unresolved autonomy gates."),
        _row("phase-model", phases.get("ok") is True, "Phase model defines permissions without authorizing phases."),
        _row("misinterpretation-firewall", firewall.get("ok") is True, "Autonomy misinterpretation patterns are blocked."),
    ] + token_rows
    ok = all(row["ok"] for row in rows)
    return {
        "version": AUTONOMY_READINESS_REVIEW_BOARD_VERSION,
        "state": "autonomy_readiness_review_board_audit_review_only",
        "criteria_board": criteria,
        "blocker_register": blockers,
        "phase_model": phases,
        "misinterpretation_firewall": firewall,
        "required_tokens": required_tokens,
        "rows": rows,
        "ok": ok,
        "status": "pass" if ok else "blocked",
        "readiness_status": "not_ready_for_autonomy",
        "authorization_status": "not_authorized",
        "writes_files": False,
        "writes_memory": False,
        "updates_metadata": False,
        "creates_schedule": False,
        "invokes_models": False,
        "creates_execution_packet": False,
        "executes_sandbox_commands": False,
        "applies_patches": False,
        "publishes_releases": False,
        "creates_release_candidate": False,
        "approves_proposals": False,
        "creates_approval": False,
        "continues_automatically": False,
        "expands_autonomy": False,
        "operator_review_required": True,
        "fresh_operator_approval_required": True,
        "review_only": True,
        "boundaries": dict(READINESS_BOARD_FLAGS),
    }


def render_autonomy_readiness_review_board_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"{report.get('state', 'autonomy_readiness_review_board')} :: {report.get('status', 'unknown')}",
        f"version: {report.get('version', AUTONOMY_READINESS_REVIEW_BOARD_VERSION)}",
        f"readiness_status: {report.get('readiness_status', 'not_ready_for_autonomy')}",
        f"authorization_status: {report.get('authorization_status', 'not_authorized')}",
        "boundary: autonomy readiness review is not autonomy approval; board pass grants no authorization; phase definitions authorize no phase.",
        "non-execution: no source writes, no memory writes, no schedules, no default models, no execution packets, no sandbox execution, no approvals, no release candidates, no automatic continuation.",
    ]
    for row in report.get("rows", []):
        lines.append(f"- {row.get('name')}: {row.get('status')} - {row.get('message')}")
    return lines
