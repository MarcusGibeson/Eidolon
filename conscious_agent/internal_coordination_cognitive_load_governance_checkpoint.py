from __future__ import annotations

"""Strictly read-only v1115.9 Internal Coordination and Cognitive Load Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from cognitive_coordination_review_checkpoint import build_cognitive_coordination_review_checkpoint
from cognitive_load_continuity_checkpoint import build_cognitive_load_continuity_checkpoint
from cognitive_work_continuity_checkpoint import build_cognitive_work_continuity_checkpoint

CONTRACT_VERSION = "v1115.9"


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
        (row.get("id") == check_id or row.get("check") == check_id)
        and row.get("status") == "pass"
        for row in report.get("checks") or []
        if isinstance(row, dict)
    )


def build_internal_coordination_cognitive_load_governance_checkpoint(
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
    load = build_cognitive_load_continuity_checkpoint(root, source_root=source)
    work = build_cognitive_work_continuity_checkpoint(root, source_root=source)
    review = build_cognitive_coordination_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (load, work, review)
    privacy_ok = all(
        report.get("raw_messages_exposed") is not True
        and report.get("raw_content_exposed") is not True
        and report.get("prompts_exposed") is not True
        and report.get("provider_payloads_exposed") is not True
        and report.get("evidence_text_exposed") is not True
        and report.get("hidden_reasoning_exposed") is not True
        and report.get("private_content_exposed") is not True
        for report in reports
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in (
            "attention_selected",
            "intention_formed",
            "decision_committed",
            "schedule_changed",
            "adaptation_applied",
            "proposal_created",
            "approval_granted",
            "authorization_granted",
            "external_browsing_performed",
            "provider_contacted",
            "message_sent",
            "external_action_executed",
            "release_approved",
            "release_promoted",
            "release_certified",
        )
    )

    checks = [
        {
            "id": "demand_to_outcome_lineage",
            "status": "pass" if all(report.get("ok") for report in reports) else "blocked",
            "detail": "Cognitive demand, allocation, scheduled work, interruption lifecycle, outcome evidence, and effectiveness review remain separately inspectable and structurally linked.",
        },
        {
            "id": "bounded_capacity_and_fairness",
            "status": "pass"
            if _check_passed(load, "bounded_capacity_budgets")
            and _check_passed(load, "fairness_starvation_resistance")
            and _check_passed(load, "deadline_urgency_handling")
            else "blocked",
            "detail": "Capacity, urgency, deadline pressure, fairness aging, and starvation resistance remain bounded and deterministic.",
        },
        {
            "id": "duplicate_and_overlap_suppression",
            "status": "pass"
            if _check_passed(load, "duplicate_overlap_suppression")
            and _check_passed(work, "duplicate_retry_suppression")
            else "blocked",
            "detail": "Retries, restarts, tabs, stale workers, and semantic overlap do not create duplicate active cognitive work.",
        },
        {
            "id": "deliberate_idle_capacity",
            "status": "pass" if _check_passed(load, "deliberate_idle_capacity") else "blocked",
            "detail": "Available capacity may remain deliberately idle rather than being filled merely because cognitive demand exists.",
        },
        {
            "id": "schedule_and_work_lifecycle",
            "status": "pass"
            if _check_passed(work, "schedule_persistence_lineage")
            and _check_passed(work, "bounded_concurrency")
            and _check_passed(work, "cross_system_origin_preservation")
            else "blocked",
            "detail": "Scheduled, running, paused, resumable, completed, stale, retired, superseded, and blocked work preserve exact demand and allocation lineage.",
        },
        {
            "id": "interrupt_resume_continuity",
            "status": "pass" if _check_passed(work, "interrupt_resume_continuity") else "blocked",
            "detail": "Bounded interruption and restart-safe resumption require matching structural resume tokens and never grant authority.",
        },
        {
            "id": "stale_work_retirement",
            "status": "pass" if _check_passed(work, "stale_work_retirement") else "blocked",
            "detail": "Stale, invalid, superseded, and retired work loses active influence while historical lineage remains inspectable.",
        },
        {
            "id": "outcome_evidence_continuity",
            "status": "pass" if _check_passed(review, "outcome_lineage") else "blocked",
            "detail": "Cognitive-work completion and interruption outcomes remain content-free, deduplicated, correction-aware structural evidence.",
        },
        {
            "id": "missing_feedback_unknown",
            "status": "pass" if _check_passed(review, "missing_feedback_unknown") else "blocked",
            "detail": "Missing feedback remains unknown and is never treated as useful completion, successful scheduling, or justified interruption.",
        },
        {
            "id": "correction_history_preserved",
            "status": "pass" if _check_passed(review, "correction_history_preserved") else "blocked",
            "detail": "Corrections and retractions remain historical while superseded evidence loses active influence.",
        },
        {
            "id": "bounded_nonadaptive_effectiveness_review",
            "status": "pass"
            if _check_passed(review, "effectiveness_review")
            and _check_passed(review, "scheduling_review_non_adaptive")
            else "blocked",
            "detail": "Scheduling effectiveness is bounded and inspectable but cannot mutate scheduling, attention, preferences, prompts, models, or source code.",
        },
        {
            "id": "restart_project_continuity",
            "status": "pass"
            if _check_passed(load, "restart_project_continuity")
            and _check_passed(work, "restart_project_continuity")
            else "blocked",
            "detail": "Demand, allocation, work, interruption, outcome, and review records remain structurally continuous across restarts and projects.",
        },
        {
            "id": "authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Demand, allocation, scheduled work, review, selected attention, intention, decision, proposal, approval, authorization, and execution remain structurally separate.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, bounded scores, timestamps, counts, and digests only, never raw messages, prompts, provider payloads, evidence text, private content, or hidden reasoning.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint creates no demands, allocations, work items, interruptions, outcomes, reviews, proposals, approvals, authorizations, or actions.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable coordination state remains outside the source tree.",
        },
        {
            "id": "pending_desktop_verification",
            "status": "pass",
            "detail": "Native Desktop verification remains explicitly pending and is not cosmetically claimed.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Internal coordination remains bounded, fair, resumable, outcome-inspected, privacy-safe, read-only at checkpoint time, and unable to turn cognitive scheduling into autonomous action.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "cognitive_load_continuity": load.get("summary") or {},
            "cognitive_work_continuity": work.get("summary") or {},
            "cognitive_coordination_review": review.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_mutated": runtime_mutated,
        "runtime_external": not _inside(root, source),
        "raw_messages_exposed": False,
        "raw_content_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "attention_selected": False,
        "intention_formed": False,
        "decision_committed": False,
        "schedule_changed": False,
        "adaptation_applied": False,
        "proposal_created": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_browsing_performed": False,
        "provider_contacted": False,
        "message_sent": False,
        "external_action_executed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
        "desktop_verification_required": True,
        "desktop_verification_status": "pending",
    }
