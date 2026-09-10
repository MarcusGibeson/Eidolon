from __future__ import annotations
"""v2585 operator-review packets for retrieval-policy learning evidence."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2585.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_memory_retrieval_policy_review_packet(observability:Mapping[str,Any])->dict[str,Any]:
    candidates=[]
    for row in observability.get('profiles') or []:
        if not isinstance(row,Mapping) or row.get('history_label')!='adverse_history':continue
        candidates.append({'retrieval_state':str(row.get('retrieval_state') or 'unknown')[:48],'observation_count':int(row.get('count') or 0),'negative_count':int(row.get('negative') or 0),'correction_count':int(row.get('corrections') or 0),'evidence_confidence':float(row.get('evidence_confidence') or 0.0),'recommended_review':'inspect_precision_thresholds_and_evidence_sources','policy_change_applied':False})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'review_required':bool(candidates),'candidates':candidates[:8],'operator_selection_required':bool(candidates),'automatic_policy_change_permitted':False,'retrieval_weights_changed':False,'thresholds_changed':False,'memory_mutated':False,'source_mutated':False,'provider_contacted':False,'authority_granted':False,'raw_content_stored':False}
    out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_memory_retrieval_policy_review_packet']
