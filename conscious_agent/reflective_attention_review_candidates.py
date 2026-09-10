from __future__ import annotations
"""Durable v1123.1 reflective attention-review candidates; candidacy never selects attention."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from structural_salience_signals import StructuralSalienceSignalStore

CONTRACT_VERSION = "v1123.1"
STATES = {"active", "suppressed", "deferred", "awaiting_prerequisite", "requires_operator_review",
          "merged", "superseded", "stale", "obsolete", "retracted", "retired"}


def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def _clean(value: Any, limit=300): return " ".join(str(value or "").split())[:limit]
def _digest(*parts: Any): return hashlib.sha256("\x1f".join(_clean(x, 2000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"


def _default():
    return {"schema_version": "1", "contract_version": CONTRACT_VERSION, "candidates": [], "processed_events": [],
            "revision": 0, "updated_at": "", "authority_boundary": {
                "can_select_attention": False, "can_create_reflection": False, "can_create_intention": False,
                "can_initiate_communication": False, "can_create_notification": False,
                "can_create_proposal": False, "can_approve": False, "can_authorize": False,
                "can_execute": False, "can_browse": False, "can_contact_provider": False,
                "can_mutate_schedule": False, "can_promote": False, "can_certify": False}}


class ReflectiveAttentionReviewCandidateStore:
    def __init__(self, runtime_root=None, *, signals=None, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "reflective_attention_review_candidates.json"
        self.signals = signals or StructuralSalienceSignalStore(self.runtime_root)
        self.clock = clock or _now

    def _load(self):
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items(): state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self): return deepcopy(self._load())

    def register(self, event_id: str, *, signal_ids: list[str], cognitive_load: float = .5,
                 recovery_compatibility: float = .5, sensitivity: str = "normal",
                 operator_review_required: bool = False, prerequisite_ids: list[str] | None = None,
                 confidence: float = .5, uncertainty: float = .5, structural_digest: str = ""):
        event_id = _clean(event_id, 180)
        ids = sorted(set(_clean(x, 220) for x in signal_ids if _clean(x, 220)))
        prerequisites = sorted(set(_clean(x, 220) for x in (prerequisite_ids or []) if _clean(x, 220)))
        if not event_id or not ids: raise ValueError("event and salience-signal lineage required")
        active = {x["signal_id"]: x for x in self.signals.snapshot().get("signals", []) if x.get("state") == "active"}
        if any(signal_id not in active for signal_id in ids): raise ValueError("all salience signals must be active")
        clamp = lambda value: round(max(0.0, min(float(value), 1.0)), 4)
        source_categories = sorted(set(active[x]["salience_category"] for x in ids))
        semantic_key = _digest(*ids, *source_categories, structural_digest)
        relevance = max(active[x]["relevance"] for x in ids)
        importance = max(active[x]["importance"] for x in ids)
        urgency = max(active[x]["urgency"] for x in ids)
        salience_uncertainty = max(active[x]["uncertainty"] for x in ids)
        persistence = max(active[x]["persistence"] for x in ids)
        novelty = max(active[x]["novelty"] for x in ids)
        novelty_only = all(active[x].get("transient_novelty") for x in ids)
        false_urgency = urgency >= .8 and importance < .5 and persistence < .5
        suppressed = novelty_only or false_urgency
        overlap_state = ""
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior: return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            duplicate = next((x for x in state["candidates"] if x.get("semantic_key") == semantic_key and x.get("state") in {"active", "deferred", "requires_operator_review", "awaiting_prerequisite"}), None)
            if duplicate:
                result = {"status": "duplicate_attention_review_candidate_ignored", "candidate_id": duplicate["candidate_id"]}
            else:
                overlapping = next((x for x in state["candidates"] if set(x.get("signal_ids", [])) & set(ids) and set(x.get("signal_ids", [])) != set(ids) and x.get("state") not in {"retracted", "obsolete", "retired", "superseded"}), None)
                if overlapping: overlap_state = "semantic_overlap_detected"
                now = self.clock(); candidate_id = f"reflective-attention-review-candidate-{semantic_key[:24]}"
                initial_state = "suppressed" if suppressed else ("awaiting_prerequisite" if prerequisites else ("requires_operator_review" if operator_review_required else "active"))
                row = {"candidate_id": candidate_id, "semantic_key": semantic_key, "signal_ids": ids,
                       "source_categories": source_categories, "relevance": relevance, "importance": importance,
                       "urgency": urgency, "uncertainty": max(clamp(uncertainty), salience_uncertainty),
                       "persistence": persistence, "novelty": novelty,
                       "novelty_classification": "transient_novelty" if novelty_only else "durable_or_mixed",
                       "false_urgency_suppressed": false_urgency, "novelty_only_suppressed": novelty_only,
                       "cognitive_load": clamp(cognitive_load), "recovery_compatibility": clamp(recovery_compatibility),
                       "sensitivity": _clean(sensitivity, 32), "operator_review_required": bool(operator_review_required),
                       "prerequisite_ids": prerequisites, "confidence": clamp(confidence),
                       "structural_digest": _clean(structural_digest, 128), "semantic_overlap": bool(overlapping),
                       "overlap_candidate_id": overlapping.get("candidate_id", "") if overlapping else "",
                       "state": initial_state, "created_at": now, "updated_at": now,
                       "history": [{"change": initial_state, "occurred_at": now, "content_free": True}],
                       "selected_attention_id": "", "reflection_id": "", "intention_id": "", "initiative_id": "",
                       "message_id": "", "notification_id": "", "proposal_id": "", "approval_id": "",
                       "authorization_id": "", "action_id": ""}
                state["candidates"].append(row)
                status = "novelty_only_suppressed" if novelty_only else ("false_urgency_suppressed" if false_urgency else (overlap_state or "reflective_attention_review_candidate_registered"))
                result = {"status": status, "candidate_id": candidate_id, "state": initial_state}
            now = self.clock(); state["processed_events"].append({"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True})
            state["revision"] += 1; state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def revise(self, event_id: str, candidate_id: str, *, new_state: str, replacement_id: str = ""):
        if new_state not in STATES - {"active"}: raise ValueError("invalid state")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load(); prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior: return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            row = next((x for x in state["candidates"] if x.get("candidate_id") == candidate_id), None)
            if not row: raise ValueError("unknown attention-review candidate")
            now = self.clock(); row["state"] = new_state; row["replacement_id"] = _clean(replacement_id, 220); row["updated_at"] = now
            row["history"].append({"change": new_state, "occurred_at": now, "content_free": True})
            result = {"status": "reflective_attention_review_candidate_revised", "candidate_id": candidate_id, "state": new_state}
            state["processed_events"].append({"event_id": _clean(event_id, 180), "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True})
            state["revision"] += 1; state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self):
        state = self._load(); counts = {}
        for row in state["candidates"]: counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = ("candidate_id", "signal_ids", "source_categories", "relevance", "importance", "urgency",
                "uncertainty", "persistence", "novelty", "novelty_classification", "false_urgency_suppressed",
                "novelty_only_suppressed", "cognitive_load", "recovery_compatibility", "sensitivity",
                "operator_review_required", "prerequisite_ids", "confidence", "structural_digest",
                "semantic_overlap", "overlap_candidate_id", "state", "replacement_id", "selected_attention_id",
                "reflection_id", "intention_id", "initiative_id", "message_id", "notification_id", "proposal_id",
                "approval_id", "authorization_id", "action_id")
        return {"ok": True, "contract_version": CONTRACT_VERSION, "candidate_count": len(state["candidates"]),
                "state_counts": counts, "recent_candidates": [{key: row.get(key) for key in keys} for row in state["candidates"][-24:]],
                "authority_boundary": deepcopy(state["authority_boundary"]), "runtime_mutated": False,
                "raw_messages_exposed": False, "raw_content_exposed": False, "prompts_exposed": False,
                "provider_payloads_exposed": False, "evidence_text_exposed": False, "motivational_text_exposed": False,
                "identity_text_exposed": False, "objective_text_exposed": False, "hidden_reasoning_exposed": False,
                "private_content_exposed": False}


def build_reflective_attention_review_candidate_inspection(runtime_root=None):
    return ReflectiveAttentionReviewCandidateStore(runtime_root).inspection_summary()
