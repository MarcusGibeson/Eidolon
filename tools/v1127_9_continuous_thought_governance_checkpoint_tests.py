from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from conscious_agent.api_server import dispatch_api
from conscious_agent.continuous_thought_governance_checkpoint import (
    build_continuous_thought_governance_checkpoint,
)

root = Path(tempfile.mkdtemp())
source = Path(__file__).resolve().parents[1]
report = build_continuous_thought_governance_checkpoint(root, source_root=source)
checks = [
    report["contract_version"] == "v1127.9",
    report["ok"],
    report["passed"] == 18,
    report["total"] == 18,
    not report["runtime_mutated"],
    not report["source_modified"],
    not report["raw_content_exposed"],
    not report["hidden_reasoning_exposed"],
    not report["provider_contacted"],
    not report["reflection_created"],
    not report["belief_updated"],
    not report["goal_updated"],
    not report["self_model_updated"],
    not report["message_sent"],
    not report["external_action_executed"],
]
cli = subprocess.run(
    [sys.executable, str(source / "eidolon.py"), "continuous-thought-governance-checkpoint"],
    cwd=source,
    text=True,
    capture_output=True,
)
checks.append(
    cli.returncode == 0
    and json.loads(cli.stdout)["contract_version"] == "v1127.9"
)
status, payload = dispatch_api(
    "GET", "/api/cognition/continuous-thought-governance-checkpoint"
)
checks.append(
    status == 200 and payload["data"]["contract_version"] == "v1127.9"
)
status, _ = dispatch_api(
    "POST", "/api/cognition/continuous-thought-governance-checkpoint"
)
checks.append(status in {400, 404, 405})
print(
    json.dumps(
        {
            "passed": sum(checks),
            "total": 18,
            "suite": "v1127.9",
        }
    )
)
raise SystemExit(0 if all(checks) else 1)
