from __future__ import annotations

"""v1145.4 exact provider-context assembly and bounded local generation.

The execution seam consumes one exact v1145.3 generation-eligible arbitration.
Raw context and generated output exist only in the in-memory provider call and
return value. Durable records contain identifiers, digests, counts, budgets,
usage, lifecycle, cancellation, timeout, and exact lineage only. A completed
output is never delivered or committed to conversation by this module.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from conversation_cognition_communication_arbitration import ConversationCognitionCommunicationArbitrationStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from unified_context_candidates import UnifiedContextCandidateStore
from unified_conversational_context_eligibility import _clean, _identifier
from workload_coordination_continuity import WorkloadCoordinationContinuityStore
from workload_live_arbitration import WorkloadLiveArbitrationStore

CONTRACT_VERSION = "v1145.4"
SCHEMA_VERSION = "1"
STATES = {
    "running",
    "cancellation_requested",
    "completed",
    "cancelled",
    "timed_out",
    "budget_exhausted",
    "context_rejected",
    "provider_rejected",
    "provider_failed",
    "stale_worker",
    "stale_arbitration",
    "duplicate_suppressed",
    "retired",
}
TERMINAL_STATES = {
    "completed",
    "cancelled",
    "timed_out",
    "budget_exhausted",
    "context_rejected",
    "provider_rejected",
    "provider_failed",
    "stale_worker",
    "stale_arbitration",
    "duplicate_suppressed",
    "retired",
}
AUTHORITY_KEYS = (
    "can_send_message",
    "can_create_notification",
    "can_commit_generated_output",
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

_ACTIVE_CANCEL_EVENTS: dict[str, threading.Event] = {}
_ACTIVE_CANCEL_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_text(value: str) -> str:
    return _digest_bytes(value.encode("utf-8"))


def _digest(*parts: Any) -> str:
    return hashlib.sha256(
        "\x1f".join(_clean(part, 12000) for part in parts).encode("utf-8")
    ).hexdigest()


def _estimate_tokens(value: str) -> int:
    return max(1, int(math.ceil(len(value.encode("utf-8")) / 4.0)))


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
        "receipts": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "controls": {
            "maximum_records": 1024,
            "maximum_context_characters": 120000,
            "minimum_timeout_ms": 1,
            "cancellation_grace_ms": 100,
        },
        "authority_boundary": {key: False for key in AUTHORITY_KEYS},
    }


@runtime_checkable
class BoundedGenerationProvider(Protocol):
    profile_id: str
    profile_digest: str

    def generate(
        self,
        prompt: str,
        *,
        cancel_event: threading.Event,
        max_tokens: int,
        timeout_ms: int,
    ) -> str:
        ...


class ConfiguredLocalModelProvider:
    """Adapter for Eidolon's configured local-model provider seam."""

    def __init__(self, profile_id: str) -> None:
        self.profile_id = _identifier(profile_id)
        if not self.profile_id:
            raise ValueError("exact configured provider profile identifier required")
        from settings_manager import load_settings
        from local_model import LocalModelConfig

        self._config = LocalModelConfig.from_settings(load_settings())
        generation = self._config.generation
        profile = {
            "provider": self._config.provider,
            "endpoint": self._config.endpoint,
            "model": self._config.model,
            "context_size": self._config.context_size,
            "connect_timeout_seconds": self._config.connect_timeout_seconds,
            "read_timeout_seconds": self._config.read_timeout_seconds,
            "retry_limit": self._config.retry_limit,
            "retry_delay_seconds": self._config.retry_delay_seconds,
            "generation": {
                "temperature": generation.temperature,
                "top_p": generation.top_p,
                "top_k": generation.top_k,
                "repeat_penalty": generation.repeat_penalty,
                "seed": generation.seed,
                "stop": list(generation.stop),
            },
        }
        self.profile_digest = _digest_text(json.dumps(profile, sort_keys=True, separators=(",", ":")))

    def generate(
        self,
        prompt: str,
        *,
        cancel_event: threading.Event,
        max_tokens: int,
        timeout_ms: int,
    ) -> str:
        del timeout_ms  # Wall-clock enforcement is owned by the bounded executor.
        from local_model import LocalModelClient

        config = self._config.with_generation(max_tokens=max_tokens)
        with LocalModelClient(config, cancel_event=cancel_event) as client:
            return client.generate(prompt)


