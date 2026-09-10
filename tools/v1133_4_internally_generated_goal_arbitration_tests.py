from pathlib import Path
import tempfile
from conscious_agent.internally_generated_goal_signals import InternallyGeneratedGoalSignalStore
from conscious_agent.internally_generated_goal_candidates import InternallyGeneratedGoalCandidateStore
from conscious_agent.internally_generated_goal_deliberation_sessions import InternallyGeneratedGoalDeliberationSessionStore
from conscious_agent.internally_generated_goal_arbitration import InternallyGeneratedGoalArbitrationStore
def session(root,suffix,urgency=.2,importance=.8,value=.8):
 sid=InternallyGeneratedGoalSignalStore(root).register('s-'+suffix,origin_ids=['o-'+suffix],purpose_category='capability_improvement',source_categories=['motivation'],evidence_ids=['e-'+suffix],urgency=urgency,importance=importance,expected_value=value)['result']['signal_id']; cid=InternallyGeneratedGoalCandidateStore(root).register('c-'+suffix,signal_ids=[sid])['result']['candidate_id']; return InternallyGeneratedGoalDeliberationSessionStore(root).open('d-'+suffix,candidate_id=cid)['session_id']
def main():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=InternallyGeneratedGoalArbitrationStore(r).arbitrate('a',session_id=session(r,'a'),feasibility=.9,value_support=.9,risk_acceptability=.9,priority_coherence=.9); assert x['outcome']=='goal_acceptance_recommended'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=InternallyGeneratedGoalArbitrationStore(r).arbitrate('b',session_id=session(r,'b',urgency=.76,importance=.36),feasibility=.9,value_support=.9,risk_acceptability=.9,priority_coherence=.9); assert x['outcome']=='suppress_false_urgency'
 with tempfile.TemporaryDirectory() as td:
  r=Path(td); x=InternallyGeneratedGoalArbitrationStore(r).arbitrate('c',session_id=session(r,'c'),deliberate_no_goal=True); assert x['outcome']=='deliberate_no_goal'
 print('v1133.4 internally generated goal arbitration: 3/3 passed')
if __name__=='__main__': main()
