from __future__ import annotations
"""v1309 idempotent goal lifecycle."""
from typing import Mapping
from cognitive_coding_foundations import DENIED_AUTHORITY,digest
CONTRACT_VERSION='v1309.8';TRANSITIONS={'draft':{'start':'active','abandon':'abandoned'},'active':{'pause':'paused','revise':'active','complete':'completed','abandon':'abandoned'},'paused':{'resume':'active','revise':'paused','abandon':'abandoned'},'recovering':{'resume':'active','abandon':'abandoned'}}
def transition_goal(goal:Mapping,action:str,*,event_id:str):
 row=dict(goal);events=list(row.get('lifecycle_events') or []);eid=digest(str(event_id))
 if any(x.get('event_id_digest')==eid for x in events):return row
 state=str(row.get('state') or 'draft');a=str(action)
 if a=='recover_after_crash' and state in {'active','paused'}:new='recovering'
 else:new=TRANSITIONS.get(state,{}).get(a)
 if not new:raise ValueError('goal_transition_invalid')
 row['state']=new;events.append({'event_id_digest':eid,'from':state,'action':a,'to':new});row['lifecycle_events']=events[-64:];row['goal_digest']=digest({k:v for k,v in row.items() if k!='goal_digest'});return row
__all__=['CONTRACT_VERSION','TRANSITIONS','transition_goal']
