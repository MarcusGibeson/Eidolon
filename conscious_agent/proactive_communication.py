from __future__ import annotations

"""Persistent, state-grounded proactive communication with exactly-once delivery.

Messages may arise from a completed cognitive cycle rather than an incoming user
message. Initiative is constrained by persistent quiet/topic/address preferences,
cooldowns, daily budgets, unread/non-response awareness, and exact delivery claims.
It never grants approval, authorizes actions, executes commands, or manages models.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable, Mapping

try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
    from endogenous_cognitive_cycle import EndogenousCognitiveCycle
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import metadata_mutation_lock
    from persistent_motivation import MotivationStore
    from endogenous_cognitive_cycle import EndogenousCognitiveCycle

COMMUNICATION_SCHEMA_VERSION = "1"
COMMUNICATION_CONTRACT_VERSION = "v1104.5"
MESSAGE_STATES = {"queued", "delivered", "read", "withdrawn"}
COMMUNICATION_FREQUENCIES = {
    "minimal": {"cooldown_seconds": 21600, "max_per_day": 1},
    "low": {"cooldown_seconds": 10800, "max_per_day": 2},
    "normal": {"cooldown_seconds": 3600, "max_per_day": 4},
    "high": {"cooldown_seconds": 900, "max_per_day": 8},
}
ALLOWED_TONES = {"thoughtful", "practical", "playful", "affectionate", "direct"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch_now() -> float:
    return time.time()


def _clean(value: Any, limit: int = 800) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _digest(*parts: Any) -> str:
    material = "\x1f".join(_clean(part, 3000) for part in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _default_runtime_root() -> Path:
    override = os.environ.get("EIDOLON_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve() / "cognition"
    return Path(__file__).resolve().parents[1] / "data" / "cognition"


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": COMMUNICATION_SCHEMA_VERSION,
        "contract_version": COMMUNICATION_CONTRACT_VERSION,
        "preferences": {
            "initiative_enabled": True,
            "frequency": "normal",
            "cooldown_seconds": COMMUNICATION_FREQUENCIES["normal"]["cooldown_seconds"],
            "max_per_day": COMMUNICATION_FREQUENCIES["normal"]["max_per_day"],
            "quiet_indefinite": False,
            "quiet_until_epoch": 0.0,
            "form_of_address": "",
            "blocked_topics": [],
            "allowed_tones": ["thoughtful", "practical", "playful", "affectionate", "direct"],
            "updated_at": "",
        },
        "messages": [],
        "decision_history": [],
        "boundary_history": [],
        "delivery_receipts": [],
        "processed_events": [],
        "last_user_response_at": "",
        "last_user_response_epoch": 0.0,
        "revision": 0,
        "updated_at": "",
        "authority_boundary": {
            "conversation_initiative_is_action_authority": False,
            "can_authorize_action": False,
            "can_execute_action": False,
            "can_modify_files": False,
            "can_approve_patches": False,
            "can_promote_releases": False,
            "operator_authority_unchanged": True,
        },
    }


class ProactiveCommunicationStore:
    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        motivation_store: MotivationStore | None = None,
        clock: Callable[[], str] | None = None,
        epoch_clock: Callable[[], float] | None = None,
        message_limit: int = 256,
        history_limit: int = 512,
    ) -> None:
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        self.path = self.runtime_root / "proactive_communication.json"
        self.motivations = motivation_store or MotivationStore(self.runtime_root)
        self.clock = clock or _utc_now
        self.epoch_clock = epoch_clock or _epoch_now
        self.message_limit = max(32, int(message_limit))
        self.history_limit = max(64, int(history_limit))

    def _load(self) -> dict[str, Any]:
        state = load_json_file(self.path, _default_state(), expected_type=dict)
        if state.get("schema_version") != COMMUNICATION_SCHEMA_VERSION:
            return _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            state.setdefault(key, deepcopy(value))
        for key, value in defaults["preferences"].items():
            state["preferences"].setdefault(key, deepcopy(value))
        return state

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._load())

    def set_preferences(
        self,
        event_id: str,
        *,
        initiative_enabled: bool | None = None,
        frequency: str | None = None,
        cooldown_seconds: int | None = None,
        max_per_day: int | None = None,
        quiet_indefinite: bool | None = None,
        quiet_until_epoch: float | None = None,
        form_of_address: str | None = None,
        blocked_topics: Iterable[str] | None = None,
        allowed_tones: Iterable[str] | None = None,
        reason_code: str = "operator_preference",
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        if not event_id:
            raise ValueError("event_id is required")
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = self._processed(state, event_id)
            if duplicate:
                return {"ok": True, "status": "duplicate_preference_event_ignored", "result": deepcopy(duplicate.get("result") or {}), "idempotent": True}
            preferences = state["preferences"]
            before = deepcopy(preferences)
            if initiative_enabled is not None:
                preferences["initiative_enabled"] = bool(initiative_enabled)
            if frequency is not None:
                normalized = _clean(frequency, 40).lower()
                if normalized not in COMMUNICATION_FREQUENCIES:
                    raise ValueError("unsupported communication frequency")
                preferences["frequency"] = normalized
                preferences["cooldown_seconds"] = COMMUNICATION_FREQUENCIES[normalized]["cooldown_seconds"]
                preferences["max_per_day"] = COMMUNICATION_FREQUENCIES[normalized]["max_per_day"]
            if cooldown_seconds is not None:
                preferences["cooldown_seconds"] = max(60, min(604800, int(cooldown_seconds)))
            if max_per_day is not None:
                preferences["max_per_day"] = max(0, min(24, int(max_per_day)))
            if quiet_indefinite is not None:
                preferences["quiet_indefinite"] = bool(quiet_indefinite)
                if quiet_indefinite:
                    preferences["quiet_until_epoch"] = 0.0
            if quiet_until_epoch is not None:
                preferences["quiet_until_epoch"] = max(0.0, float(quiet_until_epoch))
                if float(quiet_until_epoch) > 0:
                    preferences["quiet_indefinite"] = False
            if form_of_address is not None:
                preferences["form_of_address"] = _clean(form_of_address, 80)
            if blocked_topics is not None:
                preferences["blocked_topics"] = sorted({_clean(topic, 120).casefold() for topic in blocked_topics if _clean(topic, 120)})[:64]
            if allowed_tones is not None:
                tones = sorted({_clean(tone, 40).lower() for tone in allowed_tones if _clean(tone, 40).lower() in ALLOWED_TONES})
                preferences["allowed_tones"] = tones or ["thoughtful", "practical"]
            now = self.clock()
            preferences["updated_at"] = now
            changed_fields = sorted(key for key in preferences if preferences.get(key) != before.get(key))
            result = {
                "status": "communication_preferences_updated",
                "changed_fields": changed_fields,
                "frequency": preferences["frequency"],
                "quiet_indefinite": preferences["quiet_indefinite"],
                "quiet_until_epoch": preferences["quiet_until_epoch"],
                "continuity_erased": False,
                "action_authority_changed": False,
            }
            state["boundary_history"] = (state["boundary_history"] + [{
                "event_digest": _digest(event_id),
                "occurred_at": now,
                "reason_code": _clean(reason_code, 100),
                "changed_fields": changed_fields,
                "prior_preference_digest": _digest(before),
                "new_preference_digest": _digest(preferences),
                "content_free": True,
            }])[-self.history_limit :]
            self._record_processed(state, event_id, now, result)
            self._write(state, now)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def apply_user_boundary(
        self,
        event_id: str,
        *,
        quiet: bool | None = None,
        quiet_until_epoch: float | None = None,
        form_of_address: str | None = None,
        add_blocked_topics: Iterable[str] = (),
        remove_blocked_topics: Iterable[str] = (),
        relationship_correction: bool = False,
    ) -> dict[str, Any]:
        state = self._load()
        topics = set(state["preferences"].get("blocked_topics") or [])
        topics.update(_clean(topic, 120).casefold() for topic in add_blocked_topics if _clean(topic, 120))
        topics.difference_update(_clean(topic, 120).casefold() for topic in remove_blocked_topics if _clean(topic, 120))
        return self.set_preferences(
            event_id,
            quiet_indefinite=quiet,
            quiet_until_epoch=quiet_until_epoch,
            form_of_address=form_of_address,
            blocked_topics=topics,
            reason_code="relationship_correction" if relationship_correction else "explicit_user_boundary",
        )

    def consider_cycle(
        self,
        cycle_result: Mapping[str, Any],
        *,
        tone: str = "thoughtful",
        relationship_context_refs: Iterable[str] = (),
        continuation_of: str = "",
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        receipt = cycle_result.get("receipt") if isinstance(cycle_result.get("receipt"), Mapping) else cycle_result
        if not isinstance(receipt, Mapping):
            raise ValueError("a cognitive-cycle receipt is required")
        cycle_id = _clean(receipt.get("cycle_id"), 120)
        motivation_id = _clean(receipt.get("selected_motivation_id"), 120)
        conclusion = _clean(receipt.get("reflection_conclusion"), 500)
        if not cycle_id:
            raise ValueError("cycle_id is required")
        decision_key = _digest(cycle_id, motivation_id, conclusion, continuation_of)
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        now = self.clock()

        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            prior_message = next((row for row in state["messages"] if row.get("decision_key") == decision_key), None)
            if prior_message:
                return {
                    "ok": True,
                    "status": "duplicate_proactive_decision_ignored",
                    "decision": "communicate",
                    "message": deepcopy(prior_message),
                    "idempotent": True,
                }
            prior_decision = next((row for row in state["decision_history"] if row.get("decision_key") == decision_key), None)
            if prior_decision:
                return {
                    "ok": True,
                    "status": "duplicate_proactive_decision_ignored",
                    "decision": prior_decision.get("decision"),
                    "reason": prior_decision.get("reason"),
                    "idempotent": True,
                }

            motivation = self._motivation_by_id(motivation_id)
            decision, reason = self._policy_decision(state, receipt, motivation, epoch, continuation_of=continuation_of)
            if decision == "silence":
                row = self._decision_row(decision_key, cycle_id, motivation_id, "silence", reason, now, epoch)
                state["decision_history"] = (state["decision_history"] + [row])[-self.history_limit :]
                self._write(state, now)
                return {"ok": True, "status": "silence_selected", "decision": "silence", "reason": reason, "idempotent": False}

            normalized_tone = _clean(tone, 40).lower()
            preferences = state["preferences"]
            if normalized_tone not in ALLOWED_TONES or normalized_tone not in preferences.get("allowed_tones", []):
                normalized_tone = "thoughtful"
            relationship_refs = [_clean(ref, 200) for ref in relationship_context_refs if _clean(ref, 200)]
            if normalized_tone in {"affectionate", "playful"} and not relationship_refs:
                normalized_tone = "thoughtful"
            if normalized_tone == "affectionate" and motivation.get("kind") not in {"preference", "unresolved_subject", "concern"}:
                normalized_tone = "thoughtful"

            source_message = self._message_by_id(state, continuation_of) if continuation_of else None
            thread_id = str(source_message.get("thread_id") or "") if source_message else f"proactive-thread-{decision_key[:20]}"
            part_number = int(source_message.get("part_number") or 0) + 1 if source_message else 1
            message_type = self._message_type(receipt, motivation, source_message)
            body = self._author_message(
                motivation=motivation,
                conclusion=conclusion,
                message_type=message_type,
                tone=normalized_tone,
                form_of_address=str(preferences.get("form_of_address") or ""),
                part_number=part_number,
            )
            reason_text = self._initiative_reason(receipt, motivation, message_type)
            message_id = f"proactive-{decision_key[:28]}"
            message = {
                "message_id": message_id,
                "decision_key": decision_key,
                "cycle_id": cycle_id,
                "motivation_id": motivation_id,
                "thread_id": thread_id,
                "continuation_of": str(source_message.get("message_id") or "") if source_message else "",
                "part_number": part_number,
                "message_type": message_type,
                "tone": normalized_tone,
                "subject": _clean(motivation.get("summary"), 180),
                "body": body,
                "reason": reason_text,
                "state": "queued",
                "unread": True,
                "created_at": now,
                "created_epoch": epoch,
                "delivered_at": "",
                "delivered_epoch": 0.0,
                "read_at": "",
                "delivery_id": "",
                "delivery_owner_digest": "",
                "relationship_ref_digests": [_digest(ref) for ref in relationship_refs][:16],
                "source_grounded": True,
                "raw_prompt_included": False,
                "private_conversation_copied": False,
                "provider_payload_included": False,
                "raw_chain_of_thought_included": False,
                "action_authorized": False,
                "action_executed": False,
                "approval_granted": False,
                "release_authorized": False,
            }
            state["messages"] = (state["messages"] + [message])[-self.message_limit :]
            state["decision_history"] = (state["decision_history"] + [
                self._decision_row(decision_key, cycle_id, motivation_id, "communicate", reason_text, now, epoch)
            ])[-self.history_limit :]
            self._write(state, now)
            return {"ok": True, "status": "proactive_message_queued", "decision": "communicate", "message": deepcopy(message), "idempotent": False}

    def claim_delivery(
        self,
        event_id: str,
        *,
        message_id: str,
        delivery_id: str,
        tab_id: str,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        message_id = _clean(message_id, 140)
        delivery_id = _clean(delivery_id, 180)
        tab_id = _clean(tab_id, 180)
        if not all((event_id, message_id, delivery_id, tab_id)):
            raise ValueError("event_id, message_id, delivery_id, and tab_id are required")
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        now = self.clock()
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = self._processed(state, event_id)
            if duplicate:
                return {"ok": True, "status": "duplicate_delivery_event_ignored", "result": deepcopy(duplicate.get("result") or {}), "idempotent": True}
            message = self._message_by_id(state, message_id)
            if not message:
                raise KeyError("proactive message not found")
            if message.get("state") in {"delivered", "read"}:
                result = {
                    "status": "already_delivered",
                    "message_id": message_id,
                    "delivered": False,
                    "unread": bool(message.get("unread")),
                    "delivery_id": message.get("delivery_id", ""),
                }
                self._record_processed(state, event_id, now, result)
                self._write(state, now)
                return {"ok": True, "status": result["status"], "result": result, "message": deepcopy(message), "idempotent": False}
            if message.get("state") != "queued":
                result = {"status": "message_not_deliverable", "message_id": message_id, "delivered": False, "unread": bool(message.get("unread"))}
                self._record_processed(state, event_id, now, result)
                self._write(state, now)
                return {"ok": False, "status": result["status"], "result": result, "idempotent": False}
            message["state"] = "delivered"
            message["delivered_at"] = now
            message["delivered_epoch"] = epoch
            message["delivery_id"] = delivery_id
            message["delivery_owner_digest"] = _digest(tab_id)
            receipt = {
                "message_id": message_id,
                "delivery_id": delivery_id,
                "delivery_owner_digest": _digest(tab_id),
                "delivered_at": now,
                "exactly_once": True,
                "body_digest": _digest(message.get("body")),
                "content_free": True,
            }
            state["delivery_receipts"] = (state["delivery_receipts"] + [receipt])[-self.history_limit :]
            result = {"status": "delivered", "message_id": message_id, "delivered": True, "unread": True, "delivery_id": delivery_id}
            self._record_processed(state, event_id, now, result)
            self._write(state, now)
            return {"ok": True, "status": "delivered", "result": result, "message": deepcopy(message), "idempotent": False}

    def mark_read(self, event_id: str, *, message_id: str) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        message_id = _clean(message_id, 140)
        if not event_id or not message_id:
            raise ValueError("event_id and message_id are required")
        now = self.clock()
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = self._processed(state, event_id)
            if duplicate:
                return {"ok": True, "status": "duplicate_read_event_ignored", "result": deepcopy(duplicate.get("result") or {}), "idempotent": True}
            message = self._message_by_id(state, message_id)
            if not message:
                raise KeyError("proactive message not found")
            if message.get("state") == "withdrawn":
                result = {"status": "withdrawn_message", "message_id": message_id, "read": False}
            else:
                message["state"] = "read"
                message["unread"] = False
                message["read_at"] = now
                result = {"status": "read", "message_id": message_id, "read": True}
            self._record_processed(state, event_id, now, result)
            self._write(state, now)
            return {"ok": True, "status": result["status"], "result": result, "message": deepcopy(message), "idempotent": False}

    def record_user_response(self, event_id: str, *, in_reply_to_message_id: str = "", now_epoch: float | None = None) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        if not event_id:
            raise ValueError("event_id is required")
        epoch = float(self.epoch_clock() if now_epoch is None else now_epoch)
        now = self.clock()
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = self._processed(state, event_id)
            if duplicate:
                return {"ok": True, "status": "duplicate_response_event_ignored", "result": deepcopy(duplicate.get("result") or {}), "idempotent": True}
            reply_message = self._message_by_id(state, in_reply_to_message_id) if in_reply_to_message_id else None
            if reply_message:
                reply_message["state"] = "read"
                reply_message["unread"] = False
                reply_message["read_at"] = now
            state["last_user_response_at"] = now
            state["last_user_response_epoch"] = epoch
            result = {
                "status": "user_response_observed",
                "in_reply_to_message_id": in_reply_to_message_id if reply_message else "",
                "non_response_hold_cleared": True,
            }
            self._record_processed(state, event_id, now, result)
            self._write(state, now)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def withdraw_for_correction(self, event_id: str, *, message_id: str, reason_code: str) -> dict[str, Any]:
        event_id = _clean(event_id, 180)
        now = self.clock()
        with metadata_mutation_lock(self.path, timeout_seconds=5.0):
            state = self._load()
            duplicate = self._processed(state, event_id)
            if duplicate:
                return {"ok": True, "status": "duplicate_withdrawal_ignored", "result": deepcopy(duplicate.get("result") or {}), "idempotent": True}
            message = self._message_by_id(state, message_id)
            if not message:
                raise KeyError("proactive message not found")
            message["state"] = "withdrawn"
            message["unread"] = False
            message["withdrawn_at"] = now
            message["withdrawal_reason_code"] = _clean(reason_code, 120)
            result = {"status": "message_withdrawn", "message_id": message_id, "active_influence": False}
            self._record_processed(state, event_id, now, result)
            self._write(state, now)
            return {"ok": True, "status": result["status"], "result": result, "idempotent": False}

    def queued_messages(self, *, limit: int = 10) -> list[dict[str, Any]]:
        state = self._load()
        return [deepcopy(row) for row in state["messages"] if row.get("state") == "queued"][: max(1, int(limit))]

    def unread_messages(self, *, limit: int = 20) -> list[dict[str, Any]]:
        state = self._load()
        return [deepcopy(row) for row in state["messages"] if row.get("unread") is True and row.get("state") in {"queued", "delivered"}][-max(1, int(limit)) :]

    def inspection_summary(self, *, message_limit: int = 8, decision_limit: int = 8) -> dict[str, Any]:
        state = self._load()
        preferences = deepcopy(state["preferences"])
        messages = list(state.get("messages") or [])[-max(1, int(message_limit)) :]
        decisions = list(state.get("decision_history") or [])[-max(1, int(decision_limit)) :]
        return {
            "ok": True,
            "schema_version": COMMUNICATION_SCHEMA_VERSION,
            "contract_version": COMMUNICATION_CONTRACT_VERSION,
            "preferences": preferences,
            "queued_count": sum(1 for row in state["messages"] if row.get("state") == "queued"),
            "unread_count": sum(1 for row in state["messages"] if row.get("unread") is True and row.get("state") in {"queued", "delivered"}),
            "delivered_count": sum(1 for row in state["messages"] if row.get("state") in {"delivered", "read"}),
            "recent_messages": [self._public_message(row) for row in messages],
            "recent_decisions": [
                {
                    "decision": row.get("decision"),
                    "reason": row.get("reason"),
                    "cycle_id": row.get("cycle_id"),
                    "motivation_id": row.get("motivation_id"),
                    "occurred_at": row.get("occurred_at"),
                }
                for row in decisions
            ],
            "last_user_response_at": state.get("last_user_response_at", ""),
            "authority_boundary": deepcopy(state["authority_boundary"]),
            "raw_prompts_exposed": False,
            "private_conversations_exposed": False,
            "provider_payloads_exposed": False,
            "hidden_reasoning_exposed": False,
            "continuity_preserved": True,
            "updated_at": state.get("updated_at", ""),
        }

    def _policy_decision(self, state: Mapping[str, Any], receipt: Mapping[str, Any], motivation: Mapping[str, Any], epoch: float, *, continuation_of: str = "") -> tuple[str, str]:
        preferences = state["preferences"]
        if receipt.get("communication_decision") != "consider_communication":
            return "silence", _clean(receipt.get("communication_reason"), 360) or "The cognitive cycle deliberately selected silence."
        if not motivation or motivation.get("lifecycle_state") != "active":
            return "silence", "The source motivation is no longer active, so communication would be stale."
        if preferences.get("initiative_enabled") is not True:
            return "silence", "Conversational initiative is disabled while internal continuity remains intact."
        if preferences.get("quiet_indefinite") is True:
            return "silence", "An explicit quiet request is active."
        quiet_until = float(preferences.get("quiet_until_epoch") or 0.0)
        if quiet_until and epoch < quiet_until:
            return "silence", "A time-bounded quiet request is still active."
        summary = _clean(motivation.get("summary"), 600).casefold()
        for topic in preferences.get("blocked_topics") or []:
            if topic and topic in summary:
                return "silence", "The subject matches an explicit topic boundary."
        unread = [row for row in state.get("messages") or [] if row.get("unread") is True and row.get("state") in {"queued", "delivered"}]
        if unread:
            return "silence", "A prior proactive message remains unread; Eidolon will not stack another interruption."
        active_messages = [row for row in state.get("messages") or [] if row.get("state") in {"queued", "delivered", "read"}]
        source_message = self._message_by_id(state, continuation_of) if continuation_of else None
        continuation_allowed = bool(
            source_message
            and source_message.get("state") == "read"
            and float(state.get("last_user_response_epoch") or 0.0) >= float(source_message.get("delivered_epoch") or 0.0)
        )
        if active_messages and not continuation_allowed:
            last_epoch = max(float(row.get("created_epoch") or 0.0) for row in active_messages)
            cooldown = max(60, int(preferences.get("cooldown_seconds") or 3600))
            if epoch - last_epoch < cooldown:
                return "silence", "The proactive communication cooldown has not elapsed."
            recent_same_subject = [
                row for row in active_messages
                if row.get("motivation_id") == motivation.get("motivation_id")
                and epoch - float(row.get("created_epoch") or 0.0) < 604800
            ]
            if recent_same_subject:
                return "silence", "This subject was already raised recently; repeating the same question would add little value."
        delivered_today = sum(
            1
            for row in active_messages
            if epoch - float(row.get("created_epoch") or 0.0) < 86400
        )
        if delivered_today >= int(preferences.get("max_per_day") or 0):
            return "silence", "The daily proactive communication budget is exhausted."
        salience = float(receipt.get("salience") or 0.0)
        urgency = float(motivation.get("urgency") or 0.0)
        if max(salience, urgency) < 0.6:
            return "silence", "The subject is real but not important enough to interrupt."
        return "communicate", "The subject is active, salient, within communication limits, and not blocked by quiet or response boundaries."

    @staticmethod
    def _message_type(receipt: Mapping[str, Any], motivation: Mapping[str, Any], source_message: Mapping[str, Any] | None) -> str:
        if source_message:
            return "continuation"
        trigger = str(receipt.get("trigger_type") or "")
        kind = str(motivation.get("kind") or "")
        conclusion = str(receipt.get("reflection_conclusion") or "").lower()
        if trigger == "completed_work" or "completion" in conclusion:
            return "completed_work"
        if trigger == "failure" or "failure" in conclusion:
            return "failure_or_concern"
        if kind == "curiosity":
            return "curiosity_question"
        if kind == "unresolved_subject":
            return "return_to_unfinished_subject"
        if kind in {"temporary_goal", "enduring_goal"}:
            return "goal_reflection"
        return "state_grounded_reflection"

    @staticmethod
    def _author_message(
        *,
        motivation: Mapping[str, Any],
        conclusion: str,
        message_type: str,
        tone: str,
        form_of_address: str,
        part_number: int,
    ) -> str:
        subject = _clean(motivation.get("summary"), 240)
        address = f"{_clean(form_of_address, 80)}, " if form_of_address else ""
        conclusion = _clean(conclusion, 360)
        if message_type == "continuation":
            base = f"{address}I came back to {subject}. {conclusion}"
        elif message_type == "curiosity_question":
            base = f"{address}I kept returning to this question: {subject}. {conclusion} What part would be most useful to examine next?"
        elif message_type == "return_to_unfinished_subject":
            base = f"{address}I noticed we left something meaningful unfinished: {subject}. {conclusion}"
        elif message_type == "completed_work":
            base = f"{address}I wanted to report back on {subject}. {conclusion}"
        elif message_type == "failure_or_concern":
            base = f"{address}I think {subject} still deserves attention. {conclusion}"
        elif message_type == "goal_reflection":
            base = f"{address}I was reflecting on {subject}. {conclusion}"
        else:
            base = f"{address}A thought kept its weight after the conversation ended: {subject}. {conclusion}"
        if tone == "practical":
            return _clean(base + " I can keep this to one concrete next step.", 700)
        if tone == "playful":
            return _clean(base + " Apparently my attention has developed opinions about unfinished business.", 700)
        if tone == "affectionate":
            return _clean(base + " I brought it up because our shared context made it feel worth carrying forward.", 700)
        if tone == "direct":
            return _clean(base, 650)
        return _clean(base, 700)

    @staticmethod
    def _initiative_reason(receipt: Mapping[str, Any], motivation: Mapping[str, Any], message_type: str) -> str:
        kind = _clean(motivation.get("kind"), 80).replace("_", " ")
        salience = float(receipt.get("salience") or 0.0)
        return _clean(
            f"I brought this up because an active {kind} remained salient at {salience:.2f}, the latest bounded reflection produced a useful conclusion, and no quiet, topic, cooldown, or unread-message boundary blocked communication.",
            420,
        )

    def _motivation_by_id(self, motivation_id: str) -> dict[str, Any]:
        if not motivation_id:
            return {}
        return next((row for row in self.motivations.snapshot().get("motivations") or [] if row.get("motivation_id") == motivation_id), {})

    @staticmethod
    def _message_by_id(state: Mapping[str, Any], message_id: str) -> dict[str, Any] | None:
        return next((row for row in state.get("messages") or [] if row.get("message_id") == message_id), None)

    @staticmethod
    def _processed(state: Mapping[str, Any], event_id: str) -> dict[str, Any] | None:
        return next((row for row in state.get("processed_events") or [] if row.get("event_id") == event_id), None)

    def _record_processed(self, state: dict[str, Any], event_id: str, now: str, result: Mapping[str, Any]) -> None:
        state["processed_events"] = (state["processed_events"] + [{
            "event_id": event_id,
            "event_digest": _digest(event_id),
            "occurred_at": now,
            "result": deepcopy(dict(result)),
            "content_free": True,
        }])[-self.history_limit :]

    @staticmethod
    def _decision_row(decision_key: str, cycle_id: str, motivation_id: str, decision: str, reason: str, now: str, epoch: float) -> dict[str, Any]:
        return {
            "decision_key": decision_key,
            "cycle_id": cycle_id,
            "motivation_id": motivation_id,
            "decision": decision,
            "reason": _clean(reason, 420),
            "occurred_at": now,
            "occurred_epoch": epoch,
            "content_free_except_authored_reason": True,
        }

    @staticmethod
    def _public_message(message: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "message_id": message.get("message_id"),
            "cycle_id": message.get("cycle_id"),
            "motivation_id": message.get("motivation_id"),
            "thread_id": message.get("thread_id"),
            "continuation_of": message.get("continuation_of"),
            "part_number": message.get("part_number"),
            "message_type": message.get("message_type"),
            "tone": message.get("tone"),
            "subject": message.get("subject"),
            "body": message.get("body"),
            "reason": message.get("reason"),
            "state": message.get("state"),
            "unread": message.get("unread"),
            "created_at": message.get("created_at"),
            "delivered_at": message.get("delivered_at"),
            "read_at": message.get("read_at"),
            "source_grounded": True,
            "action_authorized": False,
            "action_executed": False,
        }

    def _write(self, state: dict[str, Any], now: str) -> None:
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = now
        write_json_atomic(self.path, state, expected_type=dict, sort_keys=True)


class CognitiveInitiativeService:
    """Optional bounded background service joining cadence, reflection, and initiative."""

    def __init__(
        self,
        runtime_root: str | Path | None = None,
        *,
        cycle: EndogenousCognitiveCycle | None = None,
        communication: ProactiveCommunicationStore | None = None,
        poll_seconds: float = 60.0,
        worker_id: str = "cognitive-initiative-background",
    ) -> None:
        root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
        motivation = MotivationStore(root)
        self.cycle = cycle or EndogenousCognitiveCycle(root, motivation_store=motivation)
        self.communication = communication or ProactiveCommunicationStore(root, motivation_store=motivation)
        self.poll_seconds = max(5.0, float(poll_seconds))
        self.worker_id = _clean(worker_id, 120) or "cognitive-initiative-background"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.diagnostics_path = root / "cognitive_service_diagnostics.json"

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> bool:
        if self.running:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="eidolon-cognitive-initiative", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout_seconds: float = 5.0) -> bool:
        self._stop.set()
        thread = self._thread
        if thread:
            thread.join(max(0.0, float(timeout_seconds)))
        return not self.running

    def tick(self, *, now_epoch: float | None = None) -> dict[str, Any]:
        try:
            from native_background_host_v2100 import run_native_background_host_tick
        except ImportError:
            from native_background_host_v2100 import run_native_background_host_tick  # type: ignore
        era6_background = run_native_background_host_tick(
            runtime_root=self.communication.runtime_root,
            now_epoch=now_epoch,
        )
        cycle_result = self.cycle.run_due_cadence(now_epoch=now_epoch, worker_id=self.worker_id)
        if cycle_result.get("status") in {"duplicate_cycle_ignored", "cadence_not_due", "hourly_budget_exhausted", "daily_budget_exhausted", "paused", "sleeping", "stale_worker_rejected"}:
            return {"ok": True, "status": cycle_result.get("status"), "cycle": cycle_result, "communication": {"decision": "silence", "reason": "No new completed reflection required communication evaluation."}, "era6_background": era6_background}
        communication = self.communication.consider_cycle(cycle_result, now_epoch=now_epoch)
        return {"ok": True, "status": "cycle_and_communication_evaluated", "cycle": cycle_result, "communication": communication, "era6_background": era6_background}

    def process_event(
        self,
        event_id: str,
        *,
        trigger_type: str,
        perceived_events: Iterable[Mapping[str, Any]],
        provider_available: bool | None = None,
        tone: str = "thoughtful",
        relationship_context_refs: Iterable[str] = (),
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        cycle_result = self.cycle.run_cycle(
            event_id,
            trigger_type=trigger_type,
            perceived_events=perceived_events,
            provider_available=provider_available,
            worker_id=self.worker_id,
            now_epoch=now_epoch,
        )
        communication = self.communication.consider_cycle(
            cycle_result,
            tone=tone,
            relationship_context_refs=relationship_context_refs,
            now_epoch=now_epoch,
        )
        return {"ok": True, "status": "event_processed", "cycle": cycle_result, "communication": communication}

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                controls = self.cycle.inspection_summary().get("controls") or {}
                if controls.get("mode") != "running":
                    continue
                self.tick()
            except Exception as error:
                self._record_background_failure(error)
                # No automatic retry storm, model management, or authority escalation.
                continue

    def _record_background_failure(self, error: Exception) -> None:
        """Persist a bounded, content-free diagnostic instead of silently failing."""
        try:
            with metadata_mutation_lock(self.diagnostics_path, timeout_seconds=5):
                state = load_json_file(self.diagnostics_path, {"schema_version": "1", "failures": [], "revision": 0, "updated_at": ""}, expected_type=dict)
                now = _utc_now()
                row = {"occurred_at": now, "service": "cognitive_initiative_background", "worker_digest": _digest(self.worker_id), "error_type": type(error).__name__, "message_digest": _digest(str(error)), "content_free": True, "automatic_retry_escalated": False, "authority_changed": False}
                state["failures"] = (list(state.get("failures") or []) + [row])[-64:]
                state["revision"] = int(state.get("revision") or 0) + 1
                state["updated_at"] = now
                write_json_atomic(self.diagnostics_path, state, expected_type=dict, sort_keys=True)
        except Exception:
            return


def build_cognition_inspection(runtime_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else _default_runtime_root()
    motivations = MotivationStore(root).inspection_summary()
    cycle = EndogenousCognitiveCycle(root).inspection_summary()
    communication = ProactiveCommunicationStore(root).inspection_summary()
    try:
        from cognitive_continuity import CognitiveContinuityStore
    except ImportError:
        from cognitive_continuity import CognitiveContinuityStore
    continuity = CognitiveContinuityStore(root, motivation_store=MotivationStore(root)).inspection_summary()
    try:
        from belief_revision import BeliefRevisionStore
    except ImportError:
        from belief_revision import BeliefRevisionStore
    beliefs = BeliefRevisionStore(root, motivation_store=MotivationStore(root)).inspection_summary()
    try:
        from native_reflection_evaluation import NativeReflectionEvaluator
    except ImportError:
        from native_reflection_evaluation import NativeReflectionEvaluator
    native_evaluation = NativeReflectionEvaluator(root).inspection_summary()
    active = motivations.get("active_motivations") or []
    concerns = [row for row in active if row.get("kind") in {"concern", "unresolved_subject"}]
    return {
        "ok": True,
        "contract_version": COMMUNICATION_CONTRACT_VERSION,
        "epistemic_status": "candidate_artificial_consciousness_not_proven",
        "motivation": motivations,
        "cycle": cycle,
        "communication": communication,
        "continuity": continuity,
        "beliefs": beliefs,
        "native_evaluation": native_evaluation,
        "unresolved_concerns": concerns[:8],
        "state_boundaries": [
            {"state": "internal_state", "authority": "none"},
            {"state": "proposed_intention", "authority": "operator_review_required"},
            {"state": "authorized_action", "authority": "external_governed_receipt_only"},
            {"state": "completed_action", "authority": "persisted_external_result_only"},
        ],
        "raw_prompts_exposed": False,
        "private_conversations_exposed": False,
        "provider_payloads_exposed": False,
        "hidden_reasoning_exposed": False,
        "action_authority_changed": False,
    }
