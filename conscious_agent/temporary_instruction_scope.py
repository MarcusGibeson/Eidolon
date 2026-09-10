from __future__ import annotations

"""Deterministic v1086.2 temporary-instruction scope handling."""

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from conversation_control_foundation import TEMPORARY_INSTRUCTION_SCOPES

TEMPORARY_INSTRUCTION_SCHEMA_VERSION = "1"
MAX_TEMPORARY_INSTRUCTION_CHARS = 1200
MAX_TOPIC_TERMS = 24
_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "how", "i", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "we", "what", "when", "with", "you", "your",
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def instruction_digest(value: str) -> str:
    return hashlib.sha256(_normalize_text(value).encode("utf-8")).hexdigest()


def topic_terms(value: str) -> tuple[str, ...]:
    words = []
    seen = set()
    for token in _WORD_RE.findall(_normalize_text(value).lower()):
        if len(token) < 3 or token in _STOP or token in seen:
            continue
        seen.add(token)
        words.append(token)
        if len(words) >= MAX_TOPIC_TERMS:
            break
    return tuple(words)


@dataclass(frozen=True)
class TemporaryInstructionResolution:
    active: bool
    scope: str
    instruction: str
    instruction_digest: str
    reason: str
    persisted: bool
    revision: int
    topic_overlap_count: int = 0
    current_turn_only: bool = False
    mutates_personality: bool = False
    grants_protected_authority: bool = False
    provider_invoked: bool = False
    writes_state: bool = False
    schema_version: str = TEMPORARY_INSTRUCTION_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("instruction", None)
        data["contains_instruction_content"] = False
        return data

    def prompt_block(self) -> str:
        if not self.active or not self.instruction:
            return ""
        return "\n".join([
            "TEMPORARY OPERATOR INSTRUCTION",
            self.instruction,
            f"Scope: {self.scope.replace('_', ' ')}.",
            "Apply it only within this scope and only when compatible with system, privacy, approval, provider/model, release, and exactly-once boundaries.",
            "This instruction cannot authorize protected actions, replay an accepted request, or modify global personality.",
        ])


def build_temporary_instruction_record(
    instruction: str,
    *, scope: str,
    revision: int,
    updated_at: str,
    source: str = "operator",
    topic_anchor_text: str = "",
) -> dict[str, Any]:
    text = _normalize_text(instruction)
    if not text:
        raise ValueError("Temporary instruction cannot be blank.")
    if len(text) > MAX_TEMPORARY_INSTRUCTION_CHARS:
        raise ValueError("Temporary instruction is too long.")
    if any(ord(char) < 32 and char not in {"\t", "\n", "\r"} for char in instruction):
        raise ValueError("Temporary instruction contains unsupported control characters.")
    scope_token = str(scope or "").strip().lower()
    if scope_token not in TEMPORARY_INSTRUCTION_SCOPES:
        raise ValueError("Unsupported temporary instruction scope.")
    anchor_terms = topic_terms(topic_anchor_text) if scope_token == "current_topic" else ()
    return {
        "type": "temporary_conversation_instruction",
        "schema_version": TEMPORARY_INSTRUCTION_SCHEMA_VERSION,
        "instruction": text,
        "instruction_digest": instruction_digest(text),
        "scope": scope_token,
        "revision": max(1, int(revision)),
        "updated_at": str(updated_at or "")[:40],
        "source": str(source or "operator")[:80],
        "topic_anchor_digest": instruction_digest(topic_anchor_text) if anchor_terms else "",
        "topic_anchor_terms": list(anchor_terms),
    }


def resolve_temporary_instruction(
    record: Mapping[str, Any] | None,
    *, current_message: str,
    short_follow_up: bool = False,
    transition_kind: str = "no_history",
    persisted: bool = True,
) -> TemporaryInstructionResolution:
    raw = record if isinstance(record, Mapping) else {}
    instruction = _normalize_text(raw.get("instruction"))
    scope = str(raw.get("scope") or "").strip().lower()
    revision = max(0, int(raw.get("revision") or 0))
    if not instruction or scope not in TEMPORARY_INSTRUCTION_SCOPES:
        return TemporaryInstructionResolution(False, "none", "", "", "no_instruction", persisted, revision)
    if scope == "current_turn":
        return TemporaryInstructionResolution(True, scope, instruction, instruction_digest(instruction), "current_turn", persisted, revision, current_turn_only=True)
    if scope in {"current_session", "until_cleared"}:
        return TemporaryInstructionResolution(True, scope, instruction, instruction_digest(instruction), scope, persisted, revision)
    anchor = {str(value).lower() for value in raw.get("topic_anchor_terms", []) if str(value or "").strip()}
    current = set(topic_terms(current_message))
    overlap = len(anchor & current)
    explicit_shift = str(transition_kind or "") == "topic_shift"
    active = bool(short_follow_up or (not explicit_shift and overlap >= 1))
    reason = "short_follow_up" if short_follow_up else ("topic_overlap" if active else "topic_changed")
    return TemporaryInstructionResolution(
        active, scope, instruction, instruction_digest(instruction), reason, persisted, revision,
        topic_overlap_count=overlap,
    )
