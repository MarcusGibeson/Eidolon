from __future__ import annotations

"""Durable provider-neutral motivation and self-model state.

This module records observable cognitive state without claiming consciousness and
without storing hidden chain-of-thought. It is deliberately unable to authorize or
execute protected actions. Internal thoughts, desires, intentions, commitments,
and proposals are represented as distinct states; operator-authorized actions can
only be referenced from an external governed receipt.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import uuid

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock

MOTIVATION_SCHEMA_VERSION = "1"
MOTIVATION_CONTRACT_VERSION = "v1104.3"

MOTIVATION_KINDS = {
    "enduring_goal",
    "temporary_goal",
    "curiosity",
    "need",
    "concern",
    "preference",
    "unresolved_subject",
}
COGNITIVE_STATES = {
    "thought",
    "desire",
    "intention",
    "commitment",
    "proposal",
    "authorized_action",
}
ACTIVE_STATES = {"active", "suspended"}
TERMINAL_STATES = {"resolved", "retracted", "superseded", "abandoned"}
RELATIONSHIP_TYPES = {
    "supports",
    "conflicts_with",
    "derived_from_memory",
    "linked_commitment",
    "affected_by_outcome",
    "concerns_project",
    "concerns_relationship",
    "supersedes",
}
INTERNAL_COGNITIVE_STATES = COGNITIVE_STATES - {"authorized_action"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean(value: Any, limit: int = 600) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _bounded_float(value: Any, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return round(max(minimum, min(maximum, number)), 4)


def _digest(*parts: Any) -> str:
    material = "\x1f".join(_clean(part, 2000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    override = os.environ.get("EIDOLON_DATA_DIR")
    if override:
        data_root = Path(override).expanduser().resolve()
    else:
        data_root = Path(__file__).resolve().parents[1] / "data"
    return data_root / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": MOTIVATION_SCHEMA_VERSION,
        "contract_version": MOTIVATION_CONTRACT_VERSION,
        "identity": {
            "identity_id": "eidolon",
            "display_name": "Eidolon",
            "continuity_anchor": "operator-governed-local-artificial-mind",
            "epistemic_status": "candidate_artificial_consciousness_not_proven",
            "provider_neutral": True,
            "project_neutral": True,
            "revision": 0,
            "updated_at": "",
            "history": [],
        },
        "self_model": {
            "role": "operator-governed local artificial mind",
            "capabilities": [],
            "limitations": [
                "consciousness is not established",
                "internal state does not grant action authority",
                "provider availability does not define identity",
            ],
            "current_projects": [],
            "provider_observations": [],
            "current_focus": "",
            "operating_state": "running",
            "uncertainty": "bounded",
            "resource_posture": "idle",
            "revision": 0,
            "updated_at": "",
            "history": [],
        },
        "motivations": [],
        "processed_events": [],
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {
            "internal_state_can_authorize": False,
            "internal_state_can_execute": False,
            "authorized_action_requires_external_governed_receipt": True,
            "operator_authority_unchanged": True,
        },
    }


class MotivationStore:
    """Transactional durable store for self-model and motivational records."""

    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        clock: Callable[[], str] | None = None,
        event_history_limit: int = 512,
        item_history_limit: int = 64,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "motivation_state.json"
        self.clock = clock or _utc_now
        self.event_history_limit = max(32, int(event_history_limit))
        self.item_history_limit = max(8, int(item_history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != MOTIVATION_SCHEMA_VERSION:
            return _default_state()
        state.setdefault("motivations", [])
        state.setdefault("processed_events", [])
        state.setdefault("identity", deepcopy(_default_state()["identity"]))
        state.setdefault("self_model", deepcopy(_default_state()["self_model"]))
        state.setdefault("authority_boundary", deepcopy(_default_state()["authority_boundary"]))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def _mutate(self, event_id: str, mutator: Callable[[dict[str, Any], str], dict[str, Any]]) -> dict[str, Any]:
        event_id = _clean(event_id, 160)
        if not event_id:
            raise ValueError("event_id is required for accountable idempotent mutation")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior = next((row for row in state["processed_events"] if row.get("event_id") == event_id), None)
            if prior:
                return {
                    "ok": True,
                    "status": "duplicate_event_ignored",
                    "event_id": event_id,
                    "result": deepcopy(prior.get("result") or {}),
                    "revision": int(state.get("revision") or 0),
                    "idempotent": True,
                }
            now = self.clock()
            result = mutator(state, now)
            state["revision"] = int(state.get("revision") or 0) + 1
            state["updated_at"] = now
            receipt = {
                "event_id": event_id,
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "result": deepcopy(result),
                "content_free": True,
            }
            state["processed_events"] = (state["processed_events"] + [receipt])[-self.event_history_limit :]
            write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)
            return {
                "ok": True,
                "status": str(result.get("status") or "updated"),
                "event_id": event_id,
                "result": deepcopy(result),
                "revision": state["revision"],
                "idempotent": False,
            }

    def initialize_self_model(
        self,
        event_id: str,
        *,
        identity_id: str = "eidolon",
        display_name: str = "Eidolon",
        role: str = "operator-governed local artificial mind",
        capabilities: Iterable[str] = (),
        limitations: Iterable[str] = (),
        project_ids: Iterable[str] = (),
        provider_id: str = "",
        evidence_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            identity = state["identity"]
            before_identity = identity.get("identity_id") or "eidolon"
            requested_identity = _clean(identity_id, 120) or before_identity
            if int(identity.get("revision") or 0) > 0 and requested_identity != before_identity:
                raise ValueError("identity_id cannot be changed by ordinary self-model updates")
            identity.update({
                "identity_id": requested_identity,
                "display_name": _clean(display_name, 120) or "Eidolon",
                "revision": int(identity.get("revision") or 0) + 1,
                "updated_at": now,
            })
            identity_event = {
                "event": "identity_continuity_observed",
                "occurred_at": now,
                "identity_digest": _digest(requested_identity),
                "provider_neutral": True,
                "project_neutral": True,
            }
            identity["history"] = (list(identity.get("history") or []) + [identity_event])[-self.item_history_limit :]

            self_model = state["self_model"]
            if role:
                self_model["role"] = _clean(role, 240)
            if capabilities:
                self_model["capabilities"] = sorted({_clean(item, 180) for item in capabilities if _clean(item, 180)})
            retained_limits = set(self_model.get("limitations") or [])
            retained_limits.update(_clean(item, 240) for item in limitations if _clean(item, 240))
            self_model["limitations"] = sorted(retained_limits)
            self_model["current_projects"] = sorted({_clean(item, 120) for item in project_ids if _clean(item, 120)})
            if provider_id:
                observation = {
                    "provider_digest": _digest(provider_id),
                    "observed_at": now,
                    "identity_changed": False,
                    "provider_managed": False,
                }
                observations = list(self_model.get("provider_observations") or [])
                if not observations or observations[-1].get("provider_digest") != observation["provider_digest"]:
                    observations.append(observation)
                self_model["provider_observations"] = observations[-32:]
            self_model["revision"] = int(self_model.get("revision") or 0) + 1
            self_model["updated_at"] = now
            history = list(self_model.get("history") or [])
            history.append({
                "event": "self_model_updated",
                "occurred_at": now,
                "changed_fields": ["role", "capabilities", "limitations", "current_projects", "provider_observations"],
                "evidence_ref_digests": [_digest(ref) for ref in evidence_refs if _clean(ref, 300)][:16],
                "consciousness_claimed": False,
            })
            self_model["history"] = history[-self.item_history_limit :]
            return {
                "status": "self_model_initialized" if self_model["revision"] == 1 else "self_model_updated",
                "identity_id": requested_identity,
                "identity_revision": identity["revision"],
                "self_model_revision": self_model["revision"],
                "provider_neutral": True,
            }

        return self._mutate(event_id, apply)

    def observe_self_state(
        self,
        event_id: str,
        *,
        operating_state: str,
        current_focus: str = "",
        uncertainty: str = "bounded",
        resource_posture: str = "provider_free_bounded_cycle",
        provider_available: bool | None = None,
        supporting_refs: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Record one concise current self-observation without claiming sentience."""
        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            model = state["self_model"]
            model["operating_state"] = _clean(operating_state, 80) or "running"
            model["current_focus"] = _clean(current_focus, 120)
            model["uncertainty"] = _clean(uncertainty, 80) or "bounded"
            model["resource_posture"] = _clean(resource_posture, 120) or "provider_free_bounded_cycle"
            if provider_available is not None:
                model["provider_available"] = bool(provider_available)
            model["revision"] = int(model.get("revision") or 0) + 1
            model["updated_at"] = now
            history = list(model.get("history") or [])
            history.append({
                "event": "bounded_self_observation",
                "occurred_at": now,
                "changed_fields": ["operating_state", "current_focus", "uncertainty", "resource_posture", "provider_available"],
                "evidence_ref_digests": [_digest(ref) for ref in supporting_refs if _clean(ref, 300)][:16],
                "consciousness_claimed": False,
                "authorizes_action": False,
            })
            model["history"] = history[-self.item_history_limit :]
            return {
                "status": "self_state_observed",
                "self_model_revision": model["revision"],
                "current_focus": model["current_focus"],
                "authorizes_action": False,
            }

        return self._mutate(event_id, apply)

    def record_motivation(
        self,
        event_id: str,
        *,
        kind: str,
        summary: str,
        cognitive_state: str = "desire",
        valence: float = 0.0,
        urgency: float = 0.5,
        confidence: float = 0.5,
        origin_type: str,
        origin_ref: str,
        origin_phase: str = "perception_or_reflection",
        scope_project_id: str = "",
        relationship_refs: Iterable[Mapping[str, Any]] = (),
        motivation_id: str = "",
    ) -> dict[str, Any]:
        kind = _clean(kind, 80)
        cognitive_state = _clean(cognitive_state, 80)
        summary = _clean(summary, 600)
        origin_type = _clean(origin_type, 80)
        origin_ref = _clean(origin_ref, 240)
        origin_phase = _clean(origin_phase, 80)
        if kind not in MOTIVATION_KINDS:
            raise ValueError(f"unsupported motivation kind: {kind}")
        if cognitive_state not in INTERNAL_COGNITIVE_STATES:
            if cognitive_state == "authorized_action":
                raise PermissionError("internal cognition cannot create an authorized action")
            raise ValueError(f"unsupported cognitive state: {cognitive_state}")
        if not summary or not origin_type or not origin_ref:
            raise ValueError("summary, origin_type, and origin_ref are required")
        if origin_phase in {"post_generation_justification", "dialogue_already_generated"}:
            raise ValueError("motivations cannot be created to justify dialogue already generated")
        normalized_relationships = self._normalize_relationships(relationship_refs)
        semantic_key = _digest(kind, summary.casefold(), cognitive_state, scope_project_id)
        requested_id = _clean(motivation_id, 120)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            motivations = state["motivations"]
            existing = next(
                (
                    row
                    for row in motivations
                    if row.get("semantic_key") == semantic_key
                    and row.get("lifecycle_state") in ACTIVE_STATES
                ),
                None,
            )
            if existing:
                return {
                    "status": "duplicate_motivation_ignored",
                    "motivation_id": existing["motivation_id"],
                    "created": False,
                    "active": existing.get("lifecycle_state") == "active",
                }
            item_id = requested_id or f"mot-{uuid.uuid4().hex}"
            if any(row.get("motivation_id") == item_id for row in motivations):
                raise ValueError("motivation_id already exists with different content")
            item = {
                "motivation_id": item_id,
                "semantic_key": semantic_key,
                "kind": kind,
                "summary": summary,
                "cognitive_state": cognitive_state,
                "lifecycle_state": "active",
                "valence": _bounded_float(valence, minimum=-1.0, maximum=1.0),
                "urgency": _bounded_float(urgency),
                "confidence": _bounded_float(confidence),
                "origin": {
                    "type": origin_type,
                    "reference": origin_ref,
                    "phase": origin_phase,
                    "occurred_at": now,
                    "created_before_communication": True,
                },
                "scope": {
                    "identity_id": state["identity"].get("identity_id") or "eidolon",
                    "project_id": _clean(scope_project_id, 120),
                    "provider_bound": False,
                },
                "relationships": normalized_relationships,
                "created_at": now,
                "updated_at": now,
                "last_attended_at": "",
                "update_history": [
                    {
                        "event": "created",
                        "occurred_at": now,
                        "reason_code": origin_type,
                        "prior_state": "absent",
                        "new_state": "active",
                        "supporting_ref_digests": [_digest(origin_ref)],
                        "authored_conclusion": "A new motivation was recorded from evidence available before any related communication.",
                    }
                ],
                "authority": {
                    "authorizes_action": False,
                    "executes_action": False,
                    "approval_id": "",
                    "external_authorization_receipt": "",
                },
            }
            motivations.append(item)
            return {"status": "motivation_created", "motivation_id": item_id, "created": True, "active": True}

        return self._mutate(event_id, apply)

    def update_motivation(
        self,
        event_id: str,
        motivation_id: str,
        *,
        reason_code: str,
        event_type: str = "evidence_update",
        valence: float | None = None,
        urgency: float | None = None,
        confidence: float | None = None,
        cognitive_state: str | None = None,
        lifecycle_state: str | None = None,
        authored_conclusion: str = "",
        supporting_refs: Iterable[str] = (),
        outcome_ref: str = "",
    ) -> dict[str, Any]:
        motivation_id = _clean(motivation_id, 120)
        reason_code = _clean(reason_code, 120)
        event_type = _clean(event_type, 80)
        if not motivation_id or not reason_code:
            raise ValueError("motivation_id and reason_code are required")
        if cognitive_state is not None:
            cognitive_state = _clean(cognitive_state, 80)
            if cognitive_state not in INTERNAL_COGNITIVE_STATES:
                if cognitive_state == "authorized_action":
                    raise PermissionError("internal cognition cannot promote itself to authorized action")
                raise ValueError("unsupported cognitive state")
        if lifecycle_state is not None:
            lifecycle_state = _clean(lifecycle_state, 80)
            if lifecycle_state not in ACTIVE_STATES | TERMINAL_STATES:
                raise ValueError("unsupported lifecycle state")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["motivations"] if row.get("motivation_id") == motivation_id), None)
            if not item:
                raise KeyError("motivation not found")
            prior = {
                "valence": item.get("valence"),
                "urgency": item.get("urgency"),
                "confidence": item.get("confidence"),
                "cognitive_state": item.get("cognitive_state"),
                "lifecycle_state": item.get("lifecycle_state"),
            }
            if valence is not None:
                item["valence"] = _bounded_float(valence, minimum=-1.0, maximum=1.0)
            if urgency is not None:
                item["urgency"] = _bounded_float(urgency)
            if confidence is not None:
                item["confidence"] = _bounded_float(confidence)
            if cognitive_state is not None:
                item["cognitive_state"] = cognitive_state
            if lifecycle_state is not None:
                item["lifecycle_state"] = lifecycle_state
            if outcome_ref:
                relationship = {"type": "affected_by_outcome", "target_type": "outcome", "target_id": _clean(outcome_ref, 240)}
                if relationship not in item["relationships"]:
                    item["relationships"].append(relationship)
            item["updated_at"] = now
            history = list(item.get("update_history") or [])
            history.append({
                "event": event_type,
                "occurred_at": now,
                "reason_code": reason_code,
                "prior_state": prior,
                "new_state": {
                    "valence": item.get("valence"),
                    "urgency": item.get("urgency"),
                    "confidence": item.get("confidence"),
                    "cognitive_state": item.get("cognitive_state"),
                    "lifecycle_state": item.get("lifecycle_state"),
                },
                "supporting_ref_digests": [_digest(ref) for ref in supporting_refs if _clean(ref, 300)][:16],
                "authored_conclusion": _clean(authored_conclusion, 420),
            })
            item["update_history"] = history[-self.item_history_limit :]
            return {
                "status": "motivation_updated",
                "motivation_id": motivation_id,
                "lifecycle_state": item["lifecycle_state"],
                "active_influence": item["lifecycle_state"] == "active",
                "cognitive_state": item["cognitive_state"],
            }

        return self._mutate(event_id, apply)

    def retract_motivation(self, event_id: str, motivation_id: str, *, reason_code: str, correction_ref: str) -> dict[str, Any]:
        return self.update_motivation(
            event_id,
            motivation_id,
            reason_code=reason_code,
            event_type="correction_or_retraction",
            lifecycle_state="retracted",
            urgency=0.0,
            authored_conclusion="The prior motivation remains in accountable history but no longer influences active behavior.",
            supporting_refs=[correction_ref],
        )

    def reference_authorized_action(
        self,
        event_id: str,
        *,
        motivation_id: str,
        governed_action_id: str,
        authorization_receipt_id: str,
        outcome_ref: str = "",
    ) -> dict[str, Any]:
        """Attach an external authorization reference without creating authority.

        The caller must already possess a governed authorization receipt from the
        existing approval/action subsystem. This method only records the relationship.
        """
        motivation_id = _clean(motivation_id, 120)
        governed_action_id = _clean(governed_action_id, 160)
        authorization_receipt_id = _clean(authorization_receipt_id, 160)
        if not all((motivation_id, governed_action_id, authorization_receipt_id)):
            raise ValueError("motivation, governed action, and authorization receipt are required")

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["motivations"] if row.get("motivation_id") == motivation_id), None)
            if not item:
                raise KeyError("motivation not found")
            relation = {"type": "linked_commitment", "target_type": "governed_action", "target_id": governed_action_id}
            if relation not in item["relationships"]:
                item["relationships"].append(relation)
            item["authority"] = {
                "authorizes_action": False,
                "executes_action": False,
                "approval_id": "",
                "external_authorization_receipt": authorization_receipt_id,
            }
            history = list(item.get("update_history") or [])
            history.append({
                "event": "external_authorization_observed",
                "occurred_at": now,
                "reason_code": "governed_action_receipt",
                "prior_state": item.get("cognitive_state"),
                "new_state": "authorized_action_reference_only",
                "supporting_ref_digests": [_digest(authorization_receipt_id), _digest(outcome_ref)] if outcome_ref else [_digest(authorization_receipt_id)],
                "authored_conclusion": "A separately governed action receipt was linked; cognition did not grant the authorization.",
            })
            item["update_history"] = history[-self.item_history_limit :]
            item["updated_at"] = now
            return {
                "status": "external_authorization_referenced",
                "motivation_id": motivation_id,
                "governed_action_id": governed_action_id,
                "internal_authority_granted": False,
            }

        return self._mutate(event_id, apply)

    def mark_attended(self, event_id: str, motivation_id: str, *, conclusion: str, supporting_refs: Iterable[str] = ()) -> dict[str, Any]:
        motivation_id = _clean(motivation_id, 120)

        def apply(state: dict[str, Any], now: str) -> dict[str, Any]:
            item = next((row for row in state["motivations"] if row.get("motivation_id") == motivation_id), None)
            if not item:
                raise KeyError("motivation not found")
            item["last_attended_at"] = now
            item["updated_at"] = now
            history = list(item.get("update_history") or [])
            history.append({
                "event": "attention_and_reflection",
                "occurred_at": now,
                "reason_code": "bounded_cognitive_cycle",
                "prior_state": item.get("lifecycle_state"),
                "new_state": item.get("lifecycle_state"),
                "supporting_ref_digests": [_digest(ref) for ref in supporting_refs if _clean(ref, 300)][:16],
                "authored_conclusion": _clean(conclusion, 420),
            })
            item["update_history"] = history[-self.item_history_limit :]
            return {"status": "motivation_attended", "motivation_id": motivation_id, "active_influence": item.get("lifecycle_state") == "active"}

        return self._mutate(event_id, apply)

    def active_motivations(self) -> list[dict[str, Any]]:
        state = self._load()
        return [deepcopy(row) for row in state["motivations"] if row.get("lifecycle_state") == "active"]

    def inspection_summary(self, *, item_limit: int = 12) -> dict[str, Any]:
        state = self._load()
        active = [row for row in state["motivations"] if row.get("lifecycle_state") == "active"]
        active.sort(key=lambda row: (-float(row.get("urgency") or 0), -float(row.get("confidence") or 0), str(row.get("created_at") or ""), str(row.get("motivation_id") or "")))
        items = []
        for row in active[: max(1, int(item_limit))]:
            items.append({
                "motivation_id": row.get("motivation_id"),
                "kind": row.get("kind"),
                "summary": _clean(row.get("summary"), 240),
                "cognitive_state": row.get("cognitive_state"),
                "lifecycle_state": row.get("lifecycle_state"),
                "valence": row.get("valence"),
                "urgency": row.get("urgency"),
                "confidence": row.get("confidence"),
                "project_id": (row.get("scope") or {}).get("project_id", ""),
                "relationship_count": len(row.get("relationships") or []),
                "last_attended_at": row.get("last_attended_at", ""),
                "authority_state": "internal_only",
            })
        terminal_count = sum(1 for row in state["motivations"] if row.get("lifecycle_state") in TERMINAL_STATES)
        return {
            "ok": True,
            "schema_version": MOTIVATION_SCHEMA_VERSION,
            "contract_version": MOTIVATION_CONTRACT_VERSION,
            "identity": {
                "identity_id": state["identity"].get("identity_id"),
                "display_name": state["identity"].get("display_name"),
                "epistemic_status": state["identity"].get("epistemic_status"),
                "revision": state["identity"].get("revision"),
                "provider_neutral": True,
                "project_neutral": True,
            },
            "self_model": {
                "role": state["self_model"].get("role"),
                "capabilities": list(state["self_model"].get("capabilities") or []),
                "limitations": list(state["self_model"].get("limitations") or []),
                "current_projects": list(state["self_model"].get("current_projects") or []),
                "revision": state["self_model"].get("revision"),
            },
            "active_motivation_count": len(active),
            "historical_inactive_count": terminal_count,
            "active_motivations": items,
            "cognitive_state_distinctions": [
                {"state": "thought", "can_authorize": False, "meaning": "a considered representation"},
                {"state": "desire", "can_authorize": False, "meaning": "a valued possible state"},
                {"state": "intention", "can_authorize": False, "meaning": "a selected internal direction"},
                {"state": "commitment", "can_authorize": False, "meaning": "a durable internal promise or obligation"},
                {"state": "proposal", "can_authorize": False, "meaning": "a request offered for operator review"},
                {"state": "authorized_action", "can_authorize": False, "meaning": "an external governed action reference only"},
            ],
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "updated_at": state.get("updated_at", ""),
            "raw_chain_of_thought_stored": False,
            "provider_payloads_stored": False,
        }

    @staticmethod
    def _normalize_relationships(values: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for value in values:
            if not isinstance(value, Mapping):
                continue
            relation_type = _clean(value.get("type"), 80)
            target_type = _clean(value.get("target_type"), 80)
            target_id = _clean(value.get("target_id"), 240)
            if relation_type not in RELATIONSHIP_TYPES or not target_type or not target_id:
                continue
            row = {"type": relation_type, "target_type": target_type, "target_id": target_id}
            if row not in result:
                result.append(row)
        return result[:32]


def build_motivation_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    return MotivationStore(runtime_root).inspection_summary()


def motivation_state_contains_forbidden_authority(state: Mapping[str, Any]) -> bool:
    boundary = state.get("authority_boundary") if isinstance(state.get("authority_boundary"), Mapping) else {}
    if boundary.get("internal_state_can_authorize") is not False or boundary.get("internal_state_can_execute") is not False:
        return True
    for item in state.get("motivations") or []:
        if not isinstance(item, Mapping):
            continue
        authority = item.get("authority") if isinstance(item.get("authority"), Mapping) else {}
        if authority.get("authorizes_action") or authority.get("executes_action"):
            return True
    return False
