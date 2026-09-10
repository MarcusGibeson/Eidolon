import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from multi_day_continuity import *
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1379_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=capsule();x=r['continuity_capsule'];p=persist_continuity_capsule(runtime_root=td,capsule=x);req(p['ok'],'persist');N+=1
 a=assess_multi_day_resume(runtime_root=td,campaign_id='camp',expected_capsule_digest=x['capsule_digest'],current_source_digest=S,current_workspace_digest=W,current_upstream_digest=U,now_unix=2000);req(a['ok'] and a['resume_assessment']['decision']=='resume_ready','resume');N+=1
 req(a['resume_assessment']['calendar_gap_seconds']==1000 and not a['resume_assessment']['chat_history_read'],'gap');N+=1
 c=process_ordinary_chat_development_turn('show campaign continuity',project_state={'multi_day_continuity':a['resume_assessment']});req(c.get('active') and c.get('ok'),'chat');N+=1
 req(not c['action_executed'] and not c['automatic_resume_authorized'],'inspect only');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1379-integration'})
