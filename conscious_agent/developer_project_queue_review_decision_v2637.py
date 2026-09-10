from __future__ import annotations
"""v2637 digest-bound operator review decision evidence; never starts work."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2637.0';DECISIONS={'acknowledge','defer','request_revalidation'}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_queue_review_decision(*,review:Mapping[str,Any],decision:str,operator_selection_digest:str)->dict[str,Any]:
 d=str(decision or '');sel=str(operator_selection_digest or '')[:64];review_digest=str(review.get('review_digest') or '')[:64];valid=d in DECISIONS and len(sel)==64 and len(review_digest)==64
 out={'ok':valid,'contract_version':CONTRACT_VERSION,'decision':d if d in DECISIONS else 'invalid','review_digest':review_digest,'operator_selection_digest':sel,'decision_applied':False,'queue_mutated':False,'project_started':False,'campaign_started':False,'automatic_transition_permitted':False,'authority_granted':False};out['decision_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_queue_review_decision']
