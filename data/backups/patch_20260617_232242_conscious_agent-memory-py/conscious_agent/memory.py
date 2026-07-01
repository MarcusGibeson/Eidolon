import json
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import MEMORY_FILE, THOUGHT_LOG_FILE


def load_json(path: Path, default: Any) -> Any:
    """Load JSON safely. Empty or broken files return the supplied default."""
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_memories(limit: int | None = None) -> list[dict[str, Any]]:
    memories = load_json(MEMORY_FILE, [])
    if not isinstance(memories, list):
        memories = []
    return memories[-limit:] if limit else memories


def store_memory(memory: dict[str, Any]) -> None:
    memory.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    memories = load_memories()
    memories.append(memory)
    save_json(MEMORY_FILE, memories)

    with THOUGHT_LOG_FILE.open("a", encoding="utf-8") as log:
        content = memory.get("content") or memory.get("thought") or str(memory)
        log.write(f"[{memory['created_at']}] {memory.get('type', 'memory')}: {content}\n")

    # Also store a semantic vector when ChromaDB + Ollama embeddings are available.
    # This is intentionally non-fatal so Eidolon still works without the vector stack.
    try:
        from vector_memory import add_memory_vector
        add_memory_vector(memory)
    except Exception:
        # Semantic memory is optional. If ChromaDB/Ollama is unavailable, JSON memory still works.
        pass


def search_memories(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    keyword = keyword.lower().strip()
    matches = []
    for memory in reversed(load_memories()):
        text = json.dumps(memory).lower()
        if keyword in text:
            matches.append(memory)
        if len(matches) >= limit:
            break
    return matches
