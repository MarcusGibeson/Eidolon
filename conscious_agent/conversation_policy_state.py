from __future__ import annotations

"""v1159.0-v1159.2 canonical bounded ordinary-conversation policy state.

The state consolidates already-selected response intent, contextual presentation,
and follow-up/silence policy. It is prompt data only: it grants no approval,
authorization, execution, turn initiation, installation, promotion, or
certification authority.
"""

from dataclasses import dataclass, asdict
import hashlib
import json
import re
from typing import Any

CONTRACT_VERSION = "v1159.8"
SCHEMA_VERSION = "1"
MAX_PROMPT_CHARS = 1800
_TOKEN = re.compile(r"[^a-z0-9_:-]+")

_ALLOWED_INTENTS = {
    "direct_answer", "explanation", "clarification", "acknowledgment", "summary",
    "correction", "follow_up", "governed_approval_request",
    "defer_insufficient_evidence", "intentional_silence",
}
_ALLOWED_CONTEXT = {"suppressed", "implicit", "bounded_explicit"}
_ALLOWED_DISPOSITIONS = {
    "answer_only", "ask_one_question", "answer_then_one_question",
    "answer_then_optional_question", "intentional_silence",
}
_ALLOWED_SCOPE = {"none", "missing_information_only", "current_topic_only"}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _token(value: Any, default: str, maximum: int = 80) -> str:
    cleaned = _TOKEN.sub("_", str(value or default).lower()).strip("_")[:maximum]
    return cleaned or default


@dataclass(frozen=True)
class ConversationPolicyState:
    selected_intent: str
    intent_confidence: str
    intent_ambiguous: bool
    context_application: str
    warmth: str
    familiarity: str
    directness: str
    continuity_reference: str
    emotional_calibration: str
    output_disposition: str
    question_scope: str
    max_follow_up_questions: int
    generic_offer_prohibited: bool
    explicit_silence_verified: bool
    emit_no_substantive_content: bool
    literal_request_precedence: bool
    selected_intent_precedence: bool
    protected_constraints_precedence: bool
    approval_granted: bool
    authorization_granted: bool
    execution_permitted: bool
    may_initiate_new_turn: bool
    provider_contacted_for_policy: bool
    component_recovery_present: bool
    component_conflict_present: bool
    response_intent_digest: str
    contextual_behavior_digest: str
    follow_up_silence_digest: str
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_memory_text": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "runtime_mutated": False,
        })
        result["policy_state_digest"] = _digest(result)
        return result


def _component_digest(value: Any, advertised: str) -> str:
    if isinstance(value, dict):
        candidate = str(value.get(advertised) or "")
        if re.fullmatch(r"[0-9a-f]{64}", candidate):
            return candidate
        public = {k: v for k, v in value.items() if k not in {"prompt_section", "evidence", "candidates"}}
        return _digest(public)
    return _digest({"malformed": True})


