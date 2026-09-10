from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import build_action_proposal_handoff
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval
from action_proposal_approval_decisions import decide_action_proposal
from action_execution_admission import authorize_action_proposal_execution
from authoritative_action_results import execute_admitted_action
from supervised_result_reliability import recover_stale_execution_attempt, inspect_result_reliability, MAX_RECOVERY_RECEIPT_BYTES
from supervised_result_presentation import build_supervised_result_presentation
checks=[]
def req(v): checks.append(bool(v)); assert v

def admitted(path,start=100):
 p=build_natural_language_action_projection('Run diagnostics')
 h=build_action_proposal_handoff(p,operation_id='reliability-candidate')
 pd=h['proposal']['proposal_digest']
 s=persist_action_proposal(path,h,expected_proposal_digest=pd,now=start)
 r=request_action_proposal_approval(path,proposal_id=s['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=start+1)
 d=decide_action_proposal(path,proposal_id=s['proposal_id'],proposal_digest=pd,approval_request_digest=r['approval_request_digest'],explicit_operator_text=f'Approve proposal {s["proposal_id"]}',operator_authority='operator',now=start+2)
 a=authorize_action_proposal_execution(path,proposal_id=s['proposal_id'],proposal_digest=pd,approval_decision_digest=d['approval_decision_digest'],explicit_operator_text=f'Authorize execution for proposal {s["proposal_id"]}',operator_authority='operator',operation_id='reliability-operation',now=start+3)
 return s,pd,a

with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'ledger.json'; s,pd,a=admitted(path)
 result=execute_admitted_action(path,proposal_id=s['proposal_id'],proposal_digest=pd,authorization_digest=a['authorization_digest'],execution_admission_digest=a['execution_admission_digest'],operation_digest=a['operation_digest'],admission_receipt_digest=a['receipt_digest'],executor=lambda:{'ok':True,'status':'completed','result_kind':'diagnostics'},now=104)
 req(result['state']=='execution_succeeded' and len(result['execution_attempt_digest'])==64)
 state=json.loads(path.read_text()); row=state['records'][-1]
 req(row['execution_in_progress'] is False and len(row['execution_attempt_digest'])==64)
 req(row['execution_terminal'] is True and row['execution_result_digest']==result['terminal_result_digest'])
 # identical duplicate receipts deduplicate rather than becoming ambiguous
 presentation=build_supervised_result_presentation('diagnostics',[result,dict(result)])
 req(presentation['authoritative_receipt_present'] and presentation['receipt_count']==1)
 # conflicting terminal receipts remain ambiguous
 conflict=dict(result,terminal_result_digest='f'*64)
 req(build_supervised_result_presentation('diagnostics',[result,conflict])['presentation_status']=='ambiguous')
 # synthesize a crashed in-progress attempt and recover it without executor
 p2=Path(td)/'stale.json'; s2,pd2,a2=admitted(p2,start=200)
 state=json.loads(p2.read_text()); row=state['records'][-1]
 row.update(state='execution_in_progress',execution_in_progress=True,execution_started_at=204.0,execution_attempt_digest='e'*64)
 p2.write_text(json.dumps(state,sort_keys=True,separators=(',',':')))
 inspect=inspect_result_reliability(p2,now=600)
 req(inspect['in_progress']==1 and inspect['stale_in_progress']==1 and not inspect['executor_invoked'])
 recovered=recover_stale_execution_attempt(p2,proposal_id=s2['proposal_id'],attempt_digest='e'*64,now=600,stale_after_seconds=300)
 req(recovered['ok'] and recovered['state']=='execution_failed' and recovered['recovered'])
 req(not recovered['executor_invoked'] and not recovered['execution_performed'])
 req(recovered['error_kind']=='interrupted_before_terminal_result' and recovered['terminal'])
 req(len(recovered['terminal_result_digest'])==64 and len(recovered['supervised_result_digest'])==64 and len(recovered['outcome_digest'])==64)
 req('reliability-operation' not in p2.read_text() and len(json.dumps(recovered).encode())<=MAX_RECOVERY_RECEIPT_BYTES)
 # replay and wrong digest fail closed
 replay=recover_stale_execution_attempt(p2,proposal_id=s2['proposal_id'],attempt_digest='e'*64,now=700)
 req(not replay['ok'] and replay['state']=='terminal')
 p3=Path(td)/'fresh.json'; s3,pd3,a3=admitted(p3,start=300)
 state=json.loads(p3.read_text()); row=state['records'][-1]
 row.update(state='execution_in_progress',execution_in_progress=True,execution_started_at=400.0,execution_attempt_digest='a'*64)
 p3.write_text(json.dumps(state,sort_keys=True,separators=(',',':')))
 req(recover_stale_execution_attempt(p3,proposal_id=s3['proposal_id'],attempt_digest='b'*64,now=800)['state']=='blocked')
 req(recover_stale_execution_attempt(p3,proposal_id=s3['proposal_id'],attempt_digest='a'*64,now=500,stale_after_seconds=300)['state']=='not_stale')
 req(inspect_result_reliability(Path(td)/'malformed.json')['record_count']==0)
 req(MAX_RECOVERY_RECEIPT_BYTES<=4096)
print(json.dumps({'ok':True,'suite':'v1178.6-v1178.8-supervised-result-reliability-recovery','passed':sum(checks),'total':len(checks)},sort_keys=True))
