from __future__ import annotations
"""v2660 bounded runtime-only history for synthetic project rehearsals."""
from pathlib import Path
from typing import Any,Mapping,Sequence
import hashlib,json,os,tempfile
CONTRACT_VERSION='v2660.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_rehearsal_history(rows:Sequence[Mapping[str,Any]],limit:int=32)->dict[str,Any]:
 out=[]
 for r in rows[-max(1,min(128,int(limit))):]:
  if not isinstance(r,Mapping):continue
  out.append({'project_id':str(r.get('project_id') or '')[:120],'project_digest':str(r.get('project_digest') or '')[:64],'state':str(r.get('simulation_health_state') or r.get('state') or 'insufficient')[:32],'scenario_count':int(r.get('scenario_count') or 0),'failure_mode_count':len(r.get('failure_modes') or []),'synthetic_evidence_only':True})
 result={'ok':True,'contract_version':CONTRACT_VERSION,'rows':out,'count':len(out),'synthetic_evidence_only':True,'real_outcome_history':False,'automatic_strategy_learning_permitted':False,'authority_granted':False};result['history_digest']=_digest(result);return result
__all__=['CONTRACT_VERSION','build_rehearsal_history']
