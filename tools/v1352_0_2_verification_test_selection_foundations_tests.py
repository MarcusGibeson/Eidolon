from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from verification_test_selection import *
from v1352_test_support import *
P=0
with tempfile.TemporaryDirectory() as td:
 a,b=d('a'),d('b');r=build_test_selection(source_manifest_digest=d('s'),requirement_digests=[a,b],candidate_tests=[{'test_id':'t1','covers':[a,b],'cost':2},{'test_id':'t2','covers':[a],'cost':1}],runtime_root=td);req(r['ok'],'ok');P+=1;req(r['test_selection']['selected_test_count']==1,'small');P+=1;req(r['test_selection']['estimated_cost']==2,'cost');P+=1;req(not r['test_execution_authorized'],'noexec');P+=1;req(r['test_selection']['content_free'],'content');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1352.0-2-test-selection-foundations'})
