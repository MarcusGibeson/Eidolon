from __future__ import annotations
from typing import Any,Iterable,Mapping
from value_risk_deliberation_foundations import DENIED_AUTHORITY
CONTRACT_VERSION='v1292.8'
def assess_value_risk_deliberation_reliability(rows:Iterable[Mapping[str,Any]])->dict[str,Any]:
 rs=[dict(x) for x in rows];v=[]
 for i,r in enumerate(rs):
  p=f'deliberation_{i}';rec=str(r.get('recommended_proposal_id') or '')
  if r.get('recommendation_is_priority_mutation') is not False:v.append(p+':priority_mutation_claim')
  if r.get('recommendation_is_authorization') is not False:v.append(p+':authorization_claim')
  if rec:
   matches=[x for x in r.get('ranked') or [] if x.get('proposal_id')==rec]
   if len(matches)!=1:v.append(p+':recommended_identity_missing')
   elif matches[0].get('blocked'):v.append(p+':blocked_candidate_recommended')
   if not r.get('operator_decision_required'):v.append(p+':operator_decision_missing')
  if any(bool(r.get(k)) for k in DENIED_AUTHORITY):v.append(p+':authority_expansion')
 return {'contract_version':CONTRACT_VERSION,'ok':not v,'deliberation_count':len(rs),'violations':v,'violation_count':len(v),'content_free':True,'read_only':True,**DENIED_AUTHORITY}
