import json,tempfile
from pathlib import Path
from conscious_agent.reflective_subject_intake import ReflectiveSubjectIntakeStore
from conscious_agent.model_backed_reflective_session import ModelBackedReflectiveSessionStore
root=Path(tempfile.mkdtemp())
subjects=ReflectiveSubjectIntakeStore(root)
r=subjects.register('e1',subject_kind='selected_attention',source_id='attn-1',source_contract='v1124.0',importance=.8,uncertainty=.3)
sid=r['subject_id']
model=lambda p: json.dumps({'outcome':'conclusion','conclusion':'Structural conclusion only','uncertainty':.25,'evidence_refs':['attn-1'],'communication_recommendation':'silence'})
store=ModelBackedReflectiveSessionStore(root,model_generate=model)
a=store.run('r1',subject_id=sid,max_cycles=1,max_tokens=400);b=store.run('r1',subject_id=sid,max_cycles=1,max_tokens=400);snap=store.snapshot();inspect=store.inspection_summary()
checks=[a['outcome']=='conclusion',a['message_sent'] is False,a['belief_updated'] is False,b['idempotent'] is True,len(snap['sessions'])==1,snap['sessions'][0]['evidence_refs']==['attn-1'],snap['sessions'][0]['communication_recommendation']=='silence',inspect['prompts_exposed'] is False,inspect['provider_payloads_exposed'] is False,inspect['external_action_executed'] is False]
print(json.dumps({'passed':sum(checks),'total':10,'suite':'v1125.0'}));raise SystemExit(0 if all(checks) else 1)
