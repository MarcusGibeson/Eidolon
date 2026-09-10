import sys,tempfile;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from shadow_execution import *;from self_change_isolation import *;from v1386_test_support import *
N=0
with tempfile.TemporaryDirectory() as td:
 r=Path(td);b,s=roots(r);x=create_self_change_workspace(source_root=s,runtime_root=r/'rt',candidate_id=CID,self_model_digest=SM,backlog_candidate_digest=BC);q=run_shadow_execution(baseline_root=b,private_workspace=x['private_workspace'],expected_lineage_digest=x['self_change_workspace']['lineage_digest'],scenario_paths=['shadow/scenario.py']);v=q['shadow_execution'];req(q['ok'],'checkpoint');N+=1
 req(v['shadow_only'],'shadow');N+=1
 req(v['candidate_id']==CID,'lineage');N+=1
 req(v['regression_count']==0,'regressions');N+=1
 req(not v['installation_authorized'] and not v['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1386-checkpoint'})
