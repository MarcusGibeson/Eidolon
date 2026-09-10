from __future__ import annotations

"""Integrated Era 8 security, recovery, audit, and incident boundary."""

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from fine_grained_authority_v2200 import public_policy_state
from audit_incident_governance_v2200 import inspect_incidents
from trust_zone_defense_v2200 import classify_trust_zone
from transactional_recovery_v2200 import RECOVERY_CLASSES

CONTRACT_VERSION = "v2299.9"

_DENIED = {
    "tool_executed": False,
    "network_contacted": False,
    "provider_contacted": False,
    "source_modified": False,
    "private_runtime_modified": False,
    "external_notification_sent": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "secret_access_authorized": False,
    "destructive_operation_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def build_era8_trust_snapshot(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    authority = public_policy_state(runtime_root=runtime_root)
    incidents = inspect_incidents(runtime_root=runtime_root)
    zones = {name: classify_trust_zone(name) for name in (
        "system_policy", "operator_instruction", "project_content", "provider_output", "web_content", "memory_record", "generated_artifact"
    )}
    result = {
        "ok": True,
        "status": "era8_trustworthy_operation_snapshot",
        "contract_version": CONTRACT_VERSION,
        "authority": authority,
        "incidents": incidents,
        "trust_zones": {name: {"trust_level": row["trust_level"], "may_define_authority": row["may_define_authority"], "treated_as_data": row["treated_as_data"]} for name, row in zones.items()},
        "recovery_classes": list(RECOVERY_CLASSES),
        "authority_is_capability_specific": True,
        "revocation_is_first_class": True,
        "untrusted_content_cannot_redefine_authority": True,
        "recovery_requires_exact_lineage": True,
        "audit_receipts_are_content_free": True,
        "incident_freeze_is_logical_until_existing_executor_enforces_it": True,
        **_DENIED,
    }
    result["snapshot_digest"] = _digest(result)
    return result


def process_era8_trust_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {
        "inspect security recovery and trust status",
        "show security recovery and trust status",
        "inspect era8 trust status",
        "show era8 trust status",
        "inspect authority and incident status",
        "show authority and incident status",
    }
    if raw in exact:
        return {"active": True, **build_era8_trust_snapshot(runtime_root=runtime_root)}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era8_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = ["CONTRACT_VERSION", "build_era8_trust_snapshot", "process_era8_trust_control"]
