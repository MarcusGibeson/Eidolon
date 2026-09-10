from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1190-2-api-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.unified_experience_foundations_checkpoint import build_unified_experience_foundations_checkpoint

checks: list[bool] = []
require = lambda value: checks.append(bool(value))

with tempfile.TemporaryDirectory(prefix="eidolon-v1190-2-suite-") as temp:
    report = build_unified_experience_foundations_checkpoint(
        source_root=ROOT, runtime_root=Path(temp) / "runtime"
    )
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(report.get("contract_version") == "v1190.2")
    require(report.get("checkpoint_id") == "unified-experience-foundations:v1190.2")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("source_modified") is False)
    require(report.get("runtime_mutated") is False)
    require(report.get("production_source_modified") is False)
    require(report.get("sandbox_modified") is False)
    require(report.get("provider_contacted") is False)
    require(report.get("model_contacted") is False)
    require(report.get("automatic_continuation") is False)
    require(report.get("approval_created") is False)
    require(report.get("approval_consumed") is False)
    require(report.get("execution_invoked") is False)
    require(report.get("authority_granted") is False)
    require(report.get("authority_preserved") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    require(report.get("source_signature_before") == report.get("source_signature_after"))
    require(len(report.get("limitations", [])) == 5)
    require(len(str(report.get("structural_digest", ""))) == 64)
    summary = report.get("summary", {})
    require(summary.get("domain_count") == 9)
    require(summary.get("valid_snapshot_count") == 1)
    require(summary.get("blocked_boundary_case_count") == 8)
    require(summary.get("selected_domain") == "campaign")

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "unified-experience-foundations-checkpoint"),
    None,
)
require(row is not None)
require((row or {}).get("contract_version") == "v1190.2")
require((row or {}).get("builder") == "build_unified_experience_foundations_checkpoint")
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "unified-experience-foundations-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=180,
    env={
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1190-2-cli-"),
    },
)
require(proc.returncode == 0)
if proc.returncode == 0:
    cli = json.loads(proc.stdout)
    require(cli.get("ok") is True)
    require(cli.get("contract_version") == "v1190.2")
    require(cli.get("passed") == cli.get("total"))

status, payload = dispatch_api("GET", "/api/cognition/unified-experience-foundations-checkpoint")
require(status == 200)
require(payload.get("ok") is True)
require(payload.get("data", {}).get("contract_version") == "v1190.2")
require(payload.get("data", {}).get("post_available") is False)
status_post, _ = dispatch_api("POST", "/api/cognition/unified-experience-foundations-checkpoint")
require(status_post in {404, 405})

html = render_first_use_shell()
require("unified-experience-foundations-checkpoint-panel" in html)
require("/api/cognition/unified-experience-foundations-checkpoint" in html)
require("refreshUnifiedExperienceFoundationsCheckpoint" in html)
require("v1190.3-v1190.5" in html)
script_match = re.search(r"<script>(.*?)</script>", html, re.S)
require(script_match is not None)
if script_match:
    js_path = Path(tempfile.mkdtemp(prefix="eidolon-v1190-2-js-")) / "dashboard.js"
    js_path.write_text(script_match.group(1), encoding="utf-8")
    node = subprocess.run(["node", "--check", str(js_path)], text=True, capture_output=True, timeout=60)
    require(node.returncode == 0)

release_text = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
require(release_text.count("v1190.2-unified-experience-foundations") == 1)
require(release_text.count("tools/v1190_0_2_unified_experience_foundations_tests.py") == 1)

metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1190.2"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1189.9"' in metadata)
require("v1190.3-v1190.5 Operator Navigation and Coordinated Experience Transitions" in metadata)
for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("Current source: v1190.2" in text)
    require("v1190.0-v1190.2 Unified Experience Foundations" in text)
    require("v1190.3-v1190.5" in text)
    require("v1200" in text)

result = {
    "suite": "v1190.0-2-unified-experience-foundations",
    "passed": sum(checks),
    "total": len(checks),
    "ok": all(checks),
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