def configured_local_provider_profile_digest() -> str:
    """Return the exact configured provider profile digest without contacting it."""
    return ConfiguredLocalModelProvider("configured-local-model").profile_digest


class ConversationCognitionBoundedGenerationStore:
    def __init__(
        self,
        runtime_root: Path | str | None = None,
        *,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else _root()
        self.path = self.runtime_root / "conversation_cognition_bounded_generation.json"
        self.clock = clock or _now
        self.arbitrations = ConversationCognitionCommunicationArbitrationStore(self.runtime_root)
        self.candidates = UnifiedContextCandidateStore(self.runtime_root)
        self.workloads = WorkloadLiveArbitrationStore(self.runtime_root)
        self.continuity = WorkloadCoordinationContinuityStore(self.runtime_root)

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default(), expected_type=dict)
        for key, value in _default().items():
            state.setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _active_key(self, operation_id: str) -> str:
        return f"{self.path}:{operation_id}"

    def _set_active_event(self, operation_id: str, event: threading.Event | None) -> None:
        key = self._active_key(operation_id)
        with _ACTIVE_CANCEL_LOCK:
            if event is None:
                _ACTIVE_CANCEL_EVENTS.pop(key, None)
            else:
                _ACTIVE_CANCEL_EVENTS[key] = event

    def _get_active_event(self, operation_id: str) -> threading.Event | None:
        with _ACTIVE_CANCEL_LOCK:
            return _ACTIVE_CANCEL_EVENTS.get(self._active_key(operation_id))

    def _persist_terminal(
        self,
        operation_id: str,
        *,
        state_name: str,
        reason_code: str,
        updates: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            row = next((item for item in state["receipts"] if item.get("operation_id") == operation_id), None)
            if not row:
                raise ValueError("exact generation operation receipt required")
            row["state"] = state_name
            row["reason_code"] = _clean(reason_code, 120)
            row["completed_at"] = self.clock()
            for key, value in (updates or {}).items():
                row[key] = deepcopy(value)
            row.setdefault("history", []).append(
                {
                    "change": "generation_finalized",
                    "state": state_name,
                    "reason_code": _clean(reason_code, 120),
                    "occurred_at": row["completed_at"],
                    "content_free": True,
                }
            )
            row["structural_digest"] = _digest(
                row.get("operation_id"),
                row.get("arbitration_id"),
                row.get("candidate_id"),
                row.get("provider_profile_id"),
                row.get("provider_profile_digest"),
                row.get("context_set_digest"),
                row.get("prompt_digest"),
                row.get("response_digest"),
                state_name,
                reason_code,
                row.get("input_token_estimate"),
                row.get("output_token_estimate"),
                row.get("latency_used_ms"),
                row.get("cpu_used_ms"),
                row.get("memory_estimate_mb"),
            )
            final_status = {
                "completed": "generation_completed",
                "cancelled": "generation_cancelled",
                "timed_out": "generation_timed_out",
                "budget_exhausted": "generation_budget_exhausted",
                "provider_failed": "generation_failed",
            }.get(state_name, "generation_finished")
            for event in state["processed_events"]:
                result = event.get("result") or {}
                if event.get("event_kind") == "generation" and result.get("operation_id") == operation_id:
                    event["result"] = {
                        "status": final_status,
                        "receipt_id": row.get("receipt_id"),
                        "operation_id": operation_id,
                        "state": state_name,
                        "reason_code": _clean(reason_code, 120),
                    }
            state["revision"] += 1
            state["updated_at"] = row["completed_at"]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return deepcopy(row)

    def _record_immediate_terminal(
        self,
        event_id: str,
        *,
        operation_id: str,
        arbitration: Mapping[str, Any],
        arbitration_revision: int,
        observed_arbitration_revision: int | None,
        worker_claim_id: str,
        worker_epoch: int,
        current_worker_epoch: int,
        state_name: str,
        reason_code: str,
        provider: BoundedGenerationProvider | None = None,
    ) -> dict[str, Any]:
        now = self.clock()
        receipt_id = f"conversation-cognition-generation-{_digest(operation_id, arbitration.get('arbitration_id'))[:24]}"
        row = {
            "receipt_id": receipt_id,
            "operation_id": operation_id,
            "arbitration_id": arbitration.get("arbitration_id"),
            "arbitration_store_revision": arbitration_revision,
            "observed_arbitration_revision": observed_arbitration_revision,
            "arbitration_structural_digest": arbitration.get("structural_digest"),
            "candidate_id": arbitration.get("candidate_id"),
            "candidate_structural_digest": arbitration.get("candidate_structural_digest"),
            "eligibility_id": arbitration.get("eligibility_id"),
            "session_id": arbitration.get("session_id"),
            "conversation_id": arbitration.get("conversation_id"),
            "workload_arbitration_id": arbitration.get("workload_arbitration_id"),
            "workload_arbitration_digest": arbitration.get("workload_arbitration_digest"),
            "workload_continuity_id": "",
            "workload_continuity_state": "",
            "provider_profile_id": getattr(provider, "profile_id", arbitration.get("provider_profile_id")),
            "provider_profile_digest": getattr(provider, "profile_digest", ""),
            "context_set_digest": "",
            "source_count": len(arbitration.get("included_source_ids") or []),
            "source_lineage_digest": "",
            "prompt_digest": "",
            "prompt_character_count": 0,
            "input_token_estimate": 0,
            "maximum_output_tokens": 0,
            "response_digest": "",
            "response_character_count": 0,
            "output_token_estimate": 0,
            "budget_limits": deepcopy(arbitration.get("budget_limits") or {}),
            "latency_used_ms": 0,
            "cpu_used_ms": 0,
            "memory_estimate_mb": 0,
            "worker_claim_id": worker_claim_id,
            "worker_epoch": max(0, int(worker_epoch)),
            "current_worker_epoch": max(0, int(current_worker_epoch)),
            "context_assembled": False,
            "provider_contacted": False,
            "generation_completed": False,
            "cancellation_requested": state_name == "cancelled",
            "timeout_observed": state_name == "timed_out",
            "state": state_name,
            "reason_code": reason_code,
            "message_sent": False,
            "notification_created": False,
            "generated_output_committed": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
            "content_free": True,
            "created_at": now,
            "completed_at": now,
            "structural_digest": "",
            "history": [
                {
                    "change": "generation_rejected",
                    "state": state_name,
                    "reason_code": reason_code,
                    "occurred_at": now,
                    "content_free": True,
                }
            ],
        }
        row["structural_digest"] = _digest(operation_id, arbitration.get("arbitration_id"), state_name, reason_code)
        result = {
            "status": "generation_not_started",
            "receipt_id": receipt_id,
            "operation_id": operation_id,
            "state": state_name,
            "reason_code": reason_code,
            "generated_text": "",
        }
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((item for item in state["processed_events"] if item.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}
            state["receipts"].append(row)
            state["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_kind": "generation",
                    "occurred_at": now,
                    "result": {key: value for key, value in result.items() if key != "generated_text"},
                    "content_free": True,
                }
            )
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
        return {"ok": True, **result, "idempotent": False}

    def _resolve_context(
        self,
        candidate: Mapping[str, Any],
        source_resolver: Mapping[str, str] | Callable[[Mapping[str, Any]], str],
    ) -> tuple[str, dict[str, Any]]:
        lineage = list(candidate.get("included_source_lineage") or [])
        ordered_ids = list(candidate.get("relevance_order") or candidate.get("included_source_ids") or [])
        by_id = {str(row.get("source_id")): row for row in lineage}
        if set(by_id) != set(ordered_ids) or len(by_id) != len(ordered_ids):
            raise ValueError("candidate source lineage does not exactly match relevance order")
        if isinstance(source_resolver, Mapping):
            supplied = {str(key) for key in source_resolver}
            if supplied != set(ordered_ids):
                raise ValueError("provider context source set must match the exact candidate set")

        sections: list[str] = []
        lineage_tokens: list[str] = []
        for source_id in ordered_ids:
            row = by_id[source_id]
            value = source_resolver[source_id] if isinstance(source_resolver, Mapping) else source_resolver(row)
            if not isinstance(value, str) or not value:
                raise ValueError("every exact source reference must resolve to non-empty text in memory")
            if _digest_text(value) != str(row.get("source_digest") or ""):
                raise ValueError("resolved source digest does not match exact candidate lineage")
            category = _clean(row.get("source_category"), 80)
            revision = max(0, int(row.get("source_revision") or 0))
            sections.extend(
                [
                    f"[CONTEXT category={category} id={source_id} revision={revision}]",
                    value,
                    "[/CONTEXT]",
                ]
            )
            lineage_tokens.append(
                _digest(category, source_id, revision, row.get("source_digest"), row.get("lineage_digest"))
            )

        prompt = "\n".join(
            [
                "EIDOLON_UNIFIED_CONVERSATION_CONTEXT_V1",
                f"SESSION_ID={candidate.get('session_id')}",
                f"CONVERSATION_ID={candidate.get('conversation_id')}",
                f"COMMUNICATION_POLICY_ID={candidate.get('communication_policy_id')}",
                f"PRIVACY_POLICY_IDS={','.join(candidate.get('privacy_policy_ids') or [])}",
                *sections,
                "GENERATE_ONE_BOUNDED_CONVERSATIONAL_OUTPUT",
            ]
        )
        metadata = {
            "context_set_digest": _digest(*ordered_ids, *lineage_tokens),
            "source_count": len(ordered_ids),
            "source_lineage_digest": _digest(*lineage_tokens),
            "prompt_digest": _digest_text(prompt),
            "prompt_character_count": len(prompt),
            "input_token_estimate": _estimate_tokens(prompt),
        }
        return prompt, metadata

    def execute(
        self,
        event_id: str,
        *,
        operation_id: str,
        arbitration_id: str,
        observed_arbitration_revision: int | None,
        worker_claim_id: str,
        worker_epoch: int,
        current_worker_epoch: int,
        source_resolver: Mapping[str, str] | Callable[[Mapping[str, Any]], str],
        provider: BoundedGenerationProvider | None = None,
        maximum_output_tokens: int = 128,
        timeout_ms: int | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        event_id = _identifier(event_id, 180)
        operation_id = _identifier(operation_id)
        arbitration_id = _identifier(arbitration_id)
        worker_claim_id = _identifier(worker_claim_id)
        if not all((event_id, operation_id, arbitration_id, worker_claim_id)):
            raise ValueError("bounded event, operation, arbitration, and worker lineage required")

        early = self._load()
        prior = next((item for item in early["processed_events"] if item.get("event_id") == event_id), None)
        if prior:
            return {"ok": True, **deepcopy(prior["result"]), "generated_text": "", "idempotent": True}

        arbitration_state = self.arbitrations.snapshot()
        arbitration = next(
            (row for row in arbitration_state.get("arbitrations", []) if row.get("arbitration_id") == arbitration_id),
            None,
        )
        if not arbitration:
            raise ValueError("exact v1145.3 communication arbitration required")
        exact_arbitration_revision = int(arbitration.get("arbitration_revision") or 0)
        if exact_arbitration_revision <= 0:
            raise ValueError("exact arbitration record revision required")

        if int(worker_epoch) != int(current_worker_epoch):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="stale_worker",
                reason_code="current_worker_epoch_required",
                provider=provider,
            )
        if observed_arbitration_revision is None or int(observed_arbitration_revision) != exact_arbitration_revision:
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="stale_arbitration",
                reason_code="arbitration_revision_changed",
                provider=provider,
            )
        if arbitration.get("outcome") != "generation_eligible" or not arbitration.get("generation_eligible"):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="provider_rejected",
                reason_code="arbitration_not_generation_eligible",
                provider=provider,
            )

        candidate_state = self.candidates.snapshot()
        candidate = next(
            (row for row in candidate_state.get("candidates", []) if row.get("candidate_id") == arbitration.get("candidate_id")),
            None,
        )
        if not candidate or candidate.get("structural_digest") != arbitration.get("candidate_structural_digest"):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="stale_arbitration",
                reason_code="candidate_lineage_changed",
                provider=provider,
            )

        workload = next(
            (
                row
                for row in self.workloads.snapshot().get("arbitrations", [])
                if row.get("arbitration_id") == arbitration.get("workload_arbitration_id")
            ),
            None,
        )
        if (
            not workload
            or workload.get("state") != "admitted"
            or workload.get("structural_digest") != arbitration.get("workload_arbitration_digest")
        ):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="provider_rejected",
                reason_code="exact_workload_admission_changed",
                provider=provider,
            )

        resolved_provider = provider or ConfiguredLocalModelProvider(str(arbitration.get("provider_profile_id") or ""))
        if not isinstance(resolved_provider, BoundedGenerationProvider):
            raise ValueError("bounded generation provider contract required")
        provider_lineage = next(
            (
                row
                for row in candidate.get("included_source_lineage") or []
                if row.get("source_id") == candidate.get("provider_profile_id")
            ),
            None,
        )
        if (
            resolved_provider.profile_id != candidate.get("provider_profile_id")
            or not provider_lineage
            or resolved_provider.profile_digest != provider_lineage.get("source_digest")
        ):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="provider_rejected",
                reason_code="provider_profile_lineage_mismatch",
                provider=resolved_provider,
            )

        try:
            prompt, context = self._resolve_context(candidate, source_resolver)
        except (KeyError, TypeError, ValueError):
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="context_rejected",
                reason_code="exact_context_resolution_failed",
                provider=resolved_provider,
            )

        controls = self._load().get("controls") or _default()["controls"]
        budget = arbitration.get("budget_limits") or {}
        token_budget = max(0, int(budget.get("token_budget") or 0))
        output_budget = max(0, min(int(maximum_output_tokens), token_budget - int(context["input_token_estimate"])))
        maximum_characters = max(1, int(controls.get("maximum_context_characters") or 120000))
        if context["prompt_character_count"] > maximum_characters or output_budget <= 0:
            return self._record_immediate_terminal(
                event_id,
                operation_id=operation_id,
                arbitration=arbitration,
                arbitration_revision=exact_arbitration_revision,
                observed_arbitration_revision=observed_arbitration_revision,
                worker_claim_id=worker_claim_id,
                worker_epoch=worker_epoch,
                current_worker_epoch=current_worker_epoch,
                state_name="budget_exhausted",
                reason_code="context_or_output_token_budget_exhausted",
                provider=resolved_provider,
            )

        latency_budget_ms = max(1, int(budget.get("latency_budget_ms") or 1))
        effective_timeout_ms = max(
            int(controls.get("minimum_timeout_ms") or 1),
            min(latency_budget_ms, int(timeout_ms) if timeout_ms is not None else latency_budget_ms),
        )
        receipt_id = f"conversation-cognition-generation-{_digest(operation_id, arbitration_id)[:24]}"
        now = self.clock()
        row = {
            "receipt_id": receipt_id,
            "operation_id": operation_id,
            "arbitration_id": arbitration_id,
            "arbitration_store_revision": exact_arbitration_revision,
            "observed_arbitration_revision": observed_arbitration_revision,
            "arbitration_structural_digest": arbitration.get("structural_digest"),
            "candidate_id": candidate.get("candidate_id"),
            "candidate_structural_digest": candidate.get("structural_digest"),
            "eligibility_id": candidate.get("eligibility_id"),
            "session_id": candidate.get("session_id"),
            "conversation_id": candidate.get("conversation_id"),
            "workload_arbitration_id": arbitration.get("workload_arbitration_id"),
            "workload_arbitration_digest": arbitration.get("workload_arbitration_digest"),
            "workload_continuity_id": "",
            "workload_continuity_state": "",
            "provider_profile_id": resolved_provider.profile_id,
            "provider_profile_digest": resolved_provider.profile_digest,
            **context,
            "maximum_output_tokens": output_budget,
            "response_digest": "",
            "response_character_count": 0,
            "output_token_estimate": 0,
            "budget_limits": deepcopy(budget),
            "latency_used_ms": 0,
            "cpu_used_ms": 0,
            "memory_estimate_mb": max(1, int(math.ceil(len(prompt.encode("utf-8")) / (1024 * 1024)))),
            "worker_claim_id": worker_claim_id,
            "worker_epoch": max(0, int(worker_epoch)),
            "current_worker_epoch": max(0, int(current_worker_epoch)),
            "context_assembled": True,
            "provider_contacted": False,
            "generation_completed": False,
            "cancellation_requested": bool(cancel_event and cancel_event.is_set()),
            "timeout_observed": False,
            "state": "running",
            "reason_code": "bounded_provider_generation_started",
            "message_sent": False,
            "notification_created": False,
            "generated_output_committed": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
            "content_free": True,
            "created_at": now,
            "completed_at": "",
            "structural_digest": _digest(operation_id, arbitration_id, context["prompt_digest"], "running"),
            "history": [
                {
                    "change": "generation_started",
                    "state": "running",
                    "occurred_at": now,
                    "content_free": True,
                }
            ],
        }
        initial_result = {
            "status": "generation_started",
            "receipt_id": receipt_id,
            "operation_id": operation_id,
            "state": "running",
            "reason_code": "bounded_provider_generation_started",
        }
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((item for item in state["processed_events"] if item.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "generated_text": "", "idempotent": True}
            duplicate = next(
                (
                    item
                    for item in state["receipts"]
                    if item.get("arbitration_id") == arbitration_id
                    and item.get("state") in {"running", "cancellation_requested", "completed"}
                ),
                None,
            )
            if duplicate:
                duplicate_receipt_id = f"conversation-cognition-generation-{_digest(operation_id, arbitration_id, 'duplicate')[:24]}"
                duplicate_row = deepcopy(row)
                duplicate_row.update({
                    "receipt_id": duplicate_receipt_id,
                    "operation_id": operation_id,
                    "duplicate_of_receipt_id": duplicate.get("receipt_id"),
                    "provider_contacted": False,
                    "generation_completed": False,
                    "state": "duplicate_suppressed",
                    "reason_code": "exact_arbitration_already_consumed",
                    "completed_at": now,
                    "structural_digest": _digest(operation_id, arbitration_id, duplicate.get("receipt_id"), "duplicate_suppressed"),
                    "history": [{
                        "change": "duplicate_generation_suppressed",
                        "state": "duplicate_suppressed",
                        "occurred_at": now,
                        "content_free": True,
                    }],
                })
                state["receipts"].append(duplicate_row)
                result = {
                    "status": "duplicate_generation_suppressed",
                    "receipt_id": duplicate_receipt_id,
                    "operation_id": operation_id,
                    "state": "duplicate_suppressed",
                    "reason_code": "exact_arbitration_already_consumed",
                }
                state["processed_events"].append(
                    {
                        "event_id": event_id,
                        "event_kind": "generation",
                        "occurred_at": now,
                        "result": deepcopy(result),
                        "content_free": True,
                    }
                )
                state["revision"] += 1
                state["updated_at"] = now
                write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
                return {"ok": True, **result, "generated_text": "", "idempotent": False}
            state["receipts"].append(row)
            state["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_kind": "generation",
                    "occurred_at": now,
                    "result": deepcopy(initial_result),
                    "content_free": True,
                }
            )
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)

        active_cancel = cancel_event or threading.Event()
        self._set_active_event(operation_id, active_cancel)
        if active_cancel.is_set():
            final = self._persist_terminal(
                operation_id,
                state_name="cancelled",
                reason_code="cancellation_requested_before_provider_contact",
                updates={"cancellation_requested": True},
            )
            self._set_active_event(operation_id, None)
            return {
                "ok": True,
                "status": "generation_cancelled",
                "receipt_id": final["receipt_id"],
                "operation_id": operation_id,
                "state": "cancelled",
                "reason_code": final["reason_code"],
                "generated_text": "",
                "idempotent": False,
            }

        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            live = next(item for item in state["receipts"] if item.get("operation_id") == operation_id)
            live["provider_contacted"] = True
            live["history"].append(
                {
                    "change": "provider_contact_started",
                    "occurred_at": self.clock(),
                    "content_free": True,
                }
            )
            state["revision"] += 1
            state["updated_at"] = self.clock()
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)

        started_wall = time.perf_counter_ns()
        started_cpu = time.process_time_ns()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eidolon-v1145-generation")
        future = executor.submit(
            resolved_provider.generate,
            prompt,
            cancel_event=active_cancel,
            max_tokens=output_budget,
            timeout_ms=effective_timeout_ms,
        )
        generated = ""
        state_name = "provider_failed"
        reason_code = "provider_generation_failed"
        error_code = ""
        try:
            generated = str(future.result(timeout=effective_timeout_ms / 1000.0))
            latest = next(
                (
                    item
                    for item in self._load().get("receipts", [])
                    if item.get("operation_id") == operation_id
                ),
                {},
            )
            if active_cancel.is_set() or latest.get("cancellation_requested"):
                state_name, reason_code, generated = "cancelled", "exact_cancellation_won", ""
            elif not generated:
                state_name, reason_code = "provider_failed", "empty_provider_output"
            else:
                state_name, reason_code = "completed", "bounded_generation_completed"
        except FutureTimeoutError:
            active_cancel.set()
            future.cancel()
            state_name, reason_code = "timed_out", "bounded_latency_timeout"
        except Exception as error:  # Provider errors are reduced to structural type codes.
            error_code = _clean(type(error).__name__, 80)
            if active_cancel.is_set() or "cancel" in error_code.lower():
                state_name, reason_code = "cancelled", "provider_observed_cancellation"
            elif "timeout" in error_code.lower():
                state_name, reason_code = "timed_out", "provider_timeout"
            else:
                state_name, reason_code = "provider_failed", "provider_error"
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            self._set_active_event(operation_id, None)

        latency_ms = max(0, int((time.perf_counter_ns() - started_wall) / 1_000_000))
        cpu_ms = max(0, int((time.process_time_ns() - started_cpu) / 1_000_000))
        response_chars = len(generated)
        output_tokens = _estimate_tokens(generated) if generated else 0
        memory_estimate_mb = max(
            1,
            int(math.ceil((len(prompt.encode("utf-8")) + len(generated.encode("utf-8"))) / (1024 * 1024))),
        )
        over_budget = bool(
            cpu_ms > int(budget.get("cpu_budget_ms") or 0)
            or latency_ms > int(budget.get("latency_budget_ms") or 0)
            or memory_estimate_mb > int(budget.get("memory_budget_mb") or 0)
            or int(context["input_token_estimate"]) + output_tokens > token_budget
            or output_tokens > output_budget
        )
        if state_name == "completed" and over_budget:
            state_name, reason_code, generated = "budget_exhausted", "measured_generation_budget_exceeded", ""

        action = {
            "completed": "complete",
            "cancelled": "cancel",
            "timed_out": "timeout",
            "budget_exhausted": "run",
        }.get(state_name, "yield")
        continuity_result = self.continuity.register(
            f"generation-continuity-{_digest(operation_id, state_name)[:24]}",
            arbitration_id=str(arbitration.get("workload_arbitration_id") or ""),
            continuity_key=operation_id,
            worker_claim_id=worker_claim_id,
            restart_epoch=max(0, int(current_worker_epoch)),
            action=action,
            cpu_used_ms=cpu_ms,
            memory_peak_mb=memory_estimate_mb,
            latency_used_ms=latency_ms,
            tokens_used=int(context["input_token_estimate"]) + output_tokens,
        )

        response_digest = _digest_text(generated) if generated else ""
        final = self._persist_terminal(
            operation_id,
            state_name=state_name,
            reason_code=reason_code,
            updates={
                "response_digest": response_digest,
                "response_character_count": response_chars if response_digest else 0,
                "output_token_estimate": output_tokens if response_digest else 0,
                "latency_used_ms": latency_ms,
                "cpu_used_ms": cpu_ms,
                "memory_estimate_mb": memory_estimate_mb,
                "generation_completed": state_name == "completed",
                "cancellation_requested": state_name == "cancelled",
                "timeout_observed": state_name == "timed_out",
                "provider_error_code": error_code,
                "workload_continuity_id": continuity_result.get("continuity_id", ""),
                "workload_continuity_state": continuity_result.get("state", ""),
            },
        )
        status = {
            "completed": "generation_completed",
            "cancelled": "generation_cancelled",
            "timed_out": "generation_timed_out",
            "budget_exhausted": "generation_budget_exhausted",
            "provider_failed": "generation_failed",
        }.get(state_name, "generation_finished")
        return {
            "ok": state_name == "completed",
            "status": status,
            "receipt_id": final["receipt_id"],
            "operation_id": operation_id,
            "state": state_name,
            "reason_code": reason_code,
            "generated_text": generated if state_name == "completed" else "",
            "idempotent": False,
        }

    def request_cancellation(self, event_id: str, *, operation_id: str) -> dict[str, Any]:
        event_id = _identifier(event_id, 180)
        operation_id = _identifier(operation_id)
        if not event_id or not operation_id:
            raise ValueError("bounded cancellation event and exact operation required")
        with metadata_mutation_lock(self.path, timeout_seconds=5):
            state = self._load()
            prior = next((item for item in state["processed_events"] if item.get("event_id") == event_id), None)
            if prior:
                return {"ok": True, **deepcopy(prior["result"]), "idempotent": True}
            row = next((item for item in state["receipts"] if item.get("operation_id") == operation_id), None)
            if not row:
                result = {"status": "operation_not_found", "operation_id": operation_id, "state": "not_found"}
            elif row.get("state") in TERMINAL_STATES:
                result = {
                    "status": "operation_already_terminal",
                    "operation_id": operation_id,
                    "state": row.get("state"),
                }
            else:
                row["cancellation_requested"] = True
                row["state"] = "cancellation_requested"
                row["reason_code"] = "exact_cancellation_requested"
                row.setdefault("history", []).append(
                    {
                        "change": "cancellation_requested",
                        "occurred_at": self.clock(),
                        "content_free": True,
                    }
                )
                result = {
                    "status": "cancellation_requested",
                    "operation_id": operation_id,
                    "state": "cancellation_requested",
                }
            now = self.clock()
            state["processed_events"].append(
                {
                    "event_id": event_id,
                    "event_kind": "cancellation",
                    "occurred_at": now,
                    "result": deepcopy(result),
                    "content_free": True,
                }
            )
            state["revision"] += 1
            state["updated_at"] = now
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
        active = self._get_active_event(operation_id)
        if active is not None and result.get("status") == "cancellation_requested":
            active.set()
        return {"ok": result.get("status") != "operation_not_found", **result, "idempotent": False}

    def inspection_summary(self) -> dict[str, Any]:
        state = self._load()
        counts: dict[str, int] = {}
        for row in state["receipts"]:
            counts[row.get("state")] = counts.get(row.get("state"), 0) + 1
        keys = (
            "receipt_id",
            "operation_id",
            "duplicate_of_receipt_id",
            "arbitration_id",
            "arbitration_store_revision",
            "observed_arbitration_revision",
            "arbitration_structural_digest",
            "candidate_id",
            "candidate_structural_digest",
            "eligibility_id",
            "session_id",
            "conversation_id",
            "workload_arbitration_id",
            "workload_arbitration_digest",
            "workload_continuity_id",
            "workload_continuity_state",
            "provider_profile_id",
            "provider_profile_digest",
            "context_set_digest",
            "source_count",
            "source_lineage_digest",
            "prompt_digest",
            "prompt_character_count",
            "input_token_estimate",
            "maximum_output_tokens",
            "response_digest",
            "response_character_count",
            "output_token_estimate",
            "budget_limits",
            "latency_used_ms",
            "cpu_used_ms",
            "memory_estimate_mb",
            "worker_claim_id",
            "worker_epoch",
            "current_worker_epoch",
            "context_assembled",
            "provider_contacted",
            "generation_completed",
            "cancellation_requested",
            "timeout_observed",
            "state",
            "reason_code",
            "provider_error_code",
            "message_sent",
            "notification_created",
            "generated_output_committed",
            "cognition_mutated",
            "conversation_mutated",
            "structural_digest",
        )
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "record_count": len(state["receipts"]),
            "state_counts": counts,
            "recent_records": [
                {key: deepcopy(row.get(key)) for key in keys}
                for row in state["receipts"][-32:]
            ],
            "recognized_states": sorted(STATES),
            "exact_provider_context_assembly": True,
            "configured_local_model_path_available": True,
            "cancellation_supported": True,
            "timeout_supported": True,
            "workload_continuity_integrated": True,
            "receipts_are_structural_only": True,
            "generated_output_requires_separate_commit": True,
            "message_delivery_requires_separate_authority": True,
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
            "message_sent": False,
            "notification_created": False,
            "generated_output_committed": False,
            "cognition_mutated": False,
            "conversation_mutated": False,
        }


def build_conversation_cognition_bounded_generation_inspection(
    runtime_root: Path | str | None = None,
) -> dict[str, Any]:
    return ConversationCognitionBoundedGenerationStore(runtime_root).inspection_summary()
