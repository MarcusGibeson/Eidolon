from __future__ import annotations
import json, sys, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import build_action_proposal_handoff
from supervised_action_execution import build_supervised_execution_projection, execute_supervised_action, MAX_RESULT_BYTES

checks=[]
def req(name, cond, detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: raise AssertionError(f'{name}: {detail}')

def handoff(text): return build_action_proposal_handoff(build_natural_language_action_projection(text),operation_id='proposal-op')
def approval(h):
    p=h['proposal']
    return {'authoritative':True,'status':'approved','authority':'operator','capability_id':p['capability_id'],'proposal_digest':p['proposal_digest'],'approval_digest':'a'*64,'revoked':False,'expired':False}

h=handoff('Run diagnostics.')
p=build_supervised_execution_projection(h,approval_receipt=approval(h),operation_id='exec-1')
req('diagnostics eligible',p['execution_eligible'],p)
req('exact approval verified',p['approval_verified'],p)
req('admitted',p['admitted'],p)
req('conversation cannot execute',not p['conversation_can_execute'],p)

for text in ['Change the dashboard background.','Review conscious_agent/memory.py.','Install a new model.']:
    x=handoff(text); q=build_supervised_execution_projection(x,approval_receipt=approval(x),operation_id='x')
    req(text+' blocked',not q['admitted'],q)

bad=dict(approval(h)); bad['proposal_digest']='b'*64
req('digest mismatch blocked',not build_supervised_execution_projection(h,approval_receipt=bad,operation_id='x')['admitted'])
bad=dict(approval(h)); bad['authority']='model'
req('model authority blocked',not build_supervised_execution_projection(h,approval_receipt=bad,operation_id='x')['admitted'])
bad=dict(approval(h)); bad['revoked']=True
req('revoked blocked',not build_supervised_execution_projection(h,approval_receipt=bad,operation_id='x')['admitted'])
req('missing op blocked',not build_supervised_execution_projection(h,approval_receipt=approval(h))['admitted'])
prior=[{'operation_digest':p['operation_digest'],'terminal':True}]
req('replay blocked',not build_supervised_execution_projection(h,approval_receipt=approval(h),prior_result_receipts=prior,operation_id='exec-1')['admitted'])

r=execute_supervised_action(p,executor=lambda:{'ok':True,'status':'completed','result_kind':'diagnostics','item_count':3,'secret':'never expose'})
req('success authoritative result',r['state']=='succeeded' and r['ok'],r)
req('result content free',r['content_free'] and not r['raw_output_included'],r)
req('secret absent','secret' not in json.dumps(r),r)
req('bounded result',len(json.dumps(r,separators=(',',':')).encode())<=MAX_RESULT_BYTES,len(json.dumps(r)))

r=execute_supervised_action(p,executor=lambda:{'ok':False,'status':'failed','item_count':1})
req('reported failure',r['state']=='failed' and not r['ok'],r)
r=execute_supervised_action(p,executor=lambda:'bad')
req('malformed result',r['error_kind']=='malformed_executor_result',r)
r=execute_supervised_action(p,executor=lambda:(_ for _ in ()).throw(RuntimeError('private secret')))
req('exception redacted',r['error_kind']=='executor_exception' and 'secret' not in json.dumps(r),r)
r=execute_supervised_action(p,executor=lambda:(time.sleep(.08) or {'ok':True}),timeout_seconds=.01)
req('timeout bounded',r['state']=='timed_out',r)
e=threading.Event(); e.set(); r=execute_supervised_action(p,executor=lambda:{'ok':True},cancel_event=e)
req('cancel before start',r['state']=='cancelled' and not r['executed'],r)

runtime=(ROOT/'conscious_agent'/'conversation_runtime.py').read_text()
req('stream projection parity',runtime.count('build_supervised_execution_projection(action_handoff, operation_id=operation_id)')==2)
req('stream public parity',runtime.count('supervised_execution_public(execution_projection)')==2)
req('stream prompt parity',runtime.count('supervised_execution_prompt(execution_projection)')==2)
req('conversation never calls executor','execute_supervised_action(' not in runtime)

rows=[]
for i in range(200):
    t=time.perf_counter(); build_supervised_execution_projection(h,operation_id=str(i)); rows.append((time.perf_counter()-t)*1000)
req('p95 under 10ms',sorted(rows)[189]<10,sorted(rows)[189])
print(json.dumps({'ok':all(x[1] for x in checks),'suite':'v1175.6-v1175.8-supervised-action-execution-results-reliability','passed':sum(x[1] for x in checks),'total':len(checks),'p95_ms':round(sorted(rows)[189],4),'conversation_execution':False,'automatic_approval':False},sort_keys=True))
