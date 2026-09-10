from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    Iterable: Any
    Mapping: Any
    default: Any
    digest: Any
    valid_digest: Any



def seal_candidate_identity(*, campaign_id: str, baseline_digest: str, approach_digest: str, workspace_digest: str, changed_path_digests: _deps.Iterable[str], _deps: SymbolDependencies) -> dict[str, Any]:
    cid = str(campaign_id or '').strip()
    base = str(baseline_digest or '').lower().strip()
    approach = str(approach_digest or '').lower().strip()
    workspace = str(workspace_digest or '').lower().strip()
    changed = tuple(sorted({str(x).lower().strip() for x in changed_path_digests if str(x).strip()}))
    if not cid or not all((_deps.valid_digest(x) for x in (base, approach, workspace))) or (not changed) or (not all((_deps.valid_digest(x) for x in changed))):
        raise ValueError('sealed_candidate_identity_required')
    row = {'campaign_id': cid, 'baseline_digest': base, 'approach_digest': approach, 'workspace_digest': workspace, 'changed_path_digests': changed, 'changed_path_count': len(changed), 'content_free': True}
    row['candidate_id'] = f'candidate-{_deps.digest(row)[:24]}'
    row['candidate_identity_digest'] = _deps.digest(row)
    return row


def normalize_candidate_evidence(raw: _deps.Mapping[str, Any], *, _deps: SymbolDependencies) -> dict[str, Any]:
    required = ('candidate_id', 'candidate_identity_digest', 'campaign_id', 'baseline_digest', 'approach_digest', 'workspace_digest', 'verification_run_digest')
    if any((not str(raw.get(k) or '') for k in required)):
        raise ValueError('candidate_evidence_identity_required')
    for key in ('candidate_identity_digest', 'baseline_digest', 'approach_digest', 'workspace_digest', 'verification_run_digest'):
        if not _deps.valid_digest(raw.get(key)):
            raise ValueError(f'valid_{key}_required')

    def n(k: str, default: int=0) -> int:
        return max(0, min(100, int(raw.get(k, _deps.default))))
    return {'candidate_id': str(raw['candidate_id']), 'candidate_identity_digest': str(raw['candidate_identity_digest']), 'campaign_id': str(raw['campaign_id']), 'baseline_digest': str(raw['baseline_digest']), 'approach_digest': str(raw['approach_digest']), 'workspace_digest': str(raw['workspace_digest']), 'verification_run_digest': str(raw['verification_run_digest']), 'focused_verification_passed': bool(raw.get('focused_verification_passed', False)), 'regression_verification_passed': bool(raw.get('regression_verification_passed', False)), 'scope_conforming': bool(raw.get('scope_conforming', False)), 'evidence_fresh': bool(raw.get('evidence_fresh', True)), 'private_evidence': bool(raw.get('private_evidence', False)), 'quality_disposition': str(raw.get('quality_disposition') or 'insufficient_evidence'), 'quality_score': n('quality_score'), 'risk': n('risk'), 'cost': n('cost'), 'reversibility': n('reversibility'), 'residual_uncertainty': n('residual_uncertainty'), 'content_free': True}
