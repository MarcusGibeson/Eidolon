from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1215-c-data-"))
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

import conversational_supervised_repair_execution as repair
from ordinary_chat_development_campaign import _atomic_json, process_ordinary_chat_development_turn
from v1215_supervised_repair_fixture import build_authorized_repair_fixture, provider_output

checks: list[bool] = []


def require(value, detail=None):
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


# Live leases block duplicate execution without provider contact.
fixture = build_authorized_repair_fixture("c")
runtime = fixture["runtime"]
calls: list[int] = []
try:
    proposal = fixture["proposal"]
    bounded = fixture["repair_proposal"]
    prepared = repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"], runtime_root=runtime,
    )
    path = repair._execution_path(proposal["proposal_id"], 1, 2, runtime)
    running = json.loads(path.read_text(encoding="utf-8"))
    running.update({
        "phase": "running", "status": "supervised_repair_running",
        "lease_token": "live", "lease_expires_unix": time.time() + 60,
        **repair._authority(authorized=True),
    })
    _atomic_json(path, repair._seal(running))
    blocked = repair.authorize_and_run_conversational_supervised_repair(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        authorization_phrase=bounded["authorization_phrase"], runtime_root=runtime,
        provider_generate=lambda prompt: calls.append(1) or provider_output(prompt, repaired=True),
        python_executable=sys.executable,
    )
    require(blocked["status"] == "supervised_repair_in_progress", blocked)
    require(calls == [])
    require(blocked["apply_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Expired leases recover under the same authorization and then seal once.
fixture = build_authorized_repair_fixture("d")
runtime = fixture["runtime"]
calls = []
try:
    proposal = fixture["proposal"]
    bounded = fixture["repair_proposal"]
    prepared = repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"], runtime_root=runtime,
    )
    path = repair._execution_path(proposal["proposal_id"], 1, 2, runtime)
    running = json.loads(path.read_text(encoding="utf-8"))
    running.update({
        "phase": "running", "status": "supervised_repair_running",
        "lease_token": "expired", "lease_expires_unix": time.time() - 1,
        **repair._authority(authorized=True),
    })
    _atomic_json(path, repair._seal(running))
    recovered = repair.authorize_and_run_conversational_supervised_repair(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        authorization_phrase=bounded["authorization_phrase"], runtime_root=runtime,
        provider_generate=lambda prompt: calls.append(1) or provider_output(prompt, repaired=True),
        python_executable=sys.executable,
    )
    require(recovered["status"] == "supervised_repair_completed", recovered)
    require(recovered["operation_status"] == "recovered")
    require(recovered["recovery_count"] == 1)
    require(len(calls) == 1)
    replay = repair.authorize_and_run_conversational_supervised_repair(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        authorization_phrase=bounded["authorization_phrase"], runtime_root=runtime,
        provider_generate=lambda prompt: calls.append(1) or provider_output(prompt, repaired=True),
        python_executable=sys.executable,
    )
    require(replay["operation_status"] == "resumed")
    require(len(calls) == 1)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Execution-record and proposal tampering fail closed.
fixture = build_authorized_repair_fixture("e")
runtime = fixture["runtime"]
try:
    proposal = fixture["proposal"]
    bounded = fixture["repair_proposal"]
    repair.prepare_conversational_supervised_repair_execution(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"], runtime_root=runtime,
    )
    path = repair._execution_path(proposal["proposal_id"], 1, 2, runtime)
    damaged = json.loads(path.read_text(encoding="utf-8"))
    damaged["repair_attempt_limit"] = 99
    damaged["apply_authorized"] = True
    _atomic_json(path, damaged)
    require(repair.load_conversational_supervised_repair_execution(
        proposal["proposal_id"], 1, 2, runtime_root=runtime
    ) == {})
    blocked = repair.authorize_and_run_conversational_supervised_repair(
        proposal["proposal_id"], expected_revision=1, expected_attempt_number=2,
        expected_repair_proposal_digest=bounded["repair_proposal_digest"],
        authorization_phrase=bounded["authorization_phrase"], runtime_root=runtime,
    )
    require(blocked["status"] == "supervised_repair_execution_record_invalid")
    require(blocked["apply_authorized"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)


# Stale digests and private provider errors expose neither data nor authority.
fixture = build_authorized_repair_fixture("f")
runtime = fixture["runtime"]
try:
    bounded = fixture["repair_proposal"]
    stale_phrase = bounded["authorization_phrase"].replace(
        bounded["repair_proposal_digest"], "0" * 64
    )
    stale = process_ordinary_chat_development_turn(stale_phrase, runtime_root=runtime)
    require(stale["event"] == "supervised_repair_stale_authorization", stale)
    require(stale["supervised_repair_execution"]["repair_execution_authorized"] is False)

    def private_failure(prompt: str) -> str:
        raise RuntimeError(r"C:\Users\private\secret-project\prompt-and-code.txt")

    failed = process_ordinary_chat_development_turn(
        bounded["authorization_phrase"], runtime_root=runtime,
        provider_generate=private_failure, python_executable=sys.executable,
    )
    encoded = json.dumps(failed, sort_keys=True)
    require(failed["event"] in {"supervised_repair_build_blocked", "supervised_repair_internal_error"}, failed)
    require("Users" not in encoded)
    require("secret-project" not in encoded)
    require("prompt-and-code" not in encoded)
    require(failed["supervised_repair_execution"]["private_path_exposed"] is False)
    require(failed["supervised_repair_execution"]["raw_provider_output_exposed"] is False)
    require(failed["supervised_repair_execution"]["apply_authorized"] is False)
    require(failed["supervised_repair_execution"]["release_authorized"] is False)
    require(failed["supervised_repair_execution"]["authority_granted"] is False)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

source = (ROOT / "conscious_agent" / "conversational_supervised_repair_execution.py").read_text(encoding="utf-8")
require("run_or_resume_general_small_project_implementation" not in source)
require("run_or_resume_selected_test_adapter" not in source)
require("authorize_and_run_conversational_build_test_loop" in source)
require('"apply_authorized": True' not in source)
require('"release_authorized": True' not in source)
require('"authority_granted": True' not in source)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count('"v1215.8-supervised-repair-execution-reliability"') == 2)
require(release.count("tools/v1215_6_8_supervised_repair_execution_reliability_tests.py") == 1)

print(json.dumps({
    "ok": True,
    "version": "1215.8",
    "checks": len(checks),
    "passed": sum(checks),
    "duplicate_blocked": True,
    "expired_lease_recovered": True,
    "tamper_rejected": True,
    "private_error_exposed": False,
    "apply_authorized": False,
}, sort_keys=True))
