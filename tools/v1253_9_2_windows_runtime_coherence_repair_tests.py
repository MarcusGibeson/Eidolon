from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
RUNTIME = Path(tempfile.mkdtemp(prefix="eid-v1253-9-2-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

CHECKS: list[str] = []


def require(value: object, label: str) -> None:
    if not value:
        raise AssertionError(label)
    CHECKS.append(label)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


before = source_signature()

from persistent_state_index import append_memory_records, load_indexed_memories

memory_file = RUNTIME / "memory" / "memories.json"
append_memory_records(memory_file, [{"id": "one", "text": "first", "type": "test"}])
append_memory_records(memory_file, [{"id": "two", "text": "second", "type": "test"}])
require([row["id"] for row in json.loads(memory_file.read_text(encoding="utf-8"))] == ["one", "two"], "windows_memory_journal_append")
require([row["id"] for row in load_indexed_memories(memory_file)] == ["one", "two"], "memory_index_matches_canonical_store")

from persistent_state_performance import benchmark_persistent_state_scaling

cleanup_probe = benchmark_persistent_state_scaling(memory_count=40, session_count=8, action_count=40)
require(isinstance(cleanup_probe, dict) and cleanup_probe["counts"]["memories"] == 40, "sqlite_connections_close_before_temp_cleanup")

import conversation_runtime
from conversation_sessions import create_conversation_session


class FakeLocalModelClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        self.last_retry_count = 0

    def generate(self, prompt: str) -> str:
        type(self).calls += 1
        return "The repaired Windows conversation completed."

    def cancel(self) -> None:
        return None

    def close(self) -> None:
        return None


original_client = conversation_runtime.LocalModelClient
conversation_runtime.LocalModelClient = FakeLocalModelClient
try:
    session = create_conversation_session(title="v1253.9.2 Windows conversation", select_session=False)
    turn = conversation_runtime.run_conversation_turn(
        "Verify the repaired conversation path.",
        use_ai=True,
        session_id=session["id"],
        select_session_on_record=False,
    )
finally:
    conversation_runtime.LocalModelClient = original_client
require(turn.success is True and turn.completion_state == "completed", "ordinary_conversation_completes")
require(FakeLocalModelClient.calls == 1 and turn.provider_request_count == 1, "ordinary_conversation_exactly_one_provider_request")
require(turn.receipt_persisted is True, "conversation_receipt_persisted")

maintenance_runtime = Path(tempfile.mkdtemp(prefix="eid-v1253-9-2-maintenance-"))
marker = maintenance_runtime / "executions.txt"
start_at = time.time() + 2.0
child = r'''
import os, sys, time
from pathlib import Path
root, runtime, marker, start_at = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), float(sys.argv[4])
os.environ["EIDOLON_DATA_DIR"] = str(runtime)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, str(root / "conscious_agent"))
import bounded_internal_maintenance as maintenance
def execute(job):
    with marker.open("a", encoding="utf-8") as handle:
        handle.write(str(os.getpid()) + "\n")
        handle.flush()
maintenance._execute = execute
while time.time() < start_at:
    time.sleep(0.002)
try:
    print(maintenance.enqueue_internal_maintenance("projection_cache_prune")["status"], flush=True)
except Exception as error:
    print("ERROR:" + repr(error), flush=True)
time.sleep(1.0)
'''
processes = [
    subprocess.Popen(
        [sys.executable, "-c", child, str(ROOT), str(maintenance_runtime), str(marker), str(start_at)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "EIDOLON_DATA_DIR": str(maintenance_runtime), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    for _ in range(4)
]
children = []
for process in processes:
    stdout, stderr = process.communicate(timeout=20)
    children.append((process.returncode, stdout.strip(), stderr.strip()))
executions = marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []
require(len(executions) == 1 and len(set(executions)) == 1, "cross_process_maintenance_exactly_once")
require(all(code == 0 and not stderr and not stdout.startswith("ERROR:") for code, stdout, stderr in children), "cross_process_maintenance_no_errors")
require(sum(stdout == "queued" for _, stdout, _ in children) == 1, "cross_process_single_queue_owner")

from dynamic_execution_plan_revision_checkpoint import build_dynamic_execution_plan_revision_checkpoint

encoding_checkpoint = build_dynamic_execution_plan_revision_checkpoint(source_root=ROOT)
require(isinstance(encoding_checkpoint, dict) and "checks" in encoding_checkpoint, "retained_checkpoint_utf8_read")

from dashboard_full_navigation_get_side_effect_safety_gate import _extract_nav_items

dashboard_source = (ROOT / "conscious_agent" / "dashboard.py").read_text(encoding="utf-8")
require(len(_extract_nav_items(dashboard_source)) > 0, "dashboard_navigation_registry_without_eval")

maintenance_source = (ROOT / "conscious_agent" / "bounded_internal_maintenance.py").read_text(encoding="utf-8")
self_maintenance_source = (ROOT / "conscious_agent" / "self_maintenance.py").read_text(encoding="utf-8")
navigation_source = (ROOT / "conscious_agent" / "dashboard_full_navigation_get_side_effect_safety_gate.py").read_text(encoding="utf-8")
require("cross_process_coalescing" in maintenance_source and "owner_pid" in maintenance_source, "cross_process_contract_present")
require("shell=True" not in self_maintenance_source, "transaction_rehearsal_shell_free")
require("value = eval(" not in navigation_source, "dashboard_navigation_eval_free")

from performance_budgets import DEFAULT_BUDGETS

warm_budget = DEFAULT_BUDGETS["warm_pre_provider_ms"]
require(warm_budget["hardware_sensitive"] is True, "warm_pre_provider_budget_is_hardware_sensitive")
require(warm_budget["median_max"] == 125.0 and warm_budget["p95_max"] == 500.0, "warm_pre_provider_budget_bounds_windows_outliers")

from release_authority import WORKING_SOURCE_VERSION, PREVIOUS_WORKING_SOURCE_VERSION

require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split(".")) >= (1253, 9, 2), "working_version_at_or_beyond_repair")
require(bool(PREVIOUS_WORKING_SOURCE_VERSION), "previous_version_recorded")
require(source_signature() == before, "source_unchanged")

report = {
    "ok": True,
    "version": "1253.9.2",
    "passed": len(CHECKS),
    "total": len(CHECKS),
    "checks": CHECKS,
    "provider_contacted": False,
    "project_mutation_authorized": False,
    "release_authorized": False,
    "independent_authority_granted": False,
}
print(json.dumps(report, indent=2 if "--json" in sys.argv else None, sort_keys=True))
