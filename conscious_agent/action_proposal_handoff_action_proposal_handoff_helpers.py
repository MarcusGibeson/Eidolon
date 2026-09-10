from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    MAX_HANDOFF_BYTES: Any
    Mapping: Any
    SCHEMA_VERSION: Any
    _CAPABILITIES: Any
    _EXPLICIT_APPROVAL: Any
    _EXPLICIT_EXECUTION: Any
    _bounded_id: Any
    _digest: Any
    re: Any



def build_action_proposal_handoff(action_projection: _deps.Mapping[str, Any], *, operation_id: str='', explicit_control_text: str='', persisted_proposal: _deps.Mapping[str, Any] | None=None, _deps: SymbolDependencies) -> dict[str, Any]:
    intent = dict(action_projection.get('intent') or {})
    grounding = dict(action_projection.get('grounding') or {})
    capability_id = _deps._bounded_id(grounding.get('capability_id'))
    matched = bool(grounding.get('grounding_status') == 'matched' and capability_id in _deps._CAPABILITIES)
    needs_clarification = bool(intent.get('requires_clarification'))
    capability = _deps._CAPABILITIES.get(capability_id, {})
    boundary = str(capability.get('boundary') or '')
    risk = str(grounding.get('risk_level') or 'unknown')[:20]
    proposal_ready = bool(matched and (not needs_clarification))
    proposal = {'schema_version': _deps.SCHEMA_VERSION, 'contract_version': _deps.CONTRACT_VERSION, 'proposal_state': 'ready_for_operator_review' if proposal_ready else 'not_ready', 'capability_id': capability_id if matched else '', 'capability_registered': matched, 'proposal_digest': '', 'persisted': False, 'deduplicated': True, 'content_free': True, 'authority_free': True, 'source_projection_digest': str(action_projection.get('projection_digest') or '')[:64], 'operation_digest': _deps._digest(str(operation_id or '')[:160]) if operation_id else '', 'risk_level': risk, 'reversible': bool(grounding.get('reversible')), 'required_authority': str(grounding.get('required_authority') or 'none')[:120], 'approval_required': bool(grounding.get('authority_required')), 'execution_requested': bool(intent.get('action_intent_present')), 'execution_admission_state': 'not_admitted', 'approval_state': 'not_created', 'authorization_state': 'not_granted', 'execution_state': 'not_executed', 'missing_information': list(grounding.get('missing_information') or [])[:4], 'suggested_clarification': str(grounding.get('suggested_clarification') or '')[:240]}
    proposal['proposal_digest'] = _deps._digest({k: v for k, v in proposal.items() if k != 'proposal_digest'})
    persisted = dict(persisted_proposal or {})
    persisted_capability = _deps._bounded_id(persisted.get('capability_id'))
    persisted_digest = str(persisted.get('proposal_digest') or '')
    persisted_valid = bool(persisted.get('persisted') is True and persisted_capability == capability_id and _deps.re.fullmatch('[0-9a-f]{64}', persisted_digest) and (persisted.get('proposal_state') in {'proposed', 'awaiting_approval'}))
    approval_match = _deps._EXPLICIT_APPROVAL.fullmatch(str(explicit_control_text or '').strip())
    execute_match = _deps._EXPLICIT_EXECUTION.fullmatch(str(explicit_control_text or '').strip())
    requested_control_capability = _deps._bounded_id((approval_match or execute_match).group(1)) if approval_match or execute_match else ''
    exact_reference = bool(requested_control_capability and requested_control_capability == capability_id)
    handoff = {'proposal': proposal, 'approval_handoff': {'state': 'eligible_for_separate_governed_handoff' if proposal_ready else 'not_eligible', 'explicit_control_phrase_present': bool(approval_match or execute_match), 'exact_capability_reference': exact_reference, 'persisted_proposal_verified': persisted_valid, 'approval_created': False, 'approval_granted': False, 'automatic_approval_allowed': False, 'go_ahead_is_approval': False}, 'execution_admission': {'state': 'preview_only', 'registered_capability': matched, 'proposal_ready': proposal_ready, 'persisted_proposal_verified': persisted_valid, 'explicit_execution_phrase_present': bool(execute_match), 'exact_capability_reference': exact_reference, 'risk_level': risk, 'registry_boundary': boundary, 'admitted': False, 'executed': False, 'authoritative_receipt_created': False, 'reason': 'Execution remains outside this foundation bundle. A separate governed executor must verify the persisted proposal, exact capability, authority, risk, and current state.' if proposal_ready else 'No execution admission is possible until one registered capability is unambiguously grounded.'}, 'diagnostics': {'existing_registry_reused': True, 'new_tool_registry_created': False, 'proposal_persisted': False, 'approval_created': False, 'execution_performed': False, 'source_modified': False, 'raw_user_text_included': False, 'raw_arguments_included': False, 'raw_command_included': False, 'content_free': True}}
    handoff['handoff_digest'] = _deps._digest(handoff)
    encoded = json.dumps(handoff, sort_keys=True, separators=(',', ':')).encode('utf-8')
    if len(encoded) > _deps.MAX_HANDOFF_BYTES:
        raise ValueError('Action proposal handoff exceeded bounded size contract')
    handoff['diagnostics']['handoff_bytes'] = len(encoded)
    handoff['diagnostics']['handoff_bounded'] = True
    return handoff


def action_proposal_handoff_prompt(handoff: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> str:
    proposal = dict(handoff.get('proposal') or {})
    approval = dict(handoff.get('approval_handoff') or {})
    execution = dict(handoff.get('execution_admission') or {})
    capability = str(proposal.get('capability_id') or 'none')
    return '\n'.join(['Action proposal and approval boundary (bounded, non-authoritative):', f"- Proposal state: {proposal.get('proposal_state', 'not_ready')}; capability: {capability}.", f"- Separate governed approval handoff: {approval.get('state', 'not_eligible')}.", f"- Execution admission: {execution.get('state', 'preview_only')}; admitted: false; executed: false.", '- Do not claim that a proposal was persisted, an approval was created or granted, or an action ran.', "- 'Go ahead' is never approval. Exact persisted proposal evidence and a separate governed control are required."])


def action_proposal_handoff_public(handoff: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    return {'proposal': dict(handoff.get('proposal') or {}), 'approval_handoff': dict(handoff.get('approval_handoff') or {}), 'execution_admission': dict(handoff.get('execution_admission') or {}), 'diagnostics': dict(handoff.get('diagnostics') or {}), 'handoff_digest': str(handoff.get('handoff_digest') or '')[:64]}
