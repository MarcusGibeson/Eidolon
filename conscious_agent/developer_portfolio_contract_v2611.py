from __future__ import annotations
"""v2611 read-only developer portfolio candidate contract."""
from typing import Any, Mapping, Sequence
import hashlib, json
CONTRACT_VERSION='v2611.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_developer_portfolio_candidates(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 out=[]
 for r in rows[:24]:
  if not isinstance(r,Mapping): continue
  pid=str(r.get('project_id') or '')[:120]; strat=str(r.get('strategy_code') or 'unspecified')[:80]
  if not pid: continue
  out.append({'project_id':pid,'project_digest':str(r.get('project_digest') or _digest({'project_id':pid}))[:64],'strategy_code':strat,'expected_value':max(-1,min(1,float(r.get('expected_value') or 0))),'effort':max(0,float(r.get('effort') or 0)),'risk':max(0,min(1,float(r.get('risk') or 0))),'reversibility':max(0,min(1,float(r.get('reversibility') if r.get('reversibility') is not None else .5))),'operator_priority':max(0,min(1,float(r.get('operator_priority') if r.get('operator_priority') is not None else .5))),'verification_confidence':max(0,min(1,float(r.get('verification_confidence') if r.get('verification_confidence') is not None else .5))),'candidate_only':True})
 result={'ok':True,'contract_version':CONTRACT_VERSION,'candidates':out,'candidate_count':len(out),'automatic_project_selection_permitted':False,'campaign_start_authorized':False,'operator_priority_overridden':False,'authority_granted':False};result['portfolio_digest']=_digest(result);return result
__all__=['CONTRACT_VERSION','build_developer_portfolio_candidates']
