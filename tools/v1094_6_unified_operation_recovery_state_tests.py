from __future__ import annotations
import json, os, sys, tempfile, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
    if not c: raise AssertionError(m)
def check(n,f):
    try:f();RESULTS.append({'name':n,'ok':True})
    except Exception as e:RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def main():
  with tempfile.TemporaryDirectory(prefix='eidolon-v1094-6-') as td:
    os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=str(Path(td)/'runtime');os.environ['EIDOLON_METADATA_LOCK_DIR']=str(Path(td)/'locks')
    from process_ownership import accept_process_operation, activate_process_operation, write_process_result, finalize_process_operation
    from process_recovery import build_unified_process_recovery_state, inspect_process_operation_for_context
    def create(state='starting', tab='t1', rev=2, mutate=False):
      op='op_'+uuid.uuid4().hex; a=accept_process_operation(op,operation_kind='verification',may_mutate=mutate,acceptance_key=op,project_id='eidolon',session_id='s1',tab_id=tab,tab_revision=rev);require(a['ok'],'accept')
      x=activate_process_operation(op,a['generation']);require(x['ok'],'activate')
      if state=='completed':
        write_process_result(op,generation=1,owner_nonce=x['owner_nonce'],state='completed',applied=mutate);finalize_process_operation(op,1,x['owner_nonce'],state='completed')
      return op
    def unified_contract():
      create(); state=build_unified_process_recovery_state(project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=2);require(state['unified_recovery_contract'] and state['ordinary_conversation_available'],'contract missing');require(state['status']=='busy','busy status')
    def terminal_states():
      op=create('completed'); row=inspect_process_operation_for_context(op,project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=2);require(row['status']=='completed' and not row['replay_allowed'],'terminal')
    def stale_tab_read_only():
      op=create(tab='old',rev=1); row=inspect_process_operation_for_context(op,project_id='eidolon',session_id='s1',tab_id='new',tab_revision=2);require(row['stale_tab'] and not row['cancellation_available'],'stale tab control')
    def privacy():
      create(); encoded=json.dumps(build_unified_process_recovery_state(project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=2));
      for term in ('owner_nonce','owner_pid','child_pid','process_start_identity','cancellation_owner_nonce_digest','stdout_path','command_args','environment_values'):
        require(term not in encoded,f'leak {term}')
    def bounded_history():
      for _ in range(55): create('completed')
      state=build_unified_process_recovery_state(project_id='eidolon',session_id='s1',tab_id='t1',tab_revision=2);require(state['operation_count']==50 and state['history_truncated'],'history not bounded')
    def source_contract():
      text=(AGENT/'process_recovery.py').read_text();require('build_unified_process_recovery_state' in text and '_content_free_recovery_row' in text,'source contract')
    def version():
      from release_metadata import RUNTIME_VERSION;require(tuple(map(int,RUNTIME_VERSION.split('.'))) >= tuple(map(int,'1094.6'.split('.'))),RUNTIME_VERSION)
    for n,f in [('unified recovery contract',unified_contract),('terminal state truth',terminal_states),('stale tab read only',stale_tab_read_only),('content-free state',privacy),('bounded long-session history',bounded_history),('source contract',source_contract),('runtime version',version)]:check(n,f)
  passed=sum(r['ok'] for r in RESULTS);report={'version':'1094.6','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS};print(json.dumps(report,indent=2,sort_keys=True));return 0 if passed==len(RESULTS) else 1
if __name__=='__main__':raise SystemExit(main())
