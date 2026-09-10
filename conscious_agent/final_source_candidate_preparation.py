from __future__ import annotations
"""Read-only v1199.2 final source-only candidate preparation foundations."""
import hashlib, json
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1199.2"
CHECKPOINT_ID = "final-source-candidate-preparation-checkpoint"
PREPARATION_AREAS = (
    "source_manifest", "retained_verification", "unresolved_risks", "desktop_handoff",
    "native_provider_handoff", "privacy_boundary", "authority_boundary", "release_boundary",
)
RISK_SEVERITIES = ("critical", "high", "medium", "low")
RISK_STATES = ("open", "mitigated_not_closed", "accepted_for_review", "deferred")
PRIVATE_TOKENS = ("prompt", "conversation_text", "memory_content", "secret", "password", "raw_source", "patch", "stdout", "stderr", "provider_payload", "private_reasoning", "credential", "api_key")

def _digest(v: object) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()

def _is_digest(v: object) -> bool:
    s=str(v or ""); return len(s)==64 and all(c in "0123456789abcdef" for c in s)

def _private(v: object, prefix: str="") -> list[str]:
    out=[]
    if isinstance(v, Mapping):
        for k,x in v.items():
            p=f"{prefix}.{k}" if prefix else str(k)
            if any(t in str(k).lower() for t in PRIVATE_TOKENS): out.append(p)
            out.extend(_private(x,p))
    elif isinstance(v,(list,tuple)):
        for i,x in enumerate(v): out.extend(_private(x,f"{prefix}[{i}]"))
    return sorted(set(out))

def create_candidate_plan(*, candidate_id:str, snapshot_digest:str, context_digest:str, source_version:str, source_manifest_digest:str, retained_verification_digest:str, unresolved_risk_digest:str, desktop_handoff_digest:str, native_provider_handoff_digest:str, purpose_code:str, max_manifest_files:int=5000, max_verification_rows:int=512, max_risks:int=128) -> dict[str,Any]:
    row={"contract_version":CONTRACT_VERSION,"candidate_id":candidate_id,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"source_version":source_version,"source_manifest_digest":source_manifest_digest,"retained_verification_digest":retained_verification_digest,"unresolved_risk_digest":unresolved_risk_digest,"desktop_handoff_digest":desktop_handoff_digest,"native_provider_handoff_digest":native_provider_handoff_digest,"purpose_code":purpose_code,"max_manifest_files":max_manifest_files,"max_verification_rows":max_verification_rows,"max_risks":max_risks,"content_free":True,"read_only":True,"source_only":True,"candidate_prepared":False,"release_approved":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"publication_performed":False,"release_performed":False,"provider_contacted":False,"model_contacted":False,"process_started":False,"thread_started":False,"source_modified":False,"runtime_mutated":False,"approval_created":False,"approval_consumed":False,"automatic_continuation":False,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}
    row["plan_digest"]=_digest(row); return row

def create_manifest_entry(*, path_id:str, sequence:int, file_digest:str, size_bytes:int, category:str="source") -> dict[str,Any]:
    row={"contract_version":CONTRACT_VERSION,"path_id":path_id,"sequence":sequence,"file_digest":file_digest,"size_bytes":size_bytes,"category":category,"content_free":True,"source_only":True,"private_content_present":False,"runtime_artifact":False,"compiled_artifact":False,"settings_artifact":False}
    row["entry_digest"]=_digest(row); return row

def create_verification_row(*, verifier_id:str, sequence:int, classification:str, status:str, passed:int, total:int, evidence_digest:str) -> dict[str,Any]:
    row={"contract_version":CONTRACT_VERSION,"verifier_id":verifier_id,"sequence":sequence,"classification":classification,"status":status,"passed":passed,"total":total,"evidence_digest":evidence_digest,"content_free":True,"executed_by_contract":False,"global_pass_inferred":False}
    row["row_digest"]=_digest(row); return row

def create_risk(*, risk_id:str, sequence:int, severity:str, state:str, owner:str, evidence_digest:str, blocks_release:bool) -> dict[str,Any]:
    row={"contract_version":CONTRACT_VERSION,"risk_id":risk_id,"sequence":sequence,"severity":severity,"state":state,"owner":owner,"evidence_digest":evidence_digest,"blocks_release":blocks_release,"content_free":True,"risk_closed":False,"release_waived":False}
    row["risk_digest"]=_digest(row); return row

