from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'));sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2025-data-')
from attention_salience_focus_v2000 import score_salience_candidates, choose_focus, update_focus_control, read_focus_state, public_focus_state
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2025-runtime-'))
D='a'*64
rows=[
 {'candidate_id':'conversation:blocking','evidence_digest':D,'provenance':'conversation','urgency':.9,'importance':.9,'novelty':.5,'emotional_relevance':.7,'risk':.8,'deadline_pressure':.4,'operator_priority':1.0,'freshness':1,'uncertainty':.1},
 {'candidate_id':'maintenance:easy','evidence_digest':'b'*64,'provenance':'maintenance','urgency':.2,'importance':.4,'novelty':.3,'emotional_relevance':0,'risk':.2,'deadline_pressure':.1,'operator_priority':.1,'freshness':1,'uncertainty':.05},
]
scored=score_salience_candidates(rows,runtime_root=runtime,now=datetime(2026,8,23,tzinfo=timezone.utc))
req(scored['ok'] and scored['candidate_count']==2,'salience_scores_candidates')
req(scored['candidates'][0]['candidate_id']=='conversation:blocking','high_value_item_outranks_easy_maintenance')
req(all(name in scored['candidates'][0]['factors'] for name in ('urgency','importance','novelty','emotional_relevance','risk','deadline_pressure','operator_priority')),'all_required_factors_present')
req(scored['raw_content_retained'] is False and scored['work_executed'] is False,'salience_content_free_nonexecuting')
first=choose_focus(rows,event_id='cycle-1',runtime_root=runtime)
req(first['ok'] and first['status']=='focus_shifted','focus_selected')
req(first['state']['active_focus']['candidate_id']=='conversation:blocking','correct_focus_owned')
replay=choose_focus(rows,event_id='cycle-1',runtime_root=runtime)
req(replay['status']=='focus_selection_replayed' and replay['idempotent'] is True,'focus_exactly_once')
state=public_focus_state(read_focus_state(runtime_root=runtime))
defer=update_focus_control('defer',candidate_id='conversation:blocking',expected_state_digest=state['state_digest'],event_id='defer-1',runtime_root=runtime)
req(defer['ok'] and 'conversation:blocking' in defer['state']['deferred_candidate_ids'],'digest_bound_defer')
req(defer['state']['active_focus'] is None,'defer_releases_focus')
stale=update_focus_control('resume',candidate_id='conversation:blocking',expected_state_digest=state['state_digest'],event_id='resume-stale',runtime_root=runtime)
req(stale['status']=='stale_focus_state_digest','stale_control_rejected')
next_pick=choose_focus(rows,event_id='cycle-2',runtime_root=runtime)
req(next_pick['state']['active_focus']['candidate_id']=='maintenance:easy','deferred_candidate_not_selected')
current=public_focus_state(read_focus_state(runtime_root=runtime))
resume=update_focus_control('resume',candidate_id='conversation:blocking',expected_state_digest=current['state_digest'],event_id='resume-1',runtime_root=runtime)
req(resume['ok'] and 'conversation:blocking' not in resume['state']['deferred_candidate_ids'],'resume_control')
# Anti-fixation penalizes repeated normal focus but exempts genuine urgent/risky/operator work.
normal=[{'candidate_id':'normal','evidence_digest':'c'*64,'provenance':'test','urgency':.5,'importance':.7,'novelty':.5,'emotional_relevance':.2,'risk':.4,'deadline_pressure':.2,'operator_priority':.3,'freshness':1,'uncertainty':0}]
for i in range(4): choose_focus(normal,event_id=f'fix-{i}',runtime_root=runtime)
fix=score_salience_candidates(normal,runtime_root=runtime)['candidates'][0]
req(fix['fixation_penalty']>0 and fix['fixation_exempt'] is False,'anti_fixation_penalty_applied')
urgent=[dict(normal[0],candidate_id='urgent',evidence_digest='d'*64,urgency=.95,risk=.9)]
for i in range(4): choose_focus(urgent,event_id=f'urgent-{i}',runtime_root=runtime)
ur=score_salience_candidates(urgent,runtime_root=runtime)['candidates'][0]
req(ur['fixation_penalty']==0 and ur['fixation_exempt'] is True,'urgent_work_fixation_exempt')
req(first['installation_authorized'] is False and first['authority_expanded'] is False,'focus_never_grants_authority')
print(json.dumps({'suite':'v2025.9-attention-salience','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
