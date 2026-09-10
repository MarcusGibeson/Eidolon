import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.conversation_cognition_bounded_generation import ConversationCognitionBoundedGenerationStore
from conscious_agent.conversation_cognition_communication_arbitration import ConversationCognitionCommunicationArbitrationStore
from conscious_agent.conversation_cognition_unification_execution_checkpoint import (
    build_conversation_cognition_unification_execution_checkpoint,
)
from tools.v1145_bundle_b_test_support import build_context_chain, build_workload_admission

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


class CheckpointProvider:
    def __init__(self, profile_id: str, profile_digest: str) -> None:
        self.profile_id = profile_id
        self.profile_digest = profile_digest

    def generate(self, prompt: str, *, cancel_event, max_tokens: int, timeout_ms: int) -> str:
        del prompt, cancel_event, timeout_ms
        return "Q" * min(20, max_tokens)


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    context = build_context_chain(runtime, suffix="checkpoint")
    workload = build_workload_admission(runtime, suffix="checkpoint")
    arbitration_store = ConversationCognitionCommunicationArbitrationStore(runtime, clock=lambda: "2026-07-29T21:01:00Z")
    ready = arbitration_store.arbitrate(
        "checkpoint-arbitration-ready",
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
    generation = ConversationCognitionBoundedGenerationStore(runtime, clock=lambda: "2026-07-29T21:02:00Z")
    completed = generation.execute(
        "checkpoint-generation-event",
        operation_id="checkpoint-generation-operation",
        arbitration_id=ready["arbitration_id"],
        observed_arbitration_revision=arbitration_store.snapshot()["revision"],
        worker_claim_id="checkpoint-generation-worker",
        worker_epoch=1,
        current_worker_epoch=1,
        source_resolver=context["contents"],
        provider=CheckpointProvider(context["provider_profile_id"], context["provider_profile_digest"]),
        maximum_output_tokens=64,
        timeout_ms=200,
    )
    require(completed["state"] == "completed")

    silence_context = build_context_chain(runtime, suffix="checkpoint-silence")
    silence = arbitration_store.arbitrate(
        "checkpoint-arbitration-silence",
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
    require(silence["outcome"] == "deliberate_silence")

    report = build_conversation_cognition_unification_execution_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1145.5")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 29)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["arbitration"]["contract_version"] == "v1145.3")
    require(report["generation"]["contract_version"] == "v1145.4")
    require(report["summary"]["communication_arbitration_count"] == 2)
    require(report["summary"]["generation_receipt_count"] == 1 and report["summary"]["completed_generation_count"] == 1)
    require(report["summary"]["deliberate_silence_count"] == 1)
    require(not any(report[key] for key in ("raw_conversation_exposed", "prompt_exposed", "provider_payload_exposed", "generated_response_exposed", "hidden_reasoning_exposed")))
    require(not any(report[key] for key in ("communication_arbitration_performed_by_checkpoint", "provider_context_assembled_by_checkpoint", "provider_contacted_by_checkpoint", "conversation_generated_by_checkpoint")))
    require(not any(report[key] for key in ("message_sent", "notification_created", "generated_output_committed", "cognition_mutated", "conversation_mutated")))
    require(not any(report[key] for key in ("approval_created", "authorization_created", "installation_performed", "promotion_performed", "certification_performed")))
    require(not report["consciousness_proven"] and report["desktop_verification_pending"])

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "conversation-cognition-unification-execution-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1145.5")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/conversation-cognition-unification-execution-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1145.5")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/conversation-cognition-unification-execution-checkpoint",
            body={},
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "conversation-cognition-unification-execution-checkpoint-panel" in dashboard
        and "/api/cognition/conversation-cognition-unification-execution-checkpoint" in dashboard
        and "loadConversationCognitionUnificationExecutionCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(working >= (1145, 5) and (working != (1145, 5) or previous == (1145, 4)))
    require("v1145.5 Conversation-Cognition Unification Execution Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))

print(json.dumps({"passed": passed, "total": 23, "suite": "v1145.5"}))
