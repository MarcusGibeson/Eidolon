import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.unified_context_candidates import UnifiedContextCandidateStore
from conscious_agent.unified_conversational_context_eligibility import (
    REQUIRED_CONTEXT_CATEGORIES,
    UnifiedConversationalContextEligibilityStore,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


def source(category: str, token: str, *, temporal: str = "current", lifecycle: str = "active", eligible: bool = True, privacy: str = "internal") -> dict:
    return {
        "source_category": category,
        "source_id": token,
        "source_revision": 2,
        "source_digest": (token[0] if token and token[0] in "abcdef" else "b") * 64,
        "temporal_status": temporal,
        "relevance_category": "immediate" if temporal == "current" else "background",
        "relevance_score": 0.8,
        "confidence": 0.75,
        "uncertainty": 0.25,
        "recorded_at": "2026-07-29T16:00:00Z",
        "expires_at": "2026-07-30T16:00:00Z",
        "privacy_class": privacy,
        "communication_eligible": eligible,
        "required_exclusion": False,
        "operator_review_required": False,
        "lifecycle_state": lifecycle,
        "session_id": "session-1",
        "conversation_id": "conversation-1",
        "relationship_boundary": "relationship_only" if category == "relationship_context" else "",
    }


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime" / "cognition"
    eligibility_store = UnifiedConversationalContextEligibilityStore(runtime, clock=lambda: "2026-07-29T17:00:00Z")
    refs = [source("active_thought", "a-thought"), source("memory_reference", "c-memory", temporal="historical")]
    refs += [source(category, f"b-{category}") for category in sorted(REQUIRED_CONTEXT_CATEGORIES)]
    refs += [source("operator_correction", "d-correction", temporal="historical", lifecycle="retracted")]
    eligibility = eligibility_store.register(
        "eligibility-event",
        assembly_id="assembly-1",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-1",
        worker_claim_id="worker-1",
        worker_epoch=1,
        current_worker_epoch=1,
        retry_token_id="retry-1",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 120, "memory_budget_mb": 256, "latency_budget_ms": 600, "token_budget": 800},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T19:00:00Z",
    )
    require(eligibility["state"] == "eligible")
    row = eligibility_store.snapshot()["records"][0]
    included = list(reversed(row["eligible_source_ids"]))
    provider_id = next(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "provider_state" and item["included"])
    communication_id = next(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "communication_policy" and item["included"])
    privacy_ids = sorted(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "privacy_policy" and item["included"])

    candidates = UnifiedContextCandidateStore(runtime, clock=lambda: "2026-07-29T17:01:00Z")
    result = candidates.register(
        "candidate-event",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope",
        included_source_ids=included,
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-1",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(result["state"] == "candidate_ready")
    candidate = candidates.snapshot()["candidates"][0]
    require(candidate["relevance_order"] == row["eligible_source_ids"])
    require(set(candidate["included_source_ids"]) <= set(row["eligible_source_ids"]))
    require(candidate["provider_profile_id"] == provider_id and candidate["communication_policy_id"] == communication_id)
    require(candidate["silence_eligible"] and all(value > 0 for value in candidate["budget_limits"].values()))
    require("d-correction" in candidate["lifecycle_lineage"]["correction_source_ids"] and "d-correction" in candidate["lifecycle_lineage"]["retracted_source_ids"])
    require("d-correction" not in candidate["included_source_ids"])
    require(all(item["content_free"] for item in candidate["included_source_lineage"] + candidate["excluded_source_lineage"]))
    require(not candidate["provider_contacted"] and not candidate["conversation_generated"] and not candidate["message_sent"])

    duplicate = candidates.register(
        "candidate-event-2",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope",
        included_source_ids=row["eligible_source_ids"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-1",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(duplicate["status"] == "duplicate_candidate_suppressed")

    broadened = candidates.register(
        "candidate-event-3",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope-3",
        included_source_ids=row["eligible_source_ids"] + ["not-eligible"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-3",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(broadened["state"] == "suppressed")

    budget_broadened = candidates.register(
        "candidate-event-4",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope-4",
        included_source_ids=row["eligible_source_ids"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-4",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 999, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(budget_broadened["state"] == "suppressed")

    no_cognition = [item for item in row["eligible_source_ids"] if item != "a-thought" and item != "c-memory"]
    silence = candidates.register(
        "candidate-event-5",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope-5",
        included_source_ids=no_cognition,
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-5",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(silence["state"] == "silence_only")

    no_silence = candidates.register(
        "candidate-event-6",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope-6",
        included_source_ids=row["eligible_source_ids"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-6",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=False,
    )
    require(no_silence["state"] == "suppressed")

    inspection = candidates.inspection_summary()
    require(inspection["contract_version"] == "v1145.1")
    require(inspection["deterministic_construction"] and not inspection["eligible_set_broadening_allowed"])
    require(inspection["silence_is_valid_outcome"])
    require(not any(inspection["authority_boundary"].values()))
    require(not inspection["raw_conversation_exposed"] and not inspection["hidden_reasoning_exposed"])
    require(not inspection["provider_contacted"] and not inspection["provider_context_assembled"] and not inspection["message_sent"])

print(json.dumps({"passed": passed, "total": 21, "suite": "v1145.1"}))
