from __future__ import annotations

"""v1147.7 structural reliability review for architecture consolidation."""

import hashlib
import json
from typing import Any

from architecture_consolidation_continuity import build_architecture_consolidation_continuity
from checkpoint_registry import inspect_checkpoint_registry

CONTRACT_VERSION = "v1147.7"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_architecture_consolidation_reliability(*, prior_record: dict[str, Any] | None = None, source_root: str | None = None) -> dict[str, Any]:
    continuity = build_architecture_consolidation_continuity(prior_record=prior_record)
    registry = inspect_checkpoint_registry()
    dispatch_failures = sum(1 for row in registry["checkpoints"] if not row["read_only"] or row["post_available"])
    modules = [row["module"] for row in registry["checkpoints"]]
    builders = [row["builder"] for row in registry["checkpoints"]]
    duplicate_plumbing = len({item for item in modules if modules.count(item) > 1}) + len({item for item in builders if builders.count(item) > 1})
    issue_count = continuity["issue_count"] + dispatch_failures + duplicate_plumbing
    reliability_score = max(0, 100 - issue_count * 15 - (10 if continuity["drift_detected"] else 0))
    uncertainty = min(100, issue_count * 10 + (10 if continuity["drift_detected"] else 0))
    classification = "reliable" if reliability_score >= 90 and uncertainty <= 10 else "review_required"
    report = {
        "contract_version": CONTRACT_VERSION,
        "review_id": f"architecture-consolidation-reliability:{continuity['revision']}",
        "continuity_revision": continuity["revision"],
        "continuity_digest": continuity["structural_digest"],
        "ownership_drift_detected": continuity["drift_detected"],
        "continuity_issue_count": continuity["issue_count"],
        "checkpoint_dispatch_count": registry["checkpoint_count"],
        "checkpoint_dispatch_failure_count": dispatch_failures,
        "duplicate_plumbing_count": duplicate_plumbing,
        "deferred_tier_started": continuity["deferred_tier_started"],
        "historical_modules_preserved": continuity["historical_modules_preserved"],
        "reliability_score": reliability_score,
        "uncertainty": uncertainty,
        "classification": classification,
        "operator_visible_state": "ready" if classification == "reliable" else "attention",
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "content_free": True,
        "read_only": True,
    }
    report["structural_digest"] = _digest(report)
    return report
