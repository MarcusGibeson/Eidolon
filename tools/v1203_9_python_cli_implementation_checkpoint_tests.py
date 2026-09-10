from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))

from ordinary_chat_development_campaign import (  # noqa: E402
    _digest,
    list_development_campaign_proposals,
    process_ordinary_chat_development_turn,
)
from python_cli_implementation_checkpoint import (  # noqa: E402
    STAGES,
    _path as _final_path,
    load_python_cli_implementation_checkpoint,
    public_python_cli_implementation_checkpoint,
    run_or_resume_python_cli_implementation_checkpoint,
    seal_or_resume_python_cli_implementation_checkpoint,
)
from python_cli_result_disposition import (  # noqa: E402
    _disposition_path,
    _packet_path,
    create_or_resume_python_cli_review_packet,
    dispose_python_cli_result,
)
from python_cli_test_execution_checkpoint import run_or_resume_python_cli_with_tests  # noqa: E402
from isolated_implementation_workspace import _record_path, _workspace_root  # noqa: E402

PYTHON_EXECUTABLE = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable
START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


def source_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"} for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def approved(runtime_root: Path, session_id: str) -> dict:
    result = process_ordinary_chat_development_turn(
        "Build me a Python CLI that counts words",
        action_projection={"intent": {"category": "action_request"}},
        session_id=session_id,
        runtime_root=runtime_root,
    )
    proposal = result["proposal"]
    approval = process_ordinary_chat_development_turn(
        f"Approve development proposal {proposal['proposal_id']} revision {proposal['revision']}.",
        runtime_root=runtime_root,
    )
    require(approval["event"] == "approval_consumed")
    require(approval["approval_consumption_count"] == 1)
    return proposal


def provider(calls: list[str]):
    def generate(prompt: str) -> str:
        calls.append(hashlib.sha256(prompt.encode()).hexdigest())
        payload = json.loads(prompt)
        content = {
            "main.py": (
                "import argparse\n"
                "from tool import count_words\n"
                "parser=argparse.ArgumentParser()\n"
                "parser.add_argument('text',nargs='*')\n"
                "args=parser.parse_args()\n"
                "print(count_words(' '.join(args.text)))\n"
            ),
            "tool.py": "def count_words(text):\n    return len(str(text).split())\n",
            "tests/test_tool.py": (
                "from tool import count_words\n"
                "assert count_words('one two') == 2\n"
            ),
            "README.md": "# Word counter\n",
        }
        return json.dumps(
            {
                "authority": payload["authority"],
                "files": [
                    {"path": path, "operation": "create", "content": content[path]}
                    for path in payload["planned_paths"]
                ],
            }
        )

    return generate


def ready(runtime_root: Path, session_id: str):
    proposal = approved(runtime_root, session_id)
    calls: list[str] = []
    tested = run_or_resume_python_cli_with_tests(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=runtime_root,
        provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
    )
    require(tested["ok"] is True, tested)
    require(tested["stage_count"] == 7)
    require(len(calls) == 1)
    packet = create_or_resume_python_cli_review_packet(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        runtime_root=runtime_root,
    )
    require(packet["ok"] is True)
    return proposal, tested, packet, calls


BEFORE = source_signature()

# Coordinator reaches a stable eight-stage review boundary without consuming a disposition.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-pending-"))
try:
    proposal = approved(rt, "pending")
    calls: list[str] = []
    pending = run_or_resume_python_cli_implementation_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=rt,
        provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
    )
    require(pending["ok"] is True)
    require(pending["status"] == "python_cli_implementation_checkpoint_awaiting_disposition")
    require(pending["stage_count"] == 8)
    require(pending["operator_disposition_required"] is True)
    require(len(calls) == 1)
    require(not _final_path(proposal["proposal_id"], 1, rt).exists())
    resumed = run_or_resume_python_cli_implementation_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        runtime_root=rt,
        provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
    )
    require(resumed["review_packet_digest"] == pending["review_packet_digest"])
    require(resumed["test_checkpoint_digest"] == pending["test_checkpoint_digest"])
    require(len(calls) == 1)
finally:
    shutil.rmtree(rt, ignore_errors=True)

