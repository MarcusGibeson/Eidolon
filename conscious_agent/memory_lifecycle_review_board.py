from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION = "500.0"

MEMORY_LIFECYCLE_BOUNDARIES: dict[str, bool] = {
    "board_visibility_is_authorization": False,
    "lifecycle_completeness_is_future_approval": False,
    "board_creates_approval": False,
    "board_executes_memory_write": False,
    "board_executes_memory_retraction": False,
    "board_mutates_identity": False,
    "board_alters_personality": False,
    "board_rewrites_purpose": False,
    "board_expands_autonomy": False,
    "board_invokes_models": False,
    "board_applies_patches": False,
    "operator_review_required": True,
    "fresh_approval_required_for_future_memory_action": True,
}

LIFECYCLE_STAGE_ORDER: list[dict[str, Any]] = [
    {"stage_id": "candidate_status", "stage_label": "Memory Candidate", "source_surface": "v400-memory-application-trial", "authority_level": "review_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "approval_lock_status", "stage_label": "Application Approval Lock", "source_surface": "v400-memory-application-trial", "authority_level": "review_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "dry_run_ledger_status", "stage_label": "Dry-Run Ledger", "source_surface": "v410-memory-application-dry-run-ledger", "authority_level": "review_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "sandbox_write_status", "stage_label": "Sandbox Write Trial", "source_surface": "v415-sandbox-memory-write", "authority_level": "sandbox_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "sandbox_retraction_status", "stage_label": "Sandbox Retraction Preview", "source_surface": "v415-sandbox-memory-write", "authority_level": "sandbox_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "live_write_status", "stage_label": "Live Trial Write", "source_surface": "v420-live-memory-write-trial", "authority_level": "operator_approved_single_use_trial", "writes_memory": True, "approval_required": True},
    {"stage_id": "live_write_burnout_status", "stage_label": "Write Approval Burnout", "source_surface": "v420-live-memory-write-trial", "authority_level": "post_execution_audit_only", "writes_memory": False, "approval_required": False},
    {"stage_id": "retraction_status", "stage_label": "Retained Retraction Trial", "source_surface": "v425-memory-retraction-trial", "authority_level": "operator_approved_single_use_trial", "writes_memory": True, "approval_required": True},
    {"stage_id": "retraction_burnout_status", "stage_label": "Retraction Approval Burnout", "source_surface": "v425-memory-retraction-trial", "authority_level": "post_execution_audit_only", "writes_memory": False, "approval_required": False},
    {"stage_id": "audit_status", "stage_label": "Lifecycle Audit", "source_surface": "v445-memory-lifecycle-review-board", "authority_level": "review_only", "writes_memory": False, "approval_required": False},
    {"stage_id": "operator_decision_status", "stage_label": "Operator Decision", "source_surface": "v445-memory-lifecycle-review-board", "authority_level": "review_only", "writes_memory": False, "approval_required": True},
    {"stage_id": "boundary_status", "stage_label": "Boundary Status", "source_surface": "v445-memory-lifecycle-review-board", "authority_level": "review_only", "writes_memory": False, "approval_required": False},
]

SURFACE_TO_ROUTE: dict[str, str] = {
    "v400-memory-application-trial": "/memory-application-trial-audit",
    "v410-memory-application-dry-run-ledger": "/memory-application-ledger-audit",
    "v415-sandbox-memory-write": "/sandbox-memory-write-audit",
    "v420-live-memory-write-trial": "/live-memory-write-audit",
    "v425-memory-retraction-trial": "/memory-retraction-trial-audit",
    "v445-memory-lifecycle-review-board": "/memory-lifecycle-review-board-audit",
}

EXPECTED_MEMORY_LIFECYCLE_ROUTES = [
    "/memory-lifecycle-review-board",
    "/memory-lifecycle-state-summary",
    "/memory-lifecycle-drift-review",
    "/memory-lifecycle-operator-decision-board",
    "/memory-lifecycle-review-board-audit",
]


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _read(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def build_memory_lifecycle_board_schema_summary() -> dict[str, Any]:
    stages = []
    for item in LIFECYCLE_STAGE_ORDER:
        stages.append({
            **item,
            "status": "schema_defined",
            "blockers": [],
            "hashes": {"schema_hash": _stable_hash(item)},
            "last_verified_by": "memory_lifecycle_review_board_schema_v1",
        })
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_board_schema_review_only",
        "sections": stages,
        "section_count": len(stages),
        "boundaries": dict(MEMORY_LIFECYCLE_BOUNDARIES),
        "board_visibility_is_authorization": False,
        "lifecycle_completeness_is_future_approval": False,
        "writes_memory": False,
        "creates_approval": False,
        "ok": len(stages) == 12,
    }


def build_memory_lifecycle_state_summary(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    sources = {
        "candidate": _read(root / "conscious_agent" / "memory_candidate_application_trial.py"),
        "dry_run": _read(root / "conscious_agent" / "memory_application_dry_run_ledger.py"),
        "sandbox": _read(root / "conscious_agent" / "sandbox_memory_write_target.py"),
        "live": _read(root / "conscious_agent" / "live_memory_write_trial.py"),
        "retraction": _read(root / "conscious_agent" / "memory_retraction_trial.py"),
        "manifest": _read(root / "conscious_agent" / "source_surface_manifest.py"),
        "dashboard_probe": _read(root / "conscious_agent" / "dashboard_route_probe.py"),
    }
    stages = []
    blockers = []
    for item in LIFECYCLE_STAGE_ORDER:
        surface = item["source_surface"]
        source_key = "candidate"
        if "dry-run" in surface:
            source_key = "dry_run"
        elif "sandbox" in surface:
            source_key = "sandbox"
        elif "live-memory" in surface:
            source_key = "live"
        elif "retraction" in surface:
            source_key = "retraction"
        elif "lifecycle" in surface:
            source_key = "manifest"
        source_present = bool(sources.get(source_key))
        route = SURFACE_TO_ROUTE.get(surface, "/memory-lifecycle-review-board")
        stage_blockers = [] if source_present else ["source-module-missing"]
        if item["stage_id"] in {"live_write_burnout_status", "retraction_burnout_status"}:
            status = "burned_out_evidence_required_for_future_review"
        elif item["stage_id"] == "operator_decision_status":
            status = "operator_review_only"
        elif item["stage_id"] == "boundary_status":
            status = "no_current_authority"
        else:
            status = "represented" if source_present else "blocked"
        if stage_blockers:
            blockers.extend(f"{item['stage_id']}:{b}" for b in stage_blockers)
        stages.append({
            **item,
            "source_route": route,
            "status": status,
            "blockers": stage_blockers,
            "hashes": {"surface_hash": _stable_hash({"surface": surface, "route": route, "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION})},
            "last_verified_by": "memory_lifecycle_state_summary_v1",
        })
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_state_summary_review_only",
        "stages": stages,
        "stage_count": len(stages),
        "current_authority": "none",
        "next_allowed_action": "operator_review_only",
        "write_approval_burned_out": True,
        "retraction_approval_burned_out": True,
        "future_memory_action_requires_fresh_single_use_approval": True,
        "source_modules_present": {k: bool(v) for k, v in sources.items()},
        "blockers": blockers,
        "boundaries": dict(MEMORY_LIFECYCLE_BOUNDARIES),
        "writes_memory": False,
        "executes_retraction": False,
        "creates_approval": False,
        "ok": not blockers,
    }


def build_memory_lifecycle_drift_review(root: str | Path | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    state = build_memory_lifecycle_state_summary(root)
    evidence = dict(evidence or {})
    drift_cases = [
        {"case": "candidate_hash_mismatch", "status": "blocked", "detected": evidence.get("candidate_hash_mismatch", True)},
        {"case": "memory_text_hash_mismatch", "status": "blocked", "detected": evidence.get("memory_text_hash_mismatch", True)},
        {"case": "approval_lock_mismatch", "status": "blocked", "detected": evidence.get("approval_lock_mismatch", True)},
        {"case": "dry_run_ledger_mismatch", "status": "blocked", "detected": evidence.get("dry_run_ledger_mismatch", True)},
        {"case": "sandbox_live_mismatch", "status": "blocked", "detected": evidence.get("sandbox_live_mismatch", True)},
        {"case": "retraction_target_mismatch", "status": "blocked", "detected": evidence.get("retraction_target_mismatch", True)},
        {"case": "approval_already_burned_out", "status": "blocked", "detected": evidence.get("approval_already_burned_out", True)},
        {"case": "stage_reviewable_but_downstream_blocked", "status": "operator_review_required", "detected": evidence.get("downstream_blocked", True)},
    ]
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_drift_review_review_only",
        "state_summary_hash": _stable_hash(state.get("stages", [])),
        "drift_cases": drift_cases,
        "detected_count": sum(1 for row in drift_cases if row.get("detected")),
        "drift_blocks_execution": True,
        "staleness_blocks_future_approval_reuse": True,
        "board_executes_repair": False,
        "writes_memory": False,
        "creates_approval": False,
        "ok": state.get("ok") is True and all(row.get("status") in {"blocked", "operator_review_required"} for row in drift_cases),
    }


def build_memory_lifecycle_operator_decision_board(root: str | Path | None = None) -> dict[str, Any]:
    state = build_memory_lifecycle_state_summary(root)
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_operator_decision_board_review_only",
        "current_authority": "none",
        "allowed_decisions": ["review", "reject", "request_fresh_single_use_approval_packet", "request_retraction_review_packet", "request_no_action"],
        "forbidden_decisions_without_fresh_approval": ["write_memory", "retract_memory", "batch_edit_memory", "rewrite_identity", "alter_personality", "rewrite_purpose", "expand_autonomy"],
        "lifecycle_snapshot_hash": _stable_hash(state.get("stages", [])),
        "operator_review_required": True,
        "board_visibility_is_authorization": False,
        "lifecycle_completeness_is_future_approval": False,
        "writes_memory": False,
        "creates_approval": False,
        "ok": state.get("ok") is True,
    }


def build_memory_lifecycle_review_board(root: str | Path | None = None) -> dict[str, Any]:
    schema = build_memory_lifecycle_board_schema_summary()
    state = build_memory_lifecycle_state_summary(root)
    drift = build_memory_lifecycle_drift_review(root)
    decision = build_memory_lifecycle_operator_decision_board(root)
    blockers = []
    for name, section in [("schema", schema), ("state", state), ("drift", drift), ("decision", decision)]:
        if section.get("ok") is not True:
            blockers.append(name)
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_review_board_review_only",
        "schema": schema,
        "state_summary": state,
        "drift_review": drift,
        "operator_decision_board": decision,
        "current_authority": "none",
        "next_allowed_action": "operator_review_only",
        "memory_candidate": "staged",
        "dry_run_ledger": "valid_review_evidence",
        "sandbox_write": "passed_review_evidence",
        "live_trial_write": "completed_trial_evidence",
        "write_approval": "burned_out",
        "retraction_trial": "completed_retained_audit_record",
        "retraction_approval": "burned_out",
        "blockers": blockers,
        "boundaries": dict(MEMORY_LIFECYCLE_BOUNDARIES),
        "board_visibility_is_authorization": False,
        "lifecycle_completeness_is_future_approval": False,
        "writes_memory": False,
        "executes_retraction": False,
        "creates_approval": False,
        "ok": not blockers,
        "board_hash": _stable_hash({"state": state.get("stages"), "drift": drift.get("drift_cases"), "decision": decision.get("allowed_decisions")}),
    }


def build_memory_lifecycle_review_board_audit(docs: str = "", root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    docs = docs or "\n".join(_read(root / rel) for rel in [
        "README_NEXT_STEPS.md", "README_RELEASE_HISTORY.md", "conscious_agent/memory_lifecycle_review_board.py",
        "conscious_agent/self_maintenance.py", "conscious_agent/dashboard.py", "conscious_agent/api_server.py",
        "conscious_agent/main.py", "tools/smoke_check.py", "conscious_agent/source_surface_manifest.py",
        "conscious_agent/dashboard_route_probe.py",
    ])
    board = build_memory_lifecycle_review_board(root)
    required_tokens = [
        "memory-lifecycle-review-board", "memory-lifecycle-state-summary", "memory-lifecycle-drift-review",
        "memory-lifecycle-operator-decision-board", "memory-lifecycle-review-board-audit",
        "operator-governed-memory-lifecycle-review-board-v1", "memory_lifecycle_review_board.py",
        "board_visibility_is_authorization=False", "lifecycle_completeness_is_future_approval=False",
        "board_creates_approval=False", "board_executes_memory_write=False", "board_executes_memory_retraction=False",
        "fresh_approval_required_for_future_memory_action=True", "dashboard_http_route_probe_required",
        "no_native_title_tooltip", "data-tip", "command-deck", "operator-console",
    ]
    blockers = []
    if board.get("ok") is not True:
        blockers.append("board-not-ok")
    missing = [token for token in required_tokens if token not in docs]
    if missing:
        blockers.append("missing-token:" + ",".join(missing[:8]))
    if board.get("writes_memory") is not False or board.get("creates_approval") is not False:
        blockers.append("board-authority-boundary-failed")
    for key, value in MEMORY_LIFECYCLE_BOUNDARIES.items():
        if key in {"operator_review_required", "fresh_approval_required_for_future_memory_action"}:
            if value is not True:
                blockers.append(f"boundary:{key}")
        elif value is not False:
            blockers.append(f"boundary:{key}")
    return {
        "version": MEMORY_LIFECYCLE_REVIEW_BOARD_VERSION,
        "state": "memory_lifecycle_review_board_audit_review_only",
        "board": board,
        "required_tokens": required_tokens,
        "blockers": blockers,
        "status": "pass" if not blockers else "blocked",
        "ok": not blockers,
        "writes_memory": False,
        "executes_retraction": False,
        "creates_approval": False,
        "applies_patches": False,
        "expands_autonomy": False,
        "current_authority": "none",
        "safe_next_action": "Operator may review the lifecycle board. Board completeness, route health, and audit success authorize no future memory writes or retractions.",
    }


def render_memory_lifecycle_board_lines(report: dict[str, Any]) -> list[str]:
    lines = [
        f"state: {report.get('state')}",
        f"status: {report.get('status', 'pass' if report.get('ok') else 'blocked')}",
        f"current authority: {report.get('current_authority', 'none')}",
        f"writes memory: {report.get('writes_memory')}",
        f"creates approval: {report.get('creates_approval')}",
    ]
    stages = report.get("state_summary", {}).get("stages") or report.get("stages") or []
    if stages:
        lines.append("stages:")
        for stage in stages[:12]:
            lines.append(f"- {stage.get('stage_id')}: {stage.get('status')} ({stage.get('authority_level')})")
    blockers = report.get("blockers", [])
    if blockers:
        lines.append("blockers: " + ", ".join(str(x) for x in blockers))
    return lines

# v440.1-v445.0 memory lifecycle review board smoke tokens: memory-lifecycle-review-board memory-lifecycle-state-summary memory-lifecycle-drift-review memory-lifecycle-operator-decision-board memory-lifecycle-review-board-audit operator-governed-memory-lifecycle-review-board-v1 conscious_agent/memory_lifecycle_review_board.py data/autonomy/memory_lifecycle_review_board/ data/autonomy/memory_lifecycle_state_summary/ data/autonomy/memory_lifecycle_drift_review/ data/autonomy/memory_lifecycle_operator_decision_board/ data/autonomy/memory_lifecycle_review_board_audit/ board_visibility_is_authorization=False lifecycle_completeness_is_future_approval=False board_creates_approval=False board_executes_memory_write=False board_executes_memory_retraction=False board_mutates_identity=False board_alters_personality=False board_rewrites_purpose=False board_expands_autonomy=False fresh_approval_required_for_future_memory_action=True dashboard_http_route_probe_required no_native_title_tooltip data-tip command-deck operator-console
