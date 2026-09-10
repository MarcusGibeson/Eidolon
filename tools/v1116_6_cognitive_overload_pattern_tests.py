import json,tempfile
from pathlib import Path
from conscious_agent.cognitive_recovery_lifecycle import CognitiveRecoveryLifecycleStore
from conscious_agent.sustainable_cognitive_windows import SustainableCognitiveWindowStore
from conscious_agent.cognitive_overload_patterns import CognitiveOverloadPatternStore
p=t=0
def c(n,x):
 global p,t;t+=1
 if x:p+=1
 else:raise AssertionError(n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);life=CognitiveRecoveryLifecycleStore(r);a=life.propose('p',review_id='r',recommendation='recovery_window_recommended')['result']['recovery_id'];w=SustainableCognitiveWindowStore(r)
 ids=[]
 for i in range(2): ids.append(w.record(f'w{i}',recovery_id=a,before_pressure=.8+i*.01,after_pressure=.8,before_margin=.2,after_margin=.2,observation_count=1)['result']['outcome_id'])
 s=CognitiveOverloadPatternStore(r);x=s.evaluate('e',recovery_id=a,window_outcome_ids=ids);c('ok',x['ok']);c('supported',x['result']['pattern_status']=='repeated_overload_supported');c('dup event',s.evaluate('e',recovery_id=a)['idempotent']);c('count',s.inspection_summary()['pattern_count']==1);c('content free',s.inspection_summary()['recent_patterns'][0]['content_free']);c('no success missing',not s.inspection_summary()['missing_feedback_is_success']);c('no authority',not any(s.inspection_summary()['recent_patterns'][0][k] for k in ('authorization_id','action_id')));c('contract',s.inspection_summary()['contract_version']=='v1116.6')
print(json.dumps({'passed':p,'total':t,'suite':'v1116.6'}))
