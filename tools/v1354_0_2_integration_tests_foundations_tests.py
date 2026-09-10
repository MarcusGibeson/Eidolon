from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from integration_test_verification import *
from v1354_test_support import *
def main():
 P=0
 with tempfile.TemporaryDirectory() as td:
  src,runtime,grant,wid,candidate,pre=fixture(Path(td));r=run_integration_verification(wid,[sys.executable,'worker.py'],active_grant=grant,precondition_record_id=pre,expected_artifacts=[{'relative_path':'result.json','sha256':result_sha()}],runtime_root=runtime,now_unix=101);req(r['ok'],'ok');P+=1;v=r['integration_verification'];req(v['real_process_boundary_exercised'] and not v['mock_only'],'real');P+=1;req(v['controlled_runtime_root'],'runtime');P+=1;req(v['artifact_checks'][0]['ok'],'artifact');P+=1;req(not r['source_mutation_authorized'] and not r['network_authorized'],'authority');P+=1;cleanup(runtime,grant,wid)
 print({'ok':P==5,'passed':P,'total':5,'suite':'v1354.0-2-integration-tests-foundations'})
if __name__=='__main__':main()
