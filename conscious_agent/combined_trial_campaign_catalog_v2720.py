from __future__ import annotations
"""v2720 authoritative read-only catalog for the parked combined operator trial campaign."""
from typing import Any, Mapping
import hashlib, json

CONTRACT_VERSION = 'v2720.2'
TRIALS = (
    ('research','Research trial','v2503.5.6','read_only_public_research',()),
    ('read_only_capability','Real read-only capability trial','v2521.0','read_only_external_capability',()),
    ('provider_internal_voice','Provider-enabled internal-voice trial','v2532.9','provider_contact_no_external_action',()),
    ('memory_policy_adaptation','Memory retrieval policy adaptation trial','v2586.9','operator_reviewed_policy_change',()),
    ('response_repair_execution','Automatic response-grounding repair execution trial','v2689.9','user_visible_response_repair',()),
    ('verification_gap_remediation','Verification-gap remediation execution trial','v2568.9','supervised_source_test_change',()),
    ('architecture_project','Architecture project trial','v2503.8.0','self_architecture_project_design',()),
    ('project_start','Operator-selected project-start trial','v2643.9','supervised_project_start',('architecture_project',)),
)

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def build_combined_trial_catalog() -> dict[str, Any]:
    rows = []
    for i, (tid, name, minimum, risk, deps) in enumerate(TRIALS, 1):
        row = {
            'trial_id': tid,
            'display_name': name,
            'minimum_checkpoint': minimum,
            'risk_class': risk,
            'dependencies': list(deps),
            'ordinal_hint': i,
            'parked': True,
            'operator_start_required': True,
            'automatic_start_permitted': False,
            'raw_trial_content_stored': False,
        }
        row['trial_digest'] = _digest(row)
        rows.append(row)
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'trial_count': len(rows),
        'trials': rows,
        'combined_campaign_prepared': True,
        'campaign_started': False,
        'automatic_transition_permitted': False,
        'operator_confirmation_required_between_trials': True,
        'authority_granted': False,
    }
    out['catalog_digest'] = _digest(out)
    return out

def validate_combined_trial_catalog(catalog: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_combined_trial_catalog()
    if dict(catalog) != expected:
        raise ValueError('noncanonical_combined_trial_catalog')
    return expected

__all__ = ['CONTRACT_VERSION', 'TRIALS', 'build_combined_trial_catalog', 'validate_combined_trial_catalog']
