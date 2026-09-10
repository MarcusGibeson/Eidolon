from __future__ import annotations
from typing import Any,Iterable,Mapping
from independent_improvement_proposals_foundations import DENIED_AUTHORITY,MAX_PROPOSALS,digest,normalize_observations,proposal_eligibility
CONTRACT_VERSION='v1291.5'
def generate_improvement_proposals(observations:Iterable[Mapping[str,Any]],*,max_proposals:int=MAX_PROPOSALS)->dict[str,Any]:
 rows=normalize_observations(observations);eligible=[];suppressed=[]
 for row in rows:
  gate=proposal_eligibility(row)
  if not gate['eligible']:suppressed.append({'issue_digest':row['issue_digest'],'kind':row['kind'],'reasons':gate['suppression_reasons'],'content_free':True});continue
  score=round(.28*row['impact']+.24*row['relevance']+.20*row['actionability']+.16*row['confidence']+(.12*100 if row['novel'] else 0),2)
  p={'proposal_id':'improvement-'+row['issue_digest'][:20],'kind':row['kind'],'issue_digest':row['issue_digest'],'evidence_digest':row['evidence_digest'],'score':score,'rationale_codes':['evidence_backed','current_relevance','material_impact','actionable','novel'],'state':'proposal_only','requires_operator_selection':True,'creates_backlog_item':False,'executes_work':False,'content_free':True,**DENIED_AUTHORITY};p['proposal_digest']=digest(p);eligible.append(p)
 eligible.sort(key=lambda x:(-x['score'],x['proposal_id']));eligible=eligible[:max(1,min(MAX_PROPOSALS,int(max_proposals)))]
 return {'contract_version':CONTRACT_VERSION,'proposal_count':len(eligible),'suppressed_count':len(suppressed),'proposals':eligible,'suppressed':suppressed,'nothing_worth_proposing':not eligible,'observations_do_not_imply_work':True,'content_free':True,'read_only':True,**DENIED_AUTHORITY}
def observations_from_product_quality(judgment:Mapping[str,Any])->list[dict[str,Any]]:
 out=[];states=judgment.get('dimension_states') or {};scope=str(judgment.get('scope_digest') or judgment.get('evidence_digest') or '')
 if len(scope)!=64:scope=digest({'judgment':judgment.get('judgment_digest')})
 kind_map={'coherence':'reliability','usability':'usability','accessibility':'accessibility','maintainability':'maintainability','completeness':'completeness','operator_readiness':'operator_readiness'}
 for dim,state in states.items():
  if state not in {'fail','warn'}:continue
  issue=digest({'scope':scope,'dimension':dim,'state':state});out.append({'kind':kind_map.get(dim,'reliability'),'issue_digest':issue,'evidence_digest':str(judgment.get('judgment_digest') or issue)[:64] if len(str(judgment.get('judgment_digest') or ''))>=64 else issue,'relevance':90,'impact':90 if state=='fail' else 60,'confidence':90 if state=='fail' else 70,'actionability':70,'novel':True,'fresh':True,'private':False})
 return out
