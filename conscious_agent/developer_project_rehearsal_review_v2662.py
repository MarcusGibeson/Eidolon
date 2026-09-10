from __future__ import annotations
"""v2662 advisory learning review over rehearsal history, isolated from real strategy learning."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2662.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_rehearsal_learning_review(history:Mapping[str,Any])->dict[str,Any]:
 rows=history.get('rows') or [];attention=sum(1 for r in rows if isinstance(r,Mapping) and str(r.get('state')) in {'attention','insufficient'});failures=sum(int(r.get('failure_mode_count') or 0) for r in rows if isinstance(r,Mapping))
 out={'ok':bool(history.get('ok')),'contract_version':CONTRACT_VERSION,'rehearsal_count':len(rows),'attention_rehearsal_count':attention,'simulated_failure_mode_count':failures,'candidate_type':'rehearsal_risk_pattern_candidate' if failures else 'rehearsal_nominal_pattern_candidate','synthetic_evidence_only':True,'durable_real_strategy_lesson_committed':False,'real_strategy_weights_mutated':False,'operator_review_required':bool(rows),'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_rehearsal_learning_review']
