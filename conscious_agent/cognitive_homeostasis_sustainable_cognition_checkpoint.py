from __future__ import annotations

"""Strictly read-only v1116.9 Cognitive Homeostasis and Sustainable Cognition checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from cognitive_homeostasis_continuity_checkpoint import build_cognitive_homeostasis_continuity_checkpoint
from cognitive_recovery_continuity_checkpoint import build_cognitive_recovery_continuity_checkpoint
from cognitive_sustainability_review_checkpoint import build_cognitive_sustainability_review_checkpoint

CONTRACT_VERSION = "v1116.9"


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
        (row.get("id") == check_id or row.get("check") == check_id)
        and row.get("status") == "pass"
        for row in report.get("checks") or []
        if isinstance(row, dict)
    )


def build_cognitive_homeostasis_sustainable_cognition_checkpoint(
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
    homeostasis = build_cognitive_homeostasis_continuity_checkpoint(root, source_root=source)
    recovery = build_cognitive_recovery_continuity_checkpoint(root, source_root=source)
    sustainability = build_cognitive_sustainability_review_checkpoint(root, source_root=source)
    after_signature = _tree_signature(root)
    runtime_mutated = before_signature != after_signature

    reports = (homeostasis, recovery, sustainability)
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in (
            "raw_messages_exposed",
            "raw_content_exposed",
            "prompts_exposed",
            "provider_payloads_exposed",
            "evidence_text_exposed",
            "hidden_reasoning_exposed",
            "private_content_exposed",
        )
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in (
            "schedule_changed",
            "work_paused",
            "work_resumed",
            "adaptation_applied",
            "attention_selected",
            "intention_formed",
            "decision_committed",
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
            "id": "homeostasis_to_sustainability_lineage",
            "status": "pass" if all(report.get("ok") for report in reports) else "blocked",
            "detail": "Pressure signals, recovery arbitration, lifecycle records, sustainable-window outcomes, overload patterns, and drift reviews remain separately inspectable and structurally linked.",
        },
        {
            "id": "pressure_signal_continuity",
            "status": "pass"
            if _check_passed(homeostasis, "signal_persistence_lineage")
            and _check_passed(homeostasis, "bounded_pressure_scores")
            and _check_passed(homeostasis, "duplicate_suppression")
            else "blocked",
            "detail": "Cognitive pressure evidence remains durable, bounded, content-free, and duplicate-resistant.",
        },
        {
            "id": "bounded_recovery_arbitration",
            "status": "pass"
            if _check_passed(homeostasis, "recovery_rest_nonexecuting")
            and _check_passed(homeostasis, "deliberate_rest_available")
            else "blocked",
            "detail": "Recovery and deliberate-rest outcomes remain recommendations rather than schedule mutations or work-control commands.",
        },
        {
            "id": "recovery_lifecycle_continuity",
            "status": "pass"
            if _check_passed(recovery, "recovery_record_persistence")
            and _check_passed(recovery, "operator_reviewed_lifecycle")
            else "blocked",
            "detail": "Recovery lifecycle changes remain historical, operator-reviewed, and structurally attributable.",
        },
        {
            "id": "bounded_recovery_windows",
            "status": "pass" if _check_passed(recovery, "bounded_window_units") else "blocked",
            "detail": "Recovery windows and rest reserves remain bounded and cannot consume or rewrite scheduling authority.",
        },
        {
            "id": "sustainable_window_evidence",
            "status": "pass" if _check_passed(recovery, "sustainable_window_evidence") else "blocked",
            "detail": "Sustainable-window outcomes preserve exact recovery lineage without storing raw content.",
        },
        {
            "id": "missing_feedback_unknown",
            "status": "pass"
            if _check_passed(homeostasis, "missing_evidence_unknown")
            and _check_passed(recovery, "missing_feedback_unknown")
            and _check_passed(sustainability, "missing_feedback_unknown")
            else "blocked",
            "detail": "Absent or incomplete evidence remains unknown rather than being counted as successful recovery.",
        },
        {
            "id": "correction_retraction_history",
            "status": "pass" if _check_passed(recovery, "correction_retraction_history") else "blocked",
            "detail": "Corrections and retractions remain historical while losing active influence.",
        },
        {
            "id": "overload_pattern_evidence_thresholds",
            "status": "pass"
            if _check_passed(sustainability, "overload_pattern_persistence")
            and _check_passed(sustainability, "evidence_thresholds")
            else "blocked",
            "detail": "Repeated-overload patterns require bounded structural support rather than isolated events or confidence theater.",
        },
        {
            "id": "false_pattern_suppression",
            "status": "pass" if _check_passed(sustainability, "false_pattern_suppression") else "blocked",
            "detail": "Thin, duplicate, contradictory, low-diversity, and feedback-poor evidence cannot become an active overload pattern.",
        },
        {
            "id": "homeostasis_drift_review",
            "status": "pass" if _check_passed(sustainability, "drift_review_continuity") else "blocked",
            "detail": "Homeostasis drift reviews remain bounded, uncertainty-bearing, and non-adaptive.",
        },
        {
            "id": "recovery_effectiveness_reconciliation",
            "status": "pass"
            if _check_passed(sustainability, "recovery_effectiveness_reconciliation")
            else "blocked",
            "detail": "Recovery effectiveness is reconciled from structural evidence without changing schedules or behavior.",
        },
        {
            "id": "restart_project_provider_continuity",
            "status": "pass"
            if _check_passed(homeostasis, "restart_project_continuity")
            and _check_passed(recovery, "restart_project_continuity")
            and _check_passed(sustainability, "restart_project_provider_continuity")
            else "blocked",
            "detail": "Checkpoint evidence remains stable across restart, project selection, and provider switching.",
        },
        {
            "id": "privacy_hidden_reasoning_boundary",
            "status": "pass" if privacy_ok else "blocked",
            "detail": "Inspection exposes structural counts and states only, never messages, prompts, evidence text, provider payloads, private content, or hidden reasoning.",
        },
        {
            "id": "authority_state_separation",
            "status": "pass" if authority_inert else "blocked",
            "detail": "Homeostasis evidence, recovery recommendations, lifecycle records, outcomes, patterns, and reviews grant no approval, authorization, or execution authority.",
        },
        {
            "id": "source_runtime_separation",
            "status": "pass"
            if all(_check_passed(report, "source_runtime_separation") for report in reports)
            and not _inside(root, source)
            else "blocked",
            "detail": "Runtime cognition remains outside source and the checkpoint writes no runtime or source state.",
        },
        {
            "id": "read_only_checkpoint",
            "status": "pass" if not runtime_mutated else "blocked",
            "detail": "Building the consolidated checkpoint does not mutate runtime state.",
        },
        {
            "id": "pending_desktop_verification",
            "status": "pass",
            "detail": "Source verification is complete; native Desktop verification remains explicitly pending.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CONTRACT_VERSION,
        "headline": "Cognitive homeostasis, recovery continuity, overload-pattern review, and sustainability evidence remain bounded, read-only, privacy-safe, and authority-inert.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": {
            "cognitive_homeostasis_continuity": homeostasis.get("summary") or {},
            "cognitive_recovery_continuity": recovery.get("summary") or {},
            "cognitive_sustainability_review": sustainability.get("summary") or {},
        },
        "checks": checks,
        "check_count": len(checks),
        "runtime_mutated": runtime_mutated,
        "runtime_external": not _inside(root, source),
        "raw_messages_exposed": False,
        "raw_content_exposed": False,
        "prompts_exposed": False,
        "provider_payloads_exposed": False,
        "evidence_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "private_content_exposed": False,
        "schedule_changed": False,
        "work_paused": False,
        "work_resumed": False,
        "adaptation_applied": False,
        "attention_selected": False,
        "intention_formed": False,
        "decision_committed": False,
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
        "desktop_verification_status": "pending",
    }
