from __future__ import annotations
import json, os, sys, tempfile, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
    if not c: raise AssertionError(m)
def check(n,f):
    try: f(); RESULTS.append({'name':n,'ok':True})
    except Exception as e: RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def wait_state(op, expected, timeout=15):
    from process_ownership import inspect_process_operation
    end=time.monotonic()+timeout; state=inspect_process_operation(op)
    while state.get('state') not in expected and time.monotonic()<end:
        time.sleep(.03); state=inspect_process_operation(op)
    return state

def main():
  with tempfile.TemporaryDirectory(prefix='eidolon-v1094-3-') as td:
    os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=str(Path(td)/'runtime'); os.environ['EIDOLON_METADATA_LOCK_DIR']=str(Path(td)/'locks')
    from process_ownership import accept_process_operation, activate_process_operation, inspect_process_operation, request_process_operation_cancellation_exact, finalize_process_operation
    from process_worker_entrypoints import start_bounded_command_worker
    def accepted(**kw):
        return accept_process_operation(f'op_{uuid.uuid4().hex}', operation_kind='verification', may_mutate=False, acceptance_key=uuid.uuid4().hex, project_id='eidolon', session_id='session-a', tab_id='tab-a', tab_revision=7, **kw)
    def literal_confirmation():
        a=accepted(); denied=request_process_operation_cancellation_exact(a['operation_id'],generation=1,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,operator_confirmed='true')
        require(denied['status']=='confirmation_required','truthy string accepted')
    def stale_generation():
        a=accepted(); active=activate_process_operation(a['operation_id'],1); require(active['status']=='starting','starting state missing')
        r=request_process_operation_cancellation_exact(a['operation_id'],generation=2,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,operator_confirmed=True)
        require(r['status']=='generation_mismatch' and r['stale_request'],'stale generation accepted')
        finalize_process_operation(a['operation_id'],1,active['owner_nonce'],state='interrupted')
    def context_binding():
        for field,value,status in [('project_id','other','project_id_mismatch'),('session_id','other','session_id_mismatch'),('tab_id','other','tab_id_mismatch'),('tab_revision',8,'tab_revision_mismatch')]:
            a=accepted(); active=activate_process_operation(a['operation_id'],1)
            args=dict(generation=1,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,operator_confirmed=True); args[field]=value
            r=request_process_operation_cancellation_exact(a['operation_id'],**args); require(r['status']==status,f'{field} mismatch accepted: {r}')
            finalize_process_operation(a['operation_id'],1,active['owner_nonce'],state='interrupted')
    def cooperative_real_worker():
        op=f'worker_{uuid.uuid4().hex}'
        launched=start_bounded_command_worker(operation_id=op,acceptance_key='accept',operation_kind='verification',may_mutate=False,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,config={'command':[sys.executable,'-c','import time; time.sleep(30)'],'cwd':str(ROOT),'environment':{},'timeout_seconds':60})
        require(launched['worker_started'],'worker did not start')
        state=wait_state(op,{'running','starting'}); require(state['state'] in {'running','starting'},f'not active {state}')
        r=request_process_operation_cancellation_exact(op,generation=1,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,operator_confirmed=True)
        require(r['status']=='cancellation_requested' and r['cooperative_first'],'cancellation not requested')
        launched['worker_handle'].join(15); require(not launched['worker_handle'].is_alive(),'worker did not cancel')
        require(wait_state(op,{'cancelled'}).get('state')=='cancelled','worker not cancelled')
    def terminal_rejected():
        a=accepted(); active=activate_process_operation(a['operation_id'],1); finalize_process_operation(a['operation_id'],1,active['owner_nonce'],state='completed')
        r=request_process_operation_cancellation_exact(a['operation_id'],generation=1,project_id='eidolon',session_id='session-a',tab_id='tab-a',tab_revision=7,operator_confirmed=True)
        require(r['status']=='already_terminal','terminal cancellation accepted')
    def private_binding():
        a=accepted(); public=inspect_process_operation(a['operation_id']); encoded=json.dumps(public)
        require('session-a' not in encoded and 'tab-a' not in encoded and 'owner_nonce' not in encoded,'private binding leaked')
    def route_contract():
        source=(AGENT/'dashboard.py').read_text(); require('/api/process-operation/cancel' in source and 'request_process_operation_cancellation_exact' in source,'exact cancellation route missing')
    def state_contract():
        source=(AGENT/'process_ownership.py').read_text(); require('"starting"' in source and 'cancellation_child_identity_digest' in source,'lifecycle states missing')
    for n,f in [('literal cancellation confirmation',literal_confirmation),('stale generation rejected',stale_generation),('project session tab binding',context_binding),('cooperative real worker cancellation',cooperative_real_worker),('terminal cancellation rejected',terminal_rejected),('private bindings remain private',private_binding),('dashboard cancellation route',route_contract),('bounded lifecycle states',state_contract)]: check(n,f)
  passed=sum(1 for r in RESULTS if r['ok']); report={'version':'1094.3','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS}; print(json.dumps(report,indent=2,sort_keys=True)); return 0 if passed==len(RESULTS) else 1
if __name__=='__main__': raise SystemExit(main())
