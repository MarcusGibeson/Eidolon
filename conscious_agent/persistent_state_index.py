from __future__ import annotations

"""Private runtime indexes for v1252 persistent-state performance.

Canonical conversation transcripts and chat-action receipts remain JSON files.
The memory JSON list also remains compatibility-visible, but ordinary append
operations no longer need to parse and rewrite the entire file.  SQLite holds
only private runtime indexes/copies used for bounded retrieval.  No record in
this module grants execution, approval, release, provider-contact, or mutation
authority outside the explicitly requested persistence operation.
"""

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "v1252.0"
INDEX_FILENAME = "persistent_state_index.sqlite3"
SCHEMA_VERSION = 3
_MAX_SUMMARY_CHARS = 720
_MAX_SEARCH_CHARS = 4096
_INDEX_LOCK = threading.RLock()
_STOPWORDS = {
    "the","and","for","that","this","with","you","your","are","was","were","from","have","has","had",
    "but","not","what","when","where","who","how","why","can","could","would","should","will","just",
    "into","about","there","their","they","them","then","than","also","been","being","its","our","out",
    "all","any","some","more","most","very","too","here","please","thanks","thank","hello","hi",
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _data_root_from(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.is_dir():
        return resolved.parent if resolved.name in {"conversation_sessions", "chat_actions"} else resolved
    return resolved.parent


def index_path_for(path: str | Path) -> Path:
    return _data_root_from(Path(path)) / INDEX_FILENAME


def _file_signature(path: Path) -> str:
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_size)}:{int(stat.st_mtime_ns)}"


