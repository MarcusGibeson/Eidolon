from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.autonomous_attention_agenda import AutonomousAttentionAgenda
from conscious_agent.motivation_agenda_arbitration import MotivationAgendaArbitrator
from conscious_agent.agenda_guided_reflection import AgendaGuidedReflection
from conscious_agent.bounded_intention_formation import BoundedIntentionStore
def req(v,d='failed'):
 if not v:raise AssertionError(d)
def eligible():
 root=Path(tempfile.mkdtemp())/'runtime'/'cognition';clock=lambda:'2026-07-27T12:00:00.000Z';a=AutonomousAttentionAgenda(root,clock=clock);arb=MotivationAgendaArbitrator(root,agenda=a,clock=clock,epoch_clock=lambda:1e5);a.upsert_candidate('a',origin_type='motivation',origin_ref='m',subject='private',subject_key='m',salience=1,urgency=1,uncertainty=.5,confidence=.5);sel=arb.arbitrate('s',arbitration_key='s',gather_candidates=False,quiet=False,minimum_score=.1);r=AgendaGuidedReflection(root,clock=clock);i=r.intake('i',receipt_id=sel['result']['receipt_id'],eligible_for_intention=True);return root,i['result']['intake_id']
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','detail':repr(e)})
 def forms():
  root,i=eligible();s=BoundedIntentionStore(root);x=s.form('f',intake_id=i,intention_kind='reflect_further');req(x['status']=='intention_formed',x);q=s.snapshot()['intentions'][0];req(q['proposal_id']==q['authorized_action_id']==q['completed_action_id']=='',q)
 def rejects_ineligible():
  root=Path(tempfile.mkdtemp())/'runtime'/'cognition';x=BoundedIntentionStore(root).form('f',intake_id='missing');req(x['status']=='intention_not_formed',x)
 def dedup():
  root,i=eligible();s=BoundedIntentionStore(root);x=s.form('a',intake_id=i);y=BoundedIntentionStore(root).form('b',intake_id=i);req(x['result']['intention_id']==y['result']['intention_id'] and y['status']=='duplicate_intention_ignored',(x,y))
 def separation():
  root,i=eligible();s=BoundedIntentionStore(root);s.form('f',intake_id=i);q=s.inspection_summary();req(all(v is False for v in q['state_separation'].values()),q);req(not any(q['authority_boundary'].values()),q)
 for n,f in [('form_non_authorizing_intention',forms),('reject_ineligible',rejects_ineligible),('semantic_dedup',dedup),('state_separation',separation)]:run(n,f)
 return rows
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();out={'suite':'v1107.4-bounded-intention-formation','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
