from __future__ import annotations
"""v2668 advisory rehearsal-risk annotations for developer portfolio candidates."""
from typing import Any,Mapping,Sequence
import hashlib,json
CONTRACT_VERSION='v2668.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def annotate_portfolio_rehearsal_risk(candidates:Sequence[Mapping[str,Any]],comparisons:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 rows=[]
 for c in candidates[:24]:
  if not isinstance(c,Mapping):continue
  pid=str(c.get('project_id') or '')[:120];comp=comparisons.get(pid) if isinstance(comparisons,Mapping) else None;trend=str((comp or {}).get('trend') or 'insufficient');failures=list((comp or {}).get('failure_counts') or []);risk='unknown'
  if trend in {'worsening','unstable'}:risk='elevated'
  elif trend in {'stable','improving'}:risk='bounded'
  rows.append({'project_id':pid,'project_digest':str(c.get('project_digest') or '')[:64],'operator_priority':float(c.get('operator_priority') or 0),'rehearsal_trend':trend,'rehearsal_risk':risk,'latest_simulated_failure_count':int(failures[-1]) if failures else 0,'synthetic_evidence_only':True})
 out={'ok':True,'contract_version':CONTRACT_VERSION,'projects':rows,'project_count':len(rows),'synthetic_evidence_only':True,'portfolio_order_changed':False,'automatic_project_selection_permitted':False,'authority_granted':False};out['annotation_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','annotate_portfolio_rehearsal_risk']
