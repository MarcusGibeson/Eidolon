from __future__ import annotations
import hashlib,json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1298-'))
from repeated_self_maintenance_foundations import *
from repeated_self_maintenance import *
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
def d(x):return hashlib.sha256(str(x).encode()).hexdigest()
def emit(state,etype,*,test_passed=None,new=0,opened=None,final=''):
 c=state['active_cycle'];e=maintenance_event(c,sequence=c['next_sequence'],event_type=etype,evidence_digest=d((c['cycle_index'],etype,c['next_sequence'])),source_digest=c['source_digest_at_start'],prior_event_digest=c['prior_event_digest'],test_passed=test_passed,new_proposal_count=new,open_proposal_count=opened,final_source_digest=final);return apply_maintenance_event(state,e)
def run_cycle(state,work,final,*,fail_once=False,new=1):
 state=start_cycle(state,work_item_digest=d(work),current_source_digest=state['current_source_digest'])
 state=emit(state,'inspection_complete');state=emit(state,'backlog_complete',new=new,opened=min(state['max_open_proposals'],state['open_proposal_count']+new));state=emit(state,'priority_selected');state=emit(state,'plan_complete');state=emit(state,'build_complete')
 if fail_once:
  state=emit(state,'test_result',test_passed=False);state=emit(state,'repair_complete')
 state=emit(state,'test_result',test_passed=True);state=emit(state,'review_complete',final=d(final));return state
s=create_maintenance_session(objective_digest=d('objective'),initial_source_digest=d('s0'),max_cycles=4,max_open_proposals=5,max_new_proposals_per_cycle=2);s=run_cycle(s,'w1','s1');req(len(s['cycles'])==1 and s['current_source_digest']==d('s1'),'cycle1');s=run_cycle(s,'w2','s2',fail_once=True);req(s['cycles'][1]['test_failures']==1 and s['cycles'][1]['repair_count']==1,'repair_cycle');s=run_cycle(s,'w3','s3');summary=maintenance_summary(s);req(summary['completed_cycle_count']==3,'three_cycles');req(summary['repair_count']==1 and summary['test_failure_count']==1,'repair_summary');req(not summary['duplicate_work_detected'],'no_duplicate');req(summary['current_source_digest']==d('s3'),'lineage');req(summary['open_proposal_count']<=s['max_open_proposals'],'bounded_proposals');req(not any(summary[k] for k in DENIED_AUTHORITY),'authority')
try:start_cycle(s,work_item_digest=d('w2'),current_source_digest=d('s3'));dup=False
except ValueError:dup=True
req(dup,'duplicate_blocked')
# proposal explosion blocked
x=create_maintenance_session(objective_digest=d('o2'),initial_source_digest=d('x0'),max_cycles=2,max_open_proposals=2,max_new_proposals_per_cycle=1);x=start_cycle(x,work_item_digest=d('xw'),current_source_digest=d('x0'));x=emit(x,'inspection_complete');c=x['active_cycle'];e=maintenance_event(c,sequence=c['next_sequence'],event_type='backlog_complete',evidence_digest=d('boom'),source_digest=c['source_digest_at_start'],prior_event_digest=c['prior_event_digest'],new_proposal_count=2,open_proposal_count=2);blocked=apply_maintenance_event(x,e);req(blocked['status']=='maintenance_blocked' and blocked['block_reason']=='proposal_growth_budget_exceeded','growth_block')
# replay blocked
r=create_maintenance_session(objective_digest=d('o3'),initial_source_digest=d('r0'),max_cycles=2);r=start_cycle(r,work_item_digest=d('rw'),current_source_digest=d('r0'));c=r['active_cycle'];ev=maintenance_event(c,sequence=1,event_type='inspection_complete',evidence_digest=d('r1'),source_digest=d('r0'));r2=apply_maintenance_event(r,ev);replay=apply_maintenance_event(r2,ev);req(replay['block_reason']=='stale_or_replayed_sequence','replay')
print(json.dumps({'suite':'v1298.3-v1298.5-repeated-self-maintenance-integration','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
