from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_runtime = tempfile.TemporaryDirectory(prefix="eidolon-v1253-9-1-test-")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["EIDOLON_DATA_DIR"] = _runtime.name

checks: list[bool] = []
def req(value):
    checks.append(bool(value)); assert value

# 1. Terminal launcher owns no second local-model reflection.
launcher = (ROOT / "conscious_agent/chat_launcher.py").read_text(encoding="utf-8")
legacy_chat = (ROOT / "conscious_agent/chat.py").read_text(encoding="utf-8")
for terminal_path in (launcher, legacy_chat):
    req("_post_reply_reflection" not in terminal_path)
    req("generate_inner_thought" not in terminal_path)
    req("brain_mode=\"local_ai\"" not in terminal_path)
req("resume_pending_internal_maintenance" in launcher)
req("post-turn cognition is owned by conversation_runtime" in legacy_chat)

# 2. Decision-support phrasing keeps planning on the critical path and gets a useful budget.
from response_time_runtime import classify_turn_relevance, generation_token_budget
for phrase in (
    "What should I do about this situation?",
    "Help me decide between option A and option B.",
    "Which one would you choose?",
    "I need to figure out what to do next.",
    "Can you help me think through this?",
    "What are my options here?",
    "What are the trade-offs?",
):
    rel = classify_turn_relevance(phrase)
    req(rel.planning_relevant)
    req(generation_token_budget(phrase, 350, relevance=rel) >= 256)

# 3. Maintenance queue executes one globally coalesced job under heavy concurrent scheduling.
import bounded_internal_maintenance as bim
executed: list[str] = []
_original_execute = bim._execute

def fake_execute(job):
    executed.append(str(job.get("job_id") or ""))
    time.sleep(0.02)

bim._execute = fake_execute
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
    futures = [pool.submit(bim.enqueue_internal_maintenance, "projection_cache_prune", dedupe_key=f"session-{i}") for i in range(100)]
    receipts = [future.result(timeout=5) for future in futures]
bim._Q.join()
req(executed == ["projection_cache_prune:global"])
req(all(row.get("job_id") == "projection_cache_prune:global" for row in receipts))
status = bim.internal_maintenance_status()
req(status["persisted_jobs"] == 0)
req(status["global_housekeeping_coalesced"] is True)
req(status["exact_pending_running_lifecycle"] is True)

# 4. A restart-persisted running job is explicitly reconciled and executed once.
state = {
    "schema_version": bim.SCHEMA_VERSION,
    "contract_version": bim.CONTRACT_VERSION,
    "jobs": [{
        "job_id": "persistent_index_health_sample:global",
        "kind": "persistent_index_health_sample",
        "dedupe_key": "global",
        "state": "running",
        "created_at": "2026-08-07T00:00:00Z",
        "updated_at": "2026-08-07T00:00:00Z",
        "content_free": True,
    }],
    "recent_completed": {},
}
bim._write(state)
bim._SCHEDULED.clear()
executed.clear()
resume = bim.resume_pending_internal_maintenance()
bim._Q.join()
req(resume["ok"] and resume["restart_resume_hook"])
req(executed == ["persistent_index_health_sample:global"])
req(bim.internal_maintenance_status()["persisted_jobs"] == 0)
bim._execute = _original_execute

# 5. Same-host baselines are coarse/content-free and explicitly accepted.
from performance_baseline import accept_same_host_baseline, coarse_host_profile, load_same_host_baseline
profile = coarse_host_profile()
req("hostname" not in json.dumps(profile).lower())
req("username" not in json.dumps(profile).lower())
record = accept_same_host_baseline({"terminal_cold_start_seconds": {"count": 3, "median": 1.5, "p95": 1.7}}, source_version="1253.9.1")
req(record["content_free"] is True and record["release_authorized"] is False)
loaded = load_same_host_baseline()
req(loaded is not None and loaded["source_version"] == "1253.9.1")

# 6. Benchmark cleans its temporary runtime dirs and reports coherent metric names.
from runtime_efficiency_benchmark import benchmark_runtime_efficiency
before = {p.resolve() for p in Path(tempfile.gettempdir()).glob("eidolon-v1253-*") if p.is_dir()}
bench = benchmark_runtime_efficiency(source_root=ROOT, include_persistent_scale=True)
after = {p.resolve() for p in Path(tempfile.gettempdir()).glob("eidolon-v1253-*") if p.is_dir()}
req(bench["ok"])
req(after == before)
for name in (
    "terminal_cold_start_fresh_data_seconds",
    "terminal_cold_start_established_runtime_seconds",
    "python_process_start_seconds",
    "conversation_runtime_process_start_seconds",
    "conversation_runtime_incremental_import_seconds",
    "first_message_pre_provider_ms",
    "first_message_next_input_ready_ms",
    "first_message_provider_request_count",
):
    req(name in bench["measurements"])
