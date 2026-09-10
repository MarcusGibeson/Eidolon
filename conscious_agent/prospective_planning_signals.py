from __future__ import annotations
"""v1134.0 durable content-free prospective-planning eligibility signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1134.0"
SCHEMA_VERSION = "1"
SOURCE_CATEGORIES = {
    "accepted_goal_outcome", "goal_revision_outcome", "world_model_outcome",
    "inquiry_outcome", "perception_outcome", "obligation", "constraint",
    "operator_requirement",
}
PURPOSE_CATEGORIES = {
    "capability_path", "reliability_path", "knowledge_path", "project_path",
    "relationship_path", "maintenance_path", "risk_mitigation",
    "deliberate_no_action_review",
}
STATES = {
    "active", "suppressed", "deferred", "awaiting_prerequisite",
    "requires_operator_review", "superseded", "retracted", "stale", "retired",
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]

def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(x, 3000) for x in parts).encode()).hexdigest()

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
            "can_activate_goal": False,
            "can_create_plan": False,
            "can_create_initiative": False,
            "can_browse": False,
            "can_contact_provider": False,
            "can_execute": False,
            "can_modify_files": False,
            "can_send_message": False,
            "can_create_notification": False,
            "can_approve": False,
            "can_authorize": False,
            "can_promote": False,
            "can_certify": False,
        },
    }

class ProspectivePlanningSignalStore:
    def __init__(self, runtime_root: Path | str | None = None, *, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "prospective_planning_signals.json"
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(
        self,
        event_id: str,
        *,
        origin_ids: list[str],
        source_categories: list[str],
        goal_ids: list[str],
        purpose_category: str,
        evidence_ids: list[str],
        relevance: float = .5,
        importance: float = .5,
        urgency: float = 0.0,
        uncertainty: float = .5,
        expected_value: float = .5,
        estimated_cost: float = .5,
        estimated_duration: float = .5,
        risk: float = .5,
        reversibility: float = .5,
        time_horizon: str = "unspecified",
        alternative_ids: list[str] | None = None,
        counterfactual_ids: list[str] | None = None,
        stop_condition_ids: list[str] | None = None,
        prerequisite_ids: list[str] | None = None,
        constraint_ids: list[str] | None = None,
        predecessor_plan_ids: list[str] | None = None,
        project_id: str = "",
        conversation_id: str = "",
        scope_digest: str = "",
        operator_review_required: bool = False,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        origins = list(dict.fromkeys(_clean(x, 220) for x in origin_ids if _clean(x, 220)))
        sources = sorted(set(source_categories))
        goals = list(dict.fromkeys(_clean(x, 220) for x in goal_ids if _clean(x, 220)))
        evidence = list(dict.fromkeys(_clean(x, 220) for x in evidence_ids if _clean(x, 220)))
        alternatives = list(dict.fromkeys(_clean(x, 220) for x in (alternative_ids or []) if _clean(x, 220)))
        counterfactuals = list(dict.fromkeys(_clean(x, 220) for x in (counterfactual_ids or []) if _clean(x, 220)))
        stops = list(dict.fromkeys(_clean(x, 220) for x in (stop_condition_ids or []) if _clean(x, 220)))
        prereqs = list(dict.fromkeys(_clean(x, 220) for x in (prerequisite_ids or []) if _clean(x, 220)))
        constraints = list(dict.fromkeys(_clean(x, 220) for x in (constraint_ids or []) if _clean(x, 220)))
        predecessors = list(dict.fromkeys(_clean(x, 220) for x in (predecessor_plan_ids or []) if _clean(x, 220)))
        if (
            not event_id or not origins or not goals or not evidence or not sources
            or not set(sources).issubset(SOURCE_CATEGORIES)
            or purpose_category not in PURPOSE_CATEGORIES
        ):
            raise ValueError("complete structural prospective-planning lineage required")
        clamp = lambda x: round(max(0.0, min(float(x), 1.0)), 4)
        relevance, importance, urgency, uncertainty, expected_value, estimated_cost, estimated_duration, risk, reversibility = [
            clamp(x) for x in (relevance, importance, urgency, uncertainty, expected_value, estimated_cost, estimated_duration, risk, reversibility)
        ]
        false_pressure = (urgency > .8 and importance < .35) or (expected_value < .2 and importance < .25)
        unsupported_action_pressure = risk > .9 and reversibility < .15 and not stops
        semantic = _digest(*origins, *sources, *goals, purpose_category, *evidence, scope_digest, time_horizon, *alternatives, *counterfactuals, *stops)
        review = bool(operator_review_required or unsupported_action_pressure)
        state = "requires_operator_review" if review else ("awaiting_prerequisite" if prereqs else ("suppressed" if false_pressure or uncertainty > .97 else "active"))
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            data = self._load()
            prior = next((x for x in data["processed_events"] if x.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            duplicate = next((x for x in data["signals"] if x.get("semantic_key") == semantic and x.get("state") in {"active", "deferred", "awaiting_prerequisite", "requires_operator_review"}), None)
            if duplicate:
                result = {"status": "duplicate_signal_ignored", "signal_id": duplicate["signal_id"]}
            else:
                now = self.clock()
                signal_id = f"plan-signal-{semantic[:24]}"
                row = {
                    "signal_id": signal_id,
                    "semantic_key": semantic,
                    "origin_ids": origins,
                    "source_categories": sources,
                    "goal_ids": goals,
                    "purpose_category": purpose_category,
                    "evidence_ids": evidence,
                    "relevance": relevance,
                    "importance": importance,
                    "urgency": urgency,
                    "uncertainty": uncertainty,
                    "expected_value": expected_value,
                    "estimated_cost": estimated_cost,
                    "estimated_duration": estimated_duration,
                    "risk": risk,
                    "reversibility": reversibility,
                    "time_horizon": _clean(time_horizon, 80),
                    "alternative_ids": alternatives,
                    "counterfactual_ids": counterfactuals,
                    "stop_condition_ids": stops,
                    "prerequisite_ids": prereqs,
                    "constraint_ids": constraints,
                    "predecessor_plan_ids": predecessors,
                    "project_id": _clean(project_id, 160),
                    "conversation_id": _clean(conversation_id, 160),
                    "scope_digest": _clean(scope_digest, 128),
                    "operator_review_required": review,
                    "false_pressure_suppressed": bool(false_pressure),
                    "unsupported_action_pressure": bool(unsupported_action_pressure),
                    "deliberate_no_action_eligible": purpose_category == "deliberate_no_action_review" or risk >= .8,
                    "state": state,
                    "created_at": now,
                    "updated_at": now,
                    "plan_candidate_id": "",
                    "plan_id": "",
                    "initiative_id": "",
                    "message_id": "",
                    "notification_id": "",
                    "approval_id": "",
                    "authorization_id": "",
                    "action_id": "",
                }
                data["signals"].append(row)
                result = {"status": "planning_signal_registered", "signal_id": signal_id, "state": state}
            now = self.clock()
            data["processed_events"].append({"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True})
            data["revision"] += 1
            data["updated_at"] = now
            write_json_atomic(self.path, data, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        data = self._load()
        counts: dict[str, int] = {}
        for row in data["signals"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "signal_id", "origin_ids", "source_categories", "goal_ids", "purpose_category", "evidence_ids",
            "relevance", "importance", "urgency", "uncertainty", "expected_value", "estimated_cost",
            "estimated_duration", "risk", "reversibility", "time_horizon", "alternative_ids",
            "counterfactual_ids", "stop_condition_ids", "prerequisite_ids", "constraint_ids",
            "predecessor_plan_ids", "project_id", "conversation_id", "scope_digest",
            "operator_review_required", "false_pressure_suppressed", "unsupported_action_pressure",
            "deliberate_no_action_eligible", "state", "plan_candidate_id", "plan_id", "initiative_id",
            "message_id", "notification_id", "approval_id", "authorization_id", "action_id",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "signal_count": len(data["signals"]),
            "state_counts": counts,
            "recent_signals": [{key: row.get(key) for key in keys} for row in data["signals"][-24:]],
            "authority_boundary": deepcopy(data["authority_boundary"]),
            "raw_content_exposed": False,
            "goal_text_exposed": False,
            "plan_text_exposed": False,
            "evidence_text_exposed": False,
            "hidden_reasoning_exposed": False,
            "provider_contacted": False,
            "external_action_executed": False,
        }

def build_prospective_planning_signal_inspection(runtime_root: Path | str | None = None) -> dict[str, Any]:
    return ProspectivePlanningSignalStore(runtime_root).inspection_summary()
