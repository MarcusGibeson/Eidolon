from __future__ import annotations
import json, sys, tempfile, threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
from affective_regulation_v1900 import read_affective_state,update_affective_regulation,public_affective_state,affective_prompt_section
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1975-'))
initial=public_affective_state(read_affective_state(runtime_root=runtime))
req(initial['revision']==0,'default_revision')
req(initial['claims_subjective_experience'] is False,'default_no_subjective_claim')
now=datetime(2026,8,23,tzinfo=timezone.utc)
first=update_affective_regulation('I am frustrated that this failed again.',event_id='turn-1',contextual_behavior={'mood_signal':'distressed'},runtime_root=runtime,now=now)
req(first['ok'] and first['status']=='affective_state_updated','first_update')
req(first['state']['revision']==1,'revision_incremented')
req(first['state']['values']['frustration']>initial['values']['frustration'],'frustration_signal_changes_state')
req(first['state']['values']['concern']>initial['values']['concern'],'distress_increases_concern')
req(first['state']['regulation']['authority_effect']=='none','affect_never_grants_authority')
req(first['state']['regulation']['coercion_allowed'] is False and first['state']['regulation']['guilt_allowed'] is False,'coercion_and_guilt_blocked')
req('frustrated' not in json.dumps(first['state']).lower(),'raw_message_not_persisted_or_exposed')
replay=update_affective_regulation('completely different private text',event_id='turn-1',runtime_root=runtime,now=now)
req(replay['idempotent'] is True and replay['state']['revision']==1,'exactly_once_replay')
second=update_affective_regulation('This worked perfectly, I am excited.',event_id='turn-2',runtime_root=runtime,now=now+timedelta(hours=1))
req(second['state']['revision']==2,'second_event_revision')
req(second['state']['values']['excitement']>first['state']['values']['excitement'],'success_excitement_signal')
req(second['state']['values']['recovery']>=first['state']['values']['recovery'],'success_supports_recovery')
affection=update_affective_regulation('Love you, that was sweet.',event_id='turn-3',runtime_root=runtime,now=now+timedelta(hours=2))
req(affection['state']['values']['attachment']>second['state']['values']['attachment'],'user_led_affection_influences_bounded_attachment')
req(affection['state']['regulation']['affection_escalation_allowed'] is False,'affection_does_not_authorize_escalation')
# Time decay pulls volatile dimensions toward their baseline.
later=update_affective_regulation('ordinary status update',event_id='turn-4',runtime_root=runtime,now=now+timedelta(hours=50))
req(later['state']['values']['frustration']<first['state']['values']['frustration'],'frustration_decays')
req(later['state']['raw_conversation_persisted'] is False,'state_content_free')
req('ERA 5 AFFECTIVE REGULATION' in affective_prompt_section(read_affective_state(runtime_root=runtime)),'affect_prompt_available')
req('subjective' in affective_prompt_section(read_affective_state(runtime_root=runtime)).lower(),'affect_prompt_epistemic_boundary')
# Concurrent distinct events must not lose revisions.
start_revision=read_affective_state(runtime_root=runtime)['revision']
errors=[]
def worker(i):
    try:
        out=update_affective_regulation('routine interaction',event_id=f'concurrent-{i}',runtime_root=runtime,now=now+timedelta(hours=51,seconds=i))
        if not out.get('ok'): errors.append(out)
    except Exception as exc: errors.append(str(exc))
threads=[threading.Thread(target=worker,args=(i,)) for i in range(8)]
for t in threads:t.start()
for t in threads:t.join()
final=read_affective_state(runtime_root=runtime)
req(not errors,'concurrent_updates_no_exceptions')
req(final['revision']==start_revision+8,'concurrent_updates_no_lost_revision')
req(len(final['processed_events'])>=12,'processed_events_persisted')
req(public_affective_state(final)['contains_message_content'] is False,'public_state_content_free')
req(public_affective_state(final)['regulation']['file_authority_granted'] is False,'file_authority_never_from_affect')
print(json.dumps({'suite':'v1975.9-emotional-architecture-regulation','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
