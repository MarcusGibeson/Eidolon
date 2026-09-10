from __future__ import annotations

"""Strictly read-only v1120.9 Self-Model Integrity and Identity Claim Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from self_model_continuity_review_checkpoint import build_self_model_continuity_review_checkpoint
from self_model_integrity_intake_checkpoint import build_self_model_integrity_intake_checkpoint
from self_model_revision_deliberation_checkpoint import build_self_model_revision_deliberation_checkpoint

CONTRACT_VERSION = "v1120.9"


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


def build_self_model_integrity_identity_claim_governance_checkpoint(
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
    intake = build_self_model_integrity_intake_checkpoint(root, source_root=source)
    deliberation = build_self_model_revision_deliberation_checkpoint(root, source_root=source)
    continuity = build_self_model_continuity_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (intake, deliberation, continuity)
    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "claim_text_exposed",
        "identity_text_exposed",
        "self_model_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    privacy_ok = all(
        report.get(field) is not True for report in reports for field in privacy_fields
    )

    authority_fields = (
        "identity_revised",
        "identity_claim_mutated",
        "self_model_revised",
        "self_model_mutated",
        "temporary_state_promoted",
        "persistent_trait_created",
        "records_deleted",
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
            "id": "self_model_governance_arc_lineage",
            "status": "pass"
            if intake.get("ok")
            and deliberation.get("ok")
            and continuity.get("ok")
            and intake.get("contract_version") == "v1120.2"
            and deliberation.get("contract_version") == "v1120.5"
            and continuity.get("contract_version") == "v1120.8"
            else "blocked",
            "detail": "Integrity intake, bounded revision deliberation, durable revision lineage, and stability review remain separately attributable across the complete v1120 arc.",
        },
        {
            "id": "signal_candidate_lineage",
            "status": "pass"
            if _check_passed(intake, "signal_persistence_lineage")
            and _check_passed(intake, "candidate_persistence_lineage")
            else "blocked",
            "detail": "Structural signals and review candidates preserve exact identity-claim, self-model, support, dependency, and digest lineage without revising those records.",
        },
        {
            "id": "support_contradiction_and_unsupported_claim_review",
            "status": "pass"
            if _check_passed(intake, "support_contradiction_separation")
            and _check_passed(intake, "claim_content_excluded")
            else "blocked",
            "detail": "Support gaps, contradictions, unsupported claims, and lineage gaps remain distinct structural review conditions rather than automatic identity conclusions.",
        },
        {
            "id": "temporal_scope_and_state_trait_separation",
            "status": "pass"
            if _check_passed(intake, "temporal_scope_handling")
            and _check_passed(intake, "state_trait_separation")
            else "blocked",
            "detail": "Temporary states, persistent traits, and temporal-scope mismatches remain explicitly distinguishable so transient evidence cannot become a durable identity claim by accident.",
        },
        {
            "id": "persistence_confidence_uncertainty_review",
            "status": "pass"
            if _check_passed(intake, "persistence_mismatch_handling")
            else "blocked",
            "detail": "Persistence, confidence, uncertainty, capability, limitation, and role mismatches remain bounded review evidence rather than claim mutation triggers.",
        },
        {
            "id": "duplicate_correction_retraction_accountability",
            "status": "pass"
            if _check_passed(intake, "duplicate_suppression")
            and _check_passed(intake, "semantic_overlap_distinct")
            and _check_passed(intake, "correction_retraction_visibility")
            else "blocked",
            "detail": "Retries and semantic overlap cannot multiply active influence, while corrected and retracted integrity records remain historically visible.",
        },
        {
            "id": "bounded_self_model_revision_deliberation",
            "status": "pass"
            if _check_passed(deliberation, "session_lineage")
            and _check_passed(deliberation, "arbitration_lineage")
            else "blocked",
            "detail": "Content-free deliberation sessions and deterministic arbitration remain review mechanisms rather than identity or self-model write paths.",
        },
        {
            "id": "recognized_identity_revision_outcomes",
            "status": "pass"
            if _check_passed(deliberation, "recognized_revision_outcomes")
            and _check_passed(deliberation, "retain_weaken_suspend")
            and _check_passed(deliberation, "reclassify_temporary_state")
            and _check_passed(deliberation, "replace_candidate")
            else "blocked",
            "detail": "Retain, weaken, suspend, temporary-state reclassification, replacement candidacy, unresolved, deliberate non-revision, and operator-review outcomes remain structurally distinct and non-mutative.",
        },
        {
            "id": "unresolved_and_deliberate_non_revision",
            "status": "pass"
            if _check_passed(deliberation, "unresolved_preserved")
            and _check_passed(deliberation, "deliberate_no_revision")
            else "blocked",
            "detail": "Weak, balanced, or ambiguous support may remain unresolved or deliberately avoid revision instead of forcing a synthetic identity narrative.",
        },
        {
            "id": "operator_review_deliberation_boundary",
            "status": "pass"
            if _check_passed(deliberation, "operator_review_boundary")
            else "blocked",
            "detail": "Sensitive identity reconsideration may require operator review, but that requirement grants no claim mutation, approval, authorization, or execution authority.",
        },
        {
            "id": "durable_identity_revision_lineage",
            "status": "pass"
            if _check_passed(continuity, "revision_lineage")
            and _check_passed(continuity, "historical_revisions_preserved")
            else "blocked",
            "detail": "Identity revision records preserve claim, session, predecessor, replacement, temporal-scope, persistence, confidence, uncertainty, and structural-digest lineage.",
        },
        {
            "id": "historical_supersession_without_deletion",
            "status": "pass"
            if _check_passed(continuity, "supersession_without_deletion")
            else "blocked",
            "detail": "Superseded identity revisions remain historically visible and cannot be silently deleted, rewritten, or promoted into current truth merely by recency.",
        },
        {
            "id": "self_model_stability_and_reliability_review",
            "status": "pass"
            if _check_passed(continuity, "identity_oscillation_detection")
            and _check_passed(continuity, "repeated_reversal_detection")
            and _check_passed(continuity, "revision_reliability_evidence")
            else "blocked",
            "detail": "Oscillation, repeated reversal, recurrence, state-trait instability, and revision reliability remain deterministic structural evidence reviews.",
        },
        {
            "id": "false_instability_suppression",
            "status": "pass"
            if _check_passed(continuity, "false_instability_suppression")
            else "blocked",
            "detail": "Thin evidence cannot become an identity-instability pattern merely because a dramatic explanation is available.",
        },
        {
            "id": "operator_reviewed_identity_policy_boundary",
            "status": "pass"
            if _check_passed(continuity, "operator_reviewed_policy_proposals")
            and _check_passed(continuity, "proposal_not_applied")
            else "blocked",
            "detail": "Identity-policy proposals remain unapplied, unapproved, unauthorized, and unable to revise identity, promote traits, or alter policy.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, categories, states, scores, counts, timestamps, and digests only, never conversations, prompts, provider payloads, claim text, private content, or hidden reasoning.",
        },
        {
            "id": "identity_governance_authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Identity claim, self-model claim, integrity signal, review candidate, deliberation, arbitration, revision lineage, stability review, and policy proposal remain distinct from attention, intention, approval, authorization, execution, promotion, and certification.",
        },
        {
            "id": "source_runtime_caution_and_pending_desktop_verification",
            "status": "pass"
            if not _inside(root, source) and not runtime_mutated
            else "blocked",
            "detail": "Mutable cognition remains outside source; checkpoint construction is read-only; observable self-model mechanisms do not prove consciousness, sentience, subjective experience, or personhood; native Desktop verification remains pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Self-model integrity preserves bounded identity review, explicit state-trait separation, durable revision lineage, and stability accountability without autonomous identity mutation or action authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "summary": {
            "self_model_integrity_intake": intake.get("summary") or {},
            "self_model_revision_deliberation": deliberation.get("summary") or {},
            "self_model_continuity_review": continuity.get("summary") or {},
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
        "claim_text_exposed": False,
        "identity_text_exposed": False,
        "self_model_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "identity_revised": False,
        "identity_claim_mutated": False,
        "self_model_revised": False,
        "self_model_mutated": False,
        "temporary_state_promoted": False,
        "persistent_trait_created": False,
        "records_deleted": False,
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
        "self_model_integrity_intake": intake,
        "self_model_revision_deliberation": deliberation,
        "self_model_continuity_review": continuity,
    }
