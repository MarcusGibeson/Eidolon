from __future__ import annotations

"""Content-free ordinary-chat projection for supervised development campaigns.

This seam lets conversation recognize and explain the existing v1180-v1190
development campaign without reading private campaign records, persisting a
proposal, creating approval, executing work, or granting authority.
"""

import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1191.9"
_STAGE_CODES = (
    "inspect", "specify", "plan", "operator_review", "implement_in_sandbox",
    "test", "diagnose_or_repair", "present_result", "bounded_learning",
)
_LINEAGE_SURFACES = (
    "supervised_project_development", "persistent_development_campaign",
    "durable_campaign_continuation", "bounded_campaign_work_execution",
    "complete_campaign_development_loop", "persistent_supervised_developer_alpha",
    "unified_experience", "responsive_work_queue",
)

def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()

def build_developer_campaign_conversation_projection(
    action_projection: Mapping[str, Any],
    action_handoff: Mapping[str, Any],
    *,
    project_state: Mapping[str, Any] | None = None,
    lifecycle_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    grounding = dict(action_projection.get("grounding") or {})
    proposal = dict(action_handoff.get("proposal") or {})
    capability = str(grounding.get("capability_id") or "")
    matched = bool(grounding.get("grounding_status") == "matched" and capability == "software_development")
    proposal_ready = bool(matched and proposal.get("proposal_state") == "ready_for_operator_review")
    lifecycle = dict(lifecycle_state or {})
    persisted_proposal = dict(lifecycle.get("proposal") or {})
    lifecycle_active = bool(lifecycle.get("active"))
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "supervised_campaign_proposal_visible" if proposal_ready else "inactive",
        "capability_id": "software_development" if matched else "",
        "campaign_connected_to_conversation": matched,
        "proposal_ready_for_operator_review": proposal_ready,
        "active_project_present": bool(project_state),
        "stage_codes": list(_STAGE_CODES) if matched else [],
        "stage_count": len(_STAGE_CODES) if matched else 0,
        "lineage_surfaces": list(_LINEAGE_SURFACES) if matched else [],
        "lineage_surface_count": len(_LINEAGE_SURFACES) if matched else 0,
        "foreground_conversation_preserved": True,
        "proposal_persisted": bool(persisted_proposal),
        "proposal_id": str(persisted_proposal.get("proposal_id") or lifecycle.get("proposal_id") or ""),
        "proposal_revision": int(persisted_proposal.get("revision") or lifecycle.get("revision") or 0),
        "proposal_lifecycle_state": str(persisted_proposal.get("lifecycle_state") or lifecycle.get("status") or ""),
        "lifecycle_event": str(lifecycle.get("event") or "inactive"),
        "approval_created": bool(persisted_proposal),
        "approval_consumed": bool(persisted_proposal.get("approval_consumed") or lifecycle.get("approval_consumed_now")),
        "execution_invoked": False,
        "campaign_started": False,
        "automatic_continuation": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "source_modified": False,
        "runtime_modified": lifecycle_active,
        "content_free": True,
        "private_campaign_content_included": False,
        "authority_granted": False,
    }
    result["projection_digest"] = _digest(result)
    return result

def developer_campaign_conversation_prompt(projection: Mapping[str, Any]) -> str:
    if projection.get("campaign_connected_to_conversation"):
        return "\n".join((
            "Supervised software-development campaign surface (content-free):",
            "- The user request matches the registered proposal-only software-development capability.",
            "- Explain that the governed campaign can inspect, specify, plan, review, sandbox-implement, test, repair, present, and learn in later bounded stages.",
            "- The ordinary-chat lifecycle may have persisted one external-runtime proposal and consumed one exact revision-bound approval; follow its authoritative lifecycle response.",
            "- Do not claim implementation, provider generation, workspace creation, command execution, source mutation, model management, release promotion, or independent authority occurred.",
        ))
    return "Supervised software-development campaign surface: inactive for this turn."

def developer_campaign_conversation_public(projection: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "schema_version", "contract_version", "status", "capability_id",
        "campaign_connected_to_conversation", "proposal_ready_for_operator_review",
        "active_project_present", "stage_codes", "stage_count", "lineage_surfaces",
        "lineage_surface_count", "foreground_conversation_preserved", "proposal_persisted",
        "proposal_id", "proposal_revision", "proposal_lifecycle_state", "lifecycle_event",
        "approval_created", "approval_consumed", "execution_invoked", "campaign_started",
        "automatic_continuation", "provider_contacted", "model_contacted", "thread_started",
        "process_started", "source_modified", "runtime_modified", "content_free",
        "private_campaign_content_included", "authority_granted", "projection_digest",
    )
    return {key: projection.get(key) for key in allowed}
