from __future__ import annotations
"""v2588 advisory arbitration over context attribution; does not rebuild the prompt."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2588.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_context_relevance_arbitration(attribution:Mapping[str,Any])->dict[str,Any]:
    pressure=float(attribution.get('budget_pressure') or 0.0);mstate=str(attribution.get('memory_retrieval_state') or 'unknown')
    omitted=set(attribution.get('omitted_lanes') or ());included=set(attribution.get('included_lanes') or ())
    advisories=[]
    if pressure>=.92: advisories.append({'code':'high_prompt_pressure','priority':'high','recommendation':'prefer_direct_and_active_thread_context'})
    elif pressure>=.78: advisories.append({'code':'elevated_prompt_pressure','priority':'medium','recommendation':'review_low_salience_optional_context'})
    if mstate in {'weak_context_only','no_useful_memory'} and int(attribution.get('memories_included') or 0)>0: advisories.append({'code':'weak_memory_context_present','priority':'medium','recommendation':'preserve_uncertainty_and_avoid_memory_overweight'})
    if int(attribution.get('history_turns_omitted') or 0)>0 and int(attribution.get('history_turns_included') or 0)==0: advisories.append({'code':'history_fully_omitted','priority':'medium','recommendation':'verify_active_thread_continuity'})
    if omitted and not included: advisories.append({'code':'optional_context_fully_omitted','priority':'low','recommendation':'confirm_direct_answer_path'})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'advisories':advisories[:8],'advisory_count':len(advisories[:8]),'current_message_priority':'protected','protected_instruction_priority':'protected','prompt_rebuild_permitted':False,'context_lane_mutation_performed':False,'automatic_budget_change_permitted':False,'provider_contacted':False,'authority_granted':False}
    out['arbitration_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_context_relevance_arbitration']
