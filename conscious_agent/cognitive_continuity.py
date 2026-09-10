from __future__ import annotations

"""Bounded multi-day cognitive continuity and consolidation.

The store schedules revisits and records concise consolidation conclusions. It does
not store hidden chain-of-thought, contact a model, or authorize/execute actions.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore

CONTINUITY_SCHEMA_VERSION = "1"
CONTINUITY_CONTRACT_VERSION = "v1104.6"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch_now() -> float:
    return datetime.now(timezone.utc).timestamp()


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(*parts: Any) -> str:
    material = "\x1f".join(_clean(part, 2000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _day_key(epoch: float) -> str:
    return datetime.fromtimestamp(float(epoch), timezone.utc).date().isoformat()


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": CONTINUITY_SCHEMA_VERSION,
        "contract_version": CONTINUITY_CONTRACT_VERSION,
        "mode": "awake",
        "current_day": "",
        "last_wake_epoch": 0.0,
        "last_sleep_epoch": 0.0,
        "subjects": [],
        "day_ledger": [],
        "consolidation_receipts": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "controls": {
            "half_life_days": 7.0,
            "max_consolidations_per_sleep": 8,
            "max_due_revisits": 12,
            "minimum_relevance": 0.08,
        },
        "authority_boundary": {
            "can_authorize_action": False,
            "can_execute_action": False,
            "can_manage_models": False,
            "operator_authority_unchanged": True,
        },
    }


class CognitiveContinuityStore:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        motivation_store: MotivationStore | None = None,
        clock: Callable[[], str] | None = None,
        epoch_clock: Callable[[], float] | None = None,
        history_limit: int = 512,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "cognitive_continuity.json"
        self.motivations = motivation_store or MotivationStore(self.runtime_root)
        self.clock = clock or _utc_now
        self.epoch_clock = epoch_clock or _epoch_now
        self.history_limit = max(64, int(history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != CONTINUITY_SCHEMA_VERSION:
            return _default_state()
        for key, default in _default_state().items():
            state.setdefault(key, deepcopy(default))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _mutate(self, event_id: str, mutator: Callable[[dict[str, Any], str], dict[str, Any]]) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        if not event_id:
            raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior.get("result") or {}), "idempotent": True}
            now = self.clock()
            result = mutator(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            state["processed_events"] = (state["processed_events"] + [{
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }])[-self.history_limit :]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": str(result.get("status") or "updated"), "result": deepcopy(result), "idempotent": False}

    @staticmethod
    def _floor(kind: str) -> float:
        return {"enduring_goal": 0.42, "commitment": 0.42, "concern": 0.24, "unresolved_subject": 0.2, "need": 0.18}.get(kind, 0.05)

    def _sync_subjects(self, state: dict[str, Any], epoch: float) -> tuple[int, int]:
        motivations = self.motivations.snapshot().get("motivations") or []
        by_id = {str(row.get("motivation_id") or ""): row for row in motivations}
        existing = {str(row.get("motivation_id") or ""): row for row in state["subjects"]}
        created = 0
        deactivated = 0
        for motivation_id, item in by_id.items():
            if not motivation_id:
                continue
            active = item.get("lifecycle_state") == "active"
            subject = existing.get(motivation_id)
            if subject is None and active:
                base = max(0.0, min(1.0, float(item.get("urgency") or 0.0) * 0.6 + float(item.get("confidence") or 0.0) * 0.4))
                subject = {
                    "motivation_id": motivation_id,
                    "kind": _clean(item.get("kind"), 80),
                    "summary": _clean(item.get("summary"), 240),
                    "base_relevance": round(base, 4),
                    "current_relevance": round(base, 4),
                    "first_observed_epoch": epoch,
                    "last_refreshed_epoch": epoch,
                    "source_updated_at": _clean(item.get("updated_at"), 80),
                    "last_consolidated_epoch": 0.0,
                    "next_revisit_epoch": epoch,
                    "revisit_interval_seconds": 86400.0,
                    "revisit_count": 0,
                    "active": True,
                    "history": [],
                }
                state["subjects"].append(subject)
                existing[motivation_id] = subject
                created += 1
            elif subject is not None:
                if subject.get("active") and not active:
                    deactivated += 1
                subject["active"] = active
                subject["kind"] = _clean(item.get("kind"), 80)
                subject["summary"] = _clean(item.get("summary"), 240)
                if active:
                    source_updated_at = _clean(item.get("updated_at"), 80)
                    if source_updated_at and source_updated_at != subject.get("source_updated_at"):
                        subject["base_relevance"] = round(max(float(subject.get("base_relevance") or 0.0), float(item.get("urgency") or 0.0) * 0.6 + float(item.get("confidence") or 0.0) * 0.4), 4)
                        subject["last_refreshed_epoch"] = epoch
                        subject["source_updated_at"] = source_updated_at
        return created, deactivated

    def advance_time(self, event_id: str, *, now_epoch: float | None = None) -> dict[str, Any]:
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            created, deactivated = self._sync_subjects(state, epoch)
            half_life = max(1.0, float(state["controls"].get("half_life_days") or 7.0))
            minimum = max(0.0, float(state["controls"].get("minimum_relevance") or 0.0))
            due = []
            for row in state["subjects"]:
                if not row.get("active"):
                    row["current_relevance"] = 0.0
                    continue
                last_refreshed = row.get("last_refreshed_epoch")
                if last_refreshed is None:
                    last_refreshed = epoch
                age_days = max(0.0, (epoch - float(last_refreshed)) / 86400.0)
                decayed = float(row.get("base_relevance") or 0.0) * math.pow(0.5, age_days / half_life)
                floor = self._floor(str(row.get("kind") or ""))
                row["current_relevance"] = round(max(minimum, floor, min(1.0, decayed)), 4)
                if epoch >= float(row.get("next_revisit_epoch") or 0.0):
                    due.append(row)
            day = _day_key(epoch)
            boundary = bool(state.get("current_day") and state.get("current_day") != day)
            if boundary:
                state["day_ledger"] = (state["day_ledger"] + [{
                    "day": day,
                    "transition_epoch": epoch,
                    "active_subject_count": sum(1 for row in state["subjects"] if row.get("active")),
                    "due_subject_count": len(due),
                    "content_free": True,
                }])[-120:]
            state["current_day"] = day
            due.sort(key=lambda row: (-float(row.get("current_relevance") or 0.0), float(row.get("next_revisit_epoch") or 0.0), str(row.get("motivation_id") or "")))
            return {
                "status": "continuity_advanced",
                "calendar_boundary_crossed": boundary,
                "created_subjects": created,
                "deactivated_subjects": deactivated,
                "active_subject_count": sum(1 for row in state["subjects"] if row.get("active")),
                "due_motivation_ids": [row.get("motivation_id") for row in due[: int(state["controls"].get("max_due_revisits") or 12)]],
                "provider_contacted": False,
                "action_authority_changed": False,
            }

        return self._mutate(event_id, apply)

    def sleep_and_consolidate(self, event_id: str, *, now_epoch: float | None = None, max_items: int | None = None) -> dict[str, Any]:
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            self._sync_subjects(state, epoch)
            cap = max(0, min(32, int(max_items if max_items is not None else state["controls"].get("max_consolidations_per_sleep") or 8)))
            candidates = [row for row in state["subjects"] if row.get("active") and epoch >= float(row.get("next_revisit_epoch") or 0.0)]
            candidates.sort(key=lambda row: (-float(row.get("current_relevance") or row.get("base_relevance") or 0.0), str(row.get("motivation_id") or "")))
            receipts = []
            for row in candidates[:cap]:
                count = int(row.get("revisit_count") or 0) + 1
                interval = min(30 * 86400.0, max(3600.0, float(row.get("revisit_interval_seconds") or 86400.0) * 1.6))
                row["revisit_count"] = count
                row["last_consolidated_epoch"] = epoch
                row["next_revisit_epoch"] = epoch + interval
                row["revisit_interval_seconds"] = interval
                conclusion = "Retain this subject across the next day and revisit it only when due or when new evidence changes its relevance."
                record = {
                    "consolidation_id": f"consolidation-{_digest(event_id, row.get('motivation_id'))[:24]}",
                    "motivation_id": row.get("motivation_id"),
                    "kind": row.get("kind"),
                    "conclusion": conclusion,
                    "relevance": row.get("current_relevance"),
                    "next_revisit_epoch": row.get("next_revisit_epoch"),
                    "occurred_at": now,
                    "supporting_ref_digests": [_digest(row.get("motivation_id"))],
                    "raw_chain_of_thought_stored": False,
                    "authorizes_action": False,
                }
                receipts.append(record)
                row["history"] = (list(row.get("history") or []) + [{"event": "sleep_consolidation", "occurred_at": now, "conclusion_digest": _digest(conclusion)}])[-32:]
            state["mode"] = "sleeping"
            state["last_sleep_epoch"] = epoch
            state["consolidation_receipts"] = (state["consolidation_receipts"] + receipts)[-self.history_limit :]
            return {
                "status": "sleep_consolidation_completed",
                "consolidated_count": len(receipts),
                "consolidation_ids": [row["consolidation_id"] for row in receipts],
                "bounded": len(receipts) <= cap,
                "provider_contacted": False,
                "action_authority_changed": False,
            }

        result = self._mutate(event_id, apply)
        self.motivations.observe_self_state(f"{event_id}:self-state", operating_state="sleeping", current_focus="bounded consolidation", supporting_refs=[event_id])
        return result

    def wake(self, event_id: str, *, now_epoch: float | None = None) -> dict[str, Any]:
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            prior_day = str(state.get("current_day") or "")
            current_day = _day_key(epoch)
            state["mode"] = "awake"
            state["last_wake_epoch"] = epoch
            state["current_day"] = current_day
            return {
                "status": "continuity_awake",
                "calendar_boundary_crossed": bool(prior_day and prior_day != current_day),
                "current_day": current_day,
                "continuity_erased": False,
                "provider_contacted": False,
                "action_authority_changed": False,
            }

        result = self._mutate(event_id, apply)
        self.motivations.observe_self_state(f"{event_id}:self-state", operating_state="running", current_focus="re-entry after bounded consolidation", supporting_refs=[event_id])
        return result

    def due_revisit_events(self, *, now_epoch: float | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        state = self._load()
        cap = max(1, min(32, int(limit if limit is not None else state["controls"].get("max_due_revisits") or 12)))
        due = [row for row in state["subjects"] if row.get("active") and epoch >= float(row.get("next_revisit_epoch") or 0.0)]
        due.sort(key=lambda row: (-float(row.get("current_relevance") or 0.0), str(row.get("motivation_id") or "")))
        return [{
            "event_type": "scheduled_revisit",
            "event_ref": f"continuity:{_digest(row.get('motivation_id'), row.get('next_revisit_epoch'))[:24]}",
            "motivation_id": row.get("motivation_id"),
            "content_free": True,
        } for row in due[:cap]]

    def inspection_summary(self, *, item_limit: int = 10) -> dict[str, Any]:
        state = self._load()
        subjects = [row for row in state["subjects"] if row.get("active")]
        subjects.sort(key=lambda row: (-float(row.get("current_relevance") or 0.0), str(row.get("motivation_id") or "")))
        return {
            "ok": True,
            "schema_version": CONTINUITY_SCHEMA_VERSION,
            "contract_version": CONTINUITY_CONTRACT_VERSION,
            "mode": state.get("mode"),
            "current_day": state.get("current_day"),
            "active_subject_count": len(subjects),
            "due_subject_count": sum(1 for row in subjects if float(row.get("next_revisit_epoch") or 0.0) <= float(self.epoch_clock())),
            "subjects": [{
                "motivation_id": row.get("motivation_id"),
                "kind": row.get("kind"),
                "summary": row.get("summary"),
                "relevance": row.get("current_relevance"),
                "next_revisit_epoch": row.get("next_revisit_epoch"),
                "revisit_count": row.get("revisit_count"),
            } for row in subjects[: max(1, int(item_limit))]],
            "recent_consolidations": deepcopy(state["consolidation_receipts"][-8:]),
            "calendar_boundary_count": len(state["day_ledger"]),
            "controls": deepcopy(state["controls"]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "provider_contacted": False,
            "raw_chain_of_thought_stored": False,
            "updated_at": state.get("updated_at", ""),
        }


def build_cognitive_continuity_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return CognitiveContinuityStore(runtime_root).inspection_summary()
