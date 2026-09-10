import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_modification_checkpoint import *;from v1390_test_support import *
N=0;sm,b,w,s,d,sh,c,t,l=synthetic(True);q=build_self_modification_checkpoint(self_model=sm,self_model_digest=sm['self_model_digest'],self_improvement_backlog=b,backlog_digest=b['backlog_digest'],self_change_workspace=w,protected_scope=s,dogfood_verification=d,shadow_execution=sh,canary_self_update=c,self_update_transaction=t,update_lineage=l);x=q['self_modification_checkpoint'];req(q['ok'],'rollback checkpoint');N+=1
req(x['safe_rollback_observed'] and not x['successful_update_observed'],'rollback');N+=1
req(x['passed']==x['total'],'all');N+=1
req(x['content_free'],'privacy');N+=1
req(not x['automatic_self_modification_authorized'] and not x['independent_authority_granted'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1390-checkpoint'})
