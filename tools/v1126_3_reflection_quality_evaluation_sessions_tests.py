from pathlib import Path
import json,tempfile
from conscious_agent.reflection_quality_evaluation_sessions import ReflectionQualityEvaluationSessionStore
root=Path(tempfile.mkdtemp()); root.mkdir(parents=True,exist_ok=True)
(root/'reflection_quality_evaluation_candidates.json').write_text(json.dumps({'schema_version':'1','contract_version':'v1126.1','candidates':[{'candidate_id':'c1','signal_id':'s1','outcome_id':'o1','subject_id':'sub1','category':'unsupported_conclusion','state':'active'},{'candidate_id':'c2','signal_id':'s2','outcome_id':'o2','subject_id':'sub2','category':'provider_failure','state':'deferred'},{'candidate_id':'c3','signal_id':'s3','outcome_id':'o3','subject_id':'sub3','category':'contradiction','state':'requires_operator_review'}],'processed_events':[],'revision':0,'updated_at':''}))
s=ReflectionQualityEvaluationSessionStore(root);a=s.open('e1',candidate_id='c1',evaluation_budget=2);b=s.open('e2',candidate_id='c2',provider_available=False);c=s.open('e3',candidate_id='c3');d=s.open('e1',candidate_id='c1');i=s.inspection_summary()
checks=[a['state']=='open',b['state']=='paused',c['state']=='paused',d['idempotent'],i['contract_version']=='v1126.3',i['session_count']==3,not i['conclusions_exposed'],not i['hidden_reasoning_exposed'],not i['provider_contacted'],not i['external_action_executed']]
print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1126.3'}));raise SystemExit(0 if all(checks) else 1)
