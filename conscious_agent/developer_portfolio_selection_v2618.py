from __future__ import annotations
"""v2618 exact operator-selection evidence for developer portfolio candidates."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2618.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def bind_operator_portfolio_selection(review:Mapping[str,Any], *, project_id:str, project_digest:str, confirm:str)->dict[str,Any]:
 rows=[x for x in review.get('ranked_candidates') or [] if isinstance(x,Mapping)]
 match=next((x for x in rows if str(x.get('project_id'))==str(project_id) and str(x.get('project_digest'))==str(project_digest)),None)
 expected=f'SELECT {project_id}'
 valid=bool(review.get('operator_selection_required')) and match is not None and str(confirm)==expected
 out={'ok':valid,'contract_version':CONTRACT_VERSION,'selection_status':'bound' if valid else 'rejected','project_id':str(project_id)[:120] if valid else '','project_digest':str(project_digest)[:64] if valid else '','portfolio_review_digest':str(review.get('review_digest') or '')[:64],'confirmation_digest':_digest(str(confirm)),'operator_selection_bound':valid,'campaign_started':False,'project_mutation_authorized':False,'source_mutation_authorized':False,'authority_granted':False};out['selection_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','bind_operator_portfolio_selection']
