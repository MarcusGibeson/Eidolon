from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, list_development_campaign_proposals
from selected_project_apply import create_or_resume_rollback_request, authorize_and_rollback_selected_project
from selected_project_apply_rollback_checkpoint import (
    _apply_checkpoint_path,
    _rollback_checkpoint_path,
    load_selected_project_apply_rollback_checkpoint,
    public_selected_project_apply_rollback_checkpoint,
    seal_or_resume_selected_project_apply_rollback_checkpoint,
)

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


# Reuse the complete v1204.8 deterministic fixture and reliability floor.
with contextlib.redirect_stdout(io.StringIO()):
    prior = runpy.run_path(str(ROOT / "tools/v1204_6_8_selected_project_apply_rollback_reliability_tests.py"))
prepared = prior["prepared"]
sig = prior["sig"]


def seal_apply(rt: Path, proposal: dict, request: dict, applied: dict) -> dict:
    return seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"],
        expected_apply_result_digest=applied["apply_result_digest"],
        runtime_root=rt,
    )


# Applied checkpoint seals eight exact stages and projects content-free evidence.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-apply-"))
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-apply")
    after = sig(project)
    checkpoint = seal_apply(rt, proposal, request, applied)
    require(checkpoint["ok"] is True, checkpoint)
    require(checkpoint["status"] == "selected_project_apply_checkpoint_ready")
    require(checkpoint["checkpoint_phase"] == "applied")
    require(checkpoint["stage_count"] == 8)
    require([row["sequence"] for row in checkpoint["stage_receipts"]] == list(range(1, 9)))
    require([row["stage"] for row in checkpoint["stage_receipts"]] == [
        "implementation_checkpoint", "selected_project_snapshot", "apply_request", "apply_authorization",
        "rollback_preparation", "apply_journal", "apply_result", "project_state",
    ])
    require(checkpoint["stage_lineage_digest"] == _digest(checkpoint["stage_receipts"]))
    require(checkpoint["apply_authorization_consumption_count"] == 1)
    require(checkpoint["selected_project_modified"] is True)
    require(checkpoint["implementation_applied"] is True)
    require(checkpoint["rollback_prepared"] is True)
    require(checkpoint["rollback_available"] is True)
    require(checkpoint["rollback_authorized"] is False)
    require(checkpoint["release_authorized"] is False)
    require(checkpoint["authority_granted"] is False)
    require(sig(project) == after and after != before)
    require(len(calls) == 1)

    resumed = seal_apply(rt, proposal, request, applied)
    require(resumed["operation_status"] == "resumed")
    require(resumed["checkpoint_digest"] == checkpoint["checkpoint_digest"])
    require(len(calls) == 1)

    public = public_selected_project_apply_rollback_checkpoint(checkpoint)
    encoded = json.dumps(public, sort_keys=True)
    require(str(project) not in encoded)
    require("main.py" not in encoded)
    require("count_words" not in encoded)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(public["rollback_content_exposed"] is False)
    require(public["authorization_phrase_exposed"] is False)

    rows = list_development_campaign_proposals(runtime_root=rt, public=True)["proposals"]
    row = next(item for item in rows if item["proposal_id"] == proposal["proposal_id"])
    require(row["selected_project_apply_rollback_checkpoint"]["checkpoint_digest"] == checkpoint["checkpoint_digest"])
    require(row["current_stage"] == "selected_project_apply_checkpoint_ready")
    require(row["selected_project_modified"] is True)

    stale = seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"], expected_apply_result_digest="f" * 64,
        runtime_root=rt,
    )
    require(stale["status"] == "stale_selected_project_checkpoint")
finally:
    shutil.rmtree(rt, ignore_errors=True)


