from __future__ import annotations

"""Deterministically extracted symbol family; active wrappers retain public behavior."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class SymbolDependencies:
    CONTRACT_VERSION: Any
    DENIED_AUTHORITY: Any
    MAX_OBSERVATION_WINDOW_SECONDS: Any
    Mapping: Any
    TRIGGER_CODES: Any
    _backup_path: Any
    _current_state: Any
    _read_json: Any
    digest: Any
    load_governed_self_update: Any
    time: Any
    valid_digest: Any
    validate_governed_self_update_packet: Any



def prepare_recovery_contract(update_id: str, source_root: str | Path, *, runtime_root: str | Path, health_policy_digest: str, observation_window_seconds: int=900, prepared_unix: float | None=None, _deps: SymbolDependencies) -> dict[str, Any]:
    source = Path(source_root).resolve(strict=True)
    rec = _deps.load_governed_self_update(update_id, runtime_root=runtime_root)
    if not rec or not _deps.validate_governed_self_update_packet(rec).get('ok'):
        raise ValueError('valid_v1269_update_required')
    if rec.get('phase') != 'applied_verified' or rec.get('authorization_consumed') is not True:
        raise ValueError('consumed_successful_v1269_update_required')
    if not _deps.valid_digest(health_policy_digest):
        raise ValueError('health_policy_digest_required')
    if _deps._current_state(source, rec) != 'candidate':
        raise ValueError('candidate_state_required')
    backup = _deps._read_json(_deps._backup_path(update_id, runtime_root))
    if not backup or backup.get('update_id') != update_id or backup.get('source_manifest_digest') != rec.get('source_manifest_digest') or (not _deps.valid_digest(backup.get('backup_digest'))):
        raise ValueError('bound_baseline_backup_required')
    window = int(observation_window_seconds)
    if window < 30 or window > _deps.MAX_OBSERVATION_WINDOW_SECONDS:
        raise ValueError('bounded_observation_window_required')
    now = float(_deps.time.time() if prepared_unix is None else prepared_unix)
    body = {'contract_version': _deps.CONTRACT_VERSION, 'update_id': update_id, 'update_result_digest': str(rec.get('result_digest') or ''), 'baseline_source_digest': str(rec.get('source_manifest_digest') or ''), 'candidate_source_digest': str(rec.get('candidate_manifest_digest') or ''), 'changed_files_digest': str(rec.get('changed_files_digest') or ''), 'backup_digest': str(backup.get('backup_digest') or ''), 'health_policy_digest': health_policy_digest, 'prepared_unix': now, 'expires_unix': now + window, 'observation_window_seconds': window, 'allowed_trigger_codes': sorted(_deps.TRIGGER_CODES), 'restore_target': 'exact_pre_update_backup_only', 'post_update_health_failure_recovery_is_part_of_consumed_update': True, 'successful_operator_initiated_rollback_still_separately_governed': True, 'content_free': True}
    body['recovery_contract_id'] = 'recovery_' + _deps.digest(body)[:24]
    body['recovery_contract_digest'] = _deps.digest(body)
    return body | _deps.DENIED_AUTHORITY


def recovery_trigger(contract: _deps.Mapping[str, Any], *, trigger_code: str, evidence_digest: str, observed_unix: float, source_state: str='candidate', fresh: bool=True, private_finding_count: int=0, _deps: SymbolDependencies) -> dict[str, Any]:
    code = str(trigger_code)
    if code not in _deps.TRIGGER_CODES:
        raise ValueError('defined_recovery_trigger_required')
    if not _deps.valid_digest(contract.get('recovery_contract_digest')) or not _deps.valid_digest(evidence_digest):
        raise ValueError('sealed_recovery_evidence_required')
    when = float(observed_unix)
    if when < float(contract.get('prepared_unix') or 0) or when > float(contract.get('expires_unix') or 0):
        raise ValueError('trigger_outside_observation_window')
    if source_state != 'candidate':
        raise ValueError('automatic_recovery_only_from_candidate_state')
    if not fresh:
        raise ValueError('stale_recovery_trigger_rejected')
    row = {'contract_version': _deps.CONTRACT_VERSION, 'recovery_contract_id': contract.get('recovery_contract_id'), 'recovery_contract_digest': contract.get('recovery_contract_digest'), 'trigger_code': code, 'evidence_digest': evidence_digest, 'observed_unix': when, 'source_state': source_state, 'fresh': True, 'private_finding_count': max(0, int(private_finding_count)), 'content_free': True}
    row['trigger_digest'] = _deps.digest(row)
    return row | _deps.DENIED_AUTHORITY
