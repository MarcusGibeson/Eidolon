from __future__ import annotations

"""Durable, bounded self-directed inquiry records.

Inquiry is internal cognitive work, not autonomous browsing or action. Records keep
concise questions, uncertainty, evidence sought, stop conditions, progress
conclusions, and supporting-reference digests. They never store hidden reasoning,
contact a provider, browse externally, or grant action authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore

INQUIRY_SCHEMA_VERSION = "1"
INQUIRY_CONTRACT_VERSION = "v1105.0"
ACTIVE_STATUSES = {"active", "paused"}
TERMINAL_STATUSES = {"completed", "abandoned", "corrected", "superseded"}
ALLOWED_MOTIVATION_KINDS = {"curiosity", "unresolved_subject"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _bounded(value: Any, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 4)


def _digest(*parts: Any) -> str:
    material = "\x1f".join(_clean(part, 2000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    root = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return root / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": INQUIRY_SCHEMA_VERSION,
        "contract_version": INQUIRY_CONTRACT_VERSION,
        "inquiries": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "resource_limits": {
            "max_progress_steps_per_inquiry": 32,
            "max_open_inquiries": 24,
            "provider_requests_per_step": 0,
            "external_browse_requests_per_step": 0,
        },
        "authority_boundary": {
            "inquiry_can_authorize_action": False,
            "inquiry_can_execute_action": False,
            "inquiry_can_browse_externally": False,
            "inquiry_can_manage_models": False,
            "operator_authority_unchanged": True,
        },
    }


class InquiryWorkspace:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        motivation_store: MotivationStore | None = None,
        clock: Callable[[], str] | None = None,
        event_history_limit: int = 512,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "inquiry_workspace.json"
        self.motivations = motivation_store or MotivationStore(self.runtime_root)
        self.clock = clock or _utc_now
        self.event_history_limit = max(64, int(event_history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != INQUIRY_SCHEMA_VERSION:
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
                return {
                    "ok": True,
                    "status": "duplicate_event_ignored",
                    "event_id": event_id,
                    "result": deepcopy(prior.get("result") or {}),
                    "idempotent": True,
                }
            now = self.clock()
            result = mutator(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            receipt = {
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }
            state["processed_events"] = (list(state["processed_events"]) + [receipt])[-self.event_history_limit :]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {
                "ok": True,
                "status": str(result.get("status") or "updated"),
                "event_id": event_id,
                "result": deepcopy(result),
                "idempotent": False,
            }

    def create_inquiry(
        self,
        event_id: str,
        *,
        motivation_id: str,
        question: str,
        uncertainty: float = 0.5,
        sources_sought: Iterable[str] = (),
        stop_conditions: Iterable[str] = (),
        project_id: str = "",
        inquiry_id: str = "",
    ) -> dict[str, Any]:
        motivation_id = _clean(motivation_id, 120)
        question = _clean(question, 700)
        if not motivation_id or not question:
            raise ValueError("motivation_id and question are required")
        motivation = next((row for row in self.motivations.active_motivations() if row.get("motivation_id") == motivation_id), None)
        if not motivation:
            raise KeyError("active motivation not found")
        if motivation.get("kind") not in ALLOWED_MOTIVATION_KINDS:
            raise ValueError("inquiries require an active curiosity or unresolved subject")
        source_rows = sorted({_clean(row, 180) for row in sources_sought if _clean(row, 180)})[:12]
        stop_rows = sorted({_clean(row, 220) for row in stop_conditions if _clean(row, 220)})[:12]
        if not stop_rows:
            stop_rows = ["Stop after 12 bounded progress steps.", "Stop when uncertainty is at or below 0.2."]
        semantic_key = _digest(motivation_id, question.casefold(), _clean(project_id, 120))

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            duplicate = next(
                (row for row in state["inquiries"] if row.get("semantic_key") == semantic_key and row.get("status") in ACTIVE_STATUSES),
                None,
            )
            if duplicate:
                return {"status": "duplicate_inquiry_ignored", "inquiry_id": duplicate["inquiry_id"], "created": False}
            open_count = sum(1 for row in state["inquiries"] if row.get("status") in ACTIVE_STATUSES)
            if open_count >= int(state["resource_limits"]["max_open_inquiries"]):
                raise ValueError("open inquiry budget reached")
            item_id = _clean(inquiry_id, 120) or f"inquiry-{uuid.uuid4().hex}"
            if any(row.get("inquiry_id") == item_id for row in state["inquiries"]):
                raise ValueError("inquiry_id already exists")
            priority = _bounded((float(motivation.get("urgency") or 0.0) + float(uncertainty)) / 2.0)
            state["inquiries"].append(
                {
                    "inquiry_id": item_id,
                    "semantic_key": semantic_key,
                    "motivation_id": motivation_id,
                    "project_id": _clean(project_id, 120),
                    "question": question,
                    "status": "active",
                    "uncertainty": _bounded(uncertainty),
                    "priority": priority,
                    "sources_sought": source_rows,
                    "stop_conditions": stop_rows,
                    "progress": [],
                    "step_count": 0,
                    "created_at": now,
                    "updated_at": now,
                    "history": [
                        {
                            "event": "inquiry_created",
                            "occurred_at": now,
                            "authored_conclusion": "A durable curiosity became a bounded inquiry without external browsing or action authority.",
                        }
                    ],
                    "authority": {
                        "browses_externally": False,
                        "authorizes_action": False,
                        "executes_action": False,
                    },
                }
            )
            return {"status": "inquiry_created", "inquiry_id": item_id, "created": True, "priority": priority}

        return self._mutate(event_id, apply)

    def add_progress(
        self,
        event_id: str,
        *,
        inquiry_id: str,
        conclusion: str,
        supporting_refs: Iterable[str] = (),
        uncertainty_after: float | None = None,
        next_question: str = "",
    ) -> dict[str, Any]:
        inquiry_id = _clean(inquiry_id, 120)
        conclusion = _clean(conclusion, 700)
        if not inquiry_id or not conclusion:
            raise ValueError("inquiry_id and conclusion are required")
        refs = sorted({_digest(_clean(row, 300)) for row in supporting_refs if _clean(row, 300)})[:16]

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            inquiry = next((row for row in state["inquiries"] if row.get("inquiry_id") == inquiry_id), None)
            if not inquiry:
                raise KeyError("inquiry not found")
            if inquiry.get("status") != "active":
                raise ValueError("progress can only be added to an active inquiry")
            maximum = int(state["resource_limits"]["max_progress_steps_per_inquiry"])
            if int(inquiry.get("step_count") or 0) >= maximum:
                inquiry["status"] = "paused"
                inquiry["updated_at"] = now
                return {"status": "inquiry_step_budget_reached", "inquiry_id": inquiry_id, "step_count": inquiry["step_count"]}
            prior_uncertainty = float(inquiry.get("uncertainty") or 0.0)
            new_uncertainty = prior_uncertainty if uncertainty_after is None else _bounded(uncertainty_after)
            step = {
                "step_id": f"step-{uuid.uuid4().hex}",
                "occurred_at": now,
                "conclusion": conclusion,
                "supporting_reference_digests": refs,
                "prior_uncertainty": prior_uncertainty,
                "uncertainty_after": new_uncertainty,
                "next_question": _clean(next_question, 500),
                "provider_contacted": False,
                "external_browsing_performed": False,
                "hidden_reasoning_stored": False,
            }
            inquiry["progress"] = (list(inquiry.get("progress") or []) + [step])[-maximum:]
            inquiry["step_count"] = int(inquiry.get("step_count") or 0) + 1
            inquiry["uncertainty"] = new_uncertainty
            inquiry["priority"] = _bounded((float(inquiry.get("priority") or 0.0) + new_uncertainty) / 2.0)
            inquiry["updated_at"] = now
            inquiry["history"] = (list(inquiry.get("history") or []) + [{"event": "progress_recorded", "occurred_at": now, "step_id": step["step_id"], "uncertainty_after": new_uncertainty}])[-64:]
            return {
                "status": "inquiry_progress_recorded",
                "inquiry_id": inquiry_id,
                "step_id": step["step_id"],
                "step_count": inquiry["step_count"],
                "uncertainty": new_uncertainty,
            }

        return self._mutate(event_id, apply)

    def set_status(
        self,
        event_id: str,
        *,
        inquiry_id: str,
        status: str,
        reason_code: str,
        correction_ref: str = "",
    ) -> dict[str, Any]:
        inquiry_id = _clean(inquiry_id, 120)
        status = _clean(status, 40).lower()
        reason_code = _clean(reason_code, 160)
        if status not in ACTIVE_STATUSES | TERMINAL_STATUSES:
            raise ValueError("unsupported inquiry status")
        if not inquiry_id or not reason_code:
            raise ValueError("inquiry_id and reason_code are required")
        if status == "corrected" and not _clean(correction_ref, 300):
            raise ValueError("corrected inquiries require correction_ref")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            inquiry = next((row for row in state["inquiries"] if row.get("inquiry_id") == inquiry_id), None)
            if not inquiry:
                raise KeyError("inquiry not found")
            prior = str(inquiry.get("status") or "active")
            inquiry["status"] = status
            inquiry["updated_at"] = now
            inquiry["history"] = (list(inquiry.get("history") or []) + [{
                "event": "status_changed",
                "occurred_at": now,
                "prior_status": prior,
                "status": status,
                "reason_code": reason_code,
                "correction_reference_digest": _digest(correction_ref) if correction_ref else "",
            }])[-64:]
            return {"status": "inquiry_status_changed", "inquiry_id": inquiry_id, "prior_status": prior, "new_status": status}

        return self._mutate(event_id, apply)

    def select_next(self) -> dict[str, Any] | None:
        rows = [row for row in self._load()["inquiries"] if row.get("status") == "active"]
        rows.sort(key=lambda row: (-float(row.get("priority") or 0.0), str(row.get("created_at") or ""), str(row.get("inquiry_id") or "")))
        return deepcopy(rows[0]) if rows else None

    def inspection_summary(self, *, item_limit: int = 10) -> dict[str, Any]:
        state = self._load()
        active = [row for row in state["inquiries"] if row.get("status") == "active"]
        paused = [row for row in state["inquiries"] if row.get("status") == "paused"]
        terminal = [row for row in state["inquiries"] if row.get("status") in TERMINAL_STATUSES]
        active.sort(key=lambda row: (-float(row.get("priority") or 0.0), str(row.get("created_at") or "")))
        return {
            "ok": True,
            "contract_version": INQUIRY_CONTRACT_VERSION,
            "active_inquiry_count": len(active),
            "paused_inquiry_count": len(paused),
            "historical_inquiry_count": len(terminal),
            "active_inquiries": deepcopy(active[: max(1, int(item_limit))]),
            "next_inquiry": deepcopy(active[0]) if active else None,
            "resource_limits": deepcopy(state["resource_limits"]),
            "revision": int(state.get("revision") or 0),
            "provider_contacted": False,
            "external_browsing_performed": False,
            "hidden_reasoning_exposed": False,
            "action_authority_changed": False,
            "authority_boundary": deepcopy(state["authority_boundary"]),
        }


def build_inquiry_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return InquiryWorkspace(runtime_root).inspection_summary()
