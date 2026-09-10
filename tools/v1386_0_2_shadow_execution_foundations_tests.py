import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from shadow_execution import *;from self_change_isolation import *;from v1386_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);b,s=roots(r);x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);q=run_shadow_execution(baseline_root=b,private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],scenario_paths=['shadow/scenario.py']);req(q['ok'],'run');N+=1
 v=q['shadow_execution'];req(v['scenario_count']==1,'count');N+=1
 req(v['behavior_changed_count']==0 and v['regression_count']==0,'parity');N+=1
 req(v['baseline_remained_live_authority'] and not v['candidate_had_live_authority'],'authority split');N+=1
 req(v['content_free'] and not v['release_authorized'],'boundary');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1386-foundations'})
