from __future__ import annotations
"""v2640 review-only start preflight for one exact queued developer project."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2640.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_start_preflight(*,project_id:str,project_digest:str,recovery:Mapping[str,Any],readiness:Mapping[str,Any],staleness:Mapping[str,Any],verification_health:Mapping[str,Any]|None=None)->dict[str,Any]:
 pid=str(project_id or '')[:120];pd=str(project_digest or '')[:64];vh=verification_health if isinstance(verification_health,Mapping) else {}
 entry=next((e for e in (recovery.get('queue') or {}).get('entries') or [] if isinstance(e,Mapping) and str(e.get('project_id') or '')==pid and str(e.get('project_digest') or '')==pd),None)
 stale=pid in {str(x) for x in staleness.get('stale_project_ids') or []};ready=pid in {str(x) for x in readiness.get('ready_project_ids') or []};blocked=bool((entry or {}).get('blockers'));verification_state=str(vh.get('state') or 'unknown')
 checks={'recovery_coherent':bool(recovery.get('ok')),'entry_exact_match':entry is not None,'ready':ready,'not_stale':not stale,'no_blockers':not blocked,'verification_not_degraded':verification_state!='degraded'}
 eligible=all(checks.values())
 out={'ok':bool(pid and pd and entry),'contract_version':CONTRACT_VERSION,'project_id':pid,'project_digest':pd,'checks':checks,'eligible_for_operator_start_review':eligible,'verification_state':verification_state,'operator_start_confirmation_required':True,'automatic_project_start_permitted':False,'campaign_started':False,'queue_mutation_permitted':False,'source_mutation_authorized':False,'authority_granted':False};out['preflight_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_start_preflight']
