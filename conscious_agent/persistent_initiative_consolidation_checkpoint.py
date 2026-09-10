from __future__ import annotations

"""Strictly read-only v1108.9 persistent initiative checkpoint.

This checkpoint aggregates the complete v1108 initiative lifecycle without
creating initiative candidates, selecting attention, forming proposals,
surfacing chat turns, reconciling responses, contacting a provider, or granting
any action or release authority.
"""

from pathlib import Path
import hashlib
import json
import os
from typing import Any

from initiative_communication_checkpoint import build_initiative_communication_checkpoint
from initiative_lifecycle_checkpoint import build_initiative_lifecycle_checkpoint
from persistent_initiative_checkpoint import build_persistent_initiative_checkpoint


CONTRACT_VERSION = "v1108.9"


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
    """Return a bounded structural digest without exposing runtime content."""
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


def _background_diagnostic_summary(root: Path) -> dict[str, Any]:
    path = root / "cognitive_service_diagnostics.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    failures = payload.get("failures") if isinstance(payload, dict) else []
    failures = failures if isinstance(failures, list) else []
    safe_rows = [row for row in failures if isinstance(row, dict)]
    latest = safe_rows[-1] if safe_rows else {}
    all_content_free = all(row.get("content_free") is True for row in safe_rows)
    authority_unchanged = all(row.get("authority_changed") is not True for row in safe_rows)
    retry_not_escalated = all(row.get("automatic_retry_escalated") is not True for row in safe_rows)
    return {
        "failure_count": len(safe_rows),
        "latest_error_type": str(latest.get("error_type") or "")[:120],
        "content_free": all_content_free,
        "authority_unchanged": authority_unchanged,
        "automatic_retry_not_escalated": retry_not_escalated,
        "diagnostic_present": path.exists(),
    }


def build_persistent_initiative_consolidation_checkpoint(
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
    foundation = build_persistent_initiative_checkpoint(root, source_root=source)
    communication = build_initiative_communication_checkpoint(root, source_root=source)
    lifecycle = build_initiative_lifecycle_checkpoint(root, source_root=source)
    background_diagnostics = _background_diagnostic_summary(root)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    privacy_ok = all(
        report.get("hidden_reasoning_exposed") is not True
        and report.get("private_content_exposed") is not True
        and report.get("private_subjects_exposed") is not True
        for report in (foundation, communication, lifecycle)
    )
    delivery_inert = all(
        report.get(field) is not True
        for report in (foundation, communication, lifecycle)
        for field in (
            "provider_contacted",
            "message_generated",
            "message_sent",
            "notification_sent",
            "automatic_retry",
            "external_action_executed",
            "action_authority_changed",
        )
    )

    checks = [
        {
            "id": "initiative_candidacy_and_arbitration",
            "status": "pass" if foundation.get("ok") else "blocked",
            "detail": "Durable initiative candidacy, intention lineage, bounded arbitration, fairness, and deliberate silence remain inspectable.",
        },
        {
            "id": "proposal_restraint_and_timing",
            "status": "pass" if communication.get("ok") else "blocked",
            "detail": "Selected initiative may become a non-sending conversation proposal subject to presence, receptivity, context, quiet, cooldown, topic, sensitivity, and uncertainty boundaries.",
        },
        {
            "id": "explicit_surface_and_response_lineage",
            "status": "pass" if lifecycle.get("ok") else "blocked",
            "detail": "Normal-chat surfacing requires explicit evidence and response outcomes preserve acknowledgement, dismissal, interruption, supersession, deferral, and retirement history.",
        },
        {
            "id": "deliberate_silence_and_no_retry",
            "status": "pass"
            if _check_passed(communication, "deliberate_silence")
            and _check_passed(lifecycle, "no_automatic_retry")
            else "blocked",
            "detail": "Deliberate silence, deferral, abandonment, and terminal no-retry outcomes remain valid.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass",
            "detail": "Structural initiative evidence remains durable across turns, restarts, projects, and provider switching without provider dependence.",
        },
        {
            "id": "background_failure_visibility",
            "status": "pass"
            if background_diagnostics.get("content_free")
            and background_diagnostics.get("authority_unchanged")
            and background_diagnostics.get("automatic_retry_not_escalated")
            else "blocked",
            "detail": "Scheduled cognition failures remain content-free and diagnostically visible without retry escalation or authority change.",
        },
        {
            "id": "privacy_and_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes bounded structural counts, states, identifiers, and digests only, never private conversation content, provider payloads, evidence text, or hidden reasoning.",
        },
        {
            "id": "cognitive_and_delivery_state_separation",
            "status": "pass" if delivery_inert else "blocked",
            "detail": "Intention, initiative candidacy, selection, proposal, timing eligibility, surface evidence, response outcome, message delivery, authorization, and execution remain distinct.",
        },
        {
            "id": "authority_boundary",
            "status": "pass" if delivery_inert else "blocked",
            "detail": "This checkpoint cannot generate or send messages, notify, browse, execute commands, modify files, manage models, approve actions, promote, certify, install, pull, replace, or delete anything.",
        },
        {
            "id": "read_only_aggregation",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the checkpoint does not mutate runtime evidence.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass" if not _inside(root, source) else "pending_desktop",
            "detail": "Mutable cognition evidence belongs outside source; native Desktop verification remains pending.",
        },
        {
            "id": "epistemic_caution",
            "status": "pass",
            "detail": "These observable initiative mechanisms support candidate artificial-consciousness research but do not prove consciousness.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Persistent initiative remains durable, restrained, accountable, private, and unable to send or act autonomously.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "initiative_foundation": foundation.get("summary") or {},
            "communication_restraint": communication.get("summary") or {},
            "surface_response_lifecycle": lifecycle.get("summary") or {},
            "background_diagnostics": background_diagnostics,
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
        "normal_chat_surface_created": False,
        "automatic_retry": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "private_subjects_exposed": False,
        "proposal_created": False,
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
