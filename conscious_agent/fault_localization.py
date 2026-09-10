from __future__ import annotations
"""v1362 evidence-ranked fault localization without speculative edits."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1362.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'repair_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def localize_fault(*,source_manifest_digest:str,reproduction_digest:str,candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not all(re.fullmatch(r'[a-f0-9]{64}',str(x or '')) for x in (source_manifest_digest,reproduction_digest)):return {'ok':False,'status':'fault_localization_lineage_required','action_executed':False,**DENIED}
 if not candidates or len(candidates)>256:return {'ok':False,'status':'fault_localization_candidate_count_invalid','action_executed':False,**DENIED}
 rows=[];seen=set()
 try:
  for raw in candidates:
   cid=str(raw.get('component_id') or '');ev=list(raw.get('evidence_digests') or []);dist=int(raw.get('call_distance'))
   if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}',cid) or cid in seen or dist<0 or dist>100 or not ev or any(not re.fullmatch(r'[a-f0-9]{64}',str(x)) for x in ev):raise ValueError
   seen.add(cid);score=min(3,len(ev))*1.0 + 4.0/(1+dist)
   score+=5 if raw.get('direct_failure_link') is True else 0;score+=3 if raw.get('state_transition_match') is True else 0;score+=2 if raw.get('recent_diff') is True else 0;score-=5 if raw.get('environment_only') is True else 0
   rows.append({'component_id_digest':_d(cid),'score':round(score,4),'evidence_count':len(ev),'call_distance':dist,'direct_failure_link':raw.get('direct_failure_link') is True,'state_transition_match':raw.get('state_transition_match') is True,'recent_diff':raw.get('recent_diff') is True,'environment_only':raw.get('environment_only') is True,'evidence_digest':_d(sorted(ev))})
 except Exception:return {'ok':False,'status':'fault_localization_candidate_invalid','action_executed':False,**DENIED}
 rows.sort(key=lambda x:(-x['score'],x['component_id_digest']));top=rows[0]['score'];ties=sum(x['score']==top for x in rows);margin=top-(rows[1]['score'] if len(rows)>1 else 0);confidence='high' if ties==1 and margin>=4 and rows[0]['direct_failure_link'] else ('medium' if ties==1 and margin>=1 else 'low')
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'reproduction_digest':reproduction_digest,'candidate_count':len(rows),'ranked_candidates':rows,'top_tie_count':ties,'top_score':top,'top_margin':round(margin,4),'confidence':confidence,'single_cause_asserted':False,'speculative_edit_performed':False,'content_free':True,'read_only':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'fault_localization_ranked','fault_localization':rec,'action_executed':False,**DENIED}
def process_fault_localization_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show fault localization','inspect fault localization','show likely causes'}:return {'active':False}
 rec=dict((project_state or {}).get('fault_localization') or {});return {'active':True,'ok':bool(rec),'status':'fault_localization_found' if rec else 'fault_localization_missing','fault_localization':rec,'action_executed':False,**DENIED}
