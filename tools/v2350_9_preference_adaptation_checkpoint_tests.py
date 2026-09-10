from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2350-data-')
from preference_adaptation_v2300 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2350-runtime-')); D='a'*64
r=record_preference(preference_id='p1',domain='detail',value='concise',kind='explicit',evidence_digests=[D],event_id='e1',runtime_root=runtime)
req(r['ok'] and r['record']['kind']=='explicit','explicit_preference_recorded')
req('value' not in r['record'] and r['record']['value_digest'],'public_record_hides_raw_value')
rep=record_preference(preference_id='p1',domain='detail',value='concise',kind='explicit',evidence_digests=[D],event_id='e1',runtime_root=runtime)
req(rep['status']=='preference_record_replayed','preference_replay_exactly_once')
inf=record_preference(preference_id='p2',domain='tone',value='dry',kind='inferred',evidence_digests=[D],event_id='e2',runtime_root=runtime)
req(not inf['ok'] and inf['status']=='inferred_preference_requires_repeated_evidence','inferred_requires_repetition')
inf2=record_preference(preference_id='p2',domain='tone',value='dry',kind='inferred',evidence_digests=[D,'b'*64],confidence=.99,event_id='e3',runtime_root=runtime)
req(inf2['ok'] and inf2['record']['confidence']<=.8,'inferred_confidence_bounded')
req(not record_preference(preference_id='p3',domain='health',value='x',kind='explicit',evidence_digests=[D],event_id='e4',runtime_root=runtime)['ok'],'sensitive_domain_rejected')
req(not record_preference(preference_id='p4',domain='tone',value='x',kind='situational',evidence_digests=[D],event_id='e5',runtime_root=runtime)['ok'],'situational_requires_scope')
sit=record_preference(preference_id='p4',domain='tone',value='formal',kind='situational',scope_code='work',evidence_digests=[D],event_id='e6',runtime_root=runtime)
req(sit['ok'],'situational_preference_recorded')
proj=build_adaptation_projection(context_codes=['work'],runtime_root=runtime)
req(proj['ok'] and len(proj['applied'])>=2,'contextual_projection_applies_preferences')
req(proj['raw_values_exposed'] is False and proj['preference_can_grant_authority'] is False,'projection_content_free_non_authorizing')
conf=record_preference(preference_id='p5',domain='tone',value='casual',kind='explicit',scope_code='work',evidence_digests=['c'*64],event_id='e7',runtime_root=runtime)
req(conf['ok'],'conflicting_preference_recorded')
proj2=build_adaptation_projection(context_codes=['work'],runtime_root=runtime)
req(proj2['conflict_count']==1,'conflicting_preferences_remain_explicit')
exp=record_preference(preference_id='p6',domain='timing',value='morning',kind='explicit',evidence_digests=[D],expires_at=time.time()-1,event_id='e8',runtime_root=runtime)
req(exp['ok'],'expired_preference_can_be_recorded_historically')
state=inspect_preferences(runtime_root=runtime)
req(any(x['preference_id']=='p6' and x['state']=='expired' for x in state['records']),'expired_preference_not_active')
stale=revise_preference(preference_id='p1',expected_digest='d'*64,action='forget',event_id='e9',runtime_root=runtime)
req(not stale['ok'] and stale['status']=='stale_preference_digest','stale_preference_revision_rejected')
rev=revise_preference(preference_id='p1',expected_digest=r['record']['preference_digest'],action='forget',event_id='e10',runtime_root=runtime)
req(rev['ok'] and rev['record']['state']=='forgotten','operator_forgetting_supported')
priv=build_private_adaptation_prompt(context_codes=['conversation','work'],runtime_root=runtime)
req(priv['ok'] and priv['evidence']['raw_values_publicly_exposed'] is False,'private_prompt_has_content_free_evidence')
req('casual' not in priv['prompt_section'] and 'formal' not in priv['prompt_section'],'conflicting_values_suppressed_from_private_prompt')
req(context_codes_for_message('Please debug this project at work')==('conversation','development','work'),'message_context_codes_bounded')
req(all(not r[k] for k in ('identity_inferred','authority_modified','source_modified','authority_expanded')),'preference_authority_inert')
print(json.dumps({'suite':'v2350.9-preference-adaptation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
