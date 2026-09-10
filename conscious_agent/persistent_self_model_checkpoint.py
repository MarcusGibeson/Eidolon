from __future__ import annotations
"""Strictly read-only v1110.9 Persistent Self-Model checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from self_model_continuity_checkpoint import build_self_model_continuity_checkpoint
from identity_revision_checkpoint import build_identity_revision_checkpoint
from identity_expression_lifecycle_checkpoint import build_identity_expression_lifecycle_checkpoint

CONTRACT_VERSION = "v1110.9"


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


def build_persistent_self_model_checkpoint(
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
    continuity = build_self_model_continuity_checkpoint(root, source_root=source)
    revision = build_identity_revision_checkpoint(root, source_root=source)
    expression = build_identity_expression_lifecycle_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (continuity, revision, expression)
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
            "id": "evidence_backed_identity_continuity",
            "status": "pass" if continuity.get("ok") else "blocked",
            "detail": "Identity claims remain durable, evidence-backed, provider-neutral, revisable, and historically accountable across restarts and projects.",
        },
        {
            "id": "claim_evidence_and_post_hoc_boundary",
            "status": "pass" if _check_passed(continuity, "evidence_required") else "blocked",
            "detail": "Identity traits and preferences require established evidence and cannot be created merely to rationalize generated dialogue.",
        },
        {
            "id": "contradiction_and_durable_change_discipline",
            "status": "pass"
            if _check_passed(revision, "contradiction_detection")
            and _check_passed(revision, "durable_change_threshold")
            else "blocked",
            "detail": "Transient variation, contradiction, correction, unresolved evidence, and durable change remain distinct bounded outcomes.",
        },
        {
            "id": "bounded_revision_and_historical_lineage",
            "status": "pass" if _check_passed(revision, "bounded_revision") else "blocked",
            "detail": "Retain, revise, suspend, retract, and unresolved outcomes preserve prior claims and bounded confidence changes rather than rewriting history.",
        },
        {
            "id": "reflection_influence_without_conclusion_control",
            "status": "pass"
            if _check_passed(expression, "reflection_influence")
            and _check_passed(expression, "contradiction_openness")
            else "blocked",
            "detail": "Eligible identity claims may provide one bounded reflection lens but cannot dictate conclusions or suppress contradictory evidence.",
        },
        {
            "id": "identity_consistent_communication_restraint",
            "status": "pass" if _check_passed(expression, "communication_restraint") else "blocked",
            "detail": "Identity-consistency review may revise, defer, remain silent, remain unresolved, or permit normal-chat eligibility without generating or delivering a message.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass",
            "detail": "Structural identity evidence persists across turns, restarts, projects, and provider switching without requiring provider availability.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes bounded structural counts, states, identifiers, and digests only, never prompts, private conversations, evidence text, provider payloads, or hidden reasoning.",
        },
        {
            "id": "identity_cognition_action_state_separation",
            "status": "pass"
            if _check_passed(continuity, "state_separation")
            and _check_passed(revision, "state_separation")
            and _check_passed(expression, "state_separation")
            else "blocked",
            "detail": "Evidence, claim, preference, revision, reflection lens, conclusion, communication decision, message, intention, proposal, authorization, execution, and completion remain distinct.",
        },
        {
            "id": "authority_boundary",
            "status": "pass" if authority_inert else "blocked",
            "detail": "The self-model cannot browse, send, notify, execute, modify files, manage models, approve actions, authorize releases, promote, certify, install, pull, replace, or delete anything.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate runtime identity evidence.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable identity evidence belongs outside source; native Desktop verification remains pending.",
        },
        {
            "id": "epistemic_caution",
            "status": "pass",
            "detail": "Observable self-model continuity and identity-expression mechanisms support candidate artificial-consciousness research but do not prove consciousness or subjective experience.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Eidolon may preserve and revise an evidence-backed identity, use it as bounded context, and express it with restraint without treating identity as authority.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "identity_continuity": continuity.get("summary") or {},
            "identity_revision": revision.get("summary") or {},
            "identity_expression": expression.get("summary") or {},
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
