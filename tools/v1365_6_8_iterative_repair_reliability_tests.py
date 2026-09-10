from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from iterative_repair_loop import *
from v1365_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));a=attempts();a[1]['strategy_digest']=a[0]['strategy_digest'];r=run_iterative_repair_loop(wid,attempts=a,active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);req(not r['ok'] and r['status']=='repeated_strategy_blocked','repeat');P+=1;clean(runtime,grant,wid)
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));a=attempts();a[0]['evidence_supports_attempt']=False;r=run_iterative_repair_loop(wid,attempts=a,active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);req(r['status']=='evidence_exhausted' and r['iterative_repair_loop']['attempt_count']==0,'evidence');P+=1;clean(runtime,grant,wid)
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));a=attempts();a[0]['expected_content_digest']='0'*64;r=run_iterative_repair_loop(wid,attempts=a,active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);req(r['status']=='patch_failed','stale');P+=1;req((src/'app.py').read_text()==BUG,'source unchanged');P+=1;clean(runtime,grant,wid)
 req(not run_iterative_repair_loop('x',attempts=attempts(),active_grant={},file_precondition_record_id='x',shell_precondition_record_id='x',max_attempts=1)['ok'],'budget');P+=1
 req(not r['application_authorized'],'authority');P+=1
 print({'ok':P==6,'passed':P,'total':6,'suite':'v1365.6-8-iterative-repair-reliability'})
if __name__=='__main__':main()
