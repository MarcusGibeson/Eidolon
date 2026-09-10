from __future__ import annotations
"""Deterministic, non-authorizing conflict and replacement handling for intentions."""
from copy import deepcopy
import hashlib
from typing import Any
from intention_reconsideration_decay import IntentionLifecycle, _clean, _now
from json_storage import write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1107.7"
def _digest(*parts: Any) -> str: return hashlib.sha256("\x1f".join(_clean(x, 2000) for x in parts).encode()).hexdigest()

class IntentionConflictResolver:
    def __init__(self, runtime_root=None, *, clock=None):
        self.lifecycle = IntentionLifecycle(runtime_root, clock=clock); self.intentions = self.lifecycle.intentions; self.path = self.intentions.path; self.clock = clock or _now

    def resolve(self, event_id: str, *, intention_ids: list[str]):
        event_id = _clean(event_id, 180); ids = sorted({_clean(x, 180) for x in intention_ids if _clean(x, 180)})
        if not event_id or len(ids) < 2: raise ValueError("event_id and at least two intention_ids required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self.intentions._load(); prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior: return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            rows = [x for x in state["intentions"] if x.get("intention_id") in ids and x.get("active") is True]
            if len(rows) < 2:
                result = {"status": "conflict_not_resolved", "reason": "insufficient_active_intentions", "winner_id": "", "replaced_ids": []}
            else:
                rows.sort(key=lambda x: (-float(x.get("priority", 0)), -float(x.get("confidence", 0)), str(x.get("created_at", "")), str(x.get("intention_id", ""))))
                winner = rows[0]; losers = rows[1:]; now = self.clock()
                for row in losers:
                    row["active"] = False; row["lifecycle"] = "replaced"; row["updated_at"] = now; row["replaced_by_intention_id"] = winner["intention_id"]
                    row.setdefault("lifecycle_history", []).append({"event_digest": _digest(event_id), "outcome": "replace", "reason_code": "deterministic_conflict_resolution", "occurred_at": now, "content_free": True})
                winner.setdefault("conflict_history", []).append({"event_digest": _digest(event_id), "replaced_count": len(losers), "occurred_at": now, "content_free": True})
                result = {"status": "conflict_resolved", "winner_id": winner["intention_id"], "replaced_ids": [x["intention_id"] for x in losers], "proposal_created": False, "authority_granted": False}
            now = self.clock(); state["processed_events"] = (state["processed_events"] + [{"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True}])[-1024:]
            state["revision"] += 1; state["updated_at"] = now; write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self):
        state = self.intentions.snapshot(); rows = state["intentions"]
        return {"ok": True, "contract_version": CONTRACT_VERSION, "conflict_receipt_count": sum(len(x.get("conflict_history", [])) for x in rows), "replaced_intention_count": sum(x.get("lifecycle") == "replaced" for x in rows), "recent_replacements": [{"intention_id": x.get("intention_id"), "replaced_by_intention_id": x.get("replaced_by_intention_id", ""), "subject_digest": x.get("subject_digest"), "lifecycle": x.get("lifecycle")} for x in rows if x.get("lifecycle") == "replaced"][-24:], "deterministic": True, "provider_contacted": False, "proposal_created": False, "action_authority_changed": False, "external_action_executed": False, "hidden_reasoning_exposed": False, "runtime_mutated": False}

def build_intention_conflict_inspection(runtime_root=None): return IntentionConflictResolver(runtime_root).inspection_summary()
