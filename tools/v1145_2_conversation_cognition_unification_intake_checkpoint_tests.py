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

from conscious_agent.conversation_cognition_unification_intake_checkpoint import (
    build_conversation_cognition_unification_intake_checkpoint,
)
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


def source(category: str, token: str, *, temporal: str = "current", lifecycle: str = "active") -> dict:
    return {
        "source_category": category,
        "source_id": token,
        "source_revision": 3,
        "source_digest": (token[0] if token and token[0] in "abcdef" else "c") * 64,
        "temporal_status": temporal,
        "relevance_category": "immediate" if temporal == "current" else "background",
        "relevance_score": 0.85,
        "confidence": 0.8,
        "uncertainty": 0.2,
        "recorded_at": "2026-07-29T16:00:00Z",
        "expires_at": "2026-07-30T16:00:00Z",
        "privacy_class": "internal",
        "communication_eligible": True,
        "required_exclusion": False,
        "operator_review_required": False,
        "lifecycle_state": lifecycle,
        "session_id": "session-checkpoint",
        "conversation_id": "conversation-checkpoint",
        "relationship_boundary": "relationship_only" if category == "relationship_context" else "",
    }


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    refs = [
        source("active_thought", "a-thought"),
        source("memory_reference", "b-memory", temporal="historical"),
        source("relationship_context", "c-relationship", temporal="historical"),
        source("mood_state", "d-mood"),
        source("goal", "e-goal"),
        source("motivation", "f-motivation"),
        source("concern", "a-concern"),
        source("attention_target", "b-attention"),
        source("inquiry_state", "c-inquiry"),
        source("operator_correction", "d-correction", temporal="historical"),
        source("accepted_guidance", "e-guidance", temporal="historical"),
    ]
    refs += [source(category, f"f-{category}") for category in sorted(REQUIRED_CONTEXT_CATEGORIES)]
    eligibility_store = UnifiedConversationalContextEligibilityStore(runtime, clock=lambda: "2026-07-29T17:00:00Z")
    eligibility = eligibility_store.register(
        "eligibility-event",
        assembly_id="assembly-checkpoint",
        session_id="session-checkpoint",
        conversation_id="conversation-checkpoint",
        tab_id="tab-checkpoint",
        worker_claim_id="worker-checkpoint",
        worker_epoch=7,
        current_worker_epoch=7,
        retry_token_id="retry-checkpoint",
        source_references=refs,
        budget_limits={"cpu_budget_ms": 120, "memory_budget_mb": 256, "latency_budget_ms": 600, "token_budget": 800},
        reference_time="2026-07-29T17:00:00Z",
        expiry_at="2026-07-29T19:00:00Z",
    )
    row = eligibility_store.snapshot()["records"][0]
    provider_id = next(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "provider_state")
    communication_id = next(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "communication_policy")
    privacy_ids = sorted(item["source_id"] for item in row["source_lineage"] if item["source_category"] == "privacy_policy")
    candidate = UnifiedContextCandidateStore(runtime, clock=lambda: "2026-07-29T17:01:00Z").register(
        "candidate-event",
        eligibility_id=eligibility["eligibility_id"],
        candidate_scope_id="candidate-scope",
        included_source_ids=row["eligible_source_ids"],
        provider_profile_id=provider_id,
        communication_policy_id=communication_id,
        privacy_policy_ids=privacy_ids,
        temporal_window_id="window-checkpoint",
        window_start="2026-07-29T17:00:00Z",
        window_end="2026-07-29T18:00:00Z",
        budget_limits={"cpu_budget_ms": 100, "memory_budget_mb": 128, "latency_budget_ms": 500, "token_budget": 512},
        silence_eligible=True,
    )
    require(candidate["state"] == "candidate_ready")

    report = build_conversation_cognition_unification_intake_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1145.2")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 25)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["eligibility"]["contract_version"] == "v1145.0")
    require(report["candidates"]["contract_version"] == "v1145.1")
    require(report["summary"]["eligibility_record_count"] == 1 and report["summary"]["context_candidate_count"] == 1)
    require(not any(report[key] for key in ("raw_conversation_exposed", "prompt_exposed", "provider_payload_exposed", "hidden_reasoning_exposed")))
    require(not any(report[key] for key in ("communication_arbitration_performed", "provider_context_assembled", "provider_contacted", "conversation_generated", "message_sent", "notification_created")))
    require(not any(report[key] for key in ("cognition_mutated", "memory_mutated", "relationship_mutated", "mood_mutated", "goal_mutated", "motivation_mutated", "attention_mutated", "conversation_mutated")))
    require(not any(report[key] for key in ("approval_created", "authorization_created", "installation_performed", "promotion_performed", "certification_performed")))
    require(not report["eligibility_created_by_checkpoint"] and not report["candidate_created_by_checkpoint"] and not report["consciousness_proven"])

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "conversation-cognition-unification-intake-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1145.2")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/conversation-cognition-unification-intake-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1145.2")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/conversation-cognition-unification-intake-checkpoint",
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
        "conversation-cognition-unification-intake-checkpoint-panel" in dashboard
        and "/api/cognition/conversation-cognition-unification-intake-checkpoint" in dashboard
        and "loadConversationCognitionUnificationIntakeCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(working >= (1145, 2) and (working != (1145, 2) or previous == (1145, 1)))
    require("v1145.2 Conversation-Cognition Unification Intake Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 21, "suite": "v1145.2"}))
