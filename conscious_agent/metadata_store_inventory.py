from __future__ import annotations

"""Authoritative inventory for mutable JSON runtime stores.

The inventory describes storage families, not individual private records. It is
used to keep BOM loading, root-shape validation, canonical saves, and migration
coverage aligned without returning payload content or operator paths.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from paths import DATA_DIR
try:
    from json_storage import inspect_json_encoding
except ImportError:
    from json_storage import inspect_json_encoding


@dataclass(frozen=True)
class MutableJsonStore:
    store_id: str
    category: str
    relative_pattern: str
    expected_type: type[Any]
    migration_allowed: bool = True
    operator_registry: bool = False

    def public_record(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "category": self.category,
            "relative_pattern": self.relative_pattern,
            "expected_root_type": self.expected_type.__name__,
            "migration_allowed": self.migration_allowed,
            "operator_registry": self.operator_registry,
        }


MUTABLE_JSON_STORES: tuple[MutableJsonStore, ...] = (
    MutableJsonStore("settings", "provider_settings", "settings.json", dict),
    MutableJsonStore("projects", "projects", "projects.json", dict, operator_registry=True),
    MutableJsonStore("memories", "memory", "memories.json", list),
    MutableJsonStore("self_model", "memory", "self_model.json", dict),
    MutableJsonStore("desires", "memory", "desires.json", dict),
    MutableJsonStore("opinions", "memory", "opinions.json", dict),
    MutableJsonStore("tasks", "tasks", "tasks.json", dict),
    MutableJsonStore("approvals", "approvals", "approvals/*.json", dict),
    MutableJsonStore("conversations", "conversation", "conversations/*.json", dict),
    MutableJsonStore("conversation_drafts", "conversation", "conversation_drafts/*.json", dict),
    MutableJsonStore("conversation_controls", "conversation", "conversation_controls/*.json", dict),
    MutableJsonStore("conversation_operations", "operation_ownership", "conversation_operations/*.json", dict),
    MutableJsonStore("conversation_navigation", "conversation", "conversation_navigation/**/*.json", dict),
    MutableJsonStore("conversation_tabs", "operation_ownership", "conversation_tabs/*.json", dict),
    MutableJsonStore("project_switching", "projects", "project_switching/*.json", dict),
    MutableJsonStore("project_root_recovery", "projects", "project_root_recovery/*.json", dict),
    MutableJsonStore("conversation_evaluations", "evaluation", "conversation_evaluations/*.json", dict),
    MutableJsonStore("conversation_campaigns", "evaluation", "conversation_evaluation_campaigns/*.json", dict),
    MutableJsonStore("conversation_findings", "evaluation", "conversation_evaluation_findings/*.json", dict),
    MutableJsonStore("workspace_execution", "supervised_development", "workspace_execution/*.json", dict),
    MutableJsonStore("release_pipeline", "release", "release_pipeline/*.json", dict),
    MutableJsonStore("self_development", "supervised_development", "self_development/**/*.json", dict),
)


def list_mutable_json_stores() -> list[dict[str, Any]]:
    return [row.public_record() for row in MUTABLE_JSON_STORES]


def get_mutable_json_store(store_id: str) -> MutableJsonStore | None:
    token = str(store_id or "").strip().lower()
    return next((row for row in MUTABLE_JSON_STORES if row.store_id == token), None)


def iter_store_paths(store: MutableJsonStore, *, data_dir: Path | None = None) -> Iterable[Path]:
    root = Path(data_dir or DATA_DIR)
    pattern = store.relative_pattern
    if any(character in pattern for character in "*?["):
        yield from sorted(path for path in root.glob(pattern) if path.is_file())
        return
    candidate = root / pattern
    if candidate.is_file():
        yield candidate


def inspect_mutable_json_stores(*, data_dir: Path | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for store in MUTABLE_JSON_STORES:
        paths = list(iter_store_paths(store, data_dir=data_dir))
        states = [inspect_json_encoding(path, expected_type=store.expected_type) for path in paths]
        rows.append(
            {
                **store.public_record(),
                "file_count": len(paths),
                "bom_file_count": sum(1 for state in states if state["utf8_bom_present"]),
                "invalid_json_count": sum(1 for state in states if not state["valid_json"]),
                "invalid_shape_count": sum(
                    1 for state in states if state["valid_json"] and not state["root_shape_valid"]
                ),
                "payload_returned": False,
            }
        )
    return {
        "ok": True,
        "status": "inventory_complete",
        "store_count": len(rows),
        "stores": rows,
        "payload_returned": False,
    }
