from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

AUTHORITY_DENIED = {
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


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def sealed(kind: str, payload: Mapping[str, Any], *, version: str, status: str = "ready", content_free: bool = True) -> dict[str, Any]:
    row = {
        "schema": "eidolon.bounded-capability-evidence.v1",
        "kind": str(kind),
        "version": str(version),
        "status": str(status),
        "content_free": bool(content_free),
        "payload": dict(payload),
        **AUTHORITY_DENIED,
    }
    row["evidence_digest"] = digest(row)
    return row


def valid_seal(row: Mapping[str, Any]) -> bool:
    body=dict(row)
    supplied=str(body.pop("evidence_digest", ""))
    return len(supplied)==64 and supplied==digest(body)


def bounded_float(value: Any, default: float = 0.0, *, lo: float = 0.0, hi: float = 1.0) -> float:
    try: x=float(value)
    except Exception: x=default
    return max(lo,min(hi,x))


def bounded_int(value: Any, default: int = 0, *, lo: int = 0, hi: int = 1_000_000) -> int:
    try: x=int(value)
    except Exception: x=default
    return max(lo,min(hi,x))


def utc_ts(value: str | None = None) -> str:
    if value:
        try:
            dt=datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
        except Exception: pass
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")


def structural_summary(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"count": len(items), "digest": digest([dict(x) for x in items])}
