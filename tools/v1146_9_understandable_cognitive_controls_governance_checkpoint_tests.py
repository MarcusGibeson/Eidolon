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

from conscious_agent.understandable_cognitive_control_activation import (
    CONFIRMATION_PHRASE,
    activate_cognitive_control_preview,
)
from conscious_agent.understandable_cognitive_control_configuration import (
    create_cognitive_control_configuration_preview,
)
from conscious_agent.understandable_cognitive_control_continuity import (
    record_cognitive_control_continuity,
)
from conscious_agent.understandable_cognitive_control_enforcement import (
    evaluate_cognitive_control,
)
from conscious_agent.understandable_cognitive_control_reliability import (
    review_cognitive_control_reliability,
)
from conscious_agent.understandable_cognitive_controls_governance_checkpoint import (
    build_understandable_cognitive_controls_governance_checkpoint,
)

passed = 0

def require(value):
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1

with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    preview = create_cognitive_control_configuration_preview(
        {"domain": "attention", "mode": "focused", "intensity": 0.5},
        runtime_root=runtime,
        operator_id="operator-1",
        source_event_id="event-1",
    )
    activation = activate_cognitive_control_preview(
        runtime_root=runtime,
        preview_id=preview["configuration_id"],
        preview_digest=preview["structural_digest"],
        confirmation=CONFIRMATION_PHRASE,
        operator_id="operator-1",
        request_id="request-1",
    )
    require(activation["ok"])
    evaluate_cognitive_control(
        runtime_root=runtime,
        domain="attention",
        event_id="enforcement-1",
        consumer_id="attention-consumer",
        requested_intensity=0.8,
        resource_cost=0.2,
    )
    record_cognitive_control_continuity(
        runtime_root=runtime,
        cycle_id="cycle-1",
        operator_correction_id="correction-1",
    )
    review_cognitive_control_reliability(runtime_root=runtime, review_id="review-1")

    report = build_understandable_cognitive_controls_governance_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1146.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 24)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1146.2")
    require(report["execution"]["contract_version"] == "v1146.5")
    require(report["reliability"]["contract_version"] == "v1146.8")
    require(report["summary"]["control_domain_count"] == 6)
    require(report["summary"]["configuration_preview_count"] == 1)
    require(report["summary"]["active_control_count"] == 1)
    require(report["summary"]["enforcement_receipt_count"] == 1)
    require(report["summary"]["continuity_record_count"] == 1 and report["summary"]["reliability_review_count"] == 1)
    require(
        not any(
            report[key]
            for key in (
                "control_definition_created_by_checkpoint", "configuration_preview_created_by_checkpoint",
                "control_activation_performed_by_checkpoint", "control_rollback_performed_by_checkpoint",
                "control_enforcement_performed_by_checkpoint", "continuity_record_created_by_checkpoint",
                "reliability_review_created_by_checkpoint", "cognition_started_by_checkpoint",
                "provider_contacted_by_checkpoint", "message_sent", "notification_created",
                "goal_created", "plan_created", "development_proposal_created",
                "cognition_mutated", "memory_mutated", "relationship_mutated", "mood_mutated",
                "goal_mutated", "motivation_mutated", "attention_mutated", "approval_created",
                "authorization_created", "installation_performed", "promotion_performed",
                "certification_performed", "consciousness_proven",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "raw_conversation_exposed", "raw_message_exposed", "prompt_exposed",
                "reflection_text_exposed", "memory_text_exposed", "relationship_text_exposed",
                "mood_text_exposed", "goal_text_exposed", "motivation_text_exposed",
                "provider_payload_exposed", "generated_response_exposed", "hidden_reasoning_exposed",
            )
        )
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "understandable-cognitive-controls-governance-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1146.9")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/understandable-cognitive-controls-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1146.9")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/understandable-cognitive-controls-governance-checkpoint",
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
        "understandable-cognitive-controls-governance-checkpoint-panel" in dashboard
        and "/api/cognition/understandable-cognitive-controls-governance-checkpoint" in dashboard
        and "loadUnderstandableCognitiveControlsGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(working >= (1146, 9) and (working != (1146, 9) or previous == (1146, 8)))
    require("v1146.9 Understandable Cognitive Controls Governance Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
    require(report["desktop_verification_pending"] and report["read_only"] and not report["post_available"])

print(json.dumps({"passed": passed, "total": 23, "suite": "v1146.9"}))
