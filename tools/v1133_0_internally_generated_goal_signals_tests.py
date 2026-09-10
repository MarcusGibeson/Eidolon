from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_signals import InternallyGeneratedGoalSignalStore

def main():
 with TemporaryDirectory() as d:
  s=InternallyGeneratedGoalSignalStore(Path(d))
  a=s.register('e1',origin_ids=['m1'],source_categories=['motivation'],purpose_category='project_progress',evidence_ids=['ev1'],importance=.8,expected_value=.7,scope_digest='a'*64)
  assert a['ok'] and a['result']['state']=='active'
  b=s.register('e2',origin_ids=['m2'],source_categories=['motivation'],purpose_category='project_progress',evidence_ids=['ev2'],importance=.1,urgency=.95,expected_value=.1)
  assert b['result']['state']=='suppressed'
  assert s.register('e1',origin_ids=['m1'],source_categories=['motivation'],purpose_category='project_progress',evidence_ids=['ev1'])['idempotent']
  out=s.inspection_summary(); assert out['signal_count']==2 and not any(out['authority_boundary'].values()) and not out['goal_text_exposed']
 print('v1133.0: 8/8')
if __name__=='__main__': main()
