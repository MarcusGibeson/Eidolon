from __future__ import annotations
from typing import Any,Iterable,Mapping
from value_risk_deliberation_foundations import DENIED_AUTHORITY,ARCHITECTURE_LINEAGE,alternative_score,digest,normalize_alternatives
CONTRACT_VERSION='v1292.5'
def deliberate_value_and_risk(alternatives:Iterable[Mapping[str,Any]],*,minimum_score:float=15.0,ambiguity_margin:float=3.0)->dict[str,Any]:
 rows=normalize_alternatives(alternatives);ranked=[]
 for row in rows:
  assessment=alternative_score(row);ranked.append(row|assessment)
 ranked.sort(key=lambda r:(r['blocked'],-r['score'],r['proposal_id']))
 viable=[r for r in ranked if not r['blocked'] and r['score']>=float(minimum_score)]
 selected=None;disposition='defer_no_viable_candidate';reason='all_candidates_blocked_or_low_value'
 if viable:
  first=viable[0];second=viable[1] if len(viable)>1 else None
  if second and abs(first['score']-second['score'])<float(ambiguity_margin) and max(first['uncertainty'],second['uncertainty'])>=55:
   disposition='defer_ambiguous_tradeoff';reason='top_candidates_too_close_under_uncertainty'
  else:selected=first;disposition='recommend_for_operator_review';reason='highest_defensible_value_risk_score'
 comparisons=[]
 if selected:
  for other in ranked:
   if other['proposal_id']==selected['proposal_id']:continue
   codes=[]
   if other['blocked']:codes.append('alternative_blocked')
   if selected['score']>other['score']:codes.append('higher_net_value')
   if selected['risk']<other['risk']:codes.append('lower_risk')
   if selected['reversibility']>other['reversibility']:codes.append('more_reversible')
   if selected['uncertainty']<other['uncertainty']:codes.append('lower_uncertainty')
   comparisons.append({'alternative_proposal_id':other['proposal_id'],'reason_codes':codes or ['tie_broken_deterministically'],'content_free':True})
 result={'contract_version':CONTRACT_VERSION,'disposition':disposition,'reason':reason,'recommended_proposal_id':selected['proposal_id'] if selected else '', 'recommended_proposal_digest':selected['proposal_digest'] if selected else '', 'ranked_count':len(ranked),'viable_count':len(viable),'ranked':[{'proposal_id':r['proposal_id'],'score':r['score'],'blocked':r['blocked'],'block_reasons':r['block_reasons'],'expected_value':r['expected_value'],'risk':r['risk'],'reversibility':r['reversibility'],'cost':r['cost'],'uncertainty':r['uncertainty'],'urgency':r['urgency'],'content_free':True} for r in ranked],'comparisons':comparisons,'recommendation_is_priority_mutation':False,'recommendation_is_authorization':False,'operator_decision_required':bool(selected),'architecture_lineage':dict(ARCHITECTURE_LINEAGE),'content_free':True,'read_only':True,**DENIED_AUTHORITY};result['deliberation_digest']=digest(result);return result
def alternatives_from_improvement_proposals(proposal_result:Mapping[str,Any],evidence:Mapping[str,Mapping[str,Any]])->list[dict[str,Any]]:
 out=[]
 for p in proposal_result.get('proposals') or []:
  pid=str(p.get('proposal_id') or '');e=dict(evidence.get(pid) or {});e.update({'proposal_id':pid,'proposal_digest':p.get('proposal_digest')});out.append(e)
 return out
