from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from integration_test_verification import *
from v1354_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_integration_verification(wid,[sys.executable,'worker.py'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'result.json','sha256':result_sha()}],runtime_root=runtime,now_unix=101);req(r['ok'],'ok');P+=1;req(r['integration_verification']['verification_passed'],'verified');P+=1;req((src/'result.json').exists() is False,'source');P+=1;req(not r['release_authorized'] and not r['provider_contact_authorized'],'authority');P+=1;cleanup(runtime,grant,wid)
 print({'ok':P==4,'passed':P,'total':4,'suite':'v1354.9-integration-tests-checkpoint'})
if __name__=='__main__':main()
