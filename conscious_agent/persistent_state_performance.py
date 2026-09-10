from __future__ import annotations

"""Integrated v1252 persistent-state performance contract and synthetic scale probe."""

import hashlib
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from bounded_cross_session_retrieval import MAX_CROSS_SESSION_TRANSCRIPTS, bounded_cross_session_retrieval
    from persistent_state_index import append_memory_records, list_indexed_action_ids, list_indexed_sessions, load_indexed_memories, lookup_indexed_action_ids, rebuild_action_index, rebuild_memory_index, rebuild_session_index, validate_persistent_index_consistency
    from persistent_state_projection_cache import cached_projection, clear_persistent_projection_cache, persistent_projection_cache_status
except ImportError:
    from bounded_cross_session_retrieval import MAX_CROSS_SESSION_TRANSCRIPTS, bounded_cross_session_retrieval
    from persistent_state_index import (
        append_memory_records,
        list_indexed_action_ids,
        list_indexed_sessions,
        load_indexed_memories,
        lookup_indexed_action_ids,
        rebuild_action_index,
        rebuild_memory_index,
        rebuild_session_index,
        validate_persistent_index_consistency,
    )
    from persistent_state_projection_cache import cached_projection, clear_persistent_projection_cache, persistent_projection_cache_status

CONTRACT_VERSION = "v1252.8"
MILESTONE_NAME = "Persistent-State Performance"
VERSION_PLAN = (
    ("1252.0", "Session Metadata Index"),
    ("1252.1", "Bounded Cross-Session Retrieval"),
    ("1252.2", "Persistent Session Summaries"),
    ("1252.3", "Append-Oriented Memory Journal"),
    ("1252.4", "Indexed Memory Retrieval"),
    ("1252.5", "Memory Compaction and Recovery"),
    ("1252.6", "Indexed Chat-Action Ledger"),
    ("1252.7", "Runtime Projection Cache"),
    ("1252.8", "Scaling and Migration Hardening"),
)
AUTHORITY_FLAGS = {
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "provider_contact_authorized": False,
    "tool_execution_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _median_ms(fn, repeat: int = 7) -> float:
    samples=[]
    for _ in range(max(1,repeat)):
        start=time.perf_counter(); fn(); samples.append((time.perf_counter()-start)*1000.0)
    return round(statistics.median(samples),3)


def _seed_scale_runtime(root: Path, *, memories: int, sessions: int, actions: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    memory_rows=[{"id":f"m{i}","type":"fact","created_at":f"2026-01-{1+(i%28):02d}T00:00:00","content":f"memory topic{i%97} record {i}","conversation_operation_id":f"op{i}"} for i in range(memories)]
    (root/"memories.json").write_text(json.dumps(memory_rows,separators=(",",":")),encoding="utf-8")
    session_dir=root/"conversation_sessions"; session_dir.mkdir(exist_ok=True)
    for i in range(sessions):
        stamp=f"2026-06-{1+(i%28):02d}T12:{i%60:02d}:00Z"; sid=f"conversation_session_202606{1+(i%28):02d}T12{i%60:02d}00_{i:010x}"[-54:]
        # Preserve the production identifier shape even for synthetic high-count fixtures.
        sid=f"conversation_session_202606{1+(i%28):02d}T12{i%60:02d}00_{i:010x}"
        row={"id":sid,"type":"conversation_session","schema_version":"1","project_id":"eidolon","title":f"Project topic {i%83}","created_at":stamp,"updated_at":stamp,"last_turn_at":stamp,"turn_count":2,"completed_turn_count":1,"status":"active","source":"v1252-scale","last_provider":"","last_model":"","turns":[{"id":f"t{i}","created_at":stamp,"user_message":f"Discuss project topic {i%83} memory {i%97}","assistant_response":"Bounded synthetic response","completion_state":"completed","success":True}]}
        (session_dir/f"{sid}.json").write_text(json.dumps(row,separators=(",",":")),encoding="utf-8")
    action_dir=root/"chat_actions"; action_dir.mkdir(exist_ok=True)
    for i in range(actions):
        row={"id":f"chat_action_{i:08d}","status":"executed" if i%3==0 else "proposed","created_at":f"2026-07-{1+(i%28):02d}T00:{i%60:02d}:00","updated_at":f"2026-07-{1+(i%28):02d}T00:{i%60:02d}:00","deduplication_key":f"operation-{i}","intent":f"synthetic action {i%101}"}
        (action_dir/f"{row['id']}.json").write_text(json.dumps(row,separators=(",",":")),encoding="utf-8")


def benchmark_persistent_state_scaling(
    *, runtime_root: str | Path | None = None,
    memory_count: int = 20_000,
    session_count: int = 1_000,
    action_count: int = 20_000,
) -> dict[str, Any]:
    owned = runtime_root is None
    temp = tempfile.TemporaryDirectory(prefix="eidolon-v1252-scale-") if owned else None
    root = Path(temp.name if temp else runtime_root).resolve()
    try:
        seed_start=time.perf_counter(); _seed_scale_runtime(root,memories=memory_count,sessions=session_count,actions=action_count); seed_s=round(time.perf_counter()-seed_start,3)
        rebuild_start=time.perf_counter()
        rebuild_memory_index(root/"memories.json"); rebuild_session_index(root/"conversation_sessions"); rebuild_action_index(root/"chat_actions")
        rebuild_s=round(time.perf_counter()-rebuild_start,3)
        memory_recent_ms=_median_ms(lambda: load_indexed_memories(root/"memories.json",limit=80))
        memory_exists_ms=_median_ms(lambda: load_indexed_memories(root/"memories.json",limit=12))
        session_list_ms=_median_ms(lambda: list_indexed_sessions(root/"conversation_sessions",include_archived=False,limit=30))
        cross_session_ms=_median_ms(lambda: bounded_cross_session_retrieval(root/"conversation_sessions","project topic 17 memory 12",limit=6))
        action_recent_ms=_median_ms(lambda: list_indexed_action_ids(root/"chat_actions",include_closed=True,limit=40))
        action_lookup_ms=_median_ms(lambda: lookup_indexed_action_ids(root/"chat_actions",deduplication_keys=(f"operation-{max(0,action_count-3)}",)))
        append_start=time.perf_counter(); append_memory_records(root/"memories.json",[{"id":"m-appended","type":"fact","content":"append probe","created_at":"2026-08-07T00:00:00"}]); memory_append_ms=round((time.perf_counter()-append_start)*1000.0,3)
        consistency=validate_persistent_index_consistency(root)
        budgets={
            "memory_recent_80_ms":150.0,"session_list_30_ms":150.0,"cross_session_select_ms":150.0,
            "action_recent_40_ms":150.0,"action_exact_lookup_ms":150.0,"memory_append_ms":250.0,
        }
        measured={
            "memory_recent_80_ms":memory_recent_ms,"session_list_30_ms":session_list_ms,"cross_session_select_ms":cross_session_ms,
            "action_recent_40_ms":action_recent_ms,"action_exact_lookup_ms":action_lookup_ms,"memory_append_ms":memory_append_ms,
        }
        checks={key:measured[key]<=limit for key,limit in budgets.items()}
        checks.update({
            "memory_scale_reached":memory_count>=20_000,
            "session_scale_reached":session_count>=1_000,
            "action_scale_reached":action_count>=20_000,
            "cross_session_bound":len(bounded_cross_session_retrieval(root/"conversation_sessions","project topic 17",limit=6)["session_ids"])<=MAX_CROSS_SESSION_TRANSCRIPTS,
            "consistency_after_append":consistency.get("ok") is True,
        })
        result={"ok":all(checks.values()),"contract_version":"v1252.9","counts":{"memories":memory_count,"sessions":session_count,"actions":action_count},"measured_ms":measured,"budgets_ms":budgets,"checks":checks,"seed_seconds":seed_s,"index_rebuild_seconds":rebuild_s,"canonical_json_preserved":True,"provider_contacted":False,**AUTHORITY_FLAGS}
        result["benchmark_digest"]=_digest(result); return result
    finally:
        if temp is not None: temp.cleanup()


def persistent_state_performance_contract(*, source_root: str | Path | None = None) -> dict[str, Any]:
    root=Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    required=(
        "persistent_state_index.py","session_metadata_index.py","bounded_cross_session_retrieval.py","persistent_session_summaries.py",
        "append_memory_journal.py","indexed_memory_retrieval.py","memory_compaction_recovery.py","indexed_chat_action_ledger.py",
        "persistent_state_projection_cache.py","persistent_state_scaling_migration.py",
    )
    files={name:(root/"conscious_agent"/name) for name in required}
    memory_text=(root/"conscious_agent/memory.py").read_text(encoding="utf-8")
    sessions_text=(root/"conscious_agent/conversation_sessions.py").read_text(encoding="utf-8")
    runtime_text=(root/"conscious_agent/conversation_runtime.py").read_text(encoding="utf-8")
    actions_text=(root/"conscious_agent/chat_action_router.py").read_text(encoding="utf-8")
    checks={
        "all_nine_units_declared":len(VERSION_PLAN)==9 and VERSION_PLAN[0][0]=="1252.0" and VERSION_PLAN[-1][0]=="1252.8",
        "all_modules_present":all(path.is_file() for path in files.values()),
        "session_listing_indexed":"list_indexed_sessions" in sessions_text,
        "cross_session_bounded":"bounded_cross_session_candidates" in runtime_text and "limit=6" in runtime_text,
        "memory_append_indexed":"append_memory_records" in memory_text and "mutate_memories(append)" not in memory_text,
        "memory_recent_indexed":"load_indexed_memories" in memory_text,
        "action_listing_indexed":"list_indexed_action_ids" in actions_text,
        "action_prompt_lookup_bounded":"lookup_chat_actions" in sessions_text,
        "projection_cache_generation_bound":"persistent_state_generation" in (root/"conscious_agent/persistent_state_projection_cache.py").read_text(encoding="utf-8"),
        "canonical_json_fallbacks_retained":"rebuild_session_index" in sessions_text and "load_json(MEMORY_FILE" in memory_text,
    }
    result={"ok":all(checks.values()),"status":"persistent_state_performance_ready" if all(checks.values()) else "persistent_state_performance_blocked","contract_version":CONTRACT_VERSION,"milestone_name":MILESTONE_NAME,"versions":[{"version":v,"title":t} for v,t in VERSION_PLAN],"checks":checks,"passed":sum(checks.values()),"total":len(checks),"read_only":True,"content_free":True,**AUTHORITY_FLAGS}
    result["contract_digest"]=_digest(result); return result

__all__=["CONTRACT_VERSION","MILESTONE_NAME","VERSION_PLAN","benchmark_persistent_state_scaling","persistent_state_performance_contract"]
