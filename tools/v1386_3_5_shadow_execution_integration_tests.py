import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from shadow_execution import *;from self_change_isolation import *;from ordinary_chat_development_campaign import process_ordinary_chat_development_turn;from v1386_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);b,s=roots(r,'changed');x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);q=run_shadow_execution(baseline_root=b,private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],scenario_paths=['shadow/scenario.py']);req(q['ok'],'changed not failure');N+=1
 v=q['shadow_execution'];req(v['behavior_changed_count']==1 and v['regression_count']==0,'difference');N+=1
 req(v['scenarios'][0]['baseline']['output_digest']!=v['scenarios'][0]['candidate']['output_digest'],'digest');N+=1
 chat=process_ordinary_chat_development_turn('show shadow execution',project_state={'shadow_execution':v});req(chat.get('active') and chat.get('ok'),'chat');N+=1
 req(not chat['live_authority_granted'],'no authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1386-integration'})
