from __future__ import annotations
"""v2673 deterministic assertion calibration from grounding policy."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2673.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_assertion_calibration(policy:Mapping[str,Any])->dict[str,Any]:
 a=str(policy.get('assertiveness') or 'cautious');level='normal' if a=='grounded' else ('limited' if a=='current_turn_only' else 'explicit_uncertainty')
 out={'ok':bool(policy.get('ok')),'contract_version':CONTRACT_VERSION,'assertion_level':level,'may_state_retrieved_personal_fact':bool(policy.get('personal_memory_reference_permitted')),'must_label_memory_uncertainty':bool(policy.get('preserve_uncertainty')),'must_honor_correction_precedence':bool(policy.get('correction_precedence')),'must_not_invent_memory':True,'must_not_claim_execution_without_receipt':True,'response_content_generated':False,'authority_granted':False};out['calibration_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_assertion_calibration']
