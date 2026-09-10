from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from integration_test_verification import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1354_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_integration_verification(wid,[sys.executable,'worker.py'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'result.json','sha256':result_sha()}],runtime_root=runtime,now_unix=101);i=r['integration_verification']['integration_verification_id'];req(load_integration_verification(i,runtime_root=runtime),'load');P+=1;c=process_ordinary_chat_development_turn('show integration verification',project_state={'integration_verification_id':i},runtime_root=runtime);req(c['active'] and c['ok'],'chat');P+=1;req(c['action_executed'] is False,'readonly');P+=1;req((Path(workspace_record(runtime,wid)['runtime_data_private_path'])/'boundary_seen.txt').read_text()=='isolated','isolated runtime');P+=1;req((src/'result.json').exists() is False,'source unchanged');P+=1;cleanup(runtime,grant,wid)
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1354.3-5-integration-tests-integration'})
if __name__=='__main__':main()
