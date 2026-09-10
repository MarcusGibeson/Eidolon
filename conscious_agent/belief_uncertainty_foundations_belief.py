from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    MAX_PROPOSITION_CHARS: Any
    UNCERTAINTY_STATES: Any
    _compact: Any
    _digest: Any
    _now: Any
    _prior_matches: Any
    _terms: Any
    classify_uncertainty: Any



def build_belief_candidate(*, reflection: dict[str, Any], operation_id: str, prior_candidates: list[dict[str, Any]] | None=None, _deps: SymbolDependencies) -> dict[str, Any]:
    """Build one provisional, evidence-linked and non-authoritative belief candidate."""
    proposition = _deps._compact(reflection.get('conclusion') or reflection.get('content'), _deps.MAX_PROPOSITION_CHARS)
    evidence_refs = [str(x)[:120] for x in reflection.get('evidence_refs') or [] if str(x)][:4]
    confidence = max(0.0, min(1.0, float(reflection.get('confidence', 0.35) or 0.35)))
    sufficient = bool(evidence_refs and reflection.get('use_in_conversation'))
    uncertainty = _deps.classify_uncertainty(confidence, len(evidence_refs), sufficient)
    semantic_key = str(reflection.get('semantic_subject_key') or _deps._digest(sorted(_deps._terms(proposition))))
    prior = [r for r in prior_candidates or [] if isinstance(r, dict) and str(r.get('type') or '') == 'belief_candidate' and (str(r.get('lifecycle_state') or 'active') in {'active', 'contested'})]
    matching = [r for r in prior if _deps._prior_matches(reflection, r)]
    supersedes = ''
    retires: list[str] = []
    lifecycle = 'active'
    revision_basis = 'new_evidence'
    if matching:
        latest = matching[-1]
        supersedes = str(latest.get('belief_candidate_id') or latest.get('memory_id') or '')
        if reflection.get('operator_correction') and supersedes:
            retires = [supersedes]
            revision_basis = 'explicit_user_correction'
        elif abs(float(latest.get('confidence', 0.5) or 0.5) - confidence) >= 0.25:
            lifecycle = 'contested'
            revision_basis = 'material_confidence_change'
    candidate_id = f'belief-candidate-{_deps._digest([operation_id, semantic_key, proposition])[:24]}'
    return {'created_at': _deps._now(), 'type': 'belief_candidate', 'belief_candidate_id': candidate_id, 'proposition': proposition, 'content': proposition, 'semantic_subject_key': semantic_key, 'subject_terms': sorted(set(reflection.get('subject_terms') or _deps._terms(proposition))), 'origin_reflection_id': str(reflection.get('reflection_id') or ''), 'evidence_refs': evidence_refs, 'evidence_count': len(evidence_refs), 'confidence': round(confidence, 3), **uncertainty, 'lifecycle_state': lifecycle, 'revisable': True, 'revision_basis': revision_basis, 'supersedes_belief_candidate_id': supersedes, 'retires_belief_candidate_ids': retires, 'use_in_conversation': sufficient and lifecycle != 'contested', 'epistemic_status': 'provisional', 'recommended_action': 'store_only', 'operator_authority_required_for_action': True, 'provider_contacted': False, 'action_executed': False, 'authority_broadened': False, 'historical_records_preserved': True, 'contract_version': _deps.CONTRACT_VERSION}


def inspect_belief_candidates(memories: list[dict[str, Any]], *, _deps: SymbolDependencies) -> dict[str, Any]:
    rows = [r for r in memories if isinstance(r, dict) and r.get('type') == 'belief_candidate']
    return {'contract_version': _deps.CONTRACT_VERSION, 'candidate_count': len(rows), 'active_count': sum((r.get('lifecycle_state') == 'active' for r in rows)), 'contested_count': sum((r.get('lifecycle_state') == 'contested' for r in rows)), 'explicit_uncertainty_count': sum((r.get('uncertainty_state') in _deps.UNCERTAINTY_STATES for r in rows)), 'all_revisable': all((r.get('revisable') is True for r in rows)), 'authority_preserved': all((not r.get('authority_broadened') and (not r.get('action_executed')) for r in rows)), 'raw_content_exposed': False}
