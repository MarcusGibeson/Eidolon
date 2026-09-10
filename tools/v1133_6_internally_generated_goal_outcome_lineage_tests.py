from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.internally_generated_goal_signals import InternallyGeneratedGoalSignalStore
from conscious_agent.internally_generated_goal_candidates import InternallyGeneratedGoalCandidateStore
from conscious_agent.internally_generated_goal_deliberation_sessions import InternallyGeneratedGoalDeliberationSessionStore
from conscious_agent.internally_generated_goal_arbitration import InternallyGeneratedGoalArbitrationStore
from conscious_agent.internally_generated_goal_outcome_lineage import InternallyGeneratedGoalOutcomeLineageStore
with TemporaryDirectory() as td:
 r=Path(td); s=InternallyGeneratedGoalSignalStore(r); x=s.register('s',origin_ids=['m1'],source_categories=['motivation'],purpose_category='project_progress',evidence_ids=['ev1'],importance=.8,expected_value=.9,scope_digest='abc'); c=InternallyGeneratedGoalCandidateStore(r); y=c.register('c',signal_ids=[x['result']['signal_id']],goal_class='development',scope_digest='abc'); d=InternallyGeneratedGoalDeliberationSessionStore(r); z=d.open('d',candidate_id=y['result']['candidate_id']); a=InternallyGeneratedGoalArbitrationStore(r); q=a.arbitrate('a',session_id=z['session_id'],feasibility=.8,value_support=.8,risk_acceptability=.8,priority_coherence=.8); o=InternallyGeneratedGoalOutcomeLineageStore(r); out=o.record('o',arbitration_id=q['arbitration_id'],lifecycle_state='active'); assert out['ok']; snap=o.inspection_summary(); assert snap['outcome_count']==1 and not snap['authority_boundary']['can_activate_goal']; assert o.record('o',arbitration_id=q['arbitration_id'])['idempotent']
print('v1133.6 checks: 7/7')
