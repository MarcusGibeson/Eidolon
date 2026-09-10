from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
from conscious_agent.api_server import dispatch_api
from conscious_agent.release_archive_coherence import metadata_version_contradictions
from conscious_agent.supervised_repair_implementation_intake_checkpoint import build_supervised_repair_implementation_intake_checkpoint

checks = []
def check(name, value):
    checks.append((name, bool(value)))
    print(("PASS" if value else "FAIL"), name)

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "cognition"
    report = build_supervised_repair_implementation_intake_checkpoint(runtime, source_root=ROOT)
    check("checkpoint 24/24", report["ok"] and report["passed"] == report["total"] == 24)
    check("contracts", report["eligibility"]["contract_version"] == "v1141.0" and report["work_orders"]["contract_version"] == "v1141.1")
    check("read only", not report["runtime_mutated"] and not report["source_modified"])
    check("privacy", not report["raw_source_exposed"] and not report["patch_text_exposed"] and not report["hidden_reasoning_exposed"])
    check("no authority", not report["sandbox_created"] and not report["commands_executed"] and not report["tests_executed"] and not report["approval_created"] and not report["authorization_created"] and not report["external_action_executed"])

    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "supervised-repair-implementation-intake-checkpoint"], cwd=ROOT, env=env, text=True, capture_output=True, timeout=60)
    check("cli", cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1141.2")

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    try:
        status, payload = dispatch_api("GET", "/api/cognition/supervised-repair-implementation-intake-checkpoint")
        check("get api", status == 200 and payload["data"]["contract_version"] == "v1141.2")
        post_status, _ = dispatch_api("POST", "/api/cognition/supervised-repair-implementation-intake-checkpoint", body={})
        check("post unavailable", post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

    absent_runtime_metadata = metadata_version_contradictions(
        "1141.2", internal_version="1141.2", settings_present=False, project_present=False
    )
    check("source-only metadata absence", absent_runtime_metadata == [])
    mismatched_runtime_metadata = metadata_version_contradictions(
        "1141.2",
        internal_version="1141.2",
        settings_version="1140.9",
        project_version="1140.9",
        settings_present=True,
        project_present=True,
    )
    mismatch_kinds = {row.get("kind") for row in mismatched_runtime_metadata}
    check("packaged metadata mismatch fails closed", mismatch_kinds == {"settings_metadata_version_mismatch", "project_metadata_version_mismatch"})

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    check("dashboard", "supervised-repair-implementation-intake-checkpoint-panel" in dashboard and "/api/cognition/supervised-repair-implementation-intake-checkpoint" in dashboard and "loadSupervisedRepairImplementationIntakeCheckpoint" in dashboard)

assert all(value for _, value in checks)
print(f"RESULT {sum(value for _, value in checks)}/{len(checks)}")
