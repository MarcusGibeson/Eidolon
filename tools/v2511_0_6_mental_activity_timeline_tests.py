from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline
from conscious_agent.mental_activity_projection_v2511 import cognitive_transition,background_transition,memory_transition,self_model_transition,planning_transition,action_transition
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
with tempfile.TemporaryDirectory() as td:
 t=MentalActivityTimeline(td)
 fixtures=[
  (cognitive_transition({'status':'awaiting_cognitive_work','selected_operation':'REFLECT'}),'cog'),
  (background_transition({'status':'suppressed','selected_operation':'PLAN'}),'bg'),
  (memory_transition({'candidate_type':'PROCEDURAL_LESSON_REVIEW'}),'mem'),
  (self_model_transition({'trait_code':'verification_scope_bias'}),'self'),
  (planning_transition({'health_state':'replan_required'}),'plan'),
  (action_transition({'proposal_ready':True,'capability_id':'calendar.create'}),'action'),
 ]
 for (kind,transition,outcome),eid in fixtures:
  r=t.append(eid,event_kind=kind,transition=transition,source_digest=d(eid),subject_ref='subject-digest:'+d(eid)[:16],outcome_code=outcome)
  req(r['ok'],f'append_{eid}')
  req(not r['event']['hidden_reasoning_exposed'] and not r['event']['raw_content_stored'],f'private_{eid}')
 req(t.recent(limit=20)['event_count']==6,'six_events')
 req(t.recent(limit=20,kind='planning')['event_count']==1,'kind_filter')
 req(t.inspection_summary()['sequence']==6,'monotonic_sequence')
 req(not t.inspection_summary()['authority_boundary']['can_execute_action'],'no_action_authority')
 replay=t.append('cog',event_kind='cognitive',transition='cycle_started',source_digest=d('cog'))
 req(replay['idempotent'],'idempotent')
 req(t.inspection_summary()['event_count']==6,'replay_not_duplicate')
print({'ok':True,'passed':len(checks),'total':len(checks),'checks':checks})
