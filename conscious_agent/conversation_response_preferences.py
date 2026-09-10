from __future__ import annotations

"""Deterministic v1086.1 per-conversation response preferences."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from conversation_control_foundation import RESPONSE_FORMATS, RESPONSE_MODES

RESPONSE_PREFERENCE_SCHEMA_VERSION = "1"

_MODE_INSTRUCTIONS = {
    "default": "",
    "concise": "Prefer concise replies for this conversation unless the latest message explicitly asks for more detail.",
    "detailed": "Prefer detailed, well-explained replies for this conversation unless the latest message explicitly asks for brevity.",
    "technical": "Prefer technically precise wording and concrete implementation detail while still explaining uncommon terms plainly.",
    "casual": "Prefer a relaxed, natural conversational style without changing identity, safety boundaries, or factual standards.",
    "brainstorming": "Prefer several clearly differentiated ideas and tradeoffs rather than prematurely collapsing to one answer.",
}
_FORMAT_INSTRUCTIONS = {
    "default": "",
    "prose": "Prefer natural prose unless structure is needed for clarity.",
    "bullets": "Prefer a compact bulleted structure when it improves scanning.",
    "steps": "Prefer ordered steps when the request involves a process or sequence.",
}


@dataclass(frozen=True)
class ResponsePreferenceProfile:
    mode: str = "default"
    format: str = "default"
    revision: int = 0
    updated_at: str = ""
    source: str = "default"
    session_local: bool = True
    current_turn_override_allowed: bool = True
    mutates_global_personality: bool = False
    provider_invoked: bool = False
    schema_version: str = RESPONSE_PREFERENCE_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_block(self, *, explicit_length_cue: bool = False) -> str:
        lines = ["PER-CONVERSATION RESPONSE PREFERENCE"]
        mode_instruction = _MODE_INSTRUCTIONS.get(self.mode, "")
        format_instruction = _FORMAT_INSTRUCTIONS.get(self.format, "")
        if explicit_length_cue and self.mode in {"concise", "detailed"}:
            lines.append("The latest user's explicit length request overrides the stored session length preference for this turn.")
        elif mode_instruction:
            lines.append(mode_instruction)
        if format_instruction:
            lines.append(format_instruction)
        lines.append("This preference is local to this conversation and does not modify the configured personality or future conversations.")
        return "\n".join(lines)


def normalize_response_preferences(value: Mapping[str, Any] | None) -> ResponsePreferenceProfile:
    raw = value if isinstance(value, Mapping) else {}
    mode = str(raw.get("mode") or "default").strip().lower()
    fmt = str(raw.get("format") or "default").strip().lower()
    if mode not in RESPONSE_MODES:
        mode = "default"
    if fmt not in RESPONSE_FORMATS:
        fmt = "default"
    return ResponsePreferenceProfile(
        mode=mode,
        format=fmt,
        revision=max(0, int(raw.get("revision") or 0)),
        updated_at=str(raw.get("updated_at") or "")[:40],
        source=str(raw.get("source") or "default")[:80],
    )


def response_preference_payload(
    *, mode: str = "default", format: str = "default", revision: int = 0,
    updated_at: str = "", source: str = "operator",
) -> dict[str, Any]:
    return normalize_response_preferences({
        "mode": mode,
        "format": format,
        "revision": revision,
        "updated_at": updated_at,
        "source": source,
    }).public_summary()