def build_conversation_policy_state(
    response_intent: dict[str, Any] | None,
    contextual_behavior: dict[str, Any] | None,
    follow_up_silence: dict[str, Any] | None,
) -> dict[str, Any]:
    intent = response_intent if isinstance(response_intent, dict) else {}
    behavior = contextual_behavior if isinstance(contextual_behavior, dict) else {}
    follow = follow_up_silence if isinstance(follow_up_silence, dict) else {}
    recovered = not all(isinstance(v, dict) for v in (response_intent, contextual_behavior, follow_up_silence))

    selected = str(intent.get("selected_intent") or intent.get("intent") or "direct_answer")
    if selected not in _ALLOWED_INTENTS:
        selected = "direct_answer"
        recovered = True
    confidence = _token(intent.get("confidence"), "low", 24)
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
        recovered = True

    context_application = str(behavior.get("context_application") or "suppressed")
    if context_application not in _ALLOWED_CONTEXT:
        context_application = "suppressed"
        recovered = True

    disposition = str(follow.get("output_disposition") or "answer_only")
    if disposition not in _ALLOWED_DISPOSITIONS:
        disposition = "answer_only"
        recovered = True
    scope = str(follow.get("question_scope") or "none")
    if scope not in _ALLOWED_SCOPE:
        scope = "none"
        recovered = True

    explicit_silence = follow.get("explicit_silence_verified") is True
    if disposition == "intentional_silence" and not explicit_silence:
        disposition = "answer_only"
        scope = "none"
        recovered = True
    if explicit_silence:
        selected = "intentional_silence"
        disposition = "intentional_silence"
        scope = "none"
        max_questions = 0
    else:
        try:
            requested_questions = int(follow.get("max_follow_up_questions") or 0)
        except (TypeError, ValueError):
            requested_questions = 0
            recovered = True
        max_questions = 1 if requested_questions > 0 and disposition in {
            "ask_one_question", "answer_then_one_question", "answer_then_optional_question"
        } else 0
        if max_questions == 0:
            scope = "none"
            if disposition != "answer_only":
                disposition = "answer_only"
                recovered = True

    conflict = bool(
        behavior.get("conflicting_context_suppressed")
        or behavior.get("context_integrity") == "conflicted"
        or follow.get("contextual_conflict")
    )
    if conflict:
        context_application = "suppressed"
        max_questions = 0
        scope = "none"
        if disposition != "intentional_silence":
            disposition = "answer_only"

    state = ConversationPolicyState(
        selected_intent=selected,
        intent_confidence=confidence,
        intent_ambiguous=bool(intent.get("ambiguous") or intent.get("low_confidence")),
        context_application=context_application,
        warmth=_token(behavior.get("warmth"), "neutral", 32),
        familiarity=_token(behavior.get("familiarity"), "ordinary", 32),
        directness=_token(behavior.get("directness"), "direct", 32),
        continuity_reference=_token(behavior.get("continuity_reference"), "none", 32),
        emotional_calibration=_token(behavior.get("emotional_calibration"), "neutral", 32),
        output_disposition=disposition,
        question_scope=scope,
        max_follow_up_questions=max_questions,
        generic_offer_prohibited=True,
        explicit_silence_verified=explicit_silence,
        emit_no_substantive_content=disposition == "intentional_silence",
        literal_request_precedence=True,
        selected_intent_precedence=True,
        protected_constraints_precedence=True,
        approval_granted=False,
        authorization_granted=False,
        execution_permitted=False,
        may_initiate_new_turn=False,
        provider_contacted_for_policy=False,
        component_recovery_present=recovered or bool(
            intent.get("selection_recovered") or behavior.get("policy_recovered") or follow.get("policy_recovered")
        ),
        component_conflict_present=conflict,
        response_intent_digest=_component_digest(intent, "selection_digest"),
        contextual_behavior_digest=_component_digest(behavior, "policy_digest"),
        follow_up_silence_digest=_component_digest(follow, "policy_digest"),
    )
    public = state.public_summary()
    public["prompt_section"] = conversation_policy_prompt_section(public)
    return public


def conversation_policy_prompt_section(policy: dict[str, Any]) -> str:
    projection_keys = (
        "selected_intent", "intent_confidence", "intent_ambiguous",
        "context_application", "warmth", "familiarity", "directness",
        "continuity_reference", "emotional_calibration", "output_disposition",
        "question_scope", "max_follow_up_questions", "generic_offer_prohibited",
        "explicit_silence_verified", "emit_no_substantive_content",
        "literal_request_precedence", "selected_intent_precedence",
        "protected_constraints_precedence", "approval_granted",
        "authorization_granted", "execution_permitted", "may_initiate_new_turn",
    )
    projection = {key: policy.get(key) for key in projection_keys}
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    section = '<conversation_policy_state data_only="true" authority="none">' + payload + '</conversation_policy_state>'
    if len(section) > MAX_PROMPT_CHARS:
        raise ValueError("Conversation policy prompt exceeded hard bound")
    return section

# v1159.3-v1159.5 durable canonical conversation-policy continuity.
from pathlib import Path
import os
import uuid
import time

_POLICY_STATE_SCHEMA = "2"
_MAX_PENDING_AGE_SECONDS = 86400
_MAX_CHANGED_FIELDS = 16
_TRANSITION_FIELDS = (
    "selected_intent", "intent_confidence", "context_application", "warmth",
    "familiarity", "directness", "continuity_reference", "emotional_calibration",
    "output_disposition", "question_scope", "max_follow_up_questions",
    "explicit_silence_verified", "component_recovery_present", "component_conflict_present",
)


