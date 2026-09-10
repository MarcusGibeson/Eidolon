from __future__ import annotations

"""Era 5 bounded affective state and regulation.

The state is a content-free runtime signal used only to influence expression and
attention.  It stores no conversation text, grants no authority, and does not
claim subjective experience.  Read/check/write updates are serialized so a
concurrent turn cannot silently overwrite another affect update.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from json_storage import AtomicJsonWriteError, load_json_file, write_json_atomic
from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
from paths import DATA_DIR

CONTRACT_VERSION = "v1975.9"
SCHEMA_VERSION = "1"
STATE_FILE = "affective_regulation.json"
MAX_PROCESSED_EVENTS = 256
MAX_CAUSES = 16
AXES = (
    "valence", "arousal", "concern", "frustration", "excitement",
    "confidence", "attachment", "recovery",
)

_POSITIVE = re.compile(r"\b(?:great|awesome|good|happy|excited|proud|love this|nice|perfect|glad)\b", re.I)
_DISTRESS = re.compile(r"\b(?:sad|hurt|scared|worried|anxious|lonely|grief|upset|afraid|terrified)\b", re.I)
_FRUSTRATION = re.compile(r"\b(?:frustrated|annoyed|angry|mad|stuck|broken|failed|wrong again|not working)\b", re.I)
_AFFECTION = re.compile(r"\b(?:love you|care about you|miss you|affection|hug|sweetheart|dear)\b", re.I)
_CORRECTION = re.compile(r"^(?:no\b|actually\b|correction\b)|\b(?:you misunderstood|that's wrong|that is wrong|i meant)\b", re.I)
_SUCCESS = re.compile(r"\b(?:worked|fixed|passed|success|completed|resolved)\b", re.I)
_FAILURE = re.compile(r"\b(?:failed|error|crash|broken|didn't work|did not work|timeout)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _bounded(value: Any, default: float = 0.5) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return round(default, 4)


def _now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "companion" / STATE_FILE


def _default_state() -> dict[str, Any]:
    values = {
        "valence": 0.5,
        "arousal": 0.35,
        "concern": 0.25,
        "frustration": 0.15,
        "excitement": 0.25,
        "confidence": 0.55,
        "attachment": 0.30,
        "recovery": 0.75,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "updated_at": "",
        "values": values,
        "causes": [],
        "processed_events": [],
        "authority_effect": "none",
        "tone_influence_only": True,
        "attention_weight_cap": 0.2,
        "claims_subjective_experience": False,
        "raw_conversation_persisted": False,
    }


def _valid_state(value: Any) -> dict[str, Any]:
    row = deepcopy(value) if isinstance(value, dict) else _default_state()
    if not isinstance(row.get("values"), dict):
        row["values"] = _default_state()["values"]
    for axis in AXES:
        row["values"][axis] = _bounded(row["values"].get(axis), _default_state()["values"][axis])
    if not isinstance(row.get("causes"), list):
        row["causes"] = []
    if not isinstance(row.get("processed_events"), list):
        row["processed_events"] = []
    row["authority_effect"] = "none"
    row["tone_influence_only"] = True
    row["attention_weight_cap"] = min(0.2, _bounded(row.get("attention_weight_cap"), 0.2))
    row["claims_subjective_experience"] = False
    row["raw_conversation_persisted"] = False
    return row


def _signals(message: Any, contextual_behavior: Mapping[str, Any] | None = None) -> tuple[list[str], dict[str, float]]:
    text = " ".join(str(message or "")[:4096].split())
    codes: list[str] = []
    target = dict(_default_state()["values"])
    context_mood = str((contextual_behavior or {}).get("mood_signal") or "").strip().lower()
    if _POSITIVE.search(text) or context_mood == "positive":
        codes.append("positive_interaction")
        target.update(valence=0.78, excitement=0.68, arousal=0.52, frustration=0.08, recovery=0.82)
    if _DISTRESS.search(text) or context_mood == "distressed":
        codes.append("user_distress_context")
        target.update(valence=0.36, concern=0.82, arousal=0.55, excitement=0.08, recovery=0.62)
    if _FRUSTRATION.search(text):
        codes.append("friction_or_failure")
        target.update(valence=0.32, frustration=0.72, concern=max(target["concern"], 0.55), arousal=0.62, recovery=0.55)
    if _CORRECTION.search(text):
        codes.append("operator_correction")
        target.update(confidence=0.42, concern=max(target["concern"], 0.52), frustration=min(target["frustration"], 0.35), recovery=0.68)
    if _AFFECTION.search(text):
        codes.append("user_led_affection")
        target.update(valence=max(target["valence"], 0.72), attachment=0.62, concern=max(target["concern"], 0.35))
    if _SUCCESS.search(text):
        codes.append("verified_or_reported_success")
        target.update(confidence=0.72, recovery=0.86, frustration=0.06, excitement=max(target["excitement"], 0.58))
    if _FAILURE.search(text):
        codes.append("reported_failure")
        target.update(confidence=0.42, frustration=max(target["frustration"], 0.62), concern=max(target["concern"], 0.52))
    if not codes:
        codes.append("ordinary_interaction")
    return list(dict.fromkeys(codes)), {axis: _bounded(target[axis]) for axis in AXES}


def _decayed(values: Mapping[str, Any], *, elapsed_hours: float) -> dict[str, float]:
    # Drift toward a neutral baseline.  Recovery drifts upward rather than toward .5.
    baseline = _default_state()["values"]
    fraction = min(0.75, max(0.0, elapsed_hours) / 48.0)
    result: dict[str, float] = {}
    for axis in AXES:
        old = _bounded(values.get(axis), baseline[axis])
        target = baseline[axis]
        result[axis] = _bounded(old * (1.0 - fraction) + target * fraction, baseline[axis])
    return result


def _regulation(values: Mapping[str, Any]) -> dict[str, Any]:
    valence = _bounded(values.get("valence"))
    arousal = _bounded(values.get("arousal"))
    concern = _bounded(values.get("concern"))
    frustration = _bounded(values.get("frustration"))
    excitement = _bounded(values.get("excitement"))
    attachment = _bounded(values.get("attachment"))
    mixed = bool((concern >= 0.6 and excitement >= 0.6) or (frustration >= 0.6 and attachment >= 0.55))
    if frustration >= 0.62 or arousal >= 0.78:
        expression = "deliberate_grounded"
    elif concern >= 0.65:
        expression = "gentle_attentive"
    elif excitement >= 0.65 and valence >= 0.62:
        expression = "lively_bounded"
    elif attachment >= 0.58:
        expression = "warm_user_led"
    else:
        expression = "steady_natural"
    return {
        "expression_mode": expression,
        "mixed_state": mixed,
        "humor_suppressed": concern >= 0.7 or frustration >= 0.65,
        "question_pressure_cap": 0.15 if concern >= 0.7 else 0.35,
        "initiative_cap": 0.20 if frustration >= 0.65 else 0.40,
        "affection_escalation_allowed": False,
        "coercion_allowed": False,
        "guilt_allowed": False,
        "authority_effect": "none",
        "action_authority_granted": False,
        "file_authority_granted": False,
        "installation_authority_granted": False,
    }


def public_affective_state(state: Mapping[str, Any]) -> dict[str, Any]:
    row = _valid_state(state)
    public = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": int(row.get("revision") or 0),
        "updated_at": str(row.get("updated_at") or ""),
        "values": {axis: _bounded(row["values"].get(axis)) for axis in AXES},
        "cause_codes": [str(item.get("code") or "")[:48] for item in row.get("causes", [])[-MAX_CAUSES:] if isinstance(item, dict)],
        "processed_event_count": len(row.get("processed_events", [])),
        "regulation": _regulation(row["values"]),
        "authority_effect": "none",
        "tone_influence_only": True,
        "claims_subjective_experience": False,
        "raw_conversation_persisted": False,
        "contains_message_content": False,
        "contains_memory_content": False,
        "contains_private_chain_of_thought": False,
    }
    public["state_digest"] = _digest(public)
    return public


def read_affective_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def update_affective_regulation(
    message: Any,
    *,
    event_id: str,
    contextual_behavior: Mapping[str, Any] | None = None,
    runtime_root: str | Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    event_token = str(event_id or "").strip()
    if not event_token:
        return {"ok": False, "status": "event_id_required", "state": public_affective_state(_default_state()), "idempotent": False}
    event_digest = _digest(event_token)
    path = _state_path(runtime_root)
    current_time = _now(now)
    try:
        with metadata_mutation_lock(path, timeout_seconds=5.0):
            state = _valid_state(load_json_file(path, _default_state(), expected_type=dict))
            processed = [row for row in state.get("processed_events", []) if isinstance(row, dict)]
            if any(str(row.get("event_digest") or "") == event_digest for row in processed):
                return {"ok": True, "status": "affective_event_replayed", "state": public_affective_state(state), "idempotent": True}

            previous_time = _parse_time(state.get("updated_at"))
            elapsed_hours = max(0.0, (current_time - previous_time).total_seconds() / 3600.0) if previous_time else 0.0
            base = _decayed(state["values"], elapsed_hours=elapsed_hours)
            codes, targets = _signals(message, contextual_behavior)
            next_values: dict[str, float] = {}
            for axis in AXES:
                # A moderate update keeps affect responsive without allowing one turn to dominate.
                weight = 0.30
                if axis in {"attachment", "confidence"}:
                    weight = 0.18
                next_values[axis] = _bounded(base[axis] * (1.0 - weight) + targets[axis] * weight)

            cause_rows = [row for row in state.get("causes", []) if isinstance(row, dict)][-MAX_CAUSES:]
            for code in codes:
                cause_rows.append({"code": code, "event_digest": event_digest, "occurred_at": current_time.isoformat()})
            cause_rows = cause_rows[-MAX_CAUSES:]
            processed.append({"event_digest": event_digest, "occurred_at": current_time.isoformat()})
            processed = processed[-MAX_PROCESSED_EVENTS:]
            updated = {
                **state,
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "revision": int(state.get("revision") or 0) + 1,
                "updated_at": current_time.isoformat(),
                "values": next_values,
                "causes": cause_rows,
                "processed_events": processed,
                "authority_effect": "none",
                "tone_influence_only": True,
                "attention_weight_cap": 0.2,
                "claims_subjective_experience": False,
                "raw_conversation_persisted": False,
            }
            write_json_atomic(path, updated, expected_type=dict, sort_keys=True, coordinate=False)
            return {"ok": True, "status": "affective_state_updated", "state": public_affective_state(updated), "idempotent": False}
    except (MetadataMutationBusy, AtomicJsonWriteError, OSError) as error:
        current = read_affective_state(runtime_root=runtime_root)
        return {
            "ok": False,
            "status": getattr(error, "status", "affective_state_write_blocked"),
            "state": public_affective_state(current),
            "idempotent": False,
            "safe_retry": bool(getattr(error, "safe_retry", True)),
            "uncertain_result": bool(getattr(error, "uncertain_result", False)),
        }


def affective_prompt_section(state: Mapping[str, Any]) -> str:
    public = public_affective_state(state)
    values = public["values"]
    regulation = public["regulation"]
    return (
        "ERA 5 AFFECTIVE REGULATION\n"
        f"Expression state: {regulation['expression_mode']}; valence={values['valence']:.2f}, arousal={values['arousal']:.2f}, "
        f"concern={values['concern']:.2f}, frustration={values['frustration']:.2f}, excitement={values['excitement']:.2f}.\n"
        "Use this only to modulate tone and attention. It is not proof of subjective feeling, never grants authority, and must not coerce, guilt, escalate intimacy, or override the current request."
    )


__all__ = [
    "CONTRACT_VERSION", "AXES", "read_affective_state", "update_affective_regulation",
    "public_affective_state", "affective_prompt_section",
]
