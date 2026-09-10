from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.feature_freeze_architecture_consolidation_checkpoint import build_feature_freeze_architecture_consolidation_checkpoint

checks: list[bool] = []
def require(value: object) -> None:
    checks.append(bool(value)); assert value

with tempfile.TemporaryDirectory(prefix="eidolon-v1198-2-") as temporary:
    runtime = Path(temporary) / "runtime-must-not-exist"
    report = build_feature_freeze_architecture_consolidation_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True), ("contract_version", "v1198.2"), ("read_only", True),
    ("post_available", False), ("content_free", True), ("source_unchanged", True),
    ("runtime_mutated", False), ("production_source_modified", False),
    ("files_moved", False), ("modules_merged", False), ("files_deleted", False),
    ("imports_rewritten", False), ("startup_executed", False),
    ("new_feature_authorized", False), ("exception_approved", False),
    ("approval_created", False), ("approval_consumed", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("process_started", False), ("thread_started", False),
    ("installation_performed", False), ("promotion_performed", False),
    ("certification_performed", False), ("publication_performed", False),
    ("release_performed", False), ("automatic_continuation", False),
    ("global_profile_pass_claimed", False), ("authority_granted", False),
): require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 70)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 25)
require(report["privacy"]["ok"] is True)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1198.2"), ("status", "ready_for_operator_review"),
    ("component_count", 12), ("candidate_count", 4), ("area_count", 12),
    ("owner_count", 12), ("feature_freeze_active", True),
    ("architecture_ownership_explicit", True), ("duplicate_visibility_preserved", True),
    ("historical_truth_preserved", True), ("current_regressions_separate", True),
    ("inherited_debt_visible", True), ("content_free", True), ("read_only", True),
    ("files_moved", False), ("modules_merged", False), ("files_deleted", False),
    ("imports_rewritten", False), ("startup_executed", False),
    ("runtime_mutated", False), ("source_modified", False),
    ("new_feature_authorized", False), ("exception_approved", False),
    ("approval_created", False), ("approval_consumed", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("process_started", False), ("thread_started", False),
    ("installation_performed", False), ("promotion_performed", False),
    ("certification_performed", False), ("publication_performed", False),
    ("release_performed", False), ("automatic_continuation", False),
    ("global_profile_pass_claimed", False), ("authority_state", "separate_not_granted"),
): require(summary.get(key) == expected)
require(summary["startup_total_ms"] <= summary["startup_budget_ms"])
require(len(summary["assessment_digest"]) == 64)

for name in (
    "duplicate-component", "duplicate-sequence", "unsupported-area", "missing-owner",
    "bad-freeze-state", "bad-module-digest", "private-field", "file-move", "module-merge",
    "source-modification", "authority", "unknown-canonical", "unknown-related",
    "unsupported-kind", "unsupported-disposition", "candidate-file-delete", "new-feature",
    "exception-approved", "files-moved", "imports-rewritten", "startup-executed",
    "approval-created", "provider-contact", "process-start", "release",
    "automatic-continuation", "plan-authority",
):
    require(name in report["blocked_cases"]); require(bool(report["blocked_cases"][name]))

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "feature-freeze-architecture-consolidation-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1198.2")
require((descriptor or {}).get("builder") == "build_feature_freeze_architecture_consolidation_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run([sys.executable, str(ROOT / "eidolon.py"), "feature-freeze-architecture-consolidation-checkpoint"], cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1198-2-cli-")})
require(process.returncode == 0)
cli = json.loads(process.stdout.strip().splitlines()[-1])
require(cli["ok"] is True); require(cli["contract_version"] == "v1198.2")
require(cli["summary"]["component_count"] == 12); require(cli["summary"]["candidate_count"] == 4)

status, payload = dispatch_api("GET", "/api/cognition/feature-freeze-architecture-consolidation-checkpoint", {}, None)
require(status == 200); require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1198.2")
require(payload["data"]["summary"]["feature_freeze_active"] is True)
status_post, payload_post = dispatch_api("POST", "/api/cognition/feature-freeze-architecture-consolidation-checkpoint", {}, {})
require(status_post in {404, 405}); require(payload_post.get("ok") is False)

html = render_first_use_shell()
for token in ("feature-freeze-architecture-consolidation-panel", "feature-freeze-architecture-consolidation-state", "feature-freeze-architecture-consolidation-summary", "/api/cognition/feature-freeze-architecture-consolidation-checkpoint", "v1198.3-v1198.5"):
    require(token in html)
require("no files are moved" in html.lower())
require("global pass not claimed" in html.lower())

for relative in ("README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py"):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1198.2" in text or "v1198_0_2" in text)
    require("v1198.3-v1198.5" in text)
metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1198.2"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1197.9"' in metadata)
release = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
require(release.count("v1198.2-feature-freeze-architecture-consolidation") == 1)
require(release.count("v1198_0_2_feature_freeze_architecture_consolidation_tests.py") == 1)

print(f"v1198.0-v1198.2 feature freeze and architecture consolidation: {sum(checks)}/{len(checks)} PASS")
