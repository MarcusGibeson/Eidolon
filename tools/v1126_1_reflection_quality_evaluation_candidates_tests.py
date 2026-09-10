import json,tempfile
from pathlib import Path
from conscious_agent.reflective_subject_intake import ReflectiveSubjectIntakeStore
from conscious_agent.model_backed_reflective_session import ModelBackedReflectiveSessionStore
from conscious_agent.reflective_outcome_lineage import ReflectiveOutcomeLineageStore
from conscious_agent.reflection_quality_signals import ReflectionQualitySignalStore
from conscious_agent.reflection_quality_evaluation_candidates import ReflectionQualityEvaluationCandidateStore
root=Path(tempfile.mkdtemp());sub=ReflectiveSubjectIntakeStore(root);sub.register('s1',subject_kind='concern',source_id='c1',source_contract='test')
class M:
 def complete(self,*a,**k): return '{"outcome":"conclusion","conclusion":"x","uncertainty":0.2,"evidence_refs":[],"communication_recommendation":"silence"}'
r=ModelBackedReflectiveSessionStore(root,model_generate=lambda prompt: M().complete()).run('e1',subject_id=sub.snapshot()['subjects'][0]['subject_id']);o=ReflectiveOutcomeLineageStore(root).record('e2',session_id=r['session_id']);sg=ReflectionQualitySignalStore(root);x=sg.derive('e3',outcome_id=o['outcome_id']);st=ReflectionQualityEvaluationCandidateStore(root);a=st.create('e4',signal_id=x['signal_id']);b=st.create('e5',signal_id=x['signal_id'],cognitive_load=.9);i=st.inspection_summary();checks=[a['state']=='active',b['state']=='deferred',i['candidate_count']==2,'requires_operator_review' in i['recognized_states'],i['conclusions_exposed'] is False,i['hidden_reasoning_exposed'] is False,i['belief_updated'] is False,i['provider_contacted'] is False,i['message_sent'] is False,i['external_action_executed'] is False];print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1126.1'}));raise SystemExit(0 if all(checks) else 1)
