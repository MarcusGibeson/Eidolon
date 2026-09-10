from __future__ import annotations
"""Read-only v1199.5 operator final-candidate review and handoff acceptance."""
import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION="v1199.5"
CHECKPOINT_ID="final-candidate-review-checkpoint"
REVIEW_ACTIONS=("candidate_acceptance","retained_verification_acceptance","risk_ledger_acceptance","desktop_handoff_acceptance","native_provider_handoff_acceptance")
DECISIONS=("approve","reject","defer")
PURPOSE_CODES=("review_final_source_candidate","review_retained_verification","review_unresolved_risks","review_desktop_handoff","review_native_provider_handoff")
PRIVATE_TOKENS=("prompt","conversation_text","memory_content","secret","password","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","credential","api_key")

def _digest(v:object)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:
    s=str(v or ""); return len(s)==64 and all(c in "0123456789abcdef" for c in s)
def _private(v:object,prefix:str="")->list[str]:
    out=[]
    if isinstance(v,Mapping):
        for k,x in v.items():
            p=f"{prefix}.{k}" if prefix else str(k)
            if any(t in str(k).lower() for t in PRIVATE_TOKENS): out.append(p)
            out.extend(_private(x,p))
    elif isinstance(v,(list,tuple)):
        for i,x in enumerate(v): out.extend(_private(x,f"{prefix}[{i}]"))
    return sorted(set(out))

def create_review_request(*,review_id:str,candidate_id:str,action:str,decision:str,sequence:int,prior_review_receipt_digest:str|None,snapshot_digest:str,context_digest:str,candidate_plan_digest:str,candidate_assessment_digest:str,source_manifest_digest:str,retained_verification_digest:str,unresolved_risk_digest:str,desktop_handoff_digest:str,native_provider_handoff_digest:str,operator_review_digest:str,purpose_code:str)->dict[str,Any]:
    row={"contract_version":CONTRACT_VERSION,"review_id":review_id,"candidate_id":candidate_id,"action":action,"decision":decision,"sequence":sequence,"prior_review_receipt_digest":prior_review_receipt_digest,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"candidate_plan_digest":candidate_plan_digest,"candidate_assessment_digest":candidate_assessment_digest,"source_manifest_digest":source_manifest_digest,"retained_verification_digest":retained_verification_digest,"unresolved_risk_digest":unresolved_risk_digest,"desktop_handoff_digest":desktop_handoff_digest,"native_provider_handoff_digest":native_provider_handoff_digest,"operator_review_digest":operator_review_digest,"purpose_code":purpose_code,"content_free":True,"read_only":True,"source_only":True,"presentation_only":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"release_approved":False,"approval_created":False,"approval_consumed":False,"candidate_prepared":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"publication_performed":False,"release_performed":False,"provider_contacted":False,"model_contacted":False,"process_started":False,"thread_started":False,"source_modified":False,"runtime_mutated":False,"automatic_continuation":False,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}
    row["request_digest"]=_digest(row); return row

def review_final_candidate(request:Mapping[str,Any],*,current_snapshot_digest:str,current_context_digest:str,expected_candidate_plan_digest:str,expected_candidate_assessment_digest:str,expected_source_manifest_digest:str,expected_retained_verification_digest:str,expected_unresolved_risk_digest:str,expected_desktop_handoff_digest:str,expected_native_provider_handoff_digest:str,expected_sequence:int,expected_prior_review_receipt_digest:str|None)->dict[str,Any]:
    r=dict(request); errors=[]
    errors += [f"private_field:{x}" for x in _private(r)]
    u=dict(r); supplied=u.pop("request_digest",None)
    if supplied!=_digest(u): errors.append("request_tamper")
    if r.get("contract_version")!=CONTRACT_VERSION: errors.append("unsupported_contract")
    if r.get("action") not in REVIEW_ACTIONS: errors.append("unsupported_action")
    if r.get("decision") not in DECISIONS: errors.append("unsupported_decision")
    if r.get("purpose_code") not in PURPOSE_CODES: errors.append("unsupported_purpose")
    if r.get("snapshot_digest")!=current_snapshot_digest: errors.append("stale_snapshot")
    if r.get("context_digest")!=current_context_digest: errors.append("stale_context")
    expected={"candidate_plan_digest":expected_candidate_plan_digest,"candidate_assessment_digest":expected_candidate_assessment_digest,"source_manifest_digest":expected_source_manifest_digest,"retained_verification_digest":expected_retained_verification_digest,"unresolved_risk_digest":expected_unresolved_risk_digest,"desktop_handoff_digest":expected_desktop_handoff_digest,"native_provider_handoff_digest":expected_native_provider_handoff_digest}
    for k,v in expected.items():
        if r.get(k)!=v: errors.append(f"stale_{k}")
    for k in ("snapshot_digest","context_digest",*expected.keys(),"operator_review_digest"):
        if not _is_digest(r.get(k)): errors.append(f"malformed_{k}")
    if r.get("sequence")!=expected_sequence: errors.append("invalid_review_sequence")
    if r.get("prior_review_receipt_digest")!=expected_prior_review_receipt_digest: errors.append("broken_review_lineage")
    if expected_sequence>1 and not _is_digest(r.get("prior_review_receipt_digest")): errors.append("malformed_prior_review_receipt_digest")
    forbidden=("candidate_accepted","handoff_accepted","risk_waived","release_approved","approval_created","approval_consumed","candidate_prepared","installation_performed","promotion_performed","certification_performed","publication_performed","release_performed","provider_contacted","model_contacted","process_started","thread_started","source_modified","runtime_mutated","automatic_continuation","global_profile_pass_claimed")
    for f in forbidden:
        if r.get(f) is not False: errors.append(f"forbidden_claim:{f}")
    for f in ("content_free","read_only","source_only","presentation_only"):
        if r.get(f) is not True: errors.append(f"boundary_loss:{f}")
    if r.get("authority_state")!="separate_not_granted": errors.append("authority_expansion")
    decision=r.get("decision")
    outcome={"approve":"eligible_for_separate_v1200_decision_gate","reject":"rejected_for_handoff","defer":"deferred_for_more_evidence"}.get(decision,"blocked")
    if errors: outcome="blocked"
    receipt_payload={"request_digest":r.get("request_digest"),"decision":decision,"action":r.get("action"),"sequence":r.get("sequence"),"outcome":outcome,"errors":sorted(set(errors))}
    receipt=_digest(receipt_payload)
    return {"ok":not errors,"status":outcome,"errors":sorted(set(errors)),"review_receipt_digest":receipt,"summary":{"action":r.get("action"),"decision":decision,"sequence":r.get("sequence"),"presentation_only":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"release_approved":False,"source_modified":False,"runtime_mutated":False,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}}