# Every explicit disposition seals a nine-stage final checkpoint and remains idempotent.
expected_status = {
    "retain": "python_cli_implementation_checkpoint_retained",
    "revise": "python_cli_implementation_checkpoint_revision_requested",
    "reject": "python_cli_implementation_checkpoint_rejected",
    "discard": "python_cli_implementation_checkpoint_discarded",
}
for action in ("retain", "revise", "reject", "discard"):
    rt = Path(tempfile.mkdtemp(prefix=f"eid-v1202-9-{action}-"))
    try:
        proposal = approved(rt, action)
        calls: list[str] = []
        final = run_or_resume_python_cli_implementation_checkpoint(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            action=action,
            runtime_root=rt,
            provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
        )
        require(final["ok"] is True)
        require(final["status"] == expected_status[action])
        require(final["contract_version"] == "v1203.9")
        require(final["stage_count"] == 9)
        require([row["stage"] for row in final["stage_receipts"]] == list(STAGES))
        require([row["sequence"] for row in final["stage_receipts"]] == list(range(1, 10)))
        require(all(row["passed"] is True for row in final["stage_receipts"]))
        require(all(row["stage_receipt_digest"] == _digest({k: v for k, v in row.items() if k != "stage_receipt_digest"}) for row in final["stage_receipts"]))
        require(final["stage_lineage_digest"] == _digest(final["stage_receipts"]))
        require(final["disposition_action"] == action)
        require(final["disposition_consumption_count"] == 1)
        require(final["operator_review_complete"] is True)
        require(final["operator_disposition_required"] is False)
        require(final["workspace_discarded"] == (action == "discard"))
        require(final["workspace_retained"] == (action != "discard"))
        require(final["working_result_available"] == (action != "discard"))
        require(final["terminal"] == (action in {"reject", "discard"}))
        require(final["revision_required"] == (action == "revise"))
        require(final["evidence_retained"] is True)
        require(final["implementation_applied"] is False)
        require(final["selected_project_modified"] is False)
        require(final["repair_authorized"] is False)
        require(final["apply_authorized"] is False)
        require(final["release_authorized"] is False)
        require(final["authority_granted"] is False)
        require(len(calls) == 1)

        loaded = load_python_cli_implementation_checkpoint(proposal["proposal_id"], 1, rt)
        require(loaded["implementation_checkpoint_digest"] == final["implementation_checkpoint_digest"])
        public = public_python_cli_implementation_checkpoint(final)
        encoded = json.dumps(public, sort_keys=True)
        require(str(rt) not in encoded)
        require("main.py" not in encoded)
        require("count_words" not in encoded)
        require(public["stage_count"] == 9)
        require(public["disposition_action"] == action)
        require(public["private_path_exposed"] is False)
        require(public["private_content_exposed"] is False)
        require(public["implementation_applied"] is False)

        rows = list_development_campaign_proposals(runtime_root=rt, public=True)["proposals"]
        row = next(item for item in rows if item["proposal_id"] == proposal["proposal_id"])
        require(row["python_cli_implementation_checkpoint"]["implementation_checkpoint_digest"] == final["implementation_checkpoint_digest"])
        require(row["implementation_checkpoint_stage"] == expected_status[action])
        require(row["python_cli_disposition"]["action"] == action)

        resumed = run_or_resume_python_cli_implementation_checkpoint(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            action=action,
            runtime_root=rt,
            provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
        )
        require(resumed["operation_status"] == "resumed")
        require(resumed["implementation_checkpoint_digest"] == final["implementation_checkpoint_digest"])
        require(len(calls) == 1)
        stale_existing = run_or_resume_python_cli_implementation_checkpoint(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            action=action,
            expected_review_packet_digest="f" * 64,
            runtime_root=rt,
            provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
        )
        require(stale_existing["status"] == "stale_review_packet")
        require(stale_existing["failed_stage"] == "review")
        require(len(calls) == 1)

        conflicting = run_or_resume_python_cli_implementation_checkpoint(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            action="reject" if action != "reject" else "retain",
            runtime_root=rt,
            provider_generate=provider(calls),
        python_executable=PYTHON_EXECUTABLE,
        )
        require(conflicting["status"] == "python_cli_disposition_already_consumed")
        require(conflicting["failed_stage"] == "disposition")
        require(len(calls) == 1)
    finally:
        shutil.rmtree(rt, ignore_errors=True)

# A persisted disposition recovers a missing final checkpoint without consuming twice.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-recovery-"))
try:
    proposal, tested, packet, calls = ready(rt, "recovery")
    first = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    require(first["implementation_checkpoint_sealed"] is True)
    require(first["consumption_count"] == 1)
    final_path = _final_path(proposal["proposal_id"], 1, rt)
    original = json.loads(final_path.read_text())
    final_path.unlink()
    require(not final_path.exists())
    recovered = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    require(recovered["operation_status"] == "resumed")
    require(recovered["consumption_count"] == 1)
    require(recovered["implementation_checkpoint_sealed"] is True)
    require(recovered["implementation_checkpoint_digest"] == original["implementation_checkpoint_digest"])
    require(recovered["implementation_checkpoint_operation_status"] == "created")
    require(len(calls) == 1)
