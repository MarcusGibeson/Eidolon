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
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp())

from conscious_agent.cognitive_alpha_release_continuity import CognitiveAlphaReleaseContinuityStore
from conscious_agent.cognitive_alpha_feature_freeze_governance_checkpoint import (
    build_cognitive_alpha_feature_freeze_governance_checkpoint,
)

passed = 0


def require(value):
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    CognitiveAlphaReleaseContinuityStore(runtime).record_cycle("governance-cycle")
    report = build_cognitive_alpha_feature_freeze_governance_checkpoint(runtime, source_root=ROOT)

    require(report["contract_version"] == "v1149.9")
    require(report["checkpoint_id"] == "cognitive-alpha-feature-freeze-governance:v1149.9")
    require(report["ok"] and report["status"] == "ready_for_v1150_benchmark")
    require(report["passed"] == report["total"] == 24)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["read_only"] and not report["post_available"])
    require(not report["source_modified"] and not report["runtime_mutated"])
    require(report["intake"]["contract_version"] == "v1149.2")
    require(report["execution"]["contract_version"] == "v1149.5")
    require(report["reliability"]["contract_version"] == "v1149.8")
    require(report["summary"]["feature_count"] == 12)
    require(report["summary"]["readiness_path_count"] == 5)
    require(report["summary"]["execution_count"] == 5)
    require(report["summary"]["stable_recovery_count"] == 5)
    require(report["summary"]["continuity_record_count"] == 1)
    require(report["summary"]["new_feature_intake_open"] is False)
    require(0 <= report["summary"]["reliability_score"] <= 100)
    require(report["summary"]["classification"] in {"reliable", "review_required"})
    require(
        not any(
            report[key]
            for key in (
                "feature_freeze_modified_by_checkpoint",
                "readiness_execution_performed_by_checkpoint",
                "installation_performed",
                "upgrade_performed",
                "backup_created",
                "rollback_performed",
                "packaging_performed",
                "provider_contacted",
                "command_executed",
                "message_sent",
                "notification_created",
                "goal_created",
                "plan_created",
                "development_proposal_created",
                "approval_created",
                "authorization_created",
                "promotion_performed",
                "certification_performed",
                "v1150_benchmark_performed",
                "consciousness_proven",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "raw_conversation_exposed",
                "raw_message_exposed",
                "prompt_exposed",
                "reflection_text_exposed",
                "memory_text_exposed",
                "belief_text_exposed",
                "goal_text_exposed",
                "motivation_text_exposed",
                "relationship_text_exposed",
                "mood_text_exposed",
                "provider_payload_exposed",
                "source_text_exposed",
                "patch_text_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(report["desktop_verification_pending"] and report["v1150_benchmark_pending"])

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "cognitive-alpha-feature-freeze-governance-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1149.9")

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/cognitive-alpha-feature-freeze-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1149.9")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/cognitive-alpha-feature-freeze-governance-checkpoint",
            body={"confirm": True},
        )
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old


dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require(
    "cognitive-alpha-feature-freeze-governance-checkpoint-panel" in dashboard
    and "/api/cognition/cognitive-alpha-feature-freeze-governance-checkpoint" in dashboard
    and "refreshCognitiveAlphaFeatureFreezeGovernanceCheckpoint" in dashboard
)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) == (1149, 9) and tuple(map(int, previous.groups())) == (1149, 8))
require(
    "v1149.9 Cognitive Alpha Feature Freeze Governance Checkpoint"
    in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
)
require("v1150 Full Desktop Codex Benchmark" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"))

print(json.dumps({"passed": passed, "total": 28, "suite": "v1149.9"}))
