from __future__ import annotations
"""v2726 content-minimized operator runbook for combined trials."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2726.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_combined_trial_runbook(catalog:Mapping[str,Any],plan:Mapping[str,Any],stop_matrix:Mapping[str,Any])->dict[str,Any]:
    by={str(r.get('trial_id')):dict(r) for r in catalog.get('trials') or []};stops={str(r.get('trial_id')):dict(r) for r in stop_matrix.get('rows') or []};steps=[]
    for p in plan.get('plan') or []:
        tid=str(p.get('trial_id'));t=by[tid];sr=stops.get(tid,{})
        steps.append({'sequence':int(p.get('sequence') or 0),'trial_id':tid,'display_name':str(t.get('display_name')),'operator_action':'explicitly_start_this_trial','preconditions':['prior_dependency_trials_reviewed'] if t.get('dependencies') else ['campaign_readiness_reviewed'],'evidence_required':['trial_specific_structural_receipts','checkpoint_or_runtime_digest','operator_observation'],'pass_rule':'trial_specific_pass_criteria_must_be_explicitly_reviewed','stop_conditions':list(sr.get('stop_conditions') or []),'rollback_strategy':str(sr.get('rollback_strategy') or ''),'automatic_start_permitted':False,'automatic_next_step_permitted':False})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'step_count':len(steps),'steps':steps,'operator_confirmation_between_every_step':True,'campaign_started':False,'raw_trial_content_stored':False,'automatic_transition_permitted':False,'authority_granted':False};out['runbook_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_combined_trial_runbook']
