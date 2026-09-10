from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from local_brain import local_generate
from memory import load_memories, save_json, store_memory
from paths import DATA_DIR, MEMORY_FILE


MEMORY_SUMMARIES_DIR = DATA_DIR / "memory_summaries"
MEMORY_ARCHIVE_DIR = DATA_DIR / "memory_archive"
MAX_AI_CONTEXT_CHARS = 20_000
DEFAULT_KEEP_RECENT = 40
DEFAULT_MIN_MEMORIES = 80


@dataclass
class MemoryCompactionResult:
    ok: bool
    summary_id: str = ""
    compacted_count: int = 0
    kept_recent_count: int = 0
    total_before: int = 0
    total_after: int = 0
    dry_run: bool = False
    text: str = ""
    error: str = ""


def _ensure_storage() -> None:
    MEMORY_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    summaries_readme = MEMORY_SUMMARIES_DIR / "README.md"
    if not summaries_readme.exists():
        summaries_readme.write_text(
            "# Memory Summaries\n\n"
            "This folder stores memory compaction summaries. "
            "Compaction replaces older detailed memories with a safer summary memory while archiving originals.\n",
            encoding="utf-8",
        )

    archive_readme = MEMORY_ARCHIVE_DIR / "README.md"
    if not archive_readme.exists():
        archive_readme.write_text(
            "# Memory Archive\n\n"
            "This folder stores original memories that were compacted out of data/memories.json. "
            "These archives allow manual inspection or restoration if needed.\n",
            encoding="utf-8",
        )


def _new_summary_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"memsum_{timestamp}"


def _summary_path(summary_id: str) -> Path:
    return MEMORY_SUMMARIES_DIR / f"{summary_id}.json"


def _archive_path(summary_id: str) -> Path:
    return MEMORY_ARCHIVE_DIR / f"{summary_id}_archive.json"


def resolve_memory_summary_id(summary_id: str) -> str:
    token = (summary_id or "").strip()
    if token.lower() not in {"latest", "last"}:
        return token

    summaries = list_memory_summaries()
    if not summaries:
        return ""
    return summaries[0].get("id", "")


def save_memory_summary(summary: dict[str, Any]) -> None:
    _ensure_storage()
    with _summary_path(summary["id"]).open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)


def load_memory_summary(summary_id: str) -> dict[str, Any] | None:
    resolved_id = resolve_memory_summary_id(summary_id)
    if not resolved_id:
        return None

    path = _summary_path(resolved_id)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def list_memory_summaries() -> list[dict[str, Any]]:
    _ensure_storage()
    summaries: list[dict[str, Any]] = []

    for path in sorted(MEMORY_SUMMARIES_DIR.glob("memsum_*.json"), reverse=True):
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            summaries.append(data)

    return summaries


def _memory_content(memory: dict[str, Any]) -> str:
    return str(memory.get("content") or memory.get("thought") or memory.get("summary") or memory)


def _memory_line(memory: dict[str, Any]) -> str:
    created = memory.get("created_at", "?")
    mem_type = memory.get("type", "memory")
    content = _memory_content(memory).replace("\n", " ").strip()
    if len(content) > 240:
        content = content[:240] + "..."
    return f"[{created}] {mem_type}: {content}"


