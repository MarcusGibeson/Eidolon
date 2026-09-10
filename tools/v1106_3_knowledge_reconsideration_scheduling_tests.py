from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace

def req(v,d='failed'):
 if not v:raise AssertionError(d)
def fix():
 b=Path(tempfile.mkdtemp());r=b/'runtime'/'cognition';m=MotivationStore(r);mid=m.record_motivation('m',kind='curiosity',summary='aging question',cognitive_state='desire',urgency=.8,confidence=.8,origin_type='fixture',origin_ref='v1106.3')['result']['motivation_id'];w=InquiryWorkspace(r,motivation_store=m);w.create_inquiry('q',motivation_id=mid,question='What remains?',uncertainty=.95);return b,r
def tests():
 out=[]
 def run(n,f):
  try:f();out.append({'name':n,'status':'pass'})
  except Exception as e:out.append({'name':n,'status':'fail','detail':repr(e)})
 def creates():
  b,r=fix();x=KnowledgeReconsiderationScheduler(r).schedule_from_checkpoint('e',now='2026-07-27T00:00:00Z');req(x['result']['created_count']>=1)
 def duplicate():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.schedule_from_checkpoint('e');x=s.schedule_from_checkpoint('e');req(x['idempotent'])
 def semantic_dedup():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.schedule_from_checkpoint('a');x=s.schedule_from_checkpoint('b');req(x['result']['created_count']==0)
 def due():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.schedule_from_checkpoint('a',now='2026-01-01T00:00:00Z');req(len(s.due(now='2027-01-01T00:00:00Z'))>=1)
 def bounded():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.schedule_from_checkpoint('a',max_items=1);req(len(s.snapshot()['schedules'])<=1)
 def pause():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.set_paused('p',paused=True);x=s.schedule_from_checkpoint('a');req(x['status']=='scheduling_paused')
 def complete():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);x=s.schedule_from_checkpoint('a');sid=x['result']['schedule_ids'][0];req(s.complete('c',schedule_id=sid,outcome='reviewed')['result']['status']=='reconsideration_completed')
 def restart():
  b,r=fix();s=KnowledgeReconsiderationScheduler(r);s.schedule_from_checkpoint('a');req(KnowledgeReconsiderationScheduler(r).inspection_summary()['scheduled_count']==1)
 def provider():
  b,r=fix();q=KnowledgeReconsiderationScheduler(r).inspection_summary();req(q['provider_contacted'] is False and q['external_browsing_performed'] is False)
 def authority():
  b,r=fix();q=KnowledgeReconsiderationScheduler(r).inspection_summary();req(q['authority_boundary']['can_authorize_action'] is False and q['authority_boundary']['can_execute_action'] is False)
 for n,f in [('creates',creates),('duplicate',duplicate),('semantic_dedup',semantic_dedup),('due',due),('bounded',bounded),('pause',pause),('complete',complete),('restart',restart),('provider',provider),('authority',authority)]:run(n,f)
 return out
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();x={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(x,indent=2));raise SystemExit(0 if x['passed']==x['total'] else 1)
