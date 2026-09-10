from __future__ import annotations
from daily_use_sustained_readiness_v2716 import build_sustained_daily_use_readiness
from daily_use_failure_mode_review_v2717 import build_daily_use_failure_mode_review
from daily_use_trial_readiness_packet_v2718 import build_daily_use_trial_readiness_packet

def build_checkpoint():
    obs={'state':'nominal'};r=build_sustained_daily_use_readiness(obs,continuity_supported=True,background_cognition_supported=True,memory_persistence_supported=True,queue_persistence_supported=True);f=build_daily_use_failure_mode_review({'concerns':[]},r);p=build_daily_use_trial_readiness_packet(r,f)
    checks={'engineering_ready':r['engineering_ready'],'not_live_proven':not r['real_daily_use_proven'],'no_failure_modes':f['failure_mode_count']==0,'operator_review_ready':p['eligible_for_operator_trial_review'],'trial_not_started':not p['trial_started'] and not p['automatic_trial_start'],'selection_required':p['operator_selection_required'],'no_text':not p['raw_conversation_text_stored'],'no_authority':not p['authority_granted']}
    return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
