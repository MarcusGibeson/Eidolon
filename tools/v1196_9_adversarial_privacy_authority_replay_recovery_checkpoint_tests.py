from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1196-9-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.adversarial_privacy_authority_replay_recovery_checkpoint import (
    CONTRACT_VERSION,
    build_adversarial_privacy_authority_replay_recovery_checkpoint,
)

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))
    assert value

with tempfile.TemporaryDirectory(prefix="eidolon-v1196-9-") as temporary:
    report = build_adversarial_privacy_authority_replay_recovery_checkpoint(
        source_root=ROOT, runtime_root=Path(temporary) / "runtime"
    )

for key, expected in (
    ("ok", True), ("contract_version", "v1196.9"), ("read_only", True),
    ("post_available", False), ("content_free", True), ("source_unchanged", True),
    ("runtime_mutated", False), ("production_source_modified", False),
    ("attacks_executed", False), ("private_state_fetched", False),
    ("automatic_recovery", False), ("automatic_retry", False),
    ("recovery_executed", False), ("retry_executed", False),
    ("cancellation_executed", False), ("execution_invoked", False),
    ("approval_created", False), ("approval_consumed", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("thread_started", False), ("process_started", False),
    ("installation_performed", False), ("promotion_performed", False),
    ("certification_performed", False), ("publication_performed", False),
    ("release_performed", False), ("automatic_continuation", False),
    ("global_profile_pass_claimed", False), ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 110)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 45)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1196.9"),
    ("foundation_contract_version", "v1196.2"),
    ("review_contract_version", "v1196.5"),
    ("reliability_contract_version", "v1196.8"),
    ("retained_checkpoint_count", 3), ("attack_class_count", 14),
    ("authority_domain_count", 16), ("review_event_class_count", 5),
    ("review_action_count", 4), ("decision_count", 3),
    ("reliability_event_class_count", 8), ("surface_count", 12),
    ("blocked_attack_count", 14), ("review_count", 15),
    ("reliability_sample_count", 8), ("content_free", True),
    ("read_only", True), ("privacy_preserved", True),
    ("authority_boundary_preserved", True), ("original_evidence_preserved", True),
    ("exact_lineage_verified", True), ("operator_review_accountable", True),
    ("foreground_available", True), ("historical_truth_preserved", True),
    ("current_regressions_separate", True), ("inherited_debt_visible", True),
    ("attacks_executed", False), ("private_state_fetched", False),
    ("privacy_attack_succeeded", False), ("automatic_recovery", False),
    ("automatic_retry", False), ("recovery_executed", False),
    ("retry_executed", False), ("cancellation_executed", False),
    ("execution_invoked", False), ("approval_created", False),
    ("approval_consumed", False), ("runtime_mutated", False),
    ("production_source_modified", False), ("provider_contacted", False),
    ("model_contacted", False), ("thread_started", False),
    ("process_started", False), ("installation_performed", False),
    ("promotion_performed", False), ("certification_performed", False),
    ("publication_performed", False), ("release_performed", False),
    ("automatic_continuation", False), ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"), ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(len(summary["checkpoint_digest"]) == 64)
require(summary["blocked_case_count"] == len(report["blocked_cases"]))

for name in (
    "private-field", "foundation-contract-drift", "review-contract-drift",
    "reliability-contract-drift", "retained-count", "attack-count",
    "authority-domain-count", "review-event-count", "action-count",
    "decision-count", "reliability-event-count", "surface-count",
    "privacy-loss", "authority-boundary-loss", "evidence-loss", "lineage-loss",
    "review-accountability-loss", "foreground-block", "historical-truth-loss",
    "verification-boundary-loss", "debt-hidden", "attack-execution",
    "private-fetch", "privacy-attack-success", "automatic-recovery",
    "automatic-retry", "recovery-execution", "retry-execution",
    "cancellation-execution", "hidden-execution", "approval-create",
    "approval-consume", "runtime-mutation", "source-mutation",
    "provider-contact", "model-contact", "thread-start", "process-start",
    "installation", "promotion", "certification", "publication", "release",
    "automatic-continuation", "global-pass-claim", "authority-state",
    "authority", "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

for key, version, total in (
    ("foundations", "v1196.2", 72),
    ("review", "v1196.5", 114),
    ("reliability", "v1196.8", 167),
):
    retained = report["retained_checkpoints"][key]
    require(retained["contract_version"] == version)
    require(retained["passed"] == total)
    require(retained["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "adversarial-privacy-authority-replay-recovery-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
require((descriptor or {}).get("builder") == "build_adversarial_privacy_authority_replay_recovery_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "adversarial-privacy-authority-checkpoint",
    "adversarial-replay-recovery-review-checkpoint",
    "adversarial-reliability-integration-checkpoint",
    "adversarial-privacy-authority-replay-recovery-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "adversarial-privacy-authority-replay-recovery-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1196-9-cli-")},
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1196.9")
    require(cli_report["summary"]["attack_class_count"] == 14)
    require(cli_report["summary"]["review_event_class_count"] == 5)
    require(cli_report["summary"]["reliability_event_class_count"] == 8)
    require(cli_report["summary"]["execution_invoked"] is False)
except Exception:
    for _ in range(6): require(False)

status, payload = dispatch_api("GET", "/api/cognition/adversarial-privacy-authority-replay-recovery-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1196.9")
require(payload["data"]["summary"]["attack_class_count"] == 14)
require(payload["data"]["summary"]["authority_domain_count"] == 16)
require(payload["data"]["summary"]["decision_count"] == 3)
require(payload["data"]["summary"]["surface_count"] == 12)
require(payload["data"]["summary"]["execution_invoked"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/adversarial-privacy-authority-replay-recovery-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("adversarial-privacy-authority-replay-recovery-checkpoint-panel" in html)
require("adversarial-privacy-authority-replay-recovery-checkpoint-state" in html)
require("adversarial-privacy-authority-replay-recovery-checkpoint-summary" in html)
require("/api/cognition/adversarial-privacy-authority-replay-recovery-checkpoint" in html)
require("next bounded unit: v1197.0-v1197.2" in html.lower())
require("no attacks" in html.lower())
require("global pass not claimed" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1196.9" in text or "v1196_9" in text)
    require("v1197.0-v1197.2" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1196.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1196.8"' in metadata)
require("Adversarial Privacy, Authority, Replay, and Recovery Checkpoint" in metadata)
require('WORKING_SOURCE_VERSION = "1196.8"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1196.5"' in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1196.9-adversarial-privacy-authority-replay-recovery-checkpoint") == 1)
require(release.count("v1196_9_adversarial_privacy_authority_replay_recovery_checkpoint_tests.py") == 1)

print(f"v1196.9 adversarial privacy authority replay recovery checkpoint: {sum(checks)}/{len(checks)} PASS")
