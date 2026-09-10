import sys,tempfile,json;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from multi_day_continuity import *
from v1379_test_support import *
N=0
req(not capsule(campaign_record_digest='bad')['ok'],'lineage');N+=1
req(not capsule(completed_steps=9)['ok'],'progress');N+=1
req(not capsule(generation=2)['ok'],'generation');N+=1
with tempfile.TemporaryDirectory() as td:
 r=capsule();x=r['continuity_capsule'];persist_continuity_capsule(runtime_root=td,capsule=x)
 a=assess_multi_day_resume(runtime_root=td,campaign_id='camp',expected_capsule_digest=x['capsule_digest'],current_source_digest=D('new'),current_workspace_digest=W,current_upstream_digest=U,now_unix=2000);req(a['resume_assessment']['decision']=='reconciliation_required' and a['resume_assessment']['source_drift_detected'],'drift');N+=1
 b=assess_multi_day_resume(runtime_root=td,campaign_id='camp',expected_capsule_digest=x['capsule_digest'],current_source_digest=S,current_workspace_digest=W,current_upstream_digest=U,now_unix=1000+8*24*3600,max_unreviewed_gap_seconds=7*24*3600);req(b['resume_assessment']['decision']=='operator_review_required_after_long_gap','long gap');N+=1
 path=Path(td)/'campaign_continuity'/'camp'/'capsule.json';raw=json.loads(path.read_text());raw['completed_steps']=4;path.write_text(json.dumps(raw));req(not assess_multi_day_resume(runtime_root=td,campaign_id='camp',expected_capsule_digest=x['capsule_digest'],current_source_digest=S,current_workspace_digest=W,current_upstream_digest=U,now_unix=2000)['ok'],'tamper');N+=1
 req(not assess_multi_day_resume(runtime_root=td,campaign_id='bad/id',expected_capsule_digest=x['capsule_digest'],current_source_digest=S,current_workspace_digest=W,current_upstream_digest=U)['ok'],'request');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1379-reliability'})