# Rollback checkpoint extends the immutable applied lineage to thirteen stages.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-rollback-"))
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-rollback")
    applied_checkpoint = seal_apply(rt, proposal, request, applied)
    rollback_request = create_or_resume_rollback_request(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_apply_result_digest=applied["apply_result_digest"], runtime_root=rt,
    )
    phrase = f"ROLLBACK {proposal['proposal_id']} REVISION 1 REQUEST {rollback_request['rollback_request_digest']}"
    rolled_back = authorize_and_rollback_selected_project(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"], authorization_phrase=phrase,
        runtime_root=rt,
    )
    require(rolled_back["ok"] is True, rolled_back)
    require(sig(project) == before)
    final = seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"], expected_apply_result_digest=applied["apply_result_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"],
        expected_rollback_result_digest=rolled_back["rollback_result_digest"], runtime_root=rt,
    )
    require(final["ok"] is True, final)
    require(final["status"] == "selected_project_apply_rollback_checkpoint_ready")
    require(final["checkpoint_phase"] == "rolled_back")
    require(final["stage_count"] == 13)
    require(final["apply_checkpoint_digest"] == applied_checkpoint["checkpoint_digest"])
    require(final["stage_receipts"][:8] == applied_checkpoint["stage_receipts"])
    require([row["stage"] for row in final["stage_receipts"][8:]] == [
        "rollback_request", "rollback_authorization", "rollback_journal", "rollback_result", "final_project_state",
    ])
    require(final["stage_lineage_digest"] == _digest(final["stage_receipts"]))
    require(final["apply_authorization_consumption_count"] == 1)
    require(final["rollback_authorization_consumption_count"] == 1)
    require(final["selected_project_modified"] is False)
    require(final["implementation_applied"] is False)
    require(final["rollback_authorized"] is True)
    require(final["rollback_executed"] is True)
    require(final["rollback_available"] is False)
    require(final["observed_project_scope"] == "original")
    require(final["release_authorized"] is False)
    require(final["authority_granted"] is False)

    loaded = load_selected_project_apply_rollback_checkpoint(proposal["proposal_id"], 1, rt)
    require(loaded["checkpoint_digest"] == final["checkpoint_digest"])
    require(loaded["checkpoint_phase"] == "rolled_back")
    resumed = seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"], expected_apply_result_digest=applied["apply_result_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"],
        expected_rollback_result_digest=rolled_back["rollback_result_digest"], runtime_root=rt,
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["checkpoint_digest"] == final["checkpoint_digest"])

    incomplete = seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"], expected_apply_result_digest=applied["apply_result_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"], runtime_root=rt,
    )
    require(incomplete["status"] == "complete_rollback_binding_required")
finally:
    shutil.rmtree(rt, ignore_errors=True)


# A completed rollback can reconstruct the missing apply checkpoint from fully bound historical receipts.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-direct-rollback-"))
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-direct-rollback")
    rollback_request = create_or_resume_rollback_request(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_apply_result_digest=applied["apply_result_digest"], runtime_root=rt,
    )
    phrase = f"ROLLBACK {proposal['proposal_id']} REVISION 1 REQUEST {rollback_request['rollback_request_digest']}"
    rolled_back = authorize_and_rollback_selected_project(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"], authorization_phrase=phrase,
        runtime_root=rt,
    )
    require(not _apply_checkpoint_path(proposal["proposal_id"], 1, rt).exists())
    final = seal_or_resume_selected_project_apply_rollback_checkpoint(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"],
        expected_implementation_checkpoint_digest=request["implementation_checkpoint_digest"],
        expected_apply_request_digest=request["apply_request_digest"], expected_apply_result_digest=applied["apply_result_digest"],
        expected_rollback_request_digest=rollback_request["rollback_request_digest"],
        expected_rollback_result_digest=rolled_back["rollback_result_digest"], runtime_root=rt,
    )
    require(final["ok"] is True, final)
    require(final["checkpoint_phase"] == "rolled_back")
    reconstructed = _read_json(_apply_checkpoint_path(proposal["proposal_id"], 1, rt))
    require(reconstructed["state_evidence_mode"] == "historical_apply_and_rollback_receipts")
    require(reconstructed["observed_project_scope"] == "generated")
    require(reconstructed["stage_receipts"][7]["status"] == "project_state_generated_before_authorized_rollback")
    require(sig(project) == before)
finally:
    shutil.rmtree(rt, ignore_errors=True)


# Eight concurrent checkpoint requests converge on one immutable record.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-race-"))
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-race")
    barrier = threading.Barrier(8)
    output: list[dict] = []
    output_lock = threading.Lock()

    def worker():
        barrier.wait()
        item = seal_apply(rt, proposal, request, applied)
        with output_lock:
            output.append(item)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [thread.start() for thread in threads]
    [thread.join(30) for thread in threads]
    require(len(output) == 8)
    require(all(item.get("ok") is True for item in output))
    require(len({item["checkpoint_digest"] for item in output}) == 1)
    require(sum(item["operation_status"] == "created" for item in output) == 1)
    require(sum(item["operation_status"] == "resumed" for item in output) == 7)
    require(all(item["apply_authorization_consumption_count"] == 1 for item in output))
    require(len(calls) == 1)
finally:
    shutil.rmtree(rt, ignore_errors=True)


