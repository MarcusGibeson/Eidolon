import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from multi_day_continuity import *
from v1379_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=capsule(last_active_unix=100);x=r['continuity_capsule'];req(r['ok'],'capsule');N+=1
 req(persist_continuity_capsule(runtime_root=td,capsule=x)['ok'],'persist');N+=1
 a=assess_multi_day_resume(runtime_root=td,campaign_id='camp',expected_capsule_digest=x['capsule_digest'],current_source_digest=S,current_workspace_digest=W,current_upstream_digest=U,now_unix=200);req(a['resume_assessment']['decision']=='resume_ready','resume');N+=1
 req(a['resume_assessment']['compact_state_only'] and not a['resume_assessment']['chat_history_required'],'compact');N+=1
 req(not a['automatic_resume_authorized'] and not a['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1379-checkpoint'})
