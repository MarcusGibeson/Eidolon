from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from unit_contract_test_generation import *
from v1353_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_unit_contract_test_plan(source_manifest_digest=d('checkpoint'),contracts=sample_contracts(),runtime_root=td);req(r['ok'],'ok');P+=1;plan=r['unit_contract_test_plan'];req(plan['deterministic'] and plan['content_free'],'evidence');P+=1;req(plan['case_count']>=plan['contract_count'],'coverage');P+=1;req(not r['release_authorized'] and not r['approval_granted'],'authority');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1353.9-unit-contract-tests-checkpoint'})
