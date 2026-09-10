from __future__ import annotations
import json, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from structured_action_clarification import build_structured_clarification_request, apply_structured_clarification_answer, build_clarified_proposal_binding
from action_proposal_handoff import build_action_proposal_handoff
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval, inspect_persisted_action_proposals
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 pth=Path(td)/'action_proposals.json'
 direct=build_natural_language_action_projection('Run diagnostics')
 hand=build_action_proposal_handoff(direct,operation_id='diag-1')
 pd=hand['proposal']['proposal_digest']
 saved=persist_action_proposal(pth,hand,expected_proposal_digest=pd,now=100)
 req(saved['ok'] and saved['state']=='proposed' and saved['persisted'])
 raw=pth.read_text()
 req('Run diagnostics' not in raw and '\"argument_values\":' not in raw)
 req('approval_created":true' not in raw and 'authorization_granted":true' not in raw)
 dup=persist_action_proposal(pth,hand,expected_proposal_digest=pd,now=101)
 req(dup['state']=='duplicate' and not dup['persisted'])
 wrong=persist_action_proposal(pth,hand,expected_proposal_digest='0'*64,now=102)
 req(not wrong['ok'] and wrong['state']=='rejected')
 vague=request_action_proposal_approval(pth,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='go ahead',now=103)
 req(not vague['ok'] and not vague['approval_requested'])
 mismatch=request_action_proposal_approval(pth,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='request approval for maintenance',now=104)
 req(not mismatch['ok'])
 approval=request_action_proposal_approval(pth,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics.',now=105)
 req(approval['ok'] and approval['state']=='awaiting_approval' and approval['approval_requested'])
 req(not approval['approval_created'] and not approval['approval_granted'] and not approval['authorization_granted'] and not approval['execution_performed'])
 replay=request_action_proposal_approval(pth,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=106)
 req(not replay['ok'] and replay['state']=='replayed')
 ins=inspect_persisted_action_proposals(pth,now=107)
 req(ins['record_count']==1 and ins['awaiting_approval_count']==1)
 req(not ins['raw_content_exposed'] and not ins['argument_values_exposed'])
 # clarified proposal preserves names/digests, never values
 proj=build_natural_language_action_projection('Review a file')
 cr=build_structured_clarification_request(proj)
 ans=apply_structured_clarification_answer(proj,cr,{'target_ref':'conscious_agent/memory.py'})
 bound=build_clarified_proposal_binding(proj,ans,operation_id='review-1')
 bpd=bound['proposal_binding']['proposal_digest']
 bs=persist_action_proposal(pth,bound,expected_proposal_digest=bpd,now=200)
 req(bs['ok'] and bs['persisted'])
 raw2=pth.read_text()
 req('conscious_agent/memory.py' not in raw2)
 req('target_ref' in raw2)
 # malformed store recovers empty and remains bounded
 bad=Path(td)/'bad.json'; bad.write_text('{bad')
 req(inspect_persisted_action_proposals(bad)['record_count']==0)
 # expiry prevents approval request
 exp_path=Path(td)/'expire.json'; es=persist_action_proposal(exp_path,hand,expected_proposal_digest=pd,now=0)
 ex=request_action_proposal_approval(exp_path,proposal_id=es['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=700000)
 req(not ex['ok'] and ex['state']=='expired')
 # ordinary conversation never creates store
 q=build_natural_language_action_projection('Do you like the name Eidolon?')
 req(q['intent']['category']=='question' and not pth.with_name('ordinary.json').exists())
 c=build_natural_language_action_projection('Stop calling me Daddy.')
 req(c['intent']['category']=='correction')
 start=time.perf_counter()
 for i in range(100): inspect_persisted_action_proposals(pth,now=300+i)
 req(time.perf_counter()-start<1.0)
 req(len(raw2.encode())<16384)
print(json.dumps({'ok':True,'suite':'v1177.0-v1177.2-persisted-action-proposal-explicit-approval-request-foundations','passed':sum(checks),'total':len(checks)},sort_keys=True))