# Tampered checkpoint records are blocked rather than projected as trusted evidence.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-tamper-"))
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-tamper")
    checkpoint = seal_apply(rt, proposal, request, applied)
    path = _apply_checkpoint_path(proposal["proposal_id"], 1, rt)
    tampered = _read_json(path)
    tampered["observed_project_scope"] = "invented"
    _atomic_json(path, tampered)
    blocked = seal_apply(rt, proposal, request, applied)
    require(blocked["status"] == "selected_project_checkpoint_invalid")
    require(load_selected_project_apply_rollback_checkpoint(proposal["proposal_id"], 1, rt) == {})
finally:
    shutil.rmtree(rt, ignore_errors=True)


# Real POST-only dashboard finalization returns content-free checkpoint evidence.
rt = Path(tempfile.mkdtemp(prefix="eid-v1204-9-http-"))
process = None
try:
    project, proposal, request, applied, before, calls = prepared(rt, "checkpoint-http")
    port_file = rt / "dashboard-port.txt"
    server_code = """
import sys
from http.server import HTTPServer
sys.path.insert(0, sys.argv[1])
from dashboard import EidolonDashboardHandler
server=HTTPServer(('127.0.0.1',0),EidolonDashboardHandler)
open(sys.argv[2],'w',encoding='utf-8').write(str(server.server_address[1]))
server.handle_request()
server.server_close()
"""
    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(rt)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-c", server_code, str(ROOT / "conscious_agent"), str(port_file)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + 20
    while not port_file.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    require(port_file.exists())
    payload = json.dumps({
        "proposal_id": proposal["proposal_id"], "revision": 1, "revision_digest": proposal["revision_digest"],
        "implementation_checkpoint_digest": request["implementation_checkpoint_digest"],
        "apply_request_digest": request["apply_request_digest"], "apply_result_digest": applied["apply_result_digest"],
    }).encode()
    http_request = urllib.request.Request(
        f"http://127.0.0.1:{int(port_file.read_text())}/api/development-campaign/finalize-selected-project-apply-rollback-checkpoint",
        data=payload, headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(http_request, timeout=30) as response:
        body = json.loads(response.read().decode())
        require(response.status == 200)
    stdout, stderr = process.communicate(timeout=30)
    require(process.returncode == 0, (stdout, stderr))
    require(body["ok"] is True)
    require(body["checkpoint_phase"] == "applied")
    require(body["stage_count"] == 8)
    require(str(project) not in json.dumps(body, sort_keys=True))
    require("main.py" not in json.dumps(body, sort_keys=True))
finally:
    if process is not None and process.poll() is None:
        process.kill()
    shutil.rmtree(rt, ignore_errors=True)


# Static release, dashboard, privacy, and verifier coverage.
dashboard = (ROOT / "conscious_agent/dashboard.py").read_text(errors="ignore")
metadata = (ROOT / "conscious_agent/release_metadata.py").read_text()
verifier = (ROOT / "tools/release_verify.py").read_text()
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text()
history = (ROOT / "README_RELEASE_HISTORY.md").read_text()
require("/api/development-campaign/finalize-selected-project-apply-rollback-checkpoint" in dashboard)
require("selected-project apply/rollback checkpoint" in dashboard)
require('WORKING_SOURCE_VERSION = "1204.9"' in metadata)
require("v1204.9 Selected-Project Apply and Rollback Checkpoint" in metadata)
require(verifier.count("v1204.9-selected-project-apply-rollback-checkpoint") == 2)
require(verifier.count("tools/v1204_9_selected_project_apply_rollback_checkpoint_tests.py") == 1)
require("v1204.9" in next_steps)
require("v1204.9 Selected-Project Apply and Rollback Checkpoint" in history)
for source_path in (
    ROOT / "conscious_agent/selected_project_apply_rollback_checkpoint.py",
    ROOT / "tools/v1204_9_selected_project_apply_rollback_checkpoint_tests.py",
):
    encoded = source_path.read_text(errors="ignore")
    windows_prefix = "C:" + chr(92) + "Users" + chr(92)
    posix_prefix = "/" + "Users" + "/"
    require(windows_prefix not in encoded and posix_prefix not in encoded)

print(json.dumps({
    "ok": True,
    "version": "1204.9",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "apply_checkpoint_stage_count": 8,
    "rollback_checkpoint_stage_count": 13,
    "exact_apply_authorization_bound": True,
    "exact_rollback_authorization_bound": True,
    "phase_journal_lineage": True,
    "checkpoint_content_free": True,
    "release_authorized": False,
    "authority_granted": False,
}, sort_keys=True))
