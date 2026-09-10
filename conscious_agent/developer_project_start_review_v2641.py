from __future__ import annotations
"""v2641 exact preflight-bound operator start review packet; no start authority."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2641.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_start_review(preflight:Mapping[str,Any],queue_review:Mapping[str,Any]|None=None)->dict[str,Any]:
 qr=queue_review if isinstance(queue_review,Mapping) else {};eligible=bool(preflight.get('eligible_for_operator_start_review'));binding_ok=not qr or (str(qr.get('project_id') or '')==str(preflight.get('project_id') or '') and str(qr.get('project_digest') or '')==str(preflight.get('project_digest') or ''))
 out={'ok':bool(preflight.get('ok')) and binding_ok,'contract_version':CONTRACT_VERSION,'project_id':str(preflight.get('project_id') or '')[:120],'project_digest':str(preflight.get('project_digest') or '')[:64],'preflight_digest':str(preflight.get('preflight_digest') or '')[:64],'eligible':eligible and binding_ok,'operator_action_required':'explicit_project_start_authorization' if eligible and binding_ok else 'resolve_preflight_blockers','review_only':True,'start_authorization_issued':False,'project_started':False,'campaign_started':False,'source_mutation_authorized':False,'authority_granted':False};out['start_review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_start_review']
