from __future__ import annotations
"""v2665 compare repeated synthetic rehearsals for one project digest lineage."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2665.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def compare_project_rehearsals(history:Mapping[str,Any],project_id:str)->dict[str,Any]:
 pid=str(project_id or '')[:120];rows=[r for r in history.get('rows') or [] if isinstance(r,Mapping) and str(r.get('project_id') or '')==pid][-16:]
 states=[str(r.get('state') or 'insufficient') for r in rows];failures=[int(r.get('failure_mode_count') or 0) for r in rows]
 transitions=sum(1 for a,b in zip(states,states[1:]) if a!=b);trend='insufficient'
 if len(rows)>=2:
  if failures[-1]<failures[0]:trend='improving'
  elif failures[-1]>failures[0]:trend='worsening'
  elif transitions:trend='unstable'
  else:trend='stable'
 out={'ok':True,'contract_version':CONTRACT_VERSION,'project_id':pid,'rehearsal_count':len(rows),'states':states,'failure_counts':failures,'state_transition_count':transitions,'trend':trend,'synthetic_evidence_only':True,'real_project_outcome_inferred':False,'automatic_strategy_change_permitted':False,'authority_granted':False};out['comparison_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','compare_project_rehearsals']
