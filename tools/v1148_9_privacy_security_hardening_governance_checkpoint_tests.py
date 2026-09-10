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

from conscious_agent.privacy_security_hardening_governance_checkpoint import build_privacy_security_hardening_governance_checkpoint

passed = 0
def require(value):
    global passed
    if not value:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1

report = build_privacy_security_hardening_governance_checkpoint(source_root=ROOT)
require(report["contract_version"] == "v1148.9")
require(report["checkpoint_id"] == "privacy-security-hardening-governance:v1148.9")
require(report["ok"] and report["status"] == "ready_for_desktop_verification")
require(report["passed"] == report["total"] == 24)
require(all(row["status"] == "pass" for row in report["checks"]))
require(report["read_only"] and not report["post_available"])
require(not report["source_modified"] and not report["runtime_mutated"])
require(report["intake"]["contract_version"] == "v1148.2")
require(report["execution"]["contract_version"] == "v1148.5")
require(report["reliability"]["contract_version"] == "v1148.8")
require(report["summary"]["threat_category_count"] == 6)
require(report["summary"]["scenario_count"] == 12)
require(0 <= report["summary"]["reliability_score"] <= 100)
require(report["summary"]["classification"] in {"reliable", "review_required"})
require(not any(report[k] for k in ("security_test_executed_by_checkpoint", "provider_contacted_by_checkpoint", "command_executed_by_checkpoint", "source_modified_by_checkpoint", "runtime_modified_by_checkpoint", "message_sent", "notification_created", "goal_created", "plan_created", "development_proposal_created", "approval_created", "authorization_created", "installation_performed", "promotion_performed", "certification_performed", "consciousness_proven")))
require(not any(report[k] for k in ("raw_conversation_exposed", "raw_message_exposed", "prompt_exposed", "reflection_text_exposed", "memory_text_exposed", "belief_text_exposed", "goal_text_exposed", "relationship_text_exposed", "mood_text_exposed", "provider_payload_exposed", "source_text_exposed", "patch_text_exposed", "hidden_reasoning_exposed")))

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "privacy-security-hardening-governance-checkpoint"], cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1148.9")
    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/privacy-security-hardening-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1148.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/privacy-security-hardening-governance-checkpoint", body={"confirm": True})
        require(post_status in (404, 405))
    finally:
        if old is None: os.environ.pop("EIDOLON_DATA_DIR", None)
        else: os.environ["EIDOLON_DATA_DIR"] = old

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("privacy-security-hardening-governance-checkpoint-panel" in dashboard and "/api/cognition/privacy-security-hardening-governance-checkpoint" in dashboard and "loadPrivacySecurityHardeningGovernanceCheckpoint" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
current_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(current_version >= (1148, 9) and (current_version != (1148, 9) or previous_version == (1148, 8)))
require("v1148.9 Privacy and Security Hardening Governance Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require(report["desktop_verification_pending"] and not report["consciousness_proven"])
print(json.dumps({"passed": passed, "total": 23, "suite": "v1148.9"}))
