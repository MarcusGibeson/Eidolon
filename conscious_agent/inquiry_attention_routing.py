from __future__ import annotations

"""Bounded routing of active inquiries into endogenous attention."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from self_directed_inquiry import InquiryWorkspace

CONTRACT_VERSION = "v1105.3"
SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(p, 2000) for p in parts).encode()).hexdigest()


def _root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "controls": {"enabled": True, "minimum_priority": 0.30, "max_activations_per_day": 8},
        "activations": [], "processed_events": [], "revision": 0, "updated_at": "",
        "authority_boundary": {"can_browse": False, "can_call_provider": False, "can_authorize_action": False, "can_execute_action": False},
    }


class InquiryAttentionRouter:
    def __init__(self, runtime_root: str | Path | None = None, *, workspace: InquiryWorkspace | None = None, clock: Callable[[], str] | None = None) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "inquiry_attention_routing.json"
        self.workspace = workspace or InquiryWorkspace(self.runtime_root)
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for k, v in _default().items(): state.setdefault(k, deepcopy(v))
        return state

    def snapshot(self) -> dict[str, Any]: return deepcopy(self._load())

    def activate(self, event_id: str, *, trigger_type: str = "cadence", allow_silence: bool = True) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        if not event_id: raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((r for r in state["processed_events"] if r.get("event_id") == event_id), None)
            if prior: return {"ok": True, "status": "duplicate_activation_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            controls = state["controls"]
            selected = self.workspace.select_next()
            status, reason = "silence_selected", "No eligible inquiry warranted attention."
            activation = None
            if controls.get("enabled") and selected and float(selected.get("priority") or 0) >= float(controls.get("minimum_priority") or 0):
                today = self.clock()[:10]
                count = sum(1 for r in state["activations"] if str(r.get("occurred_at", "")).startswith(today))
                if count < int(controls.get("max_activations_per_day") or 0):
                    status, reason = "inquiry_attention_selected", "An active inquiry exceeded the bounded attention threshold."
                    activation = {
                        "activation_id": f"inq-attn-{_digest(event_id, selected['inquiry_id'])[:24]}",
                        "inquiry_id": selected["inquiry_id"], "motivation_id": selected.get("motivation_id", ""),
                        "trigger_type": _clean(trigger_type, 80), "priority": float(selected.get("priority") or 0),
                        "question_digest": _digest(selected.get("question", "")), "occurred_at": self.clock(),
                        "provider_contacted": False, "external_browsing_performed": False, "action_authorized": False,
                    }
                    state["activations"] = (state["activations"] + [activation])[-256:]
            elif not allow_silence:
                status, reason = "no_eligible_inquiry", "No eligible inquiry was available."
            result = {"status": status, "reason": reason, "activation": activation, "silence": activation is None}
            now = self.clock(); state["revision"] += 1; state["updated_at"] = now
            state["processed_events"] = (state["processed_events"] + [{"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result)}])[-512:]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": status, "result": result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load(); rows = list(state["activations"])
        return {"ok": True, "contract_version": CONTRACT_VERSION, "controls": deepcopy(state["controls"]), "activation_count": len(rows), "recent_activations": deepcopy(rows[-8:]), "provider_contacted": False, "external_browsing_performed": False, "action_authority_changed": False, "authority_boundary": deepcopy(state["authority_boundary"])}


def build_inquiry_attention_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return InquiryAttentionRouter(runtime_root).inspection_summary()
