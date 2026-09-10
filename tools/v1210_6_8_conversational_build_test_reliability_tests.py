from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import conversational_build_test_loop as loop
from ordinary_chat_development_campaign import _atomic_json, create_or_resume_development_proposal, approve_development_campaign_proposal

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def prepared_runtime():
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1210-c-"))
    proposal = create_or_resume_development_proposal("Build me a Python CLI that counts words", runtime_root=runtime)
    approve_development_campaign_proposal(proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime)
    prepared = loop.prepare_conversational_build_test_loop(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    return runtime, proposal, prepared


# Tampered records fail closed and never run a provider or adapter.
runtime, proposal, prepared = prepared_runtime()
try:
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["selected_adapter_id"] = "browser_runtime"
    _atomic_json(path, record)
    blocked = loop.authorize_and_run_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_loop_digest=prepared["loop_digest"], authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
    )
    require(blocked["status"] == "conversational_build_test_loop_record_invalid", blocked)
    require(blocked["provider_contacted"] is False)
    require(blocked["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# A live lease blocks a duplicate; an expired lease is recoverable and remains
# bound to the same loop digest.
runtime, proposal, prepared = prepared_runtime()
try:
    path = loop._loop_path(proposal["proposal_id"], 1, runtime)
    current = json.loads(path.read_text(encoding="utf-8"))
    current.update({"phase": "running", "status": "conversational_build_test_running", "lease_token": "live", "lease_expires_unix": time.time() + 60, "attempt_count": 1, "build_authorized": True, "test_execution_authorized": True})
    _atomic_json(path, loop._seal(current))
    live = loop.authorize_and_run_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], expected_loop_digest=prepared["loop_digest"], authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
    )
    require(live["status"] == "conversational_build_test_in_progress")
    require(live["tests_executed"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Exceptions are reduced to a digest-only internal-error result and sealed for
# deterministic replay without private exception/path leakage.
runtime, proposal, prepared = prepared_runtime()
import general_small_project_implementation as coordinator
original = coordinator.run_or_resume_general_small_project_implementation
try:
    coordinator.run_or_resume_general_small_project_implementation = lambda *a, **k: (_ for _ in ()).throw(RuntimeError(f"private {runtime}"))
    failed = loop.authorize_and_run_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], expected_loop_digest=prepared["loop_digest"], authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
    )
    require(failed["status"] == "conversational_build_test_internal_error", failed)
    require(str(runtime) not in json.dumps(loop.public_conversational_build_test_loop(failed), sort_keys=True))
    replay = loop.authorize_and_run_conversational_build_test_loop(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], expected_loop_digest=prepared["loop_digest"], authorization_phrase=prepared["authorization_phrase"], runtime_root=runtime,
    )
    require(replay["operation_status"] == "resumed")
finally:
    coordinator.run_or_resume_general_small_project_implementation = original
    shutil.rmtree(runtime, ignore_errors=True)

source = (ROOT / "conscious_agent" / "conversational_build_test_loop.py").read_text(encoding="utf-8")
for forbidden in ("diagnosis_authorized\": True", "repair_authorized\": True", "apply_authorized\": True", "release_authorized\": True"):
    require(forbidden not in source)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1210.8-conversational-build-test-reliability"') == 2)
require(release.count("tools/v1210_6_8_conversational_build_test_reliability_tests.py") == 1)
print(json.dumps({"ok": True, "version": "1210.8", "checks": len(checks), "passed": sum(checks), "tamper_rejected": True, "duplicate_blocked": True, "private_error_exposed": False, "repair_authorized": False, "apply_authorized": False}, sort_keys=True))

