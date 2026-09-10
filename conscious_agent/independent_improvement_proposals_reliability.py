from __future__ import annotations
from typing import Any,Iterable,Mapping
from independent_improvement_proposals_foundations import DENIED_AUTHORITY
CONTRACT_VERSION='v1291.8'
def assess_improvement_proposal_reliability(results:Iterable[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(x) for x in results];v=[]
 for i,r in enumerate(rows):
  p=f'result_{i}'
  if not r.get('observations_do_not_imply_work'):v.append(p+':observation_work_conflation')
  for q in r.get('proposals') or []:
   if q.get('state')!='proposal_only' or q.get('executes_work') or q.get('creates_backlog_item'):v.append(p+':proposal_became_work')
   if not q.get('requires_operator_selection'):v.append(p+':operator_selection_missing')
   if any(bool(q.get(k)) for k in DENIED_AUTHORITY):v.append(p+':proposal_authority_expansion')
  if any(bool(r.get(k)) for k in DENIED_AUTHORITY):v.append(p+':result_authority_expansion')
 return {'contract_version':CONTRACT_VERSION,'ok':not v,'result_count':len(rows),'violations':v,'violation_count':len(v),'content_free':True,'read_only':True,**DENIED_AUTHORITY}
