from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1207-9-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from v1207_test_support import campaign, source_signature
from dashboard import EidolonDashboardHandler
from node_javascript_test_adapter import (
    _operation_path,
    _result_path,
    run_or_resume_node_javascript_tests,
)
from node_javascript_test_adapter_checkpoint import (
    STAGES,
    _checkpoint_path,
    load_node_javascript_test_adapter_checkpoint,
    public_node_javascript_test_adapter_checkpoint,
    seal_or_resume_node_javascript_test_adapter_checkpoint,
)
from isolated_implementation_workspace import _record_path
from ordinary_chat_development_campaign import _approval_path, _read_json, list_development_campaign_proposals

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def prepare(runtime_root: Path, *, mode: str = "pass", session: str = "checkpoint"):
    proposal, implementation = campaign(runtime_root, mode=mode, session_id=session)
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=runtime_root,
    )
    require(result.get("node_javascript_test_digest"), result)
    return proposal, implementation, result


def seal(proposal, implementation, result, runtime_root: Path):
    return seal_or_resume_node_javascript_test_adapter_checkpoint(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"],
        expected_node_javascript_test_digest=result["node_javascript_test_digest"],
        runtime_root=runtime_root,
    )


before = source_signature()

# Passing test outcome seals the exact eight-stage lineage.
rt = RUNTIME / "pass"
proposal, implementation, result = prepare(rt, session="checkpoint-pass")
checkpoint = seal(proposal, implementation, result, rt)
require(checkpoint["ok"] is True, checkpoint)
require(checkpoint["status"] == "node_javascript_test_adapter_checkpoint_passed")
require(checkpoint["tests_passed"] is True)
require(checkpoint["stage_count"] == len(STAGES) == 8)
require([row["stage"] for row in checkpoint["stage_receipts"]] == list(STAGES))
require(checkpoint["node_javascript_test_digest"] == result["node_javascript_test_digest"])
require(checkpoint["workspace_digest"] == implementation["workspace_digest"])
require(checkpoint["operator_review_required"] is True)
require(checkpoint["network_allowed"] is False)
require(checkpoint["dependencies_installed"] is False)
require(checkpoint["shell_executed"] is False)
require(checkpoint["repair_authorized"] is False)
require(checkpoint["apply_authorized"] is False)
require(checkpoint["release_authorized"] is False)
resumed = seal(proposal, implementation, result, rt)
require(resumed["operation_status"] == "resumed")
require(resumed["checkpoint_digest"] == checkpoint["checkpoint_digest"])
loaded = load_node_javascript_test_adapter_checkpoint(proposal["proposal_id"], 1, rt)
require(loaded["checkpoint_digest"] == checkpoint["checkpoint_digest"])
public = public_node_javascript_test_adapter_checkpoint(checkpoint)
encoded = json.dumps(public, sort_keys=True)
require(public["private_request_exposed"] is False)
require(public["private_path_exposed"] is False)
require(public["private_content_exposed"] is False)
require(public["raw_output_exposed"] is False)
require(public["node_executable_path_exposed"] is False)
require(str(rt) not in encoded)
require("tests/tool.test.js" not in encoded)
require("node --test" not in encoded)

# Public campaign state shows result and checkpoint separately.
projection = list_development_campaign_proposals(runtime_root=rt, public=True)
require(projection["proposal_count"] == 1)
row = projection["proposals"][0]
require(row["node_javascript_test_result"]["node_javascript_test_digest"] == result["node_javascript_test_digest"])
require(row["node_javascript_test_adapter_checkpoint"]["checkpoint_digest"] == checkpoint["checkpoint_digest"])
require(row["current_stage"] == "node_javascript_test_adapter_checkpoint_passed")
require(str(rt) not in json.dumps(row, sort_keys=True))

# Failing tests are checkpointed as review evidence without repair authority.
rt_fail = RUNTIME / "fail"
p_fail, i_fail, r_fail = prepare(rt_fail, mode="fail", session="checkpoint-fail")
require(r_fail["passed"] is False)
c_fail = seal(p_fail, i_fail, r_fail, rt_fail)
require(c_fail["ok"] is True)
require(c_fail["status"] == "node_javascript_test_adapter_checkpoint_failed_review_required")
require(c_fail["tests_passed"] is False)
require(c_fail["repair_authorized"] is False)
require(c_fail["test_outcome_class"] == "tests_failed")

# Eight concurrent finalizers converge on one immutable checkpoint.
rt_race = RUNTIME / "race"
p_race, i_race, r_race = prepare(rt_race, session="checkpoint-race")
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows = list(pool.map(lambda _index: seal(p_race, i_race, r_race, rt_race), range(8)))
require(len({item.get("checkpoint_digest") for item in rows}) == 1, rows)
require(sum(item.get("operation_status") == "created" for item in rows) == 1)
require(sum(item.get("operation_status") == "resumed" for item in rows) == 7)

