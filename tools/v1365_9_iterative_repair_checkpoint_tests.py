from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from iterative_repair_loop import *
from v1365_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));r=run_iterative_repair_loop(wid,attempts=attempts(),active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);v=r['iterative_repair_loop'];req(r['status']=='repair_succeeded','checkpoint');P+=1;req(v['attempt_count']==2,'iteration');P+=1;req(v['candidate_only_mutation'] and not v['selected_source_modified'],'isolation');P+=1;req(v['content_free'] and v['stop_reason']=='repair_succeeded','evidence');P+=1;req(not r['release_authorized'] and not r['source_mutation_authorized'],'authority');P+=1;clean(runtime,grant,wid)
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1365.9-iterative-repair-checkpoint'})
if __name__=='__main__':main()
