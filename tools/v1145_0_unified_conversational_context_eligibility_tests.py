import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.unified_conversational_context_eligibility import (
    REQUIRED_CONTEXT_CATEGORIES,
    SOURCE_CATEGORIES,
    UnifiedConversationalContextEligibilityStore,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


def source(category: str, token: str, *, temporal: str = "current", privacy: str = "internal", eligible: bool = True, lifecycle: str = "active", relationship_boundary: str = "") -> dict:
    return {
        "source_category": category,
        "source_id": token,
        "source_revision": 1,
        "source_digest": (token[0] if token and token[0] in "abcdef" else "a") * 64,
        "temporal_status": temporal,
        "relevance_category": "immediate" if temporal == "current" else "background",
        "relevance_score": 0.9,
        "confidence": 0.8,
        "uncertainty": 0.2,
        "recorded_at": "2026-07-29T16:00:00Z",
        "expires_at": "2026-07-30T16:00:00Z",
        "privacy_class": privacy,
        "communication_eligible": eligible,
        "required_exclusion": False,
        "operator_review_required": False,
        "lifecycle_state": lifecycle,
        "session_id": "session-1",
        "conversation_id": "conversation-1",
        "relationship_boundary": relationship_boundary,
    }


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime" / "cognition"
    store = UnifiedConversationalContextEligibilityStore(runtime, clock=lambda: "2026-07-29T17:00:00Z")
    refs = [source("active_thought", "a-thought")]
    for index, category in enumerate(sorted(REQUIRED_CONTEXT_CATEGORIES)):
        refs.append(source(category, f"b-{index}-{category}"))
    refs.append(source("memory_reference", "c-memory", temporal="historical"))
    refs.append(source("relationship_context", "d-relationship", relationship_boundary="relationship_only"))
    refs.append(source("mood_state", "e-mood", privacy="private"))
    result = store.register(
        "event-1",
        assembly_id="assembly-1",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-1",
        worker_claim_id="worker-1",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-1",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(result["state"] == "eligible")
    row = store.snapshot()["records"][0]
    require(set(REQUIRED_CONTEXT_CATEGORIES) <= set(row["included_categories"]))
    require("e-mood" in row["excluded_source_ids"] and "mood_state" in row["excluded_categories"])
    require("a-thought" in row["current_source_ids"] and "c-memory" in row["historical_source_ids"])
    require(all(item["lineage_digest"] and item["content_free"] for item in row["source_lineage"]))
    require(row["communication_eligible"] and not row["provider_contacted"] and not row["message_sent"])
    require(all(value > 0 for value in row["budget_limits"].values()))

    repeated = store.register(
        "event-1",
        assembly_id="assembly-1",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-1",
        worker_claim_id="worker-1",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-1",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(repeated["idempotent"] and len(store.snapshot()["records"]) == 1)

    retry = store.register(
        "event-2",
        assembly_id="assembly-2",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-1",
        worker_claim_id="worker-1",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-1",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(retry["status"] == "duplicate_retry_suppressed")

    cross_tab = store.register(
        "event-3",
        assembly_id="assembly-3",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-2",
        worker_claim_id="worker-2",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-3",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(cross_tab["status"] == "cross_tab_duplicate_suppressed")

    stale = store.register(
        "event-4",
        assembly_id="assembly-4",
        session_id="session-2",
        conversation_id="conversation-2",
        tab_id="tab-4",
        worker_claim_id="worker-4",
        worker_epoch=3,
        current_worker_epoch=4,
        retry_token_id="retry-4",
        source_references=[{**item, "session_id": "session-2", "conversation_id": "conversation-2"} for item in refs],
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(stale["state"] == "stale_worker")

    private_required = [source("active_thought", "a-private-thought")]
    for index, category in enumerate(sorted(REQUIRED_CONTEXT_CATEGORIES)):
        private_required.append(source(category, f"b-private-{index}", privacy="private" if category == "communication_policy" else "internal"))
    blocked = store.register(
        "event-5",
        assembly_id="assembly-5",
        session_id="session-1",
        conversation_id="conversation-1",
        tab_id="tab-5",
        worker_claim_id="worker-5",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-5",
        source_references=private_required,
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(blocked["state"] == "awaiting_required_lineage")

    contradictory = refs + [{**refs[0], "source_digest": "f" * 64}]
    contradicted = store.register(
        "event-6",
        assembly_id="assembly-6",
        session_id="session-3",
        conversation_id="conversation-3",
        tab_id="tab-6",
        worker_claim_id="worker-6",
        worker_epoch=4,
        current_worker_epoch=4,
        retry_token_id="retry-6",
        source_references=[{**item, "session_id": "session-3", "conversation_id": "conversation-3"} for item in contradictory],
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T18:00:00Z",
    )
    require(contradicted["state"] == "suppressed")

    try:
        store.register(
            "event-raw",
            assembly_id="assembly-raw",
            session_id="session-raw",
            conversation_id="conversation-raw",
            tab_id="tab-raw",
            worker_claim_id="worker-raw",
            worker_epoch=1,
            current_worker_epoch=1,
            retry_token_id="retry-raw",
            source_references=[{**source("active_thought", "a-raw"), "text": "forbidden"}],
            budget_limits={"cpu_budget_ms": 1, "memory_budget_mb": 1, "latency_budget_ms": 1, "token_budget": 1},
            reference_time="2026-07-29T17:00:00Z",
            expiry_at="2026-07-29T18:00:00Z",
        )
    except ValueError:
        raw_rejected = True
    else:
        raw_rejected = False
    require(raw_rejected)

    inspection = store.inspection_summary()
    require(inspection["contract_version"] == "v1145.0")
    require(set(inspection["recognized_source_categories"]) == SOURCE_CATEGORIES)
    require(all(inspection["suppression_controls"].values()))
    require(not any(inspection["authority_boundary"].values()))
    require(not inspection["raw_conversation_exposed"] and not inspection["hidden_reasoning_exposed"])
    require(not inspection["provider_contacted"] and not inspection["conversation_generated"] and not inspection["message_sent"])

print(json.dumps({"passed": passed, "total": 20, "suite": "v1145.0"}))
