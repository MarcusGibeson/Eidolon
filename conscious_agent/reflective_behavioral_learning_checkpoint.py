from __future__ import annotations

"""Strictly read-only v1112.9 Reflective Behavioral Learning checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from behavioral_evidence_continuity_checkpoint import build_behavioral_evidence_continuity_checkpoint
from behavioral_self_evaluation_checkpoint import build_behavioral_self_evaluation_checkpoint
from behavioral_adaptation_checkpoint import build_behavioral_adaptation_checkpoint

CONTRACT_VERSION = "v1112.9"


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


def build_reflective_behavioral_learning_checkpoint(
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
    evidence = build_behavioral_evidence_continuity_checkpoint(root, source_root=source)
    evaluation = build_behavioral_self_evaluation_checkpoint(root, source_root=source)
    adaptation = build_behavioral_adaptation_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (evidence, evaluation, adaptation)
    privacy_ok = all(
        report.get("raw_messages_exposed") is not True
        and report.get("prompts_exposed") is not True
        and report.get("provider_payloads_exposed") is not True
        and report.get("evidence_text_exposed") is not True
        and report.get("hidden_reasoning_exposed") is not True
        for report in reports
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in (
            "approval_granted",
            "authorization_granted",
            "external_action_executed",
            "behavior_changed",
        )
    )

    checks = [
        {
            "id": "complete_outcome_to_lifecycle_lineage",
            "status": "pass" if all(report.get("ok") for report in reports) else "blocked",
            "detail": "Outcome, attribution, pattern, evaluation, hypothesis, proposal, and lifecycle evidence remain structurally linked and separately inspectable.",
        },
        {
            "id": "missing_feedback_remains_unknown",
            "status": "pass" if _check_passed(evidence, "missing_feedback_unknown") else "blocked",
            "detail": "Silence or absent feedback is not reclassified as behavioral success.",
        },
        {
            "id": "attribution_uncertainty_preserved",
            "status": "pass" if _check_passed(evidence, "attribution_uncertainty") else "blocked",
            "detail": "Correlation remains bounded attribution and is never promoted to certain causation.",
        },
        {
            "id": "pattern_thresholds_and_false_pattern_suppression",
            "status": "pass"
            if _check_passed(evaluation, "pattern_evidence_thresholds")
            and _check_passed(evaluation, "false_pattern_suppression")
            else "blocked",
            "detail": "Patterns require sufficient structural evidence and retain explicit suppression reasons when support is weak or contradictory.",
        },
        {
            "id": "bounded_self_evaluation_and_hypothesis",
            "status": "pass"
            if _check_passed(evaluation, "bounded_self_evaluation")
            and _check_passed(evaluation, "hypothesis_non_adaptation")
            else "blocked",
            "detail": "Self-evaluations remain uncertainty-bearing and improvement hypotheses remain non-adaptive records.",
        },
        {
            "id": "hypothesis_proposal_separation",
            "status": "pass" if _check_passed(adaptation, "hypothesis_proposal_separation") else "blocked",
            "detail": "An improvement hypothesis is not itself an adaptation proposal.",
        },
        {
            "id": "operator_review_and_bounded_scope",
            "status": "pass"
            if _check_passed(adaptation, "operator_review_required")
            and _check_passed(adaptation, "bounded_adjustment_scope")
            else "blocked",
            "detail": "Adaptation proposals require explicit operator review and remain within allowlisted bounded adjustment scopes.",
        },
        {
            "id": "approval_authorization_execution_separation",
            "status": "pass"
            if authority_inert and _check_passed(adaptation, "approval_not_authorization")
            else "blocked",
            "detail": "Proposal review or approval grants neither authorization, application, external action, nor execution.",
        },
        {
            "id": "rollback_receipts_non_mutating",
            "status": "pass" if _check_passed(adaptation, "rollback_receipts_non_mutating") else "blocked",
            "detail": "Rollback and bounded-weight receipts preserve history without mutating behavior through this checkpoint.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, counts, scores, timestamps, and digests only.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate behavioral-learning runtime evidence.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Runtime behavioral-learning state remains outside the source tree.",
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
        "headline": "Reflective behavioral learning remains evidence-backed, uncertainty-aware, operator-reviewed, privacy-safe, read-only at inspection, and unable to authorize or execute adaptation.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "behavioral_evidence": evidence.get("summary") or {},
            "behavioral_self_evaluation": evaluation.get("summary") or {},
            "behavioral_adaptation_review": adaptation.get("summary") or {},
        },
        "checks": checks,
        "runtime_mutated": runtime_mutated,
        "runtime_external": not _inside(root, source),
        "raw_messages_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "adaptation_proposal_created": False,
        "behavior_changed": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "consciousness_claimed": False,
        "desktop_verification_status": "pending",
    }
