from __future__ import annotations
import json, multiprocessing as mp, os, sys, tempfile, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
    if not c: raise AssertionError(m)
def check(n,f):
    try:f();RESULTS.append({'name':n,'ok':True})
    except Exception as e:RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def _result_then_die(op,generation,runtime,locks):
    os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=runtime; os.environ['EIDOLON_METADATA_LOCK_DIR']=locks
    if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
    from process_ownership import activate_process_operation,write_process_result
    a=activate_process_operation(op,generation)
    if a.get('ok'): write_process_result(op,generation=generation,owner_nonce=a['owner_nonce'],state='completed')
    os._exit(0)
def main():
  with tempfile.TemporaryDirectory(prefix='eidolon-v1094-4-') as td:
    runtime=str(Path(td)/'runtime'); locks=str(Path(td)/'locks'); os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=runtime; os.environ['EIDOLON_METADATA_LOCK_DIR']=locks
    from process_worker_entrypoints import start_bounded_command_worker
    from process_ownership import accept_process_operation, request_process_operation_cancellation_exact, ownership_root
    from process_recovery import build_process_restart_state, inspect_process_operation_for_context
    def launch():
        op=f'live_{uuid.uuid4().hex}'; x=start_bounded_command_worker(operation_id=op,acceptance_key='a',operation_kind='verification',may_mutate=False,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4,config={'command':[sys.executable,'-c','import time;time.sleep(30)'],'cwd':str(ROOT),'environment':{},'timeout_seconds':60}); require(x['worker_started'],'not started')
        from process_ownership import inspect_process_operation
        deadline=time.monotonic()+10; state=inspect_process_operation(op)
        while state.get('state') not in {'starting','running'} and time.monotonic()<deadline:
            time.sleep(.03); state=inspect_process_operation(op)
        require(state.get('state') in {'starting','running'},f'worker never active: {state}')
        return op,x
    def exact_live_reattach():
        op,x=launch(); state=inspect_process_operation_for_context(op,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4); require(state['read_only_reattached'] and state['cancellation_available'] and not state['replay_allowed'],'live reattach failed')
        request_process_operation_cancellation_exact(op,generation=1,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4,operator_confirmed=True); x['worker_handle'].join(15)
    def new_tab_read_only():
        op,x=launch(); state=inspect_process_operation_for_context(op,project_id='eidolon',session_id='s1',tab_id='new-tab',tab_revision=4); require(state['read_only_reattached'] and state['stale_tab'] and not state['cancellation_available'],'control transferred to new tab')
        request_process_operation_cancellation_exact(op,generation=1,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4,operator_confirmed=True); x['worker_handle'].join(15)
    def project_session_isolation():
        op,x=launch(); state=inspect_process_operation_for_context(op,project_id='other',session_id='s1',tab_id='t1',tab_revision=4); require(not state['context_matches'] and not state['read_only_reattached'],'cross-project reattach')
        request_process_operation_cancellation_exact(op,generation=1,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4,operator_confirmed=True); x['worker_handle'].join(15)
    def offline_result_reconciles():
        op=f'result_{uuid.uuid4().hex}'; a=accept_process_operation(op,operation_kind='verification',may_mutate=False,acceptance_key='r',project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4)
        p=mp.get_context('spawn').Process(target=_result_then_die,args=(op,a['generation'],runtime,locks)); p.start(); p.join(10); require(p.exitcode==0,'helper failed')
        state=inspect_process_operation_for_context(op,project_id='eidolon',session_id='s1',tab_id='new',tab_revision=4); require(state['status']=='completed' and state['result_bound'] and not state['replay_allowed'],'offline result not restored')
    def aggregate_context_filter():
        state=build_process_restart_state(project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=4); require(state['restart_restored'] and not state['ownership_transferred'] and not state['replay_allowed'],'restart contract broken')
    def malformed_private_record():
        root=ownership_root(); root.mkdir(parents=True,exist_ok=True); (root/'broken.json').write_text('{bad',encoding='utf-8'); state=build_process_restart_state(project_id='eidolon'); require(state['invalid_private_record_count']>=1 and state['status']=='uncertain','invalid ownership ignored')
    def route_contract():
        src=(AGENT/'dashboard.py').read_text(); require('/api/process-operation-state' in src and ('build_process_restart_state' in src or 'build_unified_process_recovery_state' in src),'restart routes missing')
    def privacy_contract():
        state=build_process_restart_state(project_id='eidolon'); enc=json.dumps(state); require(str(Path(runtime)) not in enc and 'owner_nonce' not in enc and not state['ownership_transferred'],'restart state leaked')
    for n,f in [('live worker read-only reattachment',exact_live_reattach),('new tab cannot inherit control',new_tab_read_only),('project and session isolation',project_session_isolation),('offline result reconciliation',offline_result_reconciles),('aggregate restart restoration',aggregate_context_filter),('malformed private ownership classification',malformed_private_record),('dashboard restart routes',route_contract),('content-free restart state',privacy_contract)]:check(n,f)
  passed=sum(1 for r in RESULTS if r['ok']); report={'version':'1094.4','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS}; print(json.dumps(report,indent=2,sort_keys=True)); return 0 if passed==len(RESULTS) else 1
if __name__=='__main__': raise SystemExit(main())
