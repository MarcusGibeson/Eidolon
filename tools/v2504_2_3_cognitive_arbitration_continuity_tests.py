from __future__ import annotations
import sys,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
from conscious_agent.unified_cognitive_state_frame import build_unified_cognitive_state_frame
from conscious_agent.cognitive_operation_arbitration import arbitrate_cognitive_operation
from conscious_agent.cognitive_thought_continuity import CognitiveThoughtContinuityStore
checks=[]
def req(v,n):checks.append(n);assert v,n
with tempfile.TemporaryDirectory(prefix='eidolon-v2504-2-3-') as td:
 root=Path(td);frame=build_unified_cognitive_state_frame(root)
 idle=arbitrate_cognitive_operation(frame);req(idle['ok'],'idle_ok');req(idle['selected_operation']=='REST','empty_state_rests');req(idle['deliberate_inactivity'],'rest_explicit')
 thought=arbitrate_cognitive_operation(frame,unfinished_thought_count=1);req(thought['selected_operation']=='CONTINUE_THOUGHT','unfinished_resumes')
 experience=arbitrate_cognitive_operation(frame,new_experience=True);req(experience['selected_operation']=='INTEGRATE_EXPERIENCE','experience_integrates')
 req(not thought['provider_contacted'] and not thought['external_action_executed'],'arbitration_nonexecuting')
 store=CognitiveThoughtContinuityStore(root);r=store.record('evt-1',operation='reflect',subject_ref='subject-1',frame_digest=frame['frame_digest'],progress_marker='stage-1',next_step='reconsider evidence')
 req(r['ok'] and r['thought_status']=='unfinished','thought_recorded');dup=store.record('evt-1',operation='reflect',subject_ref='subject-1',frame_digest=frame['frame_digest']);req(dup['idempotent'],'event_idempotent')
 s=store.inspection_summary();req(s['active_count']==1,'active_one');req(not s['raw_chain_of_thought_stored'],'no_chain_of_thought')
 r2=store.record('evt-2',operation='reflect',subject_ref='subject-1',frame_digest=frame['frame_digest'],status='completed');req(r2['thought_status']=='completed','thought_completed')
 req(store.inspection_summary()['active_count']==0,'completion_clears_active');req(not store.inspection_summary()['authority_boundary']['can_execute_action'],'continuity_no_authority')
print(json.dumps({'ok':True,'contract':'v2504.2-v2504.3','passed':len(checks),'checks':checks},sort_keys=True))
