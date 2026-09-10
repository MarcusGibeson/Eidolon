from __future__ import annotations
"""v1134.1 governed content-free prospective-plan candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_planning_signals import ProspectivePlanningSignalStore

CONTRACT_VERSION = "v1134.1"
SCHEMA_VERSION = "1"
STATES = {
    "active", "suppressed", "deferred", "awaiting_timing_window", "awaiting_prerequisite",
    "requires_operator_review", "merged", "superseded", "stale", "obsolete", "retracted", "retired",
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
        "candidates": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {
            "can_activate_goal": False,
            "can_activate_plan": False,
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

class ProspectivePlanningCandidateStore:
    def __init__(self, runtime_root: Path | str | None = None, *, clock: Callable[[], str] | None = None):
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "prospective_planning_candidates.json"
        self.signals = ProspectivePlanningSignalStore(self.runtime_root)
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        data = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            data.setdefault(key, deepcopy(value))
        return data

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(
        self,
        event_id: str,
        *,
        signal_ids: list[str],
        plan_class: str = "prospective",
        scope_digest: str = "",
        semantic_overlap_key: str = "",
        predecessor_candidate_ids: list[str] | None = None,
        prerequisite_ids: list[str] | None = None,
        timing_window_id: str = "",
        operator_review_required: bool = False,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        ids = list(dict.fromkeys(_clean(x, 220) for x in signal_ids if _clean(x, 220)))
        predecessors = list(dict.fromkeys(_clean(x, 220) for x in (predecessor_candidate_ids or []) if _clean(x, 220)))
        prerequisites = list(dict.fromkeys(_clean(x, 220) for x in (prerequisite_ids or []) if _clean(x, 220)))
        known = {row.get("signal_id"): row for row in self.signals.snapshot().get("signals", [])}
        if not event_id or not ids or any(signal_id not in known for signal_id in ids):
            raise ValueError("known prospective-planning signal lineage required")
        rows = [known[signal_id] for signal_id in ids]
        semantic = _digest(*sorted(ids), plan_class, scope_digest, semantic_overlap_key)
        review = bool(operator_review_required or any(row.get("operator_review_required") for row in rows))
        false_pressure = all(row.get("false_pressure_suppressed") for row in rows)
        prerequisites = sorted(set(prerequisites + [item for row in rows for item in row.get("prerequisite_ids", [])]))
        timing_window_id = _clean(timing_window_id, 160)
        if review:
            state = "requires_operator_review"
        elif prerequisites:
            state = "awaiting_prerequisite"
        elif timing_window_id:
            state = "awaiting_timing_window"
        elif false_pressure or all(row.get("state") == "suppressed" for row in rows):
            state = "suppressed"
        else:
            state = "active"
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            data = self._load()
            prior = next((row for row in data["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            duplicate = next((row for row in data["candidates"] if row.get("semantic_key") == semantic and row.get("state") in {"active", "deferred", "awaiting_timing_window", "awaiting_prerequisite", "requires_operator_review"}), None)
            if duplicate:
                result = {"status": "duplicate_candidate_ignored", "candidate_id": duplicate["candidate_id"]}
            else:
                now = self.clock()
                candidate_id = f"plan-candidate-{semantic[:24]}"
                row = {
                    "candidate_id": candidate_id,
                    "semantic_key": semantic,
                    "signal_ids": ids,
                    "source_categories": sorted({category for item in rows for category in item.get("source_categories", [])}),
                    "goal_ids": sorted({goal_id for item in rows for goal_id in item.get("goal_ids", [])}),
                    "purpose_categories": sorted({item.get("purpose_category") for item in rows}),
                    "plan_class": _clean(plan_class, 80),
                    "scope_digest": _clean(scope_digest, 128),
                    "semantic_overlap_key": _clean(semantic_overlap_key, 128),
                    "evidence_ids": sorted({evidence_id for item in rows for evidence_id in item.get("evidence_ids", [])}),
                    "predecessor_candidate_ids": predecessors,
                    "relevance": max(item.get("relevance", 0) for item in rows),
                    "importance": max(item.get("importance", 0) for item in rows),
                    "urgency": max(item.get("urgency", 0) for item in rows),
                    "uncertainty": max(item.get("uncertainty", 0) for item in rows),
                    "expected_value": max(item.get("expected_value", 0) for item in rows),
                    "estimated_cost": max(item.get("estimated_cost", 0) for item in rows),
                    "estimated_duration": max(item.get("estimated_duration", 0) for item in rows),
                    "risk": max(item.get("risk", 0) for item in rows),
                    "reversibility": min(item.get("reversibility", 1) for item in rows),
                    "time_horizons": sorted({item.get("time_horizon") for item in rows}),
                    "alternative_ids": sorted({x for item in rows for x in item.get("alternative_ids", [])}),
                    "counterfactual_ids": sorted({x for item in rows for x in item.get("counterfactual_ids", [])}),
                    "stop_condition_ids": sorted({x for item in rows for x in item.get("stop_condition_ids", [])}),
                    "constraint_ids": sorted({x for item in rows for x in item.get("constraint_ids", [])}),
                    "prerequisite_ids": prerequisites,
                    "timing_window_id": timing_window_id,
                    "operator_review_required": review,
                    "false_pressure_suppressed": false_pressure,
                    "unsupported_action_pressure": any(item.get("unsupported_action_pressure") for item in rows),
                    "deliberate_no_action_eligible": any(item.get("deliberate_no_action_eligible") for item in rows),
                    "state": state,
                    "created_at": now,
                    "updated_at": now,
                    "planning_deliberation_id": "",
                    "plan_id": "",
                    "initiative_id": "",
                    "message_id": "",
                    "notification_id": "",
                    "approval_id": "",
                    "authorization_id": "",
                    "action_id": "",
                }
                data["candidates"].append(row)
                result = {"status": "planning_candidate_registered", "candidate_id": candidate_id, "state": state}
            now = self.clock()
            data["processed_events"].append({"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result), "content_free": True})
            data["revision"] += 1
            data["updated_at"] = now
            write_json_atomic(self.path, data, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        data = self._load()
        counts: dict[str, int] = {}
        for row in data["candidates"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "candidate_id", "signal_ids", "source_categories", "goal_ids", "purpose_categories", "plan_class",
            "scope_digest", "semantic_overlap_key", "evidence_ids", "predecessor_candidate_ids", "relevance",
            "importance", "urgency", "uncertainty", "expected_value", "estimated_cost", "estimated_duration",
            "risk", "reversibility", "time_horizons", "alternative_ids", "counterfactual_ids",
            "stop_condition_ids", "constraint_ids", "prerequisite_ids", "timing_window_id",
            "operator_review_required", "false_pressure_suppressed", "unsupported_action_pressure",
            "deliberate_no_action_eligible", "state", "planning_deliberation_id", "plan_id", "initiative_id",
            "message_id", "notification_id", "approval_id", "authorization_id", "action_id",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "candidate_count": len(data["candidates"]),
            "state_counts": counts,
            "recent_candidates": [{key: row.get(key) for key in keys} for row in data["candidates"][-24:]],
            "authority_boundary": deepcopy(data["authority_boundary"]),
            "raw_content_exposed": False,
            "goal_text_exposed": False,
            "plan_text_exposed": False,
            "evidence_text_exposed": False,
            "hidden_reasoning_exposed": False,
            "provider_contacted": False,
            "external_action_executed": False,
        }

def build_prospective_planning_candidate_inspection(runtime_root: Path | str | None = None) -> dict[str, Any]:
    return ProspectivePlanningCandidateStore(runtime_root).inspection_summary()
