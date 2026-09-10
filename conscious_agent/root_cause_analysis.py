from __future__ import annotations
"""v1363 evidence-based root-cause role separation."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1363.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'repair_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def analyze_root_cause(*,source_manifest_digest:str,reproduction_digest:str,localization_digest:str,facts:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not all(re.fullmatch(r'[a-f0-9]{64}',str(x or '')) for x in (source_manifest_digest,reproduction_digest,localization_digest)):return {'ok':False,'status':'root_cause_lineage_required','action_executed':False,**DENIED}
 if not facts or len(facts)>256:return {'ok':False,'status':'root_cause_fact_count_invalid','action_executed':False,**DENIED}
 rows=[];seen=set();roots=0
 for raw in facts:
  fid=str(raw.get('fact_id') or '');ev=str(raw.get('evidence_digest') or '')
  if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}',fid) or fid in seen or not re.fullmatch(r'[a-f0-9]{64}',ev):return {'ok':False,'status':'root_cause_fact_invalid','action_executed':False,**DENIED}
  seen.add(fid);direct=raw.get('direct_defect_evidence') is True;necessary=raw.get('necessary_for_failure') is True;trigger=raw.get('triggers_failure') is True;downstream=raw.get('downstream_of_defect') is True;env=raw.get('environment_only') is True
  if env:role='environmental_noise'
  elif direct and necessary:role='root_defect';roots+=1
  elif trigger and not direct:role='triggering_condition'
  elif downstream:role='secondary_symptom'
  else:role='unresolved'
  rows.append({'fact_id_digest':_d(fid),'evidence_digest':ev,'role':role,'direct_defect_evidence':direct,'necessary_for_failure':necessary,'confidence':'high' if role=='root_defect' and direct and necessary else ('medium' if role!='unresolved' else 'low')})
 resolved=roots>0;ambiguous=roots!=1
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'reproduction_digest':reproduction_digest,'localization_digest':localization_digest,'fact_count':len(rows),'roles':rows,'root_defect_count':roots,'root_cause_resolved':resolved,'root_cause_ambiguous':ambiguous,'trigger_count':sum(x['role']=='triggering_condition' for x in rows),'secondary_symptom_count':sum(x['role']=='secondary_symptom' for x in rows),'environmental_noise_count':sum(x['role']=='environmental_noise' for x in rows),'unresolved_count':sum(x['role']=='unresolved' for x in rows),'symptom_only_fix_recommended':False,'read_only':True,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'root_cause_resolved' if resolved and not ambiguous else ('root_cause_ambiguous' if resolved else 'root_cause_unresolved'),'root_cause_analysis':rec,'action_executed':False,**DENIED}
def process_root_cause_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show root cause analysis','inspect root cause','show root cause'}:return {'active':False}
 rec=dict((project_state or {}).get('root_cause_analysis') or {});return {'active':True,'ok':bool(rec),'status':'root_cause_analysis_found' if rec else 'root_cause_analysis_missing','root_cause_analysis':rec,'action_executed':False,**DENIED}
