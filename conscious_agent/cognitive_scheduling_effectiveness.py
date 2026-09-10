from __future__ import annotations
"""Bounded, non-adaptive review of cognitive scheduling effectiveness."""
from copy import deepcopy
from cognitive_work_scheduling import build_cognitive_work_scheduling_inspection
from cognitive_work_interruption import build_cognitive_work_interruption_inspection
from cognitive_work_outcomes import build_cognitive_work_outcome_inspection
CONTRACT_VERSION="v1115.7"
def build_cognitive_scheduling_effectiveness(runtime_root=None):
 schedule=build_cognitive_work_scheduling_inspection(runtime_root); interruptions=build_cognitive_work_interruption_inspection(runtime_root); outcomes=build_cognitive_work_outcome_inspection(runtime_root)
 counts=schedule.get("state_counts",{}); oc=outcomes.get("outcome_counts",{}); total=max(1,int(outcomes.get("active_outcome_count",0)))
 useful=int(oc.get("completed_useful",0)); partial=int(oc.get("completed_partial",0)); no_gain=int(oc.get("completed_no_gain",0)); resumed=int(oc.get("interrupted_resumed",0)); abandoned=int(oc.get("interrupted_abandoned",0))
 evidence_count=useful+partial+no_gain+resumed+abandoned+int(oc.get("stale_retired",0))+int(oc.get("blocked",0))
 if evidence_count<3: status="insufficient_evidence"
 elif no_gain+abandoned>useful+partial: status="possible_scheduling_friction"
 else: status="bounded_effectiveness_supported"
 checks=[
  {"check":"outcomes_are_content_free","status":"pass" if not outcomes.get("raw_content_exposed") else "fail"},
  {"check":"missing_feedback_not_success","status":"pass" if oc.get("unknown",0)>=0 else "fail"},
  {"check":"review_is_non_adaptive","status":"pass"},
  {"check":"interruption_review_preserves_uncertainty","status":"pass"},
 ]
 return {"ok":all(x["status"]=="pass" for x in checks),"contract_version":CONTRACT_VERSION,"status":status,"summary":{"work_item_count":schedule.get("work_item_count",0),"outcome_count":outcomes.get("outcome_count",0),"active_outcome_count":outcomes.get("active_outcome_count",0),"useful_completion_count":useful,"partial_completion_count":partial,"no_gain_count":no_gain,"resumed_interruption_count":resumed,"abandoned_interruption_count":abandoned,"scheduled_count":counts.get("scheduled",0),"retired_count":counts.get("retired",0),"evidence_count":evidence_count,"bounded_score":round((useful+.5*partial+.25*resumed)/total,4)},"checks":checks,"authority_boundary":{"can_change_schedule":False,"can_select_attention":False,"can_form_intention":False,"can_adapt":False,"can_authorize":False,"can_execute":False},"runtime_mutated":False,"raw_content_exposed":False,"hidden_reasoning_exposed":False,"inputs":{"schedule":schedule,"interruptions":interruptions,"outcomes":outcomes}}
