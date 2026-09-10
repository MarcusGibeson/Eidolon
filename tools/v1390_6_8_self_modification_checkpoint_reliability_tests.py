import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_modification_checkpoint import *;from v1390_test_support import *
N=0
for idx,key in enumerate(['self_model','backlog','scope','dogfood','shadow','canary','transaction']):
 sm,b,w,s,d,sh,c,t,l=synthetic();args=dict(self_model=sm,self_model_digest=sm['self_model_digest'],self_improvement_backlog=b,backlog_digest=b['backlog_digest'],self_change_workspace=w,protected_scope=s,dogfood_verification=d,shadow_execution=sh,canary_self_update=c,self_update_transaction=t,update_lineage=l)
 target={'self_model':sm,'backlog':b,'scope':s,'dogfood':d,'shadow':sh,'canary':c,'transaction':t}[key];target['tamper']=idx
 req(not build_self_modification_checkpoint(**args)['ok'],key);N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1390-reliability'})
