from __future__ import annotations
"""v1293.3-v1293.5 resumable, scope-bound development campaign coordinator."""
from copy import deepcopy
from typing import Any, Iterable, Mapping
from bounded_development_campaigns_foundations import (
    ARCHITECTURE_LINEAGE, DENIED_AUTHORITY, PROGRESS_STAGES, TERMINAL_STAGES,
    digest, initial_campaign_state, scope_path_digest, seal_campaign_identity,
    valid_digest, validate_state_identity,
)
from bounded_development_campaigns_campaign import (
    SymbolDependencies as _BoundedDevelopmentCampaignsCampaignSymbolDependencies,
    apply_campaign_event as _apply_campaign_event_implementation,
    campaign_public_projection as _campaign_public_projection_implementation,
)


CONTRACT_VERSION = "v1293.5"


def campaign_from_deliberation(
    deliberation: Mapping[str, Any],
    *,
    objective_digest: str,
    operator_selection_digest: str,
    scope_paths: Iterable[str],
    max_events: int = 36,
    max_recovery_attempts: int = 3,
) -> dict[str, Any]:
    if deliberation.get("disposition") != "recommend_for_operator_review":
        raise ValueError("selected_recommendation_required")
    proposal_id = str(deliberation.get("recommended_proposal_id") or "")
    proposal_digest = str(deliberation.get("recommended_proposal_digest") or "")
    identity = seal_campaign_identity(
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        objective_digest=objective_digest,
        operator_selection_digest=operator_selection_digest,
        scope_paths=scope_paths,
        max_events=max_events,
        max_recovery_attempts=max_recovery_attempts,
    )
    state = initial_campaign_state(identity)
    state["architecture_lineage"] = dict(ARCHITECTURE_LINEAGE)
    state["selection_is_execution_authority"] = False
    state["selection_is_update_authority"] = False
    state["state_digest"] = _state_digest(state)
    return state


def _state_digest(state: Mapping[str, Any]) -> str:
    return digest({k: v for k, v in state.items() if k != "state_digest"})


def _event_fingerprint(state: Mapping[str, Any], event: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    kind = str(event.get("kind") or "").strip()
    expected = str(event.get("expected_last_event_digest") or "").strip().lower()
    evidence = str(event.get("evidence_digest") or "").strip().lower()
    strategy = str(event.get("strategy_digest") or "").strip().lower()
    touched = tuple(sorted({scope_path_digest(p) for p in (event.get("touched_paths") or [])}))
    body = {
        "campaign_id": state.get("campaign_id"),
        "identity_digest": state.get("identity_digest"),
        "kind": kind,
        "expected_last_event_digest": expected,
        "evidence_digest": evidence,
        "strategy_digest": strategy,
        "touched_path_digests": touched,
        "operator_review_outcome": str(event.get("operator_review_outcome") or ""),
        "content_free": True,
    }
    return digest(body), body


def _response(state: Mapping[str, Any], status: str, *, accepted: bool = False, duplicate: bool = False, reason: str = "", extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out = {
        "ok": accepted or duplicate,
        "status": status,
        "accepted": accepted,
        "duplicate_noop": duplicate,
        "reason": reason,
        "campaign_id": state.get("campaign_id", ""),
        "current_stage": state.get("current_stage", ""),
        "paused": bool(state.get("paused")),
        "terminal": bool(state.get("terminal")),
        "event_sequence": int(state.get("event_sequence", 0)),
        "last_event_digest": state.get("last_event_digest", ""),
        "state": dict(state),
        "content_free": True,
        "read_only_coordinator": True,
        **DENIED_AUTHORITY,
    }
    if extra:
        out.update(dict(extra))
    return out


def _build_bounded_development_campaigns_campaign_dependencies() -> _BoundedDevelopmentCampaignsCampaignSymbolDependencies:
    return _BoundedDevelopmentCampaignsCampaignSymbolDependencies(
        DENIED_AUTHORITY=DENIED_AUTHORITY,
        Mapping=Mapping,
        _event_fingerprint=_event_fingerprint,
        _response=_response,
        _state_digest=_state_digest,
        deepcopy=deepcopy,
        valid_digest=valid_digest,
        validate_state_identity=validate_state_identity,
    )

def apply_campaign_event(state: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    return _apply_campaign_event_implementation(state, event, _deps=_build_bounded_development_campaigns_campaign_dependencies())



def campaign_public_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    return _campaign_public_projection_implementation(state, _deps=_build_bounded_development_campaigns_campaign_dependencies())

