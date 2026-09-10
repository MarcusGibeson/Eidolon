from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent'),str(ROOT/'tools')]
from acceptance_traceability import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1351_test_support import d,req
P=0
with tempfile.TemporaryDirectory() as td:
 r=build_acceptance_traceability(source_manifest_digest=d('src'),requirements=[{'requirement_id':'R1','implementation_evidence':[d('i')],'verification_methods':['test']}],runtime_root=td);i=r['traceability_id'];req(load_acceptance_traceability(i,runtime_root=td)['traceability_complete'],'load');P+=1;c=process_ordinary_chat_development_turn('show acceptance traceability',project_state={'acceptance_traceability_id':i},runtime_root=td);req(c['active'] and c['ok'],'chat');P+=1;req(c['action_executed'] is False,'readonly');P+=1;req(process_ordinary_chat_development_turn('hello',runtime_root=td).get('active') is False,'ordinary');P+=1
print({'ok':P==4,'passed':P,'total':4,'suite':'v1351.3-5-acceptance-traceability-integration'})
