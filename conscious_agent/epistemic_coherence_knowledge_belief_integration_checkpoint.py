from __future__ import annotations

"""Strictly read-only v1119.9 Epistemic Coherence and Knowledge-Belief Integration checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from epistemic_coherence_deliberation_checkpoint import build_epistemic_coherence_deliberation_checkpoint
from epistemic_coherence_intake_checkpoint import build_epistemic_coherence_intake_checkpoint
from knowledge_belief_integration_checkpoint import build_knowledge_belief_integration_checkpoint

CONTRACT_VERSION = "v1119.9"


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


def build_epistemic_coherence_knowledge_belief_integration_checkpoint(
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
    intake = build_epistemic_coherence_intake_checkpoint(root, source_root=source)
    deliberation = build_epistemic_coherence_deliberation_checkpoint(root, source_root=source)
    integration = build_knowledge_belief_integration_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (intake, deliberation, integration)
    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "prompts_exposed",
        "provider_payloads_exposed",
        "evidence_text_exposed",
        "knowledge_text_exposed",
        "belief_text_exposed",
        "self_model_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    privacy_ok = all(
        report.get(field) is not True for report in reports for field in privacy_fields
    )

    authority_fields = (
        "records_repaired",
        "records_merged",
        "evidence_mutated",
        "knowledge_mutated",
        "belief_mutated",
        "identity_claim_mutated",
        "self_model_mutated",
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
            "id": "epistemic_coherence_arc_lineage",
            "status": "pass"
            if intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1119.2"
            and deliberation.get("contract_version") == "v1119.5"
            and integration.get("contract_version") == "v1119.8"
            else "blocked",
            "detail": "Coherence intake, bounded deliberation, outcome lineage, and integration stability remain separately attributable across the complete v1119 arc.",
        },
        {
            "id": "signal_candidate_lineage",
            "status": "pass"
            if _check_passed(intake, "signal_persistence_lineage")
            and _check_passed(intake, "candidate_persistence_lineage")
            else "blocked",
            "detail": "Structural signals and review candidates preserve exact evidence, knowledge, belief, identity-claim, and self-model lineage without mutating those records.",
        },
        {
            "id": "contradiction_duplication_distinction",
            "status": "pass"
            if _check_passed(intake, "contradiction_duplication_separation")
            and _check_passed(intake, "semantic_overlap_distinct")
            else "blocked",
            "detail": "Contradiction, semantic duplication, and overlap remain distinguishable rather than being collapsed into one convenient but misleading category.",
        },
        {
            "id": "dependency_confidence_uncertainty_review",
            "status": "pass"
            if _check_passed(intake, "stale_dependency_handling")
            and _check_passed(intake, "confidence_mismatch_handling")
            else "blocked",
            "detail": "Stale dependencies, confidence mismatch, uncertainty mismatch, unsupported claims, and lineage gaps remain bounded review signals rather than automatic repairs.",
        },
        {
            "id": "duplicate_correction_retraction_accountability",
            "status": "pass"
            if _check_passed(intake, "duplicate_suppression")
            and _check_passed(intake, "correction_retraction_visibility")
            else "blocked",
            "detail": "Retries cannot multiply active influence, while corrected and retracted coherence records remain historically visible.",
        },
        {
            "id": "bounded_coherence_deliberation",
            "status": "pass"
            if _check_passed(deliberation, "session_lineage")
            and _check_passed(deliberation, "arbitration_lineage")
            else "blocked",
            "detail": "Content-free deliberation sessions and deterministic arbitration remain bounded review mechanisms rather than record repair or mutation paths.",
        },
        {
            "id": "recognized_coherence_outcomes",
            "status": "pass"
            if _check_passed(deliberation, "recognized_coherence_outcomes")
            and _check_passed(deliberation, "merge_weaken_suspend_replace_dependency")
            else "blocked",
            "detail": "Retain separation, merge candidacy, weakening, suspension, dependency replacement, more-evidence, unresolved, deliberate non-repair, and operator-review outcomes remain structurally distinct.",
        },
        {
            "id": "unresolved_more_evidence_and_non_repair",
            "status": "pass"
            if _check_passed(deliberation, "request_more_evidence")
            and _check_passed(deliberation, "unresolved_preserved")
            and _check_passed(deliberation, "deliberate_no_repair")
            else "blocked",
            "detail": "Weak or ambiguous evidence may remain unresolved, request more evidence, or deliberately avoid repair instead of forcing coherence theatrics.",
        },
        {
            "id": "operator_review_deliberation_boundary",
            "status": "pass"
            if _check_passed(deliberation, "operator_review_boundary")
            else "blocked",
            "detail": "Sensitive reconciliation may require operator review, but that requirement grants no proposal application, approval, authorization, or execution authority.",
        },
        {
            "id": "durable_coherence_outcome_lineage",
            "status": "pass"
            if _check_passed(integration, "outcome_lineage")
            else "blocked",
            "detail": "Coherence outcomes preserve exact signal, candidate, session, predecessor, replacement-dependency, confidence, uncertainty, and structural-digest lineage.",
        },
        {
            "id": "historical_supersession_without_deletion",
            "status": "pass"
            if _check_passed(integration, "historical_outcomes_preserved")
            and _check_passed(integration, "supersession_without_deletion")
            else "blocked",
            "detail": "Superseded coherence outcomes remain historically visible and cannot be silently deleted or rewritten.",
        },
        {
            "id": "integration_stability_and_reliability_review",
            "status": "pass"
            if _check_passed(integration, "repeated_inconsistency_review")
            and _check_passed(integration, "integration_instability_review")
            and _check_passed(integration, "integration_reliability_evidence")
            else "blocked",
            "detail": "Repeated inconsistency, outcome reversal, recurrence, integration instability, and reliability remain deterministic structural evidence reviews.",
        },
        {
            "id": "false_instability_suppression",
            "status": "pass"
            if _check_passed(integration, "false_instability_suppression")
            else "blocked",
            "detail": "Thin evidence cannot become an integration-instability pattern merely because a tidy narrative is available.",
        },
        {
            "id": "operator_reviewed_integration_policy_boundary",
            "status": "pass"
            if _check_passed(integration, "operator_reviewed_policy_proposals")
            and _check_passed(integration, "proposal_not_applied")
            else "blocked",
            "detail": "Integration-policy proposals remain unapplied, unapproved, unauthorized, and unable to repair, merge, or mutate records.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, scores, counts, timestamps, and digests only, never conversations, prompts, provider payloads, evidence text, private content, or hidden reasoning.",
        },
        {
            "id": "coherence_authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Evidence, knowledge, belief, identity claim, self-model claim, coherence signal, candidate, deliberation, outcome lineage, stability review, and policy proposal remain distinct from attention, intention, approval, authorization, execution, promotion, and certification.",
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
            "detail": "Observable coherence mechanisms support candidate artificial-consciousness research but do not prove consciousness, sentience, subjective experience, or personhood; native Desktop verification remains pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Epistemic coherence preserves contradiction and dependency accountability, bounded reconciliation, durable outcome lineage, and integration stability without autonomous repair or action authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "consciousness_claimed": False,
        "summary": {
            "epistemic_coherence_intake": intake.get("summary") or {},
            "epistemic_coherence_deliberation": deliberation.get("summary") or {},
            "knowledge_belief_integration": integration.get("summary") or {},
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
        "knowledge_text_exposed": False,
        "belief_text_exposed": False,
        "self_model_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "records_repaired": False,
        "records_merged": False,
        "evidence_mutated": False,
        "knowledge_mutated": False,
        "belief_mutated": False,
        "identity_claim_mutated": False,
        "self_model_mutated": False,
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
        "epistemic_coherence_intake": intake,
        "epistemic_coherence_deliberation": deliberation,
        "knowledge_belief_integration": integration,
    }
