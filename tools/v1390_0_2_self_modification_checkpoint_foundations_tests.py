import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_modification_checkpoint import *;from v1390_test_support import *
N=0;sm,b,w,s,d,sh,c,t,l=synthetic();q=build_self_modification_checkpoint(self_model=sm,self_model_digest=sm['self_model_digest'],self_improvement_backlog=b,backlog_digest=b['backlog_digest'],self_change_workspace=w,protected_scope=s,dogfood_verification=d,shadow_execution=sh,canary_self_update=c,self_update_transaction=t,update_lineage=l);req(q['ok'],'build');N+=1
x=q['self_modification_checkpoint'];req(x['passed']==x['total'],'checks');N+=1
req(x['successful_update_observed'] and not x['safe_rollback_observed'],'success');N+=1
req(x['operator_supervision_required'] and x['content_free'],'supervision');N+=1
req(not x['automatic_self_modification_authorized'] and not x['release_authorized'],'authority');N+=1
print({'ok':N==5,'passed':N,'total':5,'suite':'v1390-foundations'})
