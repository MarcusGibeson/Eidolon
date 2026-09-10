import json
from pathlib import Path
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.conversation_cognition_bounded_generation import (
    STATES,
    ConversationCognitionBoundedGenerationStore,
)
from conscious_agent.conversation_cognition_communication_arbitration import (
    ConversationCognitionCommunicationArbitrationStore,
)
from tools.v1145_bundle_b_test_support import build_context_chain, build_workload_admission

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


class StubProvider:
    def __init__(self, profile_id: str, profile_digest: str, mode: str = "complete") -> None:
        self.profile_id = profile_id
        self.profile_digest = profile_digest
        self.mode = mode
        self.calls = 0
        self.started = threading.Event()

    def generate(self, prompt: str, *, cancel_event: threading.Event, max_tokens: int, timeout_ms: int) -> str:
        self.calls += 1
        self.started.set()
        if self.mode == "complete":
            return "R" * min(24, max_tokens)
        if self.mode == "large":
            return "L" * 5000
        if self.mode in {"timeout", "cancel"}:
            deadline = time.monotonic() + 2
            while not cancel_event.is_set() and time.monotonic() < deadline:
                time.sleep(0.002)
            raise RuntimeError("cancelled")
        if self.mode == "failed":
            raise RuntimeError("provider-failed")
        return ""


def setup(runtime: Path, suffix: str = "main"):
    context = build_context_chain(runtime, suffix=suffix)
    workload = build_workload_admission(runtime, suffix=suffix)
    arbitration_store = ConversationCognitionCommunicationArbitrationStore(runtime, clock=lambda: "2026-07-29T21:01:00Z")
    arbitration = arbitration_store.arbitrate(
        f"communication-arbitration-{suffix}",
        candidate_id=context["candidate_id"],
        observed_candidate_revision=context["candidate_revision"],
        workload_arbitration_id=workload["arbitration_id"],
        communication_requested=True,
        communication_score=0.9,
        confidence=0.85,
        uncertainty=0.15,
        provider_available=True,
        privacy_clear=True,
        communication_policy_allows=True,
    )
    return context, arbitration_store, arbitration


