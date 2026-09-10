from __future__ import annotations
"""v2727 read-only campaign-preparation observability."""
from typing import Any
from combined_trial_campaign_state_v2725 import load_combined_trial_campaign_state
from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
CONTRACT_VERSION='v2727.1'
def build_combined_trial_campaign_observability(runtime_root=None)->dict[str,Any]:
    s=load_combined_trial_campaign_state(runtime_root);statuses=dict(s.get('status_by_trial') or {})
    integrity_error=str(s.get('integrity_error') or '')
    if s.get('ok') is False:
        state='corrupt_state_rejected'
    elif not statuses:
        catalog=build_combined_trial_catalog();statuses={str(r.get('trial_id')):'not_started' for r in catalog.get('trials') or []};state='engineering_prepared_not_persisted'
    else: state=str(s.get('campaign_state') or 'not_prepared')
    return {'ok':s.get('ok') is not False,'contract_version':CONTRACT_VERSION,'state':state,'integrity_error':integrity_error,'trial_count':len(statuses),'passed_count':sum(v=='passed' for v in statuses.values()),'failed_count':sum(v=='failed' for v in statuses.values()),'not_started_count':sum(v=='not_started' for v in statuses.values()),'campaign_started':state not in {'not_prepared','engineering_prepared_not_persisted','prepared_not_started','corrupt_state_rejected'},'operator_campaign_start_required':True,'automatic_transition_permitted':False,'raw_trial_content_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_combined_trial_campaign_observability']
