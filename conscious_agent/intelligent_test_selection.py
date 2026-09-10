from __future__ import annotations

"""v1266.3-v1266.5 integration for affected-surface self-candidate test selection."""

from pathlib import Path
from typing import Any, Mapping

from intelligent_test_selection_foundations import (
    TEST_SELECTION_DENIED_AUTHORITY,
    load_test_selection,
    prepare_intelligent_test_selection,
    public_test_selection,
    validate_test_selection,
)

CONTRACT_VERSION = "v1266.5"


def select_tests_for_isolated_self_candidate(
    source_operation_id: str,
    source_root: str | Path,
    *,
    self_modification_runtime_root: str | Path | None,
    runtime_root: str | Path | None,
) -> dict[str, Any]:
    """Build or restore the deterministic v1266 selection for a sealed v1265 candidate."""
    record = prepare_intelligent_test_selection(
        source_operation_id,
        source_root,
        self_modification_runtime_root=self_modification_runtime_root,
        runtime_root=runtime_root,
    )
    return record


def explain_selected_tests(record: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_test_selection(record)
    if not validation.get("ok"):
        return {"ok": False, "status": "test_selection_explanation_blocked_invalid_record"}
    rows = list(record.get("selected_tests") or [])
    reasons: dict[str, int] = {}
    tiers: dict[str, int] = {"focused": 0, "regression": 0}
    for row in rows:
        reasons[str(row.get("reason_code") or "unknown")] = reasons.get(str(row.get("reason_code") or "unknown"), 0) + 1
        tier = str(row.get("tier") or "")
        if tier in tiers: tiers[tier] += 1
    return {
        "ok": True, "status": "test_selection_explanation_ready", "selection_id": record.get("selection_id", ""),
        "selection_digest": record.get("selection_digest", ""), "risk_band": record.get("risk_band", ""),
        "changed_path_count": record.get("changed_path_count", 0), "affected_surfaces": list(record.get("affected_surfaces") or []),
        "selected_test_count": len(rows), "tier_counts": tiers, "reason_counts": reasons,
        "tests_executed": False, "content_minimized": True, **TEST_SELECTION_DENIED_AUTHORITY,
    }


__all__ = ["CONTRACT_VERSION", "select_tests_for_isolated_self_candidate", "explain_selected_tests", "load_test_selection", "public_test_selection"]
