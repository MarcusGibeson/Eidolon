from __future__ import annotations
"""v2661 firewall preventing synthetic rehearsal evidence from entering real outcome learning."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2661.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def classify_project_outcome_evidence(evidence:Mapping[str,Any])->dict[str,Any]:
 synthetic=bool(evidence.get('synthetic_evidence_only'));real=not synthetic and bool(evidence.get('reviewed_real_outcome') or evidence.get('real_outcome_reviewed'))
 lane='synthetic_rehearsal' if synthetic else ('reviewed_real_outcome' if real else 'untrusted_or_unreviewed')
 out={'ok':True,'contract_version':CONTRACT_VERSION,'evidence_lane':lane,'eligible_for_real_strategy_learning':real,'eligible_for_rehearsal_learning':synthetic,'automatic_promotion_between_lanes_permitted':False,'synthetic_counts_as_real_success':False,'authority_granted':False};out['classification_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','classify_project_outcome_evidence']
