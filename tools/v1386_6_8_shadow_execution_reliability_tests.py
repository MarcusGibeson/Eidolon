import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from shadow_execution import *;from self_change_isolation import *;from v1386_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);b,s=roots(r,'fail');x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);base=dict(baseline_root=b,private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'])
 q=run_shadow_execution(**base,scenario_paths=['shadow/scenario.py']);req(not q['ok'],'regression');N+=1
 req(q['shadow_execution']['regression_count']==1,'count');N+=1
 req(not run_shadow_execution(**base,scenario_paths=[])['ok'],'empty');N+=1
 req(not run_shadow_execution(**base,scenario_paths=['../x.py'])['ok'],'traversal');N+=1
 req(not run_shadow_execution(**base,scenario_paths=['shadow/missing.py'])['ok'],'missing');N+=1
 req(not run_shadow_execution(**{**base,'expected_lineage_digest':'0'*64},scenario_paths=['shadow/scenario.py'])['ok'],'lineage');N+=1
 req(not q['shadow_execution']['candidate_had_live_authority'],'authority');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1386-reliability'})
