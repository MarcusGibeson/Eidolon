from __future__ import annotations
"""v2601 planned-vs-realized project value calibration."""
from typing import Any, Mapping, Sequence
import hashlib,json,statistics
CONTRACT_VERSION='v2601.0';MIN_CALIBRATION=3
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_value_calibration(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    groups={}
    for r in rows[-128:]:
        if not isinstance(r,Mapping) or r.get('predicted_value') is None or r.get('realized_value') is None:continue
        code=str(r.get('strategy_code') or 'unspecified')[:80];groups.setdefault(code,[]).append((float(r['predicted_value']),float(r['realized_value']),r.get('effort_units')))
    profiles=[]
    for code,vals in sorted(groups.items()):
        ratios=[real/max(.0001,abs(pred)) for pred,real,_ in vals if pred!=0];errors=[real-pred for pred,real,_ in vals];n=len(vals);ratio=statistics.median(ratios) if ratios else 0.0;err=statistics.median(errors) if errors else 0.0
        if n<MIN_CALIBRATION:label='insufficient_history'
        elif ratio<.6:label='systematic_overprediction'
        elif ratio>1.4:label='systematic_underprediction'
        else:label='roughly_calibrated'
        efforts=[float(e) for _,_,e in vals if e is not None]
        profiles.append({'strategy_code':code,'sample_count':n,'median_realized_to_predicted_ratio':round(ratio,3),'median_value_error':round(err,3),'median_effort_units':round(statistics.median(efforts),3) if efforts else None,'calibration':label})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'profiles':profiles,'value_model_mutated':False,'automatic_priority_change_permitted':False,'authority_granted':False};out['calibration_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_value_calibration']