finally:
    shutil.rmtree(rt, ignore_errors=True)

# The POST-only dashboard recovery endpoint seals a persisted disposition without exposing private state.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-http-recovery-"))
try:
    proposal, tested, packet, _ = ready(rt, "http-recovery")
    disposition = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    _final_path(proposal["proposal_id"], 1, rt).unlink()
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
    env = dict(__import__("os").environ)
    env["EIDOLON_DATA_DIR"] = str(rt)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-c", server_code, str(ROOT / "conscious_agent"), str(port_file)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 15
    while not port_file.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    require(port_file.exists())
    payload = json.dumps({
        "proposal_id": proposal["proposal_id"],
        "revision": 1,
        "revision_digest": proposal["revision_digest"],
        "checkpoint_digest": tested["checkpoint_digest"],
        "review_packet_digest": packet["review_packet_digest"],
        "disposition_digest": disposition["disposition_digest"],
    }).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{int(port_file.read_text())}/api/development-campaign/finalize-python-cli-checkpoint",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode())
        require(response.status == 200)
    stdout, stderr = process.communicate(timeout=20)
    require(process.returncode == 0, (stdout, stderr))
    require(body["ok"] is True)
    require(body["stage_count"] == 9)
    require(body["implementation_checkpoint_digest"])
    require(str(rt) not in json.dumps(body, sort_keys=True))
    require("main.py" not in json.dumps(body, sort_keys=True))
finally:
    try:
        process.kill() if process.poll() is None else None
    except Exception:
        pass
    shutil.rmtree(rt, ignore_errors=True)

# Exact binding rejection for finalization.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-stale-"))
try:
    proposal, tested, packet, _ = ready(rt, "stale")
    disposition = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    _final_path(proposal["proposal_id"], 1, rt).unlink()
    cases = [
        ({"expected_revision_digest": "0" * 64}, "stale_proposal_revision"),
        ({"expected_test_checkpoint_digest": "1" * 64}, "stale_test_checkpoint_revision"),
        ({"expected_review_packet_digest": "2" * 64}, "stale_review_packet"),
        ({"expected_disposition_digest": "3" * 64}, "stale_disposition"),
    ]
    base = {
        "expected_revision": 1,
        "expected_revision_digest": proposal["revision_digest"],
        "expected_test_checkpoint_digest": tested["checkpoint_digest"],
        "expected_review_packet_digest": packet["review_packet_digest"],
        "expected_disposition_digest": disposition["disposition_digest"],
        "runtime_root": rt,
    }
    for override, status in cases:
        payload = dict(base)
        payload.update(override)
        blocked = seal_or_resume_python_cli_implementation_checkpoint(proposal["proposal_id"], **payload)
        require(blocked["status"] == status, (status, blocked))
finally:
    shutil.rmtree(rt, ignore_errors=True)

# Tampered final checkpoint blocks recovery but preserves the consumed decision.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-final-tamper-"))
try:
    proposal, tested, packet, _ = ready(rt, "final-tamper")
    disposition = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    final_path = _final_path(proposal["proposal_id"], 1, rt)
    record = json.loads(final_path.read_text())
    record["status"] = "tampered"
    final_path.write_text(json.dumps(record))
    replay = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    require(replay["consumption_count"] == 1)
    require(replay["implementation_checkpoint_sealed"] is False)
    require(replay["implementation_checkpoint_status"] == "python_cli_implementation_checkpoint_invalid")
    require(not load_python_cli_implementation_checkpoint(proposal["proposal_id"], 1, rt))
finally:
    shutil.rmtree(rt, ignore_errors=True)

# Retained workspace tampering prevents checkpoint reseal after an interruption.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-workspace-tamper-"))
try:
    proposal, tested, packet, _ = ready(rt, "workspace-tamper")
    disposition = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="retain",
        runtime_root=rt,
    )
    _final_path(proposal["proposal_id"], 1, rt).unlink()
    workspace_record = json.loads(_record_path(proposal["proposal_id"], 1, rt).read_text())
    root = _workspace_root(proposal["proposal_id"], 1, tested["generation_digest"], rt)
    relative = workspace_record["files"][0]["relative_path"]
    (root / relative).write_text("tampered", encoding="utf-8")
    blocked = seal_or_resume_python_cli_implementation_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_test_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        expected_disposition_digest=disposition["disposition_digest"],
        runtime_root=rt,
    )
    require(blocked["status"] == "retained_workspace_missing_or_invalid")
