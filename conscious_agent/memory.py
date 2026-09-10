import json
import os
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from paths import MEMORY_FILE, THOUGHT_LOG_FILE
try:
    from json_storage import load_json_file, write_json_atomic
    from persistent_state_index import append_memory_records, count_indexed_memories, load_indexed_memories, rebuild_memory_index, search_indexed_memories, memory_exists as indexed_memory_exists
    from persistent_state_projection_cache import cached_projection
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from persistent_state_index import (
        append_memory_records, count_indexed_memories, load_indexed_memories, rebuild_memory_index, search_indexed_memories, memory_exists as indexed_memory_exists,
    )
    from persistent_state_projection_cache import cached_projection

try:
    from memory_provenance_integrity import prepare_memory_for_ingestion
except ImportError:
    from memory_provenance_integrity import prepare_memory_for_ingestion

_MEMORY_LOCK = threading.RLock()
_T = TypeVar("_T")


def load_json(path: Path, default: Any) -> Any:
    """Load JSON safely, including Windows-created UTF-8 BOM files."""
    return load_json_file(path, default)


def save_json(path: Path, data: Any) -> None:
    """Persist JSON atomically as canonical UTF-8 without a BOM."""
    write_json_atomic(path, data)


def _save_memories_atomic(memories: list[dict[str, Any]]) -> None:
    write_json_atomic(MEMORY_FILE, memories, expected_type=list)


def mutate_memories(mutator: Callable[[list[dict[str, Any]]], _T]) -> _T:
    """Apply one read-modify-write operation under the shared memory lock."""
    with _MEMORY_LOCK:
        memories = load_memories()
        original = deepcopy(memories)
        result = mutator(memories)
        if memories != original:
            _save_memories_atomic(memories)
            rebuild_memory_index(MEMORY_FILE)
        return result


def load_memories(limit: int | None = None) -> list[dict[str, Any]]:
    """Load memories through the v1252 index while preserving legacy JSON authority."""
    with _MEMORY_LOCK:
        try:
            return load_indexed_memories(MEMORY_FILE, limit=limit)
        except Exception:
            memories = load_json(MEMORY_FILE, [])
            if not isinstance(memories, list):
                memories = []
            return memories[-limit:] if limit else memories


def count_memories() -> int:
    """Total memory count, falling back to the legacy JSON authority."""
    with _MEMORY_LOCK:
        try:
            return count_indexed_memories(MEMORY_FILE)
        except Exception:
            memories = load_json(MEMORY_FILE, [])
            return len(memories) if isinstance(memories, list) else 0


def store_memory(memory: dict[str, Any], *, vectorize: bool = True) -> None:
    with _MEMORY_LOCK:
        existing = load_memories(limit=256)
        prepared = prepare_memory_for_ingestion(memory, existing_records=existing)
        prepared.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        # Preserve historical caller semantics: the exact object supplied to store_memory
        # reflects the canonical stored record after ingestion normalization.
        memory.clear()
        memory.update(prepared)
        append_memory_records(MEMORY_FILE, [memory])

    with _MEMORY_LOCK:
        THOUGHT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with THOUGHT_LOG_FILE.open("a", encoding="utf-8") as log:
            content = memory.get("content") or memory.get("thought") or str(memory)
            log.write(f"[{memory['created_at']}] {memory.get('type', 'memory')}: {content}\n")

    if vectorize:
        store_memory_vector(memory)


def store_memory_vector(memory: dict[str, Any]) -> None:
    """Best-effort optional semantic indexing for an already-saved memory."""
    try:
        from vector_memory import add_memory_vector
        add_memory_vector(memory)
    except Exception:
        # Semantic memory is optional. If ChromaDB/Ollama is unavailable, JSON memory still works.
        pass


def store_memory_batch(items: Iterable[dict[str, Any]]) -> None:
    """Commit related memories to the canonical JSON store in one transaction."""
    records = [dict(item) for item in items if isinstance(item, dict)]
    if not records:
        return
    created_at = datetime.now().isoformat(timespec="seconds")
    with _MEMORY_LOCK:
        existing = load_memories(limit=256)
        prepared: list[dict[str, Any]] = []
        for record in records:
            candidate = prepare_memory_for_ingestion(record, existing_records=[*existing, *prepared])
            candidate.setdefault("created_at", created_at)
            prepared.append(candidate)
        records = prepared
        append_memory_records(MEMORY_FILE, records)

    with _MEMORY_LOCK:
        THOUGHT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with THOUGHT_LOG_FILE.open("a", encoding="utf-8") as log:
            for record in records:
                content = record.get("content") or record.get("thought") or str(record)
                log.write(f"[{record['created_at']}] {record.get('type', 'memory')}: {content}\n")

    try:
        from vector_memory import add_memory_vector
        for record in records:
            add_memory_vector(record)
    except Exception:
        pass



def memory_record_exists(operation_id: str, memory_type: str) -> bool:
    """Return exact operation/type existence from the private v1252 index."""
    with _MEMORY_LOCK:
        try:
            return indexed_memory_exists(MEMORY_FILE, operation_id, memory_type)
        except Exception:
            return any(
                str(memory.get("conversation_operation_id") or "") == str(operation_id or "")
                and str(memory.get("type") or "") == str(memory_type or "")
                for memory in load_memories() if isinstance(memory, dict)
            )

def search_memories(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search eligible memories after deterministic explicit correction suppression."""
    keyword = keyword.lower().strip()
    try:
        from context_correction_aware_retrieval import filter_correction_aware_records
        eligible, _evidence = filter_correction_aware_records(load_memories())
    except Exception:
        eligible = load_memories()
    matches = []
    for memory in reversed(eligible):
        text = json.dumps(memory).lower()
        if keyword in text:
            matches.append(memory)
        if len(matches) >= limit:
            break
    return matches
