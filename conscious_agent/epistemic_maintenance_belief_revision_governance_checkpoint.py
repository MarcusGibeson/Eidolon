from __future__ import annotations

"""Strictly read-only v1118.9 Epistemic Maintenance and Belief Revision Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from belief_continuity_review_checkpoint import build_belief_continuity_review_checkpoint
from belief_reconsideration_intake_checkpoint import build_belief_reconsideration_intake_checkpoint
from belief_revision_deliberation_checkpoint import build_belief_revision_deliberation_checkpoint

CONTRACT_VERSION = "v1118.9"


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


def build_epistemic_maintenance_belief_revision_governance_checkpoint(
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
    intake = build_belief_reconsideration_intake_checkpoint(root, source_root=source)
    deliberation = build_belief_revision_deliberation_checkpoint(root, source_root=source)
    continuity = build_belief_continuity_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (intake, deliberation, continuity)
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
        "belief_revised",
        "belief_mutated",
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
            "id": "epistemic_maintenance_arc_lineage",
            "status": "pass"
            if intake.get("ok")
            and deliberation.get("ok")
            and continuity.get("ok")
            and intake.get("contract_version") == "v1118.2"
            and deliberation.get("contract_version") == "v1118.5"
            and continuity.get("contract_version") == "v1118.8"
            else "blocked",
            "detail": "Evidence-change intake, reconsideration candidacy, revision deliberation, revision lineage, and epistemic stability remain separately attributable across the complete v1118 arc.",
        },
        {
            "id": "evidence_change_signal_lineage",
            "status": "pass"
            if _check_passed(intake, "signal_persistence_lineage")
            else "blocked",
            "detail": "Evidence additions, corrections, retractions, staleness, provenance changes, contradictions, confidence changes, uncertainty changes, and scheduled reconsideration points preserve exact structural lineage.",
        },
        {
            "id": "reconsideration_candidate_lineage",
            "status": "pass"
            if _check_passed(intake, "candidate_persistence_lineage")
            else "blocked",
            "detail": "Belief reconsideration candidates preserve exact belief and signal lineage without revising the belief they reference.",
        },
        {
            "id": "duplicate_overlap_correction_retraction_accountability",
            "status": "pass"
            if _check_passed(intake, "duplicate_suppression")
            and _check_passed(intake, "semantic_overlap_distinct")
            and _check_passed(intake, "evidence_correction_retraction")
            else "blocked",
            "detail": "Retries and semantic overlap cannot multiply active influence, while evidence corrections and retractions remain historically visible.",
        },
        {
            "id": "scheduled_reconsideration_continuity",
            "status": "pass"
            if _check_passed(intake, "scheduled_reconsideration_continuity")
            else "blocked",
            "detail": "Scheduled reconsideration remains a bounded structural trigger and never becomes proof, attention selection, belief revision, or action authority merely because time passed.",
        },
        {
            "id": "bounded_revision_deliberation",
            "status": "pass"
            if _check_passed(deliberation, "session_lineage")
            and _check_passed(deliberation, "arbitration_lineage")
            else "blocked",
            "detail": "Content-free deliberation sessions and deterministic arbitration remain bounded review mechanisms rather than belief mutations.",
        },
        {
            "id": "recognized_revision_outcomes",
            "status": "pass"
            if _check_passed(deliberation, "recognized_revision_outcomes")
            and _check_passed(deliberation, "retain_weaken_strengthen_suspend_replace")
            else "blocked",
            "detail": "Retain, weaken, strengthen, suspend, replace, unresolved, deliberate no-revision, and operator-review outcomes remain explicitly distinguishable.",
        },
        {
            "id": "unresolved_and_deliberate_no_revision",
            "status": "pass"
            if _check_passed(deliberation, "unresolved_preserved")
            and _check_passed(deliberation, "deliberate_no_revision")
            else "blocked",
            "detail": "Weak, balanced, or uncertain evidence may remain unresolved or deliberately unrevised instead of being forced into a theatrical conclusion.",
        },
        {
            "id": "operator_review_deliberation_boundary",
            "status": "pass"
            if _check_passed(deliberation, "operator_review_boundary")
            else "blocked",
            "detail": "Sensitive or consequential revision outcomes may require operator review, but that requirement grants no approval, authorization, application, or execution authority.",
        },
        {
            "id": "durable_revision_lineage",
            "status": "pass"
            if _check_passed(continuity, "revision_lineage")
            else "blocked",
            "detail": "Revision outcomes preserve durable predecessor, replacement, deliberation, confidence, uncertainty, and structural-digest lineage.",
        },
        {
            "id": "historical_supersession_without_deletion",
            "status": "pass"
            if _check_passed(continuity, "historical_revisions_preserved")
            and _check_passed(continuity, "supersession_without_deletion")
            else "blocked",
            "detail": "Superseded revisions remain historically visible and cannot be silently deleted or rewritten.",
        },
        {
            "id": "epistemic_stability_and_reversal_review",
            "status": "pass"
            if _check_passed(continuity, "oscillation_detection")
            and _check_passed(continuity, "repeated_reversal_detection")
            and _check_passed(continuity, "revision_reliability_evidence")
            else "blocked",
            "detail": "Oscillation, repeated reversal, recurrence, and reliability remain deterministic evidence reviews with accountable lineage.",
        },
        {
            "id": "false_instability_suppression",
            "status": "pass"
            if _check_passed(continuity, "false_instability_suppression")
            else "blocked",
            "detail": "Thin evidence cannot become an epistemic-instability pattern merely because a neat story is available.",
        },
        {
            "id": "operator_reviewed_policy_proposal_boundary",
            "status": "pass"
            if _check_passed(continuity, "operator_reviewed_policy_proposals")
            and _check_passed(continuity, "proposal_not_applied")
            else "blocked",
            "detail": "Epistemic-policy proposals remain unapplied, unapproved, unauthorized, and unable to mutate beliefs or policy.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, scores, counts, timestamps, and digests only, never conversations, prompts, provider payloads, evidence text, private content, or hidden reasoning.",
        },
        {
            "id": "belief_revision_authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Evidence, belief, reconsideration candidate, deliberation, revision outcome, lineage, stability review, and policy proposal remain distinct from attention, intention, decision commitment, approval, authorization, execution, promotion, and certification.",
        },
        {
            "id": "source_runtime_and_read_only_separation",
            "status": "pass"
            if not _inside(root, source) and not runtime_mutated
            else "blocked",
            "detail": "Mutable epistemic cognition belongs outside source, and building the consolidated checkpoint mutates neither runtime nor packaged source.",
        },
        {
            "id": "epistemic_caution_and_pending_desktop_verification",
            "status": "pass",
            "detail": "Observable belief-maintenance mechanisms support candidate artificial-consciousness research but do not prove consciousness, sentience, subjective experience, or personhood; native Desktop verification remains pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Epistemic maintenance preserves evidence-change lineage, bounded belief reconsideration, accountable revision history, and stability review without autonomous belief mutation or action authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "summary": {
            "belief_reconsideration_intake": intake.get("summary") or {},
            "belief_revision_deliberation": deliberation.get("summary") or {},
            "belief_continuity_review": continuity.get("summary") or {},
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
        "belief_revised": False,
        "belief_mutated": False,
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
        "belief_reconsideration_intake": intake,
        "belief_revision_deliberation": deliberation,
        "belief_continuity_review": continuity,
    }
