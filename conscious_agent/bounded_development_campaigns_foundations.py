from __future__ import annotations
"""v1293.0-v1293.2 bounded development campaign foundations.

Campaign records coordinate already-governed development evidence.  They do not
execute implementation, tests, repairs, provider calls, application, update, or
release operations and cannot convert stage progress into authority.
"""
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping
from bounded_development_campaigns_foundations_digest import (
    SymbolDependencies as _BoundedDevelopmentCampaignsFoundationsDigestSymbolDependencies,
    digest as _digest_implementation,
    valid_digest as _valid_digest_implementation,
)


CONTRACT_VERSION = "v1293.2"
MAX_SCOPE_PATHS = 256
MAX_EVENT_BUDGET = 96
MAX_RECOVERY_BUDGET = 8
TERMINAL_STAGES = frozenset({"complete", "cancelled", "blocked"})
PROGRESS_STAGES = ("prepared", "implementation", "verification", "quality_review", "operator_review", "complete")

DENIED_AUTHORITY = {
    "provider_contact_authorized": False,
    "tool_invocation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "repair_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "source_application_authorized": False,
    "self_update_authorized": False,
    "rollback_authorized": False,
    "release_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "priority_change_authorized": False,
    "scope_expansion_authorized": False,
    "background_continuation_authorized": False,
    "standing_authority_granted": False,
}

ARCHITECTURE_LINEAGE = {
    "persistent_sessions": "v1256",
    "hierarchical_goals": "v1285",
    "dynamic_replanning": "v1286",
    "cognitive_coding": "v1290",
    "value_risk_deliberation": "v1292",
}


def _build_bounded_development_campaigns_foundations_digest_dependencies() -> _BoundedDevelopmentCampaignsFoundationsDigestSymbolDependencies:
    return _BoundedDevelopmentCampaignsFoundationsDigestSymbolDependencies(
        sha256=sha256,
    )

def digest(value: Any) -> str:
    return _digest_implementation(value, _deps=_build_bounded_development_campaigns_foundations_digest_dependencies())



def valid_digest(value: Any) -> bool:
    return _valid_digest_implementation(value, _deps=_build_bounded_development_campaigns_foundations_digest_dependencies())



def _normalize_scope_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or ".." in path.parts or text.startswith("./"):
        raise ValueError("safe_relative_scope_path_required")
    return path.as_posix()


def scope_path_digest(value: Any) -> str:
    return digest({"scope_path": _normalize_scope_path(value)})


def seal_campaign_identity(
    *,
    proposal_id: str,
    proposal_digest: str,
    objective_digest: str,
    operator_selection_digest: str,
    scope_paths: Iterable[str],
    max_events: int = 36,
    max_recovery_attempts: int = 3,
) -> dict[str, Any]:
    pid = str(proposal_id or "").strip()
    pd = str(proposal_digest or "").strip().lower()
    od = str(objective_digest or "").strip().lower()
    sd = str(operator_selection_digest or "").strip().lower()
    if not pid or not all(valid_digest(v) for v in (pd, od, sd)):
        raise ValueError("sealed_campaign_identity_required")
    path_digests = tuple(sorted({scope_path_digest(p) for p in scope_paths}))
    if not path_digests or len(path_digests) > MAX_SCOPE_PATHS:
        raise ValueError("bounded_nonempty_scope_required")
    event_budget = max(6, min(MAX_EVENT_BUDGET, int(max_events)))
    recovery_budget = max(0, min(MAX_RECOVERY_BUDGET, int(max_recovery_attempts)))
    identity = {
        "proposal_id": pid,
        "proposal_digest": pd,
        "objective_digest": od,
        "operator_selection_digest": sd,
        "scope_path_digests": path_digests,
        "scope_digest": digest(path_digests),
        "max_events": event_budget,
        "max_recovery_attempts": recovery_budget,
        "content_free": True,
    }
    identity["campaign_id"] = f"campaign-{digest(identity)[:24]}"
    identity["identity_digest"] = digest(identity)
    return identity


def initial_campaign_state(identity: Mapping[str, Any]) -> dict[str, Any]:
    if not str(identity.get("campaign_id") or "") or not valid_digest(identity.get("identity_digest")):
        raise ValueError("sealed_identity_required")
    state = {
        "contract_version": CONTRACT_VERSION,
        "campaign_id": identity["campaign_id"],
        "identity_digest": identity["identity_digest"],
        "proposal_id": identity["proposal_id"],
        "proposal_digest": identity["proposal_digest"],
        "objective_digest": identity["objective_digest"],
        "operator_selection_digest": identity["operator_selection_digest"],
        "scope_path_digests": tuple(identity["scope_path_digests"]),
        "scope_digest": identity["scope_digest"],
        "max_events": int(identity["max_events"]),
        "max_recovery_attempts": int(identity["max_recovery_attempts"]),
        "current_stage": "prepared",
        "paused": False,
        "terminal": False,
        "event_sequence": 0,
        "last_event_digest": "",
        "event_digests": (),
        "completed_stage_evidence": {},
        "failed_strategy_digests": (),
        "recovery_attempts": 0,
        "completion_conditions_met": False,
        "content_free": True,
        "read_only_coordinator": True,
        **DENIED_AUTHORITY,
    }
    state["state_digest"] = digest({k: v for k, v in state.items() if k != "state_digest"})
    return state


def validate_state_identity(state: Mapping[str, Any]) -> bool:
    return bool(
        str(state.get("campaign_id") or "").startswith("campaign-")
        and valid_digest(state.get("identity_digest"))
        and valid_digest(state.get("proposal_digest"))
        and valid_digest(state.get("objective_digest"))
        and valid_digest(state.get("operator_selection_digest"))
        and valid_digest(state.get("scope_digest"))
        and not any(bool(state.get(k)) for k in DENIED_AUTHORITY)
    )
