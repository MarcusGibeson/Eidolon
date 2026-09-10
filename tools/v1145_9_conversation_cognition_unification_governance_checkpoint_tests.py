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

from conscious_agent.conversation_cognition_cross_cycle_continuity import (
    ConversationCognitionCrossCycleContinuityStore,
)
from conscious_agent.conversation_cognition_reliability_review import (
    ConversationCognitionReliabilityReviewStore,
)
from conscious_agent.conversation_cognition_unification_governance_checkpoint import (
    build_conversation_cognition_unification_governance_checkpoint,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"

    continuity = ConversationCognitionCrossCycleContinuityStore(runtime)
    continuity_row = continuity.record(
        "governance-continuity",
        session_id="session-1",
        conversation_id="conversation-1",
        prior_generation_receipt_id="generation-1",
        current_generation_receipt_id="generation-2",
        source_revisions={"thought-1": 2, "memory-1": 1},
        current_categories=["thought", "goal", "mood"],
        historical_categories=["memory", "relationship"],
        correction_ids=["correction-1"],
        accepted_guidance_ids=["guidance-1"],
        current_thought_grounded=True,
        memory_consistent=True,
        relationship_boundary_clear=True,
        mood_goal_coherent=True,
        correction_effective=True,
        silence_preserved=True,
    )
    ConversationCognitionReliabilityReviewStore(runtime).review(
        "governance-review",
        continuity_record_ids=[continuity_row["record_id"]],
        visible_behavior_class="grounded_reply_or_silence",
        correction_success_count=1,
        coherence_score=0.95,
        uncertainty=0.05,
    )

    report = build_conversation_cognition_unification_governance_checkpoint(
        runtime,
        source_root=ROOT,
    )
    require(report["contract_version"] == "v1145.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 24)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1145.2")
    require(report["execution"]["contract_version"] == "v1145.5")
    require(report["reliability"]["contract_version"] == "v1145.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_conversation_exposed",
                "raw_message_exposed",
                "prompt_exposed",
                "reflection_text_exposed",
                "memory_text_exposed",
                "relationship_text_exposed",
                "mood_text_exposed",
                "goal_text_exposed",
                "motivation_text_exposed",
                "provider_payload_exposed",
                "generated_response_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "provider_contacted_by_checkpoint",
                "conversation_generated_by_checkpoint",
                "generated_output_committed",
                "message_sent",
                "notification_created",
                "cognition_mutated",
                "memory_mutated",
                "relationship_mutated",
                "mood_mutated",
                "goal_mutated",
                "motivation_mutated",
                "attention_mutated",
                "conversation_mutated",
                "approval_created",
                "authorization_created",
                "installation_performed",
                "promotion_performed",
                "certification_performed",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["eligibility_created_by_checkpoint"]
        and not report["candidate_created_by_checkpoint"]
        and not report["communication_arbitration_performed_by_checkpoint"]
        and not report["provider_context_assembled_by_checkpoint"]
        and not report["continuity_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "conversation-cognition-unification-governance-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1145.9")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/conversation-cognition-unification-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1145.9")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/conversation-cognition-unification-governance-checkpoint",
            body={"confirm": True},
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "conversation-cognition-unification-governance-checkpoint-panel" in dashboard
        and "/api/cognition/conversation-cognition-unification-governance-checkpoint" in dashboard
        and "loadConversationCognitionUnificationGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1145, 9)
        and (working != (1145, 9) or previous == (1145, 8))
        and "v1145.9 Conversation-Cognition Unification Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "context_candidate_count",
            "communication_arbitration_count",
            "generation_receipt_count",
            "continuity_record_count",
            "reliability_review_count",
            "deliberate_silence_count",
            "stale_context_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1145.9"}))
