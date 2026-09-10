from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.reconsideration_conversation_continuity import ReconsiderationConversationBridge
from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
from conscious_agent.persistent_motivation import MotivationStore
from conscious_agent.self_directed_inquiry import InquiryWorkspace
from conscious_agent.proactive_communication import ProactiveCommunicationStore

def req(v,d='failed'):
 if not v:raise AssertionError(d)
def fix():
 b=Path(tempfile.mkdtemp());r=b/'runtime'/'cognition';m=MotivationStore(r);mid=m.record_motivation('m',kind='curiosity',summary='reconsider',cognitive_state='desire',urgency=.9,confidence=.8,origin_type='fixture',origin_ref='v1106.5')['result']['motivation_id'];InquiryWorkspace(r,motivation_store=m).create_inquiry('q',motivation_id=mid,question='Review?',uncertainty=.95);s=KnowledgeReconsiderationScheduler(r);x=s.schedule_from_checkpoint('s',now='2026-01-01T00:00:00Z');return b,r,s,x['result']['schedule_ids'][0]
def tests():
 out=[]
 def run(n,f):
  try:f();out.append({'name':n,'status':'pass'})
  except Exception as e:out.append({'name':n,'status':'fail','detail':repr(e)})
 def communicate():
  b,r,s,sid=fix();x=ReconsiderationConversationBridge(r,scheduler=s,epoch_clock=lambda:2000000000).consider('c',schedule_id=sid,conclusion='The belief changed after correction.',changed_belief=True);req(x['result']['decision'] in {'communicate','silence'})
 def duplicate():
  b,r,s,sid=fix();q=ReconsiderationConversationBridge(r,scheduler=s,epoch_clock=lambda:2000000000);q.consider('c',schedule_id=sid,conclusion='Changed.');req(q.consider('c',schedule_id=sid,conclusion='Changed.')['idempotent'])
 def quiet():
  b,r,s,sid=fix();p=ProactiveCommunicationStore(r);p.set_preferences('q',quiet_indefinite=True);x=ReconsiderationConversationBridge(r,scheduler=s,communication=p,epoch_clock=lambda:2000000000).consider('c',schedule_id=sid,conclusion='Changed.');req(x['result']['decision']=='silence')
 def disabled():
  b,r,s,sid=fix();p=ProactiveCommunicationStore(r);p.set_preferences('q',initiative_enabled=False);x=ReconsiderationConversationBridge(r,scheduler=s,communication=p,epoch_clock=lambda:2000000000).consider('c',schedule_id=sid,conclusion='Changed.');req(x['result']['decision']=='silence')
 def unread():
  b,r,s,sid=fix();p=ProactiveCommunicationStore(r);bridge=ReconsiderationConversationBridge(r,scheduler=s,communication=p,epoch_clock=lambda:2000000000);bridge.consider('a',schedule_id=sid,conclusion='First.');x=bridge.consider('b',schedule_id=sid,conclusion='Second.');req(x['result']['decision']=='silence')
 def restart():
  b,r,s,sid=fix();ReconsiderationConversationBridge(r,scheduler=s,epoch_clock=lambda:2000000000).consider('c',schedule_id=sid,conclusion='Changed.');req(ReconsiderationConversationBridge(r,scheduler=s).inspection_summary()['decision_count']==1)
 def no_action():
  b,r,s,sid=fix();x=ReconsiderationConversationBridge(r,scheduler=s,epoch_clock=lambda:2000000000).consider('c',schedule_id=sid,conclusion='Changed.');req(x['result']['action_authorized'] is False and x['result']['action_executed'] is False)
 def provider():
  b,r,s,sid=fix();req(ReconsiderationConversationBridge(r,scheduler=s).inspection_summary()['provider_contacted'] is False)
 def browse():
  b,r,s,sid=fix();req(ReconsiderationConversationBridge(r,scheduler=s).inspection_summary()['external_browsing_performed'] is False)
 def missing():
  b,r,s,sid=fix();
  try:ReconsiderationConversationBridge(r,scheduler=s).consider('c',schedule_id='missing',conclusion='x')
  except KeyError:return
  raise AssertionError('missing accepted')
 def empty():
  b,r,s,sid=fix();
  try:ReconsiderationConversationBridge(r,scheduler=s).consider('c',schedule_id=sid,conclusion='')
  except ValueError:return
  raise AssertionError('empty accepted')
 def safeguards():
  b,r,s,sid=fix();q=ReconsiderationConversationBridge(r,scheduler=s).inspection_summary();req(q['authority_boundary']['can_bypass_quiet'] is False and q['communication']['continuity_preserved'] is True)
 for n,f in [('communicate',communicate),('duplicate',duplicate),('quiet',quiet),('disabled',disabled),('unread',unread),('restart',restart),('no_action',no_action),('provider',provider),('browse',browse),('missing',missing),('empty',empty),('safeguards',safeguards)]:run(n,f)
 return out
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();x={'passed':sum(r['status']=='pass' for r in rows),'total':len(rows),'tests':rows};print(json.dumps(x,indent=2));raise SystemExit(0 if x['passed']==x['total'] else 1)
