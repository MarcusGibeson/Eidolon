from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from conscious_agent.unified_conversational_context_eligibility import (
    REQUIRED_CONTEXT_CATEGORIES,
    UnifiedConversationalContextEligibilityStore,
)
from conscious_agent.unified_context_candidates import UnifiedContextCandidateStore
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore

CLOCK = "2026-07-29T21:00:00Z"
BUDGETS = {
    "cpu_budget_ms": 250,
    "memory_budget_mb": 128,
    "latency_budget_ms": 500,
    "token_budget": 512,
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source(
    category: str,
    token: str,
    *,
    content: str | None = None,
    temporal: str = "current",
    privacy: str = "internal",
    eligible: bool = True,
    lifecycle: str = "active",
    relationship_boundary: str = "",
    operator_review_required: bool = False,
) -> dict[str, Any]:
    material = content if content is not None else f"{category}:{token}"
    return {
        "source_category": category,
        "source_id": token,
        "source_revision": 1,
        "source_digest": digest(material),
        "temporal_status": temporal,
        "relevance_category": "immediate" if temporal == "current" else "background",
        "relevance_score": 0.9,
        "confidence": 0.8,
        "uncertainty": 0.2,
        "recorded_at": "2026-07-29T20:00:00Z",
        "expires_at": "2026-07-30T20:00:00Z",
        "privacy_class": privacy,
        "communication_eligible": eligible,
        "required_exclusion": False,
        "operator_review_required": operator_review_required,
        "lifecycle_state": lifecycle,
        "session_id": "session-b",
        "conversation_id": "conversation-b",
        "relationship_boundary": relationship_boundary,
        "_fixture_content": material,
    }


def build_context_chain(
    runtime: Path,
    *,
    silence_only: bool = False,
    operator_review_required: bool = False,
    suffix: str = "main",
) -> dict[str, Any]:
    refs = [source("active_thought", f"thought-{suffix}", content=f"A{suffix}")]
    for index, category in enumerate(sorted(REQUIRED_CONTEXT_CATEGORIES)):
        refs.append(source(category, f"{category}-{suffix}-{index}", content=f"B{suffix}{index}"))
    contents = {row["source_id"]: row.pop("_fixture_content") for row in refs}
    eligibility_store = UnifiedConversationalContextEligibilityStore(runtime, clock=lambda: CLOCK)
    eligibility_result = eligibility_store.register(
        f"eligibility-event-{suffix}",
        assembly_id=f"assembly-{suffix}",
        session_id="session-b",
        conversation_id="conversation-b",
        tab_id=f"tab-{suffix}",
        worker_claim_id=f"worker-{suffix}",
        worker_epoch=2,
        current_worker_epoch=2,
        retry_token_id=f"retry-{suffix}",
        source_references=refs,
        budget_limits=BUDGETS,
        reference_time=CLOCK,
        expiry_at="2026-07-29T22:00:00Z",
    )
    eligibility_row = next(
        row
        for row in eligibility_store.snapshot()["records"]
        if row["eligibility_id"] == eligibility_result["eligibility_id"]
    )
    provider_id = next(
        row["source_id"]
        for row in eligibility_row["source_lineage"]
        if row["source_category"] == "provider_state"
    )
    communication_id = next(
        row["source_id"]
        for row in eligibility_row["source_lineage"]
        if row["source_category"] == "communication_policy"
    )
    privacy_ids = sorted(
        row["source_id"]
        for row in eligibility_row["source_lineage"]
        if row["source_category"] == "privacy_policy"
    )
    candidate_store = UnifiedContextCandidateStore(runtime, clock=lambda: CLOCK)
    candidate_result = candidate_store.register(
        f"candidate-event-{suffix}",
        eligibility_id=eligibility_result["eligibility_id"],
        candidate_scope_id=f"scope-{suffix}",
        included_source_ids=[] if silence_only else eligibility_row["eligible_source_ids"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id=f"window-{suffix}",
        window_start=CLOCK,
        window_end="2026-07-29T22:00:00Z",
        budget_limits=BUDGETS,
        silence_eligible=True,
        operator_review_required=operator_review_required,
    )
    return {
        "eligibility_id": eligibility_result["eligibility_id"],
        "candidate_id": candidate_result["candidate_id"],
        "candidate_revision": candidate_store.snapshot()["revision"],
        "provider_profile_id": provider_id,
        "provider_profile_digest": next(
            row["source_digest"]
            for row in eligibility_row["source_lineage"]
            if row["source_id"] == provider_id
        ),
        "contents": contents,
        "budgets": dict(BUDGETS),
    }


def build_workload_admission(runtime: Path, *, suffix: str = "main", budgets: dict[str, int] | None = None) -> dict[str, Any]:
    limits = dict(budgets or BUDGETS)
    eligibility_store = WorkloadBudgetEligibilityStore(runtime, clock=lambda: CLOCK)
    eligibility = eligibility_store.register(
        f"workload-eligibility-event-{suffix}",
        workload_id=f"conversation-workload-{suffix}",
        workload_kind="conversation",
        owner_id=f"conversation-owner-{suffix}",
        project_digest=digest(f"project-{suffix}"),
        scope_digest=digest(f"scope-{suffix}"),
        priority=70,
        cpu_budget_ms=limits["cpu_budget_ms"],
        memory_budget_mb=limits["memory_budget_mb"],
        latency_budget_ms=limits["latency_budget_ms"],
        token_budget=limits["token_budget"],
    )
    candidate_store = WorkloadCoordinationCandidateStore(runtime, clock=lambda: CLOCK)
    candidate = candidate_store.register(
        f"workload-candidate-event-{suffix}",
        eligibility_id=eligibility["eligibility_id"],
        coordination_action="admit",
        coordination_group_id=f"conversation-group-{suffix}",
    )
    arbitration_store = WorkloadLiveArbitrationStore(runtime, clock=lambda: CLOCK)
    arbitration = arbitration_store.arbitrate(
        f"workload-arbitration-event-{suffix}",
        candidate_id=candidate["candidate_id"],
        observed_candidate_revision=candidate_store.snapshot()["revision"],
        available_cpu_ms=limits["cpu_budget_ms"],
        available_memory_mb=limits["memory_budget_mb"],
        available_latency_ms=limits["latency_budget_ms"],
        available_tokens=limits["token_budget"],
    )
    return {
        "arbitration_id": arbitration["arbitration_id"],
        "state": arbitration["state"],
    }
