from __future__ import annotations

"""v1147.4 bounded startup-tier planning and conversation-critical execution."""

import hashlib
import json
import sys
from typing import Any

from architecture_ownership_manifest import build_architecture_ownership_manifest
from conversation_startup_runtime import conversation_startup_status, ensure_conversation_startup

CONTRACT_VERSION = "v1147.4"
TIER_ORDER = ("core", "conversation_critical", "deferred")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_startup_tier_plan() -> dict[str, Any]:
    manifest = build_architecture_ownership_manifest()
    tiers: list[dict[str, Any]] = []
    for tier in TIER_ORDER:
        domains = [row for row in manifest["domains"] if row["startup_tier"] == tier]
        modules = [row["owner_module"] for row in domains]
        tiers.append({
            "tier": tier,
            "domains": [row["domain"] for row in domains],
            "owner_modules": modules,
            "module_count": len(modules),
            "automatic_execution_allowed": tier == "conversation_critical",
            "provider_contact_allowed": False,
            "structural_digest": _digest({"tier": tier, "modules": modules}),
        })
    return {
        "contract_version": CONTRACT_VERSION,
        "plan_id": "architecture-startup-tier-plan:v1147.4",
        "tiers": tiers,
        "tier_order": list(TIER_ORDER),
        "deferred_tier_remains_lazy": True,
        "provider_contact_allowed": False,
        "content_free": True,
        "structural_digest": _digest(tiers),
    }


def run_bounded_startup_tier(tier: str) -> dict[str, Any]:
    selected = str(tier or "").strip()
    if selected not in TIER_ORDER:
        raise ValueError("unknown startup tier")
    before = conversation_startup_status()
    if selected == "conversation_critical":
        after = ensure_conversation_startup()
        outcome = "ready" if after.get("ok") else "review_required"
        executed = True
    elif selected == "core":
        after = conversation_startup_status()
        outcome = "observed"
        executed = False
    else:
        after = conversation_startup_status()
        outcome = "deferred"
        executed = False
    loaded_provider_modules = sorted(name for name in after.get("provider_modules_loaded", {}) if after["provider_modules_loaded"].get(name))
    receipt = {
        "contract_version": CONTRACT_VERSION,
        "receipt_id": f"architecture-startup-tier:{selected}:{after.get('generation', 0)}",
        "tier": selected,
        "outcome": outcome,
        "execution_performed": executed,
        "conversation_status_before": str(before.get("status") or ""),
        "conversation_status_after": str(after.get("status") or ""),
        "conversation_generation": int(after.get("generation") or 0),
        "loaded_core_module_count": len(after.get("loaded_core_modules") or []),
        "optional_failure_count": len(after.get("optional_failures") or []),
        "provider_modules_loaded": loaded_provider_modules,
        "provider_contacted": False,
        "accepted_turn_replayed": False,
        "runtime_content_mutated": False,
        "deferred_services_started": False,
        "content_free": True,
    }
    receipt["structural_digest"] = _digest(receipt)
    return receipt


def inspect_startup_consolidation() -> dict[str, Any]:
    plan = build_startup_tier_plan()
    status = conversation_startup_status()
    return {
        "contract_version": CONTRACT_VERSION,
        "inspection_id": "architecture-startup-consolidation:v1147.4",
        "plan": plan,
        "conversation_status": status,
        "loaded_owner_module_count": sum(1 for row in build_architecture_ownership_manifest()["domains"] if row["owner_module"] in sys.modules),
        "deferred_tier_started": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "read_only": True,
        "content_free": True,
        "structural_digest": _digest({"plan": plan["structural_digest"], "status": status.get("status")}),
    }
