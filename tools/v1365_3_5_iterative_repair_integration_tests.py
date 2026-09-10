from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from iterative_repair_loop import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1365_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,fpre,spre=fixture(Path(td));r=run_iterative_repair_loop(wid,attempts=attempts(),active_grant=grant,file_precondition_record_id=fpre,shell_precondition_record_id=spre,runtime_root=runtime,now_unix=101,max_attempts=2);v=r['iterative_repair_loop'];req(r['ok'],'loop');P+=1;c=process_ordinary_chat_development_turn('show repair loop',project_state={'iterative_repair_loop':v},runtime_root=runtime);req(c['active'] and c['ok'],'chat');P+=1;req(not c['action_executed'],'inspect');P+=1;req(v['distinct_strategy_count']==2,'distinct');P+=1;req(v['selected_source_modified'] is False,'source');P+=1;clean(runtime,grant,wid)
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1365.3-5-iterative-repair-integration'})
if __name__=='__main__':main()
