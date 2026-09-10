from __future__ import annotations
"""Content-free v1123.0 structural salience signals; signals never select attention."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1123.0"
SCHEMA_VERSION = "1"
SALience_CATEGORIES = {
    "objective_progress", "motivational_continuity", "prospective_obligation",
    "inquiry_uncertainty", "epistemic_inconsistency", "self_model_integrity",
    "scheduled_cognitive_work", "recovery_constraint", "operator_review",
    "conversation_relevance",
}
SOURCE_TYPES = {
    "objective", "milestone", "motivational_drive_candidate", "prospective_obligation",
    "active_inquiry", "belief", "knowledge", "identity_claim", "self_model_claim",
    "scheduled_cognitive_work", "recovery_review", "cognitive_load", "operator_review_requirement",
    "conversation_relevance_marker",
}
STATES = {"active", "corrected", "retracted", "merged", "superseded", "stale", "obsolete", "retired"}
SENSITIVITY = {"normal", "sensitive", "restricted"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 300) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(x, 2000) for x in parts).encode()).hexdigest()


def _root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "signals": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {
            "can_select_attention": False, "can_create_reflection": False,
            "can_create_intention": False, "can_initiate_communication": False,
            "can_create_notification": False, "can_create_proposal": False,
            "can_approve": False, "can_authorize": False, "can_execute": False,
            "can_browse": False, "can_contact_provider": False,
            "can_mutate_schedule": False, "can_promote": False, "can_certify": False,
        },
    }


class StructuralSalienceSignalStore:
    def __init__(self, runtime_root=None, *, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "structural_salience_signals.json"
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(self, event_id: str, *, salience_category: str, source_type: str, source_id: str,
                 related_source_type: str = "", related_source_id: str = "", relevance: float = .5,
                 importance: float = .5, urgency: float = .5, uncertainty: float = .5,
                 temporal_pressure: float = .5, persistence: float = .5, novelty: float = .5,
                 sensitivity: str = "normal", interruptibility: float = .5,
                 recovery_compatibility: float = .5, confidence: float = .5,
                 operator_review_required: bool = False, structural_digest: str = "") -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        salience_category = _clean(salience_category, 80)
        source_type = _clean(source_type, 80)
        source_id = _clean(source_id, 220)
        related_source_type = _clean(related_source_type, 80)
        related_source_id = _clean(related_source_id, 220)
        sensitivity = _clean(sensitivity, 32)
        if not event_id or salience_category not in SALience_CATEGORIES or source_type not in SOURCE_TYPES or not source_id:
            raise ValueError("valid event, salience category, and source lineage required")
        if related_source_type and related_source_type not in SOURCE_TYPES:
            raise ValueError("invalid related source type")
        if sensitivity not in SENSITIVITY:
            raise ValueError("invalid sensitivity")
        clamp = lambda value: round(max(0.0, min(float(value), 1.0)), 4)
        semantic_key = _digest(salience_category, source_type, source_id, related_source_type,
                               related_source_id, structural_digest)
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            duplicate = next((x for x in state["signals"] if x.get("semantic_key") == semantic_key and x.get("state") == "active"), None)
            if duplicate:
                result = {"status": "duplicate_salience_signal_ignored", "signal_id": duplicate["signal_id"]}
            else:
                now = self.clock()
                signal_id = f"structural-salience-signal-{semantic_key[:24]}"
                durable_salience = clamp(persistence) >= .5 and not (clamp(novelty) >= .8 and clamp(importance) < .5 and clamp(relevance) < .5)
                transient_novelty = not durable_salience and clamp(novelty) >= .5
                row = {
                    "signal_id": signal_id, "semantic_key": semantic_key,
                    "salience_category": salience_category, "source_type": source_type, "source_id": source_id,
                    "related_source_type": related_source_type, "related_source_id": related_source_id,
                    "relevance": clamp(relevance), "importance": clamp(importance), "urgency": clamp(urgency),
                    "uncertainty": clamp(uncertainty), "temporal_pressure": clamp(temporal_pressure),
                    "persistence": clamp(persistence), "novelty": clamp(novelty),
                    "durable_salience": durable_salience, "transient_novelty": transient_novelty,
                    "sensitivity": sensitivity, "interruptibility": clamp(interruptibility),
                    "recovery_compatibility": clamp(recovery_compatibility), "confidence": clamp(confidence),
                    "operator_review_required": bool(operator_review_required),
                    "structural_digest": _clean(structural_digest, 128), "state": "active",
                    "created_at": now, "updated_at": now,
                    "history": [{"change": "registered", "occurred_at": now, "content_free": True}],
                    "attention_review_candidate_id": "", "selected_attention_id": "", "reflection_id": "",
                    "intention_id": "", "initiative_id": "", "message_id": "", "notification_id": "",
                    "proposal_id": "", "approval_id": "", "authorization_id": "", "action_id": "",
                }
                state["signals"].append(row)
                result = {"status": "structural_salience_signal_registered", "signal_id": signal_id}
            now = self.clock()
            state["processed_events"].append({"event_id": event_id, "event_digest": _digest(event_id),
                                              "occurred_at": now, "result": deepcopy(result), "content_free": True})
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def revise(self, event_id: str, signal_id: str, *, new_state: str, replacement_id: str = "") -> dict[str, Any]:
        if new_state not in STATES - {"active"}:
            raise ValueError("invalid state")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((x for x in state["processed_events"] if x.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            row = next((x for x in state["signals"] if x.get("signal_id") == signal_id), None)
            if not row:
                raise ValueError("unknown salience signal")
            now = self.clock()
            row["state"] = new_state
            row["replacement_id"] = _clean(replacement_id, 220)
            row["updated_at"] = now
            row["history"].append({"change": new_state, "occurred_at": now, "content_free": True})
            result = {"status": "structural_salience_signal_revised", "signal_id": signal_id, "state": new_state}
            state["processed_events"].append({"event_id": _clean(event_id, 180), "event_digest": _digest(event_id),
                                              "occurred_at": now, "result": deepcopy(result), "content_free": True})
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["signals"]:
            counts[row.get("state", "unknown")] = counts.get(row.get("state", "unknown"), 0) + 1
        keys = ("signal_id", "salience_category", "source_type", "source_id", "related_source_type",
                "related_source_id", "relevance", "importance", "urgency", "uncertainty",
                "temporal_pressure", "persistence", "novelty", "durable_salience", "transient_novelty",
                "sensitivity", "interruptibility", "recovery_compatibility", "confidence",
                "operator_review_required", "structural_digest", "state", "replacement_id",
                "attention_review_candidate_id", "selected_attention_id", "reflection_id", "intention_id",
                "initiative_id", "message_id", "notification_id", "proposal_id", "approval_id",
                "authorization_id", "action_id")
        return {
            "ok": True, "contract_version": CONTRACT_VERSION, "signal_count": len(state["signals"]),
            "state_counts": counts,
            "durable_salience_count": sum(bool(x.get("durable_salience")) for x in state["signals"]),
            "transient_novelty_count": sum(bool(x.get("transient_novelty")) for x in state["signals"]),
            "recent_signals": [{key: row.get(key) for key in keys} for row in state["signals"][-24:]],
            "authority_boundary": deepcopy(state["authority_boundary"]), "runtime_mutated": False,
            "raw_messages_exposed": False, "raw_content_exposed": False, "prompts_exposed": False,
            "provider_payloads_exposed": False, "evidence_text_exposed": False,
            "motivational_text_exposed": False, "identity_text_exposed": False,
            "objective_text_exposed": False, "hidden_reasoning_exposed": False,
            "private_content_exposed": False,
        }


def build_structural_salience_signal_inspection(runtime_root=None) -> dict[str, Any]:
    return StructuralSalienceSignalStore(runtime_root).inspection_summary()
