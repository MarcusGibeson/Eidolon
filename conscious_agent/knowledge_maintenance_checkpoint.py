from __future__ import annotations

"""Read-only checkpoint for bounded knowledge maintenance.

The checkpoint consolidates structural evidence from reconsideration scheduling,
evidence-change propagation, bounded reflection, accountable maintenance outcomes,
and reconsideration communication. It does not mutate runtime state, contact a
provider, browse, authorize or execute protected actions, promote, certify, or
claim consciousness.
"""

import os
from pathlib import Path
from typing import Any

try:
    from knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
    from knowledge_maintenance_consolidation import build_knowledge_maintenance_consolidation
except ImportError:
    from knowledge_confidence_checkpoint import build_knowledge_confidence_checkpoint
    from knowledge_maintenance_consolidation import build_knowledge_maintenance_consolidation

CHECKPOINT_CONTRACT_VERSION = "v1106.9"


def _default_runtime_root() -> Path:
    base = Path(
        os.environ.get("EIDOLON_DATA_DIR")
        or Path(__file__).resolve().parents[1] / "data"
    ).expanduser().resolve()
    return base / "cognition"


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _false(value: Any) -> bool:
    return value is False


def _authority_clear(section: dict[str, Any]) -> bool:
    boundary = section.get("authority_boundary") or {}
    return not any(
        bool(boundary.get(name))
        for name in (
            "can_authorize_action",
            "can_execute_action",
            "can_modify_files",
            "can_browse_externally",
            "can_manage_models",
            "can_bypass_quiet",
        )
    )


def build_knowledge_maintenance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a privacy-safe, read-only v1106.9 checkpoint."""

    root = (
        Path(runtime_root).expanduser().resolve()
        if runtime_root is not None
        else _default_runtime_root()
    )
    source = (
        Path(source_root).expanduser().resolve()
        if source_root is not None
        else Path(__file__).resolve().parents[1]
    )

    confidence = build_knowledge_confidence_checkpoint(root, source_root=source)
    maintenance = build_knowledge_maintenance_consolidation(root)

    schedules = maintenance.get("scheduling") or {}
    propagation = maintenance.get("propagation") or {}
    reflections = maintenance.get("reflections") or {}
    outcomes = maintenance.get("outcomes") or {}
    communication = maintenance.get("communication") or {}

    runtime_external = not _inside(root, source)
    provider_neutral = all(
        not bool(section.get("provider_contacted"))
        for section in (confidence, schedules, propagation, reflections, outcomes, communication)
    )
    browsing_absent = all(
        not bool(section.get("external_browsing_performed"))
        for section in (confidence, schedules, propagation, outcomes, communication)
    )
    hidden_reasoning_absent = (
        reflections.get("raw_chain_of_thought_stored") is False
        and propagation.get("hidden_reasoning_exposed") is False
    )
    authority_preserved = all(
        _authority_clear(section)
        for section in (schedules, propagation, reflections, outcomes, communication)
    )

    summary = {
        "scheduled_reconsideration_count": int(schedules.get("scheduled_count") or 0),
        "due_reconsideration_count": int(schedules.get("due_count") or 0),
        "completed_reconsideration_count": int(schedules.get("completed_count") or 0),
        "evidence_propagation_count": int(propagation.get("propagation_count") or 0),
        "bounded_reflection_count": int(reflections.get("reflection_count") or 0),
        "maintenance_outcome_count": int(outcomes.get("outcome_count") or 0),
        "communication_decision_count": int(communication.get("decision_count") or 0),
        "belief_reconsideration_candidate_count": int(
            (confidence.get("summary") or {}).get("reconsideration_candidate_count") or 0
        ),
        "inquiry_review_candidate_count": int(
            (confidence.get("summary") or {}).get("inquiry_review_candidate_count") or 0
        ),
    }

    checks = [
        {
            "id": "confidence_foundation",
            "status": "pass" if confidence.get("ok") is True else "blocked",
            "detail": "Knowledge confidence and reconsideration pressure remain inspectable.",
        },
        {
            "id": "scheduling_persistence",
            "status": "pass" if schedules.get("ok") is True else "blocked",
            "detail": "Reconsideration schedules are durable and structurally visible.",
        },
        {
            "id": "evidence_change_propagation",
            "status": "pass" if propagation.get("ok") is True else "blocked",
            "detail": "Evidence changes retain bounded propagation receipts.",
        },
        {
            "id": "bounded_reflection",
            "status": "pass" if reflections.get("ok") is True else "blocked",
            "detail": "At most concise authored reconsideration conclusions are retained.",
        },
        {
            "id": "deliberate_silence",
            "status": "pass" if (reflections.get("controls") or {}).get("max_reflections_per_cycle") == 1 else "blocked",
            "detail": "A cycle remains bounded to one reflection and may intentionally remain silent.",
        },
        {
            "id": "maintenance_outcomes",
            "status": "pass" if outcomes.get("ok") is True else "blocked",
            "detail": "Retain, revise, suspend, reopen, and unresolved outcomes remain accountable.",
        },
        {
            "id": "communication_continuity",
            "status": "pass" if communication.get("ok") is True else "blocked",
            "detail": "Meaningful reconsideration may use existing proactive safeguards.",
        },
        {
            "id": "provider_neutrality",
            "status": "pass" if provider_neutral else "blocked",
            "detail": "Checkpoint construction does not contact or depend on a configured provider.",
        },
        {
            "id": "external_browsing_boundary",
            "status": "pass" if browsing_absent else "blocked",
            "detail": "No maintenance layer performs external browsing.",
        },
        {
            "id": "hidden_reasoning_boundary",
            "status": "pass" if hidden_reasoning_absent else "blocked",
            "detail": "Raw chain-of-thought and provider reasoning payloads are not exposed.",
        },
        {
            "id": "action_authority_boundary",
            "status": "pass" if authority_preserved else "blocked",
            "detail": "Knowledge maintenance cannot authorize or execute protected actions.",
        },
        {
            "id": "runtime_separation",
            "status": "pass" if runtime_external else "pending_desktop",
            "detail": "Cognitive runtime state belongs outside the source tree.",
        },
        {
            "id": "release_authority_boundary",
            "status": "pass",
            "detail": "The checkpoint does not approve, promote, install, or certify a release.",
        },
        {
            "id": "epistemic_caution",
            "status": "pass",
            "detail": "Observable maintenance mechanisms do not prove consciousness.",
        },
    ]

    ready = all(row["status"] == "pass" for row in checks)
    return {
        "ok": ready,
        "status": "ready_for_desktop_verification" if ready else "pending_desktop_verification",
        "contract_version": CHECKPOINT_CONTRACT_VERSION,
        "headline": "Knowledge maintenance remains bounded, revisable, and operator-controlled.",
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "summary": summary,
        "checks": checks,
        "check_count": len(checks),
        "runtime_external": runtime_external,
        "runtime_mutated": False,
        "provider_contacted": False,
        "external_browsing_performed": False,
        "raw_prompts_exposed": False,
        "private_conversations_exposed": False,
        "provider_payloads_exposed": False,
        "hidden_reasoning_exposed": False,
        "action_authority_changed": False,
        "external_action_executed": False,
        "model_management_performed": False,
        "release_approved": False,
        "release_promoted": False,
        "release_certified": False,
        "consciousness_claimed": False,
        "desktop_verification_required": True,
    }
