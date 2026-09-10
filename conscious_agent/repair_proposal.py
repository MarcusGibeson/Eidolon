from __future__ import annotations
"""v1364 narrow evidence-bound repair proposals."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1364.8'
DENIED={'source_mutation_authorized':False,'provider_contact_authorized':False,'network_authorized':False,'release_authorized':False,'approval_granted':False,'independent_authority_granted':False,'repair_execution_authorized':False}
def _d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def propose_repair(*,source_manifest_digest:str,root_cause_digest:str,root_cause_resolved:bool,root_cause_ambiguous:bool,candidates:Sequence[Mapping[str,Any]])->dict[str,Any]:
 if not all(re.fullmatch(r'[a-f0-9]{64}',str(x or '')) for x in (source_manifest_digest,root_cause_digest)):return {'ok':False,'status':'repair_proposal_lineage_required','action_executed':False,**DENIED}
 if not root_cause_resolved or root_cause_ambiguous:return {'ok':True,'status':'repair_proposal_deferred_root_cause_uncertain','repair_proposal':{'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'root_cause_digest':root_cause_digest,'proposal_ready':False,'deferred':True,'read_only':True,'content_free':True,'action_executed':False,**DENIED},'action_executed':False,**DENIED}
 if not candidates or len(candidates)>64:return {'ok':False,'status':'repair_candidate_count_invalid','action_executed':False,**DENIED}
 rows=[]
 for raw in candidates:
  cid=str(raw.get('candidate_id') or '');ev=str(raw.get('evidence_digest') or '');files=list(raw.get('changed_files') or []);tests=list(raw.get('test_ids') or []);risks=list(raw.get('regression_risks') or [])
  if not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',cid) or not re.fullmatch(r'[a-f0-9]{64}',ev) or not files or len(files)>64 or not tests or len(tests)>64:return {'ok':False,'status':'repair_candidate_invalid','action_executed':False,**DENIED}
  if any(not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,180}',str(x)) for x in files+tests+risks):return {'ok':False,'status':'repair_candidate_invalid','action_executed':False,**DENIED}
  acceptable=raw.get('addresses_root_cause') is True and raw.get('rollback_defined') is True and raw.get('predicted_behavior_defined') is True
  rows.append({'candidate_id_digest':_d(cid),'evidence_digest':ev,'changed_file_count':len(files),'changed_file_digests':[_d(x) for x in files],'test_count':len(tests),'test_id_digests':[_d(x) for x in tests],'regression_risk_count':len(risks),'regression_risk_digests':[_d(x) for x in risks],'addresses_root_cause':raw.get('addresses_root_cause') is True,'rollback_defined':raw.get('rollback_defined') is True,'predicted_behavior_defined':raw.get('predicted_behavior_defined') is True,'acceptable':acceptable})
 acceptable=[x for x in rows if x['acceptable']]
 if not acceptable:return {'ok':True,'status':'repair_proposal_deferred_no_sufficient_candidate','repair_proposal':{'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'root_cause_digest':root_cause_digest,'proposal_ready':False,'deferred':True,'candidate_count':len(rows),'read_only':True,'content_free':True,'action_executed':False,**DENIED},'action_executed':False,**DENIED}
 acceptable.sort(key=lambda x:(x['changed_file_count'],x['regression_risk_count'],-x['test_count'],x['candidate_id_digest']));chosen=acceptable[0]
 rec={'contract_version':CONTRACT_VERSION,'source_manifest_digest':source_manifest_digest,'root_cause_digest':root_cause_digest,'proposal_ready':True,'deferred':False,'candidate_count':len(rows),'selected':chosen,'narrowest_sufficient_candidate':True,'implementation_performed':False,'tests_executed':False,'read_only':True,'content_free':True,'action_executed':False,**DENIED};rec['record_digest']=_d(rec)
 return {'ok':True,'status':'repair_proposal_ready','repair_proposal':rec,'action_executed':False,**DENIED}
def process_repair_proposal_control(text:str,*,project_state=None,**_):
 if str(text or '').strip().lower() not in {'show repair proposal','inspect repair proposal','show proposed repair'}:return {'active':False}
 rec=dict((project_state or {}).get('repair_proposal') or {});return {'active':True,'ok':bool(rec),'status':'repair_proposal_found' if rec else 'repair_proposal_missing','repair_proposal':rec,'action_executed':False,**DENIED}
