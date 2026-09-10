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
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v1206-9-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from browser_runtime_test_adapter import (
    _runtime_operation_path,
    _runtime_test_path,
    run_or_resume_browser_runtime_test,
)
from browser_runtime_test_adapter_checkpoint import (
    STAGES,
    _checkpoint_path,
    load_browser_runtime_test_adapter_checkpoint,
    public_browser_runtime_test_adapter_checkpoint,
    seal_or_resume_browser_runtime_test_adapter_checkpoint,
)
from dashboard import EidolonDashboardHandler
from grounded_development_planning import create_or_resume_grounded_plan
from isolated_implementation_workspace import _record_path, materialize_or_resume_workspace
from isolated_workspace_preview import _preview_path, create_or_resume_workspace_preview
from ordinary_chat_development_campaign import (
    _approval_path,
    approve_development_campaign_proposal,
    create_or_resume_development_proposal,
    list_development_campaign_proposals,
)
from structured_development_generation import generate_or_resume_structured_output

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


def campaign(runtime: Path, script: str):
    proposal = create_or_resume_development_proposal("Build me a browser checkpoint webpage", runtime_root=runtime)
    approval = approve_development_campaign_proposal(
        proposal["proposal_id"], revision=1, revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    require(approval["ok"] is True, approval)
    require(approval["approval_consumption_count"] == 1)
    plan = create_or_resume_grounded_plan(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    authority = {
        "proposal_id": proposal["proposal_id"],
        "revision": 1,
        "revision_digest": proposal["revision_digest"],
        "planning_digest": plan["planning_digest"],
        "project_snapshot_digest": plan["project_snapshot_digest"],
    }
    files = [
        {
            "path": "index.html",
            "operation": "create",
            "content": "<!doctype html><html><head><title>Runtime</title><meta name='viewport' content='width=device-width'></head><body><main id='app'></main><script src='app.js'></script></body></html>",
        },
        {"path": "styles.css", "operation": "create", "content": "body{font-family:sans-serif}"},
        {"path": "app.js", "operation": "create", "content": script},
    ]
    calls: list[int] = []

    def provider(_prompt: str) -> str:
        calls.append(1)
        return json.dumps({"authority": authority, "files": files})

    generation = generate_or_resume_structured_output(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_planning_digest=plan["planning_digest"],
        runtime_root=runtime,
        provider_generate=provider,
    )
    workspace = materialize_or_resume_workspace(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_planning_digest=plan["planning_digest"],
        expected_generation_digest=generation["generation_digest"],
        runtime_root=runtime,
    )
    preview = create_or_resume_workspace_preview(
        proposal["proposal_id"], expected_revision=1, expected_revision_digest=proposal["revision_digest"], runtime_root=runtime
    )
    runtime_result = run_or_resume_browser_runtime_test(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=workspace["workspace_digest"],
        expected_preview_digest=preview["preview_digest"],
        runtime_root=runtime,
    )
    require(len(calls) == 1)
    return proposal, plan, generation, workspace, preview, runtime_result


def seal(proposal, workspace, preview, result, runtime):
    return seal_or_resume_browser_runtime_test_adapter_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=workspace["workspace_digest"],
        expected_preview_digest=preview["preview_digest"],
        expected_browser_runtime_test_digest=result["browser_runtime_test_digest"],
        runtime_root=runtime,
    )


before = source_signature()

# Passing browser runtime result seals nine exact stages and resumes idempotently.
runtime = RUNTIME / "pass"
proposal, plan, generation, workspace, preview, result = campaign(
    runtime,
    "document.querySelector('#app').setAttribute('data-runtime-ready','true'); fetch('https://example.com/private').catch(()=>{});",
)
require(result["ok"] is True, result)
require(result["passed"] is True, result)
checkpoint = seal(proposal, workspace, preview, result, runtime)
require(checkpoint["ok"] is True, checkpoint)
require(checkpoint["contract_version"] == "v1206.9")
require(checkpoint["status"] == "browser_runtime_adapter_checkpoint_passed")
require(checkpoint["stage_count"] == 9)
require([row["stage"] for row in checkpoint["stage_receipts"]] == list(STAGES))
require([row["sequence"] for row in checkpoint["stage_receipts"]] == list(range(1, 10)))
require(checkpoint["proposal_revision_digest"] == proposal["revision_digest"])
require(checkpoint["planning_digest"] == plan["planning_digest"])
require(checkpoint["generation_digest"] == generation["generation_digest"])
require(checkpoint["workspace_digest"] == workspace["workspace_digest"])
require(checkpoint["preview_digest"] == preview["preview_digest"])
require(checkpoint["browser_runtime_test_digest"] == result["browser_runtime_test_digest"])
require(checkpoint["browser_runtime_passed"] is True)
require(checkpoint["cleanup_confirmed"] is True)
require(checkpoint["blocked_external_request_count"] >= 1)
require(checkpoint["operator_review_required"] is True)
require(checkpoint["network_allowed"] is False)
require(checkpoint["apply_authorized"] is False)
require(checkpoint["rollback_authorized"] is False)
require(checkpoint["repair_authorized"] is False)
require(checkpoint["release_authorized"] is False)
require(checkpoint["model_management_authorized"] is False)
require(checkpoint["independent_authority_granted"] is False)
resumed = seal(proposal, workspace, preview, result, runtime)
require(resumed["operation_status"] == "resumed")
require(resumed["checkpoint_digest"] == checkpoint["checkpoint_digest"])
loaded = load_browser_runtime_test_adapter_checkpoint(proposal["proposal_id"], 1, runtime)
require(loaded["checkpoint_digest"] == checkpoint["checkpoint_digest"])
public = public_browser_runtime_test_adapter_checkpoint(checkpoint)
encoded = json.dumps(public, sort_keys=True)
require(public["private_request_exposed"] is False)
require(public["private_path_exposed"] is False)
require(public["private_content_exposed"] is False)
require(public["raw_browser_output_exposed"] is False)
require(str(runtime) not in encoded)
require("index.html" not in encoded)
require("example.com/private" not in encoded)

# Public campaign state exposes result and checkpoint separately without paths or source.
projection = list_development_campaign_proposals(runtime_root=runtime, public=True)
require(projection["proposal_count"] == 1)
projected = projection["proposals"][0]
require(projected["browser_runtime_test"]["browser_runtime_test_digest"] == result["browser_runtime_test_digest"])
require(projected["browser_runtime_test_adapter_checkpoint"]["checkpoint_digest"] == checkpoint["checkpoint_digest"])
require(projected["current_stage"] == "browser_runtime_adapter_checkpoint_passed")
require(str(runtime) not in json.dumps(projected, sort_keys=True))

# Concurrent checkpoint finalization converges on one immutable record.
runtime_race = RUNTIME / "race"
p2, _pl2, _g2, w2, pr2, r2 = campaign(runtime_race, "document.body.setAttribute('data-runtime-ready','true');")
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    rows = list(pool.map(lambda _index: seal(p2, w2, pr2, r2, runtime_race), range(8)))
require(len({row.get("checkpoint_digest") for row in rows}) == 1, rows)
require(sum(row.get("operation_status") == "created" for row in rows) == 1, rows)
require(sum(row.get("operation_status") == "resumed" for row in rows) == 7, rows)

# Exact stale bindings reject checkpoint creation.
runtime_stale = RUNTIME / "stale"
p3, _pl3, _g3, w3, pr3, r3 = campaign(runtime_stale, "document.body.setAttribute('data-runtime-ready','true');")
require(seal_or_resume_browser_runtime_test_adapter_checkpoint(
    p3["proposal_id"], expected_revision=1, expected_revision_digest="0" * 64,
    expected_workspace_digest=w3["workspace_digest"], expected_preview_digest=pr3["preview_digest"],
    expected_browser_runtime_test_digest=r3["browser_runtime_test_digest"], runtime_root=runtime_stale,
)["status"] == "stale_proposal_revision")
require(seal_or_resume_browser_runtime_test_adapter_checkpoint(
    p3["proposal_id"], expected_revision=1, expected_revision_digest=p3["revision_digest"],
    expected_workspace_digest="1" * 64, expected_preview_digest=pr3["preview_digest"],
    expected_browser_runtime_test_digest=r3["browser_runtime_test_digest"], runtime_root=runtime_stale,
)["status"] == "workspace_record_missing_or_stale")
require(seal_or_resume_browser_runtime_test_adapter_checkpoint(
    p3["proposal_id"], expected_revision=1, expected_revision_digest=p3["revision_digest"],
    expected_workspace_digest=w3["workspace_digest"], expected_preview_digest="2" * 64,
    expected_browser_runtime_test_digest=r3["browser_runtime_test_digest"], runtime_root=runtime_stale,
)["status"] == "preview_record_missing_or_invalid")
require(seal_or_resume_browser_runtime_test_adapter_checkpoint(
    p3["proposal_id"], expected_revision=1, expected_revision_digest=p3["revision_digest"],
    expected_workspace_digest=w3["workspace_digest"], expected_preview_digest=pr3["preview_digest"],
    expected_browser_runtime_test_digest="3" * 64, runtime_root=runtime_stale,
)["status"] == "browser_runtime_operation_result_mismatch")

# Failing runtime behavior is sealed as evidence and never grants repair authority.
runtime_failed = RUNTIME / "failed"
p4, _pl4, _g4, w4, pr4, r4 = campaign(runtime_failed, "throw new Error('private page error text');")
require(r4["passed"] is False)
failed_checkpoint = seal(p4, w4, pr4, r4, runtime_failed)
require(failed_checkpoint["ok"] is True)
require(failed_checkpoint["status"] == "browser_runtime_adapter_checkpoint_failed_review_required")
require(failed_checkpoint["browser_runtime_passed"] is False)
require(failed_checkpoint["page_error_count"] >= 1)
require(failed_checkpoint["repair_authorized"] is False)
require("private page error text" not in json.dumps(public_browser_runtime_test_adapter_checkpoint(failed_checkpoint)))

# Tampered source artifacts or sealed journals block finalization.
def tamper_case(name: str, target_getter, mutate, expected_status: str):
    rt = RUNTIME / name
    p, _plan, _gen, ws, pv, rr = campaign(rt, "document.body.setAttribute('data-runtime-ready','true');")
    target = target_getter(p, rt)
    raw = json.loads(target.read_text())
    mutate(raw)
    target.write_text(json.dumps(raw), encoding="utf-8")
    blocked = seal(p, ws, pv, rr, rt)
    require(blocked["status"] == expected_status, blocked)


tamper_case("tamper-approval", lambda p, rt: _approval_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("approval_consumed_once", False), "approval_receipt_missing_or_invalid")
tamper_case("tamper-preview", lambda p, rt: _preview_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("entrypoint", "other.html"), "preview_record_missing_or_invalid")
tamper_case("tamper-operation", lambda p, rt: _runtime_operation_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("phase", "prepared"), "browser_runtime_operation_missing_or_invalid")
tamper_case("tamper-result", lambda p, rt: _runtime_test_path(p["proposal_id"], 1, rt), lambda raw: raw.__setitem__("passed", False), "browser_runtime_result_missing_or_invalid")

# Workspace file tampering is caught even though the workspace record itself is unchanged.
runtime_workspace = RUNTIME / "tamper-workspace"
p5, _pl5, g5, w5, pr5, r5 = campaign(runtime_workspace, "document.body.setAttribute('data-runtime-ready','true');")
workspace_root = Path(w5["workspace_path"])
(workspace_root / "app.js").write_text("console.log('tampered')", encoding="utf-8")
require(seal(p5, w5, pr5, r5, runtime_workspace)["status"] == "workspace_record_invalid")

# Existing checkpoint tampering never self-heals.
runtime_checkpoint = RUNTIME / "tamper-checkpoint"
p6, _pl6, _g6, w6, pr6, r6 = campaign(runtime_checkpoint, "document.body.setAttribute('data-runtime-ready','true');")
c6 = seal(p6, w6, pr6, r6, runtime_checkpoint)
cp = _checkpoint_path(p6["proposal_id"], 1, runtime_checkpoint)
raw = json.loads(cp.read_text())
raw["stage_count"] = 99
cp.write_text(json.dumps(raw), encoding="utf-8")
require(seal(p6, w6, pr6, r6, runtime_checkpoint)["status"] == "browser_runtime_checkpoint_invalid")

# Real dashboard POST finalizes the checkpoint and rejects a stale supplied result digest.
runtime_http = RUNTIME
p7, _pl7, _g7, w7, pr7, r7 = campaign(runtime_http, "document.body.setAttribute('data-runtime-ready','true');")
server = HTTPServer(("127.0.0.1", 0), EidolonDashboardHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    url = f"http://127.0.0.1:{server.server_port}/api/development-campaign/finalize-browser-runtime-checkpoint"
    body = json.dumps({
        "proposal_id": p7["proposal_id"], "revision": 1, "revision_digest": p7["revision_digest"],
        "browser_runtime_test_digest": r7["browser_runtime_test_digest"],
    }).encode()
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read())
    require(payload["ok"] is True, payload)
    require(payload["checkpoint_digest"])
    require(payload["stage_count"] == 9)
    stale_body = json.dumps({
        "proposal_id": p7["proposal_id"], "revision": 1, "revision_digest": p7["revision_digest"],
        "browser_runtime_test_digest": "f" * 64,
    }).encode()
    stale_request = urllib.request.Request(url, data=stale_body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(stale_request, timeout=10)
        require(False, "stale request unexpectedly succeeded")
    except urllib.error.HTTPError as error:
        stale_payload = json.loads(error.read())
        require(error.code == 409)
        require(stale_payload["status"] == "stale_browser_runtime_checkpoint_request")
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)

# Static registration, UI, documentation, and privacy boundaries.
dashboard = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
require("/api/development-campaign/finalize-browser-runtime-checkpoint" in dashboard)
require("Seal browser runtime checkpoint" in dashboard)
require("browser runtime checkpoint" in dashboard)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require("v1206.9-browser-runtime-test-adapter-checkpoint" in release)
require('"v1206.9-browser-runtime-test-adapter-checkpoint"' in release.split("QUICK_STAGE_NAMES", 1)[1].split("}", 1)[0])
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1206.9"' in metadata)
require('WORKING_SOURCE_VERSION = "1206.8"' in metadata)
require("Browser Runtime Test Adapter Checkpoint" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"))
require("v1206.9" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require(not (ROOT / "data" / "development_campaigns").exists())
require(source_signature() == before)

print(json.dumps({
    "ok": True,
    "suite": "v1206.9-browser-runtime-test-adapter-checkpoint",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True))

shutil.rmtree(RUNTIME, ignore_errors=True)
