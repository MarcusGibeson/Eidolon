from __future__ import annotations
"""Bounded, provider-neutral intention aging and reconsideration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Callable
from bounded_intention_formation import BoundedIntentionStore
from json_storage import write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1107.6"
_TERMINAL = {"expired", "retired", "replaced"}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def _clean(value: Any, limit: int = 300) -> str:
    return " ".join(str(value or "").split())[:limit]

def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(x, 2000) for x in parts).encode()).hexdigest()

def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

class IntentionLifecycle:
    def __init__(self, runtime_root=None, *, clock: Callable[[], str] | None = None):
        self.intentions = BoundedIntentionStore(runtime_root, clock=clock)
        self.path = self.intentions.path
        self.clock = clock or _now

    def reconsider(self, event_id: str, *, intention_id: str, outcome: str, reason_code: str = "", expires_at: str = ""):
        event_id = _clean(event_id, 180); intention_id = _clean(intention_id, 180)
        outcome = _clean(outcome, 40).lower(); reason_code = _clean(reason_code, 100)
        allowed = {"reaffirm", "suspend", "resume", "retire", "expire"}
        if not event_id or not intention_id or outcome not in allowed:
            raise ValueError("event_id, intention_id, and valid outcome required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self.intentions._load()
            prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            row = next((x for x in state["intentions"] if x.get("intention_id") == intention_id), None)
            if not row:
                result = {"status": "intention_not_found", "intention_id": intention_id}
            elif row.get("lifecycle") in _TERMINAL and outcome not in {"retire", "expire"}:
                result = {"status": "terminal_intention_unchanged", "intention_id": intention_id, "lifecycle": row.get("lifecycle")}
            else:
                now = self.clock()
                lifecycle = {"reaffirm": "active", "resume": "active", "suspend": "suspended", "retire": "retired", "expire": "expired"}[outcome]
                row["lifecycle"] = lifecycle; row["active"] = lifecycle == "active"; row["updated_at"] = now
                if expires_at: row["expires_at"] = _clean(expires_at, 80)
                row.setdefault("lifecycle_history", []).append({"event_digest": _digest(event_id), "outcome": outcome, "reason_code": reason_code, "occurred_at": now, "content_free": True})
                row["lifecycle_history"] = row["lifecycle_history"][-64:]
                result = {"status": "intention_reconsidered", "intention_id": intention_id, "lifecycle": lifecycle, "active": row["active"]}
            now = self.clock(); state["processed_events"] = (state["processed_events"] + [{"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True}])[-1024:]
            state["revision"] += 1; state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def apply_due_expiry(self, event_id: str):
        event_id = _clean(event_id, 180)
        if not event_id: raise ValueError("event_id required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self.intentions._load()
            prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior: return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            now_text = self.clock(); now = _parse(now_text); changed = []
            for row in state["intentions"]:
                due = _parse(row.get("expires_at", ""))
                if row.get("active") is True and now and due and due <= now:
                    row["active"] = False; row["lifecycle"] = "expired"; row["updated_at"] = now_text
                    row.setdefault("lifecycle_history", []).append({"event_digest": _digest(event_id), "outcome": "expire", "reason_code": "due_expiry", "occurred_at": now_text, "content_free": True})
                    changed.append(row["intention_id"])
            result = {"status": "expiry_applied" if changed else "no_expiry_due", "expired_count": len(changed), "intention_ids": changed}
            state["processed_events"] = (state["processed_events"] + [{"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now_text, "result": deepcopy(result), "content_free": True}])[-1024:]
            state["revision"] += 1; state["updated_at"] = now_text
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self):
        state = self.intentions.snapshot(); rows = state["intentions"]
        counts = {name: sum(x.get("lifecycle") == name for x in rows) for name in ("active", "suspended", "expired", "retired", "replaced")}
        return {"ok": True, "contract_version": CONTRACT_VERSION, "revision": state["revision"], "lifecycle_counts": counts, "reconsideration_record_count": sum(len(x.get("lifecycle_history", [])) for x in rows), "recent_lifecycle": [{k: x.get(k) for k in ("intention_id", "subject_digest", "kind", "lifecycle", "active", "expires_at", "updated_at")} for x in rows[-24:]], "provider_contacted": False, "external_action_requested": False, "action_authority_changed": False, "hidden_reasoning_exposed": False, "runtime_mutated": False}

def build_intention_lifecycle_inspection(runtime_root=None):
    return IntentionLifecycle(runtime_root).inspection_summary()
