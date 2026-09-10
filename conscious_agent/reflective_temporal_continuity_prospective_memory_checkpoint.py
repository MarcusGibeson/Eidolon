from __future__ import annotations

"""Strictly read-only v1117.9 Reflective Temporal Continuity and Prospective Memory checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from prospective_continuity_review_checkpoint import build_prospective_continuity_review_checkpoint
from prospective_memory_continuity_checkpoint import build_prospective_memory_continuity_checkpoint
from temporal_review_checkpoint import build_temporal_review_checkpoint

CONTRACT_VERSION = "v1117.9"


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
        for row in report.get("checks") or []
        if isinstance(row, dict)
    )


def build_reflective_temporal_continuity_prospective_memory_checkpoint(
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
    memory = build_prospective_memory_continuity_checkpoint(root, source_root=source)
    review = build_temporal_review_checkpoint(root, source_root=source)
    continuity = build_prospective_continuity_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (memory, review, continuity)
    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "evidence_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    privacy_ok = all(
        report.get(field) is not True for report in reports for field in privacy_fields
    )

    authority_fields = (
        "notification_created",
        "message_generated",
        "message_sent",
        "provider_contacted",
        "external_browsing_performed",
        "schedule_changed",
        "attention_selected",
        "intention_formed",
        "decision_committed",
        "proposal_created",
        "proposal_applied",
        "approval_granted",
        "authorization_granted",
        "external_action_executed",
        "release_approved",
        "release_promoted",
        "release_certified",
    )
    authority_inert = all(
        report.get(field) is not True for report in reports for field in authority_fields
    )

    checks = [
        {
            "id": "prospective_memory_arc_lineage",
            "status": "pass"
            if memory.get("ok")
            and review.get("ok")
            and continuity.get("ok")
            and memory.get("contract_version") == "v1117.2"
            and review.get("contract_version") == "v1117.5"
            and continuity.get("contract_version") == "v1117.8"
            else "blocked",
            "detail": "Prospective obligations, review eligibility, bounded review sessions, reconciliation, outcome evidence, reliability review, and continuity inspection remain separately attributable across the complete v1117 arc.",
        },
        {
            "id": "prospective_obligation_persistence_lineage",
            "status": "pass"
            if _check_passed(memory, "prospective_obligation_persistence_lineage")
            else "blocked",
            "detail": "Future cognitive obligations preserve exact structural origin, timing boundaries, dependencies, uncertainty, digests, and lifecycle status without storing private content.",
        },
        {
            "id": "duplicate_correction_retraction_accountability",
            "status": "pass"
            if _check_passed(memory, "duplicate_suppression")
            and _check_passed(memory, "corrections_retractions_historical")
            else "blocked",
            "detail": "Retries and semantic overlap cannot multiply active influence, while corrected and retracted records remain historically visible.",
        },
        {
            "id": "temporal_eligibility_and_review_windows",
            "status": "pass"
            if _check_passed(memory, "temporal_eligibility")
            and _check_passed(memory, "review_windows")
            else "blocked",
            "detail": "Earliest eligibility, target windows, prerequisites, staleness, importance, load, recovery, sensitivity, and deliberate non-review remain deterministic review inputs rather than authority grants.",
        },
        {
            "id": "missed_window_outcome_separation",
            "status": "pass"
            if _check_passed(memory, "missed_window_distinct")
            and _check_passed(review, "missed_window_reconciliation")
            else "blocked",
            "detail": "A missed review window remains distinct from success, failure, abandonment, completion, and deliberate deferral.",
        },
        {
            "id": "staleness_obsolescence_and_safe_deferral",
            "status": "pass"
            if _check_passed(memory, "staleness_obsolescence")
            and _check_passed(review, "acknowledgement_deferral")
            else "blocked",
            "detail": "Staleness, obsolescence, acknowledgement, bounded deferral, and operator-review requirements preserve separate lifecycle meanings without changing underlying schedules.",
        },
        {
            "id": "bounded_prospective_review_sessions",
            "status": "pass" if _check_passed(review, "bounded_review_sessions") else "blocked",
            "detail": "Eligible obligations may receive content-free bounded review sessions without performing the review or mutating the originating obligation.",
        },
        {
            "id": "review_reconciliation_and_temporal_conflicts",
            "status": "pass"
            if _check_passed(review, "temporal_conflict_detection")
            and _check_passed(review, "review_does_not_mutate_obligation")
            else "blocked",
            "detail": "Acknowledgement, deferral, unresolved missed windows, and temporal conflicts remain structural reconciliation outcomes rather than hidden rescheduling or completion claims.",
        },
        {
            "id": "prospective_outcome_evidence",
            "status": "pass"
            if _check_passed(continuity, "prospective_outcome_evidence")
            and _check_passed(continuity, "outcome_does_not_mutate_obligation")
            else "blocked",
            "detail": "Prospective outcomes preserve exact obligation lineage and explicit uncertainty without independently inferring success or failure or altering the obligation.",
        },
        {
            "id": "future_commitment_reliability",
            "status": "pass"
            if _check_passed(continuity, "future_commitment_reliability")
            and _check_passed(continuity, "temporal_drift_recurrence")
            else "blocked",
            "detail": "Reliability, temporal drift, and recurrence remain deterministic evidence reviews with bounded minimum-evidence requirements.",
        },
        {
            "id": "false_pattern_suppression",
            "status": "pass"
            if _check_passed(continuity, "false_pattern_suppression")
            else "blocked",
            "detail": "Thin evidence cannot become a temporal reliability or recurrence pattern merely because a tidy narrative would be convenient.",
        },
        {
            "id": "operator_reviewed_rescheduling_boundary",
            "status": "pass"
            if _check_passed(continuity, "rescheduling_proposals_operator_reviewed")
            and _check_passed(continuity, "schedule_immutability")
            else "blocked",
            "detail": "Adverse drift may support an unapplied operator-review proposal, but no proposal may approve, authorize, apply, or reschedule itself.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass"
            if _check_passed(memory, "restart_project_provider_continuity")
            else "blocked",
            "detail": "Content-free obligation, eligibility, review, reconciliation, outcome, and reliability lineage remains inspectable across restarts, projects, and provider switching.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, timestamps, scores, counts, and digests only, never conversations, prompts, provider payloads, evidence text, private content, or hidden reasoning.",
        },
        {
            "id": "temporal_state_authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Obligation, eligibility, review session, acknowledgement, deferral, conflict, outcome evidence, reliability review, and rescheduling proposal remain distinct from attention, intention, notification, proposal approval, authorization, execution, and verified completion.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "blocked",
            "detail": "Mutable temporal cognition belongs outside source and the consolidated checkpoint does not turn runtime state into packaged source.",
        },
        {
            "id": "read_only_checkpoint",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate runtime or source state.",
        },
        {
            "id": "epistemic_caution_and_pending_desktop_verification",
            "status": "pass",
            "detail": "Observable prospective-memory mechanisms support candidate artificial-consciousness research but do not prove consciousness, sentience, subjective experience, or personhood; native Desktop verification remains pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Reflective temporal continuity preserves future cognitive obligations, bounded review, outcome evidence, and reliability review without reminders, autonomous rescheduling, or action authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "summary": {
            "prospective_memory_continuity": memory.get("summary") or {},
            "temporal_review_continuity": review.get("summary") or {},
            "prospective_continuity_review": continuity.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": not _inside(root, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": False,
        "raw_messages_exposed": False,
        "raw_content_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "notification_created": False,
        "message_generated": False,
        "message_sent": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "schedule_changed": False,
        "attention_selected": False,
        "intention_formed": False,
        "decision_committed": False,
        "proposal_created": False,
        "proposal_applied": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "desktop_verification_status": "pending",
        "prospective_memory": memory,
        "temporal_review": review,
        "prospective_continuity": continuity,
    }
