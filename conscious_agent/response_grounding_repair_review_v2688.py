from __future__ import annotations
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2688.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_grounding_repair_review(candidate:Mapping[str,Any])->dict[str,Any]:
 ready=str(candidate.get('state'))=='repair_candidate_ready' and bool(candidate.get('action_codes'))
 out={'ok':True,'contract_version':CONTRACT_VERSION,'review_required':ready,'state':'operator_review_required' if ready else 'no_review_required','candidate_digest':str(candidate.get('candidate_digest') or '')[:64],'action_codes':[str(x)[:100] for x in candidate.get('action_codes') or []],'automatic_response_rewrite':False,'automatic_provider_regeneration':False,'response_mutated':False,'authority_granted':False,'automatic_repair_permitted':False,'operator_execution_available':ready,'operator_confirmation_required':ready};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_grounding_repair_review']
