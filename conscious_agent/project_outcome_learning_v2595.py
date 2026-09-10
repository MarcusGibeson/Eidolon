from __future__ import annotations
"""v2595 project-outcome learning candidates; never durable lessons automatically."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2595.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_outcome_learning_candidate(evaluation:Mapping[str,Any])->dict[str,Any]:
    failed=[str(x)[:120] for x in evaluation.get('failed_required_criteria') or []]
    if evaluation.get('criteria_satisfied'):kind='successful_project_pattern_candidate'
    elif failed:kind='project_failure_pattern_candidate'
    else:kind='insufficient_project_outcome_evidence'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'candidate_type':kind,'failed_criteria':failed[:16],'criteria_satisfied':bool(evaluation.get('criteria_satisfied')),'durable_lesson_committed':False,'self_model_mutated':False,'plan_policy_mutated':False,'project_goal_completed':False,'provider_contacted':False,'operator_review_required':kind!='insufficient_project_outcome_evidence','authority_granted':False}
    out['candidate_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_outcome_learning_candidate']
