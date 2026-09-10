from __future__ import annotations
"""v2650 content-minimized rehearsal health summary."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2650.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_simulation_health(review:Mapping[str,Any],scenarios:Mapping[str,Any])->dict[str,Any]:
 failures=len(review.get('failure_modes') or []);count=int(scenarios.get('scenario_count') or 0)
 state='insufficient' if count<2 else ('attention' if failures else 'nominal')
 out={'ok':bool(review.get('ok')) and bool(scenarios.get('ok')),'contract_version':CONTRACT_VERSION,'state':state,'scenario_count':count,'failure_mode_count':failures,'adversarial_rehearsal_present':bool(scenarios.get('includes_adversarial')),'operator_review_required':state!='nominal' or failures>0,'content_minimized':True,'simulation_only':True,'automatic_project_start_permitted':False,'authority_granted':False};out['health_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_simulation_health']