finally:
    shutil.rmtree(rt, ignore_errors=True)

# A discarded workspace must stay absent when a checkpoint is recovered.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-discard-reappear-"))
try:
    proposal, tested, packet, _ = ready(rt, "discard-reappear")
    disposition = dispose_python_cli_result(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        action="discard",
        runtime_root=rt,
    )
    _final_path(proposal["proposal_id"], 1, rt).unlink()
    root = _workspace_root(proposal["proposal_id"], 1, tested["generation_digest"], rt)
    root.mkdir(parents=True)
    (root / "unexpected.txt").write_text("unexpected")
    blocked = seal_or_resume_python_cli_implementation_checkpoint(
        proposal["proposal_id"],
        expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_test_checkpoint_digest=tested["checkpoint_digest"],
        expected_review_packet_digest=packet["review_packet_digest"],
        expected_disposition_digest=disposition["disposition_digest"],
        runtime_root=rt,
    )
    require(blocked["status"] == "discarded_workspace_still_present")
finally:
    shutil.rmtree(rt, ignore_errors=True)

# Eight concurrent duplicate dispositions converge on one disposition and one final checkpoint.
rt = Path(tempfile.mkdtemp(prefix="eid-v1202-9-race-"))
try:
    proposal, tested, packet, calls = ready(rt, "race")
    barrier = threading.Barrier(8)
    lock = threading.Lock()
    outputs: list[dict] = []

    def worker():
        barrier.wait()
        result = dispose_python_cli_result(
            proposal["proposal_id"],
            expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            expected_checkpoint_digest=tested["checkpoint_digest"],
            expected_review_packet_digest=packet["review_packet_digest"],
            action="retain",
            runtime_root=rt,
        )
        with lock:
            outputs.append(result)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [thread.start() for thread in threads]
    [thread.join(30) for thread in threads]
    require(len(outputs) == 8)
    require(all(item["ok"] is True for item in outputs))
    require(len({item["disposition_digest"] for item in outputs}) == 1)
    require(len({item["implementation_checkpoint_digest"] for item in outputs}) == 1)
    require(sum(item["operation_status"] == "created" for item in outputs) == 1)
    require(sum(item["implementation_checkpoint_operation_status"] == "created" for item in outputs) == 1)
    require(all(item["consumption_count"] == 1 for item in outputs))
    require(len(calls) == 1)
finally:
    shutil.rmtree(rt, ignore_errors=True)

# Static dashboard, release metadata, and source boundaries.
dashboard = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
require("/api/development-campaign/finalize-python-cli-checkpoint" in dashboard)
require("Recover final Python CLI checkpoint" in dashboard)
require("Python CLI implementation checkpoint" in dashboard)
require("data-py-finalize" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1203.9"' in metadata)
require("v1203.9 Python CLI Implementation Checkpoint" in metadata)
require("v1203.0-v1203.2 Python Command-Line Utility Foundations" in metadata)
release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1203.9-python-cli-implementation-checkpoint") == 2)
require(release_verify.count("tools/v1203_9_python_cli_implementation_checkpoint_tests.py") == 1)
require('"v1203.5-project-owned-python-tests"' in release_verify.split("SUPPLEMENTAL_RECEIPT_STAGE_NAMES", 1)[0])
require('"v1203.8-python-cli-result-disposition"' in release_verify.split("SUPPLEMENTAL_RECEIPT_STAGE_NAMES", 1)[0])
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Working source: **v1203.9" in next_steps)
require("v1204.0-v1204.2: Selected-Project Apply Foundations" in next_steps)
require("v1203.9 Python CLI Implementation Checkpoint" in history)
require((ROOT / "archive/docs/legacy_dependencies/validation/V1203_9_CHECKPOINT_REVIEW.md").exists())
require((ROOT / "archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1203_9.md").exists())
private_path_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in ROOT.rglob("*")
    if path.is_file() and path.suffix.lower() not in {".pyc", ".pyo", ".zip"}
)
require(("C:" + "\\" + "Users" + "\\" + "marcu") not in private_path_text)
require(("C:/" + "Users" + "/" + "Marcus") not in private_path_text)
require(source_signature() == BEFORE)

print(
    json.dumps(
        {
            "ok": True,
            "version": "1203.9",
            "checks": len(CHECKS),
            "passed": sum(CHECKS),
            "elapsed_seconds": round(time.monotonic() - START, 4),
            "stage_count": 9,
            "exact_disposition_consumption": True,
            "restart_recovery": True,
            "source_immutable": True,
            "selected_project_modified": False,
            "implementation_applied": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        },
        sort_keys=True,
    )
)
