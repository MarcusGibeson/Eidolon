from __future__ import annotations
"""Read-only v1199.2 final source-only candidate preparation checkpoint."""
import hashlib
from pathlib import Path
from final_source_candidate_preparation import *
from final_source_candidate_preparation import _digest
from checkpoint_registry import inspect_checkpoint_registry

CONTRACT_VERSION = "v1199.2"
CHECKPOINT_ID="final-source-candidate-preparation-checkpoint"

def _h(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()

def build_final_source_candidate_preparation_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None):
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1])
    snap=_h("v1199.2-snapshot"); ctx=_h("v1199.2-context")
    plan=create_candidate_plan(candidate_id="eidolon-v1199-final-candidate-preparation",snapshot_digest=snap,context_digest=ctx,source_version="v1198.9",source_manifest_digest=_h("manifest"),retained_verification_digest=_h("verification"),unresolved_risk_digest=_h("risks"),desktop_handoff_digest=_h("desktop"),native_provider_handoff_digest=_h("native"),purpose_code="final_source_only_candidate_preparation")
    manifest=[create_manifest_entry(path_id=f"source:{i}",sequence=i,file_digest=_h(f"file:{i}"),size_bytes=100+i) for i in range(1,9)]
    verification=[create_verification_row(verifier_id=f"verify:{i}",sequence=i,classification=("current_regression" if i<4 else "retained_checkpoint"),status="passed",passed=10+i,total=10+i,evidence_digest=_h(f"verify:{i}")) for i in range(1,7)]
    risks=[create_risk(risk_id="risk:profile-budget",sequence=1,severity="medium",state="deferred",owner="verification",evidence_digest=_h("risk:1"),blocks_release=True),create_risk(risk_id="risk:fixture-overlap",sequence=2,severity="medium",state="deferred",owner="architecture",evidence_digest=_h("risk:2"),blocks_release=True)]
    result=assess_final_candidate(plan,manifest,verification,risks,current_snapshot_digest=snap,current_context_digest=ctx)
    checks=[]
    def req(x): checks.append(bool(x))
    req(result["ok"]); req(result["status"]=="ready_for_operator_review")
    s=result["summary"]
    for k,v in (("manifest_count",8),("verification_count",6),("risk_count",2),("blocking_risk_count",2)): req(s[k]==v)
    for f in ("content_free","source_only","read_only"): req(s[f] is True)
    for f in ("candidate_prepared","release_approved","global_profile_pass_claimed","source_modified","runtime_mutated"): req(s[f] is False)
    req(s["authority_state"]=="separate_not_granted")
    # adversarial mutations
    import copy
    mutations=[]
    p=copy.deepcopy(plan);p["release_performed"]=True;p["plan_digest"]=_digest({k:v for k,v in p.items() if k!="plan_digest"});mutations.append((p,manifest,verification,risks,"release"))
    p=copy.deepcopy(plan);p["authority_state"]="granted";p["plan_digest"]=_digest({k:v for k,v in p.items() if k!="plan_digest"});mutations.append((p,manifest,verification,risks,"authority"))
    mm=copy.deepcopy(manifest);mm[0]["private_content_present"]=True;mm[0]["entry_digest"]=_digest({k:v for k,v in mm[0].items() if k!="entry_digest"});mutations.append((plan,mm,verification,risks,"private"))
    vv=copy.deepcopy(verification);vv[0]["executed_by_contract"]=True;vv[0]["row_digest"]=_digest({k:v for k,v in vv[0].items() if k!="row_digest"});mutations.append((plan,manifest,vv,risks,"execute"))
    rr=copy.deepcopy(risks);rr[0]["risk_closed"]=True;rr[0]["risk_digest"]=_digest({k:v for k,v in rr[0].items() if k!="risk_digest"});mutations.append((plan,manifest,verification,rr,"risk"))
    blocked={}
    for pp,mm,vv,rr,name in mutations:
        out=assess_final_candidate(pp,mm,vv,rr,current_snapshot_digest=snap,current_context_digest=ctx);req(not out["ok"]);req(bool(out["errors"]));blocked[name]=out["errors"]
    registry=inspect_checkpoint_registry(source_root=source); desc=next((x for x in registry["checkpoints"] if x["checkpoint_id"]==CHECKPOINT_ID),None)
    req(bool(desc)); req((desc or {}).get("contract_version")==CONTRACT_VERSION); req((desc or {}).get("builder")=="build_final_source_candidate_preparation_checkpoint"); req((desc or {}).get("read_only") is True); req((desc or {}).get("post_available") is False)
    return {"ok":all(checks),"checkpoint_id":"final-source-candidate-preparation:v1199.2","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"source_only":True,"source_unchanged":True,"runtime_mutated":False,"candidate_prepared":False,"release_approved":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"publication_performed":False,"release_performed":False,"global_profile_pass_claimed":False,"authority_granted":False,"summary":s,"blocked_cases":blocked,"limitations":["Preparation evidence is content-free and read-only.","No final candidate is promoted, certified, published, released, or installed.","Desktop Codex and native-provider review remain future operator gates.","Inherited verifier debt remains explicit and unresolved."]}

CHECKPOINT_DESCRIPTOR={"checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"module":"conscious_agent.final_source_candidate_preparation_checkpoint","builder":"build_final_source_candidate_preparation_checkpoint","required_inputs":[],"read_only":True,"post_available":False,"content_free":True}
