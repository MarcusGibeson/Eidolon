from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.path.insert(0,str(ROOT/'tools'))
from v1336_process_operations_test_support import *
from typed_process_operations import *
from release_authority import WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT
def main():
    passed=[0]
    def req(x,n):
          assert x,n;passed[0]+=1
    with tempfile.TemporaryDirectory() as td:
     src,runtime,grant,wid,candidate,pre=process_candidate(Path(td));before=hashlib.sha256((src/'app.py').read_bytes()).hexdigest()
     started=start_candidate_process(wid,[sys.executable,'-c','from pathlib import Path;Path("generated.tmp").write_text("candidate only")'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101);done=wait_terminal(started['process_operation']['process_operation_id'],runtime);req(done['process_operation']['process_state']=='completed' and (candidate/'generated.tmp').is_file(),'candidate_process_can_mutate_candidate')
     req(hashlib.sha256((src/'app.py').read_bytes()).hexdigest()==before and not (src/'generated.tmp').exists(),'selected_source_unchanged')
     row=done['process_operation'];req(row['candidate_workspace_only'] and row['source_mutation_authorized'] is False and row['release_authorized'] is False,'authority_scope_explicit')
     req(row['stdout_bytes']<=row['max_log_bytes'] and row['stderr_bytes']<=row['max_log_bytes'],'bounded_logs_checkpoint')
    req((WORKING_SOURCE_VERSION!='1336.9') or ('v1337' in NEXT_BOUNDED_UNIT),'historical_next_exact_when_current')
    print({'ok':True,'suite':'v1336.9-process-operations-checkpoint','passed':passed[0],'total':5})

if __name__ == "__main__":
    main()
