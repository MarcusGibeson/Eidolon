from __future__ import annotations

"""Era 7 provider-neutral voice/audio interaction contracts.

This module owns portable turn-state, timestamps, interruption, silence,
prosody, and transcript reconciliation evidence. It never opens an audio
device, records audio, contacts STT/TTS providers, or speaks by itself.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from paths import DATA_DIR
from voice_foundation import VERSION as RETAINED_VOICE_FOUNDATION_VERSION, IMPLEMENTATION as RETAINED_VOICE_IMPLEMENTATION

CONTRACT_VERSION = "v2175.9"
SCHEMA_VERSION = "1"
STATE_FILE = "era7_voice_state.json"
MAX_TURNS = 64
MAX_SEGMENTS = 128
VOICE_STATES = ("idle", "listening", "transcribing", "thinking", "speaking", "interrupted", "cancelled", "completed", "failed")
PROSODY_FIELDS = ("rate", "pitch", "energy", "warmth")

_DENIED = {
    "microphone_accessed": False,
    "speaker_accessed": False,
    "audio_recorded": False,
    "audio_played": False,
    "stt_provider_contacted": False,
    "tts_provider_contacted": False,
    "provider_contacted": False,
    "message_sent": False,
    "tool_executed": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _token(value: Any, limit: int = 100) -> str:
    text = str(value or "").strip().lower()
    if not text or len(text) > limit or not re.fullmatch(r"[a-z0-9_.:-]+", text):
        return ""
    return text


def _state_path(runtime_root: str | Path | None = None) -> Path:
    root = Path(runtime_root).expanduser().resolve() if runtime_root else DATA_DIR
    return root / "voice" / STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "revision": 0,
        "profile": {
            "stt_adapter": "unconfigured",
            "tts_adapter": "unconfigured",
            "input_device_digest": "",
            "output_device_digest": "",
            "barge_in_enabled": True,
            "silence_timeout_ms": 1800,
            "prosody": {"rate": 0.5, "pitch": 0.5, "energy": 0.5, "warmth": 0.65},
        },
        "turns": [],
        "processed_events": [],
        "raw_transcript_persisted": False,
        "raw_audio_persisted": False,
    }


def _valid_state(value: Any) -> dict[str, Any]:
    state = deepcopy(value) if isinstance(value, dict) else _default_state()
    state.setdefault("revision", 0)
    if not isinstance(state.get("profile"), dict):
        state["profile"] = deepcopy(_default_state()["profile"])
    if not isinstance(state.get("turns"), list): state["turns"] = []
    if not isinstance(state.get("processed_events"), list): state["processed_events"] = []
    state["raw_transcript_persisted"] = False
    state["raw_audio_persisted"] = False
    return state


def read_voice_state(*, runtime_root: str | Path | None = None) -> dict[str, Any]:
    return _valid_state(load_json_file(_state_path(runtime_root), _default_state(), expected_type=dict))


def public_voice_state(state: Mapping[str, Any]) -> dict[str, Any]:
    profile = dict(state.get("profile") or {})
    turns = [dict(x) for x in state.get("turns", []) if isinstance(x, Mapping)]
    active = next((x for x in reversed(turns) if x.get("state") not in {"completed", "cancelled", "failed"}), None)
    result = {
        "contract_version": CONTRACT_VERSION,
        "revision": int(state.get("revision") or 0),
        "profile": {
            "stt_adapter": str(profile.get("stt_adapter") or "unconfigured"),
            "tts_adapter": str(profile.get("tts_adapter") or "unconfigured"),
            "input_device_configured": bool(profile.get("input_device_digest")),
            "output_device_configured": bool(profile.get("output_device_digest")),
            "barge_in_enabled": bool(profile.get("barge_in_enabled", True)),
            "silence_timeout_ms": int(profile.get("silence_timeout_ms") or 0),
            "prosody": dict(profile.get("prosody") or {}),
        },
        "turn_count": len(turns),
        "active_turn": {k: active.get(k) for k in ("turn_id", "state", "segment_count", "interrupted", "turn_digest") if k in active} if active else None,
        "raw_transcript_persisted": False,
        "raw_audio_persisted": False,
        "retained_voice_foundation_version": RETAINED_VOICE_FOUNDATION_VERSION,
        "retained_voice_implementation": RETAINED_VOICE_IMPLEMENTATION,
        "new_native_audio_stack_created": False,
        **_DENIED,
    }
    result["state_digest"] = _digest(result)
    return result


def configure_voice_profile(
    *, stt_adapter: str, tts_adapter: str, input_device_digest: str = "", output_device_digest: str = "",
    barge_in_enabled: bool = True, silence_timeout_ms: int = 1800, prosody: Mapping[str, Any] | None = None,
    expected_state_digest: str = "", event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    path = _state_path(runtime_root)
    event_digest = _digest(str(event_id or ""))
    if not str(event_id or "").strip():
        return {"ok": False, "status": "voice_event_id_required", **_DENIED}
    stt = _token(stt_adapter, 80); tts = _token(tts_adapter, 80)
    if not stt or not tts:
        return {"ok": False, "status": "typed_audio_adapters_required", **_DENIED}
    if input_device_digest and not _hex64(input_device_digest):
        return {"ok": False, "status": "invalid_input_device_digest", **_DENIED}
    if output_device_digest and not _hex64(output_device_digest):
        return {"ok": False, "status": "invalid_output_device_digest", **_DENIED}
    try:
        timeout = max(300, min(int(silence_timeout_ms), 15000))
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "invalid_voice_silence_timeout", **_DENIED}
    p = {}
    for key in PROSODY_FIELDS:
        try:
            value = float((prosody or {}).get(key, 0.5 if key != "warmth" else 0.65))
            if not math.isfinite(value):
                raise ValueError
            p[key] = round(max(0.0, min(1.0, value)), 3)
        except (TypeError, ValueError, OverflowError):
            return {"ok": False, "status": "invalid_voice_prosody", "field": key, **_DENIED}
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_voice_state(runtime_root=runtime_root)
        current_public = public_voice_state(state)
        if expected_state_digest and expected_state_digest != current_public["state_digest"]:
            return {"ok": False, "status": "stale_voice_state_digest", "state": current_public, **_DENIED}
        if any(x.get("event_digest") == event_digest for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            return {"ok": True, "status": "voice_profile_event_replayed", "state": current_public, "idempotent": True, **_DENIED}
        state["profile"] = {
            "stt_adapter": stt, "tts_adapter": tts,
            "input_device_digest": _hex64(input_device_digest), "output_device_digest": _hex64(output_device_digest),
            "barge_in_enabled": bool(barge_in_enabled), "silence_timeout_ms": timeout, "prosody": p,
        }
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "kind": "profile"}])[-256:]
        write_json_atomic(path, state)
        return {"ok": True, "status": "voice_profile_configured_no_device_contact", "state": public_voice_state(state), **_DENIED}


def begin_voice_turn(
    *, turn_id: str, input_audio_digest: str, event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    tid = _token(turn_id, 120); audio = _hex64(input_audio_digest); event = str(event_id or "").strip()
    if not tid or not audio or not event:
        return {"ok": False, "status": "typed_turn_audio_digest_and_event_required", **_DENIED}
    path = _state_path(runtime_root); event_digest = _digest(event)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_voice_state(runtime_root=runtime_root)
        if any(x.get("event_digest") == event_digest for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            existing = next((x for x in reversed(state["turns"]) if x.get("turn_id") == tid), None)
            return {"ok": True, "status": "voice_turn_begin_replayed", "turn": existing or {}, "idempotent": True, **_DENIED}
        active = next((x for x in reversed(state["turns"]) if x.get("state") not in {"completed", "cancelled", "failed"}), None)
        if active:
            return {"ok": False, "status": "voice_turn_already_active", "active_turn_id": active.get("turn_id"), **_DENIED}
        if any(x.get("turn_id") == tid for x in state["turns"] if isinstance(x, Mapping)):
            return {"ok": False, "status": "voice_turn_id_already_used", **_DENIED}
        turn = {
            "turn_id": tid, "input_audio_digest": audio, "state": "listening", "segments": [], "segment_count": 0,
            "interrupted": False, "speech_request_digest": "", "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        turn["turn_digest"] = _digest({k: v for k, v in turn.items() if k != "created_at"})
        state["turns"] = (state.get("turns", []) + [turn])[-MAX_TURNS:]
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": event_digest, "kind": "begin", "turn_id": tid}])[-256:]
        write_json_atomic(path, state)
        return {"ok": True, "status": "voice_turn_prepared_no_microphone_contact", "turn": dict(turn), **_DENIED}


def _mutate_turn(turn_id: str, event_id: str, runtime_root: str | Path | None, callback) -> dict[str, Any]:
    tid = _token(turn_id, 120); event = str(event_id or "").strip()
    if not tid or not event:
        return {"ok": False, "status": "voice_turn_and_event_required", **_DENIED}
    path = _state_path(runtime_root); ed = _digest(event)
    with metadata_mutation_lock(path, timeout_seconds=5.0):
        state = read_voice_state(runtime_root=runtime_root)
        if any(x.get("event_digest") == ed for x in state.get("processed_events", []) if isinstance(x, Mapping)):
            existing = next((x for x in reversed(state["turns"]) if x.get("turn_id") == tid), None)
            return {"ok": True, "status": "voice_turn_event_replayed", "turn": dict(existing or {}), "idempotent": True, **_DENIED}
        idx = next((i for i in range(len(state["turns"])-1, -1, -1) if state["turns"][i].get("turn_id") == tid), -1)
        if idx < 0:
            return {"ok": False, "status": "voice_turn_not_found", **_DENIED}
        turn = deepcopy(state["turns"][idx])
        status = callback(turn)
        if status in {"voice_turn_terminal", "voice_turn_terminal_immutable"}:
            return {"ok": False, "status": str(status), "turn": dict(state["turns"][idx]), **_DENIED}
        turn["turn_digest"] = _digest({k: v for k, v in turn.items() if k not in {"created_at", "updated_at"}})
        turn["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        state["turns"][idx] = turn
        state["revision"] = int(state.get("revision") or 0) + 1
        state["processed_events"] = (state.get("processed_events", []) + [{"event_digest": ed, "kind": str(status), "turn_id": tid}])[-256:]
        write_json_atomic(path, state)
        return {"ok": True, "status": str(status), "turn": dict(turn), **_DENIED}


def record_transcript_segment(
    *, turn_id: str, transcript_digest: str, confidence: float, start_ms: int, end_ms: int,
    event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    td = _hex64(transcript_digest)
    try:
        start = int(start_ms); end = int(end_ms)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "valid_transcript_digest_and_timestamps_required", **_DENIED}
    if not td or start < 0 or end < start:
        return {"ok": False, "status": "valid_transcript_digest_and_timestamps_required", **_DENIED}
    try:
        confidence_value = float(confidence)
        if not math.isfinite(confidence_value):
            raise ValueError
        conf = round(max(0.0, min(1.0, confidence_value)), 3)
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "valid_transcript_confidence_required", **_DENIED}
    def cb(turn):
        if turn.get("state") in {"completed", "cancelled", "failed"}: return "voice_turn_terminal"
        seg = {"transcript_digest": td, "confidence": conf, "start_ms": start, "end_ms": end}
        if not any(x.get("transcript_digest") == td and x.get("start_ms") == start for x in turn.get("segments", [])):
            turn["segments"] = (turn.get("segments", []) + [seg])[-MAX_SEGMENTS:]
        turn["segment_count"] = len(turn["segments"]); turn["state"] = "transcribing"
        return "voice_transcript_segment_recorded"
    return _mutate_turn(turn_id, event_id, runtime_root, cb)


def prepare_speech_request(
    *, turn_id: str, response_text_digest: str, event_id: str, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    rd = _hex64(response_text_digest)
    if not rd:
        return {"ok": False, "status": "response_text_digest_required", **_DENIED}
    def cb(turn):
        if turn.get("state") in {"completed", "cancelled", "failed"}: return "voice_turn_terminal"
        turn["state"] = "speaking"; turn["speech_request_digest"] = _digest({"turn_id": turn.get("turn_id"), "response_text_digest": rd})
        turn["response_text_digest"] = rd
        return "voice_speech_request_prepared_not_played"
    return _mutate_turn(turn_id, event_id, runtime_root, cb)


def handle_barge_in(*, turn_id: str, event_id: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = read_voice_state(runtime_root=runtime_root); enabled = bool((state.get("profile") or {}).get("barge_in_enabled", True))
    def cb(turn):
        if not enabled: return "voice_barge_in_disabled"
        if turn.get("state") != "speaking": return "voice_barge_in_not_applicable"
        turn["state"] = "interrupted"; turn["interrupted"] = True
        return "voice_barge_in_recorded"
    return _mutate_turn(turn_id, event_id, runtime_root, cb)


def finish_voice_turn(*, turn_id: str, outcome: str, event_id: str, runtime_root: str | Path | None = None) -> dict[str, Any]:
    out = str(outcome or "completed").strip().lower()
    if out not in {"completed", "cancelled", "failed"}:
        return {"ok": False, "status": "invalid_voice_terminal_outcome", **_DENIED}
    def cb(turn):
        if turn.get("state") in {"completed", "cancelled", "failed"}: return "voice_turn_terminal_immutable"
        turn["state"] = out
        return f"voice_turn_{out}"
    return _mutate_turn(turn_id, event_id, runtime_root, cb)


def silence_decision(*, silence_ms: int, speaking: bool, runtime_root: str | Path | None = None) -> dict[str, Any]:
    state = read_voice_state(runtime_root=runtime_root); timeout = int((state.get("profile") or {}).get("silence_timeout_ms") or 1800)
    try:
        silence = max(0, int(silence_ms))
    except (TypeError, ValueError, OverflowError):
        return {"ok": False, "status": "valid_silence_duration_required", **_DENIED}
    if speaking:
        action = "wait_for_speaker"
    elif silence < timeout:
        action = "continue_listening"
    elif silence < timeout * 2:
        action = "offer_turn_without_pressure"
    else:
        action = "close_or_wait_silently"
    return {"ok": True, "status": "voice_silence_judgment", "silence_ms": silence, "threshold_ms": timeout, "action": action, **_DENIED}


def reconcile_transcript(
    *, turn: Mapping[str, Any], corrected_transcript_digest: str = "", correction_authority: str = "",
) -> dict[str, Any]:
    segments = [dict(x) for x in turn.get("segments", []) if isinstance(x, Mapping) and _hex64(x.get("transcript_digest"))]
    correction = _hex64(corrected_transcript_digest)
    authorized = bool(correction and str(correction_authority or "").strip().lower() == "operator")
    if authorized:
        final = correction; source = "operator_correction"
    elif segments:
        final = _digest([x["transcript_digest"] for x in segments]); source = "stt_segments_composite"
    else:
        final = ""; source = "unavailable"
    return {
        "ok": bool(final), "status": "voice_transcript_reconciled" if final else "voice_transcript_unavailable",
        "final_transcript_digest": final, "source": source, "segment_count": len(segments),
        "operator_correction_applied": authorized, "raw_transcript_included": False,
        "stt_output_is_not_operator_fact": True, **_DENIED,
    }


def process_era7_voice_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split()).strip().lower().rstrip(".!?")
    exact = {"show voice and audio status", "inspect voice and audio status", "show era7 voice contract"}
    if raw in exact:
        return {"active": True, "ok": True, "status": "era7_voice_contract_inspected", "state": public_voice_state(read_voice_state(runtime_root=runtime_root)), "native_audio_deferred": True, **_DENIED}
    if any(raw.startswith(prefix) for prefix in exact):
        return {"active": True, "ok": False, "status": "era7_voice_read_only_scope_expansion_rejected", **_DENIED}
    return {"active": False}


__all__ = [
    "CONTRACT_VERSION", "VOICE_STATES", "read_voice_state", "public_voice_state", "configure_voice_profile",
    "begin_voice_turn", "record_transcript_segment", "prepare_speech_request", "handle_barge_in", "finish_voice_turn",
    "silence_decision", "reconcile_transcript", "process_era7_voice_control",
]