def _connect(index_path: Path) -> sqlite3.Connection:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(index_path), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS session_index (
            session_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_turn_at TEXT NOT NULL,
            turn_count INTEGER NOT NULL,
            completed_turn_count INTEGER NOT NULL,
            summary TEXT NOT NULL,
            search_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            source_signature TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_session_project_updated ON session_index(project_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_session_updated ON session_index(status, updated_at DESC);
        CREATE TABLE IF NOT EXISTS memory_index (
            sequence INTEGER PRIMARY KEY,
            memory_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            search_text TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_digest TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_index(created_at DESC, sequence DESC);
        CREATE INDEX IF NOT EXISTS idx_memory_operation ON memory_index(operation_id, memory_type);
        CREATE INDEX IF NOT EXISTS idx_memory_session ON memory_index(session_id, sequence DESC);
        CREATE TABLE IF NOT EXISTS action_index (
            action_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deduplication_key TEXT NOT NULL,
            intent TEXT NOT NULL,
            capability_id TEXT NOT NULL,
            search_text TEXT NOT NULL,
            source_signature TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_action_created ON action_index(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_action_status_created ON action_index(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_action_dedup ON action_index(deduplication_key);
        """
    )
    connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    connection.commit()
    return connection


def _connect_readonly(index_path: Path) -> sqlite3.Connection:
    """Open an existing index without creating files or metadata writes."""
    if not index_path.is_file():
        raise FileNotFoundError(index_path)
    uri_path = index_path.resolve().as_posix().replace("?", "%3f").replace("#", "%23")
    connection = sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True, timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA temp_store=MEMORY")
    return connection


def _metadata_get(connection: sqlite3.Connection, key: str) -> str:
    row = connection.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return str(row[0]) if row else ""


def _metadata_set(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)", (key, str(value)))


def _bump_generation(connection: sqlite3.Connection, domain: str) -> int:
    key = f"{domain}_generation"
    try:
        value = int(_metadata_get(connection, key) or 0) + 1
    except ValueError:
        value = 1
    _metadata_set(connection, key, str(value))
    return value


def persistent_state_generation(path: str | Path, domain: str) -> int:
    index_path = index_path_for(path)
    if not index_path.is_file():
        return 0
    try:
        with _INDEX_LOCK, closing(_connect_readonly(index_path)) as connection:
            return int(_metadata_get(connection, f"{str(domain)}_generation") or 0)
    except (FileNotFoundError, sqlite3.Error, ValueError):
        return 0


def _tokens(text: str, *, limit: int = 64) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_'-]{3,}", str(text or "").lower()):
        token = token.strip("_'-")
        if not token or token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        rows.append(token[:64])
        if len(rows) >= limit:
            break
    return rows


def _session_projection(session: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    metadata = {key: value for key, value in session.items() if key != "turns"}
    turns = [row for row in session.get("turns", []) if isinstance(row, Mapping)]
    completed = [
        row for row in turns
        if row.get("success") is True and str(row.get("completion_state") or "") == "completed"
    ]
    summary_parts = [str(metadata.get("title") or "New conversation").strip()]
    for row in completed[-2:]:
        user = " ".join(str(row.get("user_message") or "").split())[:220]
        assistant = " ".join(str(row.get("assistant_response") or "").split())[:260]
        if user:
            summary_parts.append(f"User: {user}")
        if assistant:
            summary_parts.append(f"Assistant: {assistant}")
    summary = " | ".join(part for part in summary_parts if part)[:_MAX_SUMMARY_CHARS]
    search_sources = [str(metadata.get("title") or ""), summary]
    for row in completed[-6:]:
        search_sources.append(str(row.get("user_message") or "")[:500])
        search_sources.append(str(row.get("assistant_response") or "")[:500])
    search_text = " ".join(_tokens(" ".join(search_sources), limit=96))[:_MAX_SEARCH_CHARS]
    return metadata, summary, search_text


def update_session_index(session_dir: str | Path, session: Mapping[str, Any]) -> None:
    session_id = str(session.get("id") or "").strip()
    if not session_id:
        return
    directory = Path(session_dir)
    _prepare_session_index_for_write(directory)
    metadata, summary, search_text = _session_projection(session)
    source_path = directory / f"{session_id}.json"
    with _INDEX_LOCK, closing(_connect(index_path_for(directory))) as connection:
        connection.execute(
            """INSERT OR REPLACE INTO session_index(
                session_id,project_id,status,title,created_at,updated_at,last_turn_at,turn_count,
                completed_turn_count,summary,search_text,metadata_json,source_signature
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id,
                str(metadata.get("project_id") or "eidolon"),
                str(metadata.get("status") or "active"),
                str(metadata.get("title") or "New conversation")[:200],
                str(metadata.get("created_at") or ""),
                str(metadata.get("updated_at") or metadata.get("created_at") or ""),
                str(metadata.get("last_turn_at") or ""),
                int(metadata.get("turn_count") or len(session.get("turns", []) or [])),
                int(metadata.get("completed_turn_count") or 0),
                summary,
                search_text,
                json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str),
                _file_signature(source_path),
            ),
        )
        _metadata_set(connection, "session_index_initialized", "1")
        _bump_generation(connection, "session")
        connection.commit()


def rebuild_session_index(session_dir: str | Path) -> dict[str, Any]:
    directory = Path(session_dir)
    indexed = 0
    skipped = 0
    with _INDEX_LOCK, closing(_connect(index_path_for(directory))) as connection:
        connection.execute("DELETE FROM session_index")
        for path in sorted(directory.glob("conversation_session_*.json")) if directory.exists() else ():
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                skipped += 1
                continue
            if not isinstance(data, dict) or data.get("type") != "conversation_session":
                skipped += 1
                continue
            metadata, summary, search_text = _session_projection(data)
            connection.execute(
                """INSERT OR REPLACE INTO session_index(
                    session_id,project_id,status,title,created_at,updated_at,last_turn_at,turn_count,
                    completed_turn_count,summary,search_text,metadata_json,source_signature
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(data.get("id") or path.stem), str(metadata.get("project_id") or "eidolon"),
                    str(metadata.get("status") or "active"), str(metadata.get("title") or "New conversation")[:200],
                    str(metadata.get("created_at") or ""), str(metadata.get("updated_at") or metadata.get("created_at") or ""),
                    str(metadata.get("last_turn_at") or ""), int(metadata.get("turn_count") or len(data.get("turns", []) or [])),
                    int(metadata.get("completed_turn_count") or 0), summary, search_text,
                    json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str),
                    _file_signature(path),
                ),
            )
            indexed += 1
        _metadata_set(connection, "session_index_initialized", "1")
        _metadata_set(connection, "session_index_rebuilt_at_ns", str(time.time_ns()))
        _bump_generation(connection, "session")
        connection.commit()
    return {"ok": True, "indexed": indexed, "skipped": skipped, "read_only_source": True}


def _ensure_session_index(session_dir: Path) -> bool:
    """Return whether a complete initialized session index is available without writing."""
    index_path = index_path_for(session_dir)
    if not index_path.is_file():
        return False
    try:
        with _INDEX_LOCK, closing(_connect_readonly(index_path)) as connection:
            return _metadata_get(connection, "session_index_initialized") == "1"
    except sqlite3.Error:
        return False


def _prepare_session_index_for_write(session_dir: Path) -> None:
    """Rebuild legacy session metadata only from an already-authorized canonical write path."""
    if not _ensure_session_index(session_dir):
        rebuild_session_index(session_dir)


def list_indexed_sessions(
    session_dir: str | Path,
    *,
    include_archived: bool = False,
    project_id: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    directory = Path(session_dir)
    if not _ensure_session_index(directory):
        raise LookupError("session index is not initialized")
    clauses: list[str] = []
    params: list[Any] = []
    if not include_archived:
        clauses.append("status != 'archived'")
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(str(project_id or "eidolon"))
    query = "SELECT metadata_json FROM session_index"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC, created_at DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(max(0, int(limit)))
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(directory))) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


def select_cross_session_ids(
    session_dir: str | Path,
    user_message: str,
    *,
    exclude_session_id: str = "",
    project_id: str | None = None,
    limit: int = 6,
    candidate_limit: int = 48,
) -> list[str]:
    directory = Path(session_dir)
    if not _ensure_session_index(directory):
        raise LookupError("session index is not initialized")
    clauses = ["status != 'archived'"]
    params: list[Any] = []
    if exclude_session_id:
        clauses.append("session_id != ?")
        params.append(str(exclude_session_id))
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(str(project_id or "eidolon"))
    query = (
        "SELECT session_id,updated_at,title,search_text FROM session_index WHERE "
        + " AND ".join(clauses)
        + " ORDER BY updated_at DESC LIMIT ?"
    )
    params.append(max(int(candidate_limit), int(limit)))
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(directory))) as connection:
        candidates = connection.execute(query, tuple(params)).fetchall()
    wanted = set(_tokens(user_message, limit=16))
    scored: list[tuple[int, str, str]] = []
    for row in candidates:
        searchable = set(str(row[3] or "").split()) | set(_tokens(str(row[2] or ""), limit=16))
        overlap = len(wanted & searchable)
        score = overlap * 100
        if wanted and overlap == 0:
            score = 0
        elif not wanted:
            score = 1
        scored.append((score, str(row[1] or ""), str(row[0])))
    if wanted and any(score > 0 for score, _stamp, _sid in scored):
        scored = [row for row in scored if row[0] > 0]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [session_id for _score, _stamp, session_id in scored[: max(0, int(limit))]]


def session_summary(session_dir: str | Path, session_id: str) -> dict[str, Any] | None:
    directory = Path(session_dir)
    if not _ensure_session_index(directory):
        raise LookupError("session index is not initialized")
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(directory))) as connection:
        row = connection.execute(
            "SELECT summary,search_text,metadata_json FROM session_index WHERE session_id=?", (str(session_id),)
        ).fetchone()
    if not row:
        return None
    try:
        metadata = json.loads(str(row[2]))
    except json.JSONDecodeError:
        metadata = {}
    return {
        "session_id": str(session_id),
        "summary": str(row[0] or ""),
        "topics": str(row[1] or "").split()[:32],
        "metadata": metadata if isinstance(metadata, dict) else {},
        "content_free_index_metadata": False,
        "private_local_runtime": True,
    }


# ---------------------------------------------------------------------------
# Memory index and crash-recoverable append path
# ---------------------------------------------------------------------------


def _memory_payload(memory: Mapping[str, Any]) -> tuple[str, str, str, str, str, str]:
    payload = json.dumps(dict(memory), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    memory_id = str(memory.get("id") or memory.get("memory_candidate_id") or "")[:160]
    created_at = str(memory.get("created_at") or "")[:80]
    memory_type = str(memory.get("type") or "memory")[:80]
    operation_id = str(memory.get("conversation_operation_id") or "")[:160]
    session_id = str(memory.get("conversation_session_id") or "")[:160]
    search_text = " ".join(_tokens(payload, limit=96))[:_MAX_SEARCH_CHARS]
    return memory_id, created_at, memory_type, operation_id, session_id, search_text


def rebuild_memory_index(memory_file: str | Path) -> dict[str, Any]:
    path = Path(memory_file)
    try:
        rows = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else []
    except (OSError, json.JSONDecodeError):
        rows = []
    if not isinstance(rows, list):
        rows = []
    index_path = index_path_for(path)
    with _INDEX_LOCK, closing(_connect(index_path)) as connection:
        connection.execute("DELETE FROM memory_index")
        for sequence, memory in enumerate(rows, 1):
            if not isinstance(memory, Mapping):
                continue
            memory_id, created_at, memory_type, operation_id, session_id, search_text = _memory_payload(memory)
            payload = json.dumps(dict(memory), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
            connection.execute(
                """INSERT INTO memory_index(sequence,memory_id,created_at,memory_type,operation_id,session_id,search_text,payload_json,payload_digest)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (sequence, memory_id, created_at, memory_type, operation_id, session_id, search_text, payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()),
            )
        _metadata_set(connection, "memory_source_signature", _file_signature(path))
        _metadata_set(connection, "memory_index_initialized", "1")
        _metadata_set(connection, "memory_count", str(len(rows)))
        _bump_generation(connection, "memory")
        connection.commit()
    return {"ok": True, "indexed": len(rows), "source_signature": _file_signature(path)}


def _ensure_memory_index(memory_file: Path) -> bool:
    """Return whether the memory index matches canonical JSON without mutating either."""
    index_path = index_path_for(memory_file)
    current_signature = _file_signature(memory_file)
    if not index_path.is_file():
        return False
    try:
        with _INDEX_LOCK, closing(_connect_readonly(index_path)) as connection:
            initialized = _metadata_get(connection, "memory_index_initialized") == "1"
            indexed_signature = _metadata_get(connection, "memory_source_signature")
    except sqlite3.Error:
        return False
    return bool(initialized and indexed_signature == current_signature)


def _prepare_memory_index_for_write(memory_file: Path) -> None:
    """Reconcile legacy memory JSON only from an explicit memory mutation path."""
    if not _ensure_memory_index(memory_file):
        rebuild_memory_index(memory_file)


def count_indexed_memories(memory_file: str | Path) -> int:
    """Count memories without materializing them.

    The status surface only needs a total, and reading every payload to take its
    length holds the index lock across a full scan. A conversation request that
    already holds the session lock then waits behind it, so every other request
    queues too.
    """
    path = Path(memory_file)
    if not _ensure_memory_index(path):
        raise LookupError("memory index is not initialized or is stale")
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(path))) as connection:
        row = connection.execute("SELECT COUNT(*) FROM memory_index").fetchone()
    return int(row[0]) if row else 0


def load_indexed_memories(memory_file: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    path = Path(memory_file)
    if not _ensure_memory_index(path):
        raise LookupError("memory index is not initialized or is stale")
    query = "SELECT payload_json FROM memory_index ORDER BY sequence"
    params: tuple[Any, ...] = ()
    if limit:
        query = "SELECT payload_json FROM memory_index ORDER BY sequence DESC LIMIT ?"
        params = (max(0, int(limit)),)
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(path))) as connection:
        rows = connection.execute(query, params).fetchall()
    if limit:
        rows = list(reversed(rows))
    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


def memory_exists(memory_file: str | Path, operation_id: str, memory_type: str) -> bool:
    path = Path(memory_file)
    if not _ensure_memory_index(path):
        raise LookupError("memory index is not initialized or is stale")
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(path))) as connection:
        row = connection.execute(
            "SELECT 1 FROM memory_index WHERE operation_id=? AND memory_type=? LIMIT 1",
            (str(operation_id), str(memory_type)),
        ).fetchone()
    return bool(row)


