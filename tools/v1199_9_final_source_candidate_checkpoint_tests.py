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
from conscious_agent.final_source_candidate_checkpoint import (
    CONTRACT_VERSION,
    _digest,
    _validate_snapshot,
    build_final_source_candidate_checkpoint,
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
report = build_final_source_candidate_checkpoint(source_root=ROOT)
after = tree_signature(ROOT)
require(report["ok"] is True)
require(report["contract_version"] == CONTRACT_VERSION == "v1199.9")
require(report["checkpoint_id"] == "final-source-candidate:v1199.9")
require(report["read_only"] is True)
require(report["post_available"] is False)
require(report["content_free"] is True)
require(report["source_only"] is True)
require(report["source_unchanged"] is True)
require(before == after)
require(report["passed"] == report["total"])
require(report["total"] >= 90)
require(len(report["limitations"]) == 5)
require(report["privacy"]["ok"] is True)
require(report["privacy"].get("forbidden_count", 0) == 0)

summary = report["summary"]
for field in (
    "content_free", "read_only", "source_only", "privacy_preserved",
    "authority_boundary_preserved", "original_candidate_preserved",
    "retained_verification_preserved", "unresolved_risks_preserved",
    "desktop_handoff_preserved", "native_provider_handoff_preserved",
    "operator_review_accountable", "exact_review_lineage_verified",
    "exact_reliability_lineage_verified", "foreground_available",
    "historical_truth_preserved", "current_regressions_separate",
    "inherited_debt_visible", "v1200_gate_required", "source_unchanged",
):
    require(summary[field] is True)
for field in (
    "candidate_prepared", "candidate_accepted", "handoff_accepted",
    "risk_waived", "release_approved", "global_profile_pass_claimed",
    "verifier_executed", "candidate_modified", "source_modified",
    "runtime_mutated", "approval_created", "approval_consumed",
    "provider_contacted", "model_contacted", "process_started",
    "thread_started", "automatic_continuation", "automatic_recovery",
    "installation_performed", "promotion_performed",
    "certification_performed", "publication_performed",
    "release_performed", "authority_granted",
):
    require(summary[field] is False)
require(summary["authority_state"] == "separate_not_granted")
require(summary["preparation_contract_version"] == "v1199.2")
require(summary["review_contract_version"] == "v1199.5")
require(summary["reliability_contract_version"] == "v1199.8")
for field, expected in (
    ("retained_checkpoint_count", 3),
    ("preparation_area_count", 8),
    ("manifest_count", 8),
    ("verification_count", 6),
    ("risk_count", 2),
    ("blocking_risk_count", 2),
    ("review_action_count", 5),
    ("decision_count", 3),
    ("review_count", 15),
    ("reliability_event_class_count", 8),
    ("reliability_event_count", 8),
):
    require(summary[field] == expected)

snapshot_for_validation = dict(summary); snapshot_for_validation.pop("blocked_case_count", None)
require(not _validate_snapshot(snapshot_for_validation))
for name, errors in report["blocked_cases"].items():
    require(bool(name)); require(bool(errors))
require(len(report["blocked_cases"]) >= 55)
require("checkpoint_tamper" in report["blocked_cases"]["tamper"])

for field, value in (
    ("privacy_preserved", False), ("original_candidate_preserved", False),
    ("retained_verification_preserved", False), ("unresolved_risks_preserved", False),
    ("desktop_handoff_preserved", False), ("native_provider_handoff_preserved", False),
    ("operator_review_accountable", False), ("exact_review_lineage_verified", False),
    ("exact_reliability_lineage_verified", False), ("foreground_available", False),
    ("historical_truth_preserved", False), ("inherited_debt_visible", False),
    ("v1200_gate_required", False), ("candidate_accepted", True),
    ("handoff_accepted", True), ("risk_waived", True),
    ("global_profile_pass_claimed", True), ("verifier_executed", True),
    ("candidate_modified", True), ("source_modified", True),
    ("runtime_mutated", True), ("release_performed", True),
    ("authority_granted", True),
):
    candidate = dict(snapshot_for_validation); candidate[field] = value
    candidate["checkpoint_digest"] = _digest({k: v for k, v in candidate.items() if k != "checkpoint_digest"})
    require(bool(_validate_snapshot(candidate)))

for key, version, total in (
    ("preparation", "v1199.2", 30),
    ("review", "v1199.5", 160),
    ("reliability", "v1199.8", 167),
):
    retained = report["retained_checkpoints"][key]
    require(retained["contract_version"] == version)
    require(retained["passed"] == retained["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "final-source-candidate-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1199.9")
require((descriptor or {}).get("builder") == "build_final_source_candidate_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "final-source-candidate-preparation-checkpoint",
    "final-candidate-review-checkpoint",
    "final-candidate-reliability-checkpoint",
    "final-source-candidate-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "final-source-candidate-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1199-9-cli-")},
)
require(process.returncode == 0)
try:
    cli = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli["ok"] is True)
    require(cli["contract_version"] == "v1199.9")
    require(cli["summary"]["manifest_count"] == 8)
    require(cli["summary"]["review_count"] == 15)
    require(cli["summary"]["reliability_event_count"] == 8)
    require(cli["summary"]["v1200_gate_required"] is True)
    require(cli["summary"]["release_performed"] is False)
except Exception:
    for _ in range(7): require(False)

status, payload = dispatch_api("GET", "/api/cognition/final-source-candidate-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1199.9")
require(payload["data"]["summary"]["manifest_count"] == 8)
require(payload["data"]["summary"]["review_count"] == 15)
require(payload["data"]["summary"]["reliability_event_count"] == 8)
status_post, payload_post = dispatch_api("POST", "/api/cognition/final-source-candidate-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
for token in (
    "final-source-candidate-checkpoint-panel",
    "final-source-candidate-checkpoint-state",
    "final-source-candidate-checkpoint-summary",
    "/api/cognition/final-source-candidate-checkpoint",
):
    require(token in html)
require("v1200" in html)
require("global pass not claimed" in html.lower())
require("no candidate or handoff is accepted" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1199.9" in text or "v1199_9" in text)
    require("v1200" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1199.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1199.8"' in metadata)
require("Final Source-Only Candidate Checkpoint" in metadata)
for marker in ('WORKING_SOURCE_VERSION = "1199.8"', 'WORKING_SOURCE_VERSION = "1199.5"', 'WORKING_SOURCE_VERSION = "1199.2"'):
    require(marker in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1199.9-final-source-candidate-checkpoint") == 1)
require(release.count("v1199_9_final_source_candidate_checkpoint_tests.py") == 1)
require(release.count("v1199.8-final-candidate-reliability") == 1)

print(f"v1199.9 final source-only candidate checkpoint: {sum(checks)}/{len(checks)} PASS")
