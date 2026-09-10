from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from ordinary_chat_development_campaign import (
    list_development_campaign_proposals,
    process_ordinary_chat_development_turn,
)
from small_website_implementation_checkpoint import (
    _checkpoint_path,
    create_or_resume_small_website_checkpoint,
    load_small_website_checkpoint,
    public_small_website_checkpoint,
    run_or_resume_small_website_implementation,
)
from bounded_workspace_validation import _validation_path
from ordinary_chat_development_campaign import _digest

start = time.monotonic()
checks: list[bool] = []


def require(value: object, detail: object = None) -> None:
    checks.append(bool(value))
    if not value:
        raise AssertionError(detail)


def source_signature() -> str:
    digest = hashlib.sha256()
    excluded = {"data", "__pycache__", ".pytest_cache", ".git", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def provider(counter: list[int], *, javascript: str = "const tasks = [];\n"):
    def generate(prompt: str) -> str:
        counter.append(1)
        payload = json.loads(prompt)
        authority = payload["authority"]
        files = []
        for path in payload["planned_paths"]:
            if path == "index.html":
                content = "<!doctype html><html><head><title>Tasks</title><meta name=\"viewport\" content=\"width=device-width\"><link rel=\"stylesheet\" href=\"styles.css\"></head><body><main id=\"app\"></main><script src=\"app.js\"></script></body></html>"
            elif path == "styles.css":
                content = "body{font-family:sans-serif;margin:2rem}"
            elif path == "app.js":
                content = javascript
            elif path == "tests/app.test.js":
                content = "const assert = require('node:assert'); assert.equal(1, 1);\n"
            else:
                content = ""
            files.append({"path": path, "operation": "create", "content": content})
        return json.dumps({"authority": authority, "files": files})
    return generate


def approved(runtime: Path):
    projection = process_ordinary_chat_development_turn(
        "Build me a to-do webpage",
        action_projection={"intent": {"category": "action_request"}},
        session_id="checkpoint-session",
        runtime_root=runtime,
    )
    require(projection["active"])
    require(projection["event"] == "proposal_created")
    proposal = projection["proposal"]
    approval = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime,
    )
    require(approval["event"] == "approval_consumed")
    require(approval["approval_consumption_count"] == 1)
    return proposal


before = source_signature()
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1201-9-runtime-"))
try:
    proposal = approved(runtime)
    calls: list[int] = []
    result = run_or_resume_small_website_implementation(
        proposal["proposal_id"],
        expected_revision=proposal["revision"],
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime,
        provider_generate=provider(calls),
    )
    require(result["ok"])
    require(result["status"] == "small_website_implementation_ready_for_operator_review")
    require(result["operation_status"] == "created")
    require(len(calls) == 1)
    require(result["stage_count"] == 7)
    require([row["stage"] for row in result["stage_receipts"]] == ["proposal", "approval", "planning", "generation", "workspace", "preview", "validation"])
    require(all(row["passed"] for row in result["stage_receipts"]))
    require(len({row["stage_receipt_digest"] for row in result["stage_receipts"]}) == 7)
    require(result["change_summary"]["file_count"] == 3)
    require(result["change_summary"]["create_count"] == 3)
    require(result["change_summary"]["modify_count"] == 0)
    require(result["change_summary"]["delete_count"] == 0)
    require(result["test_summary"]["passed"])
    require(result["test_summary"]["adapter_count"] == 2)
    require(result["test_summary"]["command_count"] == 1)
    require(result["working_result_available"])
    require(result["operator_review_required"])
    require(not result["implementation_applied"])
    require(not result["apply_authorized"])
    require(not result["repair_authorized"])
    require(not result["selected_project_modified"])
    require(not result["source_modified"])
    require(not result["release_authorized"])
    require(not result["authority_granted"])
    catalog = list_development_campaign_proposals(runtime_root=runtime, public=True)
    require(catalog["proposal_count"] == 1)
    require(catalog["proposals"][0]["current_stage"] == "small_website_checkpoint_ready")
    require(catalog["proposals"][0]["implementation_started"] is True)
    require(catalog["proposals"][0]["workspace_created"] is True)
    require(catalog["proposals"][0]["tests_executed"] is True)

    public = public_small_website_checkpoint(result)
    encoded = json.dumps(public, sort_keys=True)
    require(public["working_result_available"])
    require(public["preview_url"].startswith("/development-preview/"))
    require("Build me" not in encoded)
    require("index.html" not in encoded)
    require("const tasks" not in encoded)
    require(str(runtime) not in encoded)
    require(not public["private_request_exposed"])
    require(not public["private_path_exposed"])
    require(not public["private_content_exposed"])
    require(not public["raw_provider_output_exposed"])

    resumed = run_or_resume_small_website_implementation(
        proposal["proposal_id"],
        expected_revision=proposal["revision"],
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime,
        provider_generate=provider(calls),
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["checkpoint_digest"] == result["checkpoint_digest"])
    require(len(calls) == 1)
    require(load_small_website_checkpoint(proposal["proposal_id"], 1, runtime)["checkpoint_digest"] == result["checkpoint_digest"])

    stale = run_or_resume_small_website_implementation(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest="0" * 64,
        runtime_root=runtime,
        provider_generate=provider(calls),
    )
    require(not stale["ok"])
    require(stale["status"] == "stale_proposal_revision")
    require(len(calls) == 1)

    checkpoint_path = _checkpoint_path(proposal["proposal_id"], 1, runtime)
    raw = json.loads(checkpoint_path.read_text())
    raw["operator_review_required"] = False
    checkpoint_path.write_text(json.dumps(raw), encoding="utf-8")
    invalid = create_or_resume_small_website_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(invalid["status"] == "implementation_checkpoint_invalid")
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Failed validation is evidence, not automatic repair or checkpoint success.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1201-9-failed-"))
try:
    proposal = approved(runtime)
    calls: list[int] = []
    result = run_or_resume_small_website_implementation(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime,
        provider_generate=provider(calls, javascript="const = ;\n"),
    )
    require(not result["ok"])
    require(result["status"] == "validation_not_passed")
    require(result["failed_stage"] == "validation")
    require(not result["repair_authorized"])
    require(not _checkpoint_path(proposal["proposal_id"], 1, runtime).exists())
    require(len(calls) == 1)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Duplicate tabs/threads converge on one provider call and one checkpoint record.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1201-9-race-"))
