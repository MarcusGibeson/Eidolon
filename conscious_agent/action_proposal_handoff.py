from __future__ import annotations

"""Bounded proposal, approval-handoff, and execution-admission foundations.

This layer consumes the canonical v1175 natural-language action projection and
produces a content-free proposal candidate.  It does not persist proposals,
create approvals, execute tools, or treat conversational language as consent.
"""

import hashlib
import json
import re
from typing import Any, Mapping

from chat_action_router import SUPERVISED_CAPABILITY_REGISTRY
from action_proposal_handoff_action_proposal_handoff_helpers import (
    SymbolDependencies as _ActionProposalHandoffActionProposalHandoffHelpersSymbolDependencies,
    action_proposal_handoff_prompt as _action_proposal_handoff_prompt_implementation,
    action_proposal_handoff_public as _action_proposal_handoff_public_implementation,
    build_action_proposal_handoff as _build_action_proposal_handoff_implementation,
)


SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1175.5"
MAX_HANDOFF_BYTES = 3072
_CAPABILITIES = {str(row["id"]): dict(row) for row in SUPERVISED_CAPABILITY_REGISTRY}
_EXPLICIT_APPROVAL = re.compile(r"^(?:i\s+)?(?:explicitly\s+)?approve\s+(?:the\s+)?(?:proposed\s+)?([a-z0-9_-]+)(?:\s+action)?[.!?]*$", re.I)
_EXPLICIT_EXECUTION = re.compile(r"^(?:please\s+)?execute\s+(?:the\s+)?(?:proposed\s+)?([a-z0-9_-]+)(?:\s+action)?[.!?]*$", re.I)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _bounded_id(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text[:80] if re.fullmatch(r"[a-z0-9_-]{1,80}", text) else ""


def _build_action_proposal_handoff_action_proposal_handoff_helpers_dependencies() -> _ActionProposalHandoffActionProposalHandoffHelpersSymbolDependencies:
    return _ActionProposalHandoffActionProposalHandoffHelpersSymbolDependencies(
        CONTRACT_VERSION=CONTRACT_VERSION,
        MAX_HANDOFF_BYTES=MAX_HANDOFF_BYTES,
        Mapping=Mapping,
        SCHEMA_VERSION=SCHEMA_VERSION,
        _CAPABILITIES=_CAPABILITIES,
        _EXPLICIT_APPROVAL=_EXPLICIT_APPROVAL,
        _EXPLICIT_EXECUTION=_EXPLICIT_EXECUTION,
        _bounded_id=_bounded_id,
        _digest=_digest,
        re=re,
    )

def build_action_proposal_handoff(action_projection: Mapping[str, Any], *, operation_id: str='', explicit_control_text: str='', persisted_proposal: Mapping[str, Any] | None=None) -> dict[str, Any]:
    return _build_action_proposal_handoff_implementation(action_projection, operation_id=operation_id, explicit_control_text=explicit_control_text, persisted_proposal=persisted_proposal, _deps=_build_action_proposal_handoff_action_proposal_handoff_helpers_dependencies())



def action_proposal_handoff_prompt(handoff: Mapping[str, Any]) -> str:
    return _action_proposal_handoff_prompt_implementation(handoff, _deps=_build_action_proposal_handoff_action_proposal_handoff_helpers_dependencies())



def action_proposal_handoff_public(handoff: Mapping[str, Any]) -> dict[str, Any]:
    return _action_proposal_handoff_public_implementation(handoff, _deps=_build_action_proposal_handoff_action_proposal_handoff_helpers_dependencies())