def assess_final_candidate(plan:Mapping[str,Any], manifest:Sequence[Mapping[str,Any]], verification:Sequence[Mapping[str,Any]], risks:Sequence[Mapping[str,Any]], *, current_snapshot_digest:str,current_context_digest:str) -> dict[str,Any]:
    p=dict(plan); m=[dict(x) for x in manifest]; v=[dict(x) for x in verification]; r=[dict(x) for x in risks]; errors=[]
    errors += [f"private_field:{x}" for x in _private({"plan":p,"manifest":m,"verification":v,"risks":r})]
    u=dict(p); supplied=u.pop("plan_digest",None)
    if supplied!=_digest(u): errors.append("plan_tamper")
    if p.get("contract_version")!=CONTRACT_VERSION: errors.append("unsupported_contract")
    if p.get("snapshot_digest")!=current_snapshot_digest: errors.append("stale_snapshot")
    if p.get("context_digest")!=current_context_digest: errors.append("stale_context")
    for f in ("snapshot_digest","context_digest","source_manifest_digest","retained_verification_digest","unresolved_risk_digest","desktop_handoff_digest","native_provider_handoff_digest"):
        if not _is_digest(p.get(f)): errors.append(f"malformed_{f}")
    for f,limit in (("max_manifest_files",5000),("max_verification_rows",512),("max_risks",128)):
        x=p.get(f)
        if not isinstance(x,int) or isinstance(x,bool) or x<1 or x>limit: errors.append(f"malformed_{f}")
    if len(m)>int(p.get("max_manifest_files") or 0): errors.append("oversized_manifest")
    if len(v)>int(p.get("max_verification_rows") or 0): errors.append("oversized_verification")
    if len(r)>int(p.get("max_risks") or 0): errors.append("oversized_risks")
    forbidden=("candidate_prepared","release_approved","installation_performed","promotion_performed","certification_performed","publication_performed","release_performed","provider_contacted","model_contacted","process_started","thread_started","source_modified","runtime_mutated","approval_created","approval_consumed","automatic_continuation","global_profile_pass_claimed")
    for f in forbidden:
        if p.get(f) is not False: errors.append(f"forbidden_claim:{f}")
    if p.get("content_free") is not True or p.get("read_only") is not True or p.get("source_only") is not True: errors.append("boundary_loss")
    if p.get("authority_state")!="separate_not_granted": errors.append("authority_expansion")
    def check_rows(rows,digest_field,id_field):
        ids=[]; seq=[]
        for i,row in enumerate(rows):
            u=dict(row); s=u.pop(digest_field,None)
            if s!=_digest(u): errors.append(f"{id_field}_tamper:{i}")
            ids.append(row.get(id_field)); seq.append(row.get("sequence"))
        if len(ids)!=len(set(ids)): errors.append(f"duplicate_{id_field}")
        if seq!=list(range(1,len(rows)+1)): errors.append(f"invalid_{id_field}_sequence")
    check_rows(m,"entry_digest","path_id"); check_rows(v,"row_digest","verifier_id"); check_rows(r,"risk_digest","risk_id")
    for i,row in enumerate(m):
        if not _is_digest(row.get("file_digest")): errors.append(f"malformed_file_digest:{i}")
        if row.get("private_content_present") is not False or row.get("runtime_artifact") is not False or row.get("compiled_artifact") is not False or row.get("settings_artifact") is not False: errors.append(f"manifest_boundary_violation:{i}")
    for i,row in enumerate(v):
        if row.get("classification") not in ("current_regression","retained_checkpoint","inherited_debt"): errors.append(f"bad_classification:{i}")
        if row.get("status") not in ("passed","blocked_inherited","not_run"): errors.append(f"bad_status:{i}")
        if row.get("executed_by_contract") is not False or row.get("global_pass_inferred") is not False: errors.append(f"verification_authority:{i}")
    for i,row in enumerate(r):
        if row.get("severity") not in RISK_SEVERITIES or row.get("state") not in RISK_STATES or not row.get("owner"): errors.append(f"bad_risk:{i}")
        if row.get("risk_closed") is not False or row.get("release_waived") is not False: errors.append(f"risk_truth_loss:{i}")
    summary={"manifest_count":len(m),"verification_count":len(v),"risk_count":len(r),"blocking_risk_count":sum(1 for x in r if x.get("blocks_release") is True),"content_free":True,"source_only":True,"read_only":True,"candidate_prepared":False,"release_approved":False,"global_profile_pass_claimed":False,"source_modified":False,"runtime_mutated":False,"authority_state":"separate_not_granted"}
    return {"ok":not errors,"status":"ready_for_operator_review" if not errors else "blocked","errors":sorted(set(errors)),"summary":summary,"assessment_digest":_digest({"plan_digest":p.get("plan_digest"),"manifest":[x.get("entry_digest") for x in m],"verification":[x.get("row_digest") for x in v],"risks":[x.get("risk_digest") for x in r],"errors":sorted(set(errors))})}