def _memory_type_counts(memories: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(memory.get("type", "memory")) for memory in memories)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _heuristic_summary(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return "No memories were selected for compaction."

    type_counts = _memory_type_counts(memories)
    first_created = memories[0].get("created_at", "?")
    last_created = memories[-1].get("created_at", "?")

    important = []
    for memory in memories:
        mem_type = str(memory.get("type", "memory"))
        content = _memory_content(memory).strip()
        if not content:
            continue
        if mem_type in {
            "conversation_user",
            "conversation_eidolon",
            "patch_apply_event",
            "patch_rollback_event",
            "test_workflow_event",
            "self_improvement_event",
            "maintenance_scan_event",
            "memory_compaction_summary",
        }:
            important.append(_memory_line(memory))

    if not important:
        important = [_memory_line(memory) for memory in memories[:12]]

    important = important[:30]

    lines = [
        f"Compacted {len(memories)} memories spanning {first_created} through {last_created}.",
        "",
        "Memory type counts:",
    ]
    for mem_type, count in type_counts.items():
        lines.append(f"- {mem_type}: {count}")

    lines.append("")
    lines.append("Representative important memories:")
    for item in important:
        lines.append(f"- {item}")

    lines.append("")
    lines.append(
        "This is a heuristic summary. Original detailed memories were archived before compaction. "
        "Use the archive file if exact older details are needed."
    )
    return "\n".join(lines)


def _ai_summary(memories: list[dict[str, Any]], heuristic: str) -> str:
    context_lines = [_memory_line(memory) for memory in memories]
    context = "\n".join(context_lines)
    if len(context) > MAX_AI_CONTEXT_CHARS:
        context = context[:MAX_AI_CONTEXT_CHARS] + "\n[TRUNCATED FOR LOCAL MODEL CONTEXT]"

    prompt = f"""
You are Eidolon, a local autonomous AI agent prototype.

You are summarizing older memories so the active memory file stays small while preserving useful continuity.
You are not deleting the originals; they are archived separately.

Heuristic summary:
{heuristic}

Detailed older memory lines:
{context}

Create a concise but useful long-term memory summary.
Rules:
- Preserve project direction, important decisions, bugs, fixes, user preferences, and current workflow state.
- Do not invent events.
- Mention uncertainty if details are unclear.
- Keep it under 700 words.
- Do not write it as a letter.
"""

    output = local_generate(prompt=prompt, temperature=0.25, max_tokens=900)
    if not output or output.startswith("I tried to use my local brain") or output.startswith("My local brain"):
        return ""
    return output.strip()


def memory_status_text() -> str:
    _ensure_storage()
    memories = load_memories()
    summaries = list_memory_summaries()
    archives = sorted(MEMORY_ARCHIVE_DIR.glob("memsum_*_archive.json"), reverse=True)

    size_bytes = MEMORY_FILE.stat().st_size if MEMORY_FILE.exists() else 0
    type_counts = _memory_type_counts(memories)

    lines = [
        "# Memory Status",
        "",
        f"Active memories: {len(memories)}",
        f"memories.json size: {size_bytes} bytes",
        f"Saved memory summaries: {len(summaries)}",
        f"Archived compaction files: {len(archives)}",
    ]

    if memories:
        lines.append(f"Oldest active memory: {memories[0].get('created_at', '?')}")
        lines.append(f"Newest active memory: {memories[-1].get('created_at', '?')}")

    lines.append("")
    lines.append("Active memory types:")
    if type_counts:
        for mem_type, count in type_counts.items():
            lines.append(f"- {mem_type}: {count}")
    else:
        lines.append("- [none]")

    lines.append("")
    lines.append("Suggested command:")
    lines.append("python conscious_agent/main.py --compact-memory --dry-run")

    return "\n".join(lines)


def compact_memory(
    keep_recent: int = DEFAULT_KEEP_RECENT,
    min_memories: int = DEFAULT_MIN_MEMORIES,
    use_ai: bool = True,
    dry_run: bool = False,
) -> MemoryCompactionResult:
    _ensure_storage()

    keep_recent = max(1, int(keep_recent))
    min_memories = max(1, int(min_memories))

    memories = load_memories()
    total_before = len(memories)

    if total_before < min_memories:
        return MemoryCompactionResult(
            ok=True,
            total_before=total_before,
            total_after=total_before,
            dry_run=dry_run,
            text=(
                f"Memory compaction skipped. Active memories: {total_before}. "
                f"Minimum required before compaction: {min_memories}."
            ),
        )

    if total_before <= keep_recent + 1:
        return MemoryCompactionResult(
            ok=True,
            total_before=total_before,
            total_after=total_before,
            dry_run=dry_run,
            text=(
                f"Memory compaction skipped. keep_recent={keep_recent} would leave too little to compact."
            ),
        )

    older = memories[:-keep_recent]
    recent = memories[-keep_recent:]
    summary_id = _new_summary_id()
    archive_path = _archive_path(summary_id)

    heuristic = _heuristic_summary(older)
    ai_summary = _ai_summary(older, heuristic) if use_ai else ""
    final_summary = ai_summary or heuristic

    created_at = datetime.now().isoformat(timespec="seconds")
    summary_memory = {
        "id": summary_id,
        "type": "memory_compaction_summary",
        "content": final_summary,
        "source": "memory_compactor",
        "created_at": created_at,
        "compacted_count": len(older),
        "kept_recent_count": len(recent),
        "archive_path": str(archive_path),
    }

    summary_record = {
        "id": summary_id,
        "created_at": created_at,
        "status": "dry_run" if dry_run else "completed",
        "use_ai": use_ai,
        "total_before": total_before,
        "total_after": 1 + len(recent),
        "compacted_count": len(older),
        "kept_recent_count": len(recent),
        "archive_path": str(archive_path),
        "summary_memory": summary_memory,
        "heuristic_summary": heuristic,
        "ai_summary": ai_summary,
    }

    archive_record = {
        "id": summary_id,
        "created_at": created_at,
        "reason": "memory_compaction",
        "total_before": total_before,
        "compacted_count": len(older),
        "kept_recent_count": len(recent),
        "compacted_memories": older,
    }

    if not dry_run:
        with archive_path.open("w", encoding="utf-8") as file:
            json.dump(archive_record, file, indent=2)

        save_memory_summary(summary_record)

        new_memories = [summary_memory] + recent
        save_json(MEMORY_FILE, new_memories)

        # Rebuild vector memory from compacted JSON memory if ChromaDB/Ollama are available.
        try:
            from vector_memory import rebuild_vector_memory, reset_vector_memory
            reset_vector_memory()
            rebuild_vector_memory(new_memories)
        except Exception:
            # Semantic memory is optional. JSON memory compaction still succeeded.
            pass

        # Use direct append through store_memory would expand the freshly compacted list, so only add
        # a compact event if it is useful and small.
        store_memory({
            "type": "memory_compaction_event",
            "content": f"Compacted {len(older)} older memories into summary {summary_id}. Archive: {archive_path}.",
            "source": "memory_compactor",
            "summary_id": summary_id,
            "archive_path": str(archive_path),
        })

    preview = memory_summary_text(summary_record, include_full=False)
    return MemoryCompactionResult(
        ok=True,
        summary_id=summary_id,
        compacted_count=len(older),
        kept_recent_count=len(recent),
        total_before=total_before,
        total_after=(1 + len(recent)) if dry_run else len(load_memories()),
        dry_run=dry_run,
        text=preview,
    )


def memory_summary_text(summary: dict[str, Any], include_full: bool = False) -> str:
    summary_memory = summary.get("summary_memory", {})
    lines = [
        f"# Memory Summary {summary.get('id')}",
        "",
        f"Status: {summary.get('status')}",
        f"Created: {summary.get('created_at')}",
        f"Used local AI: {summary.get('use_ai')}",
        f"Total before: {summary.get('total_before')}",
        f"Total after: {summary.get('total_after')}",
        f"Compacted: {summary.get('compacted_count')}",
        f"Kept recent: {summary.get('kept_recent_count')}",
        f"Archive: {summary.get('archive_path')}",
        "",
        "## Summary memory content",
        summary_memory.get("content", "[no summary content]"),
    ]

    if include_full:
        lines.extend([
            "",
            "## Heuristic summary",
            summary.get("heuristic_summary", "[none]"),
            "",
            "## Local AI summary",
            summary.get("ai_summary", "[none]"),
        ])

    return "\n".join(lines)


def print_memory_status() -> None:
    print(memory_status_text())


def print_compact_memory(
    keep_recent: int = DEFAULT_KEEP_RECENT,
    min_memories: int = DEFAULT_MIN_MEMORIES,
    use_ai: bool = True,
    dry_run: bool = False,
) -> None:
    result = compact_memory(
        keep_recent=keep_recent,
        min_memories=min_memories,
        use_ai=use_ai,
        dry_run=dry_run,
    )

    if not result.ok:
        print("Memory compaction failed.")
        print(result.error)
        return

    print(result.text)
    print()
    if result.dry_run:
        print("Dry run only. No memories were changed and no archive was written.")
        print("To compact for real, run the same command without --dry-run.")
    elif result.summary_id:
        print(f"Memory compaction completed: {result.summary_id}")
        print("Use: python conscious_agent/main.py --show-memory-summary latest")
    else:
        print("No compaction was needed.")


def print_memory_summaries() -> None:
    summaries = list_memory_summaries()
    if not summaries:
        print("No memory summaries found.")
        return

    for summary in summaries:
        print(
            f"{summary.get('id')} | "
            f"created={summary.get('created_at')} | "
            f"status={summary.get('status')} | "
            f"compacted={summary.get('compacted_count')} | "
            f"kept_recent={summary.get('kept_recent_count')}"
        )


def print_memory_summary(summary_id: str, include_full: bool = False) -> None:
    summary = load_memory_summary(summary_id)
    if not summary:
        print(f"Memory summary not found: {summary_id}")
        return
    print(memory_summary_text(summary, include_full=include_full))
