import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from self_improvement_backlog import *;from v1382_test_support import *
N=0
req(not build_self_improvement_backlog(self_model_digest='bad',observations=[obs()])['ok'],'model');N+=1
req(not build_self_improvement_backlog(self_model_digest=SM,observations=[])['ok'],'empty');N+=1
bad=obs();bad['category']='unknown';req(not build_self_improvement_backlog(self_model_digest=SM,observations=[bad])['ok'],'category');N+=1
r=build_self_improvement_backlog(self_model_digest=SM,observations=[obs('failure','core','core',10,100,1,'protected_core',True)]);x=r['self_improvement_backlog'];req(x['candidates'][0]['requires_stronger_review'],'protected');N+=1
t=dict(x);t['candidate_count']=9;req(not review_self_improvement_candidate(backlog=t,expected_backlog_digest=x['backlog_digest'],candidate_id=x['candidates'][0]['candidate_id'],disposition='defer',operator_reviewed=True)['ok'],'tamper');N+=1
req(not review_self_improvement_candidate(backlog=x,expected_backlog_digest=x['backlog_digest'],candidate_id='missing',disposition='defer',operator_reviewed=True)['ok'],'missing');N+=1
req(not review_self_improvement_candidate(backlog=x,expected_backlog_digest=x['backlog_digest'],candidate_id=x['candidates'][0]['candidate_id'],disposition='propose',operator_reviewed=False)['ok'],'operator');N+=1
print({'ok':N==7,'passed':N,'total':7,'suite':'v1382-reliability'})
