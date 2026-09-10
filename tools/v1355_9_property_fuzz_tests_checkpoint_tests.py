from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from property_fuzz_verification import *
from v1355_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_property_fuzz_report(source_manifest_digest=SOURCE,properties=BASE,seed=1355,max_cases=128,max_seconds=3,runtime_root=td);v=r['property_fuzz_report'];req(r['ok'],'checkpoint');P+=1
 req(all(x['passed'] for x in v['properties']),'properties');P+=1
 req(v['failed_property_count']==0 and v['case_count']==96,'coverage');P+=1
 req(v['content_free'] and not v['payloads_persisted'],'privacy');P+=1
 req(not r['network_authorized'] and not r['provider_contact_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1355.9-property-fuzz-checkpoint'})
