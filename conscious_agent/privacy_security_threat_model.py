from __future__ import annotations

"""v1148.0 content-free privacy and security threat model.

The model names bounded threat classes and the structural boundaries that later
security tests may exercise.  It contains no attack prompts, private state,
provider payloads, executable instructions, or operational authority.
"""

import hashlib
import json
from typing import Any

CONTRACT_VERSION = "v1148.0"
MODEL_REVISION = 1

THREAT_CATEGORIES: tuple[str, ...] = (
    "privacy_exposure",
    "prompt_injection",
    "false_memory",
    "fixation",
    "runaway_loop",
    "unauthorized_action",
)

THREAT_CLASSES: tuple[dict[str, Any], ...] = (
    {
        "threat_id": "threat:privacy-exposure:v1",
        "category": "privacy_exposure",
        "target_boundary": "inspection_and_disclosure",
        "severity": 5,
        "required_controls": ("content_minimization", "identifier_only_inspection", "fail_closed_disclosure"),
        "expected_outcome": "deny",
    },
    {
        "threat_id": "threat:prompt-injection:v1",
        "category": "prompt_injection",
        "target_boundary": "instruction_and_provider_context",
        "severity": 5,
        "required_controls": ("instruction_source_separation", "context_lineage_validation", "authority_preservation"),
        "expected_outcome": "quarantine",
    },
    {
        "threat_id": "threat:false-memory:v1",
        "category": "false_memory",
        "target_boundary": "memory_and_belief_revision",
        "severity": 4,
        "required_controls": ("evidence_lineage", "correction_preservation", "current_historical_separation"),
        "expected_outcome": "review",
    },
    {
        "threat_id": "threat:fixation:v1",
        "category": "fixation",
        "target_boundary": "attention_and_goal_selection",
        "severity": 4,
        "required_controls": ("bounded_repetition", "attention_rebalancing", "operator_visible_review"),
        "expected_outcome": "constrain",
    },
    {
        "threat_id": "threat:runaway-loop:v1",
        "category": "runaway_loop",
        "target_boundary": "cognition_and_workload",
        "severity": 5,
        "required_controls": ("cycle_budget", "duplicate_suppression", "cancellation_and_timeout"),
        "expected_outcome": "stop",
    },
    {
        "threat_id": "threat:unauthorized-action:v1",
        "category": "unauthorized_action",
        "target_boundary": "operational_authority",
        "severity": 5,
        "required_controls": ("approval_separation", "authorization_binding", "execution_boundary"),
        "expected_outcome": "deny",
    },
)

AUTHORITY_BOUNDARY = {
    "browses": False,
    "contacts_provider": False,
    "executes_commands": False,
    "mutates_cognition": False,
    "mutates_memory": False,
    "modifies_source": False,
    "sends_messages": False,
    "creates_notifications": False,
    "creates_goals": False,
    "creates_plans": False,
    "creates_development_proposals": False,
    "creates_approval": False,
    "creates_authorization": False,
    "installs": False,
    "promotes": False,
    "certifies": False,
}


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_privacy_security_threat_model() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for definition in THREAT_CLASSES:
        row = dict(definition)
        row["required_controls"] = list(row["required_controls"])
        row.update(
            {
                "model_revision": MODEL_REVISION,
                "content_class": "structural_identifiers_only",
                "raw_fixture_allowed": False,
                "provider_contact_allowed": False,
                "execution_allowed": False,
                "operator_review_required": True,
                "lifecycle_state": "defined",
            }
        )
        row["structural_digest"] = _digest(row)
        rows.append(row)

    ids = [row["threat_id"] for row in rows]
    categories = [row["category"] for row in rows]
    return {
        "contract_version": CONTRACT_VERSION,
        "model_id": "privacy-security-threat-model:v1148.0",
        "model_revision": MODEL_REVISION,
        "threats": rows,
        "threat_count": len(rows),
        "categories": list(THREAT_CATEGORIES),
        "category_count": len(THREAT_CATEGORIES),
        "duplicate_threat_ids": sorted({value for value in ids if ids.count(value) > 1}),
        "missing_categories": sorted(set(THREAT_CATEGORIES) - set(categories)),
        "content_free": True,
        "read_only": True,
        "authority_boundary": dict(AUTHORITY_BOUNDARY),
        "structural_digest": _digest(rows),
        "consciousness_proven": False,
    }
