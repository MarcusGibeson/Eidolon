import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from conscious_agent.prospective_planning_signals import ProspectivePlanningSignalStore
from conscious_agent.prospective_planning_candidates import ProspectivePlanningCandidateStore
from conscious_agent.prospective_planning_intake_checkpoint import build_prospective_planning_intake_checkpoint

ROOT = Path(__file__).resolve().parents[1]

def main():
    with TemporaryDirectory() as directory:
        root = Path(directory) / "cognition"
        signals = ProspectivePlanningSignalStore(root)
        signal_id = signals.register(
            "signal-1", origin_ids=["goal-outcome-1"], source_categories=["accepted_goal_outcome"],
            goal_ids=["goal-1"], purpose_category="project_path", evidence_ids=["evidence-1"],
            alternative_ids=["alt-1"], counterfactual_ids=["cf-1"], stop_condition_ids=["stop-1"],
        )["result"]["signal_id"]
        ProspectivePlanningCandidateStore(root).register("candidate-1", signal_ids=[signal_id])
        report = build_prospective_planning_intake_checkpoint(root, source_root=ROOT)
        assert report["ok"] and len(report["checks"]) == 18
        assert not report["runtime_mutated"] and not report["source_modified"]
        assert not report["plan_created"] and not report["external_action_executed"]
        environment = dict(os.environ)
        environment["EIDOLON_DATA_DIR"] = str(Path(directory) / "cli-runtime")
        cli = subprocess.run(
            [sys.executable, str(ROOT / "eidolon.py"), "prospective-planning-intake-checkpoint"],
            cwd=ROOT, env=environment, text=True, capture_output=True, timeout=60,
        )
        assert cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1134.2"
        os.environ["EIDOLON_DATA_DIR"] = str(Path(directory) / "api-runtime")
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/prospective-planning-intake-checkpoint")
        assert status == 200 and (payload.get("data") or {}).get("contract_version") == "v1134.2"
        post_status, _ = dispatch_api("POST", "/api/cognition/prospective-planning-intake-checkpoint", body={})
        assert post_status in (404, 405)
        dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
        assert "prospective-planning-intake-checkpoint-panel" in dashboard and "/api/cognition/prospective-planning-intake-checkpoint" in dashboard
        metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
        import re
        current = re.search(r'WORKING_SOURCE_VERSION = "([0-9.]+)"', metadata)
        previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "([0-9.]+)"', metadata)
        version_key = lambda value: tuple(int(part) for part in value.split("."))
        assert current and previous and version_key(current.group(1)) >= version_key("1134.2") and version_key(previous.group(1)) >= version_key("1133.9")
    print("v1134.2 prospective planning intake checkpoint: 9/9 passed")

if __name__ == "__main__":
    main()
