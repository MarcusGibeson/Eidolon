from __future__ import annotations

"""v2505.1-v2505.6 bounded message-independent cognitive runtime.

This runtime is an admission/governance layer around UnifiedCognitiveRuntime.
It can start a cognitive cycle without a user message, but cannot perform
external actions. Completion remains structural and candidate-only.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from background_cognition_policy_v2505 import evaluate_background_cognition_admission
from background_structural_cognition_v2505 import derive_structural_background_outcome
from cognitive_operation_arbitration import arbitrate_cognitive_operation
from cognitive_thought_continuity import CognitiveThoughtContinuityStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_cognitive_runtime_v2504 import UnifiedCognitiveRuntime
from unified_cognitive_state_frame import build_unified_cognitive_state_frame

CONTRACT_VERSION = "v2505.6"
SCHEMA_VERSION = "1"

_SAFE_OUTCOMES = frozenset({
    "NO_DURABLE_CHANGE",
    "BELIEF_REVISION_CANDIDATE",
    "GOAL_UPDATE_CANDIDATE",
    "PLAN_UPDATE_CANDIDATE",
    "MEMORY_INTEGRATION_CANDIDATE",
    "SELF_MODEL_EVIDENCE_CANDIDATE",
    "CONFLICT_RESOLUTION_CANDIDATE",
    "THOUGHT_CONTINUATION",
    "THOUGHT_COMPLETED",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _clean(value: Any, limit: int = 220) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "enabled": False,
        "controls": {
            "max_cycles_per_hour": 4,
            "max_open_cycles": 1,
            "minimum_interval_seconds": 60,
            "max_records": 512,
        },
        "records": [],
        "processed_events": [],
        "updated_at": "",
        "authority_boundary": {
            "can_contact_provider": False,
            "can_browse": False,
            "can_send_message": False,
            "can_execute_tool": False,
            "can_modify_source": False,
            "can_authorize_action": False,
            "can_apply_candidate": False,
            "operator_authority_unchanged": True,
        },
    }


class BackgroundCognitiveRuntime:
    def __init__(self, runtime_root: str | Path, *, clock: Callable[[], str] | None = None):
        self.root = Path(runtime_root).expanduser().resolve()
        self.path = self.root / "background_cognitive_runtime_v2505.json"
        self.clock = clock or _now
        self.unified = UnifiedCognitiveRuntime(self.root, clock=self.clock)
        self.thoughts = CognitiveThoughtContinuityStore(self.root, clock=self.clock)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        if state.get("schema_version") != SCHEMA_VERSION:
            state = _default()
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        if not isinstance(state.get("controls"), dict):
            state["controls"] = deepcopy(_default()["controls"])
        for key, value in _default()["controls"].items():
            state["controls"].setdefault(key, value)
        if not isinstance(state.get("records"), list):
            state["records"] = []
        if not isinstance(state.get("processed_events"), list):
            state["processed_events"] = []
        return state

    def configure(self, event_id: str, *, enabled: bool | None = None, max_cycles_per_hour: int | None = None, minimum_interval_seconds: int | None = None) -> dict[str, Any]:
        token = _clean(event_id, 180)
        if not token:
            raise ValueError("event_id required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == token), None)
            if prior:
                return {"ok": True, "status": "configuration_replayed", "idempotent": True, "enabled": bool(state["enabled"])}
            if enabled is not None:
                state["enabled"] = bool(enabled)
            if max_cycles_per_hour is not None:
                state["controls"]["max_cycles_per_hour"] = max(1, min(24, int(max_cycles_per_hour)))
            if minimum_interval_seconds is not None:
                state["controls"]["minimum_interval_seconds"] = max(5, min(3600, int(minimum_interval_seconds)))
            now = self.clock()
            state["processed_events"] = (state["processed_events"] + [{"event_id": token, "event_digest": _digest(token), "occurred_at": now, "content_free": True}])[-1024:]
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": "background_cognition_configured", "enabled": bool(state["enabled"]), "controls": deepcopy(state["controls"]), "idempotent": False, **self._denied()}

    def _denied(self) -> dict[str, bool]:
        return {
            "provider_contacted": False,
            "message_sent": False,
            "external_action_executed": False,
            "tool_executed": False,
            "source_mutated": False,
            "authority_broadened": False,
            "candidate_applied": False,
            "hidden_reasoning_exposed": False,
        }

    def _window_rows(self, state: Mapping[str, Any], now: datetime) -> list[Mapping[str, Any]]:
        cutoff = now - timedelta(hours=1)
        result = []
        for row in state.get("records", []):
            if not isinstance(row, Mapping):
                continue
            created = _parse(row.get("created_at"))
            if created is not None and created >= cutoff and row.get("status") != "suppressed":
                result.append(row)
        return result

    def tick(
        self,
        event_id: str,
        *,
        trigger_type: str = "background_cadence",
        trigger_ref: str = "",
        subject_ref: str = "",
        new_experience: bool = False,
        self_model_evidence: bool = False,
        foreground_busy: bool = False,
        quiet_hours: bool = False,
        operator_paused: bool = False,
        sleeping: bool = False,
        resource_pressure: str = "normal",
    ) -> dict[str, Any]:
        token = _clean(event_id, 180)
        if not token:
            raise ValueError("event_id required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == token), None)
            if prior:
                rec = next((row for row in state["records"] if row.get("background_cycle_id") == prior.get("background_cycle_id")), {})
                return {"ok": True, "status": "background_tick_replayed", "idempotent": True, "record": deepcopy(rec), **self._denied()}
            now_text = self.clock()
            now = _parse(now_text) or datetime.now(timezone.utc)
            open_rows = [row for row in state["records"] if row.get("status") == "awaiting_cognitive_work"]
            recent = self._window_rows(state, now)
            last_started = max((_parse(row.get("created_at")) for row in recent), default=None)
            suppression: list[str] = []
            if not state.get("enabled"):
                suppression.append("background_cognition_disabled")
            if last_started is not None:
                elapsed = (now - last_started).total_seconds()
                if elapsed < int(state["controls"]["minimum_interval_seconds"]):
                    suppression.append("minimum_interval_not_elapsed")

            thought_state = self.thoughts.inspection_summary()
            frame = build_unified_cognitive_state_frame(self.root, trigger_type=trigger_type, trigger_ref=trigger_ref)
            arbitration = arbitrate_cognitive_operation(
                frame,
                unfinished_thought_count=int(thought_state.get("active_count") or 0),
                new_experience=bool(new_experience),
                self_model_evidence=bool(self_model_evidence),
            )
            operation = str(arbitration["selected_operation"])
            policy = evaluate_background_cognition_admission(
                operation=operation,
                foreground_busy=foreground_busy,
                quiet_hours=quiet_hours,
                operator_paused=operator_paused,
                sleeping=sleeping,
                resource_pressure=resource_pressure,
                open_background_cycles=len(open_rows),
                cycles_in_window=len(recent),
                max_cycles_per_window=int(state["controls"]["max_cycles_per_hour"]),
            )
            suppression.extend(policy["suppression_reasons"])
            bg_id = "background-cognitive-cycle-" + _digest({"event": token, "frame": frame["frame_digest"], "operation": operation})[:24]
            if suppression:
                row = {
                    "background_cycle_id": bg_id,
                    "event_id": token,
                    "selected_operation": operation,
                    "status": "suppressed",
                    "suppression_reasons": sorted(set(suppression)),
                    "frame_digest": frame["frame_digest"],
                    "unified_cycle_id": "",
                    "work_ticket_id": "",
                    "created_at": now_text,
                    "updated_at": now_text,
                }
                result_status = "background_cognition_suppressed"
            else:
                begun = self.unified.begin_cycle(
                    "background-unified-" + token,
                    trigger_type=trigger_type,
                    trigger_ref=trigger_ref,
                    subject_ref=subject_ref,
                    new_experience=new_experience,
                    self_model_evidence=self_model_evidence,
                )
                if begun.get("selected_operation") != operation:
                    raise RuntimeError("background arbitration changed before admission")
                structural = derive_structural_background_outcome(operation, frame) if operation != "REST" else None
                row = {
                    "background_cycle_id": bg_id,
                    "event_id": token,
                    "selected_operation": operation,
                    "status": "completed_no_action" if operation == "REST" else "awaiting_cognitive_work",
                    "suppression_reasons": [],
                    "frame_digest": frame["frame_digest"],
                    "unified_cycle_id": begun["cycle_id"],
                    "work_ticket_id": begun.get("work_ticket_id", ""),
                    "subject_ref": begun.get("subject_ref", ""),
                    "structural_outcome_hint": deepcopy(structural) if structural else {},
                    "created_at": now_text,
                    "updated_at": now_text,
                }
                result_status = "background_cognitive_work_opened" if row["status"] == "awaiting_cognitive_work" else "background_deliberate_inactivity"
            state["records"] = (state["records"] + [row])[-int(state["controls"]["max_records"]):]
            state["processed_events"] = (state["processed_events"] + [{"event_id": token, "event_digest": _digest(token), "background_cycle_id": bg_id, "occurred_at": now_text, "content_free": True}])[-1024:]
            state["revision"] += 1
            state["updated_at"] = now_text
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result_status, "idempotent": False, "record": deepcopy(row), **self._denied()}

    def complete(
        self,
        event_id: str,
        *,
        background_cycle_id: str,
        outcome_type: str,
        evidence_digests: list[str] | None = None,
        changed_fields: list[str] | None = None,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        token = _clean(event_id, 180)
        bg_id = _clean(background_cycle_id, 220)
        outcome = _clean(outcome_type, 80).upper()
        if not token or not bg_id:
            raise ValueError("event_id and background_cycle_id required")
        if outcome not in _SAFE_OUTCOMES:
            raise ValueError("outcome_type is not background-safe")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == token), None)
            if prior:
                return {"ok": True, "status": "background_completion_replayed", "idempotent": True, **self._denied()}
            row = next((row for row in state["records"] if row.get("background_cycle_id") == bg_id), None)
            if row is None:
                raise ValueError("unknown background_cycle_id")
            if row.get("status") != "awaiting_cognitive_work":
                raise ValueError("background cycle is not awaiting cognitive work")
            completed = self.unified.complete_cycle(
                "background-complete-" + token,
                cycle_id=row["unified_cycle_id"],
                work_ticket_id=row["work_ticket_id"],
                outcome_type=outcome,
                evidence_digests=evidence_digests,
                changed_fields=changed_fields,
                confidence=confidence,
            )
            now = self.clock()
            row["status"] = "completed_with_candidate" if completed.get("candidate_target") not in {None, "", "none"} else "completed_no_change"
            row["outcome_type"] = outcome
            row["outcome_id"] = completed.get("outcome_id", "")
            row["candidate_target"] = completed.get("candidate_target", "none")
            row["candidate_applied"] = False
            row["updated_at"] = now
            state["processed_events"] = (state["processed_events"] + [{"event_id": token, "event_digest": _digest(token), "background_cycle_id": bg_id, "occurred_at": now, "content_free": True}])[-1024:]
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": "background_cognitive_outcome_recorded", "idempotent": False, "record": deepcopy(row), **self._denied()}


    def run_structural_tick(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Run one admitted provider-free background cognitive operation end to end."""
        opened = self.tick("structural-begin-" + _clean(event_id, 150), **kwargs)
        if not opened.get("ok") or opened.get("status") != "background_cognitive_work_opened":
            return {**opened, "structural_completion_attempted": False}
        row = opened["record"]
        hint = row.get("structural_outcome_hint") if isinstance(row.get("structural_outcome_hint"), Mapping) else {}
        if not hint.get("outcome_type"):
            raise RuntimeError("admitted background cycle missing structural outcome hint")
        completed = self.complete(
            "structural-complete-" + _clean(event_id, 150),
            background_cycle_id=row["background_cycle_id"],
            outcome_type=str(hint["outcome_type"]),
            changed_fields=list(hint.get("changed_fields") or []),
            confidence=float(hint.get("confidence") or 0.5),
        )
        return {
            "ok": True,
            "status": "background_structural_cognition_completed",
            "background_cycle_id": row["background_cycle_id"],
            "selected_operation": row["selected_operation"],
            "outcome_type": hint["outcome_type"],
            "reason_code": hint.get("reason_code", ""),
            "completion": completed,
            "structural_completion_attempted": True,
            **self._denied(),
        }

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        records = state["records"][-64:]
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "enabled": bool(state["enabled"]),
            "revision": int(state["revision"]),
            "record_count": len(state["records"]),
            "open_cycle_count": sum(1 for row in state["records"] if row.get("status") == "awaiting_cognitive_work"),
            "recent_records": deepcopy(records),
            "controls": deepcopy(state["controls"]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            **self._denied(),
        }


__all__ = ["CONTRACT_VERSION", "BackgroundCognitiveRuntime"]
