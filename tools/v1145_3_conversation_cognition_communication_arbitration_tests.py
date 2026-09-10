import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.conversation_cognition_communication_arbitration import (
    OUTCOMES,
    ConversationCognitionCommunicationArbitrationStore,
)
from tools.v1145_bundle_b_test_support import build_context_chain, build_workload_admission

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime" / "cognition"
    context = build_context_chain(runtime)
    workload = build_workload_admission(runtime)
    store = ConversationCognitionCommunicationArbitrationStore(runtime, clock=lambda: "2026-07-29T21:01:00Z")

    ready = store.arbitrate(
        "arbitration-event-ready",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=context["candidate_revision"],
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(ready["outcome"] == "generation_eligible" and ready["generation_eligible"])
    row = store.snapshot()["arbitrations"][0]
    require(row["candidate_structural_digest"] and row["eligibility_structural_digest"])
    require(row["workload_admitted"] and row["workload_arbitration_id"] == workload["arbitration_id"])
    require(row["provider_profile_id"] and row["communication_policy_id"] and row["privacy_policy_ids"])
    require(not row["provider_contacted"] and not row["conversation_generated"] and not row["message_sent"])

    duplicate = store.arbitrate(
        "arbitration-event-ready",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=context["candidate_revision"],
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(duplicate["idempotent"] and len(store.snapshot()["arbitrations"]) == 1)

    silence_context = build_context_chain(runtime, suffix="silence")
    silence = store.arbitrate(
        "arbitration-event-silence",
        candidate_id=silence_context["candidate_id"],
        observed_candidate_revision=silence_context["candidate_revision"],
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=False,
        communication_score=0.1,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(silence["outcome"] == "deliberate_silence" and not silence["generation_eligible"])

    current_revision = store.candidates.snapshot()["revision"]
    stale = store.arbitrate(
        "arbitration-event-stale",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision - 1,
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(stale["outcome"] == "reject_stale_context")

    provider_defer = store.arbitrate(
        "arbitration-event-provider",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision,
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=False,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(provider_defer["outcome"] == "defer_for_provider")

    workload_defer = store.arbitrate(
        "arbitration-event-workload",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision,
        workload_arbitration_id="missing-workload",
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(workload_defer["outcome"] == "defer_for_workload")

    privacy = store.arbitrate(
        "arbitration-event-privacy",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision,
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=False,
        communication_policy_allows=True,
    )
    require(privacy["outcome"] == "reject_privacy")

    policy = store.arbitrate(
        "arbitration-event-policy",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision,
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=False,
    )
    require(policy["outcome"] == "reject_policy")

    cancelled = store.arbitrate(
        "arbitration-event-cancelled",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=current_revision,
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
        cancellation_requested=True,
    )
    require(cancelled["outcome"] == "cancelled_before_generation")

    review_context = build_context_chain(runtime, operator_review_required=True, suffix="review")
    review = store.arbitrate(
        "arbitration-event-review",
        candidate_id=review_context["candidate_id"],
        observed_candidate_revision=review_context["candidate_revision"],
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.8,
        confidence=0.8,
        uncertainty=0.2,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    require(review["outcome"] == "defer_for_operator_review")

    inspection = store.inspection_summary()
    require(inspection["contract_version"] == "v1145.3")
    require(set(inspection["recognized_outcomes"]) == OUTCOMES)
    require(inspection["deterministic_arbitration"] and inspection["silence_is_valid_outcome"])
    require(not inspection["arbitration_is_execution_authority"])
    require(not any(inspection["authority_boundary"].values()))
    require(not inspection["raw_conversation_exposed"] and not inspection["prompt_exposed"] and not inspection["hidden_reasoning_exposed"])
    require(not inspection["provider_contacted"] and not inspection["conversation_generated"] and not inspection["message_sent"])
    require(all(row["structural_digest"] for row in inspection["recent_records"]))
    require(all(row["silence_eligible"] for row in inspection["recent_records"]))

print(json.dumps({"passed": passed, "total": 23, "suite": "v1145.3"}))
