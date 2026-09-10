from __future__ import annotations

"""Integrated Era 9 learning, personalization, collaboration, and self-model boundary."""

import hashlib
import json
from pathlib import Path
from typing import Any

from outcome_learning_governance_v2300 import inspect_learning_state
from preference_adaptation_v2300 import inspect_preferences, build_adaptation_projection
from cooperative_development_v2300 import inspect_work_coordination
from grounded_self_model_v2300 import build_grounded_self_model

CONTRACT_VERSION = "v2399.9"

_DENIED = {
    "model_training_performed": False,
    "memory_mutated": False,
    "source_modified": False,
    "candidate_merged": False,
    "tool_executed": False,
    "provider_contacted": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def build_era9_snapshot(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    learning = inspect_learning_state(runtime_root=runtime_root)
    preferences = inspect_preferences(runtime_root=runtime_root)
    adaptation = build_adaptation_projection(runtime_root=runtime_root) if preferences.get("ok") else {"ok": False, "status": "preferences_unavailable"}
    collaboration = inspect_work_coordination(runtime_root=runtime_root)
    self_model = build_grounded_self_model(known_limitations=(
        "Browser work does not certify native behavior.",
        "Installation and promotion remain operator decisions.",
    ))
    result = {
        "ok": all(x.get("ok") for x in (learning, preferences, collaboration, self_model)),
        "status": "era9_integrated_mind_snapshot",
        "contract_version": CONTRACT_VERSION,
        "learning": learning,
        "preferences": {"record_count": preferences.get("record_count", 0), "content_free": True},
        "adaptation": {"conflict_count": adaptation.get("conflict_count", 0), "applied_count": len(adaptation.get("applied") or []), "content_free": True},
        "collaboration": {"work_item_count": collaboration.get("work_item_count", 0), "coordination_is_advisory_only": True},
        "self_model": {"self_model_digest": self_model.get("self_model_digest"), "working_source_version": self_model.get("release_identity", {}).get("working_source_version"), "consciousness_claim_status": "unknown_not_established"},
        "verified_outcomes_not_raw_logs": True,
        "preferences_do_not_define_identity": True,
        "collaboration_does_not_replace_execution_ownership": True,
        "self_claims_require_evidence": True,
        "content_free": True,
        **_DENIED,
    }
    result["snapshot_digest"] = _digest(result)
    return result


def process_era9_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {
        "show era9 learning collaboration and self model status",
        "inspect era9 learning collaboration and self model status",
        "show era9 integrated mind status",
        "inspect era9 integrated mind status",
    }
    if raw in exact:
        return {"active": True, **build_era9_snapshot(runtime_root=runtime_root)}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era9_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = ["CONTRACT_VERSION", "build_era9_snapshot", "process_era9_control"]
