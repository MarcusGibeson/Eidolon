from __future__ import annotations

"""v1146.0 understandable cognitive-control definitions and safe previews.

This module defines content-free operator control metadata. It does not apply
settings, mutate cognition, contact providers, create proposals, or grant
operational authority.
"""

from copy import deepcopy
import hashlib
import json
from typing import Any

CONTRACT_VERSION = "v1146.0"
SCHEMA_VERSION = "1"

CONTROL_DOMAINS = (
    "attention",
    "thought_activity",
    "initiative",
    "privacy",
    "resource_use",
    "development_proposals",
)
OWNERS = {
    "attention": "attention_coordinator",
    "thought_activity": "continuous_thought_coordinator",
    "initiative": "initiative_governance",
    "privacy": "privacy_governance",
    "resource_use": "workload_coordinator",
    "development_proposals": "supervised_development_governance",
}
SAFE_DEFAULTS: dict[str, dict[str, Any]] = {
    "attention": {"mode": "bounded", "intensity": 0.35, "operator_review_required": False},
    "thought_activity": {"mode": "bounded", "intensity": 0.25, "operator_review_required": False},
    "initiative": {"mode": "suggest_only", "intensity": 0.10, "operator_review_required": True},
    "privacy": {"mode": "strict", "intensity": 1.0, "operator_review_required": True},
    "resource_use": {"mode": "conservative", "intensity": 0.30, "operator_review_required": False},
    "development_proposals": {"mode": "disabled", "intensity": 0.0, "operator_review_required": True},
}
ALLOWED_MODES = {
    "attention": {"paused", "bounded", "focused"},
    "thought_activity": {"paused", "bounded", "scheduled"},
    "initiative": {"disabled", "suggest_only", "bounded"},
    "privacy": {"strict", "balanced"},
    "resource_use": {"minimal", "conservative", "bounded"},
    "development_proposals": {"disabled", "suggest_only"},
}
AUTHORITY_BOUNDARY = {
    "can_apply_controls": False,
    "can_mutate_cognition": False,
    "can_start_reflection": False,
    "can_contact_provider": False,
    "can_send_message": False,
    "can_create_notification": False,
    "can_create_goal": False,
    "can_create_plan": False,
    "can_create_development_proposal": False,
    "can_approve": False,
    "can_authorize": False,
    "can_install": False,
    "can_promote": False,
    "can_certify": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_understandable_cognitive_control_definitions() -> dict[str, Any]:
    rows = []
    for domain in CONTROL_DOMAINS:
        default = deepcopy(SAFE_DEFAULTS[domain])
        row = {
            "control_id": f"cognitive-control:{domain}",
            "domain": domain,
            "owner": OWNERS[domain],
            "scope": f"{domain}:bounded-operator-control",
            "allowed_modes": sorted(ALLOWED_MODES[domain]),
            "safe_default": default,
            "preview_only": True,
            "content_free": True,
            "operator_visible": True,
            "requires_explicit_confirmation_to_apply": True,
            "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
        }
        row["structural_digest"] = _digest(row)
        rows.append(row)
    report = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "control_domains": list(CONTROL_DOMAINS),
        "definitions": rows,
        "safe_defaults": deepcopy(SAFE_DEFAULTS),
        "preview_only": True,
        "mutation_available": False,
        "authority_boundary": deepcopy(AUTHORITY_BOUNDARY),
    }
    report["structural_digest"] = _digest(report)
    return report
