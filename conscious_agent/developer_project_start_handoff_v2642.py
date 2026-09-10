from __future__ import annotations
"""v2642 content-minimized handoff candidate for a future governed project-start boundary."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2642.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_start_handoff_candidate(review:Mapping[str,Any])->dict[str,Any]:
 eligible=bool(review.get('ok')) and bool(review.get('eligible'))
 out={'ok':eligible,'contract_version':CONTRACT_VERSION,'project_id':str(review.get('project_id') or '')[:120] if eligible else '','project_digest':str(review.get('project_digest') or '')[:64] if eligible else '','start_review_digest':str(review.get('start_review_digest') or '')[:64],'next_boundary':'operator_selected_project_start_trial' if eligible else 'preflight_remediation','handoff_candidate_only':True,'operator_start_authorization_required':True,'start_authorization_issued':False,'project_started':False,'campaign_started':False,'tool_execution_authorized':False,'source_mutation_authorized':False,'authority_granted':False};out['handoff_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_start_handoff_candidate']
