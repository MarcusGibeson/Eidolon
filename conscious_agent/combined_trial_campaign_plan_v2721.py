from __future__ import annotations
"""v2721 risk/dependency-aware operator-review plan for combined trials."""
from typing import Any, Mapping
import hashlib, json
from combined_trial_campaign_catalog_v2720 import validate_combined_trial_catalog

CONTRACT_VERSION = 'v2721.2'
_RISK_ORDER = {
    'read_only_public_research': 10,
    'read_only_external_capability': 20,
    'provider_contact_no_external_action': 30,
    'operator_reviewed_policy_change': 40,
    'user_visible_response_repair': 50,
    'supervised_source_test_change': 60,
    'self_architecture_project_design': 70,
    'supervised_project_start': 80,
}

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def build_combined_trial_plan(catalog: Mapping[str, Any]) -> dict[str, Any]:
    canonical = validate_combined_trial_catalog(catalog)
    rows = [dict(r) for r in canonical['trials']]
    by_id = {str(r['trial_id']): r for r in rows}
    planned = []
    remaining = set(by_id)
    while remaining:
        eligible = [by_id[t] for t in remaining if all(str(d) not in remaining for d in by_id[t]['dependencies'])]
        if not eligible:
            raise ValueError('trial_dependency_cycle')
        eligible.sort(key=lambda r: (_RISK_ORDER.get(str(r['risk_class']), 99), int(r['ordinal_hint']), str(r['trial_id'])))
        row = eligible[0]
        remaining.remove(str(row['trial_id']))
        planned.append({
            'sequence': len(planned) + 1,
            'trial_id': row['trial_id'],
            'trial_digest': row['trial_digest'],
            'risk_class': row['risk_class'],
            'dependencies': list(row['dependencies']),
            'state': 'awaiting_operator_start',
            'operator_confirmation_required': True,
            'automatic_start_permitted': False,
        })
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'catalog_digest': canonical['catalog_digest'],
        'trial_count': len(planned),
        'plan': planned,
        'campaign_started': False,
        'next_trial_auto_selected': False,
        'operator_may_reorder_with_dependency_review': True,
        'automatic_transition_permitted': False,
        'authority_granted': False,
    }
    out['plan_digest'] = _digest(out)
    return out

def validate_combined_trial_plan(catalog: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_combined_trial_plan(catalog)
    if dict(plan) != expected:
        raise ValueError('noncanonical_combined_trial_plan')
    return expected

__all__ = ['CONTRACT_VERSION', 'build_combined_trial_plan', 'validate_combined_trial_plan']
