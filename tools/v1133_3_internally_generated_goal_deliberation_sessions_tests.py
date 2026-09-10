from pathlib import Path
import tempfile
from conscious_agent.internally_generated_goal_signals import InternallyGeneratedGoalSignalStore
from conscious_agent.internally_generated_goal_candidates import InternallyGeneratedGoalCandidateStore
from conscious_agent.internally_generated_goal_deliberation_sessions import InternallyGeneratedGoalDeliberationSessionStore
def seed(root,suffix='a',review=False,prereqs=None):
 s=InternallyGeneratedGoalSignalStore(root); sid=s.register('s-'+suffix,origin_ids=['o-'+suffix],purpose_category='capability_improvement',source_categories=['motivation'],evidence_ids=['e-'+suffix],importance=.8,expected_value=.8)['result']['signal_id']; return InternallyGeneratedGoalCandidateStore(root).register('c-'+suffix,signal_ids=[sid],operator_review_required=review,prerequisite_ids=prereqs or [])['result']['candidate_id']
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); cid=seed(r); out=InternallyGeneratedGoalDeliberationSessionStore(r).open('o-a',candidate_id=cid,deliberation_budget=99); assert out['state']=='open'; assert InternallyGeneratedGoalDeliberationSessionStore(r).snapshot()['sessions'][0]['deliberation_budget']==6
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); cid=seed(r,'b',review=True); assert InternallyGeneratedGoalDeliberationSessionStore(r).open('o-b',candidate_id=cid)['state']=='paused'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); a=seed(r,'c'); b=seed(r,'d'); assert InternallyGeneratedGoalDeliberationSessionStore(r).open('o-c',candidate_id=a,comparison_candidate_ids=[b],conflict_review_ready=False)['state']=='paused'
 print('v1133.3 internally generated goal deliberation sessions: 3/3 passed')
if __name__=='__main__': main()
