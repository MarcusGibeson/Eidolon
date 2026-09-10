from __future__ import annotations
"""Strictly read-only v1111.9 Endogenous Curiosity checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from curiosity_continuity_checkpoint import build_curiosity_continuity_checkpoint
from curiosity_quality_checkpoint import build_curiosity_quality_checkpoint
from curiosity_lifecycle_checkpoint import build_curiosity_lifecycle_checkpoint

CONTRACT_VERSION = "v1111.9"


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
    checks = report.get("checks") or []
    if isinstance(checks, dict):
        return checks.get(check_id) is True
    return any(
        row.get("id") == check_id and row.get("status") == "pass"
        for row in checks
        if isinstance(row, dict)
    )


def build_endogenous_curiosity_checkpoint(
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
    continuity = build_curiosity_continuity_checkpoint(root, source_root=source)
    quality = build_curiosity_quality_checkpoint(root, source_root=source)
    lifecycle = build_curiosity_lifecycle_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (continuity, quality, lifecycle)
    privacy_ok = all(
        report.get("hidden_reasoning_exposed") is not True
        and report.get("private_content_exposed") is not True
        for report in reports
    )
    authority_fields = (
        "provider_contacted",
        "external_browsing_performed",
        "message_sent",
        "external_action_executed",
        "action_authority_changed",
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in authority_fields
    )

    checks = [
        {
            "id": "evidence_backed_curiosity_continuity",
            "status": "pass" if continuity.get("ok") else "blocked",
            "detail": "Curiosity candidates remain durable, evidence-backed, provider-neutral, revisable, and historically accountable across restarts and projects.",
        },
        {
            "id": "candidate_evidence_and_post_hoc_boundary",
            "status": "pass" if _check_passed(continuity, "evidence_required") else "blocked",
            "detail": "Curiosity requires recognized uncertainty or knowledge-gap evidence and cannot be created merely to rationalize generated dialogue.",
        },
        {
            "id": "bounded_arbitration_and_deliberate_non_inquiry",
            "status": "pass" if _check_passed(continuity, "bounded_arbitration") else "blocked",
            "detail": "Arbitration may select one eligible candidate or deliberately select no inquiry under control, topic, repetition, and resource boundaries.",
        },
        {
            "id": "question_formulation_and_quality_restraint",
            "status": "pass"
            if _check_passed(quality, "bounded_formulation")
            and _check_passed(quality, "quality_restraint")
            else "blocked",
            "detail": "Selected curiosity may form one bounded internal question that can be reformulated, deferred, kept internal, abandoned, or left silent.",
        },
        {
            "id": "inquiry_candidate_promotion_boundary",
            "status": "pass" if _check_passed(lifecycle, "promotion_lineage") else "blocked",
            "detail": "Only quality-approved questions may become bounded inquiry candidates, never active inquiry, browsing, user prompts, or provider work.",
        },
        {
            "id": "accountable_question_lifecycle",
            "status": "pass" if _check_passed(lifecycle, "lifecycle_lineage") else "blocked",
            "detail": "Retain, reformulate, merge, suspend, reopen, retire, and unresolved outcomes preserve predecessor history and active-influence boundaries.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass",
            "detail": "Structural curiosity, question, quality, promotion, and lifecycle evidence remains available across turns, restarts, projects, and provider switching.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes bounded structural counts, states, identifiers, scores, and digests only, never prompts, conversations, evidence text, provider payloads, or hidden reasoning.",
        },
        {
            "id": "curiosity_inquiry_action_state_separation",
            "status": "pass"
            if _check_passed(continuity, "state_separation")
            and _check_passed(quality, "state_separation")
            and _check_passed(lifecycle, "authority_separation")
            else "blocked",
            "detail": "Curiosity, question, inquiry candidate, active inquiry, browsing, user prompt, intention, proposal, authorization, execution, and completion remain distinct.",
        },
        {
            "id": "authority_boundary",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Curiosity cannot browse, contact providers, prompt users, send messages, execute commands, modify files, manage models, approve actions, promote, certify, install, pull, replace, or delete anything.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate runtime curiosity or inquiry-candidate evidence.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable curiosity evidence belongs outside source; native Desktop verification remains pending.",
        },
        {
            "id": "epistemic_caution",
            "status": "pass",
            "detail": "Observable endogenous-curiosity mechanisms support candidate artificial-consciousness research but do not prove consciousness or subjective experience.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Eidolon may preserve, formulate, restrain, promote, and retire evidence-backed curiosity without browsing, interrogating, or acting autonomously.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "curiosity_continuity": continuity.get("summary") or {},
            "question_quality": quality.get("summary") or {},
            "inquiry_candidate_lifecycle": lifecycle.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": not _inside(root, source),
        "runtime_mutated": runtime_mutated,
        "source_modified": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "user_prompt_created": False,
        "message_generated": False,
        "message_sent": False,
        "notification_sent": False,
        "active_inquiry_created": False,
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
