import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from canary_self_update import *;from self_change_isolation import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1387_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);x=create_self_change_workspace(source_root=src(r),runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);d,s=evidence();q=run_canary_self_update(private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],dogfood_verification=d,expected_dogfood_digest=d['verification_digest'],shadow_execution=s,expected_shadow_digest=s['shadow_digest'],health_scenarios=['canary/health.py']);v=q['canary_self_update'];req(q['ok'],'canary');N+=1
 req(v['dogfood_digest']==d['verification_digest'] and v['shadow_digest']==s['shadow_digest'],'lineage');N+=1
 chat=process_ordinary_chat_development_turn('show canary self update',project_state={'canary_self_update':v});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['source_replacement_authorized'],'source');N+=1
 req(v['content_free'],'privacy');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1387-integration'})
