from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.prospective_planning_signals import ProspectivePlanningSignalStore
from conscious_agent.prospective_planning_candidates import ProspectivePlanningCandidateStore
from conscious_agent.prospective_planning_deliberation_sessions import ProspectivePlanningDeliberationSessionStore
from conscious_agent.prospective_planning_arbitration import ProspectivePlanningArbitrationStore
from conscious_agent.prospective_planning_outcome_lineage import ProspectivePlanningOutcomeLineageStore
with TemporaryDirectory() as td:
 r=Path(td); s=ProspectivePlanningSignalStore(r); x=s.register('s',origin_ids=['g1'],goal_ids=['g1'],source_categories=['accepted_goal_outcome'],purpose_category='project_path',evidence_ids=['ev1'],importance=.8,expected_value=.9,scope_digest='abc',alternative_ids=['alt1'],stop_condition_ids=['stop1']); c=ProspectivePlanningCandidateStore(r); y=c.register('c',signal_ids=[x['result']['signal_id']],plan_class='development',scope_digest='abc'); d=ProspectivePlanningDeliberationSessionStore(r); z=d.open('d',candidate_id=y['result']['candidate_id']); a=ProspectivePlanningArbitrationStore(r); q=a.arbitrate('a',session_id=z['session_id'],feasibility=.8,value_support=.8,risk_acceptability=.8,reversibility_support=.8); o=ProspectivePlanningOutcomeLineageStore(r); out=o.record('o',arbitration_id=q['arbitration_id'],lifecycle_state='recommended'); assert out['ok']; snap=o.inspection_summary(); assert snap['outcome_count']==1 and not snap['authority_boundary']['can_activate_plan']; assert o.record('o',arbitration_id=q['arbitration_id'])['idempotent']
print('v1134.6 checks: 7/7')
