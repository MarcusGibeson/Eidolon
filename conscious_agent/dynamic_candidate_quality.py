from __future__ import annotations

"""v1491 deterministic quality scoring/comparison for hardened discovery candidates.

Scoring is advisory evidence only.  It can order candidates for operator review,
but it cannot select one for implementation or create any authority-bearing state.
"""

import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION='v1491.9'


def _digest(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def _score(row:Mapping[str,Any])->tuple[float,dict[str,float]]:
    confidence=max(0.0,min(1.0,float(row.get('confidence') or 0.0)))
    tests=max(0,int(row.get('test_reference_file_count') or 0))
    deps=max(0,int(row.get('estimated_dependency_count') or 0))
    reversibility=str(row.get('reversibility_classification') or '').casefold()
    comps={
      'confidence':confidence,
      'test_depth':min(1.0,tests/4.0),
      'dependency_simplicity':max(0.0,1.0-deps/36.0),
      'reversibility':1.0 if 'high' in reversibility or 'reversible' in reversibility else .6 if 'medium' in reversibility else .25,
      'scope_focus':max(.2,1.0-min(8,len(row.get('source_symbols') or ()))/10.0),
    }
    value=.35*comps['confidence']+.22*comps['test_depth']+.18*comps['dependency_simplicity']+.15*comps['reversibility']+.10*comps['scope_focus']
    return round(value,4),{k:round(v,4) for k,v in comps.items()}


def compare_dynamic_candidates(hardening:Mapping[str,Any])->dict[str,Any]:
    rows=[]
    for source in hardening.get('eligible_candidates') or ():
        row=dict(source or {})
        score,components=_score(row)
        quality='strong' if score>=.78 else 'credible' if score>=.62 else 'weak'
        rows.append({
          'candidate_id':str(row.get('candidate_id') or ''),
          'eligibility_digest':str(row.get('eligibility_digest') or ''),
          'evidence_digest':str(row.get('evidence_digest') or ''),
          'source_module':str(row.get('source_module') or ''),
          'proposed_destination_module':str(row.get('proposed_destination_module') or ''),
          'source_symbol_count':len(row.get('source_symbols') or ()),
          'quality_score':score,'quality_class':quality,'score_components':components,
          'uncertainty':str(row.get('uncertainty') or 'high'),'content_free':True,
        })
    rows.sort(key=lambda r:(-r['quality_score'],r['uncertainty'],r['candidate_id']))
    # Tie groups make uncertainty visible instead of manufacturing precision.
    tie_groups=[]
    current=[];last=None
    for row in rows:
        if last is None or abs(row['quality_score']-last)<=0.015:
            current.append(row['candidate_id'])
        else:
            if len(current)>1: tie_groups.append(current)
            current=[row['candidate_id']]
        last=row['quality_score']
    if len(current)>1:tie_groups.append(current)
    result={
      'contract_version':CONTRACT_VERSION,'hardening_digest':str(hardening.get('hardening_digest') or ''),
      'candidate_count':len(rows),'ordered_comparison':rows,'tie_groups':tie_groups,
      'top_candidate_id':rows[0]['candidate_id'] if rows else '',
      'top_candidate_is_unique':bool(rows and not any(rows[0]['candidate_id'] in g for g in tie_groups)),
      'ranking_performed':bool(rows),'selection_made':False,'operator_selection_required':bool(rows),
      'proposal_created':False,'workspace_prepared':False,'provider_contacted':False,'source_modified':False,'authority_granted':False,'content_free':True,
    }
    result['comparison_digest']=_digest({k:v for k,v in result.items() if k!='ordered_comparison'}|{'rows':[(_['candidate_id'],_['quality_score'],_['eligibility_digest']) for _ in rows]})
    return result

__all__=['CONTRACT_VERSION','compare_dynamic_candidates']
