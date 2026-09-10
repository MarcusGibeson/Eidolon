import json,tempfile
from pathlib import Path
from conscious_agent.reflective_subject_intake import ReflectiveSubjectIntakeStore
from conscious_agent.model_backed_reflective_session import ModelBackedReflectiveSessionStore
from conscious_agent.reflective_outcome_lineage import ReflectiveOutcomeLineageStore
from conscious_agent.reflective_reliability_review import ReflectiveReliabilityReviewer
root=Path(tempfile.mkdtemp());sub=ReflectiveSubjectIntakeStore(root);sid=sub.register('s1',subject_kind='goal',source_contract='test',source_id='g',importance=.8,uncertainty=.2)['subject_id'];ses=ModelBackedReflectiveSessionStore(root,model_generate=lambda p:'{"outcome":"conclusion","conclusion":"x","uncertainty":0.9,"evidence_refs":[],"communication_recommendation":"silence"}');lin=ReflectiveOutcomeLineageStore(root)
for i in range(3):
 r=ses.run(f'm{i}',subject_id=sid);lin.record(f'o{i}',session_id=r['session_id'] if 'session_id' in r else ses.snapshot()['sessions'][-1]['session_id'])
rev=ReflectiveReliabilityReviewer(root).review(subject_id=sid,operator_review_required=True);checks=[rev['contract_version']=='v1125.7',rev['sample_size']>=1,rev['unsupported_conclusion_count']>=1,rev['high_uncertainty_count']>=1,rev['status'] in {'unsupported_conclusion_pattern','insufficient_evidence'},not rev['belief_updated'],not rev['message_sent'],not rev['initiative_created'],not rev['external_action_executed'],not rev['hidden_reasoning_exposed']];print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1125.7'}));raise SystemExit(0 if all(checks) else 1)
