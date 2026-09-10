from __future__ import annotations
import json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'conscious_agent'))
from natural_language_action_routing import build_natural_language_action_projection
from action_proposal_handoff import MAX_HANDOFF_BYTES, build_action_proposal_handoff

checks=[]
def req(name, cond, detail=''):
    checks.append((name,bool(cond),detail))
    if not cond: raise AssertionError(f'{name}: {detail}')

def make(text, **kw):
    return build_action_proposal_handoff(build_natural_language_action_projection(text), **kw)

for text,cap in [('Run diagnostics.','diagnostics'),('Do a system maintenance check.','maintenance'),('Review conscious_agent/memory.py.','file_review'),('Change the dashboard background.','patch_proposal')]:
    row=make(text,operation_id='op-1')
    req(cap+' ready',row['proposal']['proposal_state']=='ready_for_operator_review',row)
    req(cap+' real',row['proposal']['capability_id']==cap,row)
    req(cap+' no persist',not row['proposal']['persisted'],row)
    req(cap+' no approve',not row['approval_handoff']['approval_created'],row)
    req(cap+' no execute',not row['execution_admission']['executed'],row)

for text in ['Do you like the name Eidolon?','Stop calling me Daddy.','Maybe run diagnostics?','Install a new model.','Go ahead.']:
    row=make(text)
    req(text+' not ready',row['proposal']['proposal_state']=='not_ready',row)
    req(text+' not admitted',not row['execution_admission']['admitted'],row)

base=make('Run diagnostics.', explicit_control_text='I explicitly approve diagnostics')
req('phrase alone no approval',not base['approval_handoff']['approval_granted'],base)
req('phrase alone no persisted evidence',not base['approval_handoff']['persisted_proposal_verified'],base)
req('exact ref seen',base['approval_handoff']['exact_capability_reference'],base)

persisted={'persisted':True,'capability_id':'diagnostics','proposal_digest':'a'*64,'proposal_state':'proposed'}
controlled=make('Run diagnostics.',explicit_control_text='execute diagnostics',persisted_proposal=persisted)
req('persisted verified',controlled['approval_handoff']['persisted_proposal_verified'],controlled)
req('still not admitted',not controlled['execution_admission']['admitted'],controlled)
req('still not executed',not controlled['execution_admission']['executed'],controlled)

mismatch=make('Run diagnostics.',explicit_control_text='execute maintenance',persisted_proposal=persisted)
req('mismatch refused',not mismatch['execution_admission']['exact_capability_reference'],mismatch)

runtime=(ROOT/'conscious_agent'/'conversation_runtime.py').read_text()
req('stream parity build',runtime.count('build_action_proposal_handoff(action_projection, operation_id=operation_id)')==2)
req('stream parity public',runtime.count('action_proposal_handoff_public(action_handoff)')==2)
req('stream parity prompt',runtime.count('action_proposal_handoff_prompt(action_handoff)')==2)

rows=[]
for _ in range(100):
    t=time.perf_counter(); row=make('Run diagnostics.',operation_id='latency'); rows.append((time.perf_counter()-t)*1000)
req('p95 under 20ms',sorted(rows)[94]<20,sorted(rows)[94])
encoded=json.dumps(row,sort_keys=True,separators=(',',':')).encode()
req('bounded',len(encoded)<=MAX_HANDOFF_BYTES,len(encoded))
req('content free',row['diagnostics']['content_free'],row)
req('registry reused',row['diagnostics']['existing_registry_reused'],row)
req('no new registry',not row['diagnostics']['new_tool_registry_created'],row)
summary={'ok':all(x[1] for x in checks),'suite':'v1175.3-v1175.5-action-proposal-handoff-foundations','passed':sum(x[1] for x in checks),'total':len(checks),'p95_ms':round(sorted(rows)[94],4),'proposal_persisted':False,'approval_created':False,'execution_performed':False}
print(json.dumps(summary,sort_keys=True))
