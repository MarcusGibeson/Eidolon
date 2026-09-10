from __future__ import annotations
import json,os,signal,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1336_process_operations_test_support import *
from typed_process_operations import *
from typed_process_operations import _process_runtime
from process_ownership import load_private_process_operation
def main():
    passed=[0]
    def req(x,n):
          assert x,n;passed[0]+=1
    with tempfile.TemporaryDirectory() as td:
     src,runtime,grant,wid,candidate,pre=process_candidate(Path(td))
     timed=start_candidate_process(wid,[sys.executable,'-c','import time;time.sleep(3)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101,timeout_seconds=.25,invocation_discriminator='timeout');done=wait_terminal(timed['process_operation']['process_operation_id'],runtime);req(done['process_operation']['process_state']=='failed' and done['process_operation']['timed_out'],'timeout_contains_tree')
     noisy=start_candidate_process(wid,[sys.executable,'-c','import sys,time;sys.stdout.write("x"*200000);sys.stdout.flush();time.sleep(2)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101,max_log_bytes=4096,invocation_discriminator='noise');noise_done=wait_terminal(noisy['process_operation']['process_operation_id'],runtime);req(noise_done['process_operation']['process_state']=='failed' and noise_done['process_operation']['log_limit_exceeded'],'bounded_log_overflow_terminates')
     op=noisy['process_operation']['process_operation_id'];path=runtime/'development_campaigns'/'phase4_process_operations'/'records'/f'{op}.json';raw=json.loads(path.read_text());raw['process_state']='completed';path.write_text(json.dumps(raw));req(not load_process_operation(op,runtime_root=runtime),'tampered_public_record_rejected')
     orphan=start_candidate_process(wid,[sys.executable,'-c','import time;time.sleep(30)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101,include_private_worker_handle=True,invocation_discriminator='orphan');handle=orphan.get('_worker_handle');oop=orphan['process_operation']['process_operation_id'];req(handle is not None,'worker_handle_internal_fixture')
     # Wait for the child identity to bind before killing only the worker owner.
     deadline=time.monotonic()+3
     while time.monotonic()<deadline:
      with _process_runtime(runtime):
       private=load_private_process_operation('v1336:'+oop) or {}
      if private.get('child_start_identity'):break
      time.sleep(.02)
     handle.terminate();handle.join(timeout=3);observed=monitor_candidate_process(oop,runtime_root=runtime);req(observed['process_operation']['process_state']=='orphan_running' and observed['process_operation']['recovery_required'],'stale_owner_child_preserved_for_recovery')
     recovered=recover_candidate_process(oop,runtime_root=runtime,terminate_orphan=True);req(recovered.get('orphan_terminated') is True and recovered['process_operation']['process_state']=='uncertain' and recovered.get('replay_allowed') is False,'exact_orphan_tree_terminated_without_replay')
    print({'ok':True,'suite':'v1336.6-8-process-operations-reliability','passed':passed[0],'total':6})

if __name__ == "__main__":
    main()
