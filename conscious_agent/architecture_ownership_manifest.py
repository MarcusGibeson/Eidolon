from __future__ import annotations

"""v1147.0 structural ownership manifest for architecture consolidation."""

import hashlib
import json
from typing import Any

CONTRACT_VERSION = "v1147.0"

OWNERSHIP_DOMAINS: tuple[dict[str, Any], ...] = (
    {"domain": "cognition", "owner_module": "conscious_agent.endogenous_cognitive_cycle", "responsibilities": ("cycle_state", "bounded_reflection"), "startup_tier": "deferred"},
    {"domain": "conversation", "owner_module": "conscious_agent.conversation_startup_runtime", "responsibilities": ("session_runtime", "conversation_generation_boundary"), "startup_tier": "conversation_critical"},
    {"domain": "memory", "owner_module": "conscious_agent.memory", "responsibilities": ("retrieval", "durable_memory_boundary"), "startup_tier": "deferred"},
    {"domain": "provider", "owner_module": "conscious_agent.local_model", "responsibilities": ("provider_requests", "provider_health"), "startup_tier": "deferred"},
    {"domain": "workload", "owner_module": "conscious_agent.workload_live_arbitration", "responsibilities": ("admission", "resource_budgets"), "startup_tier": "deferred"},
    {"domain": "governance", "owner_module": "conscious_agent.version_roles", "responsibilities": ("version_authority", "authority_separation"), "startup_tier": "core"},
    {"domain": "api", "owner_module": "conscious_agent.api_server", "responsibilities": ("local_api_dispatch", "get_post_separation"), "startup_tier": "core"},
    {"domain": "dashboard", "owner_module": "conscious_agent.dashboard_startup", "responsibilities": ("dashboard_lifecycle", "deferred_services"), "startup_tier": "core"},
    {"domain": "inspection", "owner_module": "conscious_agent.checkpoint_registry", "responsibilities": ("checkpoint_discovery", "read_only_checkpoint_invocation"), "startup_tier": "deferred"},
)

AUTHORITY_BOUNDARY = {
    "executes_commands": False, "contacts_provider": False, "mutates_runtime": False,
    "modifies_source": False, "sends_messages": False, "creates_approval": False,
    "creates_authorization": False, "installs": False, "promotes": False, "certifies": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_architecture_ownership_manifest() -> dict[str, Any]:
    rows = []
    for item in OWNERSHIP_DOMAINS:
        row = dict(item)
        row["responsibilities"] = list(row["responsibilities"])
        row["owner_id"] = f"architecture-owner:{row['domain']}"
        row["structural_digest"] = _digest(row)
        rows.append(row)
    return {
        "contract_version": CONTRACT_VERSION,
        "manifest_id": "architecture-ownership:v1147.0",
        "domains": rows,
        "domain_count": len(rows),
        "unique_owner_count": len({row["owner_module"] for row in rows}),
        "duplicate_domain_owners": [],
        "content_free": True,
        "read_only": True,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "structural_digest": _digest(rows),
    }
