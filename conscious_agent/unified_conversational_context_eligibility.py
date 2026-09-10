from __future__ import annotations

"""v1145.0 durable, content-free unified conversational context eligibility.

The records in this module identify exact cognitive and conversational lineage
that a later stage may consider. They never assemble provider prompts, generate
prose, contact a provider, send a message, or mutate cognition or conversation.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION = "v1145.0"
SCHEMA_VERSION = "1"

SOURCE_CATEGORIES = {
    "active_thought",
    "reflection",
    "memory_reference",
    "relationship_context",
    "mood_state",
    "goal",
    "motivation",
    "concern",
    "attention_target",
    "inquiry_state",
    "operator_correction",
    "accepted_guidance",
    "conversation_context",
    "workload_budget",
    "provider_state",
    "continuity_state",
    "privacy_policy",
    "communication_policy",
}
COGNITIVE_CONTEXT_CATEGORIES = {
    "active_thought",
    "reflection",
    "memory_reference",
    "relationship_context",
    "mood_state",
    "goal",
    "motivation",
    "concern",
    "attention_target",
    "inquiry_state",
    "operator_correction",
    "accepted_guidance",
}
REQUIRED_CONTEXT_CATEGORIES = {
    "conversation_context",
    "workload_budget",
    "provider_state",
    "continuity_state",
    "privacy_policy",
    "communication_policy",
}
CURRENT_ONLY_CATEGORIES = {
    "active_thought",
    "reflection",
    "mood_state",
    "goal",
    "motivation",
    "concern",
    "attention_target",
    "inquiry_state",
    "conversation_context",
    "workload_budget",
    "provider_state",
    "continuity_state",
    "privacy_policy",
    "communication_policy",
}
HISTORICAL_ALLOWED_CATEGORIES = {
    "memory_reference",
    "relationship_context",
    "operator_correction",
    "accepted_guidance",
}
TEMPORAL_STATUSES = {"current", "historical"}
PRIVACY_CLASSES = {"public", "internal", "private", "restricted"}
DISCLOSABLE_PRIVACY_CLASSES = {"public", "internal"}
SOURCE_LIFECYCLE_STATES = {
    "active",
    "stale",
    "expired",
    "contradicted",
    "superseded",
    "retracted",
    "retired",
}
STATES = {
    "eligible",
    "requires_operator_review",
    "awaiting_required_lineage",
    "awaiting_cognitive_lineage",
    "stale_worker",
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
FORBIDDEN_SOURCE_KEYS = {
    "text",
    "content",
    "message",
    "messages",
    "prompt",
    "response",
    "reasoning",
    "reflection_text",
    "memory_text",
    "relationship_text",
    "mood_text",
    "goal_text",
    "motivation_text",
    "evidence_text",
    "provider_payload",
    "payload",
    "source_code",
    "patch_text",
}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,239}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[:limit]


def _digest(*parts: Any) -> str:
    return hashlib.sha256(
        "\x1f".join(_clean(part, 12000) for part in parts).encode("utf-8")
    ).hexdigest()


def _validated_digest(value: Any) -> str:
    token = _clean(value, 64).lower()
    return token if _HEX64.fullmatch(token) else ""


def _identifier(value: Any, limit: int = 240) -> str:
    token = _clean(value, limit)
    return token if _IDENTIFIER.fullmatch(token) else ""


def _parse_time(value: Any) -> datetime | None:
    token = _clean(value, 64)
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _bounded_score(value: Any) -> float:
    return round(max(0.0, min(float(value), 1.0)), 4)


def _bounded_budget(value: Any) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    return {
        "cpu_budget_ms": max(0, int(source.get("cpu_budget_ms") or 0)),
        "memory_budget_mb": max(0, int(source.get("memory_budget_mb") or 0)),
        "latency_budget_ms": max(0, int(source.get("latency_budget_ms") or 0)),
        "token_budget": max(0, int(source.get("token_budget") or 0)),
    }


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
        "records": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


def _source_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -float(row.get("relevance_score") or 0.0),
        str(row.get("source_category") or ""),
        str(row.get("source_id") or ""),
        int(row.get("source_revision") or 0),
        str(row.get("source_digest") or ""),
    )


def _source_lineage_token(row: dict[str, Any]) -> str:
    return _digest(
        row.get("source_category"),
        row.get("source_id"),
        row.get("source_revision"),
        row.get("source_digest"),
    )


def _normalize_source_reference(
    value: Any,
    *,
    session_id: str,
    conversation_id: str,
    reference_time: datetime,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("source reference must be a structural mapping")
    if FORBIDDEN_SOURCE_KEYS.intersection(value):
        raise ValueError("raw source content is not accepted")

    category = _clean(value.get("source_category"), 80)
    source_id = _identifier(value.get("source_id"), 240)
    revision = max(0, int(value.get("source_revision") or 0))
    source_digest = _validated_digest(value.get("source_digest"))
    temporal_status = _clean(value.get("temporal_status"), 32)
    lifecycle_state = _clean(value.get("lifecycle_state"), 32)
    privacy_class = _clean(value.get("privacy_class"), 32)
    relevance_category = _clean(value.get("relevance_category"), 80)
    recorded_at = _parse_time(value.get("recorded_at"))
    expires_at = _parse_time(value.get("expires_at"))
    source_session_id = _identifier(value.get("session_id"), 240)
    source_conversation_id = _identifier(value.get("conversation_id"), 240)
    relationship_boundary = _clean(value.get("relationship_boundary"), 80)

    required_fields_present = bool(
        category in SOURCE_CATEGORIES
        and source_id
        and revision > 0
        and source_digest
        and temporal_status in TEMPORAL_STATUSES
        and lifecycle_state in SOURCE_LIFECYCLE_STATES
        and privacy_class in PRIVACY_CLASSES
        and relevance_category
        and recorded_at
        and expires_at
    )
    mismatch = bool(
        (source_session_id and source_session_id != session_id)
        or (source_conversation_id and source_conversation_id != conversation_id)
    )
    current_history_mismatch = bool(
        (category in CURRENT_ONLY_CATEGORIES and temporal_status != "current")
        or (temporal_status == "historical" and category not in HISTORICAL_ALLOWED_CATEGORIES)
    )
    relationship_identity_mismatch = bool(
        category == "relationship_context" and relationship_boundary != "relationship_only"
    )
    stale = bool(not recorded_at or recorded_at > reference_time or not expires_at or expires_at <= reference_time)
    relevant = _bounded_score(value.get("relevance_score")) > 0.0
    communication_eligible = bool(value.get("communication_eligible"))
    required_exclusion = bool(value.get("required_exclusion"))
    operator_review_required = bool(value.get("operator_review_required"))
    private = privacy_class not in DISCLOSABLE_PRIVACY_CLASSES
    inactive = lifecycle_state != "active"

    exclusion_reasons: list[str] = []
    if not required_fields_present:
        exclusion_reasons.append("missing_or_invalid_lineage")
    if mismatch:
        exclusion_reasons.append("session_or_conversation_mismatch")
    if current_history_mismatch:
        exclusion_reasons.append("current_historical_mismatch")
    if relationship_identity_mismatch:
        exclusion_reasons.append("relationship_identity_boundary")
    if stale:
        exclusion_reasons.append("stale_or_expired")
    if inactive:
        exclusion_reasons.append(f"lifecycle_{lifecycle_state or 'missing'}")
    if private:
        exclusion_reasons.append("private_or_restricted")
    if required_exclusion:
        exclusion_reasons.append("required_exclusion")
    if not relevant:
        exclusion_reasons.append("not_relevant")
    if not communication_eligible:
        exclusion_reasons.append("not_communication_eligible")

    included = not exclusion_reasons
    row = {
        "source_category": category,
        "source_id": source_id,
        "source_revision": revision,
        "source_digest": source_digest,
        "temporal_status": temporal_status,
        "relevance_category": relevance_category,
        "relevance_score": _bounded_score(value.get("relevance_score")),
        "confidence": _bounded_score(value.get("confidence")),
        "uncertainty": _bounded_score(value.get("uncertainty")),
        "recorded_at": _clean(value.get("recorded_at"), 64),
        "expires_at": _clean(value.get("expires_at"), 64),
        "privacy_class": privacy_class,
        "communication_eligible": communication_eligible,
        "required_exclusion": required_exclusion,
        "operator_review_required": operator_review_required,
        "lifecycle_state": lifecycle_state,
        "session_id": source_session_id,
        "conversation_id": source_conversation_id,
        "relationship_boundary": relationship_boundary,
        "relevant": relevant,
        "included": included,
        "exclusion_reasons": sorted(set(exclusion_reasons)),
        "lineage_digest": "",
        "content_free": True,
    }
    row["lineage_digest"] = _source_lineage_token(row)
    return row


class UnifiedConversationalContextEligibilityStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "unified_conversational_context_eligibility.json"
        self.clock = clock or _now

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
        assembly_id: str,
        session_id: str,
        conversation_id: str,
        tab_id: str,
        worker_claim_id: str,
        worker_epoch: int,
        current_worker_epoch: int,
        retry_token_id: str,
        source_references: Iterable[dict[str, Any]],
        budget_limits: dict[str, Any],
        reference_time: str,
        expiry_at: str,
        contradiction_ids: list[str] | None = None,
        retraction_ids: list[str] | None = None,
        supersession_ids: list[str] | None = None,
        retirement_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        event_id = _identifier(event_id, 180)
        assembly_id = _identifier(assembly_id)
        session_id = _identifier(session_id)
        conversation_id = _identifier(conversation_id)
        tab_id = _identifier(tab_id)
        worker_claim_id = _identifier(worker_claim_id)
        retry_token_id = _identifier(retry_token_id)
        if not all((event_id, assembly_id, session_id, conversation_id, tab_id, worker_claim_id, retry_token_id)):
            raise ValueError("bounded event, assembly, session, conversation, tab, worker, and retry lineage required")

        reference_dt = _parse_time(reference_time)
        expiry_dt = _parse_time(expiry_at)
        if not reference_dt or not expiry_dt:
            raise ValueError("valid reference and expiry timestamps required")

        sources = [
            _normalize_source_reference(
                value,
                session_id=session_id,
                conversation_id=conversation_id,
                reference_time=reference_dt,
            )
            for value in source_references
        ]
        if not sources:
            raise ValueError("at least one structural source reference required")

        lineage_keys: dict[tuple[str, str, int], set[str]] = {}
        for row in sources:
            key = (row["source_category"], row["source_id"], row["source_revision"])
            lineage_keys.setdefault(key, set()).add(row["source_digest"])
        contradictory_lineage = any(len(digests) > 1 for digests in lineage_keys.values())
        if contradictory_lineage:
            for row in sources:
                key = (row["source_category"], row["source_id"], row["source_revision"])
                if len(lineage_keys.get(key, set())) > 1:
                    row["included"] = False
                    row["exclusion_reasons"] = sorted(set(row["exclusion_reasons"] + ["contradictory_lineage"]))

        sources.sort(key=_source_sort_key)
        included = [row for row in sources if row["included"]]
        excluded = [row for row in sources if not row["included"]]
        included_categories = {row["source_category"] for row in included}
        all_categories = {row["source_category"] for row in sources}
        required_missing = sorted(REQUIRED_CONTEXT_CATEGORIES - included_categories)
        cognitive_present = bool(COGNITIVE_CONTEXT_CATEGORIES.intersection(included_categories))
        budgets = _bounded_budget(budget_limits)
        budgets_valid = all(value > 0 for value in budgets.values())
        contradictions = sorted({_identifier(value) for value in contradiction_ids or [] if _identifier(value)})
        retractions = sorted({_identifier(value) for value in retraction_ids or [] if _identifier(value)})
        supersessions = sorted({_identifier(value) for value in supersession_ids or [] if _identifier(value)})
        retirements = sorted({_identifier(value) for value in retirement_ids or [] if _identifier(value)})

        state = "eligible"
        reason = "exact_unified_context_lineage"
        if retirements:
            state, reason = "retired", "retirement_lineage"
        elif retractions:
            state, reason = "retracted", "retraction_lineage"
        elif supersessions:
            state, reason = "superseded", "supersession_lineage"
        elif contradictions or contradictory_lineage:
            state, reason = "suppressed", "contradictory_lineage"
        elif int(worker_epoch) != int(current_worker_epoch):
            state, reason = "stale_worker", "current_worker_epoch_required"
        elif expiry_dt <= reference_dt:
            state, reason = "expired", "eligibility_window_expired"
        elif required_missing or not budgets_valid:
            state, reason = "awaiting_required_lineage", "required_constraint_lineage_missing"
        elif not cognitive_present:
            state, reason = "awaiting_cognitive_lineage", "current_cognitive_lineage_required"
        elif any(row["operator_review_required"] for row in included):
            state, reason = "requires_operator_review", "included_lineage_requires_operator_review"

        source_manifest_digest = _digest(*[row["lineage_digest"] for row in sources])
        context_set_digest = _digest(
            session_id,
            conversation_id,
            source_manifest_digest,
            *budgets.values(),
            reference_time,
            expiry_at,
        )
        structural_digest = _digest(
            assembly_id,
            context_set_digest,
            tab_id,
            worker_claim_id,
            worker_epoch,
            current_worker_epoch,
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
            retry = next(
                (row for row in persisted["processed_events"] if row.get("retry_token_id") == retry_token_id),
                None,
            )
            if retry:
                result = {
                    "status": "duplicate_retry_suppressed",
                    "eligibility_id": retry["result"].get("eligibility_id", ""),
                    "state": "suppressed",
                }
            else:
                cross_tab = next(
                    (
                        row
                        for row in persisted["records"]
                        if row.get("context_set_digest") == context_set_digest
                        and row.get("tab_id") != tab_id
                        and row.get("state") in {"eligible", "requires_operator_review"}
                    ),
                    None,
                )
                duplicate = next(
                    (
                        row
                        for row in persisted["records"]
                        if row.get("structural_digest") == structural_digest
                        and row.get("state")
                        in {
                            "eligible",
                            "requires_operator_review",
                            "awaiting_required_lineage",
                            "awaiting_cognitive_lineage",
                            "stale_worker",
                        }
                    ),
                    None,
                )
                if cross_tab:
                    result = {
                        "status": "cross_tab_duplicate_suppressed",
                        "eligibility_id": cross_tab["eligibility_id"],
                        "state": "suppressed",
                    }
                elif duplicate:
                    result = {
                        "status": "duplicate_context_suppressed",
                        "eligibility_id": duplicate["eligibility_id"],
                        "state": "suppressed",
                    }
                else:
                    now = self.clock()
                    eligibility_id = f"unified-context-eligibility-{structural_digest[:24]}"
                    row = {
                        "eligibility_id": eligibility_id,
                        "assembly_id": assembly_id,
                        "session_id": session_id,
                        "conversation_id": conversation_id,
                        "tab_id": tab_id,
                        "worker_claim_id": worker_claim_id,
                        "worker_epoch": int(worker_epoch),
                        "current_worker_epoch": int(current_worker_epoch),
                        "retry_token_id_digest": _digest(retry_token_id),
                        "source_lineage": sources,
                        "source_manifest_digest": source_manifest_digest,
                        "context_set_digest": context_set_digest,
                        "source_count": len(sources),
                        "eligible_source_ids": [row["source_id"] for row in included],
                        "excluded_source_ids": [row["source_id"] for row in excluded],
                        "included_categories": sorted(included_categories),
                        "excluded_categories": sorted(all_categories - included_categories),
                        "current_source_ids": [row["source_id"] for row in sources if row["temporal_status"] == "current"],
                        "historical_source_ids": [row["source_id"] for row in sources if row["temporal_status"] == "historical"],
                        "required_missing_categories": required_missing,
                        "budget_limits": budgets,
                        "reference_time": _clean(reference_time, 64),
                        "expiry_at": _clean(expiry_at, 64),
                        "communication_eligible": state in {"eligible", "requires_operator_review"},
                        "operator_review_required": any(row["operator_review_required"] for row in included),
                        "contradiction_ids": contradictions,
                        "retraction_ids": retractions,
                        "supersession_ids": supersessions,
                        "retirement_ids": retirements,
                        "state": state,
                        "state_reason": reason,
                        "structural_digest": structural_digest,
                        "content_free": True,
                        "provider_contacted": False,
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
                    persisted["records"].append(row)
                    result = {
                        "status": "eligibility_recorded",
                        "eligibility_id": eligibility_id,
                        "state": state,
                    }

            now = self.clock()
            persisted["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_digest": _digest(event_id),
                    "retry_token_id": retry_token_id,
                    "retry_token_digest": _digest(retry_token_id),
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
        for row in state["records"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "eligibility_id",
            "assembly_id",
            "session_id",
            "conversation_id",
            "tab_id",
            "worker_claim_id",
            "worker_epoch",
            "current_worker_epoch",
            "source_lineage",
            "source_manifest_digest",
            "context_set_digest",
            "source_count",
            "eligible_source_ids",
            "excluded_source_ids",
            "included_categories",
            "excluded_categories",
            "current_source_ids",
            "historical_source_ids",
            "required_missing_categories",
            "budget_limits",
            "reference_time",
            "expiry_at",
            "communication_eligible",
            "operator_review_required",
            "contradiction_ids",
            "retraction_ids",
            "supersession_ids",
            "retirement_ids",
            "state",
            "state_reason",
            "structural_digest",
            "provider_contacted",
            "conversation_generated",
            "message_sent",
            "cognition_mutated",
            "conversation_mutated",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["records"]),
            "state_counts": counts,
            "recent_records": [
                {key: deepcopy(row.get(key)) for key in keys} for row in state["records"][-32:]
            ],
            "recognized_source_categories": sorted(SOURCE_CATEGORIES),
            "cognitive_context_categories": sorted(COGNITIVE_CONTEXT_CATEGORIES),
            "required_context_categories": sorted(REQUIRED_CONTEXT_CATEGORIES),
            "current_only_categories": sorted(CURRENT_ONLY_CATEGORIES),
            "historical_allowed_categories": sorted(HISTORICAL_ALLOWED_CATEGORIES),
            "recognized_privacy_classes": sorted(PRIVACY_CLASSES),
            "recognized_lifecycle_states": sorted(SOURCE_LIFECYCLE_STATES),
            "suppression_controls": {
                "duplicate_retry": True,
                "duplicate_context": True,
                "stale_worker": True,
                "cross_tab_duplicate": True,
            },
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
            "conversation_generated": False,
            "message_sent": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
        }


def build_unified_conversational_context_eligibility_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return UnifiedConversationalContextEligibilityStore(runtime_root).inspection_summary()
