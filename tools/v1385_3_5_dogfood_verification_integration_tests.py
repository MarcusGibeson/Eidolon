import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dogfood_verification import *;from self_change_isolation import *;from protected_core import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1385_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);s=classify_self_change_scope(changed_paths=['app.py'])['scope'];q=run_dogfood_verification(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],protected_scope=s,expected_scope_digest=s['scope_digest'],test_paths=['tools/self_test.py']);req(q['ok'],'dogfood');N+=1
 req(q['dogfood_verification']['candidate_installable'],'evidence');N+=1
 chat=process_ordinary_chat_development_turn('show dogfood verification',project_state={'dogfood_verification':q['dogfood_verification']});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['source_mutation_authorized'],'source');N+=1
 req(q['dogfood_verification']['scope_digest']==s['scope_digest'],'scope lineage');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1385-integration'})
