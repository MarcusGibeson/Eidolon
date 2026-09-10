import json,tempfile
from pathlib import Path
from conscious_agent.reflective_subject_intake import ReflectiveSubjectIntakeStore
from conscious_agent.model_backed_reflective_session import ModelBackedReflectiveSessionStore
from conscious_agent.reflective_outcome_lineage import ReflectiveOutcomeLineageStore
from conscious_agent.reflection_quality_signals import ReflectionQualitySignalStore
root=Path(tempfile.mkdtemp()); subjects=ReflectiveSubjectIntakeStore(root); subjects.register('s1',subject_kind='concern',source_id='c1',source_contract='test')
class M:
 def complete(self,*a,**k): return '{"outcome":"conclusion","conclusion":"x","uncertainty":0.2,"evidence_refs":[],"communication_recommendation":"silence"}'
s=ModelBackedReflectiveSessionStore(root,model_generate=lambda prompt: M().complete());r=s.run('e1',subject_id=subjects.snapshot()['subjects'][0]['subject_id']);l=ReflectiveOutcomeLineageStore(root);o=l.record('e2',session_id=r['session_id']);q=ReflectionQualitySignalStore(root);a=q.derive('e3',outcome_id=o['outcome_id']);b=q.derive('e3',outcome_id=o['outcome_id']);i=q.inspection_summary();checks=[a['category']=='unsupported_conclusion',b['idempotent'],i['signal_count']==1,i['conclusions_exposed'] is False,i['hidden_reasoning_exposed'] is False,i['belief_updated'] is False,i['goal_updated'] is False,i['self_model_updated'] is False,i['provider_contacted'] is False,i['external_action_executed'] is False];print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1126.0'}));raise SystemExit(0 if all(checks) else 1)
