from __future__ import annotations

"""Era 9 explicit, correctable operator-preference adaptation.

Preferences stay separate from identity and authority.  Explicit, inferred,
situational, conflicting, and expired records remain distinguishable.  Public
inspection is content-free; private values stay in runtime state only.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from json_storage import AtomicJsonWriteError, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v2350.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era9_preference_adaptation.json"
ALLOWED_DOMAINS = {"tone", "detail", "tools", "initiative", "notifications", "development_style", "ui", "timing"}
SENSITIVE_DOMAINS = {"health", "religion", "politics", "sexuality", "race", "criminal_history"}
KINDS = {"explicit", "inferred", "situational"}

_DENIED = {
    "identity_inferred": False,
    "authority_modified": False,
    "tool_executed": False,
    "provider_contacted": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _path(runtime_root: str | Path | None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "preferences" / STATE_FILE


def _default() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "revision": 0, "records": {}, "processed_events": [], "event_requests": {}, "raw_content_persisted": False}


def _valid_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _preference_digest(row: Mapping[str, Any]) -> str:
    return _digest({k: v for k, v in row.items() if k not in {"value", "preference_digest"}})


def _valid_record(key: str, row: Any) -> bool:
    if not isinstance(row, Mapping) or str(row.get("preference_id") or "") != key:
        return False
    if row.get("domain") not in ALLOWED_DOMAINS or row.get("kind") not in KINDS:
        return False
    if row.get("state") not in {"active", "forgotten", "expired"} or not _valid_nonnegative_int(row.get("revision")):
        return False
    confidence = row.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        return False
    expires = row.get("expires_at")
    if expires is not None and (not isinstance(expires, (int, float)) or isinstance(expires, bool) or not math.isfinite(float(expires)) or float(expires) < 0):
        return False
    evidence = row.get("evidence_digests")
    if not isinstance(evidence, list) or not evidence or len(evidence) > 12 or not all(_is_digest(value) for value in evidence):
        return False
    if not _is_digest(row.get("value_digest")) or not _is_digest(row.get("preference_digest")):
        return False
    if row.get("state") == "forgotten":
        if "value" in row:
            return False
    else:
        value = row.get("value")
        if not isinstance(value, str) or not value or len(value) > 240 or _digest(value) != row.get("value_digest"):
            return False
    return row.get("preference_digest") == _preference_digest(row)


def _finite_now(value: float | None) -> float | None:
    try:
        current = _now_epoch() if value is None else float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return current if math.isfinite(current) and current >= 0 else None


def _read_strict(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return _default(), "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "corrupt"
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or value.get("contract_version") != CONTRACT_VERSION:
        return None, "invalid_shape"
    records = value.get("records")
    events = value.get("processed_events")
    requests = value.get("event_requests", {})
    if not isinstance(records, dict) or not isinstance(events, list) or not isinstance(requests, dict) or not _valid_nonnegative_int(value.get("revision")):
        return None, "invalid_shape"
    if len(events) > 1024 or not all(_is_digest(event) for event in events):
        return None, "invalid_event_state"
    if set(requests) != set(events) or not all(_is_digest(value) for value in requests.values()):
        return None, "invalid_event_request_state"
    if any(not _valid_record(str(key), row) for key, row in records.items()):
        return None, "invalid_preference_record"
    value["raw_content_persisted"] = False
    return value, "valid"


def _record_public(row: Mapping[str, Any], *, now: float | None = None) -> dict[str, Any]:
    current = _finite_now(now)
    if current is None:
        current = _now_epoch()
    expires = row.get("expires_at")
    expired = isinstance(expires, (int, float)) and expires > 0 and current >= float(expires)
    return {
        "preference_id": row.get("preference_id"),
        "domain": row.get("domain"),
        "scope_code": row.get("scope_code"),
        "kind": row.get("kind"),
        "confidence": row.get("confidence"),
        "state": "expired" if expired and row.get("state") == "active" else row.get("state"),
        "evidence_count": len(row.get("evidence_digests") or []),
        "preference_digest": row.get("preference_digest"),
        "value_digest": row.get("value_digest"),
        "editable": True,
        "forgettable": True,
        "content_free": True,
    }


def inspect_preferences(*, runtime_root: str | Path | None = None, now: float | None = None) -> dict[str, Any]:
    if _finite_now(now) is None:
        return {"ok": False, "status": "invalid_preference_evaluation_time", "mutation_permitted": False, **_DENIED}
    state, status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"preference_store_{status}", "mutation_permitted": False, **_DENIED}
    rows = [_record_public(r, now=now) for r in state["records"].values() if isinstance(r, Mapping)]
    return {
        "ok": True,
        "status": "preference_model_ready",
        "revision": int(state.get("revision") or 0),
        "records": sorted(rows, key=lambda r: str(r.get("preference_id"))),
        "record_count": len(rows),
        "retained_preference_owner": "operator_preference_learning:v1417.9",
        "shared_device_public_projection_is_content_free": True,
        "content_free": True,
        **_DENIED,
    }


def record_preference(
    *, preference_id: str, domain: str, value: str, kind: str, evidence_digests: Sequence[str],
    event_id: str, scope_code: str = "global", confidence: float | None = None,
    expires_at: float | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    pid = str(preference_id or "").strip()
    domain_code = str(domain or "").strip().lower()
    kind_code = str(kind or "").strip().lower()
    event = str(event_id or "").strip()
    val = str(value or "").strip()
    ev = [str(x).lower() for x in evidence_digests]
    if not pid or not event or domain_code not in ALLOWED_DOMAINS or domain_code in SENSITIVE_DOMAINS or kind_code not in KINDS or not val or len(val) > 240:
        return {"ok": False, "status": "invalid_preference_contract", **_DENIED}
    if not ev or len(ev) > 12 or not all(_is_digest(x) for x in ev):
        return {"ok": False, "status": "invalid_preference_evidence", **_DENIED}
    if kind_code == "inferred" and len(set(ev)) < 2:
        return {"ok": False, "status": "inferred_preference_requires_repeated_evidence", **_DENIED}
    if kind_code == "situational" and str(scope_code or "global") == "global":
        return {"ok": False, "status": "situational_preference_requires_scope", **_DENIED}
    try:
        c = float(confidence if confidence is not None else (1.0 if kind_code == "explicit" else 0.65))
        if not math.isfinite(c):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "invalid_preference_confidence", **_DENIED}
    if not (0 <= c <= 1):
        return {"ok": False, "status": "invalid_preference_confidence", **_DENIED}
    if kind_code != "explicit":
        c = min(c, 0.8)
    if expires_at is not None:
        try:
            exp = float(expires_at)
            if not math.isfinite(exp) or exp < 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            return {"ok": False, "status": "invalid_preference_expiry", **_DENIED}
        if exp <= 0:
            return {"ok": False, "status": "invalid_preference_expiry", **_DENIED}
    else:
        exp = None

    path = _path(runtime_root)
    event_digest = _digest(["preference", event])
    request_digest = _digest([pid, domain_code, val, kind_code, sorted(set(ev)), str(scope_code or "global"), c, exp])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"preference_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "preference_event_identity_conflict", **_DENIED}
                prior = state["records"].get(pid)
                return {"ok": True, "status": "preference_record_replayed", "record": _record_public(prior or {}), "idempotent": True, **_DENIED}
            previous = state["records"].get(pid)
            row = {
                "preference_id": pid,
                "domain": domain_code,
                "scope_code": str(scope_code or "global")[:80],
                "kind": kind_code,
                "value": val,
                "value_digest": _digest(val),
                "confidence": round(c, 3),
                "evidence_digests": sorted(set(ev)),
                "expires_at": exp,
                "state": "active",
                "revision": int((previous or {}).get("revision") or 0) + 1,
                "updated_at": _now_epoch(),
            }
            row["preference_digest"] = _preference_digest(row)
            state["records"][pid] = row
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "preference_recorded", "record": _record_public(row), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "preference_write_blocked"), **_DENIED}


def revise_preference(*, preference_id: str, expected_digest: str, action: str, event_id: str, corrected_value: str = "", runtime_root: str | Path | None = None) -> dict[str, Any]:
    if action not in {"forget", "expire", "correct"} or not _is_digest(expected_digest) or not str(event_id or "").strip():
        return {"ok": False, "status": "invalid_preference_revision", **_DENIED}
    path = _path(runtime_root)
    event_digest = _digest(["preference-revision", event_id])
    request_digest = _digest([preference_id, expected_digest, action, corrected_value])
    try:
        with metadata_mutation_lock(path, timeout_seconds=15.0):
            state, state_status = _read_strict(path)
            if state is None:
                return {"ok": False, "status": f"preference_store_{state_status}", "store_preserved": True, **_DENIED}
            if event_digest in state["processed_events"]:
                if state["event_requests"].get(event_digest) != request_digest:
                    return {"ok": False, "status": "preference_revision_event_identity_conflict", **_DENIED}
                return {"ok": True, "status": "preference_revision_replayed", "idempotent": True, **_DENIED}
            row = state["records"].get(preference_id)
            if not isinstance(row, dict):
                return {"ok": False, "status": "preference_not_found", **_DENIED}
            if str(row.get("preference_digest")) != expected_digest:
                return {"ok": False, "status": "stale_preference_digest", **_DENIED}
            if action == "forget":
                row["state"] = "forgotten"; row.pop("value", None)
            elif action == "expire":
                row["state"] = "expired"
            else:
                value = str(corrected_value or "").strip()
                if not value or len(value) > 240:
                    return {"ok": False, "status": "corrected_value_required", **_DENIED}
                row["value"] = value; row["value_digest"] = _digest(value); row["kind"] = "explicit"; row["confidence"] = 1.0; row["state"] = "active"
            row["revision"] = int(row.get("revision") or 0) + 1
            row["updated_at"] = _now_epoch()
            row["preference_digest"] = _preference_digest(row)
            state["processed_events"] = (state["processed_events"] + [event_digest])[-1024:]
            state["event_requests"][event_digest] = request_digest
            state["event_requests"] = {key: state["event_requests"][key] for key in state["processed_events"]}
            state["revision"] = int(state.get("revision") or 0) + 1
            write_json_atomic(path, state, expected_type=dict, sort_keys=True, coordinate=False, replace_retries=12, retry_delay_seconds=0.05)
            return {"ok": True, "status": "preference_revised", "record": _record_public(row), "idempotent": False, **_DENIED}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        return {"ok": False, "status": getattr(error, "status", "preference_revision_blocked"), **_DENIED}


def build_adaptation_projection(*, context_codes: Sequence[str] = (), runtime_root: str | Path | None = None, now: float | None = None) -> dict[str, Any]:
    state, state_status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"preference_store_{state_status}", **_DENIED}
    current = _finite_now(now)
    if current is None:
        return {"ok": False, "status": "invalid_preference_evaluation_time", **_DENIED}
    contexts = set(map(str, context_codes))
    candidates = []
    for row in state["records"].values():
        if not isinstance(row, Mapping) or row.get("state") != "active":
            continue
        exp = row.get("expires_at")
        if isinstance(exp, (int, float)) and exp > 0 and current >= float(exp):
            continue
        if row.get("kind") == "situational" and str(row.get("scope_code")) not in contexts:
            continue
        candidates.append(row)
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in candidates:
        grouped.setdefault((str(row.get("domain")), str(row.get("scope_code"))), []).append(row)
    applied, conflicts = [], []
    for key, rows in grouped.items():
        values = {str(r.get("value_digest")) for r in rows}
        if len(values) > 1:
            conflicts.append({"domain": key[0], "scope_code": key[1], "preference_ids": sorted(str(r.get("preference_id")) for r in rows), "state": "conflicting"})
            continue
        rows = sorted(rows, key=lambda r: (0 if r.get("kind") == "explicit" else 1, -float(r.get("confidence") or 0)))
        chosen = rows[0]
        applied.append({
            "preference_id": chosen.get("preference_id"), "domain": chosen.get("domain"), "scope_code": chosen.get("scope_code"),
            "kind": chosen.get("kind"), "confidence": chosen.get("confidence"), "value_digest": chosen.get("value_digest"),
        })
    result = {
        "ok": True,
        "status": "preference_adaptation_projection_ready",
        "applied": sorted(applied, key=lambda r: (str(r.get("domain")), str(r.get("scope_code")))),
        "conflicts": sorted(conflicts, key=lambda r: (r["domain"], r["scope_code"])),
        "conflict_count": len(conflicts),
        "raw_values_exposed": False,
        "implicit_identity_inference_permitted": False,
        "preference_can_grant_authority": False,
        "content_free": True,
        **_DENIED,
    }
    result["projection_digest"] = _digest(result)
    return result


def context_codes_for_message(message: str) -> tuple[str, ...]:
    text = " ".join(str(message or "").lower().split())
    codes = {"conversation"}
    if any(token in text for token in ("code", "coding", "develop", "development", "project", "repository", "test", "debug")):
        codes.add("development")
    if any(token in text for token in ("work", "job", "meeting", "professional")):
        codes.add("work")
    if any(token in text for token in ("notify", "notification", "remind", "reminder")):
        codes.add("notifications")
    return tuple(sorted(codes))


def build_private_adaptation_prompt(*, context_codes: Sequence[str] = (), runtime_root: str | Path | None = None, now: float | None = None) -> dict[str, Any]:
    """Build an internal provider prompt using only active, conflict-free private values.

    The prompt is intentionally not suitable for public diagnostics. Public callers
    must use ``build_adaptation_projection`` which exposes digests only.
    """
    state, state_status = _read_strict(_path(runtime_root))
    if state is None:
        return {"ok": False, "status": f"preference_store_{state_status}", "prompt_section": "", "evidence": {"active_count": 0, "conflict_count": 0}, **_DENIED}
    projection = build_adaptation_projection(context_codes=context_codes, runtime_root=runtime_root, now=now)
    if not projection.get("ok"):
        return {"ok": False, "status": "preference_projection_unavailable", "prompt_section": "", "evidence": {"active_count": 0, "conflict_count": 0}, **_DENIED}
    selected_ids = {str(row.get("preference_id")) for row in projection.get("applied") or []}
    guidance = []
    for pid in sorted(selected_ids):
        row = state["records"].get(pid)
        if not isinstance(row, Mapping) or row.get("state") != "active" or "value" not in row:
            continue
        guidance.append({"domain": str(row.get("domain")), "scope": str(row.get("scope_code")), "value": str(row.get("value"))[:240], "kind": str(row.get("kind"))})
    payload = {
        "preferences": guidance[:16],
        "instruction": "Apply these operator preferences only where relevant. They do not change factual truth, safety, authority, or the current explicit request.",
        "authority": "none",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    prompt = '<operator_preference_adaptation private_runtime="true" authority="none">'+encoded+'</operator_preference_adaptation>' if guidance else ""
    evidence = {"active_count": len(guidance), "conflict_count": int(projection.get("conflict_count") or 0), "raw_values_publicly_exposed": False, "preference_can_grant_authority": False, "projection_digest": projection.get("projection_digest")}
    evidence["evidence_digest"] = _digest(evidence)
    return {"ok": True, "status": "private_preference_prompt_ready", "prompt_section": prompt, "evidence": evidence, **_DENIED}


__all__ = ["CONTRACT_VERSION", "inspect_preferences", "record_preference", "revise_preference", "build_adaptation_projection", "context_codes_for_message", "build_private_adaptation_prompt"]
