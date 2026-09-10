from __future__ import annotations
"""v1292.0-v1292.2 value/risk deliberation foundations for proposal comparison."""
from hashlib import sha256
import json
from typing import Any,Iterable,Mapping
CONTRACT_VERSION='v1292.2';MAX_ALTERNATIVES=12
DENIED_AUTHORITY={'backlog_mutation_authorized':False,'priority_change_authorized':False,'proposal_selection_authorized':False,'provider_contact_authorized':False,'command_execution_authorized':False,'test_execution_authorized':False,'repair_authorized':False,'project_mutation_authorized':False,'source_application_authorized':False,'self_update_authorized':False,'rollback_authorized':False,'release_authorized':False,'standing_authority_granted':False}
ARCHITECTURE_LINEAGE={'priority_selection':'v1263','calibrated_uncertainty':'v1282','hierarchical_goals':'v1285','dynamic_replanning':'v1286','improvement_proposals':'v1291'}
def digest(v:Any)->str:return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def normalize_alternatives(rows:Iterable[Mapping[str,Any]])->list[dict[str,Any]]:
 out=[];seen=set()
 for raw in rows:
  pid=str(raw.get('proposal_id') or '').strip();pd=str(raw.get('proposal_digest') or '').lower().strip()
  if not pid or len(pd)!=64:raise ValueError('proposal_identity_required')
  if pid in seen:continue
  seen.add(pid)
  def n(k,d=0):return max(0,min(100,int(raw.get(k,d))))
  deps=tuple(sorted({str(x) for x in raw.get('dependencies') or [] if str(x)}))
  out.append({'proposal_id':pid,'proposal_digest':pd,'expected_value':n('expected_value'),'risk':n('risk'),'reversibility':n('reversibility'),'cost':n('cost'),'uncertainty':n('uncertainty'),'urgency':n('urgency'),'dependency_blocked':bool(raw.get('dependency_blocked',False)),'dependencies':deps,'evidence_fresh':bool(raw.get('evidence_fresh',True)),'critical_risk':bool(raw.get('critical_risk',False)),'irreversible':bool(raw.get('irreversible',False)),'content_free':True})
 return out[:MAX_ALTERNATIVES]
def alternative_score(row:Mapping[str,Any])->dict[str,Any]:
 value=.34*int(row['expected_value'])+.12*int(row['urgency'])+.14*int(row['reversibility'])
 burden=.18*int(row['risk'])+.10*int(row['cost'])+.12*int(row['uncertainty'])
 score=round(value-burden,2);blocks=[]
 if not row.get('evidence_fresh'):blocks.append('stale_evidence')
 if row.get('dependency_blocked'):blocks.append('dependency_blocked')
 if row.get('critical_risk'):blocks.append('critical_risk')
 if row.get('irreversible') and int(row.get('risk',0))>=50:blocks.append('high_risk_irreversible')
 if int(row.get('uncertainty',0))>=85:blocks.append('uncertainty_too_high')
 return {'score':score,'blocked':bool(blocks),'block_reasons':blocks,'value_component':round(value,2),'burden_component':round(burden,2),'content_free':True,**DENIED_AUTHORITY}
