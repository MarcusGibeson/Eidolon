from __future__ import annotations

"""Strictly read-only v1121.9 Goal Coherence and Long-Horizon Objective Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from goal_continuity_review_checkpoint import build_goal_continuity_review_checkpoint
from objective_coherence_deliberation_checkpoint import build_objective_coherence_deliberation_checkpoint
from objective_coherence_intake_checkpoint import build_objective_coherence_intake_checkpoint

CONTRACT_VERSION = "v1121.9"


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


def build_goal_coherence_long_horizon_objective_governance_checkpoint(
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
    intake = build_objective_coherence_intake_checkpoint(root, source_root=source)
    deliberation = build_objective_coherence_deliberation_checkpoint(root, source_root=source)
    continuity = build_goal_continuity_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (intake, deliberation, continuity)
    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "objective_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    privacy_ok = all(
        report.get(field) is not True for report in reports for field in privacy_fields
    )

    authority_fields = (
        "objectives_reprioritized",
        "objective_abandoned",
        "dependency_modified",
        "milestone_modified",
        "policy_applied",
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
            "id": "goal_governance_arc_lineage",
            "status": "pass"
            if intake.get("ok")
            and deliberation.get("ok")
            and continuity.get("ok")
            and intake.get("contract_version") == "v1121.2"
            and deliberation.get("contract_version") == "v1121.5"
            and continuity.get("contract_version") == "v1121.8"
            else "blocked",
            "detail": "Objective-coherence intake, bounded deliberation, durable outcome lineage, and long-horizon stability review remain separately attributable across the complete v1121 arc.",
        },
        {
            "id": "signal_candidate_lineage",
            "status": "pass"
            if _check_passed(intake, "signal_persistence_lineage")
            and _check_passed(intake, "candidate_persistence_lineage")
            else "blocked",
            "detail": "Signals and review candidates preserve exact objective, milestone, dependency, and structural-digest lineage without mutating those records.",
        },
        {
            "id": "conflict_dependency_and_duplication_review",
            "status": "pass"
            if _check_passed(intake, "objective_conflict_distinct")
            and _check_passed(intake, "dependency_conflict_distinct")
            and _check_passed(intake, "semantic_overlap_distinct")
            else "blocked",
            "detail": "Objective conflict, dependency conflict, duplication, and semantic overlap remain distinct structural review conditions rather than automatic repairs.",
        },
        {
            "id": "priority_and_milestone_feasibility_review",
            "status": "pass"
            if _check_passed(intake, "priority_mismatch_distinct")
            and _check_passed(intake, "milestone_feasibility_distinct")
            else "blocked",
            "detail": "Priority mismatch and milestone infeasibility remain bounded evidence for review rather than reprioritization or milestone mutation triggers.",
        },
        {
            "id": "drift_and_abandonment_ambiguity",
            "status": "pass" if _check_passed(intake, "drift_abandonment_separation") else "blocked",
            "detail": "Objective drift, deliberate deferral, inactivity, abandonment ambiguity, and completed work remain structurally distinguishable.",
        },
        {
            "id": "duplicate_and_overlap_accountability",
            "status": "pass"
            if _check_passed(intake, "duplicate_suppression")
            and _check_passed(intake, "semantic_overlap_distinct")
            else "blocked",
            "detail": "Retries cannot multiply active influence, while semantically overlapping but structurally distinct objective concerns remain visible.",
        },
        {
            "id": "bounded_goal_coherence_deliberation",
            "status": "pass"
            if _check_passed(deliberation, "session_lineage")
            and _check_passed(deliberation, "arbitration_lineage")
            else "blocked",
            "detail": "Content-free deliberation sessions and deterministic arbitration remain review mechanisms rather than objective write paths.",
        },
        {
            "id": "recognized_goal_coherence_outcomes",
            "status": "pass"
            if _check_passed(deliberation, "recognized_outcomes")
            and _check_passed(deliberation, "retain_supported")
            and _check_passed(deliberation, "reprioritization_candidate_only")
            and _check_passed(deliberation, "dependency_repair_candidate_only")
            and _check_passed(deliberation, "milestone_revision_candidate_only")
            and _check_passed(deliberation, "abandonment_clarification_only")
            else "blocked",
            "detail": "Retain, reprioritization candidacy, dependency repair candidacy, milestone revision candidacy, abandonment clarification, unresolved, deliberate non-repair, and operator review remain distinct and non-mutative.",
        },
        {
            "id": "unresolved_and_deliberate_non_repair",
            "status": "pass"
            if _check_passed(deliberation, "unresolved_preserved")
            and _check_passed(deliberation, "deliberate_no_repair")
            else "blocked",
            "detail": "Weak, balanced, or ambiguous evidence may remain unresolved or deliberately avoid repair rather than forcing artificial goal coherence.",
        },
        {
            "id": "operator_review_deliberation_boundary",
            "status": "pass" if _check_passed(deliberation, "operator_review_boundary") else "blocked",
            "detail": "Sensitive objective reconsideration may require operator review, but that requirement grants no mutation, approval, authorization, or execution authority.",
        },
        {
            "id": "durable_objective_outcome_lineage",
            "status": "pass"
            if _check_passed(continuity, "outcome_lineage")
            and _check_passed(continuity, "historical_outcomes_preserved")
            else "blocked",
            "detail": "Objective-coherence outcomes preserve session, predecessor, dependency, milestone, confidence, uncertainty, and structural-digest lineage.",
        },
        {
            "id": "historical_supersession_without_deletion",
            "status": "pass" if _check_passed(continuity, "supersession_without_deletion") else "blocked",
            "detail": "Superseded goal-coherence outcomes remain historically visible and cannot be silently deleted, rewritten, or treated as current merely by recency.",
        },
        {
            "id": "long_horizon_goal_stability_and_reliability",
            "status": "pass"
            if _check_passed(continuity, "goal_reversal_detection")
            and _check_passed(continuity, "repeated_outcome_detection")
            and _check_passed(continuity, "goal_reliability_evidence")
            else "blocked",
            "detail": "Repeated outcomes, reversals, recurrence, and long-horizon reliability remain deterministic structural reviews rather than autonomous policy decisions.",
        },
        {
            "id": "false_instability_suppression",
            "status": "pass" if _check_passed(continuity, "false_instability_suppression") else "blocked",
            "detail": "Thin evidence cannot become a goal-instability pattern merely because a dramatic strategic explanation is available.",
        },
        {
            "id": "operator_reviewed_goal_policy_boundary",
            "status": "pass"
            if _check_passed(continuity, "operator_reviewed_policy_proposals")
            and _check_passed(continuity, "proposal_not_applied")
            else "blocked",
            "detail": "Goal-policy proposals remain unapplied, unapproved, unauthorized, and unable to reprioritize, abandon, mutate, or execute objectives.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, categories, states, scores, counts, timestamps, and digests only, never conversations, prompts, provider payloads, objective text, private content, or hidden reasoning.",
        },
        {
            "id": "goal_governance_authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Objective, milestone, dependency, coherence signal, review candidate, deliberation, arbitration, outcome lineage, stability review, and policy proposal remain distinct from attention, intention, approval, authorization, execution, promotion, and certification.",
        },
        {
            "id": "source_runtime_caution_and_pending_desktop_verification",
            "status": "pass" if not _inside(root, source) and not runtime_mutated else "blocked",
            "detail": "Mutable cognition remains outside source; checkpoint construction is read-only; observable goal-governance mechanisms do not prove consciousness, sentience, subjective experience, or personhood; native Desktop verification remains pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Goal coherence preserves bounded objective review, explicit non-repair, durable outcome lineage, and long-horizon stability accountability without autonomous reprioritization, abandonment, mutation, or action authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "summary": {
            "objective_coherence_intake": intake.get("summary") or {},
            "objective_coherence_deliberation": deliberation.get("summary") or {},
            "goal_continuity_review": continuity.get("summary") or {},
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
        "objective_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "objectives_reprioritized": False,
        "objective_abandoned": False,
        "dependency_modified": False,
        "milestone_modified": False,
        "policy_applied": False,
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
        "objective_coherence_intake": intake,
        "objective_coherence_deliberation": deliberation,
        "goal_continuity_review": continuity,
    }
