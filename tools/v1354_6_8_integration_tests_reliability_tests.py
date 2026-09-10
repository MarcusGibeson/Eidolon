from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from integration_test_verification import *
import integration_test_verification as iv
from v1354_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=fixture(Path(td));bad=run_integration_verification(wid,[sys.executable,'-c','raise SystemExit(7)'],active_grant=grant,precondition_record_id=pre,runtime_root=runtime,now_unix=101);req(not bad['ok'],'process fail');P+=1;miss=run_integration_verification(wid,[sys.executable,'-c','pass'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'missing.json'}],runtime_root=runtime,now_unix=101);req(not miss['ok'],'artifact fail');P+=1;unsafe=run_integration_verification(wid,[sys.executable,'-c','pass'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'../escape'}],runtime_root=runtime,now_unix=101);req(not unsafe['ok'],'path');P+=1;good=run_integration_verification(wid,[sys.executable,'worker.py'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'result.json','sha256':result_sha()}],runtime_root=runtime,now_unix=101);i=good['integration_verification']['integration_verification_id'];p=iv._path(i,runtime);x=json.loads(p.read_text());x['verification_passed']=False;p.write_text(json.dumps(x));req(load_integration_verification(i,runtime_root=runtime)=={},'tamper');P+=1;cleanup(runtime,grant,wid)
 print({'ok':P==4,'passed':P,'total':4,'suite':'v1354.6-8-integration-tests-reliability'})
if __name__=='__main__':main()