with tempfile.TemporaryDirectory() as td:
    base = Path(td)

    runtime = base / "complete" / "cognition"
    context, arbitration_store, arbitration = setup(runtime, "complete")
    provider = StubProvider(context["provider_profile_id"], context["provider_profile_digest"])
    generation = ConversationCognitionBoundedGenerationStore(runtime, clock=lambda: "2026-07-29T21:02:00Z")
    completed = generation.execute(
        "generation-event-complete",
        operation_id="generation-operation-complete",
        arbitration_id=arbitration["arbitration_id"],
        observed_arbitration_revision=arbitration_store.snapshot()["revision"],
        worker_claim_id="generation-worker-complete",
        worker_epoch=3,
        current_worker_epoch=3,
        source_resolver=context["contents"],
        provider=provider,
        maximum_output_tokens=64,
        timeout_ms=200,
    )
    require(completed["state"] == "completed" and completed["generated_text"] and provider.calls == 1)
    receipt = generation.snapshot()["receipts"][0]
    require(receipt["context_assembled"] and receipt["provider_contacted"] and receipt["generation_completed"])
    require(receipt["prompt_digest"] and receipt["response_digest"] and receipt["source_lineage_digest"])
    require(receipt["input_token_estimate"] + receipt["output_token_estimate"] <= receipt["budget_limits"]["token_budget"])
    require(receipt["workload_continuity_id"] and receipt["workload_continuity_state"] == "completed")
    require(not receipt["message_sent"] and not receipt["generated_output_committed"] and not receipt["conversation_mutated"])

    replay = generation.execute(
        "generation-event-complete",
        operation_id="generation-operation-complete",
        arbitration_id=arbitration["arbitration_id"],
        observed_arbitration_revision=arbitration_store.snapshot()["revision"],
        worker_claim_id="generation-worker-complete",
        worker_epoch=3,
        current_worker_epoch=3,
        source_resolver=context["contents"],
        provider=provider,
        maximum_output_tokens=64,
        timeout_ms=200,
    )
    require(replay["idempotent"] and replay["state"] == "completed" and replay["generated_text"] == "" and provider.calls == 1)

    second = generation.execute(
        "generation-event-duplicate",
        operation_id="generation-operation-duplicate",
        arbitration_id=arbitration["arbitration_id"],
        observed_arbitration_revision=arbitration_store.snapshot()["revision"],
        worker_claim_id="generation-worker-duplicate",
        worker_epoch=3,
        current_worker_epoch=3,
        source_resolver=context["contents"],
        provider=provider,
        maximum_output_tokens=64,
        timeout_ms=200,
    )
    require(second["state"] == "duplicate_suppressed" and provider.calls == 1)

    runtime_bad_context = base / "bad-context" / "cognition"
    context_bad, arbitration_store_bad, arbitration_bad = setup(runtime_bad_context, "bad-context")
    bad_provider = StubProvider(context_bad["provider_profile_id"], context_bad["provider_profile_digest"])
    bad_generation = ConversationCognitionBoundedGenerationStore(runtime_bad_context)
    bad_contents = dict(context_bad["contents"])
    first_key = next(iter(bad_contents))
    bad_contents[first_key] = bad_contents[first_key] + "X"
    rejected = bad_generation.execute(
        "generation-event-bad-context",
        operation_id="generation-operation-bad-context",
        arbitration_id=arbitration_bad["arbitration_id"],
        observed_arbitration_revision=arbitration_store_bad.snapshot()["revision"],
        worker_claim_id="generation-worker-bad-context",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=bad_contents,
        provider=bad_provider,
    )
    require(rejected["state"] == "context_rejected" and bad_provider.calls == 0)

    extra_contents = dict(context_bad["contents"])
    extra_contents["extra-source"] = "X"
    extra = bad_generation.execute(
        "generation-event-extra-context",
        operation_id="generation-operation-extra-context",
        arbitration_id=arbitration_bad["arbitration_id"],
        observed_arbitration_revision=arbitration_store_bad.snapshot()["revision"],
        worker_claim_id="generation-worker-extra-context",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=extra_contents,
        provider=bad_provider,
    )
    require(extra["state"] == "context_rejected" and bad_provider.calls == 0)

    runtime_profile = base / "profile" / "cognition"
    context_profile, arbitration_store_profile, arbitration_profile = setup(runtime_profile, "profile")
    wrong_provider = StubProvider(context_profile["provider_profile_id"], "0" * 64)
    profile_generation = ConversationCognitionBoundedGenerationStore(runtime_profile)
    profile_rejected = profile_generation.execute(
        "generation-event-profile",
        operation_id="generation-operation-profile",
        arbitration_id=arbitration_profile["arbitration_id"],
        observed_arbitration_revision=arbitration_store_profile.snapshot()["revision"],
        worker_claim_id="generation-worker-profile",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=context_profile["contents"],
        provider=wrong_provider,
    )
    require(profile_rejected["state"] == "provider_rejected" and wrong_provider.calls == 0)

    runtime_stale = base / "stale" / "cognition"
    context_stale, arbitration_store_stale, arbitration_stale = setup(runtime_stale, "stale")
    stale_provider = StubProvider(context_stale["provider_profile_id"], context_stale["provider_profile_digest"])
    stale_generation = ConversationCognitionBoundedGenerationStore(runtime_stale)
    stale_worker = stale_generation.execute(
        "generation-event-stale-worker",
        operation_id="generation-operation-stale-worker",
        arbitration_id=arbitration_stale["arbitration_id"],
        observed_arbitration_revision=arbitration_store_stale.snapshot()["revision"],
        worker_claim_id="generation-worker-stale",
        worker_epoch=1,
        current_worker_epoch=2,
        source_resolver=context_stale["contents"],
        provider=stale_provider,
    )
    require(stale_worker["state"] == "stale_worker" and stale_provider.calls == 0)
    stale_arbitration = stale_generation.execute(
        "generation-event-stale-arbitration",
        operation_id="generation-operation-stale-arbitration",
        arbitration_id=arbitration_stale["arbitration_id"],
        observed_arbitration_revision=0,
        worker_claim_id="generation-worker-stale-arbitration",
        worker_epoch=2,
        current_worker_epoch=2,
        source_resolver=context_stale["contents"],
        provider=stale_provider,
    )
    require(stale_arbitration["state"] == "stale_arbitration" and stale_provider.calls == 0)

    runtime_timeout = base / "timeout" / "cognition"
    context_timeout, arbitration_store_timeout, arbitration_timeout = setup(runtime_timeout, "timeout")
    timeout_provider = StubProvider(context_timeout["provider_profile_id"], context_timeout["provider_profile_digest"], "timeout")
    timeout_generation = ConversationCognitionBoundedGenerationStore(runtime_timeout)
    timed_out = timeout_generation.execute(
        "generation-event-timeout",
        operation_id="generation-operation-timeout",
        arbitration_id=arbitration_timeout["arbitration_id"],
        observed_arbitration_revision=arbitration_store_timeout.snapshot()["revision"],
        worker_claim_id="generation-worker-timeout",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=context_timeout["contents"],
        provider=timeout_provider,
        timeout_ms=20,
    )
    require(timed_out["state"] == "timed_out" and timed_out["generated_text"] == "")
    timeout_receipt = timeout_generation.snapshot()["receipts"][0]
    require(timeout_receipt["timeout_observed"] and timeout_receipt["workload_continuity_state"] == "timed_out")

    runtime_cancel = base / "cancel" / "cognition"
    context_cancel, arbitration_store_cancel, arbitration_cancel = setup(runtime_cancel, "cancel")
    cancel_provider = StubProvider(context_cancel["provider_profile_id"], context_cancel["provider_profile_digest"], "cancel")
    cancel_generation = ConversationCognitionBoundedGenerationStore(runtime_cancel)
    holder = {}

    def run_cancelled() -> None:
        holder["result"] = cancel_generation.execute(
            "generation-event-cancel",
            operation_id="generation-operation-cancel",
            arbitration_id=arbitration_cancel["arbitration_id"],
            observed_arbitration_revision=arbitration_store_cancel.snapshot()["revision"],
            worker_claim_id="generation-worker-cancel",
            worker_epoch=1,
            current_worker_epoch=1,
            source_resolver=context_cancel["contents"],
            provider=cancel_provider,
            timeout_ms=300,
        )

    thread = threading.Thread(target=run_cancelled)
    thread.start()
    require(cancel_provider.started.wait(1))
    cancellation = cancel_generation.request_cancellation(
        "generation-cancellation-event",
        operation_id="generation-operation-cancel",
    )
    thread.join(2)
    require(cancellation["state"] == "cancellation_requested" and holder["result"]["state"] == "cancelled")
    require(cancel_generation.snapshot()["receipts"][0]["cancellation_requested"])

    runtime_large = base / "large" / "cognition"
    context_large, arbitration_store_large, arbitration_large = setup(runtime_large, "large")
    large_provider = StubProvider(context_large["provider_profile_id"], context_large["provider_profile_digest"], "large")
    large_generation = ConversationCognitionBoundedGenerationStore(runtime_large)
    exhausted = large_generation.execute(
        "generation-event-large",
        operation_id="generation-operation-large",
        arbitration_id=arbitration_large["arbitration_id"],
        observed_arbitration_revision=arbitration_store_large.snapshot()["revision"],
        worker_claim_id="generation-worker-large",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=context_large["contents"],
        provider=large_provider,
        maximum_output_tokens=32,
        timeout_ms=200,
    )
    require(exhausted["state"] == "budget_exhausted" and exhausted["generated_text"] == "")

    inspection = generation.inspection_summary()
    require(inspection["contract_version"] == "v1145.4")
    require(set(inspection["recognized_states"]) == STATES)
    require(inspection["exact_provider_context_assembly"] and inspection["configured_local_model_path_available"])
    require(inspection["cancellation_supported"] and inspection["timeout_supported"] and inspection["workload_continuity_integrated"])
    require(inspection["receipts_are_structural_only"] and inspection["generated_output_requires_separate_commit"])
    require(not any(inspection["authority_boundary"].values()))
    require(not inspection["prompt_exposed"] and not inspection["generated_response_exposed"] and not inspection["hidden_reasoning_exposed"])
    require(not inspection["message_sent"] and not inspection["generated_output_committed"] and not inspection["conversation_mutated"])

print(json.dumps({"passed": passed, "total": 27, "suite": "v1145.4"}))
