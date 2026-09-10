from __future__ import annotations

"""Strictly read-only v1113.9 Bounded Inquiry and Epistemic Follow-Through checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from active_inquiry_continuity_checkpoint import build_active_inquiry_continuity_checkpoint
from inquiry_evidence_governance_checkpoint import build_inquiry_evidence_governance_checkpoint
from inquiry_resolution_checkpoint import build_inquiry_resolution_checkpoint

CONTRACT_VERSION = "v1113.9"


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


def build_bounded_inquiry_checkpoint(
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
    activation = build_active_inquiry_continuity_checkpoint(root, source_root=source)
    governance = build_inquiry_evidence_governance_checkpoint(root, source_root=source)
    resolution = build_inquiry_resolution_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (activation, governance, resolution)
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
            "external_browsing_performed",
            "provider_contacted",
            "message_sent",
            "external_action_executed",
            "belief_changed",
        )
    )

    checks = [
        {
            "id": "complete_candidate_to_resolution_lineage",
            "status": "pass" if all(report.get("ok") for report in reports) else "blocked",
            "detail": "Inquiry candidacy, activation, acquisition proposal, source review, evidence receipt, assimilation, resolution, and retirement remain separately inspectable and structurally linked.",
        },
        {
            "id": "activation_and_non_inquiry_restraint",
            "status": "pass"
            if _check_passed(activation, "activation_restraint")
            and _check_passed(activation, "missing_evidence_unknown")
            else "blocked",
            "detail": "An eligible question may remain inactive, deferred, internal-only, or awaiting naturally available evidence without being treated as successful research.",
        },
        {
            "id": "duplicate_and_overlap_suppression",
            "status": "pass"
            if _check_passed(activation, "duplicate_overlap_suppression")
            and _check_passed(governance, "proposal_duplicate_suppression")
            and _check_passed(resolution, "duplicate_suppression")
            else "blocked",
            "detail": "Retries, stale workers, duplicate proposals, receipts, assimilations, and semantically overlapping inquiries remain suppressed without erasing historical records.",
        },
        {
            "id": "resource_sensitivity_and_source_limits",
            "status": "pass"
            if _check_passed(activation, "resource_sensitivity_limits")
            and _check_passed(governance, "source_class_allowlist")
            and _check_passed(governance, "resource_sensitivity_restraint")
            else "blocked",
            "detail": "Inquiry activation and evidence proposals remain bounded by resource, sensitivity, intrusion, and allowlisted-source constraints.",
        },
        {
            "id": "operator_review_not_authorization",
            "status": "pass"
            if _check_passed(governance, "operator_confirmation")
            and _check_passed(governance, "approval_not_authorization")
            and _check_passed(resolution, "operator_confirmation")
            else "blocked",
            "detail": "Operator review may classify a proposal or resolution outcome but never authorizes acquisition, browsing, provider contact, messaging, or execution.",
        },
        {
            "id": "governed_evidence_provenance",
            "status": "pass"
            if _check_passed(resolution, "evidence_lineage")
            and _check_passed(resolution, "provenance_validation")
            else "blocked",
            "detail": "Evidence receipts preserve active-inquiry, acquisition-path, authorization-receipt, source-class, timestamp, score, and digest lineage without storing raw content.",
        },
        {
            "id": "missing_and_contradictory_evidence_handling",
            "status": "pass"
            if _check_passed(resolution, "missing_evidence_not_success")
            and _check_passed(resolution, "contradiction_preserves_uncertainty")
            else "blocked",
            "detail": "Missing evidence remains unknown, while contradictory evidence preserves uncertainty rather than being forced into resolution.",
        },
        {
            "id": "unsupported_resolution_rejected",
            "status": "pass"
            if _check_passed(resolution, "unsupported_completion_rejected")
            else "blocked",
            "detail": "An inquiry cannot be marked resolved merely because a proposal was approved, time passed, discussion continued, or confidence increased.",
        },
        {
            "id": "belief_and_authority_separation",
            "status": "pass"
            if authority_inert
            and _check_passed(resolution, "belief_separation")
            and _check_passed(resolution, "authority_separation")
            else "blocked",
            "detail": "Inquiry evidence and resolution outcomes cannot directly revise beliefs, approve actions, grant authorization, browse, contact providers, send messages, or execute external actions.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural identifiers, states, scores, timestamps, counts, and digests only, never raw messages, prompts, evidence text, provider payloads, or hidden reasoning.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate inquiry runtime state or create new proposals, receipts, decisions, or authority records.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Inquiry runtime state remains outside the source tree.",
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
        "headline": "Bounded inquiry remains curiosity-linked, evidence-governed, uncertainty-aware, operator-reviewed, privacy-safe, read-only at inspection, and unable to acquire evidence or exercise authority autonomously.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "active_inquiry_continuity": activation.get("summary") or {},
            "inquiry_evidence_governance": governance.get("summary") or {},
            "inquiry_resolution_continuity": resolution.get("summary") or {},
        },
        "checks": checks,
        "runtime_mutated": runtime_mutated,
        "runtime_external": not _inside(root, source),
        "raw_messages_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "research_proposal_created": False,
        "approval_granted": False,
        "authorization_granted": False,
        "external_browsing_performed": False,
        "provider_contacted": False,
        "user_prompted": False,
        "message_sent": False,
        "belief_changed": False,
        "external_action_executed": False,
        "consciousness_claimed": False,
        "desktop_verification_status": "pending",
    }
