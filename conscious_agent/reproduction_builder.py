from __future__ import annotations
"""v1361 deterministic reproduction builder from content-minimized evidence."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1361.8'
EVIDENCE_KINDS={'report','log','screenshot','failed_check','runtime_receipt'}
STEP_KINDS={'prepare_fixture','set_environment','invoke_interface','perform_action','assert_state','capture_result'}
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'reproduction_execution_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_reproduction(*,source_manifest_digest:str,evidence_inputs:Sequence[Mapping[str,Any]],candidates:Sequence[Mapping[str,Any]],environment_digest:str)->dict[str,Any]:
 if not re.fullmatch(r'[a-f0-9]{64}',str(source_manifest_digest or '')) or not re.fullmatch(r'[a-f0-9]{64}',str(environment_digest or '')):return {'ok':False,'status':'reproduction_lineage_required','action_executed':False,**DENIED}
 if not evidence_inputs or len(evidence_inputs)>64 or not candidates or len(candidates)>64:return {'ok':False,'status':'reproduction_input_count_invalid','action_executed':False,**DENIED}
 ev=[]
 for raw in evidence_inputs:
  kind=str(raw.get('kind') or '');dg=str(raw.get('evidence_digest') or '')
  if kind not in EVIDENCE_KINDS or not re.fullmatch(r'[a-f0-9]{64}',dg):return {'ok':False,'status':'reproduction_evidence_invalid','action_executed':False,**DENIED}
  ev.append({'kind':kind,'evidence_digest':dg})
 viable=[]
 for raw in candidates:
  cid=str(raw.get('candidate_id') or '');steps=list(raw.get('steps') or []);dg=str(raw.get('evidence_digest') or '')
  if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',cid) or not re.fullmatch(r'[a-f0-9]{64}',dg) or not steps or len(steps)>32:return {'ok':False,'status':'reproduction_candidate_invalid','action_executed':False,**DENIED}
  norm=[]
  for s in steps:
   kind=str(s.get('kind') or '');target=str(s.get('target_id') or '')
   if kind not in STEP_KINDS or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',target):return {'ok':False,'status':'reproduction_step_invalid','action_executed':False,**DENIED}
   norm.append({'kind':kind,'target_digest':_d(target)})
  row={'candidate_id_digest':_d(cid),'step_count':len(norm),'steps':norm,'evidence_digest':dg,'deterministic':raw.get('deterministic') is True,'reproduces':raw.get('reproduces') is True,'environment_specific':raw.get('environment_specific') is True}
  if row['deterministic'] and row['reproduces']:viable.append(row)
 if not viable:
  rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'environment_digest':environment_digest,'evidence_count':len(ev),'evidence_digest':_d(ev),'status':'not_reproducible','reproduction_found':False,'environment_dependent':any(x.get('environment_specific') is True for x in candidates),'read_only':True,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
  return {'ok':True,'status':'reproduction_not_found','reproduction':rec,'action_executed':False,**DENIED}
 viable.sort(key=lambda x:(x['step_count'],x['candidate_id_digest']));chosen=viable[0]
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'environment_digest':environment_digest,'evidence_count':len(ev),'evidence_digest':_d(ev),'status':'reproduction_ready','reproduction_found':True,'selected_candidate_digest':chosen['candidate_id_digest'],'step_count':chosen['step_count'],'steps':chosen['steps'],'candidate_evidence_digest':chosen['evidence_digest'],'minimal_among_supplied_candidates':True,'deterministic':True,'environment_dependent':chosen['environment_specific'],'raw_report_persisted':False,'raw_log_persisted':False,'raw_screenshot_persisted':False,'read_only':True,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'reproduction_ready','reproduction':rec,'action_executed':False,**DENIED}
def process_reproduction_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show reproduction','inspect reproduction','show reproduction builder'}:return {'active':False}
 rec=dict((project_state or {}).get('reproduction') or {});return {'active':True,'ok':bool(rec),'status':'reproduction_found' if rec else 'reproduction_missing','reproduction':rec,'action_executed':False,**DENIED}
