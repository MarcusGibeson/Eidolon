from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_signals import InternallyGeneratedGoalSignalStore
from conscious_agent.internally_generated_goal_candidates import InternallyGeneratedGoalCandidateStore

def main():
 with TemporaryDirectory() as d:
  r=Path(d); s=InternallyGeneratedGoalSignalStore(r); c=InternallyGeneratedGoalCandidateStore(r)
  sid=s.register('s1',origin_ids=['o1'],source_categories=['unfinished_thought'],purpose_category='self_understanding',evidence_ids=['e1'],expected_value=.8)['result']['signal_id']
  a=c.register('c1',signal_ids=[sid],scope_digest='b'*64,semantic_overlap_key='x'); assert a['result']['state']=='active'
  assert c.register('c1',signal_ids=[sid])['idempotent']
  out=c.inspection_summary(); assert out['candidate_count']==1 and not any(out['authority_boundary'].values()) and not out['goal_text_exposed']
 print('v1133.1: 6/6')
if __name__=='__main__': main()
