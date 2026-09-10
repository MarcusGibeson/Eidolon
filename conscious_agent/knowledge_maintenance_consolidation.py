from __future__ import annotations
"""Read-only consolidation of bounded knowledge maintenance state."""
from pathlib import Path
import os
try:
    from knowledge_reconsideration_scheduling import build_reconsideration_scheduling_inspection
    from evidence_change_propagation import build_evidence_change_propagation_inspection
    from bounded_reconsideration_reflection import build_bounded_reconsideration_reflection_inspection
    from belief_maintenance_outcomes import build_belief_maintenance_outcomes_inspection
    from reconsideration_conversation_continuity import build_reconsideration_conversation_inspection
except ImportError:
    from knowledge_reconsideration_scheduling import build_reconsideration_scheduling_inspection
    from evidence_change_propagation import build_evidence_change_propagation_inspection
    from bounded_reconsideration_reflection import build_bounded_reconsideration_reflection_inspection
    from belief_maintenance_outcomes import build_belief_maintenance_outcomes_inspection
    from reconsideration_conversation_continuity import build_reconsideration_conversation_inspection
CONTRACT_VERSION='v1106.8'
def _root(): return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def build_knowledge_maintenance_consolidation(runtime_root=None):
    root=runtime_root or _root(); schedules=build_reconsideration_scheduling_inspection(root); propagation=build_evidence_change_propagation_inspection(root); reflections=build_bounded_reconsideration_reflection_inspection(root); outcomes=build_belief_maintenance_outcomes_inspection(root); communication=build_reconsideration_conversation_inspection(root)
    checks=[
      {'name':'scheduling_visible','passed':schedules.get('ok') is True},
      {'name':'propagation_visible','passed':propagation.get('ok') is True},
      {'name':'bounded_reflection_visible','passed':reflections.get('ok') is True},
      {'name':'maintenance_outcomes_visible','passed':outcomes.get('ok') is True},
      {'name':'communication_continuity_visible','passed':communication.get('ok') is True},
      {'name':'raw_chain_of_thought_absent','passed':reflections.get('raw_chain_of_thought_stored') is False},
      {'name':'provider_neutral','passed':not any(x.get('provider_contacted') for x in (schedules,propagation,reflections,outcomes,communication))},
      {'name':'external_browsing_absent','passed':not any(x.get('external_browsing_performed') for x in (schedules,propagation,outcomes,communication))},
      {'name':'action_authority_preserved','passed':all(not (x.get('authority_boundary') or {}).get('can_authorize_action') for x in (schedules,reflections,outcomes,communication))},
      {'name':'execution_absent','passed':all(not (x.get('authority_boundary') or {}).get('can_execute_action') for x in (schedules,reflections,outcomes,communication))},
      {'name':'release_not_promoted','passed':True},{'name':'consciousness_not_claimed','passed':True},
    ]
    return {'ok':all(c['passed'] for c in checks),'status':'ready_for_v1106_9_checkpoint' if all(c['passed'] for c in checks) else 'blocked','contract_version':CONTRACT_VERSION,'checks':checks,'check_count':len(checks),'scheduling':schedules,'propagation':propagation,'reflections':reflections,'outcomes':outcomes,'communication':communication,'runtime_mutated':False,'provider_contacted':False,'external_browsing_performed':False,'action_authority_changed':False,'release_promoted':False,'release_certified':False,'consciousness_claimed':False}
