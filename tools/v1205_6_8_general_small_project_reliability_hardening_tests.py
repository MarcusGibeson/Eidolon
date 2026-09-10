from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

import general_small_project_implementation as unified
from grounded_development_planning import create_or_resume_grounded_plan
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from small_project_capability_registry import registry_digest

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def approved(runtime: Path, request: str, session: str) -> dict:
    created = process_ordinary_chat_development_turn(
        request,
        action_projection={"intent": {"category": "action_request"}},
        session_id=session,
        runtime_root=runtime,
    )
    require(created["active"] is True, created)
    proposal = created["proposal"]
    approved_turn = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime,
    )
    require(approved_turn["event"] == "approval_consumed", approved_turn)
    require(approved_turn["approval_consumption_count"] == 1)
    return proposal


def js_provider(calls: list[int], delay: float = 0.0):
    lock = threading.Lock()

    def generate(prompt: str) -> str:
        with lock:
            calls.append(1)
        if delay:
            time.sleep(delay)
        contract = json.loads(prompt)
        content = {
            "package.json": json.dumps({"name": "reliable-tool", "version": "1.0.0", "bin": {"reliable-tool": "cli.js"}}),
            "cli.js": "const { value } = require('./lib/tool'); if (process.argv.includes('--help')) console.log('usage'); else console.log(value);",
            "lib/tool.js": "exports.value = 1;",
            "tests/tool.test.js": "const assert=require('assert'); assert.equal(require('../lib/tool').value,1);",
        }
        return json.dumps({
            "authority": contract["authority"],
            "files": [{"path": path, "operation": "create", "content": content[path]} for path in contract["planned_paths"]],
        })

    return generate


before = source_signature()

# Twelve concurrent requests must create one coordinator record and one provider call.
runtime = Path(tempfile.mkdtemp(prefix="eid-v1205-reliable-race-"))
try:
    proposal = approved(runtime, "Build me a Node command-line tool that reports one", "race")
    calls: list[int] = []
    results: list[dict] = []
    errors: list[str] = []
    barrier = threading.Barrier(12)

    def worker():
        try:
            barrier.wait()
            results.append(unified.run_or_resume_general_small_project_implementation(
                proposal["proposal_id"],
                expected_revision=1,
                expected_revision_digest=proposal["revision_digest"],
                runtime_root=runtime,
                provider_generate=js_provider(calls, 0.08),
            ))
        except Exception:
            errors.append(traceback.format_exc())

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    require(not errors, errors)
    require(len(results) == 12, len(results))
    require(len(calls) == 1, calls)
    require(all(row.get("ok") is True for row in results), results)
    require(len({row.get("unified_result_digest") for row in results}) == 1)
    require(len({row.get("coordination_digest") for row in results}) == 1)
    require(sum(row.get("operation_status") == "created" for row in results) == 1)
    require(sum(row.get("operation_status") == "resumed" for row in results) == 11)
    path = unified._coordination_path(proposal["proposal_id"], 1, runtime)
    record = json.loads(path.read_text())
    require(record["phase"] == "sealed", record)
    require(record["attempt_count"] == 1)
    require(record["recovery_count"] == 0)
    require(record["capability_registry_digest"] == registry_digest())
    require(record["result_digest"] == unified._digest(record["result"]))
    public = unified.public_general_small_project_result(results[0])
    encoded = json.dumps(public, sort_keys=True)
    require(public["coordination_digest"] == results[0]["coordination_digest"])
    require(public["private_path_exposed"] is False)
    require(str(runtime) not in encoded)
    require("reliable-tool" not in encoded)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# An expired prepared journal is claimed once and sealed as recovered.
