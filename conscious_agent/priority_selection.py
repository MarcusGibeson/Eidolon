from __future__ import annotations

"""v1263.3-v1263.5 v1261->v1262->v1263 priority-selection integration."""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from development_backlog_generation import generate_development_backlog
from priority_selection_foundations import (
    PRIORITY_DENIED_AUTHORITY,
    public_priority_selection,
    select_priority_from_backlog,
    validate_priority_selection,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1263.5"


def generate_priority_selection(
    source_root: str | Path,
    *,
    external_evidence: Iterable[Mapping[str, Any]] = (),
    priority_context: Iterable[Mapping[str, Any]] = (),
    max_items: int = 32,
) -> dict[str, Any]:
    backlog = generate_development_backlog(source_root, external_evidence=external_evidence, max_items=max_items)
    selection = select_priority_from_backlog(backlog, priority_context=priority_context)
    selection["integration_contract_version"] = CONTRACT_VERSION
    selection["backlog_generated_in_same_read_only_pass"] = True
    selection["priority_is_judgment_not_authority"] = True
    selection["alternative_planning_deferred_to_v1264"] = True
    selection["selection_digest"] = hashlib.sha256(
        json.dumps({k: v for k, v in selection.items() if k != "selection_digest"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
    return selection


def generate_backlog_and_priority_selection(
    source_root: str | Path,
    *,
    external_evidence: Iterable[Mapping[str, Any]] = (),
    priority_context: Iterable[Mapping[str, Any]] = (),
    max_items: int = 32,
) -> tuple[dict[str, Any], dict[str, Any]]:
    backlog = generate_development_backlog(source_root, external_evidence=external_evidence, max_items=max_items)
    selection = select_priority_from_backlog(backlog, priority_context=priority_context)
    selection["integration_contract_version"] = CONTRACT_VERSION
    selection["backlog_generated_in_same_read_only_pass"] = True
    selection["priority_is_judgment_not_authority"] = True
    selection["alternative_planning_deferred_to_v1264"] = True
    selection["selection_digest"] = hashlib.sha256(
        json.dumps({k: v for k, v in selection.items() if k != "selection_digest"}, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()
    return backlog, selection


def inspect_priority_selection(
    source_root: str | Path,
    *,
    external_evidence: Iterable[Mapping[str, Any]] = (),
    priority_context: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    backlog, selection = generate_backlog_and_priority_selection(source_root, external_evidence=external_evidence, priority_context=priority_context)
    validation = validate_priority_selection(selection, backlog)
    return {
        "ok": bool(validation.get("ok")),
        "status": "priority_selection_inspection_ready" if validation.get("ok") else "priority_selection_inspection_invalid",
        "validation": validation,
        "public_selection": public_priority_selection(selection),
        "selection_digest": selection.get("selection_digest", ""),
        "backlog_digest": backlog.get("backlog_digest", ""),
        "read_only": True,
        **PRIORITY_DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "generate_priority_selection", "generate_backlog_and_priority_selection", "inspect_priority_selection"]
