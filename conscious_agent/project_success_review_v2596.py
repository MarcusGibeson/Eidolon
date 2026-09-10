from __future__ import annotations
"""v2596 operator review boundary for generic project success evaluations."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2596.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_success_review_packet(evaluation:Mapping[str,Any],learning_candidate:Mapping[str,Any]|None=None)->dict[str,Any]:
    candidate=learning_candidate if isinstance(learning_candidate,Mapping) else {}
    ready=bool(evaluation.get('criteria_satisfied') and evaluation.get('evidence_complete'))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'project_id':str(evaluation.get('project_id') or '')[:160],'goal_digest':str(evaluation.get('goal_digest') or '')[:64],'evaluation_digest':str(evaluation.get('evaluation_digest') or '')[:64],'criteria_satisfied':bool(evaluation.get('criteria_satisfied')),'evidence_complete':bool(evaluation.get('evidence_complete')),'failed_required_criteria':[str(x)[:120] for x in evaluation.get('failed_required_criteria') or []][:16],'learning_candidate_digest':str(candidate.get('candidate_digest') or '')[:64],'review_disposition':'ready_for_operator_completion_review' if ready else 'project_outcome_requires_more_work','operator_completion_decision_required':ready,'project_completed':False,'automatic_completion_permitted':False,'durable_lesson_committed':False,'source_mutated':False,'authority_granted':False}
    out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_success_review_packet']
