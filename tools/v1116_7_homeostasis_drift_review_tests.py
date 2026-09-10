import json,tempfile
from pathlib import Path
from conscious_agent.cognitive_recovery_lifecycle import CognitiveRecoveryLifecycleStore
from conscious_agent.sustainable_cognitive_windows import SustainableCognitiveWindowStore
from conscious_agent.cognitive_overload_patterns import CognitiveOverloadPatternStore
from conscious_agent.homeostasis_drift_review import HomeostasisDriftReviewStore
p=t=0
def c(n,x):
 global p,t;t+=1
 if x:p+=1
 else:raise AssertionError(n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);rid=CognitiveRecoveryLifecycleStore(r).propose('p',review_id='r',recommendation='recovery_window_recommended')['result']['recovery_id'];w=SustainableCognitiveWindowStore(r);ids=[]
 for i in range(2):ids.append(w.record(f'w{i}',recovery_id=rid,before_pressure=.8+i*.01,after_pressure=.8,before_margin=.2,after_margin=.2,observation_count=1)['result']['outcome_id'])
 pat=CognitiveOverloadPatternStore(r).evaluate('e',recovery_id=rid,window_outcome_ids=ids)['result']['pattern_id'];s=HomeostasisDriftReviewStore(r);x=s.evaluate('d',pattern_ids=[pat]);c('ok',x['ok']);c('drift',x['result']['review_status']=='drift_supported');c('dup event',s.evaluate('d',pattern_ids=[pat])['idempotent']);q=s.inspection_summary();c('count',q['review_count']==1);c('content free',q['recent_reviews'][0]['content_free']);c('no adapt',not q['recent_reviews'][0]['adaptation_applied']);c('missing unknown',not q['missing_feedback_is_success']);c('contract',q['contract_version']=='v1116.7')
print(json.dumps({'passed':p,'total':t,'suite':'v1116.7'}))
