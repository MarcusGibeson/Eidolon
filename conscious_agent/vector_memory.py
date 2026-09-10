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


def delete_memory_vector(memory_id: str) -> bool:
    """Delete one semantic-memory row without contacting an embedding provider."""
    token = str(memory_id or "").strip()
    if not token:
        return True
    collection = get_collection()
    if collection is None:
        return True
    try:
        collection.delete(ids=[token])
        return True
    except Exception as error:
        print(f"Vector memory deletion failed: {error}")
        return False


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


def inspect_memory_vector(memory_id: str) -> dict[str, Any]:
    """Return content-free presence evidence without invoking an embedding provider."""
    token = str(memory_id or "").strip()
    if not token:
        return {
            "status": "no_vector_identity",
            "present": False,
            "verified_absent": True,
            "semantic_store_available": False,
            "provider_invoked": False,
            "content_free": True,
        }
    try:
        collection = get_collection()
    except Exception as error:
        return {
            "status": "inspection_failed",
            "present": None,
            "verified_absent": False,
            "semantic_store_available": True,
            "provider_invoked": False,
            "content_free": True,
            "error_type": type(error).__name__,
        }
    if collection is None:
        return {
            "status": "semantic_store_unavailable",
            "present": None,
            "verified_absent": False,
            "semantic_store_available": False,
            "provider_invoked": False,
            "content_free": True,
        }
    try:
        result = collection.get(ids=[token])
        ids = result.get("ids") if isinstance(result, dict) else []
        flattened: list[str] = []
        if isinstance(ids, list):
            for item in ids:
                if isinstance(item, list):
                    flattened.extend(str(value) for value in item)
                else:
                    flattened.append(str(item))
        present = token in flattened
        return {
            "status": "present" if present else "absent",
            "present": present,
            "verified_absent": not present,
            "semantic_store_available": True,
            "provider_invoked": False,
            "content_free": True,
        }
    except Exception as error:
        return {
            "status": "inspection_failed",
            "present": None,
            "verified_absent": False,
            "semantic_store_available": True,
            "provider_invoked": False,
            "content_free": True,
            "error_type": type(error).__name__,
        }


def delete_memory_vector_verified(memory_id: str) -> dict[str, Any]:
    """Delete one vector row and return bounded absence evidence.

    A missing optional semantic store is reported honestly as unavailable but is not
    treated as a provider failure. No embedding or generation endpoint is contacted.
    """
    token = str(memory_id or "").strip()
    if not token:
        return {
            "cleanup_complete": True,
            "deletion_attempted": False,
            "verification_status": "no_vector_identity",
            "verified_absent": True,
            "semantic_store_available": False,
            "provider_invoked": False,
            "content_free": True,
        }
    before = inspect_memory_vector(token)
    if before.get("status") == "inspection_failed":
        return {
            "cleanup_complete": False,
            "deletion_attempted": False,
            "verification_status": "inspection_failed",
            "verified_absent": False,
            "semantic_store_available": bool(before.get("semantic_store_available")),
            "provider_invoked": False,
            "content_free": True,
            "error_type": str(before.get("error_type") or ""),
        }
    if before.get("status") == "semantic_store_unavailable":
        return {
            "cleanup_complete": True,
            "deletion_attempted": False,
            "verification_status": "semantic_store_unavailable",
            "verified_absent": False,
            "semantic_store_available": False,
            "provider_invoked": False,
            "content_free": True,
        }
    if before.get("verified_absent"):
        return {
            "cleanup_complete": True,
            "deletion_attempted": False,
            "verification_status": "already_absent",
            "verified_absent": True,
            "semantic_store_available": True,
            "provider_invoked": False,
            "content_free": True,
        }
    try:
        collection = get_collection()
        if collection is None:
            return {
                "cleanup_complete": True,
                "deletion_attempted": False,
                "verification_status": "semantic_store_unavailable",
                "verified_absent": False,
                "semantic_store_available": False,
                "provider_invoked": False,
                "content_free": True,
            }
        collection.delete(ids=[token])
    except Exception as error:
        return {
            "cleanup_complete": False,
            "deletion_attempted": True,
            "verification_status": "delete_failed",
            "verified_absent": False,
            "semantic_store_available": True,
            "provider_invoked": False,
            "content_free": True,
            "error_type": type(error).__name__,
        }
    after = inspect_memory_vector(token)
    return {
        "cleanup_complete": bool(after.get("verified_absent")),
        "deletion_attempted": True,
        "verification_status": "verified_absent" if after.get("verified_absent") else str(after.get("status") or "verification_failed"),
        "verified_absent": bool(after.get("verified_absent")),
        "semantic_store_available": bool(after.get("semantic_store_available")),
        "provider_invoked": False,
        "content_free": True,
        **({"error_type": str(after.get("error_type") or "")} if after.get("error_type") else {}),
    }