def search_indexed_memories(memory_file: str | Path, keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    path = Path(memory_file)
    if not _ensure_memory_index(path):
        raise LookupError("memory index is not initialized or is stale")
    wanted = _tokens(keyword, limit=8)
    if not wanted:
        return []
    # Search a bounded recent candidate window. Correction-aware filtering remains
    # at the public memory layer because it owns semantic eligibility rules.
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(path))) as connection:
        rows = connection.execute(
            "SELECT payload_json,search_text FROM memory_index ORDER BY sequence DESC LIMIT ?",
            (max(64, int(limit) * 32),),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        search_text = set(str(row[1] or "").split())
        if not all(token in search_text for token in wanted):
            continue
        try:
            value = json.loads(str(row[0]))
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
        if len(result) >= max(0, int(limit)):
            break
    return result


def _journal_path(memory_file: Path) -> Path:
    return memory_file.with_name(f"{memory_file.name}.append-journal.json")


def _recover_pending_memory_append(memory_file: Path) -> dict[str, Any]:
    journal = _journal_path(memory_file)
    if not journal.is_file():
        return {"recovered": False, "action": "none"}
    try:
        state = json.loads(journal.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        journal.unlink(missing_ok=True)
        return {"recovered": True, "action": "discarded_invalid_journal"}
    if not isinstance(state, dict):
        journal.unlink(missing_ok=True)
        return {"recovered": True, "action": "discarded_invalid_journal"}
    expected_digest = str(state.get("last_record_digest") or "")
    try:
        rows = json.loads(memory_file.read_text(encoding="utf-8-sig")) if memory_file.is_file() else []
    except (OSError, json.JSONDecodeError):
        rows = None
    if isinstance(rows, list) and rows:
        last_payload = json.dumps(rows[-1], sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        if hashlib.sha256(last_payload.encode("utf-8")).hexdigest() == expected_digest:
            journal.unlink(missing_ok=True)
            return {"recovered": True, "action": "committed_append_confirmed"}
    insertion_offset = int(state.get("insertion_offset") or 0)
    tail_hex = str(state.get("tail_hex") or "")
    try:
        tail = bytes.fromhex(tail_hex)
    except ValueError:
        tail = b"]\n"
    try:
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        with memory_file.open("r+b" if memory_file.exists() else "wb") as handle:
            handle.seek(max(0, insertion_offset))
            handle.write(tail)
            handle.truncate(max(0, insertion_offset) + len(tail))
            handle.flush()
            os.fsync(handle.fileno())
        action = "rolled_back_incomplete_append"
    except OSError:
        action = "recovery_failed"
    if action != "recovery_failed":
        journal.unlink(missing_ok=True)
    return {"recovered": True, "action": action}


def _append_json_array_records(memory_file: Path, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"ok": True, "appended": 0, "recovery": {"recovered": False, "action": "none"}}
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    if not memory_file.exists():
        memory_file.write_text("[]\n", encoding="utf-8")
    recovery = _recover_pending_memory_append(memory_file)
    with memory_file.open("r+b") as handle:
        handle.seek(0, os.SEEK_END)
        end = handle.tell()
        cursor = end
        while cursor > 0:
            cursor -= 1
            handle.seek(cursor)
            byte = handle.read(1)
            if byte not in b" \t\r\n":
                break
        if byte != b"]":
            raise ValueError("Legacy memory store is not a JSON array; indexed append refused.")
        insertion_offset = cursor
        cursor -= 1
        previous_nonspace = b""
        while cursor >= 0:
            handle.seek(cursor)
            previous_nonspace = handle.read(1)
            if previous_nonspace not in b" \t\r\n":
                break
            cursor -= 1
        is_empty = previous_nonspace == b"["
        handle.seek(insertion_offset)
        tail = handle.read(end - insertion_offset)
        serialized = [json.dumps(dict(row), ensure_ascii=False, separators=(",", ":"), default=str) for row in records]
        separator = "" if is_empty else ","
        body = separator + ",".join(serialized) + "]\n"
        last_canonical = json.dumps(dict(records[-1]), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        journal_state = {
            "schema_version": 1,
            "insertion_offset": insertion_offset,
            "tail_hex": tail.hex(),
            "record_count": len(records),
            "last_record_digest": hashlib.sha256(last_canonical.encode("utf-8")).hexdigest(),
        }
        journal = _journal_path(memory_file)
        with journal.open("w", encoding="utf-8") as jf:
            json.dump(journal_state, jf, sort_keys=True)
            jf.flush()
            os.fsync(jf.fileno())
        handle.seek(insertion_offset)
        handle.write(body.encode("utf-8"))
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())
    journal.unlink(missing_ok=True)
    return {"ok": True, "appended": len(records), "recovery": recovery}


def append_memory_records(memory_file: str | Path, records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    path = Path(memory_file)
    rows = [dict(row) for row in records if isinstance(row, Mapping)]
    if not rows:
        return {"ok": True, "appended": 0}
    # Reconcile externally edited legacy stores only because this call is already a canonical memory mutation.
    _prepare_memory_index_for_write(path)
    with _INDEX_LOCK:
        append_report = _append_json_array_records(path, rows)
        index_path = index_path_for(path)
        with closing(_connect(index_path)) as connection:
            current_max = int(connection.execute("SELECT COALESCE(MAX(sequence),0) FROM memory_index").fetchone()[0])
            for offset, memory in enumerate(rows, 1):
                memory_id, created_at, memory_type, operation_id, session_id, search_text = _memory_payload(memory)
                payload = json.dumps(memory, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
                connection.execute(
                    """INSERT OR REPLACE INTO memory_index(sequence,memory_id,created_at,memory_type,operation_id,session_id,search_text,payload_json,payload_digest)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (current_max + offset, memory_id, created_at, memory_type, operation_id, session_id, search_text, payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()),
                )
            _metadata_set(connection, "memory_source_signature", _file_signature(path))
            _metadata_set(connection, "memory_index_initialized", "1")
            _metadata_set(connection, "memory_count", str(current_max + len(rows)))
            _bump_generation(connection, "memory")
            connection.commit()
    append_report.update({"index_updated": True, "source_signature": _file_signature(path)})
    return append_report


def compact_memory_store(memory_file: str | Path) -> dict[str, Any]:
    path = Path(memory_file)
    _prepare_memory_index_for_write(path)
    memories = load_indexed_memories(path)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.compact.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(memories, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    report = rebuild_memory_index(path)
    report.update({"compacted": True, "count": len(memories)})
    return report


# ---------------------------------------------------------------------------
# Chat-action receipt index
# ---------------------------------------------------------------------------


def _action_fields(action: Mapping[str, Any]) -> tuple[str, ...]:
    action_id = str(action.get("id") or "")
    status = str(action.get("status") or "")
    created_at = str(action.get("created_at") or "")
    updated_at = str(action.get("updated_at") or created_at)
    dedup = str(action.get("deduplication_key") or "")
    intent = str(action.get("intent") or action.get("action_intent") or "")[:240]
    grounding = action.get("grounding") if isinstance(action.get("grounding"), Mapping) else {}
    capability = str(action.get("capability_id") or grounding.get("capability_id") or "")[:120]
    search_text = " ".join(_tokens(" ".join((intent, capability, dedup, status)), limit=64))
    return action_id, status, created_at, updated_at, dedup, intent, capability, search_text


def update_action_index(action_dir: str | Path, action: Mapping[str, Any]) -> None:
    action_id, status, created_at, updated_at, dedup, intent, capability, search_text = _action_fields(action)
    if not action_id:
        return
    directory = Path(action_dir)
    _prepare_action_index_for_write(directory)
    source_path = directory / f"{action_id}.json"
    with _INDEX_LOCK, closing(_connect(index_path_for(directory))) as connection:
        connection.execute(
            """INSERT OR REPLACE INTO action_index(action_id,status,created_at,updated_at,deduplication_key,intent,capability_id,search_text,source_signature)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (action_id, status, created_at, updated_at, dedup, intent, capability, search_text, _file_signature(source_path)),
        )
        _metadata_set(connection, "action_index_initialized", "1")
        _bump_generation(connection, "action")
        connection.commit()


def rebuild_action_index(action_dir: str | Path) -> dict[str, Any]:
    directory = Path(action_dir)
    indexed = 0
    with _INDEX_LOCK, closing(_connect(index_path_for(directory))) as connection:
        connection.execute("DELETE FROM action_index")
        for path in sorted(directory.glob("*.json")) if directory.exists() else ():
            if path.name == "README.md":
                continue
            try:
                action = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(action, dict) or not action.get("id"):
                continue
            fields = _action_fields(action)
            connection.execute(
                """INSERT OR REPLACE INTO action_index(action_id,status,created_at,updated_at,deduplication_key,intent,capability_id,search_text,source_signature)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (*fields, _file_signature(path)),
            )
            indexed += 1
        _metadata_set(connection, "action_index_initialized", "1")
        _bump_generation(connection, "action")
        connection.commit()
    return {"ok": True, "indexed": indexed}


def _ensure_action_index(action_dir: Path) -> bool:
    """Return whether a complete action index is available without writing."""
    index_path = index_path_for(action_dir)
    if not index_path.is_file():
        return False
    try:
        with _INDEX_LOCK, closing(_connect_readonly(index_path)) as connection:
            return _metadata_get(connection, "action_index_initialized") == "1"
    except sqlite3.Error:
        return False


def _prepare_action_index_for_write(action_dir: Path) -> None:
    if not _ensure_action_index(action_dir):
        rebuild_action_index(action_dir)


def list_indexed_action_ids(
    action_dir: str | Path, *, status: str = "", include_closed: bool = True, limit: int | None = None
) -> list[str]:
    directory = Path(action_dir)
    if not _ensure_action_index(directory):
        raise LookupError("action index is not initialized")
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status=?")
        params.append(str(status))
    if not include_closed:
        clauses.append("status IN ('proposed','approval_required')")
    query = "SELECT action_id FROM action_index"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(max(0, int(limit)))
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(directory))) as connection:
        return [str(row[0]) for row in connection.execute(query, tuple(params)).fetchall()]


def lookup_indexed_action_ids(
    action_dir: str | Path, *, action_ids: Sequence[str] = (), deduplication_keys: Sequence[str] = ()
) -> list[str]:
    directory = Path(action_dir)
    if not _ensure_action_index(directory):
        raise LookupError("action index is not initialized")
    wanted_ids = [str(value) for value in action_ids if str(value or "").strip()]
    wanted_dedup = [str(value) for value in deduplication_keys if str(value or "").strip()]
    clauses: list[str] = []
    params: list[Any] = []
    if wanted_ids:
        clauses.append("action_id IN (%s)" % ",".join("?" for _ in wanted_ids))
        params.extend(wanted_ids)
    if wanted_dedup:
        clauses.append("deduplication_key IN (%s)" % ",".join("?" for _ in wanted_dedup))
        params.extend(wanted_dedup)
    if not clauses:
        return []
    query = "SELECT action_id FROM action_index WHERE " + " OR ".join(clauses) + " ORDER BY created_at DESC"
    with _INDEX_LOCK, closing(_connect_readonly(index_path_for(directory))) as connection:
        return [str(row[0]) for row in connection.execute(query, tuple(params)).fetchall()]


def persistent_state_index_status(path: str | Path) -> dict[str, Any]:
    index_path = index_path_for(path)
    counts = {"sessions": 0, "memories": 0, "actions": 0}
    schema = str(SCHEMA_VERSION)
    if index_path.is_file():
        try:
            with _INDEX_LOCK, closing(_connect_readonly(index_path)) as connection:
                counts = {
                    "sessions": int(connection.execute("SELECT COUNT(*) FROM session_index").fetchone()[0]),
                    "memories": int(connection.execute("SELECT COUNT(*) FROM memory_index").fetchone()[0]),
                    "actions": int(connection.execute("SELECT COUNT(*) FROM action_index").fetchone()[0]),
                }
                schema = _metadata_get(connection, "schema_version") or str(SCHEMA_VERSION)
        except sqlite3.Error:
            pass
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "schema_version": int(schema or SCHEMA_VERSION),
        "counts": counts,
        "index_path": str(index_path),
        "canonical_json_preserved": True,
        "private_runtime_index": True,
        "read_only_inspection": True,
        "authority_granted": False,
    }


def recover_memory_append_journal(memory_file: str | Path) -> dict[str, Any]:
    """Public bounded recovery entry point used by v1252.5 validation."""
    path = Path(memory_file)
    with _INDEX_LOCK:
        report = _recover_pending_memory_append(path)
        if report.get("recovered"):
            rebuild_memory_index(path)
        return report


def validate_persistent_index_consistency(data_root: str | Path) -> dict[str, Any]:
    """Operator/test-only full consistency scan; never used on the ordinary response path."""
    root = Path(data_root)
    sessions_dir = root / "conversation_sessions"
    actions_dir = root / "chat_actions"
    memory_file = root / "memories.json"
    session_files = [p for p in sessions_dir.glob("conversation_session_*.json")] if sessions_dir.exists() else []
    action_files = [p for p in actions_dir.glob("*.json") if p.name != "README.md"] if actions_dir.exists() else []
    try:
        memory_rows = json.loads(memory_file.read_text(encoding="utf-8-sig")) if memory_file.is_file() else []
    except (OSError, json.JSONDecodeError):
        memory_rows = None
    status = persistent_state_index_status(root)
    counts = status["counts"]
    checks = {
        "session_count_matches": counts["sessions"] == len(session_files),
        "memory_count_matches": isinstance(memory_rows, list) and counts["memories"] == len(memory_rows),
        "action_count_matches": counts["actions"] == len(action_files),
        "canonical_json_preserved": True,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "counts": counts,
        "canonical_counts": {
            "sessions": len(session_files),
            "memories": len(memory_rows) if isinstance(memory_rows, list) else -1,
            "actions": len(action_files),
        },
        "full_scan_operator_validation_only": True,
        "authority_granted": False,
    }
