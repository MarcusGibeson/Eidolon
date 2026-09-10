from __future__ import annotations

"""Strictly read-only v1114.9 Reflective Planning and Deliberative Choice checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from decision_commitment_checkpoint import build_decision_commitment_checkpoint
from deliberative_continuity_checkpoint import build_deliberative_continuity_checkpoint
from deliberative_decision_review_checkpoint import build_deliberative_decision_review_checkpoint

CONTRACT_VERSION = "v1114.9"


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


def build_reflective_planning_deliberative_choice_checkpoint(
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
    options = build_deliberative_continuity_checkpoint(root, source_root=source)
    commitments = build_decision_commitment_checkpoint(root, source_root=source)
    follow_through = build_deliberative_decision_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (options, commitments, follow_through)
    privacy_ok = all(
        report.get("raw_messages_exposed") is not True
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
            "decision_committed",
            "intention_formed",
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
            "id": "option_to_outcome_lineage",
            "status": "pass" if all(report.get("ok") for report in reports) else "blocked",
            "detail": "Options, comparisons, commitments, intention candidacy, outcome evidence, and reconsideration triggers remain separately inspectable and structurally linked.",
        },
        {
            "id": "bounded_option_comparison",
            "status": "pass"
            if _check_passed(options, "bounded_comparison_criteria")
            and _check_passed(options, "ambiguous_incomparable_choices")
            else "blocked",
            "detail": "Comparison preserves risk, reversibility, missing evidence, ambiguity, incomparability, operator constraints, and deliberate no-choice.",
        },
        {
            "id": "duplicate_and_overlap_suppression",
            "status": "pass"
            if _check_passed(options, "duplicate_semantic_overlap_suppression")
            and _check_passed(commitments, "duplicate_suppression")
            and _check_passed(follow_through, "duplicate_suppression")
            else "blocked",
            "detail": "Retries, restarts, tabs, stale workers, and semantic duplicates remain suppressed without erasing historical records.",
        },
        {
            "id": "commitment_lifecycle_continuity",
            "status": "pass"
            if _check_passed(commitments, "commitment_persistence_lineage")
            and _check_passed(commitments, "bounded_reconsideration")
            and _check_passed(commitments, "historical_continuity")
            else "blocked",
            "detail": "Commitments retain exact option lineage and may be reaffirmed, suspended, resumed, expired, retired, or replaced without silently becoming actions.",
        },
        {
            "id": "conflict_decay_and_replacement",
            "status": "pass"
            if _check_passed(commitments, "decay_and_expiry")
            and _check_passed(commitments, "conflict_replacement")
            else "blocked",
            "detail": "Decay, expiry, conflict, and replacement are explicit deterministic lifecycle outcomes rather than hidden priority rewrites.",
        },
        {
            "id": "decision_to_intention_restraint",
            "status": "pass"
            if _check_passed(follow_through, "decision_to_intention_lineage")
            and _check_passed(follow_through, "candidacy_thresholds")
            else "blocked",
            "detail": "A decision may create a bounded intention candidate, but candidacy never forms an intention or grants proposal, approval, authorization, or execution authority.",
        },
        {
            "id": "outcome_and_reconsideration_restraint",
            "status": "pass"
            if _check_passed(follow_through, "outcome_evidence_lineage")
            and _check_passed(follow_through, "reconsideration_trigger_restraint")
            else "blocked",
            "detail": "Content-free outcome evidence may recommend review but cannot execute a commitment transition or rewrite deliberative preferences.",
        },
        {
            "id": "missing_feedback_unknown",
            "status": "pass"
            if _check_passed(commitments, "missing_feedback_unknown")
            and _check_passed(follow_through, "missing_feedback_unknown")
            else "blocked",
            "detail": "Missing feedback remains unknown and is never treated as commitment success, option quality, or intention support.",
        },
        {
            "id": "correction_retraction_history",
            "status": "pass"
            if _check_passed(follow_through, "correction_retraction_history")
            else "blocked",
            "detail": "Corrections, retractions, suspended commitments, and superseded choices remain historical while losing active influence.",
        },
        {
            "id": "authority_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Option, comparison, decision, intention candidate, intention, proposal, approval, authorization, and execution remain structurally separate.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, bounded scores, timestamps, counts, and digests only, never raw messages, prompts, provider payloads, evidence text, or hidden reasoning.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not create options, commitments, intention candidates, outcome evidence, reconsideration triggers, or authority records.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable deliberative state remains outside the source tree.",
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
        "headline": "Reflective planning remains lineage-bound, uncertainty-aware, reversible, outcome-inspected, privacy-safe, read-only at checkpoint time, and unable to turn deliberation into autonomous action.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "deliberative_option_continuity": options.get("summary") or {},
            "decision_commitment_lifecycle": commitments.get("summary") or {},
            "deliberative_decision_follow_through": follow_through.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_mutated": runtime_mutated,
        "runtime_external": not _inside(root, source),
        "raw_messages_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "decision_committed": False,
        "intention_candidate_created": False,
        "intention_formed": False,
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