req(float(bench["measurements"]["first_message_provider_request_count"]["median"]) == 1.0)
req(bench["fake_provider_used_for_first_message"] is True)
req(bench["provider_contacted"] is False)
req(bench["temporary_runtime_cleanup_scoped"] is True)
medium = bench["persistent_state_medium_scale"]
req(medium["benchmark_profile"] == "medium" and medium["profile_ok"] is True)
req(medium["full_scale_reached"] is False and "ok" not in medium)
req(medium["full_scale_ok"] is False)

# 7. Short mixed-load contention check: dashboard health + real cadence tick path + fake-provider chat.
from runtime_contention_benchmark import benchmark_runtime_contention
from performance_budgets import evaluate_budget
contention = benchmark_runtime_contention(source_root=ROOT)
req(contention["ok"])
req(contention["provider_contacted"] is False and contention["fake_provider"] is True)
req(float(contention["provider_request_count"]["median"]) == 1.0)
# Windows durability flushes and real-time scanning make a seven-sample p95
# equivalent to one hardware-sensitive maximum. Preserve a strict warm median
# while bounding, rather than promoting, a single filesystem outlier.
req(evaluate_budget("contention_warm_pre_provider_ms", contention["warm_pre_provider_ms"])["ok"])
req(float(contention["dashboard_fast_status_ms"]["p95"]) < 75.0)
req(contention["cadence_errors"] == [])

# 8. Repair contract/checkpoint, registry, release authority, docs, and generated metadata agree.
from pre_codex_runtime_coherence_repair import pre_codex_runtime_coherence_contract
from pre_codex_runtime_coherence_repair_checkpoint import build_pre_codex_runtime_coherence_repair_checkpoint
from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint, validate_checkpoint_report
from release_authority import release_authority_record, validate_release_authority
from release_metadata_consolidation import validate_release_metadata_consolidation
contract = pre_codex_runtime_coherence_contract(source_root=ROOT)
req(contract["ok"] and contract["passed"] == contract["total"])
cp = build_pre_codex_runtime_coherence_repair_checkpoint(source_root=ROOT)
req(cp["ok"] and cp["checkpoint_version"] == "1253.9.1")
req(validate_checkpoint_report(cp, source_root=ROOT)["ok"])
registry = checkpoint_registry_manifest(source_root=ROOT)
req(registry["ok"] and registry["record_count"] >= 92)
req(lookup_checkpoint("1253.9.1").title == "Pre-Codex Runtime Coherence Repair")
auth = release_authority_record()
req(auth["working_source_version"] == auth["history"][-1]["version"])
req(bool(auth["previous_working_source_version"]))
req(auth["history_count"] >= 92 and any(row.get("version") == "1253.9.2" for row in auth["history"]))
req(auth["schema_lineage_version"] == "v1250.0")
req(isinstance(auth["codex_review_state"], str) and bool(auth["codex_review_state"].strip()))
req(validate_release_authority(source_root=ROOT)["ok"])
req(validate_release_metadata_consolidation(source_root=ROOT)["ok"])
metadata = (ROOT / "conscious_agent/release_metadata.py").read_text(encoding="utf-8")
active_metadata = metadata.split("LEGACY_COMPATIBILITY_TEXT", 1)[0]
req('RUNTIME_UI_CONTRACT = "' in active_metadata and f"v{auth['working_source_version']}" in active_metadata)
req("HISTORICAL / ARCHIVAL DOCUMENT" in (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_DESKTOP_ALPHA.md").read_text(encoding="utf-8")[:500])
for key in (
    "installation_authorized", "promotion_authorized", "certification_authorized", "release_authorized",
    "provider_contact_authorized", "tool_execution_authorized", "project_mutation_authorized",
    "source_mutation_authorized", "approval_granted", "independent_authority_granted",
):
    req(auth[key] is False)

result = {
    "suite": "v1253.9.1-pre-codex-runtime-coherence-repair",
    "ok": all(checks),
    "passed": sum(checks),
    "total": len(checks),
    "maintenance_execution_count": 1,
    "benchmark_measurements": bench["measurements"],
    "contention_measurements": contention,
}
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
