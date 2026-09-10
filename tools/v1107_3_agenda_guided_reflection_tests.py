from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.autonomous_attention_agenda import AutonomousAttentionAgenda
from conscious_agent.motivation_agenda_arbitration import MotivationAgendaArbitrator
from conscious_agent.agenda_guided_reflection import AgendaGuidedReflection

def req(v,d='failed'):
 if not v:raise AssertionError(d)
def fixture():
 root=Path(tempfile.mkdtemp())/'runtime'/'cognition';clock=lambda:'2026-07-27T12:00:00.000Z';a=AutonomousAttentionAgenda(root,clock=clock);arb=MotivationAgendaArbitrator(root,agenda=a,clock=clock,epoch_clock=lambda:100000.0);r=AgendaGuidedReflection(root,clock=clock);return root,a,arb,r
def selected():
 root,a,arb,r=fixture();a.upsert_candidate('a',origin_type='inquiry',origin_ref='q',subject='private subject',subject_key='q',salience=1,urgency=1,uncertainty=.8,confidence=.2);x=arb.arbitrate('s',arbitration_key='s',gather_candidates=False,quiet=False,minimum_score=.1);return root,r,x['result']['receipt_id']
def tests():
 rows=[]
 def run(n,f):
  try:f();rows.append({'name':n,'status':'pass'})
  except Exception as e:rows.append({'name':n,'status':'fail','detail':repr(e)})
 def one_step():
  _,r,rid=selected();x=r.intake('i',receipt_id=rid,outcome='continue_attention',reflection_summary='bounded conclusion',eligible_for_intention=True);req(x['status']=='reflection_intake_recorded',x);q=r.snapshot()['intakes'][0];req(q['reflection_step_count']==1 and q['summary_digest'] and 'bounded conclusion' not in json.dumps(q),q)
 def silence_missing():
  _,_,_,r=fixture();x=r.intake('i',receipt_id='missing',outcome='deliberate_silence');req(x['status']=='deliberate_no_intake',x)
 def dedup_restart():
  root,r,rid=selected();x=r.intake('i',receipt_id=rid);y=AgendaGuidedReflection(root).intake('i2',receipt_id=rid);req(x['result']['intake_id']==y['result']['intake_id'] and y['status']=='duplicate_intake_ignored',(x,y))
 def no_authority():
  _,r,rid=selected();r.intake('i',receipt_id=rid,eligible_for_intention=True);q=r.inspection_summary();req(q['provider_contacted'] is False and q['external_browsing_performed'] is False and q['action_authority_changed'] is False,q)
 for n,f in [('one_step_privacy',one_step),('deliberate_no_intake',silence_missing),('restart_dedup',dedup_restart),('authority_boundary',no_authority)]:run(n,f)
 return rows
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');rows=tests();out={'suite':'v1107.3-agenda-guided-reflection','passed':sum(x['status']=='pass' for x in rows),'total':len(rows),'tests':rows};print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed']==out['total'] else 1)
