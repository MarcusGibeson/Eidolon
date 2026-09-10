from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    DENIED_AUTHORITY: Any
    Mapping: Any
    _event_fingerprint: Any
    _response: Any
    _state_digest: Any
    deepcopy: Any
    valid_digest: Any
    validate_state_identity: Any



def apply_campaign_event(state: _deps.Mapping[str, Any], event: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    """Apply one evidence transition to a campaign record, never the project itself."""
    current = _deps.deepcopy(dict(state))
    if not _deps.validate_state_identity(current) or current.get('state_digest') != _deps._state_digest(current):
        return _deps._response(current, 'blocked_invalid_or_tampered_state', reason='state_integrity_failed')
    if str(event.get('campaign_id') or '') != current['campaign_id'] or str(event.get('identity_digest') or '') != current['identity_digest']:
        return _deps._response(current, 'blocked_campaign_identity_mismatch', reason='campaign_identity_mismatch')
    try:
        event_digest, body = _deps._event_fingerprint(current, event)
    except ValueError:
        return _deps._response(current, 'blocked_unsafe_scope_path', reason='safe_relative_scope_path_required')
    if event_digest in tuple(current.get('event_digests') or ()):
        return _deps._response(current, 'duplicate_event_noop', duplicate=True, reason='idempotent_replay')
    expected = body['expected_last_event_digest']
    if expected != str(current.get('last_event_digest') or ''):
        return _deps._response(current, 'blocked_stale_event', reason='last_event_digest_mismatch')
    if current.get('terminal'):
        return _deps._response(current, 'blocked_terminal_campaign', reason='terminal_campaign_is_immutable')
    if int(current.get('event_sequence', 0)) >= int(current.get('max_events', 0)):
        return _deps._response(current, 'blocked_event_budget_exhausted', reason='bounded_event_budget_exhausted')
    touched = set(body['touched_path_digests'])
    allowed = set(current.get('scope_path_digests') or ())
    if not touched.issubset(allowed):
        return _deps._response(current, 'blocked_scope_expansion', reason='out_of_scope_paths_require_separate_confirmation', extra={'new_requirement_confirmation_required': True, 'scope_expansion_authorized': False})
    kind = body['kind']
    evidence = body['evidence_digest']
    strategy = body['strategy_digest']
    evidence_required = kind in {'implementation_ready', 'verification_pass', 'verification_fail', 'recovery_ready', 'quality_review_pass', 'quality_review_fail', 'operator_review_complete'}
    if evidence_required and (not _deps.valid_digest(evidence)):
        return _deps._response(current, 'blocked_missing_evidence', reason='stage_evidence_digest_required')
    if strategy and (not _deps.valid_digest(strategy)):
        return _deps._response(current, 'blocked_invalid_strategy_digest', reason='strategy_digest_invalid')
    if strategy and strategy in tuple(current.get('failed_strategy_digests') or ()) and (kind in {'implementation_ready', 'recovery_ready'}):
        return _deps._response(current, 'blocked_repeated_failed_strategy', reason='recorded_failed_strategy_must_not_repeat')
    stage = str(current.get('current_stage') or '')
    if kind == 'pause':
        if current.get('paused'):
            return _deps._response(current, 'already_paused', duplicate=True, reason='pause_is_idempotent')
        current['paused'] = True
    elif kind == 'resume':
        if not current.get('paused'):
            return _deps._response(current, 'blocked_not_paused', reason='resume_requires_paused_campaign')
        current['paused'] = False
    elif kind == 'cancel':
        current['current_stage'] = 'cancelled'
        current['terminal'] = True
        current['paused'] = False
    elif kind == 'block':
        current['current_stage'] = 'blocked'
        current['terminal'] = True
        current['paused'] = False
    else:
        if current.get('paused'):
            return _deps._response(current, 'blocked_paused_campaign', reason='resume_required_before_stage_transition')
        transition = None
        if stage == 'prepared' and kind == 'start_implementation':
            transition = 'implementation'
        elif stage == 'implementation' and kind == 'implementation_ready':
            transition = 'verification'
        elif stage == 'verification' and kind == 'verification_pass':
            transition = 'quality_review'
        elif stage == 'verification' and kind == 'verification_fail':
            transition = 'recovery'
        elif stage == 'recovery' and kind == 'recovery_ready':
            transition = 'verification'
        elif stage == 'quality_review' and kind == 'quality_review_pass':
            transition = 'operator_review'
        elif stage == 'quality_review' and kind == 'quality_review_fail':
            transition = 'recovery'
        elif stage == 'operator_review' and kind == 'operator_review_complete' and (str(body.get('operator_review_outcome') or '') in {'accepted_for_campaign_completion', 'reviewed_no_apply'}):
            transition = 'complete'
        if transition is None:
            return _deps._response(current, 'blocked_invalid_stage_transition', reason=f'{stage}:{kind}')
        if transition == 'recovery':
            if int(current.get('recovery_attempts', 0)) >= int(current.get('max_recovery_attempts', 0)):
                return _deps._response(current, 'blocked_recovery_budget_exhausted', reason='bounded_recovery_budget_exhausted')
            current['recovery_attempts'] = int(current.get('recovery_attempts', 0)) + 1
            if strategy:
                failed = list(current.get('failed_strategy_digests') or ())
                if strategy not in failed:
                    failed.append(strategy)
                current['failed_strategy_digests'] = tuple(failed)
        if evidence_required:
            completed = dict(current.get('completed_stage_evidence') or {})
            completed[f"{stage}:{kind}:{int(current.get('event_sequence', 0)) + 1}"] = evidence
            current['completed_stage_evidence'] = completed
        current['current_stage'] = transition
        if transition == 'complete':
            current['terminal'] = True
            current['completion_conditions_met'] = all((any((key.startswith(prefix) for key in current['completed_stage_evidence'])) for prefix in ('implementation:implementation_ready', 'verification:verification_pass', 'quality_review:quality_review_pass', 'operator_review:operator_review_complete')))
            if not current['completion_conditions_met']:
                return _deps._response(state, 'blocked_incomplete_completion_chain', reason='required_stage_evidence_missing')
    current['event_sequence'] = int(current.get('event_sequence', 0)) + 1
    current['last_event_digest'] = event_digest
    current['event_digests'] = tuple(list(current.get('event_digests') or ()) + [event_digest])
    current['state_digest'] = _deps._state_digest(current)
    return _deps._response(current, 'campaign_event_recorded', accepted=True, reason='evidence_transition_recorded', extra={'event_digest': event_digest})


def campaign_public_projection(state: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    """Content-free operator projection; it deliberately omits raw paths/content."""
    return {'campaign_id': state.get('campaign_id', ''), 'proposal_id': state.get('proposal_id', ''), 'objective_digest': state.get('objective_digest', ''), 'scope_digest': state.get('scope_digest', ''), 'scope_path_count': len(tuple(state.get('scope_path_digests') or ())), 'current_stage': state.get('current_stage', ''), 'paused': bool(state.get('paused')), 'terminal': bool(state.get('terminal')), 'event_sequence': int(state.get('event_sequence', 0)), 'recovery_attempts': int(state.get('recovery_attempts', 0)), 'max_recovery_attempts': int(state.get('max_recovery_attempts', 0)), 'completion_conditions_met': bool(state.get('completion_conditions_met')), 'next_required_authority': 'existing_stage_specific_governance_only', 'campaign_grants_authority': False, 'content_free': True, 'read_only': True, **_deps.DENIED_AUTHORITY}
