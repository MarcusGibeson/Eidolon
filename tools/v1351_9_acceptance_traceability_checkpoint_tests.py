from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from acceptance_traceability import *
from v1351_test_support import d,req
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_acceptance_traceability(source_manifest_digest=d('checkpoint'),requirements=[{'requirement_id':f'R{i}','implementation_evidence':[d(str(i))],'verification_methods':['focused-test']} for i in range(3)],runtime_root=td);req(r['ok'],'checkpoint');P+=1;req(r['traceability']['requirement_count']==3,'count');P+=1;req(r['traceability']['uncovered_count']==0,'covered');P+=1;req(not r['release_authorized'] and not r['approval_granted'],'authority');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1351.9-acceptance-traceability-checkpoint'})
