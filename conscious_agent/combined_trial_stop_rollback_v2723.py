from __future__ import annotations
"""v2723 stop/rollback matrix for the combined live trial campaign."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2723.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_trial_stop_rollback_matrix(catalog:Mapping[str,Any])->dict[str,Any]:
    rows=[]
    for t in catalog.get('trials') or []:
        tid=str(t.get('trial_id'));risk=str(t.get('risk_class'))
        rollback='restore_pretrial_checkpoint' if risk in {'operator_reviewed_policy_change','supervised_source_test_change','supervised_project_start'} else 'disable_trial_feature_and_restore_prior_runtime_state'
        stop=['authority_mismatch','unexpected_mutation','privacy_boundary_violation','evidence_binding_failure']
        if risk=='provider_contact_no_external_action':stop.append('provider_scope_escape')
        if risk in {'supervised_source_test_change','supervised_project_start'}:stop.extend(['verification_regression','source_boundary_violation'])
        rows.append({'trial_id':tid,'stop_conditions':stop,'rollback_strategy':rollback,'automatic_rollback_permitted':False,'operator_review_required':True})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'rows':rows,'global_stop_on_unexpected_authority_expansion':True,'global_stop_on_privacy_violation':True,'automatic_next_trial_after_failure':False,'automatic_rollback_permitted':False,'authority_granted':False};out['matrix_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_trial_stop_rollback_matrix']
