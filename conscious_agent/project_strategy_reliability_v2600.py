from __future__ import annotations
"""v2600 comparative reliability profiles across project strategy codes."""
from typing import Any, Mapping, Sequence
import hashlib,json,collections
CONTRACT_VERSION='v2600.0';MIN_PROJECTS=3
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_strategy_reliability(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    groups={}
    for r in rows[-128:]:
        if not isinstance(r,Mapping):continue
        code=str(r.get('strategy_code') or 'unspecified')[:80];b=groups.setdefault(code,{'project_count':0,'success_count':0,'complete_evidence_count':0,'failed':collections.Counter()});b['project_count']+=1;b['success_count']+=int(bool(r.get('criteria_satisfied')));b['complete_evidence_count']+=int(bool(r.get('evidence_complete')));b['failed'].update(str(x)[:120] for x in r.get('failed_required_criteria') or [])
    profiles=[]
    for code,b in sorted(groups.items()):
        n=b['project_count'];rate=b['success_count']/max(1,n)
        if n<MIN_PROJECTS:label='insufficient_history'
        elif rate>=.8:label='reliable'
        elif rate<=.4:label='underperforming'
        else:label='mixed'
        profiles.append({'strategy_code':code,'project_count':n,'success_count':b['success_count'],'success_rate':round(rate,3),'complete_evidence_count':b['complete_evidence_count'],'reliability':label,'recurring_failed_criteria':[{'criterion_id':k,'count':v} for k,v in b['failed'].most_common(6)]})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'profiles':profiles,'strategy_count':len(profiles),'strategy_policy_mutated':False,'automatic_strategy_selection_permitted':False,'authority_granted':False,'raw_content_stored':False};out['profile_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_strategy_reliability']
