from __future__ import annotations
from tempfile import TemporaryDirectory
from combined_trial_campaign_catalog_v2720 import build_combined_trial_catalog
from combined_trial_campaign_plan_v2721 import build_combined_trial_plan
from combined_trial_stop_rollback_v2723 import build_trial_stop_rollback_matrix
from combined_trial_campaign_readiness_v2724 import build_combined_trial_campaign_readiness
from combined_trial_campaign_state_v2725 import prepare_combined_trial_campaign_state
from combined_trial_campaign_runbook_v2726 import build_combined_trial_runbook
from combined_trial_campaign_observability_v2727 import build_combined_trial_campaign_observability

def build_checkpoint():
    c=build_combined_trial_catalog();p=build_combined_trial_plan(c);m=build_trial_stop_rollback_matrix(c);r=build_combined_trial_campaign_readiness(c,p,current_checkpoint='v2729.9',release_certified=True,daily_use_engineering_ready=True);book=build_combined_trial_runbook(c,p,m)
    with TemporaryDirectory() as td:
        state=prepare_combined_trial_campaign_state(c,p,r,runtime_root=td);o=build_combined_trial_campaign_observability(td)
        checks={'eight_trials':c['trial_count']==8,'ready_for_review':r['ready_for_operator_campaign_review'],'prepared_not_started':state['campaign_state']=='prepared_not_started' and not o['campaign_started'],'runbook':book['step_count']==8,'confirm_each':book['operator_confirmation_between_every_step'],'no_auto_transition':not book['automatic_transition_permitted'] and not o['automatic_transition_permitted'],'no_content':not o['raw_trial_content_stored'],'no_authority':not o['authority_granted']}
        return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
