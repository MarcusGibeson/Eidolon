from __future__ import annotations
"""v2683 content-free post-generation audit for response grounding claims.

Audit-only. It never rewrites generated content and stores no response text.
"""
from typing import Any, Mapping
import hashlib, json, re
CONTRACT_VERSION='v2683.0'
_MEMORY_PATTERNS=(r'\bi (?:remember|recall)\b',r"\byou(?:'ve| have)? (?:told|said|mentioned)\b",r"\bwe(?:'ve| have)? (?:talked|discussed)\b",r'\bfrom what you told me\b',r'\bas you told me\b')
_EXEC_PATTERNS=(r"\bi(?:'ve| have)?\s+(?:successfully\s+|already\s+)?(?:sent|deleted|removed|installed|changed|updated|created|ran|executed|applied|submitted|uploaded|downloaded|saved|wrote|edited|moved|renamed|cancelled|canceled)\b",r"\b(?:it|that|the\s+\w+|your\s+\w+)(?:'s| has| was| is)\s+(?:already\s+)?(?:been\s+)?(?:sent|deleted|removed|installed|changed|updated|created|run|executed|applied|submitted|uploaded|downloaded|saved|written|edited|moved|renamed|cancelled|canceled)\b")
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def audit_response_grounding_output(text:str, policy:Mapping[str,Any], calibration:Mapping[str,Any], *, authoritative_execution_evidence:bool=False)->dict[str,Any]:
    normalized=' '.join(str(text or '').lower().split())
    mem_hits=sum(bool(re.search(p,normalized)) for p in _MEMORY_PATTERNS) if not bool(policy.get('personal_memory_reference_permitted')) else 0
    exec_hits=sum(bool(re.search(p,normalized)) for p in _EXEC_PATTERNS) if bool(calibration.get('must_not_claim_execution_without_receipt')) and not authoritative_execution_evidence else 0
    concerns=[]
    if mem_hits: concerns.append('unsupported_personal_memory_claim_shape')
    if exec_hits: concerns.append('execution_claim_without_authoritative_evidence_shape')
    out={'ok':not concerns,'contract_version':CONTRACT_VERSION,'concern_count':len(concerns),'concerns':concerns,'memory_claim_shape_count':mem_hits,'execution_claim_shape_count':exec_hits,
         'audit_only':True,'response_rewritten':False,'raw_response_stored':False,'raw_prompt_stored':False,'provider_contacted':False,'authority_granted':False}
    out['response_digest']=hashlib.sha256(str(text or '').encode()).hexdigest()
    out['policy_context_digest']=_digest(policy)
    out['calibration_context_digest']=_digest(calibration)
    out['execution_evidence_present']=bool(authoritative_execution_evidence)
    out['audit_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','audit_response_grounding_output']
