from __future__ import annotations
import json, sys, tempfile, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import build_action_proposal_handoff
from persisted_action_proposals import persist_action_proposal, request_action_proposal_approval
from action_proposal_approval_decisions import decide_action_proposal
from action_execution_admission import authorize_action_proposal_execution
from authoritative_action_results import execute_admitted_action, inspect_authoritative_action_results, MAX_TERMINAL_RESULT_BYTES
checks=[]
def req(v): checks.append(bool(v)); assert v

def admitted(path, op='diag-result-op', start=100):
 p=build_natural_language_action_projection('Run diagnostics')
 h=build_action_proposal_handoff(p,operation_id='diag-result-candidate')
 pd=h['proposal']['proposal_digest']
 s=persist_action_proposal(path,h,expected_proposal_digest=pd,now=start)
 r=request_action_proposal_approval(path,proposal_id=s['proposal_id'],proposal_digest=pd,explicit_control_text='Request approval for diagnostics',now=start+1)
 d=decide_action_proposal(path,proposal_id=s['proposal_id'],proposal_digest=pd,approval_request_digest=r['approval_request_digest'],explicit_operator_text=f'Approve proposal {s["proposal_id"]}',operator_authority='operator',now=start+2)
 a=authorize_action_proposal_execution(path,proposal_id=s['proposal_id'],proposal_digest=pd,approval_decision_digest=d['approval_decision_digest'],explicit_operator_text=f'Authorize execution for proposal {s["proposal_id"]}',operator_authority='operator',operation_id=op,now=start+3)
 return s,pd,d,a

with tempfile.TemporaryDirectory() as td:
 path=Path(td)/'ledger.json'; s,pd,d,a=admitted(path)
 calls=[]
 result=execute_admitted_action(path,proposal_id=s['proposal_id'],proposal_digest=pd,authorization_digest=a['authorization_digest'],execution_admission_digest=a['execution_admission_digest'],operation_digest=a['operation_digest'],admission_receipt_digest=a['receipt_digest'],executor=lambda:(calls.append(1) or {'ok':True,'status':'completed','result_kind':'diagnostics','item_count':4}),now=104)
 req(result['ok'] and result['state']=='execution_succeeded' and result['terminal'])
 req(result['executed'] and result['executor_invoked'] and len(calls)==1)
 req(len(result['terminal_result_digest'])==64 and len(result['supervised_result_digest'])==64)
 req(not result['raw_output_included'] and not result['raw_arguments_included'])
 raw=path.read_text(); req('diag-result-op' not in raw and 'Run diagnostics' not in raw and 'completed' not in raw)
 req('execution_succeeded' in raw and len(raw.encode())<20000)
 replay=execute_admitted_action(path,proposal_id=s['proposal_id'],proposal_digest=pd,authorization_digest=a['authorization_digest'],execution_admission_digest=a['execution_admission_digest'],operation_digest=a['operation_digest'],admission_receipt_digest=a['receipt_digest'],executor=lambda:{'ok':True})
 req(not replay['ok'] and replay['state']=='replayed' and replay['terminal'])
 inspect=inspect_authoritative_action_results(path)
 req(inspect['terminal_result_count']==1 and inspect['state_counts']['execution_succeeded']==1)
 req(not inspect['raw_output_exposed'] and not inspect['conversation_can_execute'])
 # digest mismatch blocks before executor
 p2=Path(td)/'blocked.json'; s2,pd2,d2,a2=admitted(p2,op='blocked-op',start=200); called=[]
 blocked=execute_admitted_action(p2,proposal_id=s2['proposal_id'],proposal_digest=pd2,authorization_digest='0'*64,execution_admission_digest=a2['execution_admission_digest'],operation_digest=a2['operation_digest'],admission_receipt_digest=a2['receipt_digest'],executor=lambda:(called.append(1) or {'ok':True}))
 req(not blocked['ok'] and blocked['state']=='blocked' and not called)
 # reported failure
 p3=Path(td)/'failure.json'; s3,pd3,d3,a3=admitted(p3,op='fail-op',start=300)
 fail=execute_admitted_action(p3,proposal_id=s3['proposal_id'],proposal_digest=pd3,authorization_digest=a3['authorization_digest'],execution_admission_digest=a3['execution_admission_digest'],operation_digest=a3['operation_digest'],admission_receipt_digest=a3['receipt_digest'],executor=lambda:{'ok':False,'status':'failed','result_kind':'diagnostics','item_count':1})
 req(not fail['ok'] and fail['state']=='execution_failed' and fail['executed'])
 # malformed
 p4=Path(td)/'malformed.json'; s4,pd4,d4,a4=admitted(p4,op='malformed-op',start=400)
 malformed=execute_admitted_action(p4,proposal_id=s4['proposal_id'],proposal_digest=pd4,authorization_digest=a4['authorization_digest'],execution_admission_digest=a4['execution_admission_digest'],operation_digest=a4['operation_digest'],admission_receipt_digest=a4['receipt_digest'],executor=lambda:'raw secret')
 req(not malformed['ok'] and malformed['state']=='execution_failed')
 # cancellation before start
 p5=Path(td)/'cancel.json'; s5,pd5,d5,a5=admitted(p5,op='cancel-op',start=500); ev=threading.Event(); ev.set()
 cancelled=execute_admitted_action(p5,proposal_id=s5['proposal_id'],proposal_digest=pd5,authorization_digest=a5['authorization_digest'],execution_admission_digest=a5['execution_admission_digest'],operation_digest=a5['operation_digest'],admission_receipt_digest=a5['receipt_digest'],executor=lambda:{'ok':True},cancel_event=ev)
 req(cancelled['state']=='execution_cancelled' and not cancelled['executed'])
 req(MAX_TERMINAL_RESULT_BYTES<=4096)
print(json.dumps({'ok':True,'suite':'v1178.0-v1178.2-authoritative-supervised-execution-results','passed':sum(checks),'total':len(checks)},sort_keys=True))