runtime = Path(tempfile.mkdtemp(prefix="eid-v1205-reliable-recover-"))
try:
    proposal = approved(runtime, "Build me a Node CLI utility", "recover")
    plan = create_or_resume_grounded_plan(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    capability = unified.capability_for_project_kind(plan["project_kind"])
    bindings = unified._bindings(
        proposal_id=proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"],
        planning_digest=plan["planning_digest"], project_kind=plan["project_kind"],
        capability_id=capability.capability_id, capability_registry_digest=registry_digest(),
    )
    path = unified._coordination_path(proposal["proposal_id"], 1, runtime)
    prepared = {
        "schema_version": unified.SCHEMA_VERSION, "contract_version": unified.CONTRACT_VERSION, **bindings,
        "phase": "prepared", "lease_token": "dead-owner", "lease_expires_unix": time.time() - 10,
        "attempt_count": 1, "recovery_count": 0, "provider_contacted": False,
        "selected_project_modified": False, "source_modified": False, "implementation_applied": False,
        "repair_authorized": False, "apply_authorized": False, "release_authorized": False, "authority_granted": False,
    }
    prepared["coordination_digest"] = unified._coordination_digest(prepared)
    unified._atomic_json(path, prepared)
    calls: list[int] = []
    recovered = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime, provider_generate=js_provider(calls),
    )
    require(recovered["ok"] is True, recovered)
    require(recovered["operation_status"] == "recovered", recovered)
    require(recovered["coordination_recovered"] is True)
    require(len(calls) == 1)
    sealed = json.loads(path.read_text())
    require(sealed["attempt_count"] == 2)
    require(sealed["recovery_count"] == 1)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# A live prepared lease returns an in-progress state rather than invoking a second delegate.
runtime = Path(tempfile.mkdtemp(prefix="eid-v1205-reliable-live-"))
try:
    proposal = approved(runtime, "Build me a Node CLI utility", "live")
    plan = create_or_resume_grounded_plan(proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime)
    capability = unified.capability_for_project_kind(plan["project_kind"])
    bindings = unified._bindings(
        proposal_id=proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], planning_digest=plan["planning_digest"],
        project_kind=plan["project_kind"], capability_id=capability.capability_id, capability_registry_digest=registry_digest(),
    )
    path = unified._coordination_path(proposal["proposal_id"], 1, runtime)
    prepared = {"schema_version": unified.SCHEMA_VERSION, "contract_version": unified.CONTRACT_VERSION, **bindings,
        "phase": "prepared", "lease_token": "live-owner", "lease_expires_unix": time.time() + 60,
        "attempt_count": 1, "recovery_count": 0, "provider_contacted": False, "selected_project_modified": False,
        "source_modified": False, "implementation_applied": False, "repair_authorized": False,
        "apply_authorized": False, "release_authorized": False, "authority_granted": False}
    prepared["coordination_digest"] = unified._coordination_digest(prepared)
    unified._atomic_json(path, prepared)
    old_wait = unified.COORDINATOR_WAIT_SECONDS
    unified.COORDINATOR_WAIT_SECONDS = 0.08
    calls: list[int] = []
    try:
        busy = unified.run_or_resume_general_small_project_implementation(
            proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime, provider_generate=js_provider(calls),
        )
    finally:
        unified.COORDINATOR_WAIT_SECONDS = old_wait
    require(busy["status"] == "general_coordinator_in_progress", busy)
    require(len(calls) == 0)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Tampered coordinator and result records are blocked before provider contact.
for tamper_kind in ("record", "result"):
    runtime = Path(tempfile.mkdtemp(prefix=f"eid-v1205-reliable-tamper-{tamper_kind}-"))
    try:
        proposal = approved(runtime, "Build me a Node CLI utility", f"tamper-{tamper_kind}")
        calls: list[int] = []
        result = unified.run_or_resume_general_small_project_implementation(
            proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime, provider_generate=js_provider(calls),
        )
        require(result["ok"] is True)
        path = unified._coordination_path(proposal["proposal_id"], 1, runtime)
        record = json.loads(path.read_text())
        if tamper_kind == "record":
            record["attempt_count"] = 99
        else:
            record["result"]["status"] = "forged"
            record["coordination_digest"] = unified._coordination_digest(record)
        path.write_text(json.dumps(record), encoding="utf-8")
        blocked = unified.run_or_resume_general_small_project_implementation(
            proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime, provider_generate=js_provider(calls),
        )
        require(blocked["ok"] is False)
        require(blocked["status"] in {"general_coordinator_record_invalid", "general_coordinator_result_invalid"}, blocked)
        require(len(calls) == 1)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)

