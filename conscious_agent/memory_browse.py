from __future__ import annotations

"""Read-only, offline-safe, privacy-bounded curated-memory browse/search."""

from datetime import datetime
from typing import Any, Iterable
from relationship_memory_curation import list_relationship_memory_curation_records

MAX_PAGE_SIZE = 100


def browse_relationship_memories(*, query: str = "", filters: dict[str, Any] | None = None, page: int = 1, page_size: int = 25, records: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    filters = dict(filters or {})
    rows = list(records) if records is not None else list_relationship_memory_curation_records(include_retracted=bool(filters.get("include_retracted", True)))
    safe_rows = []
    needle = " ".join(str(query or "").casefold().split())
    for row in rows:
        if not isinstance(row, dict) or row.get("state") == "deleted":
            continue
        public = {k: row.get(k) for k in ("record_key","id","type","category","label","content","importance","state","created_at","updated_at","operator_curated","temporal_state","retention_confirmed","provenance","important_moment_provenance")}
        if any(token in public for token in ("receipt", "provider_payload", "credential", "vector")):
            continue
        if needle and needle not in " ".join(str(public.get(k) or "") for k in ("content","label","category","type")).casefold():
            continue
        mapping = {
            "memory_type": "category", "source": "operator_curated", "status": "state",
            "relationship_relevance": "category", "temporal_state": "temporal_state",
            "retention_state": "retention_confirmed", "retraction_state": "state",
        }
        rejected = False
        for name, field in mapping.items():
            expected = filters.get(name)
            if expected in (None, "", "all"):
                continue
            actual = public.get(field)
            if name == "retraction_state":
                actual = "retracted" if actual == "retracted" else "not_retracted"
            if str(actual).casefold() != str(expected).casefold():
                rejected = True; break
        if rejected:
            continue
        provenance_state = filters.get("provenance_state")
        if provenance_state not in (None, "", "all") and str((public.get("provenance") or {}).get("origin") or "legacy_unknown") != str(provenance_state):
            continue
        created_from, created_to = filters.get("created_from"), filters.get("created_to")
        created = str(public.get("created_at") or "")
        if created_from and created < str(created_from): continue
        if created_to and created > str(created_to): continue
        safe_rows.append(public)
    size = max(1, min(int(page_size or 25), MAX_PAGE_SIZE)); current = max(1, int(page or 1))
    total = len(safe_rows); start = (current - 1) * size
    return {"ok": True, "read_only": True, "provider_invoked": False, "offline_available": True, "page": current, "page_size": size, "total": total, "has_more": start + size < total, "records": safe_rows[start:start+size]}
