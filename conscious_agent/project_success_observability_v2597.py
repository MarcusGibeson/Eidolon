from __future__ import annotations
"""v2597 bounded runtime observability for project-success review packets."""
from pathlib import Path
from typing import Any, Mapping
import os,hashlib,json
try:
    from json_storage import load_json_file, write_json_atomic
    from mental_activity_timeline_v2511 import MentalActivityTimeline
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from mental_activity_timeline_v2511 import MentalActivityTimeline
CONTRACT_VERSION='v2597.0'
def _root(r=None):
    if r is not None:return Path(r).expanduser().resolve()
    return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def record_project_success_observability(review:Mapping[str,Any],*,runtime_root=None)->dict[str,Any]:
    root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);state={'contract_version':CONTRACT_VERSION,'project_ref_digest':hashlib.sha256(str(review.get('project_id') or '').encode()).hexdigest(),'review_digest':str(review.get('review_digest') or ''),'criteria_satisfied':bool(review.get('criteria_satisfied')),'evidence_complete':bool(review.get('evidence_complete')),'review_disposition':str(review.get('review_disposition') or '')[:80],'failed_criterion_count':len(review.get('failed_required_criteria') or []),'operator_completion_decision_required':bool(review.get('operator_completion_decision_required')),'project_completed':False,'raw_project_content_stored':False,'authority_granted':False};write_json_atomic(root/'project_success_observability_v2597.json',state,expected_type=dict,sort_keys=True);MentalActivityTimeline(root).append(f'project-success:{state["project_ref_digest"][:20]}:{state["review_digest"][:20]}',event_kind='planning',transition='project_success_review_ready' if state['operator_completion_decision_required'] else 'project_success_more_work',source_digest=state['review_digest'] or state['project_ref_digest'],subject_ref=state['project_ref_digest'][:24],outcome_code=state['review_disposition'].upper()[:80]);return {'ok':True,**state,'source_mutated':False}
def load_project_success_observability(runtime_root=None)->dict[str,Any]:
    state=load_json_file(_root(runtime_root)/'project_success_observability_v2597.json',{},expected_type=dict);return {'ok':True,'contract_version':CONTRACT_VERSION,'present':bool(state),**(dict(state) if state else {}),'raw_project_content_stored':False}
__all__=['CONTRACT_VERSION','record_project_success_observability','load_project_success_observability']
