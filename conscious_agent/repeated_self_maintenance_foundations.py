from __future__ import annotations
"""v1298.0-v1298.2 repeated supervised maintenance-cycle foundations."""
from hashlib import sha256
import json
from typing import Any,Mapping
CONTRACT_VERSION='v1298.2'
STAGES=('inspect','backlog','prioritize','plan','build','test','repair','review','complete')
DENIED_AUTHORITY={'provider_contact_authorized':False,'command_execution_authorized':False,'test_execution_authorized':False,'repair_execution_authorized':False,'project_mutation_authorized':False,'source_mutation_authorized':False,'source_application_authorized':False,'self_update_authorized':False,'rollback_authorized':False,'installation_authorized':False,'promotion_authorized':False,'certification_authorized':False,'release_authorized':False,'standing_authority_granted':False,'autonomous_authority_granted':False}
def digest(v:Any)->str:return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def valid_digest(v:Any)->bool:
 t=str(v or '').strip().lower();return len(t)==64 and all(c in '0123456789abcdef' for c in t)
def create_maintenance_session(*,objective_digest:str,initial_source_digest:str,max_cycles:int=4,max_open_proposals:int=8,max_new_proposals_per_cycle:int=3)->dict[str,Any]:
 if not valid_digest(objective_digest) or not valid_digest(initial_source_digest):raise ValueError('objective_and_source_digest_required')
 mc=int(max_cycles);mp=int(max_open_proposals);mn=int(max_new_proposals_per_cycle)
 if mc<2 or mc>8 or mp<1 or mp>32 or mn<1 or mn>mp:raise ValueError('bounded_maintenance_limits_required')
 body={'contract_version':CONTRACT_VERSION,'objective_digest':objective_digest,'initial_source_digest':initial_source_digest,'current_source_digest':initial_source_digest,'max_cycles':mc,'max_open_proposals':mp,'max_new_proposals_per_cycle':mn,'cycles':[],'seen_work_item_digests':[],'open_proposal_count':0,'active_cycle':None,'status':'ready','content_free':True}
 body['maintenance_session_id']='maintenance_'+digest(body)[:24];body['session_digest']=digest(body);return body|DENIED_AUTHORITY
def start_cycle(state:Mapping[str,Any],*,work_item_digest:str,current_source_digest:str)->dict[str,Any]:
 s=dict(state)
 if s.get('status') not in {'ready','cycle_complete'} or s.get('active_cycle') is not None:raise ValueError('maintenance_session_not_ready')
 if len(s.get('cycles') or [])>=int(s.get('max_cycles') or 0):raise ValueError('maintenance_cycle_budget_exhausted')
 if not valid_digest(work_item_digest) or not valid_digest(current_source_digest):raise ValueError('sealed_cycle_identity_required')
 if current_source_digest!=s.get('current_source_digest'):raise ValueError('stale_cycle_source')
 if work_item_digest in set(s.get('seen_work_item_digests') or []):raise ValueError('duplicate_maintenance_work_rejected')
 idx=len(s.get('cycles') or [])+1;cycle={'cycle_index':idx,'work_item_digest':work_item_digest,'source_digest_at_start':current_source_digest,'planned_source_digest':'','stage':'inspect','next_sequence':1,'prior_event_digest':'','events':[],'test_failures':0,'repair_count':0,'new_proposal_count':0,'open_proposal_count':int(s.get('open_proposal_count') or 0),'status':'active','content_free':True};cycle['cycle_digest']=digest(cycle)
 s['active_cycle']=cycle;s['status']='cycle_active';s['session_digest']=digest({k:v for k,v in s.items() if k!='session_digest'});return s|DENIED_AUTHORITY
def maintenance_event(cycle:Mapping[str,Any],*,sequence:int,event_type:str,evidence_digest:str,source_digest:str,prior_event_digest:str='',test_passed:bool|None=None,new_proposal_count:int=0,open_proposal_count:int|None=None,final_source_digest:str='')->dict[str,Any]:
 if not valid_digest(evidence_digest) or not valid_digest(source_digest):raise ValueError('sealed_event_evidence_required')
 row={'cycle_index':int(cycle.get('cycle_index') or 0),'sequence':int(sequence),'event_type':str(event_type),'evidence_digest':evidence_digest,'source_digest':source_digest,'prior_event_digest':str(prior_event_digest or ''),'test_passed':test_passed,'new_proposal_count':max(0,int(new_proposal_count)),'open_proposal_count':None if open_proposal_count is None else max(0,int(open_proposal_count)),'final_source_digest':str(final_source_digest or ''),'content_free':True};row['event_digest']=digest(row);return row|DENIED_AUTHORITY
