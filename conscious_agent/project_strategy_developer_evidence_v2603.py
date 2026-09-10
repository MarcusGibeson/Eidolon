from __future__ import annotations
"""v2603 read-only bridge from strategy learning into supervised developer evidence."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2603.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_strategy_developer_evidence(learning:Mapping[str,Any])->dict[str,Any]:
    rows=[{'strategy_code':str(x.get('strategy_code') or '')[:80],'recommendation':str(x.get('recommendation') or '')[:100],'reliability':str(x.get('reliability') or '')[:40],'calibration':str(x.get('calibration') or '')[:40]} for x in learning.get('candidates') or [] if isinstance(x,Mapping)][:12]
    out={'ok':True,'contract_version':CONTRACT_VERSION,'strategy_evidence':rows,'evidence_count':len(rows),'candidate_selection_authorized':False,'campaign_start_authorized':False,'source_mutation_authorized':False,'automatic_priority_change_permitted':False,'authority_granted':False,'raw_project_content_stored':False};out['evidence_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_strategy_developer_evidence']
