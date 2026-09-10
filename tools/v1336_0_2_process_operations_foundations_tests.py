from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1336_process_operations_test_support import *
from typed_process_operations import *
def main():
    passed=[0]
    def req(x,n):
          assert x,n;passed[0]+=1
    req(PROCESS_OPERATION_KINDS==('start','monitor','stop'),'exact_typed_surface')
    with tempfile.TemporaryDirectory() as td:
     src,runtime,grant,wid,candidate,pre=process_candidate(Path(td))
     bad=start_candidate_process(wid,'echo unsafe',active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101);req(not bad['ok'] and bad['status']=='argument_vector_required','shell_text_rejected')
     started=start_candidate_process(wid,[sys.executable,'-c','print("bounded-output")'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101);req(started['ok'] and started['operation_executed_this_request'],'real_process_started')
     op=started['process_operation']['process_operation_id'];done=wait_terminal(op,runtime);row=done['process_operation'];req(row['process_state']=='completed' and row['stdout_bytes']>0 and row['stdout_digest'],'completion_and_log_evidence')
     req(row['raw_command_exposed'] is False and row['environment_values_exposed'] is False and row['worker_or_child_identity_exposed'] is False and row['network_authorized'] is False,'content_minimized_no_network')
    print({'ok':True,'suite':'v1336.0-2-process-operations-foundations','passed':passed[0],'total':5})

if __name__ == "__main__":
    main()
