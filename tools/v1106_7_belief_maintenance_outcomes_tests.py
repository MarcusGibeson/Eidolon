from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.json_storage import write_json_atomic
from conscious_agent.belief_revision import BeliefRevisionStore
from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
from conscious_agent.bounded_reconsideration_reflection import BoundedReconsiderationReflection
from conscious_agent.belief_maintenance_outcomes import BeliefMaintenanceOutcomes

def run():
 p=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition'; beliefs=BeliefRevisionStore(root);b=beliefs.record_belief('b-create',proposition='A provisional belief',confidence=.8,origin_type='test',origin_ref='fixture')['result']['belief_id']
  sched=KnowledgeReconsiderationScheduler(root);s=sched._load();s['schedules']=[{'schedule_id':'s1','subject_type':'belief','subject_id':b,'pressure':.9,'status':'scheduled','due_at':'2020-01-01T00:00:00Z'}];write_json_atomic(sched.path,s,expected_type=dict,sort_keys=True)
  refs=BoundedReconsiderationReflection(root,scheduler=sched,beliefs=beliefs);refs.reflect('r1',schedule_id='s1',conclusion='New evidence weakens the earlier confidence.')
  out=BeliefMaintenanceOutcomes(root,beliefs=beliefs,scheduler=sched,reflections=refs)
  a=out.apply('o1',schedule_id='s1',outcome='revise',conclusion='Confidence was revised downward.',new_confidence=.35)
  snap=beliefs.snapshot();row=next(x for x in snap['beliefs'] if x['belief_id']==b)
  p += [('outcome_recorded',a['status']=='belief_maintenance_outcome_recorded'),('revised',row['confidence']<=.35),('uncertainty_explicit',row['uncertainty']>=.5),('history_accountable',row['update_history'][-1]['event']=='maintenance_outcome'),('reflection_linked',bool(a['result']['reflection_id'])),('no_authority',a['result']['action_authorized'] is False),('not_executed',a['result']['action_executed'] is False)]
  d=out.apply('o1',schedule_id='s1',outcome='retain',conclusion='duplicate');p.append(('deduplicated',d['idempotent'] is True))
  p.append(('restart_persistence',BeliefMaintenanceOutcomes(root).inspection_summary()['outcome_count']==1))
  try: out.apply('o2',schedule_id='missing',outcome='retain',conclusion='x');bad=False
  except KeyError: bad=True
  p.append(('missing_schedule_rejected',bad));p.append(('provider_free',out.inspection_summary()['provider_contacted'] is False))
 return p
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');
 r=run();print(json.dumps({'ok':all(v for _,v in r),'passed':sum(v for _,v in r),'total':len(r),'checks':[{'name':n,'passed':v} for n,v in r]}));raise SystemExit(0 if all(v for _,v in r) else 1)
