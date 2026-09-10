from __future__ import annotations
import argparse,json,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from conscious_agent.knowledge_reconsideration_scheduling import KnowledgeReconsiderationScheduler
from conscious_agent.bounded_reconsideration_reflection import BoundedReconsiderationReflection

def run():
 p=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)/'cognition'; sched=KnowledgeReconsiderationScheduler(root)
  s=sched._load();s['schedules']=[{'schedule_id':'s1','subject_type':'belief','subject_id':'b1','pressure':.9,'status':'scheduled','due_at':'2020-01-01T00:00:00Z'}];from conscious_agent.json_storage import write_json_atomic;write_json_atomic(sched.path,s,expected_type=dict,sort_keys=True)
  r=BoundedReconsiderationReflection(root,scheduler=sched)
  a=r.reflect('e1',schedule_id='s1',conclusion='The belief should be reconsidered because its support changed.')
  p += [('reflection_created',a['status']=='reconsideration_reflected'),('bounded_one',r.inspection_summary()['reflection_count']==1),('concise',len(a['result']['authored_conclusion'])<=420),('no_cot',a['result']['raw_chain_of_thought_stored'] is False),('provider_free',a['result']['provider_contacted'] is False),('no_authority',a['result']['action_authorized'] is False)]
  d=r.reflect('e1',schedule_id='s1',conclusion='duplicate');p.append(('deduplicated',d['idempotent'] is True))
  z=r.reflect('e2',schedule_id='s1',select_silence=True);p += [('silence_valid',z['result']['silence'] is True),('silence_not_stored',r.inspection_summary()['reflection_count']==1)]
  n=BoundedReconsiderationReflection(root,scheduler=sched).inspection_summary();p.append(('restart_persistence',n['reflection_count']==1))
 return p
if __name__=='__main__':
 argparse.ArgumentParser().add_argument('--json',action='store_true');
 r=run();print(json.dumps({'ok':all(v for _,v in r),'passed':sum(v for _,v in r),'total':len(r),'checks':[{'name':n,'passed':v} for n,v in r]}));raise SystemExit(0 if all(v for _,v in r) else 1)
