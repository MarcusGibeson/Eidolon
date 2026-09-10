from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from acceptance_traceability import *
from v1351_test_support import d,req
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_acceptance_traceability(source_manifest_digest=d('src'),requirements=[{'requirement_id':'R1','implementation_evidence':[d('impl')],'verification_methods':['unit']},{'requirement_id':'NG1','non_goal':True,'implementation_evidence':[d('scope')],'verification_methods':['review']}],runtime_root=td);req(r['ok'],'complete');P+=1;req(r['traceability']['covered_count']==2,'coverage');P+=1;req(r['traceability']['content_free'],'privacy');P+=1;req(not r['source_mutation_authorized'] and not r['test_execution_authorized'],'authority');P+=1;req('R1' not in str(r['traceability']),'raw id leaked');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1351.0-2-acceptance-traceability-foundations'})