# Stale bindings reject finalization.
rt_stale = RUNTIME / "stale"
p_stale, i_stale, r_stale = prepare(rt_stale, session="checkpoint-stale")
require(seal_or_resume_node_javascript_test_adapter_checkpoint(
    p_stale["proposal_id"], expected_revision=1, expected_revision_digest="0" * 64,
    expected_workspace_digest=i_stale["workspace_digest"],
    expected_node_javascript_test_digest=r_stale["node_javascript_test_digest"], runtime_root=rt_stale,
)["status"] == "stale_proposal_revision")
require(seal_or_resume_node_javascript_test_adapter_checkpoint(
    p_stale["proposal_id"], expected_revision=1, expected_revision_digest=p_stale["revision_digest"],
    expected_workspace_digest="1" * 64,
    expected_node_javascript_test_digest=r_stale["node_javascript_test_digest"], runtime_root=rt_stale,
)["status"] == "workspace_record_missing_or_stale")
require(seal_or_resume_node_javascript_test_adapter_checkpoint(
    p_stale["proposal_id"], expected_revision=1, expected_revision_digest=p_stale["revision_digest"],
    expected_workspace_digest=i_stale["workspace_digest"],
    expected_node_javascript_test_digest="2" * 64, runtime_root=rt_stale,
)["status"] == "node_javascript_operation_result_mismatch")

# Tampered approval, operation, result, workspace, or checkpoint records block.
def tamper_case(name: str, target_getter, mutate, expected_status: str):
    rt_case = RUNTIME / name
    p, impl, test = prepare(rt_case, session=name)
    target = target_getter(p, rt_case)
    raw = json.loads(target.read_text())
    mutate(raw)
    target.write_text(json.dumps(raw), encoding="utf-8")
    blocked = seal(p, impl, test, rt_case)
    require(blocked["status"] == expected_status, blocked)


tamper_case("tamper-approval", lambda p, rt: _approval_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("approval_consumed_once", False), "approval_receipt_missing_or_invalid")
tamper_case("tamper-operation", lambda p, rt: _operation_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("phase", "prepared"), "node_javascript_operation_missing_or_invalid")
tamper_case("tamper-result", lambda p, rt: _result_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("passed", False), "node_javascript_result_missing_or_invalid")
tamper_case("tamper-workspace-record", lambda p, rt: _record_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("file_count", 999), "workspace_record_invalid")

rt_checkpoint = RUNTIME / "tamper-checkpoint"
p_cp, i_cp, r_cp = prepare(rt_checkpoint, session="tamper-checkpoint")
c_cp = seal(p_cp, i_cp, r_cp, rt_checkpoint)
cp_path = _checkpoint_path(p_cp["proposal_id"], 1, rt_checkpoint)
raw = json.loads(cp_path.read_text())
raw["stage_count"] = 99
cp_path.write_text(json.dumps(raw), encoding="utf-8")
require(seal(p_cp, i_cp, r_cp, rt_checkpoint)["status"] == "node_javascript_checkpoint_invalid")

# Real dashboard POST finalizes and rejects stale supplied result digests.
p_http, i_http, r_http = prepare(RUNTIME, session="checkpoint-http")
server = HTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    url = f"http://127.0.0.1:{server.server_port}/api/development-campaign/finalize-node-javascript-test-checkpoint"
    body = json.dumps({
        "proposal_id": p_http["proposal_id"], "revision": 1,
        "revision_digest": p_http["revision_digest"],
        "node_javascript_test_digest": r_http["node_javascript_test_digest"],
    }).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read())
    require(payload["ok"] is True, payload)
    require(payload["stage_count"] == 8)
    require(payload["checkpoint_digest"])
    stale_body = json.dumps({
        "proposal_id": p_http["proposal_id"], "revision": 1,
        "revision_digest": p_http["revision_digest"],
        "node_javascript_test_digest": "f" * 64,
    }).encode()
    stale_request = urllib.request.Request(url, data=stale_body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(stale_request, timeout=15)
        require(False, "stale request unexpectedly succeeded")
    except urllib.error.HTTPError as error:
        stale_payload = json.loads(error.read())
        require(error.code == 409)
        require(stale_payload["status"] == "stale_node_javascript_checkpoint_request")
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=3)

# Static UI, verifier, metadata, docs, and privacy registration.
dashboard = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
require("/api/development-campaign/node-javascript-test" in dashboard)
require("/api/development-campaign/finalize-node-javascript-test-checkpoint" in dashboard)
require("Run Node/JavaScript tests" in dashboard)
require("Seal Node/JavaScript test checkpoint" in dashboard)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
for name in (
    "v1207.2-node-javascript-test-adapter-foundations",
    "v1207.5-node-javascript-project-test-execution",
    "v1207.8-node-javascript-test-adapter-reliability",
    "v1207.9-node-javascript-test-adapter-checkpoint",
):
    require(name in release)
    require(f'"{name}"' in release.split("QUICK_STAGE_NAMES", 1)[1].split("}", 1)[0])
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1207.9"' in metadata)
require('WORKING_SOURCE_VERSION = "1207.8"' in metadata)
require("Node and JavaScript Test Adapter Checkpoint" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"))
require("v1207.9" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require(not (ROOT / "data" / "development_campaigns").exists())
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "version": "1207.9",
    "suite": "node-javascript-test-adapter-checkpoint",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "source_immutable": True,
    "network_allowed": False,
    "dependencies_installed": False,
    "shell_executed": False,
    "operator_review_required": True,
    "repair_authorized": False,
    "release_authorized": False,
}, sort_keys=True))

shutil.rmtree(RUNTIME, ignore_errors=True)
