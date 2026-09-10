from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import build_action_proposal_handoff
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval, inspect_persisted_action_proposals
from action_proposal_approval_decisions import decide_action_proposal
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'ledger.json'
 proj=build_natural_language_action_projection('Run diagnostics')
 hand=build_action_proposal_handoff(proj,operation_id='diag-b')
 pd=hand['proposal']['proposal_digest']
 saved=persist_action_proposal(path,hand,expected_proposal_digest=pd,now=100)
 requested=request_action_proposal_approval(path,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=101)
 ard=requested['approval_request_digest']; pid=saved['proposal_id']
 req(requested['state']=='awaiting_approval')
 vague=decide_action_proposal(path,proposal_id=pid,proposal_digest=pd,approval_request_digest=ard,explicit_operator_text='go ahead',operator_authority='operator',now=102)
 req(not vague['ok'] and not vague['approval_decided'])
 wrong_actor=decide_action_proposal(path,proposal_id=pid,proposal_digest=pd,approval_request_digest=ard,explicit_operator_text=f'Approve proposal {pid}',operator_authority='assistant',now=103)
 req(not wrong_actor['ok'])
 wrong_digest=decide_action_proposal(path,proposal_id=pid,proposal_digest='0'*64,approval_request_digest=ard,explicit_operator_text=f'Approve proposal {pid}',operator_authority='operator',now=104)
 req(not wrong_digest['ok'])
 approved=decide_action_proposal(path,proposal_id=pid,proposal_digest=pd,approval_request_digest=ard,explicit_operator_text=f'Approve proposal {pid}.',operator_authority='operator',now=105)
 req(approved['ok'] and approved['state']=='approved' and approved['approval_granted'])
 req(not approved['authorization_granted'] and not approved['execution_admitted'] and not approved['execution_performed'])
 raw=path.read_text()
 req('Run diagnostics' not in raw and 'go ahead' not in raw)
 req('"approval_decision":"approve"' in raw and '"approval_decision_digest"' in raw)
 replay=decide_action_proposal(path,proposal_id=pid,proposal_digest=pd,approval_request_digest=ard,explicit_operator_text=f'Approve proposal {pid}',operator_authority='operator',now=106)
 req(not replay['ok'] and replay['state']=='replayed')
 # rejection path
 path2=Path(td)/'reject.json'; s2=persist_action_proposal(path2,hand,expected_proposal_digest=pd,now=200)
 r2=request_action_proposal_approval(path2,proposal_id=s2['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=201)
 rejected=decide_action_proposal(path2,proposal_id=s2['proposal_id'],proposal_digest=pd,approval_request_digest=r2['approval_request_digest'],explicit_operator_text=f'Reject proposal {s2["proposal_id"]}',operator_authority='operator',now=202)
 req(rejected['ok'] and rejected['state']=='rejected' and not rejected['approval_granted'])
 req(not rejected['authorization_granted'] and not rejected['execution_performed'])
 # decision before approval request blocked
 path3=Path(td)/'early.json'; s3=persist_action_proposal(path3,hand,expected_proposal_digest=pd,now=300)
 early=decide_action_proposal(path3,proposal_id=s3['proposal_id'],proposal_digest=pd,approval_request_digest='1'*64,explicit_operator_text=f'Approve proposal {s3["proposal_id"]}',operator_authority='operator',now=301)
 req(not early['ok'] and early['state']=='proposed')
 ins=inspect_persisted_action_proposals(path,now=400)
 req(ins['record_count']==1 and ins['state_counts'].get('approved')==1)
 req(not ins['raw_content_exposed'] and not ins['argument_values_exposed'])
 req(len(raw.encode())<16384)
print(json.dumps({'ok':True,'suite':'v1177.3-v1177.5-approval-decision-proposal-lifecycle-integration','passed':sum(checks),'total':len(checks)},sort_keys=True))
