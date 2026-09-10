from pathlib import Path
import tempfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from property_fuzz_verification import *
from v1355_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_property_fuzz_report(source_manifest_digest=SOURCE,properties=BASE,seed=7,max_cases=128,runtime_root=td);req(r['ok'],'pass');P+=1
 v=r['property_fuzz_report'];req(v['property_count']==4 and v['case_count']==96,'counts');P+=1
 req(v['bounded'] and v['deterministic'] and not v['generated_code'],'bounded');P+=1
 req(v['payloads_persisted'] is False and 'identifier.safe' not in str(v),'content minimized');P+=1
 req(not r['test_execution_authorized'] and not r['source_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1355.0-2-property-fuzz-foundations'})
