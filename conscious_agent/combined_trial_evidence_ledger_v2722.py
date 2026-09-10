from __future__ import annotations
"""v2722 content-minimized combined-trial evidence ledger contract."""
from typing import Any, Mapping
import hashlib, json, re
from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog, validate_combined_trial_catalog

CONTRACT_VERSION = 'v2722.2'
STATUSES = {'not_started','running','passed','failed','blocked','stopped','needs_review'}
TERMINAL_STATUSES = {'passed','failed','stopped'}
HIGH_RISK_CLASSES = {'operator_reviewed_policy_change','user_visible_response_repair','supervised_source_test_change','self_architecture_project_design','supervised_project_start'}
_RECORD_FIELDS = {
    'ok','contract_version','catalog_digest','trial_id','trial_digest','status','evidence_codes','checkpoint_digest',
    'rollback_available','raw_trial_content_stored','raw_prompt_stored','raw_response_stored','provider_output_stored',
    'automatic_transition_permitted','authority_granted','evidence_digest'
}
_HEX64 = re.compile(r'^[0-9a-fA-F]{64}$')

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def _trial(catalog: Mapping[str, Any], trial_id: str) -> dict[str, Any]:
    canonical = validate_combined_trial_catalog(catalog)
    for row in canonical['trials']:
        if str(row['trial_id']) == trial_id:
            return dict(row)
    raise ValueError('unknown_trial_id')

def build_trial_evidence_record(
    *, trial_id: str, status: str, evidence_codes: list[str] | tuple[str, ...] = (), checkpoint_digest: str = '',
    rollback_available: bool = True, catalog: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    canonical_catalog = validate_combined_trial_catalog(catalog or build_combined_trial_catalog())
    tid = str(trial_id).strip()
    st = str(status)
    row = _trial(canonical_catalog, tid)
    if st not in STATUSES:
        raise ValueError('unsupported_trial_status')
    checkpoint = str(checkpoint_digest).strip()
    if checkpoint and not _HEX64.fullmatch(checkpoint):
        raise ValueError('invalid_checkpoint_digest')
    if st in TERMINAL_STATUSES and str(row['risk_class']) in HIGH_RISK_CLASSES and not checkpoint:
        raise ValueError('high_risk_terminal_evidence_requires_checkpoint_digest')
    codes = [str(x)[:80] for x in list(evidence_codes)[:16]]
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'catalog_digest': canonical_catalog['catalog_digest'],
        'trial_id': tid,
        'trial_digest': row['trial_digest'],
        'status': st,
        'evidence_codes': codes,
        'checkpoint_digest': checkpoint,
        'rollback_available': bool(rollback_available),
        'raw_trial_content_stored': False,
        'raw_prompt_stored': False,
        'raw_response_stored': False,
        'provider_output_stored': False,
        'automatic_transition_permitted': False,
        'authority_granted': False,
    }
    out['evidence_digest'] = _digest(out)
    return out

def _validate_record(record: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    canonical_catalog = validate_combined_trial_catalog(catalog)
    r = dict(record)
    if set(r) != _RECORD_FIELDS:
        raise ValueError('noncanonical_trial_evidence_record')
    if r.get('contract_version') != CONTRACT_VERSION or r.get('ok') is not True:
        raise ValueError('invalid_trial_evidence_contract')
    supplied = str(r.get('evidence_digest') or '')
    body = dict(r)
    body.pop('evidence_digest', None)
    if not supplied or supplied != _digest(body):
        raise ValueError('trial_evidence_digest_mismatch')
    canonical = build_trial_evidence_record(
        trial_id=str(r.get('trial_id') or ''),
        status=str(r.get('status') or ''),
        evidence_codes=list(r.get('evidence_codes') or []),
        checkpoint_digest=str(r.get('checkpoint_digest') or ''),
        rollback_available=bool(r.get('rollback_available')),
        catalog=canonical_catalog,
    )
    if canonical != r:
        raise ValueError('noncanonical_trial_evidence_record')
    return canonical

def build_campaign_evidence_ledger(
    catalog: Mapping[str, Any], records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = ()
) -> dict[str, Any]:
    canonical_catalog = validate_combined_trial_catalog(catalog)
    known = {str(r['trial_id']) for r in canonical_catalog['trials']}
    rows = [_validate_record(r, canonical_catalog) for r in records]
    status = {tid: 'not_started' for tid in known}
    for r in rows:
        status[str(r['trial_id'])] = str(r['status'])
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'catalog_digest': canonical_catalog['catalog_digest'],
        'records': rows,
        'status_by_trial': dict(sorted(status.items())),
        'completed_count': sum(v == 'passed' for v in status.values()),
        'failed_count': sum(v == 'failed' for v in status.values()),
        'campaign_complete': bool(status) and all(v == 'passed' for v in status.values()),
        'automatic_transition_permitted': False,
        'raw_trial_content_stored': False,
        'authority_granted': False,
    }
    out['ledger_digest'] = _digest(out)
    return out

__all__ = ['CONTRACT_VERSION','STATUSES','build_trial_evidence_record','build_campaign_evidence_ledger']
