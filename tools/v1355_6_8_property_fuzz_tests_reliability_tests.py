from pathlib import Path
import tempfile,sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'conscious_agent'),str(ROOT/'tools')]
import property_fuzz_verification as pf
from property_fuzz_verification import *
from v1355_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 req(not build_property_fuzz_report(source_manifest_digest='bad',properties=BASE,runtime_root=td)['ok'],'lineage');P+=1
 bad=[dict(BASE[0],oracle='exec_python')];req(build_property_fuzz_report(source_manifest_digest=SOURCE,properties=bad,runtime_root=td)['status']=='property_fuzz_definition_invalid','oracle');P+=1
 req(build_property_fuzz_report(source_manifest_digest=SOURCE,properties=BASE,max_cases=10,runtime_root=td)['status']=='property_fuzz_case_budget_exceeded','budget');P+=1
 failing=[{'property_id':'seeded.zero','oracle':'nonzero_integer','generator':'bounded_integer','evidence_digest':E,'cases':8}]
 a=build_property_fuzz_report(source_manifest_digest=SOURCE,properties=failing,seed=3,max_cases=8,runtime_root=td);req(not a['ok'] and a['property_fuzz_report']['failed_property_count']==1,'counterexample');P+=1
 row=a['property_fuzz_report']['properties'][0];req(row['failure_count']>=1 and row['shrink_metadata'][0]['strategy']=='integer_toward_zero','shrink');P+=1
 with tempfile.TemporaryDirectory() as td2:
  b=build_property_fuzz_report(source_manifest_digest=SOURCE,properties=failing,seed=3,max_cases=8,runtime_root=td2);req(row['failure_digests']==b['property_fuzz_report']['properties'][0]['failure_digests'],'repro');P+=1
 rid=a['property_fuzz_report']['property_fuzz_report_id'];path=pf._root(td)/(rid+'.json');obj=json.loads(path.read_text());obj['case_count']=999;path.write_text(json.dumps(obj));req(load_property_fuzz_report(rid,runtime_root=td)=={},'tamper');P+=1
 req('value' not in str(row) and 'payload' not in str(row),'no payload');P+=1
print({'ok':P==8,'passed':P,'total':8,'suite':'v1355.6-8-property-fuzz-reliability'})
