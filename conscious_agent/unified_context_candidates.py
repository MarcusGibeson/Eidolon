from __future__ import annotations

"""v1145.1 governed, content-free unified conversational context candidates.

A candidate is a deterministic bounded subset of an exact v1145.0 eligibility
record. It remains input to later communication arbitration and grants no
provider, generation, message, mutation, approval, or release authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_conversational_context_eligibility import COGNITIVE_CONTEXT_CATEGORIES, REQUIRED_CONTEXT_CATEGORIES, UnifiedConversationalContextEligibilityStore, _clean, _digest, _identifier, _parse_time

CONTRACT_VERSION = "v1145.1"
SCHEMA_VERSION = "1"
STATES = {
    "candidate_ready",
    "silence_only",
    "requires_operator_review",
    "awaiting_eligibility",
    "suppressed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
AUTHORITY_KEYS = (
    "can_arbitrate_communication",
    "can_assemble_provider_context",
    "can_contact_provider",
    "can_generate_conversation",
    "can_send_message",
    "can_create_notification",
    "can_mutate_cognition",
    "can_mutate_memory",
    "can_mutate_relationship",
    "can_mutate_mood",
    "can_mutate_goal",
    "can_mutate_motivation",
    "can_mutate_attention",
    "can_mutate_conversation",
    "can_create_proposal",
    "can_approve",
    "can_authorize",
    "can_install",
    "can_promote",
    "can_certify",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _default() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "candidates": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


def _bounded_budget(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {
        "cpu_budget_ms": max(0, int(source.get("cpu_budget_ms") or 0)),
        "memory_budget_mb": max(0, int(source.get("memory_budget_mb") or 0)),
        "latency_budget_ms": max(0, int(source.get("latency_budget_ms") or 0)),
        "token_budget": max(0, int(source.get("token_budget") or 0)),
    }


class UnifiedContextCandidateStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "unified_context_candidates.json"
        self.clock = clock or _now
        self.eligibility = UnifiedConversationalContextEligibilityStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def register(
        self,
        event_id: str,
        *,
        eligibility_id: str,
        candidate_scope_id: str,
        included_source_ids: list[str],
        provider_profile_id: str,
        communication_policy_id: str,
        privacy_policy_ids: list[str],
        temporal_window_id: str,
        window_start: str,
        window_end: str,
        budget_limits: dict[str, Any],
        silence_eligible: bool = True,
        operator_review_required: bool = False,
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        event_id = _identifier(event_id, 180)
        eligibility_id = _identifier(eligibility_id)
        candidate_scope_id = _identifier(candidate_scope_id)
        provider_profile_id = _identifier(provider_profile_id)
        communication_policy_id = _identifier(communication_policy_id)
        temporal_window_id = _identifier(temporal_window_id)
        if not all((event_id, eligibility_id, candidate_scope_id, provider_profile_id, communication_policy_id, temporal_window_id)):
            raise ValueError("bounded event, eligibility, scope, provider, communication policy, and temporal window required")

        eligibility = next(
            (
                row
                for row in self.eligibility.snapshot().get("records", [])
                if row.get("eligibility_id") == eligibility_id
            ),
            None,
        )
        if not eligibility:
            raise ValueError("exact v1145.0 eligibility required")

        requested_ids = sorted({_identifier(value) for value in included_source_ids if _identifier(value)})
        privacy_ids = sorted({_identifier(value) for value in privacy_policy_ids if _identifier(value)})
        eligible_ids = set(eligibility.get("eligible_source_ids") or [])
        source_rows = list(eligibility.get("source_lineage") or [])
        broadened_ids = sorted(set(requested_ids) - eligible_ids)
        included_rows = [row for row in source_rows if row.get("source_id") in set(requested_ids) and row.get("included")]
        excluded_rows = [row for row in source_rows if row.get("source_id") not in set(requested_ids) or not row.get("included")]
        included_categories = {row.get("source_category") for row in included_rows}
        excluded_categories = {row.get("source_category") for row in excluded_rows}
        provider_ids = {row.get("source_id") for row in included_rows if row.get("source_category") == "provider_state"}
        communication_policy_ids = {row.get("source_id") for row in included_rows if row.get("source_category") == "communication_policy"}
        included_privacy_ids = sorted(
            row.get("source_id") for row in included_rows if row.get("source_category") == "privacy_policy"
        )
        required_missing = sorted(REQUIRED_CONTEXT_CATEGORIES - included_categories)
        cognitive_present = bool(COGNITIVE_CONTEXT_CATEGORIES.intersection(included_categories))
        requested_budget = _bounded_budget(budget_limits)
        eligible_budget = _bounded_budget(eligibility.get("budget_limits"))
        budget_broadened = any(
            requested_budget[key] <= 0 or requested_budget[key] > eligible_budget[key]
            for key in requested_budget
        )
        start_dt = _parse_time(window_start)
        end_dt = _parse_time(window_end)
        eligibility_start = _parse_time(eligibility.get("reference_time"))
        eligibility_end = _parse_time(eligibility.get("expiry_at"))
        window_valid = bool(
            start_dt
            and end_dt
            and eligibility_start
            and eligibility_end
            and eligibility_start <= start_dt < end_dt <= eligibility_end
        )
        contradictions = sorted({_identifier(value) for value in contradiction_ids or [] if _identifier(value)})
        retractions = sorted({_identifier(value) for value in retraction_ids or [] if _identifier(value)})
        supersessions = sorted({_identifier(value) for value in supersession_ids or [] if _identifier(value)})
        retirements = sorted({_identifier(value) for value in retirement_ids or [] if _identifier(value)})

        state = "candidate_ready"
        reason = "bounded_unified_context_candidate"
        if retirements:
            state, reason = "retired", "retirement_lineage"
        elif retractions:
            state, reason = "retracted", "retraction_lineage"
        elif supersessions:
            state, reason = "superseded", "supersession_lineage"
        elif contradictions:
            state, reason = "suppressed", "contradictory_candidate_lineage"
        elif eligibility.get("state") not in {"eligible", "requires_operator_review"}:
            state, reason = "awaiting_eligibility", "active_v1145_0_eligibility_required"
        elif broadened_ids:
            state, reason = "suppressed", "candidate_cannot_broaden_eligible_context"
        elif required_missing:
            state, reason = "suppressed", "required_constraint_context_excluded"
        elif provider_profile_id not in provider_ids:
            state, reason = "suppressed", "exact_provider_profile_lineage_required"
        elif communication_policy_id not in communication_policy_ids:
            state, reason = "suppressed", "exact_communication_policy_lineage_required"
        elif privacy_ids != included_privacy_ids:
            state, reason = "suppressed", "exact_privacy_policy_lineage_required"
        elif budget_broadened:
            state, reason = "suppressed", "candidate_budget_cannot_broaden_eligibility"
        elif not window_valid:
            state, reason = "expired", "bounded_temporal_window_required"
        elif not silence_eligible:
            state, reason = "suppressed", "silence_must_remain_eligible"
        elif not cognitive_present:
            state, reason = "silence_only", "no_active_cognitive_context_selected"
        elif operator_review_required or eligibility.get("operator_review_required"):
            state, reason = "requires_operator_review", "operator_review_required"

        ordered_source_ids = [row.get("source_id") for row in included_rows]
        included_lineage = [
            {
                "source_category": row.get("source_category"),
                "source_id": row.get("source_id"),
                "source_revision": row.get("source_revision"),
                "source_digest": row.get("source_digest"),
                "temporal_status": row.get("temporal_status"),
                "relevance_category": row.get("relevance_category"),
                "relevance_score": row.get("relevance_score"),
                "confidence": row.get("confidence"),
                "uncertainty": row.get("uncertainty"),
                "privacy_class": row.get("privacy_class"),
                "operator_review_required": row.get("operator_review_required"),
                "lifecycle_state": row.get("lifecycle_state"),
                "lineage_digest": row.get("lineage_digest"),
                "content_free": True,
            }
            for row in included_rows
        ]
        excluded_lineage = [
            {
                "source_category": row.get("source_category"),
                "source_id": row.get("source_id"),
                "source_revision": row.get("source_revision"),
                "source_digest": row.get("source_digest"),
                "temporal_status": row.get("temporal_status"),
                "privacy_class": row.get("privacy_class"),
                "lifecycle_state": row.get("lifecycle_state"),
                "exclusion_reasons": deepcopy(row.get("exclusion_reasons") or []),
                "lineage_digest": row.get("lineage_digest"),
                "content_free": True,
            }
            for row in excluded_rows
        ]
        lifecycle_lineage = {
            "correction_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("source_category") == "operator_correction"),
            "accepted_guidance_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("source_category") == "accepted_guidance"),
            "contradicted_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("lifecycle_state") == "contradicted"),
            "retracted_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("lifecycle_state") == "retracted"),
            "superseded_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("lifecycle_state") == "superseded"),
            "expired_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("lifecycle_state") in {"stale", "expired"}),
            "retired_source_ids": sorted(row.get("source_id") for row in source_rows if row.get("lifecycle_state") == "retired"),
        }
        structural_digest = _digest(
            eligibility_id,
            candidate_scope_id,
            *ordered_source_ids,
            provider_profile_id,
            communication_policy_id,
            *privacy_ids,
            temporal_window_id,
            window_start,
            window_end,
            *requested_budget.values(),
            bool(silence_eligible),
            bool(operator_review_required),
            *contradictions,
            *retractions,
            *supersessions,
            *retirements,
        )

        with metadata_mutation_lock(self.path, timeout_seconds=5):
            persisted = self._load()
            prior = next(
                (row for row in persisted["processed_events"] if row.get("event_id") == event_id),
                None,
            )
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}
            duplicate = next(
                (
                    row
                    for row in persisted["candidates"]
                    if row.get("structural_digest") == structural_digest
                    and row.get("state") in {"candidate_ready", "silence_only", "requires_operator_review", "awaiting_eligibility"}
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "duplicate_candidate_suppressed",
                    "candidate_id": duplicate["candidate_id"],
                    "state": "suppressed",
                }
            else:
                now = self.clock()
                candidate_id = f"unified-context-candidate-{structural_digest[:24]}"
                row = {
                    "candidate_id": candidate_id,
                    "eligibility_id": eligibility_id,
                    "eligibility_structural_digest": eligibility.get("structural_digest"),
                    "eligibility_context_set_digest": eligibility.get("context_set_digest"),
                    "candidate_scope_id": candidate_scope_id,
                    "session_id": eligibility.get("session_id"),
                    "conversation_id": eligibility.get("conversation_id"),
                    "included_source_ids": ordered_source_ids,
                    "excluded_source_ids": [row.get("source_id") for row in excluded_rows],
                    "included_source_lineage": included_lineage,
                    "excluded_source_lineage": excluded_lineage,
                    "included_categories": sorted(included_categories),
                    "excluded_categories": sorted(excluded_categories),
                    "relevance_order": ordered_source_ids,
                    "confidence_bounds": [min((float(row.get("confidence") or 0) for row in included_rows), default=0.0), max((float(row.get("confidence") or 0) for row in included_rows), default=0.0)],
                    "uncertainty_bounds": [min((float(row.get("uncertainty") or 0) for row in included_rows), default=0.0), max((float(row.get("uncertainty") or 0) for row in included_rows), default=0.0)],
                    "temporal_window_id": temporal_window_id,
                    "window_start": _clean(window_start, 64),
                    "window_end": _clean(window_end, 64),
                    "budget_limits": requested_budget,
                    "provider_profile_id": provider_profile_id,
                    "privacy_policy_ids": privacy_ids,
                    "communication_policy_id": communication_policy_id,
                    "silence_eligible": bool(silence_eligible),
                    "operator_review_required": bool(operator_review_required or eligibility.get("operator_review_required")),
                    "lifecycle_lineage": lifecycle_lineage,
                    "contradiction_ids": contradictions,
                    "retraction_ids": retractions,
                    "supersession_ids": supersessions,
                    "retirement_ids": retirements,
                    "state": state,
                    "state_reason": reason,
                    "structural_digest": structural_digest,
                    "content_free": True,
                    "provider_contacted": False,
                    "provider_context_assembled": False,
                    "conversation_generated": False,
                    "message_sent": False,
                    "cognition_mutated": False,
                    "conversation_mutated": False,
                    "created_at": now,
                    "history": [
                        {
                            "change": "recorded",
                            "state": state,
                            "occurred_at": now,
                            "content_free": True,
                        }
                    ],
                }
                persisted["candidates"].append(row)
                result = {
                    "status": "candidate_recorded",
                    "candidate_id": candidate_id,
                    "state": state,
                }

            now = self.clock()
            persisted["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_digest": hashlib.sha256(event_id.encode("utf-8")).hexdigest(),
                    "occurred_at": now,
                    "result": deepcopy(result),
                    "content_free": True,
                }
            )
            persisted["revision"] += 1
            persisted["updated_at"] = now
            write_json_atomic(self.path, persisted, expected_type=dict, sort_keys=True)
            return {"ok": True, **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["candidates"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "candidate_id",
            "eligibility_id",
            "eligibility_structural_digest",
            "eligibility_context_set_digest",
            "candidate_scope_id",
            "session_id",
            "conversation_id",
            "included_source_ids",
            "excluded_source_ids",
            "included_source_lineage",
            "excluded_source_lineage",
            "included_categories",
            "excluded_categories",
            "relevance_order",
            "confidence_bounds",
            "uncertainty_bounds",
            "temporal_window_id",
            "window_start",
            "window_end",
            "budget_limits",
            "provider_profile_id",
            "privacy_policy_ids",
            "communication_policy_id",
            "silence_eligible",
            "operator_review_required",
            "lifecycle_lineage",
            "contradiction_ids",
            "retraction_ids",
            "supersession_ids",
            "retirement_ids",
            "state",
            "state_reason",
            "structural_digest",
            "provider_contacted",
            "provider_context_assembled",
            "conversation_generated",
            "message_sent",
            "cognition_mutated",
            "conversation_mutated",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["candidates"]),
            "state_counts": counts,
            "recent_records": [
                {key: deepcopy(row.get(key)) for key in keys} for row in state["candidates"][-32:]
            ],
            "recognized_states": sorted(STATES),
            "deterministic_construction": True,
            "eligible_set_broadening_allowed": False,
            "silence_is_valid_outcome": True,
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "raw_conversation_exposed": False,
            "raw_message_exposed": False,
            "prompt_exposed": False,
            "reflection_text_exposed": False,
            "memory_text_exposed": False,
            "relationship_text_exposed": False,
            "mood_text_exposed": False,
            "goal_text_exposed": False,
            "motivation_text_exposed": False,
            "provider_payload_exposed": False,
            "generated_response_exposed": False,
            "hidden_reasoning_exposed": False,
            "provider_contacted": False,
            "provider_context_assembled": False,
            "conversation_generated": False,
            "message_sent": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
        }


def build_unified_context_candidate_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return UnifiedContextCandidateStore(runtime_root).inspection_summary()
