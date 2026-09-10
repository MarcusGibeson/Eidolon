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

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.persistent_supervised_developer_alpha_hardening_checkpoint import (
    build_persistent_supervised_developer_alpha_hardening_checkpoint,
)

checks: list[bool] = []
require = lambda value: checks.append(bool(value))

with tempfile.TemporaryDirectory(prefix="eidolon-v1189-9-suite-") as temp:
    report = build_persistent_supervised_developer_alpha_hardening_checkpoint(
        source_root=ROOT, runtime_root=Path(temp) / "runtime"
    )
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(report.get("contract_version") == "v1189.9")
    require(report.get("checkpoint_id") == "persistent-supervised-developer-alpha-hardening:v1189.9")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("source_modified") is False)
    require(report.get("runtime_mutated") is False)
    require(report.get("production_source_modified") is False)
    require(report.get("sandbox_modified") is False)
    require(report.get("provider_contacted") is False)
    require(report.get("model_contacted") is False)
    require(report.get("automatic_retry") is False)
    require(report.get("automatic_resume") is False)
    require(report.get("automatic_continuation") is False)
    require(report.get("recovery_executed") is False)
    require(report.get("policy_modified") is False)
    require(report.get("future_work_selection_modified") is False)
    require(report.get("authority_granted") is False)
    require(report.get("authority_preserved") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    require(len(report.get("limitations", [])) == 5)
    require(len(str(report.get("structural_digest", ""))) == 64)
    require(report.get("source_signature_before") == report.get("source_signature_after"))
    summary = report.get("summary", {})
    require(summary.get("retained_bundle_count") == 3)
    require(summary.get("session_state_case_count") == 8)
    require(summary.get("reliability_review_case_count") == 12)
    require(summary.get("blocked_boundary_case_count") >= 15)
    require(summary.get("durable_nonce_case_count") == 3)
    require(summary.get("long_session_case_count") == 5)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "persistent-supervised-developer-alpha-hardening-checkpoint"), None)
require(row is not None)
require((row or {}).get("contract_version") == "v1189.9")
require((row or {}).get("builder") == "build_persistent_supervised_developer_alpha_hardening_checkpoint")
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

proc = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "persistent-supervised-developer-alpha-hardening-checkpoint"],
    cwd=ROOT, text=True, capture_output=True, timeout=180,
    env={**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1189-9-cli-")},
)
require(proc.returncode == 0)
cli = json.loads(proc.stdout)
require(cli.get("ok") is True)
require(cli.get("contract_version") == "v1189.9")
require(cli.get("passed") == cli.get("total"))

status, payload = dispatch_api("GET", "/api/cognition/persistent-supervised-developer-alpha-hardening-checkpoint")
require(status == 200)
require(payload.get("ok") is True)
require(payload.get("data", {}).get("contract_version") == "v1189.9")
require(payload.get("data", {}).get("post_available") is False)
status_post, _ = dispatch_api("POST", "/api/cognition/persistent-supervised-developer-alpha-hardening-checkpoint")
require(status_post in {404, 405})

html = render_first_use_shell()
require("persistent-supervised-developer-alpha-hardening-checkpoint-panel" in html)
require("/api/cognition/persistent-supervised-developer-alpha-hardening-checkpoint" in html)
require("refreshPersistentSupervisedDeveloperAlphaHardeningCheckpoint" in html)
require("v1190.0-v1190.2" in html)
script_match = re.search(r"<script>(.*?)</script>", html, re.S)
require(script_match is not None)
if script_match:
    js_path = Path(tempfile.mkdtemp(prefix="eidolon-v1189-9-js-")) / "dashboard.js"
    js_path.write_text(script_match.group(1), encoding="utf-8")
    node = subprocess.run(["node", "--check", str(js_path)], text=True, capture_output=True, timeout=60)
    require(node.returncode == 0)

release_text = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
require(release_text.count("v1189.9-persistent-supervised-developer-alpha-hardening-checkpoint") == 1)
require(release_text.count("tools/v1189_9_persistent_supervised_developer_alpha_hardening_checkpoint_tests.py") == 1)

metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1189.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1189.8"' in metadata)
require("v1190.0-v1190.2 Unified Experience Foundations" in metadata)
for name in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md"):
    text = (ROOT / name).read_text(encoding="utf-8")
    require("Current source: v1189.9" in text)
    require("v1189.9 Persistent Supervised Developer Alpha Hardening Checkpoint" in text)
    require("v1190.0-v1190.2 Unified Experience Foundations" in text)
    require("v1200" in text)

result = {"suite": "v1189.9-persistent-supervised-developer-alpha-hardening-checkpoint", "passed": sum(checks), "total": len(checks), "ok": all(checks)}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
