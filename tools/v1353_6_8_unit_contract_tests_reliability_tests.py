from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from unit_contract_test_generation import *
from v1353_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 req(not build_unit_contract_test_plan(source_manifest_digest='bad',contracts=sample_contracts(),runtime_root=td)['ok'],'source');P+=1
 bad=sample_contracts();bad[0]=dict(bad[0],kind='shell');req(not build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=bad,runtime_root=td)['ok'],'kind');P+=1
 dup=sample_contracts()+[sample_contracts()[0]];req(not build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=dup,runtime_root=td)['ok'],'dup');P+=1
 bad=sample_contracts();bad[0]=dict(bad[0],evidence_digest='bad');req(not build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=bad,runtime_root=td)['ok'],'evidence');P+=1
 r=build_unit_contract_test_plan(source_manifest_digest=d('s'),contracts=sample_contracts(),runtime_root=td);p=Path(td)/'phase6_unit_contract_tests'/(r['unit_contract_test_plan_id']+'.json');x=json.loads(p.read_text());x['case_count']=99;p.write_text(json.dumps(x));req(load_unit_contract_test_plan(r['unit_contract_test_plan_id'],runtime_root=td)=={},'tamper');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1353.6-8-unit-contract-tests-reliability'})
