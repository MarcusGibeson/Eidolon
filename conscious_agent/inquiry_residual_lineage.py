from __future__ import annotations

"""Bounded parent/child inquiry lineage for unresolved residual questions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from self_directed_inquiry import InquiryWorkspace

CONTRACT_VERSION = "v1106.0"
SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 700) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(_clean(p, 2000) for p in parts).encode("utf-8")).hexdigest()


def _root() -> Path:
    return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve() / "cognition"


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "links": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "resource_limits": {"max_children_per_parent": 5, "max_lineage_depth": 4},
        "authority_boundary": {
            "can_browse": False,
            "can_authorize_action": False,
            "can_execute_action": False,
            "operator_authority_unchanged": True,
        },
    }


class InquiryResidualLineage:
    def __init__(self, runtime_root: str | Path | None = None, *, workspace: InquiryWorkspace | None = None, clock: Callable[[], str] | None = None) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _root()
        self.path = self.runtime_root / "inquiry_residual_lineage.json"
        self.workspace = workspace or InquiryWorkspace(self.runtime_root)
        self.clock = clock or _now

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _mutate(self, event_id: str, fn: Callable[[dict[str, Any], str], dict[str, Any]]) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        if not event_id:
            raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, "status": "duplicate_event_ignored", "result": deepcopy(prior["result"]), "idempotent": True}
            now = self.clock()
            result = fn(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            state["processed_events"] = (state["processed_events"] + [{"event_id": event_id, "event_digest": _digest(event_id), "occurred_at": now, "result": deepcopy(result)}])[-512:]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def create_child(self, event_id: str, *, parent_inquiry_id: str, residual_question: str, uncertainty: float = 0.7, child_inquiry_id: str = "") -> dict[str, Any]:
        parent_inquiry_id = _clean(parent_inquiry_id, 120)
        residual_question = _clean(residual_question, 700)
        if not parent_inquiry_id or not residual_question:
            raise ValueError("parent_inquiry_id and residual_question are required")
        snapshot = self.workspace.snapshot()
        parent = next((row for row in snapshot["inquiries"] if row.get("inquiry_id") == parent_inquiry_id), None)
        if not parent:
            raise KeyError("parent inquiry not found")
        semantic_key = _digest(parent_inquiry_id, residual_question.casefold())

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            duplicate = next((row for row in state["links"] if row.get("semantic_key") == semantic_key and row.get("active") is True), None)
            if duplicate:
                return {"status": "duplicate_child_ignored", "link_id": duplicate["link_id"], "child_inquiry_id": duplicate["child_inquiry_id"], "created": False}
            children = [row for row in state["links"] if row.get("parent_inquiry_id") == parent_inquiry_id and row.get("active") is True]
            if len(children) >= int(state["resource_limits"]["max_children_per_parent"]):
                raise ValueError("child inquiry budget reached")
            parent_link = next((row for row in state["links"] if row.get("child_inquiry_id") == parent_inquiry_id and row.get("active") is True), None)
            depth = int(parent_link.get("depth") or 1) + 1 if parent_link else 1
            if depth > int(state["resource_limits"]["max_lineage_depth"]):
                raise ValueError("lineage depth budget reached")
            child_id = _clean(child_inquiry_id, 120) or f"inquiry-{uuid.uuid4().hex}"
            created = self.workspace.create_inquiry(
                f"{event_id}:workspace",
                motivation_id=str(parent.get("motivation_id") or ""),
                question=residual_question,
                uncertainty=uncertainty,
                sources_sought=parent.get("sources_sought") or (),
                stop_conditions=parent.get("stop_conditions") or (),
                project_id=str(parent.get("project_id") or ""),
                inquiry_id=child_id,
            )
            actual_child = created["result"]["inquiry_id"]
            link = {
                "link_id": f"lineage-{uuid.uuid4().hex}",
                "semantic_key": semantic_key,
                "parent_inquiry_id": parent_inquiry_id,
                "child_inquiry_id": actual_child,
                "residual_question": residual_question,
                "depth": depth,
                "active": True,
                "created_at": now,
                "provenance": {"parent_question_digest": _digest(parent.get("question")), "source": "residual_question"},
            }
            state["links"].append(link)
            return {"status": "child_inquiry_created", "link_id": link["link_id"], "child_inquiry_id": actual_child, "depth": depth, "created": True}

        return self._mutate(event_id, apply)

    def retract_link(self, event_id: str, *, link_id: str, reason_code: str) -> dict[str, Any]:
        link_id, reason_code = _clean(link_id, 120), _clean(reason_code, 160)
        if not link_id or not reason_code:
            raise ValueError("link_id and reason_code are required")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            row = next((item for item in state["links"] if item.get("link_id") == link_id), None)
            if not row:
                raise KeyError("lineage link not found")
            row["active"] = False
            row["retracted_at"] = now
            row["retraction_reason"] = reason_code
            return {"status": "lineage_link_retracted", "link_id": link_id}

        return self._mutate(event_id, apply)

    def inspection_summary(self, *, item_limit: int = 12) -> dict[str, Any]:
        state = self._load()
        active = [row for row in state["links"] if row.get("active") is True]
        inactive = [row for row in state["links"] if row.get("active") is not True]
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "active_link_count": len(active),
            "historical_link_count": len(inactive),
            "recent_links": deepcopy((active + inactive)[-max(1, int(item_limit)):]),
            "resource_limits": deepcopy(state["resource_limits"]),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "provider_contacted": False,
            "external_browsing_performed": False,
            "action_authority_changed": False,
            "hidden_reasoning_exposed": False,
        }


def build_inquiry_residual_lineage_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return InquiryResidualLineage(runtime_root).inspection_summary()