# Invalid registry and mid-operation registry drift block authority.
runtime = Path(tempfile.mkdtemp(prefix="eid-v1205-reliable-registry-"))
try:
    proposal = approved(runtime, "Build me a Node CLI utility", "registry")
    original_safe_registry = unified._safe_registry
    original_delegate = unified._delegate
    unified._safe_registry = lambda: (False, "")
    calls: list[int] = []
    invalid = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime, provider_generate=js_provider(calls),
    )
    require(invalid["status"] == "small_project_capability_registry_invalid", invalid)
    require(len(calls) == 0)
    shutil.rmtree(runtime, ignore_errors=True)
    runtime.mkdir()
    proposal = approved(runtime, "Build me a Node CLI utility", "registry-drift")
    sequence = iter([(True, registry_digest()), (True, "f" * 64)])
    unified._safe_registry = lambda: next(sequence)
    unified._delegate = lambda *args, **kwargs: {"ok": True, "status": "javascript_tool_checkpoint_ready", "provider_contacted": True}
    drift = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(drift["status"] == "general_coordinator_registry_changed", drift)
    record = json.loads(unified._coordination_path(proposal["proposal_id"], 1, runtime).read_text())
    require(record["phase"] == "blocked")
finally:
    unified._safe_registry = original_safe_registry
    unified._delegate = original_delegate
    shutil.rmtree(runtime, ignore_errors=True)

# Delegate exceptions are reduced to a digest-only failure and persist idempotently.
runtime = Path(tempfile.mkdtemp(prefix="eid-v1205-reliable-failure-"))
try:
    proposal = approved(runtime, "Build me a Node CLI utility", "failure")
    original_delegate = unified._delegate
    unified._delegate = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("private failure path /secret/operator/project"))
    failed = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(failed["status"] == "general_coordinator_delegate_failed", failed)
    require(bool(failed["failure_digest"]))
    public = unified.public_general_small_project_result(failed)
    require("/secret/operator/project" not in json.dumps(public))
    resumed = unified.run_or_resume_general_small_project_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(resumed["failure_digest"] == failed["failure_digest"])
    require(resumed["operation_status"] == "resumed")
finally:
    unified._delegate = original_delegate
    shutil.rmtree(runtime, ignore_errors=True)

# Static release, privacy, and authority contracts.
source = (ROOT / "conscious_agent/general_small_project_implementation.py").read_text(encoding="utf-8")
require('CONTRACT_VERSION = "v1205.8"' in source)
require('"phase": "prepared"' in source)
require('"phase": "sealed"' in source)
require("COORDINATOR_LEASE_SECONDS" in source)
require("general_coordinator_registry_changed" in source)
require("private exception text is reduced to a digest-only receipt" in source)
verifier = (ROOT / "tools/post_review_development_verify.py").read_text(encoding="utf-8")
require("v1205.6-v1205.8" in verifier)
require("v1205_6_8_general_small_project_reliability_hardening_tests.py" in verifier)
release = (ROOT / "tools/release_verify.py").read_text(encoding="utf-8")
require(release.count("v1205.8-general-small-project-reliability-hardening") == 2)
metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1205.8"' in metadata)
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "version": "1205.8",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "concurrent_requests": 12,
    "provider_calls": 1,
    "prepared_journal_recovery": True,
    "registry_drift_blocked": True,
    "tamper_blocked": True,
    "selected_project_modified": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "release_authorized": False,
    "authority_granted": False,
}, sort_keys=True))
