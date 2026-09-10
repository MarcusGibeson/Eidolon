from __future__ import annotations
"""v2725 restart-safe prepared campaign state; preparation is not start authorization."""
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os
from json_storage import load_json_file, write_json_atomic
from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog, validate_combined_trial_catalog
from combined_trial_campaign_plan_v2721 import build_combined_trial_plan, validate_combined_trial_plan
from combined_trial_campaign_readiness_v2724 import (
    build_combined_trial_campaign_readiness,
    validate_combined_trial_campaign_readiness,
)

CONTRACT_VERSION = 'v2725.2'

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def _path(root=None) -> Path:
    if root is not None:
        r = Path(root).expanduser().resolve()
    else:
        r = Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1] / 'data').expanduser().resolve() / 'cognition'
    return r / 'combined_trial_campaign_state_v2725.json'

def _prepared_state(catalog: Mapping[str, Any], plan: Mapping[str, Any], readiness: Mapping[str, Any]) -> dict[str, Any]:
    canonical_catalog = validate_combined_trial_catalog(catalog)
    canonical_plan = validate_combined_trial_plan(canonical_catalog, plan)
    canonical_readiness = validate_combined_trial_campaign_readiness(canonical_catalog, canonical_plan, readiness)
    if canonical_readiness['ready_for_operator_campaign_review'] is not True or canonical_readiness['state'] != 'ready_for_operator_campaign_review':
        raise ValueError('campaign_not_ready_for_preparation')
    trial_rows = list(canonical_catalog['trials'])
    state = {
        'contract_version': CONTRACT_VERSION,
        'catalog_digest': canonical_catalog['catalog_digest'],
        'plan_digest': canonical_plan['plan_digest'],
        'readiness_digest': canonical_readiness['readiness_digest'],
        'current_checkpoint': canonical_readiness['current_checkpoint'],
        'release_certified': canonical_readiness['release_certified'],
        'daily_use_engineering_ready': canonical_readiness['daily_use_engineering_ready'],
        'trial_count': len(trial_rows),
        'trial_digest_by_id': {str(r['trial_id']): str(r['trial_digest']) for r in trial_rows},
        'status_by_trial': {str(r['trial_id']): 'not_started' for r in trial_rows},
        'campaign_state': 'prepared_not_started',
        'operator_campaign_start_required': True,
        'automatic_transition_permitted': False,
        'raw_trial_content_stored': False,
        'authority_granted': False,
    }
    state['state_digest'] = _digest(state)
    return state

def prepare_combined_trial_campaign_state(
    catalog: Mapping[str, Any], plan: Mapping[str, Any], readiness: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    state = _prepared_state(catalog, plan, readiness)
    p = _path(runtime_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(p, state, expected_type=dict, sort_keys=True)
    return {'ok': True, **state}

def _rejected(reason: str) -> dict[str, Any]:
    return {
        'ok': False,
        'contract_version': CONTRACT_VERSION,
        'present': False,
        'campaign_state': 'corrupt_state_rejected',
        'status_by_trial': {},
        'integrity_error': reason,
        'raw_trial_content_stored': False,
        'authority_granted': False,
    }

def load_combined_trial_campaign_state(runtime_root=None) -> dict[str, Any]:
    state = load_json_file(_path(runtime_root), {}, expected_type=dict)
    if not state:
        return {
            'ok': True,
            'contract_version': CONTRACT_VERSION,
            'present': False,
            'campaign_state': 'not_prepared',
            'status_by_trial': {},
            'raw_trial_content_stored': False,
            'authority_granted': False,
        }
    r = dict(state)
    supplied = str(r.get('state_digest') or '')
    body = dict(r)
    body.pop('state_digest', None)
    if not supplied or supplied != _digest(body):
        return _rejected('state_digest_mismatch')
    try:
        catalog = build_combined_trial_catalog()
        plan = build_combined_trial_plan(catalog)
        readiness = build_combined_trial_campaign_readiness(
            catalog,
            plan,
            current_checkpoint=str(r.get('current_checkpoint') or ''),
            release_certified=bool(r.get('release_certified')),
            daily_use_engineering_ready=bool(r.get('daily_use_engineering_ready')),
        )
        expected = _prepared_state(catalog, plan, readiness)
    except (TypeError, ValueError, KeyError):
        return _rejected('state_semantic_reconstruction_failed')
    if r != expected:
        return _rejected('state_semantic_mismatch')
    return {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'present': True,
        **expected,
        'raw_trial_content_stored': False,
        'authority_granted': False,
    }

__all__ = ['CONTRACT_VERSION', 'prepare_combined_trial_campaign_state', 'load_combined_trial_campaign_state']
