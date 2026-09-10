from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_test_selection import *
from v1352_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 a=d('a');req(not build_test_selection(source_manifest_digest='bad',requirement_digests=[a],candidate_tests=[],runtime_root=td)['ok'],'src');P+=1;req(not build_test_selection(source_manifest_digest=d('s'),requirement_digests=[a],candidate_tests=[],runtime_root=td)['ok'],'missing');P+=1;r=build_test_selection(source_manifest_digest=d('s'),requirement_digests=[a],candidate_tests=[{'test_id':'focus','covers':[a]},{'test_id':'auth','covers':[a],'authority_sensitive':True,'cost':2}],authority_sensitive=True,runtime_root=td);req(r['test_selection']['broadening_test_count']==1,'auth broad');P+=1;p=Path(td)/'phase6_test_selection'/(r['test_selection_id']+'.json');x=json.loads(p.read_text());x['selected_test_count']=99;p.write_text(json.dumps(x));req(load_test_selection(r['test_selection_id'],runtime_root=td)=={},'tamper');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1352.6-8-test-selection-reliability'})