try:
    proposal = approved(runtime)
    calls: list[int] = []
    outcomes: list[dict] = []
    barrier = threading.Barrier(8)
    lock = threading.Lock()
    generate = provider(calls)

    def worker() -> None:
        barrier.wait()
        value = run_or_resume_small_website_implementation(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            runtime_root=runtime,
            provider_generate=generate,
        )
        with lock:
            outcomes.append(value)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    require(len(outcomes) == 8)
    require(all(value.get("ok") for value in outcomes), outcomes)
    require(len({value.get("checkpoint_digest") for value in outcomes}) == 1)
    require(len(calls) == 1)
    require(sum(value.get("operation_status") == "created" for value in outcomes) == 1)
    require(sum(value.get("operation_status") == "resumed" for value in outcomes) == 7)
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# A resealed stale validation binding is rejected before an existing checkpoint can be trusted.
runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1201-9-binding-"))
try:
    proposal = approved(runtime)
    result = run_or_resume_small_website_implementation(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime, provider_generate=provider([]),
    )
    require(result["ok"])
    path = _validation_path(proposal["proposal_id"], 1, runtime)
    validation = json.loads(path.read_text())
    validation["preview_digest"] = "f" * 64
    validation.pop("validation_digest", None)
    validation["validation_digest"] = _digest(validation)
    path.write_text(json.dumps(validation), encoding="utf-8")
    rejected = create_or_resume_small_website_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(rejected["status"] == "validation_binding_rejected")
finally:
    shutil.rmtree(runtime, ignore_errors=True)

# Dashboard, metadata, release stage, documentation, source/runtime separation.
dashboard = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
require("/api/development-campaign/implement-small-website" in dashboard)
require("Build isolated website" in dashboard)
require("small website checkpoint" in dashboard.lower())
require("@media(max-width:760px)" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1201.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1201.8"' in metadata)
release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1201.9-small-website-implementation-checkpoint") == 2)
require(release_verify.count("tools/v1201_9_small_website_implementation_checkpoint_tests.py") == 1)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1201.9" in next_steps and "v1202.0-v1202.2" in next_steps)
require("v1201.9 Small Website Implementation Checkpoint" in history)
require(not (ROOT / "data" / "development_campaigns").exists())
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "suite": "v1201.9-small-website-implementation-checkpoint",
    "checks": len(checks),
    "passed": sum(checks),
    "elapsed_seconds": round(time.monotonic() - start, 4),
    "provider_calls_in_duplicate_race": 1,
    "source_modified": False,
    "selected_project_modified": False,
    "implementation_applied": False,
    "repair_authorized": False,
    "release_authorized": False,
    "authority_expanded": False,
}, sort_keys=True))
