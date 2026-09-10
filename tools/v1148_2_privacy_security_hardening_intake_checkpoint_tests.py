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

from conscious_agent.privacy_security_hardening_intake_checkpoint import (
    build_privacy_security_hardening_intake_checkpoint,
)

report = build_privacy_security_hardening_intake_checkpoint(source_root=ROOT)
checks = [
    report["contract_version"] == "v1148.2",
    report["checkpoint_id"] == "privacy-security-hardening-intake:v1148.2",
    report["ok"] and report["status"] == "ready_for_bundle_b",
    report["passed"] == report["total"] == 22,
    report["read_only"] and not report["post_available"],
    not report["source_modified"] and not report["runtime_mutated"],
    report["summary"]["threat_category_count"] == report["summary"]["threat_count"] == 6,
    report["summary"]["scenario_count"] == 12,
    report["summary"]["execution_eligible_count"] == 0,
    report["summary"]["operator_review_required_count"] == 12,
    not any(report[key] for key in ("security_test_executed", "provider_contacted", "command_executed", "message_sent", "notification_created", "goal_created", "plan_created", "development_proposal_created", "approval_created", "authorization_created", "installation_performed", "promotion_performed", "certification_performed")),
    not any(report[key] for key in ("raw_conversation_exposed", "raw_message_exposed", "prompt_exposed", "reflection_text_exposed", "memory_text_exposed", "belief_text_exposed", "goal_text_exposed", "relationship_text_exposed", "mood_text_exposed", "provider_payload_exposed", "source_text_exposed", "patch_text_exposed", "hidden_reasoning_exposed")),
]

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "privacy-security-hardening-intake-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    checks.append(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1148.2")

    old_data = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/privacy-security-hardening-intake-checkpoint")
        checks.append(status == 200 and payload["data"]["contract_version"] == "v1148.2")
        post, _ = dispatch_api("POST", "/api/cognition/privacy-security-hardening-intake-checkpoint", body={"confirm": True})
        checks.append(post in (404, 405))
    finally:
        if old_data is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
checks.append("privacy-security-hardening-intake-checkpoint-panel" in dashboard and "loadPrivacySecurityHardeningIntakeCheckpoint" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "([^"]+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "([^"]+)"', metadata)
current_version = tuple(int(part) for part in working.group(1).split(".")) if working else ()
previous_version = tuple(int(part) for part in previous.group(1).split(".")) if previous else ()
checks.append(bool(current_version >= (1148, 2) and (current_version != (1148, 2) or previous_version == (1148, 1))))
checks.append("v1148.2 Privacy and Security Hardening Intake Checkpoint" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
checks.append(report["desktop_verification_pending"] and not report["consciousness_proven"])

assert all(checks), [index + 1 for index, value in enumerate(checks) if not value]
print(json.dumps({"suite": "v1148.2", "passed": len(checks), "total": len(checks)}))
