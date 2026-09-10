from __future__ import annotations
"""v2606 bounded confidence annotations from historical project strategy evidence."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2606.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_strategy_confidence_annotations(reliability:Mapping[str,Any],calibration:Mapping[str,Any])->dict[str,Any]:
 cal={str(x.get('strategy_code')):x for x in calibration.get('profiles') or [] if isinstance(x,Mapping)};rows=[]
 for r in reliability.get('profiles') or []:
  if not isinstance(r,Mapping):continue
  code=str(r.get('strategy_code') or 'unspecified');rel=str(r.get('reliability') or 'insufficient_history');cl=str((cal.get(code) or {}).get('calibration') or 'insufficient_history')
  factor=1.0
  if rel=='underperforming':factor*=.65
  elif rel=='reliable':factor*=1.08
  if cl=='systematic_overprediction':factor*=.75
  elif cl=='systematic_underprediction':factor*=1.05
  factor=max(.4,min(1.1,factor));rows.append({'strategy_code':code,'confidence_factor':round(factor,3),'reliability':rel,'calibration':cl,'operator_priority_unchanged':True})
 out={'ok':True,'contract_version':CONTRACT_VERSION,'annotations':rows[:16],'automatic_plan_reprioritization_permitted':False,'operator_priority_unchanged':True,'plan_mutation_performed':False,'authority_granted':False};out['annotation_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_strategy_confidence_annotations']
