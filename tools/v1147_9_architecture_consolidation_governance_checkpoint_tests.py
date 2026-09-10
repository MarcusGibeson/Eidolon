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

from conscious_agent.architecture_consolidation_governance_checkpoint import (
    build_architecture_consolidation_governance_checkpoint,
)

passed = 0


def require(value):
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


report = build_architecture_consolidation_governance_checkpoint(source_root=ROOT)
require(report["contract_version"] == "v1147.9")
require(report["checkpoint_id"] == "architecture-consolidation-governance:v1147.9")
require(report["ok"] and report["status"] == "ready_for_desktop_verification")
require(report["passed"] == report["total"] == 24)
require(all(row["status"] == "pass" for row in report["checks"]))
require(report["read_only"] and not report["post_available"])
require(not report["source_modified"] and not report["runtime_mutated"])
require(report["intake"]["contract_version"] == "v1147.2")
require(report["execution"]["contract_version"] == "v1147.5")
require(report["reliability"]["contract_version"] == "v1147.8")
require(report["summary"]["ownership_domain_count"] == 9)
require(report["summary"]["registered_checkpoint_count"] == 2)
require(report["summary"]["dispatched_checkpoint_count"] == 2)
require(report["summary"]["startup_tier_count"] == 3)
require(report["summary"]["continuity_issue_count"] == 0)
require(report["summary"]["reliability_score"] == 100)
require(
    not any(
        report[key]
        for key in (
            "ownership_manifest_created_by_checkpoint",
            "checkpoint_registry_modified_by_checkpoint",
            "checkpoint_dispatched_with_operational_authority",
            "startup_service_started_by_checkpoint",
            "deferred_service_started_by_checkpoint",
            "provider_contacted_by_checkpoint",
            "source_modified_by_checkpoint",
            "runtime_modified_by_checkpoint",
            "message_sent",
            "notification_created",
            "goal_created",
            "plan_created",
            "development_proposal_created",
            "approval_created",
            "authorization_created",
            "installation_performed",
            "promotion_performed",
            "certification_performed",
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

with tempfile.TemporaryDirectory() as td:
    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "architecture-consolidation-governance-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=90,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1147.9")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/architecture-consolidation-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1147.9")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/architecture-consolidation-governance-checkpoint",
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
    "architecture-consolidation-governance-checkpoint-panel" in dashboard
    and "/api/cognition/architecture-consolidation-governance-checkpoint" in dashboard
    and "loadArchitectureConsolidationGovernanceCheckpoint" in dashboard
)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
require(working >= (1147, 9) and (working != (1147, 9) or previous == (1147, 8)))
require("v1147.9 Architecture Consolidation Governance Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require(report["desktop_verification_pending"] and not report["consciousness_proven"])

print(json.dumps({"passed": passed, "total": 25, "suite": "v1147.9"}))
