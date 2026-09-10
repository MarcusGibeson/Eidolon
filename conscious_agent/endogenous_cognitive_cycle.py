from __future__ import annotations

"""Bounded endogenous attention and reflection cycle.

The cycle can be activated by events or a background cadence without a new user
message. Each activation performs at most one deterministic reflection step by
default, may intentionally choose no subject, and never authorizes or executes a
protected action. Structural receipts contain trigger categories, digests, and
changed-field names rather than raw prompts, private conversation text, provider
payloads, or hidden chain-of-thought.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable, Mapping

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore

CYCLE_SCHEMA_VERSION = "1"
CYCLE_CONTRACT_VERSION = "v1104.4"
CONTROL_MODES = {"running", "paused", "sleeping"}
TRIGGER_TYPES = {
    "event",
    "cadence",
    "time_change",
    "completed_work",
    "failure",
    "memory_change",
    "unresolved_conversation",
    "manual_review",
    "provider_state_change",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch_now() -> float:
    return time.time()


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(*parts: Any) -> str:
    text = "\x1f".join(_clean(part, 2000) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    override = os.environ.get("EIDOLON_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve() / "cognition"
    return Path(__file__).resolve().parents[1] / "data" / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": CYCLE_SCHEMA_VERSION,
        "contract_version": CYCLE_CONTRACT_VERSION,
        "controls": {
            "mode": "running",
            "cadence_seconds": 900,
            "max_cycles_per_hour": 4,
            "max_cycles_per_day": 24,
            "max_reflection_steps_per_cycle": 1,
            "max_provider_calls_per_cycle": 0,
            "minimum_salience": 0.28,
            "communication_salience": 0.62,
            "updated_at": "",
        },
        "world_model": {
            "event_type_counts": {},
            "last_event_ref_digests": [],
            "completed_work_count": 0,
            "failure_count": 0,
            "memory_change_count": 0,
            "unresolved_conversation_count": 0,
            "provider_available": None,
            "updated_at": "",
        },
        "worker_generation": 1,
        "cycle_receipts": [],
        "recent_reflections": [],
        "processed_control_events": [],
        "last_cycle_at": "",
        "last_cycle_epoch": 0.0,
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {
            "can_authorize_action": False,
            "can_execute_action": False,
            "can_create_approval": False,
            "can_manage_models": False,
            "operator_authority_unchanged": True,
        },
    }


class EndogenousCognitiveCycle:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        motivation_store: MotivationStore | None = None,
        clock: Callable[[], str] | None = None,
        epoch_clock: Callable[[], float] | None = None,
        receipt_limit: int = 512,
        reflection_limit: int = 128,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "cognitive_cycle_state.json"
        self.motivations = motivation_store or MotivationStore(self.runtime_root)
        self.clock = clock or _utc_now
        self.epoch_clock = epoch_clock or _epoch_now
        self.receipt_limit = max(32, int(receipt_limit))
        self.reflection_limit = max(16, int(reflection_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != CYCLE_SCHEMA_VERSION:
            return _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            state.setdefault(key, deepcopy(value))
        for key, value in defaults["controls"].items():
            state["controls"].setdefault(key, deepcopy(value))
        for key, value in defaults["world_model"].items():
            state["world_model"].setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def set_control(
        self,
        event_id: str,
        *,
        action: str,
        cadence_seconds: int | None = None,
        max_cycles_per_hour: int | None = None,
        max_cycles_per_day: int | None = None,
        max_reflection_steps_per_cycle: int | None = None,
        minimum_salience: float | None = None,
        communication_salience: float | None = None,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        action = _clean(action, 40).lower()
        if not event_id:
            raise ValueError("event_id is required")
        if action not in {"pause", "resume", "sleep", "wake", "adjust_budget"}:
            raise ValueError("unsupported cognitive-cycle control")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_control_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_control_ignored", "result": deepcopy(prior.get("result") or {}), "idempotent": True}
            controls = state["controls"]
            before_mode = controls["mode"]
            if action == "pause":
                controls["mode"] = "paused"
            elif action == "resume":
                controls["mode"] = "running"
            elif action == "sleep":
                controls["mode"] = "sleeping"
            elif action == "wake":
                controls["mode"] = "running"
                state["worker_generation"] = int(state.get("worker_generation") or 1) + 1
            if cadence_seconds is not None:
                controls["cadence_seconds"] = max(30, min(86400, int(cadence_seconds)))
            if max_cycles_per_hour is not None:
                controls["max_cycles_per_hour"] = max(1, min(60, int(max_cycles_per_hour)))
            if max_cycles_per_day is not None:
                controls["max_cycles_per_day"] = max(1, min(1000, int(max_cycles_per_day)))
            if max_reflection_steps_per_cycle is not None:
                controls["max_reflection_steps_per_cycle"] = max(0, min(3, int(max_reflection_steps_per_cycle)))
            if minimum_salience is not None:
                controls["minimum_salience"] = round(max(0.0, min(1.0, float(minimum_salience))), 4)
            if communication_salience is not None:
                controls["communication_salience"] = round(max(0.0, min(1.0, float(communication_salience))), 4)
            # This bounded cycle never receives model-management authority.
            controls["max_provider_calls_per_cycle"] = 0
            now = self.clock()
            controls["updated_at"] = now
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            result = {
                "status": "control_updated",
                "action": action,
                "prior_mode": before_mode,
                "mode": controls["mode"],
                "worker_generation": state["worker_generation"],
                "budgets": self._budget_summary(controls),
                "continuity_erased": False,
            }
            state["processed_control_events"] = (state["processed_control_events"] + [{
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }])[-256:]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": "control_updated", "result": result, "idempotent": False}

    def run_cycle(
        self,
        cycle_event_id: str,
        *,
        trigger_type: str,
        perceived_events: Iterable[Mapping[str, Any]] = (),
        provider_available: bool | None = None,
        worker_id: str = "local-cognitive-worker",
        worker_generation: int | None = None,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        cycle_event_id = _clean(cycle_event_id, 180)
        trigger_type = _clean(trigger_type, 80).lower()
        if not cycle_event_id:
            raise ValueError("cycle_event_id is required")
        if trigger_type not in TRIGGER_TYPES:
            raise ValueError("unsupported trigger_type")
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        cycle_key = _digest(trigger_type, cycle_event_id)
        perceived = [self._normalize_event(item) for item in perceived_events if isinstance(item, Mapping)]
        perceived = [item for item in perceived if item]

        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = next((row for row in state["cycle_receipts"] if row.get("cycle_key") == cycle_key), None)
            if duplicate:
                return {
                    "ok": True,
                    "status": "duplicate_cycle_ignored",
                    "cycle_id": duplicate.get("cycle_id"),
                    "receipt": deepcopy(duplicate),
                    "idempotent": True,
                }
            current_generation = int(state.get("worker_generation") or 1)
            requested_generation = current_generation if worker_generation is None else int(worker_generation)
            if requested_generation < current_generation:
                receipt = self._receipt(
                    cycle_key=cycle_key,
                    cycle_event_id=cycle_event_id,
                    trigger_type=trigger_type,
                    status="stale_worker_rejected",
                    epoch=epoch,
                    now=self.clock(),
                    worker_id=worker_id,
                    worker_generation=requested_generation,
                    selected=None,
                    salience=0.0,
                    conclusion="",
                    communication="silence",
                    communication_reason="A stale worker generation cannot update cognitive state.",
                    changed_fields=[],
                    perceived=perceived,
                    provider_available=provider_available,
                )
                self._append_receipt_and_write(state, receipt)
                return {"ok": True, "status": "stale_worker_rejected", "cycle_id": receipt["cycle_id"], "receipt": receipt, "idempotent": False}
            if requested_generation > current_generation:
                state["worker_generation"] = requested_generation

            controls = state["controls"]
            suppression = self._suppression_reason(state, trigger_type, epoch)
            if suppression:
                receipt = self._receipt(
                    cycle_key=cycle_key,
                    cycle_event_id=cycle_event_id,
                    trigger_type=trigger_type,
                    status=suppression[0],
                    epoch=epoch,
                    now=self.clock(),
                    worker_id=worker_id,
                    worker_generation=requested_generation,
                    selected=None,
                    salience=0.0,
                    conclusion="",
                    communication="silence",
                    communication_reason=suppression[1],
                    changed_fields=[],
                    perceived=perceived,
                    provider_available=provider_available,
                )
                self._append_receipt_and_write(state, receipt)
                return {"ok": True, "status": receipt["status"], "cycle_id": receipt["cycle_id"], "receipt": receipt, "idempotent": False}

            world_changed = self._update_world_model(state, perceived, provider_available, self.clock())
            motivation_changes = self._apply_perceived_events(cycle_event_id, perceived)
            candidates = self.motivations.active_motivations()
            selected, salience = self._select_attention(candidates, perceived)
            minimum = float(controls.get("minimum_salience") or 0.0)
            reflection_steps = int(controls.get("max_reflection_steps_per_cycle") or 0)
            if not selected or salience < minimum or reflection_steps <= 0:
                conclusion = ""
                communication = "silence"
                communication_reason = "No subject exceeded the bounded salience threshold; silence was selected deliberately."
                status = "completed_with_silence"
                changed_fields = world_changed + motivation_changes
                selected = None
            else:
                conclusion = self._reflection_conclusion(selected, perceived)
                attend_event = f"cycle-attend:{cycle_key}"
                self.motivations.mark_attended(
                    attend_event,
                    str(selected.get("motivation_id") or ""),
                    conclusion=conclusion,
                    supporting_refs=[item["event_ref"] for item in perceived if item.get("event_ref")],
                )
                communication_threshold = float(controls.get("communication_salience") or 1.0)
                should_communicate = bool(
                    salience >= communication_threshold
                    and selected.get("kind") in {"curiosity", "concern", "unresolved_subject", "temporary_goal"}
                    and selected.get("lifecycle_state") == "active"
                )
                communication = "consider_communication" if should_communicate else "silence"
                communication_reason = (
                    "The selected subject is salient enough to consider a concise state-grounded communication."
                    if should_communicate
                    else "Reflection changed internal continuity but communication would add too little value right now."
                )
                status = "completed"
                changed_fields = world_changed + motivation_changes + ["motivation.last_attended_at", "recent_reflections"]

            now = self.clock()
            self_observation_event = f"cycle-self:{cycle_key}"
            try:
                self.motivations.observe_self_state(
                    self_observation_event,
                    operating_state=controls["mode"],
                    current_focus=str(selected.get("motivation_id") or "") if selected else "",
                    uncertainty="active" if selected and float(selected.get("confidence") or 0) < 0.6 else "bounded",
                    resource_posture="provider_free_bounded_cycle",
                    provider_available=provider_available,
                    supporting_refs=[cycle_event_id],
                )
                changed_fields.append("self_model.current_focus")
            except Exception:
                # A self-model observation failure cannot make the cycle unsafe or authorize recovery.
                changed_fields.append("self_model_observation_unavailable")

            if conclusion and selected:
                state["recent_reflections"] = (state["recent_reflections"] + [{
                    "reflection_id": f"reflection-{cycle_key[:24]}",
                    "cycle_key": cycle_key,
                    "motivation_id": selected.get("motivation_id"),
                    "kind": selected.get("kind"),
                    "conclusion": conclusion,
                    "uncertainty": "active" if float(selected.get("confidence") or 0) < 0.6 else "bounded",
                    "supporting_ref_digests": [_digest(item.get("event_ref")) for item in perceived if item.get("event_ref")][:16],
                    "authored_at": now,
                    "raw_chain_of_thought": False,
                }])[-self.reflection_limit:]

            receipt = self._receipt(
                cycle_key=cycle_key,
                cycle_event_id=cycle_event_id,
                trigger_type=trigger_type,
                status=status,
                epoch=epoch,
                now=now,
                worker_id=worker_id,
                worker_generation=requested_generation,
                selected=selected,
                salience=salience,
                conclusion=conclusion,
                communication=communication,
                communication_reason=communication_reason,
                changed_fields=changed_fields,
                perceived=perceived,
                provider_available=provider_available,
            )
            state["last_cycle_at"] = now
            state["last_cycle_epoch"] = epoch
            self._append_receipt_and_write(state, receipt)
            return {"ok": True, "status": status, "cycle_id": receipt["cycle_id"], "receipt": receipt, "idempotent": False}

    def run_due_cadence(self, *, now_epoch: float | None = None, worker_id: str = "background-cadence", worker_generation: int | None = None) -> dict[str, Any]:
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        state = self._load()
        cadence = max(30, int(state["controls"].get("cadence_seconds") or 900))
        bucket = int(epoch // cadence)
        return self.run_cycle(
            f"cadence:{bucket}",
            trigger_type="cadence",
            perceived_events=[{"event_type": "time_change", "event_ref": f"cadence-bucket:{bucket}"}],
            provider_available=None,
            worker_id=worker_id,
            worker_generation=worker_generation,
            now_epoch=epoch,
        )

    def inspection_summary(self, *, reflection_limit: int = 8) -> dict[str, Any]:
        state = self._load()
        controls = deepcopy(state["controls"])
        recent = list(state.get("recent_reflections") or [])[-max(1, int(reflection_limit)) :]
        receipts = list(state.get("cycle_receipts") or [])
        last = receipts[-1] if receipts else {}
        return {
            "ok": True,
            "schema_version": CYCLE_SCHEMA_VERSION,
            "contract_version": CYCLE_CONTRACT_VERSION,
            "status": controls.get("mode"),
            "controls": self._budget_summary(controls) | {"mode": controls.get("mode")},
            "world_model": deepcopy(state["world_model"]),
            "worker_generation": state.get("worker_generation"),
            "cycle_count": len(receipts),
            "last_cycle": {
                "cycle_id": last.get("cycle_id", ""),
                "status": last.get("status", "never_run"),
                "trigger_type": last.get("trigger_type", ""),
                "selected_motivation_id": last.get("selected_motivation_id", ""),
                "salience": last.get("salience", 0.0),
                "communication_decision": last.get("communication_decision", "silence"),
                "communication_reason": last.get("communication_reason", "No cycle has run."),
                "occurred_at": last.get("occurred_at", ""),
            },
            "recent_reflections": [
                {
                    "reflection_id": row.get("reflection_id"),
                    "motivation_id": row.get("motivation_id"),
                    "kind": row.get("kind"),
                    "conclusion": row.get("conclusion"),
                    "uncertainty": row.get("uncertainty"),
                    "authored_at": row.get("authored_at"),
                }
                for row in recent
            ],
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "raw_chain_of_thought_stored": False,
            "provider_payloads_stored": False,
            "model_management_performed": False,
            "updated_at": state.get("updated_at", ""),
        }

    def _suppression_reason(self, state: Mapping[str, Any], trigger_type: str, epoch: float) -> tuple[str, str] | None:
        controls = state["controls"]
        mode = controls.get("mode")
        if mode == "paused":
            return "paused", "The operator paused cognitive cycles; no reflection or communication was performed."
        if mode == "sleeping":
            return "sleeping", "The cognitive cycle is sleeping; silence and continuity preservation are intentional."
        receipts = [row for row in state.get("cycle_receipts") or [] if row.get("status") in {"completed", "completed_with_silence"}]
        hourly = sum(1 for row in receipts if epoch - float(row.get("occurred_epoch") or 0.0) < 3600)
        daily = sum(1 for row in receipts if epoch - float(row.get("occurred_epoch") or 0.0) < 86400)
        if hourly >= int(controls.get("max_cycles_per_hour") or 1):
            return "hourly_budget_exhausted", "The hourly cognitive-cycle budget is exhausted; no work was performed."
        if daily >= int(controls.get("max_cycles_per_day") or 1):
            return "daily_budget_exhausted", "The daily cognitive-cycle budget is exhausted; no work was performed."
        if trigger_type == "cadence":
            last_epoch = float(state.get("last_cycle_epoch") or 0.0)
            cadence = max(30, int(controls.get("cadence_seconds") or 900))
            if last_epoch and epoch - last_epoch < cadence:
                return "cadence_not_due", "The bounded background cadence is not due; no duplicate reflection was performed."
        return None

    def _apply_perceived_events(self, cycle_event_id: str, perceived: list[dict[str, Any]]) -> list[str]:
        changed: list[str] = []
        snapshot = self.motivations.snapshot()
        by_id = {row.get("motivation_id"): row for row in snapshot.get("motivations") or []}
        for index, event in enumerate(perceived):
            motivation_id = event.get("motivation_id")
            if not motivation_id or motivation_id not in by_id:
                continue
            row = by_id[motivation_id]
            outcome = event.get("outcome")
            event_id = f"cycle-event:{_digest(cycle_event_id, index, event.get('event_ref'))}"
            if outcome == "success":
                self.motivations.update_motivation(
                    event_id,
                    motivation_id,
                    reason_code="observed_success",
                    event_type="success",
                    urgency=0.0,
                    confidence=1.0,
                    lifecycle_state="resolved",
                    authored_conclusion="Observed completion evidence resolved the active motivation.",
                    supporting_refs=[event.get("event_ref", "")],
                    outcome_ref=event.get("event_ref", ""),
                )
                changed.append("motivation.resolved")
            elif outcome == "failure":
                self.motivations.update_motivation(
                    event_id,
                    motivation_id,
                    reason_code="observed_failure",
                    event_type="failure",
                    urgency=min(1.0, float(row.get("urgency") or 0.0) + 0.15),
                    confidence=max(0.0, float(row.get("confidence") or 0.0) - 0.1),
                    authored_conclusion="Observed failure increased attention while preserving uncertainty.",
                    supporting_refs=[event.get("event_ref", "")],
                    outcome_ref=event.get("event_ref", ""),
                )
                changed.append("motivation.failure_update")
            elif outcome == "correction" and event.get("explicit_retraction") is True:
                self.motivations.retract_motivation(
                    event_id,
                    motivation_id,
                    reason_code="explicit_correction",
                    correction_ref=event.get("event_ref", ""),
                )
                changed.append("motivation.retracted")
            elif outcome == "new_evidence":
                confidence = event.get("confidence")
                self.motivations.update_motivation(
                    event_id,
                    motivation_id,
                    reason_code="new_evidence",
                    event_type="evidence_update",
                    confidence=float(confidence) if confidence is not None else row.get("confidence"),
                    authored_conclusion="New evidence revised confidence without fabricating certainty.",
                    supporting_refs=[event.get("event_ref", "")],
                )
                changed.append("motivation.confidence")
        return changed

    def _select_attention(
        self,
        candidates: list[dict[str, Any]],
        perceived: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any] | None, float]:
        ranked: list[tuple[float, str, dict[str, Any]]] = []
        kind_bonus = {"concern": 0.1, "unresolved_subject": 0.08, "curiosity": 0.05, "temporary_goal": 0.04}
        event_targets = {
            str(item.get("motivation_id") or "")
            for item in (perceived or [])
            if str(item.get("motivation_id") or "")
        }
        for row in candidates:
            motivation_id = str(row.get("motivation_id") or "")
            score = (
                float(row.get("urgency") or 0.0) * 0.5
                + float(row.get("confidence") or 0.0) * 0.2
                + abs(float(row.get("valence") or 0.0)) * 0.15
                + kind_bonus.get(str(row.get("kind") or ""), 0.0)
                + (0.18 if motivation_id in event_targets else 0.0)
            )
            if row.get("last_attended_at"):
                score -= 0.05
            score = round(max(0.0, min(1.0, score)), 4)
            ranked.append((score, str(row.get("motivation_id") or ""), row))
        if not ranked:
            return None, 0.0
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return deepcopy(ranked[0][2]), ranked[0][0]

    @staticmethod
    def _reflection_conclusion(selected: Mapping[str, Any], perceived: list[dict[str, Any]]) -> str:
        kind = str(selected.get("kind") or "")
        event_types = {item.get("event_type") for item in perceived}
        if "failure" in event_types:
            return "The latest failure keeps this subject active; preserve the relevant boundary and seek one bounded piece of corrective evidence."
        if "completed_work" in event_types:
            return "Recent completion evidence should be reconciled with the subject’s remaining completion conditions before it is considered settled."
        if kind == "curiosity":
            return "The question remains open; the next useful reflection is to identify one bounded source of evidence rather than invent an answer."
        if kind == "concern":
            return "The concern remains active; preserve its safety boundary and compare it with the newest available evidence."
        if kind == "unresolved_subject":
            return "The subject is still unresolved; retain continuity without forcing a conclusion or an interruption."
        if kind in {"temporary_goal", "enduring_goal"}:
            return "The goal remains active; compare current evidence with its completion condition before changing commitment or priority."
        if kind == "preference":
            return "The preference remains relevant only while it is current, uncorrected, and useful in this context."
        if kind == "need":
            return "The need remains active; distinguish internal importance from permission to act."
        return "The selected subject remains active, but the bounded cycle produced no stronger conclusion."

    @staticmethod
    def _normalize_event(value: Mapping[str, Any]) -> dict[str, Any]:
        event_type = _clean(value.get("event_type"), 80).lower()
        event_ref = _clean(value.get("event_ref"), 240)
        if not event_type or not event_ref:
            return {}
        return {
            "event_type": event_type,
            "event_ref": event_ref,
            "motivation_id": _clean(value.get("motivation_id"), 120),
            "outcome": _clean(value.get("outcome"), 40).lower(),
            "explicit_retraction": value.get("explicit_retraction") is True,
            "confidence": value.get("confidence"),
            "relevance": round(max(0.0, min(1.0, float(value.get("relevance") or 0.5))), 4),
        }

    def _update_world_model(self, state: dict[str, Any], perceived: list[dict[str, Any]], provider_available: bool | None, now: str) -> list[str]:
        world = state["world_model"]
        changed: list[str] = []
        counts = dict(world.get("event_type_counts") or {})
        refs = list(world.get("last_event_ref_digests") or [])
        for event in perceived:
            event_type = event["event_type"]
            counts[event_type] = int(counts.get(event_type) or 0) + 1
            refs.append(_digest(event["event_ref"]))
            if event_type == "completed_work":
                world["completed_work_count"] = int(world.get("completed_work_count") or 0) + 1
            elif event_type == "failure":
                world["failure_count"] = int(world.get("failure_count") or 0) + 1
            elif event_type == "memory_change":
                world["memory_change_count"] = int(world.get("memory_change_count") or 0) + 1
            elif event_type == "unresolved_conversation":
                world["unresolved_conversation_count"] = int(world.get("unresolved_conversation_count") or 0) + 1
        if perceived:
            world["event_type_counts"] = counts
            world["last_event_ref_digests"] = refs[-32:]
            changed.extend(["world_model.event_type_counts", "world_model.last_event_ref_digests"])
        if provider_available is not None and world.get("provider_available") is not bool(provider_available):
            world["provider_available"] = bool(provider_available)
            changed.append("world_model.provider_available")
        world["updated_at"] = now
        return changed

    def _receipt(
        self,
        *,
        cycle_key: str,
        cycle_event_id: str,
        trigger_type: str,
        status: str,
        epoch: float,
        now: str,
        worker_id: str,
        worker_generation: int,
        selected: Mapping[str, Any] | None,
        salience: float,
        conclusion: str,
        communication: str,
        communication_reason: str,
        changed_fields: Iterable[str],
        perceived: list[dict[str, Any]],
        provider_available: bool | None,
    ) -> dict[str, Any]:
        return {
            "cycle_id": f"cycle-{cycle_key[:24]}",
            "cycle_key": cycle_key,
            "event_digest": _digest(cycle_event_id),
            "trigger_type": trigger_type,
            "status": status,
            "occurred_at": now,
            "occurred_epoch": round(float(epoch), 3),
            "worker_digest": _digest(worker_id),
            "worker_generation": int(worker_generation),
            "perceived_event_types": [item["event_type"] for item in perceived],
            "perceived_ref_digests": [_digest(item["event_ref"]) for item in perceived],
            "selected_motivation_id": str(selected.get("motivation_id") or "") if selected else "",
            "selected_kind": str(selected.get("kind") or "") if selected else "",
            "salience": round(float(salience), 4),
            "reflection_step_count": 1 if conclusion else 0,
            "reflection_mode": "deterministic_provider_free" if provider_available is not True else "deterministic_provider_available_not_used",
            "reflection_conclusion": _clean(conclusion, 500),
            "communication_decision": communication,
            "communication_reason": _clean(communication_reason, 360),
            "changed_fields": sorted(set(_clean(item, 120) for item in changed_fields if _clean(item, 120))),
            "provider_available": provider_available,
            "provider_contacted": False,
            "provider_call_count": 0,
            "model_installed": False,
            "model_pulled": False,
            "model_replaced": False,
            "model_deleted": False,
            "raw_chain_of_thought_stored": False,
            "private_conversation_stored": False,
            "authorizes_action": False,
            "executes_action": False,
            "creates_approval": False,
            "content_free_trigger_evidence": True,
        }

    def _append_receipt_and_write(self, state: dict[str, Any], receipt: dict[str, Any]) -> None:
        state["cycle_receipts"] = (state["cycle_receipts"] + [receipt])[-self.receipt_limit :]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = receipt["occurred_at"]
        write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)

    @staticmethod
    def _budget_summary(controls: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "cadence_seconds": int(controls.get("cadence_seconds") or 900),
            "max_cycles_per_hour": int(controls.get("max_cycles_per_hour") or 4),
            "max_cycles_per_day": int(controls.get("max_cycles_per_day") or 24),
            "max_reflection_steps_per_cycle": int(controls.get("max_reflection_steps_per_cycle") or 1),
            "max_provider_calls_per_cycle": 0,
            "minimum_salience": float(controls.get("minimum_salience") or 0.28),
            "communication_salience": float(controls.get("communication_salience") or 0.62),
        }


class BoundedCognitiveScheduler:
    """Optional daemon cadence runner with explicit start/stop lifecycle.

    The scheduler never invokes a model. It wakes at a bounded polling interval,
    asks the engine to perform at most one due cadence step, and relies on the
    persisted budgets and deduplication keys to suppress duplicate work.
    """

    def __init__(self, engine: EndogenousCognitiveCycle, *, poll_seconds: float = 30.0, worker_id: str = "background-cadence") -> None:
        self.engine = engine
        self.poll_seconds = max(1.0, float(poll_seconds))
        self.worker_id = _clean(worker_id, 120) or "background-cadence"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="eidolon-cognitive-cadence", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout_seconds: float = 5.0) -> bool:
        self._stop.set()
        thread = self._thread
        if thread:
            thread.join(max(0.0, float(timeout_seconds)))
        return not self.running

    def tick(self, *, now_epoch: float | None = None) -> dict[str, Any]:
        return self.engine.run_due_cadence(now_epoch=now_epoch, worker_id=self.worker_id)

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self.tick()
            except Exception:
                # Background cadence failures remain local and bounded. No retry storm.
                continue


def build_cognitive_cycle_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return EndogenousCognitiveCycle(runtime_root).inspection_summary()
