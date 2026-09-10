from __future__ import annotations

"""v1145.3 deterministic conversation-cognition communication arbitration.

Arbitration decides whether one exact v1145.1 unified context candidate may
proceed to a separately invoked bounded generation stage or should remain
silent/defer. The record itself grants no provider, generation, delivery,
mutation, approval, or release authority.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Any, Callable

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_context_candidates import UnifiedContextCandidateStore
from unified_conversational_context_eligibility import _clean, _identifier
from workload_live_arbitration import WorkloadLiveArbitrationStore

CONTRACT_VERSION = "v1145.3"
SCHEMA_VERSION = "1"
OUTCOMES = {
    "generation_eligible",
    "deliberate_silence",
    "defer_for_workload",
    "defer_for_provider",
    "defer_for_operator_review",
    "reject_stale_context",
    "reject_privacy",
    "reject_policy",
    "reject_lineage",
    "cancelled_before_generation",
    "suppressed",
    "expired",
    "superseded",
    "retracted",
    "retired",
}
ACTIVE_OUTCOMES = {
    "generation_eligible",
    "deliberate_silence",
    "defer_for_workload",
    "defer_for_provider",
    "defer_for_operator_review",
    "reject_stale_context",
    "reject_privacy",
    "reject_policy",
    "reject_lineage",
    "cancelled_before_generation",
}
AUTHORITY_KEYS = (
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


def _digest(*parts: Any) -> str:
    return hashlib.sha256(
        "\x1f".join(_clean(part, 12000) for part in parts).encode("utf-8")
    ).hexdigest()


def _bounded_score(value: Any) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)


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
        "arbitrations": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "controls": {
            "minimum_communication_score": 0.35,
            "minimum_confidence": 0.4,
            "maximum_uncertainty": 0.65,
            "maximum_records": 1024,
        },
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


class ConversationCognitionCommunicationArbitrationStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "conversation_cognition_communication_arbitration.json"
        self.clock = clock or _now
        self.candidates = UnifiedContextCandidateStore(self.runtime_root)
        self.workload_arbitrations = WorkloadLiveArbitrationStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def arbitrate(
        self,
        event_id: str,
        *,
        candidate_id: str,
        observed_candidate_revision: int | None,
        workload_arbitration_id: str,
        communication_requested: bool,
        communication_score: float,
        confidence: float,
        uncertainty: float,
        provider_available: bool,
        privacy_clear: bool,
        communication_policy_allows: bool,
        operator_confirmed: bool = False,
        cancellation_requested: bool = False,
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        event_id = _identifier(event_id, 180)
        candidate_id = _identifier(candidate_id)
        workload_arbitration_id = _identifier(workload_arbitration_id)
        if not event_id or not candidate_id:
            raise ValueError("bounded event and exact context candidate required")

        candidate_state = self.candidates.snapshot()
        candidate = next(
            (row for row in candidate_state.get("candidates", []) if row.get("candidate_id") == candidate_id),
            None,
        )
        if not candidate:
            raise ValueError("exact v1145.1 unified context candidate required")

        workload_state = self.workload_arbitrations.snapshot()
        workload = next(
            (
                row
                for row in workload_state.get("arbitrations", [])
                if row.get("arbitration_id") == workload_arbitration_id
            ),
            None,
        ) if workload_arbitration_id else None

        controls = self._load().get("controls") or _default()["controls"]
        score = _bounded_score(communication_score)
        confidence_score = _bounded_score(confidence)
        uncertainty_score = _bounded_score(uncertainty)
        contradictions = sorted({_identifier(value) for value in contradiction_ids or [] if _identifier(value)})
        retractions = sorted({_identifier(value) for value in retraction_ids or [] if _identifier(value)})
        supersessions = sorted({_identifier(value) for value in supersession_ids or [] if _identifier(value)})
        retirements = sorted({_identifier(value) for value in retirement_ids or [] if _identifier(value)})

        exact_revision = int(candidate_state.get("revision") or 0)
        stale_revision = observed_candidate_revision is None or int(observed_candidate_revision) != exact_revision
        candidate_budget = candidate.get("budget_limits") or {}
        workload_budget_covers = bool(
            workload
            and all(
                int(workload.get(key) or 0) >= int(candidate_budget.get(key) or 0)
                for key in ("cpu_budget_ms", "memory_budget_mb", "latency_budget_ms", "token_budget")
            )
        )
        exact_workload_admission = bool(
            workload
            and workload.get("state") == "admitted"
            and workload.get("workload_kind") == "conversation"
            and workload_budget_covers
        )
        required_policy_lineage = bool(
            candidate.get("communication_policy_id")
            and candidate.get("privacy_policy_ids")
            and candidate.get("provider_profile_id")
        )

        outcome = "generation_eligible"
        reason = "bounded_generation_eligible"
        if retirements:
            outcome, reason = "retired", "retirement_lineage"
        elif retractions:
            outcome, reason = "retracted", "retraction_lineage"
        elif supersessions:
            outcome, reason = "superseded", "supersession_lineage"
        elif contradictions:
            outcome, reason = "reject_lineage", "contradictory_lineage"
        elif stale_revision:
            outcome, reason = "reject_stale_context", "candidate_revision_changed"
        elif candidate.get("state") in {"expired", "superseded", "retracted", "retired"}:
            outcome, reason = str(candidate.get("state")), "candidate_lifecycle_inactive"
        elif candidate.get("state") == "requires_operator_review" and not operator_confirmed:
            outcome, reason = "defer_for_operator_review", "operator_confirmation_required"
        elif candidate.get("state") not in {"candidate_ready", "silence_only", "requires_operator_review"}:
            outcome, reason = "reject_lineage", "candidate_not_generation_eligible"
        elif cancellation_requested:
            outcome, reason = "cancelled_before_generation", "exact_cancellation_requested"
        elif not required_policy_lineage or not communication_policy_allows:
            outcome, reason = "reject_policy", "communication_policy_not_satisfied"
        elif not privacy_clear:
            outcome, reason = "reject_privacy", "privacy_clearance_not_satisfied"
        elif candidate.get("state") == "silence_only":
            outcome, reason = "deliberate_silence", "candidate_requires_silence"
        elif (
            not communication_requested
            or score < float(controls.get("minimum_communication_score") or 0.35)
            or confidence_score < float(controls.get("minimum_confidence") or 0.4)
            or uncertainty_score > float(controls.get("maximum_uncertainty") or 0.65)
        ):
            outcome, reason = "deliberate_silence", "communication_not_warranted"
        elif not provider_available:
            outcome, reason = "defer_for_provider", "configured_provider_unavailable"
        elif not exact_workload_admission:
            outcome, reason = "defer_for_workload", "exact_conversation_workload_admission_required"

        structural_digest = _digest(
            candidate_id,
            exact_revision,
            candidate.get("structural_digest"),
            workload_arbitration_id,
            workload.get("structural_digest") if workload else "",
            communication_requested,
            score,
            confidence_score,
            uncertainty_score,
            provider_available,
            privacy_clear,
            communication_policy_allows,
            operator_confirmed,
            cancellation_requested,
            outcome,
            reason,
            *contradictions,
            *retractions,
            *supersessions,
            *retirements,
        )

        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next(
                (row for row in state["processed_events"] if row.get("event_id") == event_id),
                None,
            )
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}

            duplicate = next(
                (
                    row
                    for row in state["arbitrations"]
                    if row.get("structural_digest") == structural_digest
                    and row.get("outcome") in ACTIVE_OUTCOMES
                ),
                None,
            )
            if duplicate:
                result = {
                    "status": "duplicate_arbitration_suppressed",
                    "arbitration_id": duplicate["arbitration_id"],
                    "outcome": "suppressed",
                    "generation_eligible": False,
                }
            else:
                now = self.clock()
                arbitration_id = f"conversation-cognition-arbitration-{structural_digest[:24]}"
                arbitration_revision = int(state.get("revision") or 0) + 1
                row = {
                    "arbitration_id": arbitration_id,
                    "arbitration_revision": arbitration_revision,
                    "candidate_id": candidate_id,
                    "candidate_store_revision": exact_revision,
                    "observed_candidate_revision": observed_candidate_revision,
                    "candidate_structural_digest": candidate.get("structural_digest"),
                    "eligibility_id": candidate.get("eligibility_id"),
                    "eligibility_structural_digest": candidate.get("eligibility_structural_digest"),
                    "session_id": candidate.get("session_id"),
                    "conversation_id": candidate.get("conversation_id"),
                    "included_source_ids": deepcopy(candidate.get("included_source_ids") or []),
                    "included_categories": deepcopy(candidate.get("included_categories") or []),
                    "excluded_categories": deepcopy(candidate.get("excluded_categories") or []),
                    "provider_profile_id": candidate.get("provider_profile_id"),
                    "privacy_policy_ids": deepcopy(candidate.get("privacy_policy_ids") or []),
                    "communication_policy_id": candidate.get("communication_policy_id"),
                    "workload_arbitration_id": workload_arbitration_id,
                    "workload_arbitration_digest": workload.get("structural_digest") if workload else "",
                    "workload_admitted": exact_workload_admission,
                    "budget_limits": deepcopy(candidate_budget),
                    "communication_requested": bool(communication_requested),
                    "communication_score": score,
                    "confidence": confidence_score,
                    "uncertainty": uncertainty_score,
                    "provider_available": bool(provider_available),
                    "privacy_clear": bool(privacy_clear),
                    "communication_policy_allows": bool(communication_policy_allows),
                    "operator_confirmed": bool(operator_confirmed),
                    "silence_eligible": bool(candidate.get("silence_eligible")),
                    "outcome": outcome,
                    "reason_code": reason,
                    "generation_eligible": outcome == "generation_eligible",
                    "deliberate_silence": outcome == "deliberate_silence",
                    "contradiction_ids": contradictions,
                    "retraction_ids": retractions,
                    "supersession_ids": supersessions,
                    "retirement_ids": retirements,
                    "structural_digest": structural_digest,
                    "content_free": True,
                    "provider_context_assembled": False,
                    "provider_contacted": False,
                    "conversation_generated": False,
                    "message_sent": False,
                    "notification_created": False,
                    "cognition_mutated": False,
                    "conversation_mutated": False,
                    "created_at": now,
                    "history": [
                        {
                            "change": "arbitration_recorded",
                            "outcome": outcome,
                            "occurred_at": now,
                            "content_free": True,
                        }
                    ],
                }
                state["arbitrations"].append(row)
                result = {
                    "status": "communication_arbitrated",
                    "arbitration_id": arbitration_id,
                    "arbitration_revision": arbitration_revision,
                    "outcome": outcome,
                    "generation_eligible": outcome == "generation_eligible",
                }

            now = self.clock()
            state["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_digest": hashlib.sha256(event_id.encode("utf-8")).hexdigest(),
                    "occurred_at": now,
                    "result": deepcopy(result),
                    "content_free": True,
                }
            )
            maximum = max(1, int((state.get("controls") or {}).get("maximum_records") or 1024))
            state["arbitrations"] = state["arbitrations"][-maximum:]
            state["processed_events"] = state["processed_events"][-maximum * 2:]
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {"ok": True, **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["arbitrations"]:
            counts[row.get("outcome")] = counts.get(row.get("outcome"), 0) + 1
        keys = (
            "arbitration_id",
            "arbitration_revision",
            "candidate_id",
            "candidate_store_revision",
            "observed_candidate_revision",
            "candidate_structural_digest",
            "eligibility_id",
            "eligibility_structural_digest",
            "session_id",
            "conversation_id",
            "included_source_ids",
            "included_categories",
            "excluded_categories",
            "provider_profile_id",
            "privacy_policy_ids",
            "communication_policy_id",
            "workload_arbitration_id",
            "workload_arbitration_digest",
            "workload_admitted",
            "budget_limits",
            "communication_requested",
            "communication_score",
            "confidence",
            "uncertainty",
            "provider_available",
            "privacy_clear",
            "communication_policy_allows",
            "operator_confirmed",
            "silence_eligible",
            "outcome",
            "reason_code",
            "generation_eligible",
            "deliberate_silence",
            "contradiction_ids",
            "retraction_ids",
            "supersession_ids",
            "retirement_ids",
            "structural_digest",
            "provider_context_assembled",
            "provider_contacted",
            "conversation_generated",
            "message_sent",
            "notification_created",
            "cognition_mutated",
            "conversation_mutated",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["arbitrations"]),
            "outcome_counts": counts,
            "recent_records": [
                {key: deepcopy(row.get(key)) for key in keys}
                for row in state["arbitrations"][-32:]
            ],
            "recognized_outcomes": sorted(OUTCOMES),
            "deterministic_arbitration": True,
            "silence_is_valid_outcome": True,
            "arbitration_is_execution_authority": False,
            "controls": deepcopy(state.get("controls") or {}),
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
            "provider_context_assembled": False,
            "provider_contacted": False,
            "conversation_generated": False,
            "message_sent": False,
            "notification_created": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
        }


def build_conversation_cognition_communication_arbitration_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return ConversationCognitionCommunicationArbitrationStore(runtime_root).inspection_summary()
