from __future__ import annotations
import json, os, sys, tempfile, threading, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AGENT=ROOT/'conscious_agent'
if str(AGENT) not in sys.path: sys.path.insert(0,str(AGENT))
RESULTS=[]
def require(c,m):
    if not c:raise AssertionError(m)
def check(n,f):
    try:f();RESULTS.append({'name':n,'ok':True})
    except Exception as e:RESULTS.append({'name':n,'ok':False,'error':f'{type(e).__name__}: {e}'})
def main():
 with tempfile.TemporaryDirectory(prefix='eidolon-v1094-7-') as td:
  os.environ['EIDOLON_PROCESS_RUNTIME_ROOT']=str(Path(td)/'runtime');os.environ['EIDOLON_METADATA_LOCK_DIR']=str(Path(td)/'locks')
  from process_ownership import accept_process_operation,activate_process_operation,write_process_result,finalize_process_operation
  from process_recovery import cancel_process_operation_with_escalation
  def base(mutate=False):
    op='cancel_'+uuid.uuid4().hex;a=accept_process_operation(op,operation_kind='test',may_mutate=mutate,acceptance_key=op,project_id='p',session_id='s',tab_id='t',tab_revision=3);x=activate_process_operation(op,1);return op,x['owner_nonce']
  def cooperative_result():
    op,nonce=base(False)
    def finish():
      time.sleep(.05);write_process_result(op,generation=1,owner_nonce=nonce,state='cancelled',applied=False);finalize_process_operation(op,1,nonce,state='cancelled')
    threading.Thread(target=finish,daemon=True).start()
    out=cancel_process_operation_with_escalation(op,generation=1,project_id='p',session_id='s',tab_id='t',tab_revision=3,operator_confirmed=True,cooperative_wait_seconds=.5);require(out['status']=='cancelled' and out['safe_retry'] and out['cancellation_phase']=='cooperative_complete','cooperative')
  def result_after_cancel_applied():
    op,nonce=base(True)
    def finish():
      time.sleep(.05);write_process_result(op,generation=1,owner_nonce=nonce,state='completed',applied=True);finalize_process_operation(op,1,nonce,state='completed')
    threading.Thread(target=finish,daemon=True).start()
    out=cancel_process_operation_with_escalation(op,generation=1,project_id='p',session_id='s',tab_id='t',tab_revision=3,operator_confirmed=True,cooperative_wait_seconds=.5);require(out['status']=='completed' and out['result_after_cancel'] and not out['safe_retry'],'applied result misclassified')
  def wait_requires_permission():
    op,_=base(True);out=cancel_process_operation_with_escalation(op,generation=1,project_id='p',session_id='s',tab_id='t',tab_revision=3,operator_confirmed=True,cooperative_wait_seconds=.01);require(out['status']=='cooperative_wait_expired' and out['cancellation_phase']=='awaiting_force_permission' and not out['safe_retry'],'wait boundary')
  def stale_context():
    op,_=base(False);out=cancel_process_operation_with_escalation(op,generation=1,project_id='wrong',session_id='s',tab_id='t',tab_revision=3,operator_confirmed=True);require(out['status']=='project_id_mismatch','stale context')
  def truthy_rejected():
    op,_=base(False);out=cancel_process_operation_with_escalation(op,generation=1,project_id='p',session_id='s',tab_id='t',tab_revision=3,operator_confirmed='true');require(out['status']=='confirmation_required','truthy confirmation')
  def content_free():
    op,_=base(False);out=cancel_process_operation_with_escalation(op,generation=1,project_id='p',session_id='s',tab_id='t',tab_revision=3,operator_confirmed=True,cooperative_wait_seconds=0);encoded=json.dumps(out);require('owner_nonce' not in encoded and 'child_start_identity' not in encoded,'private leak')
  def version():
    from release_metadata import RUNTIME_VERSION;require(tuple(map(int,RUNTIME_VERSION.split('.'))) >= tuple(map(int,'1094.7'.split('.'))),RUNTIME_VERSION)
  for n,f in [('cooperative cancellation completion',cooperative_result),('result after cancel applied',result_after_cancel_applied),('bounded wait needs force permission',wait_requires_permission),('stale context rejected',stale_context),('literal confirmation',truthy_rejected),('content-free escalation result',content_free),('runtime version',version)]:check(n,f)
 passed=sum(r['ok'] for r in RESULTS);report={'version':'1094.7','status':'pass' if passed==len(RESULTS) else 'fail','passed':passed,'total':len(RESULTS),'checks':RESULTS};print(json.dumps(report,indent=2,sort_keys=True));return 0 if passed==len(RESULTS) else 1
if __name__=='__main__':raise SystemExit(main())