def _policy_root() -> Path:
    base = Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data").expanduser().resolve()
    return base / "conversation_policy_state"


def _safe_id(value: Any, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")[:120]
    return token or fallback


def _bounded_scalar(value: Any, default: Any) -> Any:
    if isinstance(default, bool):
        return value is True
    if isinstance(default, int):
        try:
            return max(0, min(int(value), 1))
        except (TypeError, ValueError):
            return default
    return _token(value, str(default), 64)


def _canonical_projection(policy: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "selected_intent": "direct_answer", "intent_confidence": "low",
        "intent_ambiguous": False, "context_application": "suppressed",
        "warmth": "neutral", "familiarity": "ordinary", "directness": "direct",
        "continuity_reference": "none", "emotional_calibration": "neutral",
        "output_disposition": "answer_only", "question_scope": "none",
        "max_follow_up_questions": 0, "generic_offer_prohibited": True,
        "explicit_silence_verified": False, "emit_no_substantive_content": False,
        "literal_request_precedence": True, "selected_intent_precedence": True,
        "protected_constraints_precedence": True, "approval_granted": False,
        "authorization_granted": False, "execution_permitted": False,
        "may_initiate_new_turn": False, "provider_contacted_for_policy": False,
        "component_recovery_present": False, "component_conflict_present": False,
        "response_intent_digest": "missing", "contextual_behavior_digest": "missing",
        "follow_up_silence_digest": "missing", "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
    }
    projection = {key: _bounded_scalar(policy.get(key), default) for key, default in defaults.items()}
    # Authority and precedence invariants are reconstructed, never trusted from persisted input.
    projection.update({
        "literal_request_precedence": True, "selected_intent_precedence": True,
        "protected_constraints_precedence": True, "approval_granted": False,
        "authorization_granted": False, "execution_permitted": False,
        "may_initiate_new_turn": False, "provider_contacted_for_policy": False,
    })
    return projection

def _record_identity(operation_id: str, session_id: str, projection: dict[str, Any]) -> str:
    return _digest({
        "operation_id": str(operation_id),
        "session_id": str(session_id),
        "projection": projection,
    })


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _verify_base_record(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("projection"), dict):
        return False
    if value.get("schema_version") != _POLICY_STATE_SCHEMA:
        return False
    projection = _canonical_projection(value["projection"])
    if projection != value["projection"]:
        return False
    expected = _record_identity(str(value.get("operation_id") or ""), str(value.get("session_id") or ""), projection)
    return value.get("record_identity") == expected


def _load_verified_pending(path: Path, *, now_epoch: int | None = None) -> tuple[dict[str, Any] | None, str]:
    value = _load_json(path)
    if not _verify_base_record(value) or value.get("record_type") != "conversation_policy_pending" or value.get("completed") is not False:
        return None, "missing_or_invalid_pending"
    staged = value.get("staged_at_epoch")
    if not isinstance(staged, int) or staged < 0:
        return None, "missing_or_invalid_pending"
    now = int(time.time()) if now_epoch is None else int(now_epoch)
    if now - staged > _MAX_PENDING_AGE_SECONDS:
        return None, "stale_pending"
    return value, ""


def _load_verified_completed(path: Path) -> dict[str, Any] | None:
    value = _load_json(path)
    if not _verify_base_record(value) or value.get("record_type") != "conversation_policy_completed" or value.get("completed") is not True:
        return None
    changed = value.get("changed_fields")
    if not isinstance(changed, list) or len(changed) > _MAX_CHANGED_FIELDS or any(field not in _TRANSITION_FIELDS for field in changed):
        return None
    previous = str(value.get("previous_record_identity") or "")
    expected = _digest({"previous": previous, "current": value["record_identity"], "changed": changed})
    if value.get("transition_digest") != expected:
        return None
    expected_kind = "initial" if not previous else ("stable" if not changed else "changed")
    return value if value.get("transition_kind") == expected_kind else None

def stage_conversation_policy_state(
    policy: dict[str, Any], *, operation_id: str, session_id: str
) -> dict[str, Any]:
    """Stage content-free policy state. Staging grants no completion authority."""
    projection = _canonical_projection(policy if isinstance(policy, dict) else {})
    operation = _safe_id(operation_id, "unknown_operation")
    session = _safe_id(session_id, "unknown_session")
    identity = _record_identity(operation, session, projection)
    record = {
        "record_type": "conversation_policy_pending",
        "schema_version": _POLICY_STATE_SCHEMA,
        "operation_id": operation,
        "session_id": session,
        "projection": projection,
        "record_identity": identity,
        "completed": False,
        "staged_at_epoch": int(time.time()),
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "contains_content": False,
    }
    path = _policy_root() / "pending" / f"{operation}.json"
    try:
        _atomic_write(path, record)
        persisted = True
    except OSError:
        persisted = False
    return {
        "record_identity": identity,
        "pending_persisted": persisted,
        "completed": False,
        "contains_content": False,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
    }


def complete_conversation_policy_state(*, operation_id: str, session_id: str, now_epoch: int | None = None) -> dict[str, Any]:
    """Promote a verified pending record only after authoritative memory commit."""
    operation = _safe_id(operation_id, "unknown_operation")
    session = _safe_id(session_id, "unknown_session")
    root = _policy_root()
    archive_path = root / "operations" / f"{operation}.json"
    existing = _load_verified_completed(archive_path)
    if existing is not None:
        if existing.get("session_id") != session:
            return _completion_failure("operation_session_mismatch")
        return _completion_summary(existing, duplicate=True)

    pending_path = root / "pending" / f"{operation}.json"
    pending, failure = _load_verified_pending(pending_path, now_epoch=now_epoch)
    if pending is None:
        return _completion_failure(failure)
    if pending.get("operation_id") != operation or pending.get("session_id") != session:
        return _completion_failure("operation_session_mismatch")

    completed_path = root / "completed" / f"{session}.json"
    previous_raw = _load_json(completed_path)
    previous = _load_verified_completed(completed_path)
    if previous_raw is not None and previous is None:
        return _completion_failure("invalid_previous_completed")
    prior_projection = previous.get("projection", {}) if previous else {}
    projection = pending["projection"]
    changed = [key for key in _TRANSITION_FIELDS if prior_projection.get(key) != projection.get(key)][:_MAX_CHANGED_FIELDS]
    transition_kind = "initial" if previous is None else ("stable" if not changed else "changed")
    completed = dict(pending)
    completed.update({
        "record_type": "conversation_policy_completed",
        "completed": True,
        "completed_at_epoch": int(time.time()) if now_epoch is None else int(now_epoch),
        "previous_record_identity": str(previous.get("record_identity") or "") if previous else "",
        "transition_kind": transition_kind,
        "changed_fields": changed,
        "transition_digest": _digest({"previous": str(previous.get("record_identity") or "") if previous else "", "current": pending["record_identity"], "changed": changed}),
    })
    try:
        _atomic_write(completed_path, completed)
        _atomic_write(archive_path, completed)
        pending_path.unlink(missing_ok=True)
    except OSError:
        return _completion_failure("write_failed")
    return _completion_summary(completed, duplicate=False)


def _completion_failure(reason: str) -> dict[str, Any]:
    return {
        "completed": False, "completion_failure": reason,
        "transition_kind": "unavailable", "changed_fields": [], "contains_content": False,
        "duplicate_completion": False, "approval_granted": False,
        "authorization_granted": False, "execution_permitted": False,
    }


def _completion_summary(completed: dict[str, Any], *, duplicate: bool) -> dict[str, Any]:
    changed = list(completed.get("changed_fields") or [])[:_MAX_CHANGED_FIELDS]
    return {
        "completed": True, "record_identity": completed["record_identity"],
        "previous_record_identity": str(completed.get("previous_record_identity") or ""),
        "transition_kind": completed["transition_kind"], "changed_fields": changed,
        "changed_field_count": len(changed), "transition_digest": completed["transition_digest"],
        "duplicate_completion": duplicate, "contains_content": False,
        "approval_granted": False, "authorization_granted": False, "execution_permitted": False,
    }
