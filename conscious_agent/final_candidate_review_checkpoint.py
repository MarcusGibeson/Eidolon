from __future__ import annotations
"""Read-only v1199.5 operator final-candidate review checkpoint."""
import hashlib, copy
from pathlib import Path
from final_candidate_review import *
from final_candidate_review import _digest
from checkpoint_registry import inspect_checkpoint_registry

CONTRACT_VERSION="v1199.5"; CHECKPOINT_ID="final-candidate-review-checkpoint"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def build_final_candidate_review_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None):
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1])
    snap=_h('v1199.5-snapshot');ctx=_h('v1199.5-context')
    fixed={"candidate_plan_digest":_h('plan'),"candidate_assessment_digest":_h('assessment'),"source_manifest_digest":_h('manifest'),"retained_verification_digest":_h('verification'),"unresolved_risk_digest":_h('risks'),"desktop_handoff_digest":_h('desktop'),"native_provider_handoff_digest":_h('native')}
    action_purpose=dict(zip(REVIEW_ACTIONS,PURPOSE_CODES)); rows=[]; prior=None; seq=1
    for action in REVIEW_ACTIONS:
        for decision in DECISIONS:
            req=create_review_request(review_id=f'review:{seq}',candidate_id='eidolon-v1199-final-source-candidate',action=action,decision=decision,sequence=seq,prior_review_receipt_digest=prior,snapshot_digest=snap,context_digest=ctx,operator_review_digest=_h(f'operator:{seq}'),purpose_code=action_purpose[action],**fixed)
            out=review_final_candidate(req,current_snapshot_digest=snap,current_context_digest=ctx,expected_sequence=seq,expected_prior_review_receipt_digest=prior,**{f'expected_{k}':v for k,v in fixed.items()})
            rows.append(out); prior=out['review_receipt_digest'];seq+=1
    checks=[]
    def req(x):checks.append(bool(x))
    req(len(rows)==15); req(all(x['ok'] for x in rows)); req(sum(x['summary']['decision']=='approve' for x in rows)==5);req(sum(x['summary']['decision']=='reject' for x in rows)==5);req(sum(x['summary']['decision']=='defer' for x in rows)==5)
    for row in rows:
        req(row['summary']['presentation_only'] is True)
        for f in ('candidate_accepted','handoff_accepted','risk_waived','release_approved','source_modified','runtime_mutated','global_profile_pass_claimed'):req(row['summary'][f] is False)
        req(row['summary']['authority_state']=='separate_not_granted')
    base=create_review_request(review_id='attack',candidate_id='eidolon-v1199-final-source-candidate',action='candidate_acceptance',decision='approve',sequence=1,prior_review_receipt_digest=None,snapshot_digest=snap,context_digest=ctx,operator_review_digest=_h('operator'),purpose_code='review_final_source_candidate',**fixed)
    blocked={}
    muts=[]
    for field,value,name in [('release_performed',True,'release'),('candidate_accepted',True,'accept'),('risk_waived',True,'waive'),('authority_state','granted','authority'),('runtime_mutated',True,'mutation'),('global_profile_pass_claimed',True,'global')]:
        m=copy.deepcopy(base);m[field]=value;m['request_digest']=_digest({k:v for k,v in m.items() if k!='request_digest'});muts.append((name,m))
    m=copy.deepcopy(base);m['prompt']='private';m['request_digest']=_digest({k:v for k,v in m.items() if k!='request_digest'});muts.append(('private',m))
    m=copy.deepcopy(base);m['snapshot_digest']=_h('stale');m['request_digest']=_digest({k:v for k,v in m.items() if k!='request_digest'});muts.append(('stale',m))
    for name,m in muts:
        out=review_final_candidate(m,current_snapshot_digest=snap,current_context_digest=ctx,expected_sequence=1,expected_prior_review_receipt_digest=None,**{f'expected_{k}':v for k,v in fixed.items()});req(not out['ok']);req(bool(out['errors']));blocked[name]=out['errors']
    reg=inspect_checkpoint_registry(source_root=source); desc=next((x for x in reg['checkpoints'] if x['checkpoint_id']==CHECKPOINT_ID),None)
    req(bool(desc));req((desc or {}).get('contract_version')==CONTRACT_VERSION);req((desc or {}).get('read_only') is True);req((desc or {}).get('post_available') is False)
    summary={"review_count":15,"action_count":5,"decision_count":3,"approve_count":5,"reject_count":5,"defer_count":5,"content_free":True,"read_only":True,"source_only":True,"presentation_only":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"release_approved":False,"source_modified":False,"runtime_mutated":False,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}
    return {"ok":all(checks),"checkpoint_id":"final-candidate-review:v1199.5","contract_version":CONTRACT_VERSION,"passed":sum(checks),"total":len(checks),"read_only":True,"post_available":False,"content_free":True,"source_only":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"release_approved":False,"release_performed":False,"authority_granted":False,"summary":summary,"blocked_cases":blocked,"limitations":["Review outcomes are content-free and presentation-only.","Approve does not accept, promote, certify, publish, install, or release the candidate.","The v1200 Desktop Codex and native-provider decision gate remains required.","Unresolved risks remain explicit and unwaived."]}
CHECKPOINT_DESCRIPTOR={"checkpoint_id":CHECKPOINT_ID,"contract_version":CONTRACT_VERSION,"module":"conscious_agent.final_candidate_review_checkpoint","builder":"build_final_candidate_review_checkpoint","required_inputs":[],"read_only":True,"post_available":False,"content_free":True}
