from __future__ import annotations
"""v2690 structural outcome evidence from conversation-target output enforcement."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2690.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_conversation_target_outcome(enforcement:Mapping[str,Any])->dict[str,Any]:
    signals=[]
    mapping=(('whole_response_replaced','whole_response_duplicate_or_off_target'),('grounded_repair_applied','specific_mistake_grounding_repair'),('present_stakes_grounding_applied','generic_present_stakes_repair'))
    for key,code in mapping:
        if bool(enforcement.get(key)): signals.append(code)
    if int(enforcement.get('constraint_sentences_removed') or 0)>0: signals.append('rejected_shared_responsibility_removed')
    if int(enforcement.get('duplicate_sentences_removed') or 0)>0: signals.append('repetition_removed')
    severity='high' if any(x in signals for x in ('whole_response_duplicate_or_off_target','specific_mistake_grounding_repair')) else ('medium' if signals else 'none')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'repair_signal_count':len(signals),'repair_signals':signals,'severity':severity,'enforcement_applied':bool(enforcement.get('applied')),'conversation_policy_mutated':False,'raw_response_stored':False,'raw_prompt_stored':False,'provider_contacted':False,'authority_granted':False};out['outcome_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_conversation_target_outcome']
