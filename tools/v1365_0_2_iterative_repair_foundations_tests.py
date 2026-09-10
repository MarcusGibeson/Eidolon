from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from iterative_repair_loop import *
from v1365_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));r=run_iterative_repair_loop(wid,attempts=attempts(),active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);req(r['ok'],'success');P+=1;v=r['iterative_repair_loop'];req(v['attempt_count']==2 and v['repair_succeeded'],'attempts');P+=1;req(v['attempts'][0]['verification_passed'] is False and v['attempts'][1]['verification_passed'] is True,'iterate');P+=1;req((candidate/'app.py').read_text()==GOOD and (src/'app.py').read_text()==BUG,'candidate only');P+=1;req(not r['application_authorized'],'authority');P+=1;clean(runtime,grant,wid)
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1365.0-2-iterative-repair-foundations'})
if __name__=='__main__':main()
