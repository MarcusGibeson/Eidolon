from pathlib import Path
import sys,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from acceptance_traceability import *
from v1351_test_support import d,req
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_acceptance_traceability(source_manifest_digest=d('s'),requirements=[{'requirement_id':'R','implementation_evidence':[],'verification_methods':['x']}],runtime_root=td);req(not r['ok'] and r['traceability']['uncovered_count']==1,'missing');P+=1;req(not build_acceptance_traceability(source_manifest_digest='bad',requirements=[{}],runtime_root=td)['ok'],'lineage');P+=1;req(not build_acceptance_traceability(source_manifest_digest=d('s'),requirements=[{'requirement_id':'R','implementation_evidence':[d('i')],'verification_methods':['x']},{'requirement_id':'R','implementation_evidence':[d('j')],'verification_methods':['y']}],runtime_root=td)['ok'],'duplicate');P+=1
 good=build_acceptance_traceability(source_manifest_digest=d('z'),requirements=[{'requirement_id':'R2','implementation_evidence':[d('i')],'verification_methods':['x']}],runtime_root=td);p=Path(td)/'phase6_acceptance_traceability'/(good['traceability_id']+'.json');x=json.loads(p.read_text());x['covered_count']=0;p.write_text(json.dumps(x));req(load_acceptance_traceability(good['traceability_id'],runtime_root=td)=={},'tamper');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1351.6-8-acceptance-traceability-reliability'})
