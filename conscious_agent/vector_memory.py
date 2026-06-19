from __future__ import annotations

from typing import Any
import uuid

from paths import DATA_DIR
from local_brain import local_embed


CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "eidolon_memories"
_WARNED_CHROMA_MISSING = False


def _get_chromadb():
    """
    Imports Chroma lazily so the rest of Eidolon still runs if ChromaDB is not installed.
    """
    try:
        import chromadb  # type: ignore
        return chromadb
    except ImportError:
        return None


def get_collection():
    chromadb = _get_chromadb()
    if chromadb is None:
        return None

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(name=COLLECTION_NAME)


def _memory_content(memory: dict[str, Any]) -> str:
    content = memory.get("content") or memory.get("thought") or ""
    return str(content).strip()


def add_memory_vector(memory: dict[str, Any]) -> str:
    """
    Stores a memory in ChromaDB with a local embedding.
    Returns the vector memory id, or an empty string if skipped.
    """
    content = _memory_content(memory)
    if not content:
        return ""

    collection = get_collection()
    if collection is None:
        return ""

    embedding = local_embed(content)
    if not embedding:
        return ""

    memory_id = memory.get("id") or str(uuid.uuid4())
    memory["id"] = memory_id

    metadata = {
        "type": str(memory.get("type", "memory")),
        "importance": float(memory.get("importance", 0.5)),
        "created_at": str(memory.get("created_at", "")),
        "source": str(memory.get("source", "")),
    }

    try:
        # Chroma throws if an id already exists, so upsert is the least dramatic option.
        collection.upsert(
            ids=[memory_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        return memory_id
    except Exception as error:
        print(f"Vector memory store failed: {error}")
        return ""


def search_memory_vectors(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Searches stored memories by meaning instead of exact words.
    """
    if not query.strip():
        return []

    collection = get_collection()
    if collection is None:
        return []

    query_embedding = local_embed(query)
    if not query_embedding:
        return []

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )
    except Exception as error:
        print(f"Vector memory search failed: {error}")
        return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    memories: list[dict[str, Any]] = []

    for index, document in enumerate(documents):
        memories.append({
            "id": ids[index] if index < len(ids) else "",
            "type": "semantic_memory_result",
            "content": document,
            "metadata": metadatas[index] if index < len(metadatas) else {},
            "distance": distances[index] if index < len(distances) else None,
        })

    return memories


def rebuild_vector_memory(memories: list[dict[str, Any]]) -> int:
    """
    Adds existing JSON memories into Chroma. Useful after turning semantic memory on.
    """
    count = 0
    for memory in memories:
        if add_memory_vector(memory):
            count += 1
    return count


def reset_vector_memory() -> bool:
    """
    Deletes and recreates the Chroma collection so semantic memory matches current JSON memory.
    Returns True if reset succeeded or Chroma is unavailable.
    """
    chromadb = _get_chromadb()
    if chromadb is None:
        return True

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            # Collection may not exist yet. That is fine, despite software's urge to be dramatic.
            pass
        client.get_or_create_collection(name=COLLECTION_NAME)
        return True
    except Exception as error:
        print(f"Vector memory reset failed: {error}")
        return False
