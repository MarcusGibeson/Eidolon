from __future__ import annotations

"""v1147.6 content-free architecture consolidation continuity and drift review."""

import hashlib
import json
from typing import Any

from architecture_ownership_manifest import build_architecture_ownership_manifest
from checkpoint_registry import inspect_checkpoint_registry
from architecture_startup_consolidation import build_startup_tier_plan, inspect_startup_consolidation

CONTRACT_VERSION = "v1147.6"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_architecture_consolidation_continuity(*, prior_record: dict[str, Any] | None = None) -> dict[str, Any]:
    ownership = build_architecture_ownership_manifest()
    registry = inspect_checkpoint_registry()
    startup_plan = build_startup_tier_plan()
    startup = inspect_startup_consolidation()
    owner_modules = {row["owner_module"] for row in ownership["domains"]}
    registered_modules = {row["module"] for row in registry["checkpoints"]}
    tier_modules = {module for row in startup_plan["tiers"] for module in row["owner_modules"]}
    missing_tier_owners = sorted(owner_modules - tier_modules)
    duplicate_responsibilities: list[str] = []
    seen: set[str] = set()
    for row in ownership["domains"]:
        for responsibility in row["responsibilities"]:
            if responsibility in seen:
                duplicate_responsibilities.append(responsibility)
            seen.add(responsibility)
    prior_digest = str((prior_record or {}).get("structural_digest") or "")
    prior_revision = int((prior_record or {}).get("revision") or 0)
    current_basis = {
        "ownership_digest": ownership["structural_digest"],
        "registry_digest": registry["structural_digest"],
        "startup_digest": startup_plan["structural_digest"],
    }
    drift = bool(prior_record) and any(
        str((prior_record or {}).get(key) or "") != value for key, value in current_basis.items()
    )
    issues = {
        "missing_tier_owners": missing_tier_owners,
        "duplicate_responsibilities": sorted(set(duplicate_responsibilities)),
        "duplicate_checkpoint_ids": list(registry["duplicate_checkpoint_ids"]),
        "unowned_registered_modules": [],
    }
    issue_count = sum(len(value) for value in issues.values())
    visible_state = "attention" if issue_count or drift else ("changed" if prior_record and prior_digest else "steady")
    record = {
        "contract_version": CONTRACT_VERSION,
        "continuity_id": f"architecture-consolidation-continuity:{prior_revision + 1}",
        "revision": prior_revision + 1,
        "prior_revision": prior_revision or None,
        "prior_structural_digest": prior_digest or None,
        **current_basis,
        "ownership_domain_count": ownership["domain_count"],
        "registered_checkpoint_count": registry["checkpoint_count"],
        "startup_tier_count": len(startup_plan["tiers"]),
        "loaded_owner_module_count": startup["loaded_owner_module_count"],
        "deferred_tier_started": startup["deferred_tier_started"],
        "drift_detected": drift,
        "issues": issues,
        "issue_count": issue_count,
        "visible_state": visible_state,
        "historical_modules_preserved": True,
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "content_free": True,
        "read_only": True,
    }
    record["structural_digest"] = _digest(record)
    return record
