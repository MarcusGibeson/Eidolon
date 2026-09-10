from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.feature_freeze_architecture_consolidated_checkpoint import (
    CONTRACT_VERSION,
    _digest,
    _validate_snapshot,
    build_feature_freeze_architecture_consolidated_checkpoint,
)

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))


def tree_signature(root: Path) -> tuple[str, int]:
    digest = hashlib.sha256(); count = 0
    excluded = {"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", "reports"}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.relative_to(root).parts) or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        rel = path.relative_to(root).as_posix(); data = path.read_bytes(); count += 1
        digest.update(rel.encode("utf-8")); digest.update(b"\0"); digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest(), count

before = tree_signature(ROOT)
report = build_feature_freeze_architecture_consolidated_checkpoint(source_root=ROOT)
after = tree_signature(ROOT)
require(report["ok"] is True)
require(report["contract_version"] == CONTRACT_VERSION == "v1198.9")
require(report["checkpoint_id"] == "feature-freeze-architecture-consolidation:v1198.9")
require(report["read_only"] is True)
require(report["post_available"] is False)
require(report["content_free"] is True)
require(report["source_unchanged"] is True)
require(before == after)
require(report["passed"] == report["total"])
require(report["total"] >= 80)
require(len(report["limitations"]) == 5)
require(report["privacy"]["ok"] is True)
require(report["privacy"]["forbidden_count"] == 0)

summary = report["summary"]
for field in (
    "content_free", "read_only", "privacy_preserved", "feature_freeze_active",
    "architecture_ownership_explicit", "duplicate_visibility_preserved",
    "operator_review_accountable", "exact_review_lineage_verified",
    "startup_budget_truth_preserved", "profile_budget_truth_preserved",
    "documentation_consistent", "verifier_registration_consistent",
    "freeze_compliance_preserved", "historical_truth_preserved",
    "current_regressions_separate", "inherited_debt_visible",
    "authority_boundary_preserved", "source_unchanged",
):
    require(summary[field] is True)
for field in (
    "new_feature_authorized", "exception_applied", "files_moved", "modules_merged",
    "files_deleted", "imports_rewritten", "documentation_rewritten", "fixture_deleted",
    "verifier_retired", "startup_executed", "profiling_executed", "verifier_executed",
    "approval_created", "approval_consumed", "provider_contacted", "model_contacted",
    "process_started", "thread_started", "runtime_mutated", "production_source_modified",
    "installation_performed", "promotion_performed", "certification_performed",
    "publication_performed", "release_performed", "automatic_continuation",
    "global_profile_pass_claimed", "authority_granted",
):
    require(summary[field] is False)
require(summary["authority_state"] == "separate_not_granted")
require(summary["foundation_contract_version"] == "v1198.2")
require(summary["review_contract_version"] == "v1198.5")
require(summary["hardening_contract_version"] == "v1198.8")
require(summary["retained_checkpoint_count"] == 3)
require(summary["architecture_area_count"] == 12)
require(summary["consolidation_kind_count"] == 4)
require(summary["review_action_count"] == 5)
require(summary["decision_count"] == 3)
require(summary["review_count"] == 15)
require(summary["hardening_evidence_class_count"] == 8)
require(summary["hardening_evidence_count"] == 8)
require(summary["inherited_debt_count"] == 1)
require(summary["startup_total_ms"] <= summary["startup_budget_ms"])
snapshot_for_validation = dict(summary); snapshot_for_validation.pop("blocked_case_count", None)
require(not _validate_snapshot(snapshot_for_validation))

for name, errors in report["blocked_cases"].items():
    require(bool(name))
    require(bool(errors))
require(len(report["blocked_cases"]) >= 55)
require("checkpoint_tamper" in report["blocked_cases"]["tamper"])

for field, value in (
    ("privacy_preserved", False), ("feature_freeze_active", False),
    ("architecture_ownership_explicit", False), ("operator_review_accountable", False),
    ("exact_review_lineage_verified", False), ("startup_budget_truth_preserved", False),
    ("documentation_consistent", False), ("verifier_registration_consistent", False),
    ("historical_truth_preserved", False), ("inherited_debt_visible", False),
    ("files_moved", True), ("modules_merged", True), ("files_deleted", True),
    ("imports_rewritten", True), ("profiling_executed", True), ("verifier_executed", True),
    ("approval_consumed", True), ("runtime_mutated", True), ("release_performed", True),
    ("global_profile_pass_claimed", True), ("authority_granted", True),
):
    candidate = dict(summary); candidate.pop("blocked_case_count", None); candidate[field] = value
    candidate["checkpoint_digest"] = _digest({k: v for k, v in candidate.items() if k != "checkpoint_digest"})
    require(bool(_validate_snapshot(candidate)))

for key, version, total in (
    ("foundations", "v1198.2", 92),
    ("review", "v1198.5", 425),
    ("hardening", "v1198.8", 14),
):
    retained = report["retained_checkpoints"][key]
    require(retained["contract_version"] == version)
    require(retained["passed"] == retained["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "feature-freeze-architecture-consolidated-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1198.9")
require((descriptor or {}).get("builder") == "build_feature_freeze_architecture_consolidated_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "feature-freeze-architecture-consolidation-checkpoint",
    "feature-freeze-consolidation-review-checkpoint",
    "performance-documentation-verifier-hardening-checkpoint",
    "feature-freeze-architecture-consolidated-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "feature-freeze-architecture-consolidated-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1198-9-cli-")},
)
require(process.returncode == 0)
try:
    cli = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli["ok"] is True)
    require(cli["contract_version"] == "v1198.9")
    require(cli["summary"]["architecture_area_count"] == 12)
    require(cli["summary"]["review_count"] == 15)
    require(cli["summary"]["hardening_evidence_class_count"] == 8)
    require(cli["summary"]["global_profile_pass_claimed"] is False)
except Exception:
    for _ in range(6): require(False)

status, payload = dispatch_api("GET", "/api/cognition/feature-freeze-architecture-consolidated-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1198.9")
require(payload["data"]["summary"]["architecture_area_count"] == 12)
require(payload["data"]["summary"]["review_count"] == 15)
require(payload["data"]["summary"]["hardening_evidence_class_count"] == 8)
status_post, payload_post = dispatch_api("POST", "/api/cognition/feature-freeze-architecture-consolidated-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
for token in (
    "feature-freeze-architecture-consolidated-panel",
    "feature-freeze-architecture-consolidated-state",
    "feature-freeze-architecture-consolidated-summary",
    "/api/cognition/feature-freeze-architecture-consolidated-checkpoint",
):
    require(token in html)
require("v1199.0-v1199.2" in html)
require("global pass not claimed" in html.lower())
require("no files are moved" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1198.9" in text or "v1198_9" in text)
    require("v1199.0-v1199.2" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1198.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1198.8"' in metadata)
require("Feature Freeze and Architecture Consolidation Checkpoint" in metadata)
for marker in ('WORKING_SOURCE_VERSION = "1198.8"', 'PREVIOUS_WORKING_SOURCE_VERSION = "1198.5"'):
    require(marker in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1198.9-feature-freeze-architecture-consolidation-checkpoint") == 1)
require(release.count("v1198_9_feature_freeze_architecture_consolidation_checkpoint_tests.py") == 1)
require(release.count("v1198.8-performance-documentation-verifier-hardening") == 1)

print(f"v1198.9 feature freeze and architecture consolidation checkpoint: {sum(checks)}/{len(checks)} PASS")
