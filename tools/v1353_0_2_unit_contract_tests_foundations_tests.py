from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from unit_contract_test_generation import *
from v1353_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=sample_contracts(),runtime_root=td);req(r['ok'],'ok');P+=1;plan=r['unit_contract_test_plan'];req(plan['contract_count']==4,'contracts');P+=1;req(plan['case_count']==11,'cases');P+=1;req(plan['kinds_present']==['api','invariant','lifecycle','schema'],'kinds');P+=1;req(not plan['generated_code'] and not r['test_execution_authorized'],'declarative');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1353.0-2-unit-contract-tests-foundations'})
