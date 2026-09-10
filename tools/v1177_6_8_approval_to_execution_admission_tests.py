from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import build_action_proposal_handoff
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval, inspect_persisted_action_proposals
from action_proposal_approval_decisions import decide_action_proposal
from action_execution_admission import authorize_action_proposal_execution
checks=[]
def req(v): checks.append(bool(v)); assert v
with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'ledger.json'
 proj=build_natural_language_action_projection('Run diagnostics')
 hand=build_action_proposal_handoff(proj,operation_id='diag-c')
 pd=hand['proposal']['proposal_digest']
 saved=persist_action_proposal(path,hand,expected_proposal_digest=pd,now=100)
 requested=request_action_proposal_approval(path,proposal_id=saved['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=101)
 approved=decide_action_proposal(path,proposal_id=saved['proposal_id'],proposal_digest=pd,approval_request_digest=requested['approval_request_digest'],explicit_operator_text=f'Approve proposal {saved["proposal_id"]}',operator_authority='operator',now=102)
 pid=saved['proposal_id']; add=approved['approval_decision_digest']
 req(approved['approval_granted'] and not approved['execution_admitted'])
 vague=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest=add,explicit_operator_text='go ahead',operator_authority='operator',operation_id='diag-op-1',now=103)
 req(not vague['ok'] and not vague['authorization_granted'])
 wrong_actor=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest=add,explicit_operator_text=f'Authorize execution for proposal {pid}',operator_authority='assistant',operation_id='diag-op-1',now=104)
 req(not wrong_actor['ok'])
 wrong_decision=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest='0'*64,explicit_operator_text=f'Authorize execution for proposal {pid}',operator_authority='operator',operation_id='diag-op-1',now=105)
 req(not wrong_decision['ok'])
 missing_operation=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest=add,explicit_operator_text=f'Authorize execution for proposal {pid}',operator_authority='operator',operation_id='',now=106)
 req(not missing_operation['ok'] and 'operation_identity_required' in missing_operation.get('reason_codes',[]))
 admitted=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest=add,explicit_operator_text=f'Authorize execution for proposal {pid}.',operator_authority='operator',operation_id='diag-op-1',now=107)
 req(admitted['ok'] and admitted['state']=='execution_admitted')
 req(admitted['authorization_granted'] and admitted['execution_admitted'])
 req(not admitted['execution_performed'] and not admitted['executor_invoked'])
 req(not admitted['conversation_can_authorize'] and not admitted['conversation_can_execute'])
 req(len(admitted['operation_digest'])==64 and len(admitted['authorization_digest'])==64 and len(admitted['execution_admission_digest'])==64)
 raw=path.read_text()
 req('diag-op-1' not in raw and 'Run diagnostics' not in raw and 'go ahead' not in raw)
 req('"state":"execution_admitted"' in raw and '"execution_performed":false' in raw)
 replay=authorize_action_proposal_execution(path,proposal_id=pid,proposal_digest=pd,approval_decision_digest=add,explicit_operator_text=f'Authorize execution for proposal {pid}',operator_authority='operator',operation_id='diag-op-1',now=108)
 req(not replay['ok'] and replay['state']=='replayed')
 # rejected proposals cannot be admitted
 path2=Path(td)/'rejected.json'; s2=persist_action_proposal(path2,hand,expected_proposal_digest=pd,now=200)
 r2=request_action_proposal_approval(path2,proposal_id=s2['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=201)
 d2=decide_action_proposal(path2,proposal_id=s2['proposal_id'],proposal_digest=pd,approval_request_digest=r2['approval_request_digest'],explicit_operator_text=f'Reject proposal {s2["proposal_id"]}',operator_authority='operator',now=202)
 blocked=authorize_action_proposal_execution(path2,proposal_id=s2['proposal_id'],proposal_digest=pd,approval_decision_digest=d2['approval_decision_digest'],explicit_operator_text=f'Authorize execution for proposal {s2["proposal_id"]}',operator_authority='operator',operation_id='diag-op-2',now=203)
 req(not blocked['ok'] and blocked['state']=='rejected')
 # non-execution-eligible registered capability remains blocked
 patch_proj=build_natural_language_action_projection('Change the dashboard background')
 patch_hand=build_action_proposal_handoff(patch_proj,operation_id='patch-c')
 ppd=patch_hand['proposal']['proposal_digest']; path3=Path(td)/'patch.json'
 ps=persist_action_proposal(path3,patch_hand,expected_proposal_digest=ppd,now=300)
 pr=request_action_proposal_approval(path3,proposal_id=ps['proposal_id'],proposal_digest=ppd,explicit_control_text='Request approval for patch_proposal',now=301)
 pa=decide_action_proposal(path3,proposal_id=ps['proposal_id'],proposal_digest=ppd,approval_request_digest=pr['approval_request_digest'],explicit_operator_text=f'Approve proposal {ps["proposal_id"]}',operator_authority='operator',now=302)
 pb=authorize_action_proposal_execution(path3,proposal_id=ps['proposal_id'],proposal_digest=ppd,approval_decision_digest=pa['approval_decision_digest'],explicit_operator_text=f'Authorize execution for proposal {ps["proposal_id"]}',operator_authority='operator',operation_id='patch-op',now=303)
 req(not pb['ok'] and 'capability_not_execution_eligible' in pb.get('reason_codes',[]))
 ins=inspect_persisted_action_proposals(path,now=400)
 req(ins['record_count']==1 and ins['state_counts'].get('execution_admitted')==1)
 req(not ins['raw_content_exposed'] and not ins['argument_values_exposed'])
 req(len(raw.encode())<16384)
print(json.dumps({'ok':True,'suite':'v1177.6-v1177.8-approval-to-execution-admission-integration','passed':sum(checks),'total':len(checks)},sort_keys=True))
