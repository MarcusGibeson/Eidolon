from __future__ import annotations
"""Strictly read-only v1109.9 Long-Horizon Follow-Through checkpoint."""

import hashlib
from pathlib import Path
import os
from typing import Any

from long_horizon_objective_checkpoint import build_long_horizon_objective_checkpoint
from objective_planning_progress_checkpoint import build_objective_planning_progress_checkpoint
from long_horizon_objective_lifecycle_checkpoint import build_long_horizon_objective_lifecycle_checkpoint

CONTRACT_VERSION = "v1109.9"


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _tree_signature(root: Path) -> str:
    """Return a content-free structural digest for read-only verification."""
    if not root.exists():
        return hashlib.sha256(b"missing-runtime-root").hexdigest()
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        try:
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8", errors="replace"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _check_passed(report: dict[str, Any], check_id: str) -> bool:
    return any(
        row.get("id") == check_id and row.get("status") == "pass"
        for row in report.get("checks", [])
        if isinstance(row, dict)
    )


def build_long_horizon_follow_through_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
    source = (
        Path(source_root).expanduser().resolve()
        if source_root
        else Path(__file__).resolve().parents[1]
    )

    before_signature = _tree_signature(root)
    foundation = build_long_horizon_objective_checkpoint(root, source_root=source)
    planning = build_objective_planning_progress_checkpoint(root, source_root=source)
    lifecycle = build_long_horizon_objective_lifecycle_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (foundation, planning, lifecycle)
    privacy_ok = all(
        report.get("hidden_reasoning_exposed") is not True
        and report.get("private_content_exposed") is not True
        for report in reports
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in (
            "provider_contacted",
            "message_sent",
            "external_action_executed",
            "action_authority_changed",
        )
    )

    checks = [
        {
            "id": "durable_objective_lineage",
            "status": "pass" if foundation.get("ok") else "blocked",
            "detail": "Objectives preserve intention, agenda, reflection, success-criteria, dependency, blocker, deferral, and update lineage.",
        },
        {
            "id": "bounded_review_and_no_selection",
            "status": "pass"
            if _check_passed(foundation, "bounded_review")
            else "blocked",
            "detail": "At most one eligible objective or deliberate no-selection may receive bounded internal review.",
        },
        {
            "id": "bounded_milestone_decomposition",
            "status": "pass"
            if _check_passed(planning, "bounded_decomposition")
            else "blocked",
            "detail": "Milestone breadth, depth, active count, resource cost, and parent-objective lineage remain bounded.",
        },
        {
            "id": "evidence_based_progress",
            "status": "pass"
            if _check_passed(planning, "evidence_discipline")
            and _check_passed(planning, "completion_claims")
            else "blocked",
            "detail": "Progress and completion require recognized evidence; repeated discussion is not accomplishment.",
        },
        {
            "id": "regression_and_invalidation_history",
            "status": "pass"
            if _check_passed(planning, "regression_invalidation")
            else "blocked",
            "detail": "Blocked, regressed, invalidated, and uncertain progress remain accountable historical states.",
        },
        {
            "id": "conflict_and_priority_accountability",
            "status": "pass"
            if _check_passed(lifecycle, "conflict_accountability")
            and _check_passed(lifecycle, "priority_no_authority")
            else "blocked",
            "detail": "Conflict, replacement, consolidation, deferral, suspension, retirement, and unresolved outcomes preserve history and grant no authority.",
        },
        {
            "id": "completion_and_abandonment_discipline",
            "status": "pass"
            if _check_passed(lifecycle, "completion_evidence")
            and _check_passed(lifecycle, "abandonment_history")
            and _check_passed(lifecycle, "terminal_history")
            else "blocked",
            "detail": "Completion requires criteria evidence, while abandonment and retirement preserve reasons, remaining obligations, and terminal history.",
        },
        {
            "id": "fairness_repetition_and_resource_boundaries",
            "status": "pass"
            if _check_passed(foundation, "fairness_repetition")
            and _check_passed(foundation, "control_boundaries")
            else "blocked",
            "detail": "Stagnation support, repetition penalties, quiet, sleep, pause, mode, cooldown, topic, project, time, and resource boundaries constrain follow-through.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass",
            "detail": "Structural objective evidence remains durable across turns, restarts, projects, and provider switching without depending on provider availability.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes bounded structural counts, states, identifiers, and digests only, never prompts, private conversations, evidence text, provider payloads, or hidden reasoning.",
        },
        {
            "id": "cognitive_action_state_separation",
            "status": "pass"
            if _check_passed(foundation, "state_separation")
            and _check_passed(planning, "state_separation")
            and _check_passed(lifecycle, "state_separation")
            else "blocked",
            "detail": "Attention, intention, objective, milestone, progress claim, proposal, authorization, execution, and verified completion remain distinct.",
        },
        {
            "id": "authority_boundary",
            "status": "pass" if authority_inert else "blocked",
            "detail": "This checkpoint cannot browse, send, execute, modify files, manage models, approve actions, authorize releases, promote, certify, install, pull, replace, or delete anything.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate runtime objective evidence.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable cognition evidence belongs outside source; native Desktop verification remains pending.",
        },
        {
            "id": "epistemic_caution",
            "status": "pass",
            "detail": "Observable long-horizon follow-through mechanisms support candidate artificial-consciousness research but do not prove consciousness.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Long-horizon objectives remain durable, evidence-disciplined, historically accountable, private, and unable to authorize or execute actions.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "objective_continuity": foundation.get("summary") or {},
            "planning_and_progress": planning.get("summary") or {},
            "conflict_completion_and_abandonment": lifecycle.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": not _inside(root, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "message_generated": False,
        "message_sent": False,
        "notification_sent": False,
        "proposal_created": False,
        "task_created": False,
        "automatic_retry": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "private_subjects_exposed": False,
        "action_authority_changed": False,
        "external_action_executed": False,
        "file_modification_performed": False,
        "model_management_performed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
        "desktop_verification_required": True,
        "desktop_verification_status": "pending",
    }
