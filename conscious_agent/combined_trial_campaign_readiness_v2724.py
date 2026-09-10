from __future__ import annotations
"""v2724 engineering readiness for operator-reviewed combined trial campaign."""
from typing import Any, Mapping
import hashlib, json, re
from combined_trial_campaign_catalog_v2720 import validate_combined_trial_catalog
from combined_trial_campaign_plan_v2721 import validate_combined_trial_plan

CONTRACT_VERSION = 'v2724.2'

def _digest(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def _ver(v: str) -> tuple[int, int, int, int]:
    nums = [int(x) for x in re.findall(r'\d+', str(v))[:4]]
    return tuple((nums + [0, 0, 0, 0])[:4])

def build_combined_trial_campaign_readiness(
    catalog: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    current_checkpoint: str,
    release_certified: bool,
    daily_use_engineering_ready: bool = True,
) -> dict[str, Any]:
    canonical_catalog = validate_combined_trial_catalog(catalog)
    blockers = []
    try:
        canonical_plan = validate_combined_trial_plan(canonical_catalog, plan)
    except ValueError:
        canonical_plan = None
        blockers.append('trial_plan_catalog_mismatch')
    cur = _ver(current_checkpoint)
    if not release_certified:
        blockers.append('current_release_not_certified')
    if not daily_use_engineering_ready:
        blockers.append('daily_use_engineering_readiness_incomplete')
    for row in canonical_catalog['trials']:
        if _ver(str(row['minimum_checkpoint'])) > cur:
            blockers.append('minimum_checkpoint_not_reached:' + str(row['trial_id']))
    ready = not blockers
    out = {
        'ok': True,
        'contract_version': CONTRACT_VERSION,
        'catalog_digest': canonical_catalog['catalog_digest'],
        'plan_digest': canonical_plan['plan_digest'] if canonical_plan is not None else str(plan.get('plan_digest') or '')[:64],
        'state': 'ready_for_operator_campaign_review' if ready else 'not_ready',
        'ready_for_operator_campaign_review': ready,
        'blockers': blockers,
        'current_checkpoint': str(current_checkpoint)[:40],
        'release_certified': bool(release_certified),
        'daily_use_engineering_ready': bool(daily_use_engineering_ready),
        'campaign_started': False,
        'automatic_campaign_start': False,
        'operator_selection_required': True,
        'authority_granted': False,
    }
    out['readiness_digest'] = _digest(out)
    return out

def validate_combined_trial_campaign_readiness(
    catalog: Mapping[str, Any], plan: Mapping[str, Any], readiness: Mapping[str, Any]
) -> dict[str, Any]:
    current_checkpoint = str(readiness.get('current_checkpoint') or '')
    expected = build_combined_trial_campaign_readiness(
        catalog,
        plan,
        current_checkpoint=current_checkpoint,
        release_certified=bool(readiness.get('release_certified')),
        daily_use_engineering_ready=bool(readiness.get('daily_use_engineering_ready')),
    )
    if dict(readiness) != expected:
        raise ValueError('noncanonical_combined_trial_readiness')
    return expected

__all__ = ['CONTRACT_VERSION', 'build_combined_trial_campaign_readiness', 'validate_combined_trial_campaign_readiness']
