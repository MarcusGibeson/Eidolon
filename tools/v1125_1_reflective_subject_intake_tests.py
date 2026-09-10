import json,tempfile
from pathlib import Path
from conscious_agent.reflective_subject_intake import ReflectiveSubjectIntakeStore,SUBJECT_KINDS
root=Path(tempfile.mkdtemp());s=ReflectiveSubjectIntakeStore(root)
ids=[]
for i,k in enumerate(sorted(SUBJECT_KINDS)):ids.append(s.register(f'e{i}',subject_kind=k,source_id=f'src-{i}',source_contract='test',importance=.5,uncertainty=.4)['subject_id'])
d=s.register('dup',subject_kind='goal',source_id='src-1',source_contract='test',importance=.5,uncertainty=.4)
review=s.register('review',subject_kind='concern',source_id='sensitive',source_contract='test',operator_review_required=True)
ins=s.inspection_summary();checks=[len(ids)==6,len(set(ids))==6,d['status'] in {'reflective_subject_registered','reflective_subject_reused'},review['status']=='reflective_subject_registered',s.snapshot()['subjects'][-1]['state']=='requires_operator_review',ins['raw_messages_exposed'] is False,ins['provider_payloads_exposed'] is False,ins['reflection_created'] is False,ins['provider_contacted'] is False,ins['external_action_executed'] is False]
print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1125.1'}));raise SystemExit(0 if all(checks) else 1)
